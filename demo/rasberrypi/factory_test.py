import sqlite3
import csv
import random
import time
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
TARGET_DIR = os.getenv("TARGET_DIR", "./data")

if not os.path.exists(TARGET_DIR):
    os.makedirs(TARGET_DIR)

DB_PATH = os.path.join(TARGET_DIR, "factory.db")
CSV_PATH = os.path.join(TARGET_DIR, "factory_data.csv")

def init_storage():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assembly_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            process TEXT,
            serial_no TEXT,
            torque_val REAL,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Time', 'Process', 'Serial No', 'Torque', 'Status'])

def generate_production_data():
    serial_no = f"ENG-{random.randint(1000, 9999)}"
    torque = round(random.uniform(40.0, 50.0), 2)
    status = "PASS" if 43.0 <= torque <= 47.0 else "FAIL"
    return {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "process": "Engine_Assembly",
        "serial_no": serial_no,
        "torque_val": torque,
        "status": status
    }

def save_data(data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO assembly_logs (timestamp, process, serial_no, torque_val, status)
        VALUES (?, ?, ?, ?, ?)
    ''', (data['timestamp'], data['process'], data['serial_no'], data['torque_val'], data['status']))
    conn.commit()
    conn.close()

    with open(CSV_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([data['timestamp'], data['process'], data['serial_no'], data['torque_val'], data['status']])

init_storage()
print(f"--- Data Collection Started in: {TARGET_DIR} ---")

for i in range(20):
    data = generate_production_data()
    save_data(data)
    print(f"[{i+1}/20] SAVED: {data['serial_no']} | Result: {data['status']}")
    time.sleep(0.5)

print("--- Task Completed ---")