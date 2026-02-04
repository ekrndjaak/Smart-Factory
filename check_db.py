import sqlite3
import os

DB_PATH = "./instance/smartfactory.db"

def check_raw_events():
    if not os.path.exists(DB_PATH):
        print("DB 파일이 없습니다!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 최신 순으로 20개만 출력
    cursor.execute("SELECT * FROM raw_events ORDER BY id DESC LIMIT 20")
    rows = cursor.fetchall()
    
    print(f"{'ID':<3} | {'Time':<19} | {'Line':<12} | {'Station':<10} | {'Unit':<8} | {'Torque':<6} | {'Pass'}")
    print("-" * 85)
    
    for row in rows:
        print(f"{row[0]:<3} | {row[1]:<19} | {row[2]:<12} | {row[3]:<10} | {row[5]:<8} | {row[6]:<6} | {row[7]}")
    
    conn.close()

if __name__ == "__main__":
    check_raw_events()