import sqlite3
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_dir, "data", "factory.db")

def analyze_quality():
    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found at: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM assembly_logs")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM assembly_logs WHERE status = 'FAIL'")
        fail_count = cursor.fetchone()[0]
        
        if total_count == 0:
            print("No data found in database.")
            return

        pass_count = total_count - fail_count
        defect_rate = (fail_count / total_count) * 100

        print("-" * 30)
        print("      DAILY PRODUCTION REPORT      ")
        print("-" * 30)
        print(f"Total Produced : {total_count:>5} units")
        print(f"Pass Units     : {pass_count:>5} units")
        print(f"Fail Units     : {fail_count:>5} units")
        print("-" * 30)
        print(f"Defect Rate    : {defect_rate:>6.2f}%")
        print("-" * 30)

    except sqlite3.OperationalError as e:
        print(f"[ERROR] Table not found or DB error: {e}")
    finally:
        conn.close()

analyze_quality()