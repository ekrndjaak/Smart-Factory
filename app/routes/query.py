from flask import Blueprint, jsonify, request
from app.db import get_db

bp = Blueprint("query", __name__)

@bp.route("/kpi/today")
def kpi_today():
    db = get_db()
    date = request.args.get("date")  # 없으면 오늘 날짜로 처리해도 됨
    if not date:
        # SQLite에서 오늘 날짜
        date = db.execute("SELECT date('now','localtime') AS d").fetchone()["d"]

    rows = db.execute("""
        SELECT date, shift, line_id, produced_count, defect_count, stop_minutes, avg_cycle_time
        FROM summary_shift
        WHERE date = ?
        ORDER BY line_id, shift
    """, (date,)).fetchall()

    return jsonify([dict(r) for r in rows])
