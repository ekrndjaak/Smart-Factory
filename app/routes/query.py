from flask import Blueprint, jsonify, request
from app.db import get_db

bp = Blueprint("query", __name__)

@bp.route("/kpi/today", methods=["GET"])
def kpi_today():
    db = get_db()

    date = request.args.get("date")
    if not date:
        date = db.execute("SELECT date('now','localtime') AS d").fetchone()["d"]

    rows = db.execute("""
        SELECT date, shift, line_id,
               produced_count, defect_count, stop_minutes, avg_cycle_time,
               last_event_ts
        FROM summary_shift
        WHERE date = ?
        ORDER BY line_id ASC, shift ASC
    """, (date,)).fetchall()

    return jsonify([dict(r) for r in rows])
