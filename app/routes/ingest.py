from flask import Blueprint, request, jsonify
from app.db import get_db
import time

bp = Blueprint("ingest", __name__)

@bp.route("/events", methods=["POST"])
def ingest_event():
    data = request.get_json(silent=True) or {}

    required = ["device_id", "line_id", "event_type"]
    missing = [k for k in required if k not in data]
    if missing:
        return jsonify({"ok": False, "missing": missing}), 400

    db = get_db()
    db.execute(
        """
        INSERT INTO raw_events
        (ts, device_id, line_id, station_id, event_type, unit_id, cycle_time, defect_code, stop_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(time.time()),
            data["device_id"],
            data["line_id"],
            data.get("station_id"),
            data["event_type"],
            data.get("unit_id"),
            data.get("cycle_time"),
            data.get("defect_code"),
            data.get("stop_reason"),
        )
    )
    db.commit()

    return jsonify({"ok": True})
