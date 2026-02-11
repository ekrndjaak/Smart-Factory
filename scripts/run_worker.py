import os
import time
import sqlite3
from datetime import datetime

DB_PATH = os.path.join("instance", "smartfactory.db")

def get_shift(dt: datetime) -> str:
    return "DAY" if 8 <= dt.hour < 20 else "NIGHT"

def shift_date(dt: datetime) -> str:
    # NIGHT 교대(20~08): 0~7시는 전날로 귀속
    if dt.hour < 8:
        dt = datetime.fromtimestamp(dt.timestamp() - 24*3600)
    return dt.strftime("%Y-%m-%d")

def ensure_summary_row(cur, date, shift, line_id):
    cur.execute("""
        INSERT OR IGNORE INTO summary_shift
        (date, shift, line_id, produced_count, defect_count, stop_minutes, avg_cycle_time, last_event_ts)
        VALUES (?, ?, ?, 0, 0, 0, NULL, 0)
    """, (date, shift, line_id))

def aggregate_incremental_once():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()


    summary_rows = cur.execute("""
        SELECT date, shift, line_id, last_event_ts, produced_count, defect_count, stop_minutes
        FROM summary_shift
    """).fetchall()

    last_map = {}
    for r in summary_rows:
        last_map[(r["date"], r["shift"], r["line_id"])] = int(r["last_event_ts"] or 0)

    lines = cur.execute("SELECT DISTINCT line_id FROM raw_events").fetchall()
    line_ids = [r["line_id"] for r in lines]

    processed = 0
    changed_keys = set()

    for line_id in line_ids:

        rows = cur.execute("""
            SELECT ts, line_id, event_type, cycle_time
            FROM raw_events
            WHERE line_id = ?
            ORDER BY ts ASC
        """, (line_id,)).fetchall()

        for ev in rows:
            dt = datetime.fromtimestamp(ev["ts"])
            shift = get_shift(dt)
            date = shift_date(dt) if shift == "NIGHT" else dt.strftime("%Y-%m-%d")
            key = (date, shift, ev["line_id"])

            last_ts = last_map.get(key, 0)
            if ev["ts"] <= last_ts:
                continue

            ensure_summary_row(cur, date, shift, ev["line_id"])

            s = cur.execute("""
                SELECT produced_count, defect_count, stop_minutes, avg_cycle_time, last_event_ts
                FROM summary_shift
                WHERE date=? AND shift=? AND line_id=?
            """, key).fetchone()

            produced = int(s["produced_count"])
            defect = int(s["defect_count"])
            stopm = int(s["stop_minutes"])
            avg_cycle = s["avg_cycle_time"]
            last_event_ts = int(s["last_event_ts"])

            et = ev["event_type"]
            if et == "PRODUCED":
                produced += 1
            elif et == "DEFECT":
                defect += 1
            elif et == "STOP_MINUTE":
                stopm += 1

            if ev["cycle_time"] is not None:
                ct = float(ev["cycle_time"])
                if avg_cycle is None:
                    avg_cycle = ct
                else:
                    avg_cycle = (float(avg_cycle) + ct) / 2.0

            last_event_ts = max(last_event_ts, ev["ts"])

            cur.execute("""
                UPDATE summary_shift
                SET produced_count=?,
                    defect_count=?,
                    stop_minutes=?,
                    avg_cycle_time=?,
                    last_event_ts=?
                WHERE date=? AND shift=? AND line_id=?
            """, (produced, defect, stopm, avg_cycle, last_event_ts, *key))

            last_map[key] = last_event_ts
            changed_keys.add(key)
            processed += 1

    conn.commit()
    conn.close()
    print(f"[worker] processed_events={processed}, changed_buckets={len(changed_keys)}")

if __name__ == "__main__":
    while True:
        aggregate_incremental_once()
        time.sleep(10)
