"""Main blueprint — serves the SPA index page and health endpoint."""
from flask import Blueprint, render_template, jsonify
from app.config import SAMPLE_TEMPLATES

main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def index():
    return render_template("index.html", templates=SAMPLE_TEMPLATES)


@main_bp.get("/health")
def health():
    return jsonify({"status": "ok", "service": "VoyageIntel AI"})
