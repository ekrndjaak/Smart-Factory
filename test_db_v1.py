import os
from dotenv import load_dotenv
import pymysql

load_dotenv() 

db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'db': os.getenv('DB_NAME'),
    'charset': 'utf8mb4'
}

def insert_production_event(line_id, station, event_type, unit_id):
    connection = pymysql.connect(**db_config)
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO raw_events (line_id, station, event_type, unit_id) 
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (line_id, station, event_type, unit_id))
        connection.commit()
        print(f"✅ [SUCCESS] {station} - {event_type} 이벤트 기록 완료!")
    finally:
        connection.close()

if __name__ == "__main__":
    insert_production_event('ENG_LINE_B', 'ENG_ASSY_1', 'PASS', 'UNIT_2026_002')