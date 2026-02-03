import os
import requests
import time
import random
import socketio
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# 라즈베리파이 구동 후 127.0.0.1(localhost) 사용
#SERVER_IP = os.getenv("SERVER_IP", "127.0.0.1")
#SERVER_URL = f"http://{SERVER_IP}:5000/api/log"#

#노트북 단독 실행 시
SERVER_URL = "http://127.0.0.1:5000/api/log"
SOCKET_URL = f"http://127.0.0.1:5000"

# --- [추가] 상태 제어 변수 및 소켓 설정 ---
sio = socketio.Client()
is_running = True  # 기기 가동 상태 (기본값: 실행 중)

@sio.on('server_command')
def on_command(data):
    global is_running
    command = data.get('command')
    if command == 'stop':
        is_running = False
        print("\n[⚠️ CONTROL] EMERGENCY STOP RECEIVED FROM SERVER!")
    elif command == 'start':
        is_running = True
        print("\n[▶️ CONTROL] RESUME START RECEIVED. WORKING...")

# 서버 소켓 연결 시도
try:
    sio.connect(SOCKET_URL)
    print(f"[*] Connected to Server Socket: {SOCKET_URL}")
except Exception as e:
    print(f"[*] Socket Connection Failed: {e}")

def generate_production_data():
    # [제어 반영] 서버에서 STOP 명령을 받으면 아무것도 하지 않고 대기
    if not is_running:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ... Machine Stopped (Waiting for Start Command) ...", end='\r')
        return

    # 시간대에 따른 불량률(Fail Rate) 차등 적용
    now = datetime.now()
    hour = now.hour
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')

    # 주간(08~20)은 불량률 10%, 야간(그 외)은 20%로 설정
    fail_threshold = 0.2 if (hour < 8 or hour >= 20) else 0.1
    is_pass = 1 if random.random() > fail_threshold else 0
    
    torque = round(random.uniform(12.0, 18.0), 2)
    
    payload = {
        "line_id": "ENG_LINE_B",
        "station": "ENG_TEST",
        "event_type": "PRODUCTION",
        "unit_id": f"U{random.randint(1000, 9999)}",
        "torque": torque,
        "is_pass": is_pass,
        "timestamp": timestamp,
        "reason_code": "NORMAL" if is_pass == 1 else "ERR_TORQUE"
    }

    # 제어 상태일 때는 출력하지 않다가 작동할 때만 출력
    print(f"\n[*] Generated: {payload['unit_id']} | Station: {payload['station']} | Pass: {is_pass} | Shift: {'NIGHT' if fail_threshold == 0.2 else 'DAY'}")

    try:
        response = requests.post(SERVER_URL, json=payload, timeout=2)
        if response.status_code == 200:
            print(f" -> OK: Data Saved to raw_events table.")
    except Exception as e:
        print(f" -> Fail: Connection error ({e})")

if __name__ == "__main__":
    print(f"🚀 Local Simulator Starting... Target: {SERVER_URL}\n")
    while True:
        generate_production_data()
        time.sleep(3) 