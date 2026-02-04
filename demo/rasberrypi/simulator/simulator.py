import os
import requests
import time
import random
import socketio
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# 서버 주소 설정
SERVER_IP = os.getenv("SERVER_IP", "127.0.0.1")
SERVER_URL = f"http://{SERVER_IP}:5000/api/log"
SOCKET_URL = f"http://{SERVER_IP}:5000"

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

# ------------------------------------------

def generate_production_data():
    if not is_running:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ... Machine Stopped (Waiting for Start Command) ...", end='\r')
        return

    torque = round(random.uniform(12.0, 18.0), 2)
    is_pass = 1 if random.random() > 0.1 else 0
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    payload = {
        "machine_id": "PRD-001",
        "torque": torque,
        "is_pass": is_pass,
        "timestamp": timestamp
    }

    print(f"\n[*] Generated: {timestamp} | Torque: {torque} | Pass: {is_pass}")

    try:
        response = requests.post(SERVER_URL, json=payload, timeout=2)
        if response.status_code == 200:
            print(f" -> OK: Server received data.")
        else:
            print(f" -> Error: Server responded with {response.status_code}")
    except Exception as e:
        print(f" -> Fail: Connection error ({e})")

if __name__ == "__main__":
    print(f"Target API: {SERVER_URL}\n")
    try:
        while True:
            generate_production_data()
            time.sleep(2) # 제어 반응을 확인하기 위해 2초로 단축
    except KeyboardInterrupt:
        sio.disconnect()
        print("\nSimulator Finished.")