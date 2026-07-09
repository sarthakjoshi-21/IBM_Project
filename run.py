"""
WSGI entry point — run with:
    python run.py                  (development)
    gunicorn "run:app"             (production)
"""
from dotenv import load_dotenv
import os

# Load project.env (or fall back to .env) before any app module is imported,
# so every os.getenv() call in config.py and travel_agent.py sees the values.
_env_file = os.path.join(os.path.dirname(__file__), "project.env")
if not os.path.exists(_env_file):
    _env_file = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=_env_file, override=True)

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
