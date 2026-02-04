import os, time, sqlite3
from datetime import datetime

DB_PATH = os.path.join("instance", "smartfactory.db")

def get_shift(dt: datetime):
    h = dt.hour
    return "DAY" if 8 <= h < 20 else "NIGHT"

def get_date_for_shift(dt: datetime):
    # NIGHT(20~08)는 날짜 경계 넘어가니까 0~7시는 "전날"로 잡는 게 보통 자연스러움
    if dt.hour < 8:
        dt = dt.replace(hour=12)  # 임시로 정오로 만들어 전날 계산 쉽게
        dt = dt.fromtimestamp(dt.timestamp() - 24*3600)
    return dt.strftime("%Y-%m-%d")

def aggregate_once():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # raw_events를 전부 훑는 단순 버전(데이터 많아지면 last_event_ts 기준 증분으로 바꾸면 됨)
    rows = cur.execute("""
        SELECT ts, line_id, event_type, cycle_time
        FROM raw_events
        ORDER BY ts ASC
    """).fetchall()

    # 메모리에서 집계
    buckets = {}  # (date, shift, line_id) -> dict
    cycle_sum = {}
    cycle_cnt = {}

    for r in rows:
        dt = datetime.fromtimestamp(r["ts"])
        shift = get_shift(dt)
        date = dt.strftime("%Y-%m-%d")
        if shift == "NIGHT" and dt.hour < 8:
            # 야간 교대는 전날로 귀속
            date = get_date_for_shift(dt)

        key = (date, shift, r["line_id"])
        if key not in buckets:
            buckets[key] = {"produced":0, "defect":0, "stop":0, "last_ts":0}

        et = r["event_type"]
        if et == "PRODUCED":
            buckets[key]["produced"] += 1
        elif et == "DEFECT":
            buckets[key]["defect"] += 1
        elif et == "STOP_MINUTE":
            buckets[key]["stop"] += 1  # 1분 정지 이벤트를 1개=1분으로 치는 방식(너 이벤트 설계에 맞게 바꿔)
        # 마지막 ts 업데이트
        buckets[key]["last_ts"] = max(buckets[key]["last_ts"], r["ts"])

        if r["cycle_time"] is not None:
            cycle_sum[key] = cycle_sum.get(key, 0.0) + float(r["cycle_time"])
            cycle_cnt[key] = cycle_cnt.get(key, 0) + 1

    # summary_shift upsert
    for key, v in buckets.items():
        date, shift, line_id = key
        avg_cycle = None
        if cycle_cnt.get(key, 0) > 0:
            avg_cycle = cycle_sum[key] / cycle_cnt[key]

        cur.execute("""
            INSERT INTO summary_shift(date, shift, line_id, produced_count, defect_count, stop_minutes, avg_cycle_time, last_event_ts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date, shift, line_id)
            DO UPDATE SET
              produced_count=excluded.produced_count,
              defect_count=excluded.defect_count,
              stop_minutes=excluded.stop_minutes,
              avg_cycle_time=excluded.avg_cycle_time,
              last_event_ts=excluded.last_event_ts
        """, (date, shift, line_id, v["produced"], v["defect"], v["stop"], avg_cycle, v["last_ts"]))

    conn.commit()
    conn.close()
    print("Aggregated:", len(buckets), "buckets")

if __name__ == "__main__":
    while True:
        aggregate_once()
        time.sleep(60)
