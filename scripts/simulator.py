import time
import random
import argparse
import requests
from datetime import datetime

EVENT_TYPES = ["PRODUCED", "DEFECT", "STOP_START", "STOP_END"]

def post_event(base_url: str, payload: dict):
    url = f"{base_url.rstrip('/')}/api/events"
    r = requests.post(url, json=payload, timeout=5)
    if r.status_code >= 400:
        raise RuntimeError(f"POST failed {r.status_code}: {r.text}")
    return r.json() if r.headers.get("content-type", "").startswith("application/json") else {"ok": True}

def main():
    ap = argparse.ArgumentParser(description="Smart Factory event simulator (POST /api/events)")
    ap.add_argument("--base", default="http://localhost:5000", help="server base url (ex: http://localhost:5000)")
    ap.add_argument("--device", default="sim-01")
    ap.add_argument("--line", default="LINE-1")
    ap.add_argument("--minutes", type=float, default=1.0, help="how long to run")
    ap.add_argument("--rate", type=float, default=1.0, help="events per second (approx)")
    ap.add_argument("--seed", type=int, default=42)

    ap.add_argument("--defect_p", type=float, default=0.08, help="defect probability per produced (0~1)")
    ap.add_argument("--stop_start_p", type=float, default=0.03, help="probability to start stop per loop (0~1)")
    ap.add_argument("--stop_end_p", type=float, default=0.35, help="probability to end stop per loop while stopped (0~1)")

    args = ap.parse_args()
    random.seed(args.seed)

    stations = ["ST1", "ST2", "ST3", "ST4"]
    start = time.time()
    end = start + args.minutes * 60

    unit_no = 1
    stopped = False
    produced = 0
    defects = 0
    stops_started = 0
    stops_ended = 0

    interval = max(0.01, 1.0 / max(args.rate, 0.001))

    print(f"[sim] start {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[sim] base={args.base}, line={args.line}, minutes={args.minutes}, rate={args.rate}/s")

    while time.time() < end:
        station = random.choice(stations)
        unit_id = f"U-{unit_no:05d}"
        unit_no += 1

        cycle_time = round(random.uniform(8.0, 16.0), 2)
        post_event(args.base, {
            "device_id": args.device,
            "line_id": args.line,
            "station_id": station,
            "event_type": "PRODUCED",
            "unit_id": unit_id,
            "cycle_time": cycle_time
        })
        produced += 1

        if station == "ST3" and random.random() < args.defect_p:
            post_event(args.base, {
                "device_id": args.device,
                "line_id": args.line,
                "station_id": station,
                "event_type": "DEFECT",
                "unit_id": unit_id
            })
            defects += 1

        if (not stopped) and random.random() < args.stop_start_p:
            post_event(args.base, {
                "device_id": args.device,
                "line_id": args.line,
                "event_type": "STOP_START"
            })
            stopped = True
            stops_started += 1

        if stopped and random.random() < args.stop_end_p:
            post_event(args.base, {
                "device_id": args.device,
                "line_id": args.line,
                "event_type": "STOP_END"
            })
            stopped = False
            stops_ended += 1

        time.sleep(interval)

    if stopped:
        post_event(args.base, {
            "device_id": args.device,
            "line_id": args.line,
            "event_type": "STOP_END"
        })
        stops_ended += 1

    print("[sim] done")
    print(f"[sim] produced={produced}, defects={defects}, stop_start={stops_started}, stop_end={stops_ended}")

if __name__ == "__main__":
    main()
