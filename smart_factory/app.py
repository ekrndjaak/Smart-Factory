import os
import sqlite3
import csv
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'smart_factory_key'
socketio = SocketIO(app, cors_allowed_origins="*")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_DIR = os.getenv("DB_TARGET_DIR", "./data")
DB_PATH = os.path.join(TARGET_DIR, "factory.db")
LOG_PATH = os.path.join(TARGET_DIR, "production_logs.csv")

if not os.path.exists(TARGET_DIR):
    os.makedirs(TARGET_DIR)

# CSV 헤더 생성 (파일이 없을 경우)
if not os.path.exists(LOG_PATH):
    with open(LOG_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Timestamp', 'Torque', 'Is_Pass'])

def get_data():
    if not os.path.exists(DB_PATH):
        return 0, 0, 0, 0, []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='assembly_events'")
        if not cursor.fetchone(): return 0, 0, 0, 0, []
        cursor.execute("SELECT COUNT(*) FROM assembly_events")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM assembly_events WHERE is_pass = 0")
        fail = cursor.fetchone()[0]
        cursor.execute("SELECT id, torque_val FROM assembly_events ORDER BY id DESC LIMIT 10")
        recent_data = cursor.fetchall()
        recent_data.reverse()
        pass_units = total - fail
        rate = round((fail / total * 100), 2) if total > 0 else 0
        return total, pass_units, fail, rate, recent_data
    except:
        return 0, 0, 0, 0, []
    finally:
        conn.close()

@app.route('/api/control', methods=['POST'])
def control_machine():
    command = request.get_json().get('command')
    socketio.emit('server_command', {'command': command})
    print(f"[CONTROL] Sent command to machine: {command}")
    return jsonify({"status": "command_sent"}), 200

@app.route('/api/log', methods=['POST'])
def receive_log():
    data = request.get_json()
    if not data: return jsonify({"error": "No data"}), 400

    torque = data.get('torque')
    is_pass = data.get('is_pass')
    timestamp = data.get('timestamp')

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS assembly_events (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, torque_val REAL, is_pass INTEGER)")
        cursor.execute("INSERT INTO assembly_events (timestamp, torque_val, is_pass) VALUES (?, ?, ?)", (timestamp, torque, is_pass))
        conn.commit()
        conn.close()

        with open(LOG_PATH, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, torque, is_pass])

        total, pass_units, fail, rate, recent_data = get_data()
        socketio.emit('update_data', {
            'total': total,
            'pass': pass_units,
            'fail': fail,
            'rate': rate,
            'new_log': {'torque': torque, 'id': timestamp.split()[-1]} # ID 대용으로 시간 표시
        })

        print(f"✅ Logged & Emitted: {timestamp}")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/')
def dashboard():
    total, pass_units, fail, rate, recent_data = get_data()
    chart_data = [["ID", "Torque"]] + [[str(d[0]), d[1]] for d in recent_data]
    
    html = '''
    <html>
    <head>
        <title>Real-time Factory Monitor</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
        <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; padding: 40px; text-align: center; transition: background-color 0.5s; }
            .container { max-width: 900px; margin: auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.08); }
            .stat-container { display: flex; justify-content: space-around; margin: 20px 0; }
            .stat-box { padding: 15px; width: 22%; background: #f8f9fa; border-radius: 10px; }
            .value { font-size: 24px; font-weight: bold; display: block; }
            #curve_chart { width: 100%; height: 300px; }
            
            /* 제어 버튼 스타일 */
            .control-panel { margin-top: 20px; padding: 20px; border-top: 1px solid #eee; }
            .btn { padding: 12px 25px; font-size: 16px; font-weight: bold; border: none; border-radius: 8px; cursor: pointer; margin: 0 10px; transition: 0.3s; }
            .btn-stop { background-color: #d32f2f; color: white; }
            .btn-stop:hover { background-color: #b71c1c; }
            .btn-start { background-color: #2e7d32; color: white; }
            .btn-start:hover { background-color: #1b5e20; }
            #status_msg { font-size: 14px; font-weight: bold; margin-bottom: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🚀 Live Production Line Monitor</h2>
            
            <div class="control-panel">
                <div id="status_msg" style="color: #28a745;">● System Status: Running</div>
                <button class="btn btn-stop" onclick="sendCommand('stop')">EMERGENCY STOP</button>
                <button class="btn btn-start" onclick="sendCommand('start')">RESUME START</button>
            </div>

            <div class="stat-container">
                <div class="stat-box">Total<span id="total" class="value">''' + str(total) + '''</span></div>
                <div class="stat-box" style="color:green">Pass<span id="pass" class="value">''' + str(pass_units) + '''</span></div>
                <div class="stat-box" style="color:red">Fail<span id="fail" class="value">''' + str(fail) + '''</span></div>
                <div class="stat-box">Defect Rate<span id="rate" class="value">''' + str(rate) + '''%</span></div>
            </div>
            
            <div id="curve_chart"></div>
            <p style="font-size:11px; color:#aaa; margin-top: 20px;">Logs are saved in /data/production_logs.csv</p>
        </div>

        <script>
            google.charts.load('current', {'packages':['corechart']});
            let chartData = ''' + str(chart_data) + ''';
            
            function drawChart() {
                var data = google.visualization.arrayToDataTable(chartData);
                var options = { 
                    curveType: 'function', 
                    legend: 'none', 
                    vAxis: { title: 'Torque', minValue: 10, maxValue: 20 },
                    hAxis: { title: 'Time' },
                    colors: ['#2e7d32']
                };
                var chart = new google.visualization.LineChart(document.getElementById('curve_chart'));
                chart.draw(data, options);
            }
            google.charts.setOnLoadCallback(drawChart);

            // 서버로 제어 명령 전송 함수
            function sendCommand(cmd) {
                fetch('/api/control', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({command: cmd})
                })
                .then(response => response.json())
                .then(data => {
                    const msgElement = document.getElementById('status_msg');
                    if (cmd === 'stop') {
                        msgElement.innerText = "⚠️ System Status: STOPPED";
                        msgElement.style.color = "red";
                    } else {
                        msgElement.innerText = "● System Status: Running";
                        msgElement.style.color = "#28a745";
                    }
                });
            }

            var socket = io();
            socket.on('update_data', function(msg) {
                document.getElementById('total').innerText = msg.total;
                document.getElementById('pass').innerText = msg.pass;
                document.getElementById('fail').innerText = msg.fail;
                document.getElementById('rate').innerText = msg.rate + '%';
                
                chartData.push([msg.new_log.id, msg.new_log.torque]);
                if (chartData.length > 11) chartData.splice(1, 1);
                drawChart();
            });
        </script>
    </body>
</html>
    '''
    return render_template_string(html)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)