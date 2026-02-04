import os
import sqlite3
import csv
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'smart_factory_key'
socketio = SocketIO(app, cors_allowed_origins="*")

TARGET_DIR = os.getenv("DB_TARGET_DIR", "./data")
DB_PATH = os.path.join(TARGET_DIR, "factory.db")

if not os.path.exists(TARGET_DIR):
    os.makedirs(TARGET_DIR)

# [1] DB 초기화: raw_events와 summary 테이블 생성
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. 원본 로그 테이블 (기존과 동일)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            line_id TEXT,
            station TEXT,
            event_type TEXT,
            unit_id TEXT,
            torque_val REAL,
            is_pass INTEGER,
            reason_code TEXT
        )
    """)

    # 2. 집계 테이블 수정: shift 컬럼 추가 및 PK 재설정
    # 기존 summary 테이블이 있다면 삭제하고 새로 만듭니다 (교대조 구분을 위해)
    cursor.execute("DROP TABLE IF EXISTS summary")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS summary (
            date TEXT,
            line_id TEXT,
            shift TEXT,          -- [추가] DAY 또는 NIGHT
            produced_count INTEGER DEFAULT 0,
            defect_count INTEGER DEFAULT 0,
            PRIMARY KEY (date, line_id, shift) -- [수정] 날짜+라인+교대조 조합으로 고유값 설정
        )
    """)

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS stop_logs (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   timestamp TEXT,
                   line_id TEXT,
                   reason_code TEXT,
                   description TEXT)
                   """)
     
    conn.commit()
    conn.close()
    print("✅ DB Schema Updated: Shift column added to summary table.")

def get_current_shift(dt_obj):
    hour = dt_obj.hour
    if 8 <= hour < 20:
        return 'DAY'
    else:
        return 'NIGHT'

# 데이터 조회 로직 
def get_data():
    if not os.path.exists(DB_PATH):
        return 0, 0, 0, 0, []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM raw_events")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM raw_events WHERE is_pass = 0")
        fail = cursor.fetchone()[0]
        cursor.execute("SELECT id, torque_val FROM raw_events ORDER BY id DESC LIMIT 10")
        recent_data = cursor.fetchall()
        recent_data.reverse()
        pass_units = total - fail
        rate = round((fail / total * 100), 2) if total > 0 else 0
        return total, pass_units, fail, rate, recent_data
    except:
        return 0, 0, 0, 0, []
    finally:
        conn.close()

@app.route('/api/log', methods=['POST'])
def receive_log():
    data = request.get_json()
    if not data: return jsonify({"error": "No data"}), 400

    line_id = data.get('line_id', 'UNKNOWN_LINE')
    station = data.get('station', 'UNKNOWN_STATION')
    event_type = data.get('event_type', 'PRODUCTION')
    unit_id = data.get('unit_id', 'N/A')
    torque = data.get('torque')
    is_pass = data.get('is_pass')
    timestamp = data.get('timestamp')
    reason_code = data.get('reason_code', 'NORMAL')
    
    # 1. 교대 근무(Shift) 판별 로직
    # timestamp 형식: '2026-02-03 21:17:21'
    dt_obj = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
    today_date = dt_obj.strftime('%Y-%m-%d')
    hour = dt_obj.hour
    
    # DAY(08:00~20:00), NIGHT(그 외)
    current_shift = 'DAY' if 8 <= hour < 20 else 'NIGHT'

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 2. 원본 데이터 적재
        cursor.execute("""
            INSERT INTO raw_events (
                timestamp, line_id, station, event_type, 
                unit_id, torque_val, is_pass, reason_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, line_id, station, event_type, unit_id, torque, is_pass, reason_code))

        # 3.실시간 집계 (shift 컬럼 포함)
        # ON CONFLICT 대상에 shift를 추가하여 조별로 각각 합산되게 합니다.
        cursor.execute("""
            INSERT INTO summary (date, line_id, shift, produced_count, defect_count)
            VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(date, line_id, shift) DO UPDATE SET
                produced_count = produced_count + 1,
                defect_count = defect_count + ?
        """, (today_date, line_id, current_shift, 
              (1 if is_pass == 0 else 0), (1 if is_pass == 0 else 0)))

        conn.commit()
        conn.close()

        # 대시보드 실시간 업데이트
        total, pass_units, fail, rate, recent_data = get_data()
        socketio.emit('update_data', {
            'total': total, 'pass': pass_units, 'fail': fail, 'rate': rate,
            'new_log': {'torque': torque, 'id': timestamp.split()[-1]}
        })

        print(f"✅ Logged: {unit_id} | Shift: {current_shift} | Station: {station}")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/api/control', methods=['POST'])
def control_machine():
    data = request.get_json()
    command = data.get('command')
    code = data.get('reason_code', '005') # 기본값 005 (기타)

    # 코드별 명칭 매핑
    reason_map = {
        "001": "부품 부족",
        "002": "설비 점검",
        "003": "안전 사고",
        "004": "품질 검사",
        "005": "기타 사유"
    }
    reason_name = reason_map.get(code, "미분류")

    if command == 'stop':
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # timestamp, 라인ID, 코드번호, 코드명칭 저장
        cursor.execute("""
            INSERT INTO stop_logs (timestamp, line_id, reason_code, description)
            VALUES (?, ?, ?, ?)
        """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'ENG_LINE_B', code, reason_name))
        conn.commit()
        conn.close()
        print(f"[🚨 LINE STOP] Code {code} ({reason_name}) Recorded.")

    socketio.emit('server_command', {'command': command, 'reason_code': code, 'reason_name': reason_name})
    return jsonify({"status": "command_sent"}), 200

@app.route('/')
def dashboard():
    total, pass_units, fail, rate, recent_data = get_data()
    chart_data = [["ID", "Torque"]] + [[str(d[0]), d[1]] for d in recent_data]
    return render_template('dashboard.html', total=total, pass_units=pass_units, fail=fail, rate=rate, chart_data=chart_data)

if __name__ == '__main__':
    init_db()
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)