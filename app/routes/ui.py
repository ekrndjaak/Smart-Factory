from flask import Blueprint, render_template

bp = Blueprint("ui", __name__)

@bp.route("/dashboard", methods=["GET"])
def dashboard():
    return render_template("dashboard.html")
