import os
import requests
import time
import random
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

SERVER_IP = os.getenv("SERVER_IP", "127.0.0.1")
SERVER_URL = f"http://{SERVER_IP}:5000/api/log"

def generate_production_data():
    torque = round(random.uniform(12.0, 18.0), 2)
    is_pass = 1 if random.random() > 0.1 else 0
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    payload = {
        "machine_id": "PRD-001",
        "torque": torque,
        "is_pass": is_pass,
        "timestamp": timestamp
    }

    print(f"[*] Generated: {timestamp} | Torque: {torque} | Pass: {is_pass}")

    try:
        response = requests.post(SERVER_URL, json=payload, timeout=2)
        if response.status_code == 200:
            print(f" -> OK: Server received data.")
        else:
            print(f" -> Error: Server responded with {response.status_code}")
    except Exception as e:
        print(f" -> Fail: Connection error ({e})")

if __name__ == "__main__":
    print(f"Target: {SERVER_URL}\n")
    while True:
        generate_production_data()
        time.sleep(5)