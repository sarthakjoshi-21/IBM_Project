"""
VoyageIntel AI — Flask Application Factory
"""
import os
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask, jsonify
from flask_session import Session

from .config import get_config


# ── Module-level session extension (importable by blueprints) ─────────────────
server_session = Session()


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # ── Load config ───────────────────────────────────────────────────────────
    cfg = get_config()
    app.config.from_object(cfg)

    # ── Filesystem session store ──────────────────────────────────────────────
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_FILE_DIR"] = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), ".flask_sessions"
    )
    os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
    server_session.init_app(app)

    # ── Ensure export / log dirs ──────────────────────────────────────────────
    for d in [app.config["EXPORT_DIR"], app.config["LOG_DIR"]]:
        abs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), d)
        os.makedirs(abs_path, exist_ok=True)

    # ── Logging ───────────────────────────────────────────────────────────────
    _configure_logging(app)

    # ── Blueprints ────────────────────────────────────────────────────────────
    from .blueprints.main import main_bp
    from .blueprints.chat import chat_bp
    from .blueprints.itinerary import itinerary_bp
    from .blueprints.history import history_bp
    from .blueprints.export import export_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(chat_bp, url_prefix="/api/chat")
    app.register_blueprint(itinerary_bp, url_prefix="/api/itinerary")
    app.register_blueprint(history_bp, url_prefix="/api/history")
    app.register_blueprint(export_bp, url_prefix="/api/export")

    # ── Custom error handlers ─────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(500)
    def server_error(_e):
        app.logger.exception("Internal server error")
        return jsonify({"error": "Internal server error"}), 500

    @app.errorhandler(429)
    def rate_limited(_e):
        return jsonify({"error": "Rate limit exceeded. Please slow down."}), 429

    return app


def _configure_logging(app: Flask) -> None:
    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), app.config["LOG_DIR"]
    )
    log_file = os.path.join(log_dir, "voyageintel.log")
    handler = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=5)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    )
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info("VoyageIntel AI starting up.")
