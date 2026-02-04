from flask import Flask
from .db import close_db
from .routes.ingest import bp as ingest_bp
from .routes.query import bp as query_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object("app.config.Config")

    app.teardown_appcontext(close_db)
    app.register_blueprint(ingest_bp, url_prefix="/api")
    app.register_blueprint(query_bp, url_prefix="/api")
    return app
