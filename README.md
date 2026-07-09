# VoyageIntel AI

> **AI-Powered, Hyper-Personalized Travel Intelligence & Itinerary Automation Platform**  
> Built with Python Flask · IBM Watsonx.ai · IBM Granite · Bootstrap 5 · Chart.js

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Directory Structure](#directory-structure)
4. [Quick Start](#quick-start)
5. [Environment Configuration](#environment-configuration)
6. [Agent Instructions — Customization Guide](#agent-instructions--customization-guide)
7. [API Reference](#api-reference)
8. [Frontend Features](#frontend-features)
9. [Production Deployment](#production-deployment)
10. [Extending the Platform](#extending-the-platform)

---

## Project Overview

VoyageIntel AI is an elite travel intelligence platform that combines:

- **IBM Watsonx.ai / Granite models** for deep contextual itinerary reasoning
- **Modular Flask Blueprint architecture** for clean REST API decoupling
- **Multi-session trip history** with PDF export via ReportLab
- **Interactive Chart.js dashboards** for budget, comfort, and transit analytics
- **Cinematic dark-mode UI** built on Bootstrap 5

Users can describe complex trips in natural language ("Plan a 3-day budget road trip from Pune to Goa for 3 college students…") and receive a fully scored, structured, day-by-day itinerary matrix with feasibility scores, comfort weights, packing indexes, and contingency plans.

---

## Architecture

```
Browser (Bootstrap 5 SPA)
        │
        ▼
   Flask Application (run.py → app factory)
        │
        ├─── Blueprint: main      (GET /)
        ├─── Blueprint: chat      (/api/chat/*)
        ├─── Blueprint: itinerary (/api/itinerary/*)
        ├─── Blueprint: history   (/api/history/*)
        └─── Blueprint: export    (/api/export/*/pdf)
                │
                ▼
         TravelAgent (agents/travel_agent.py)
                │
                ▼
         IBM Watsonx.ai · Granite
         (ibm-watsonx-ai SDK)
```

**Session Storage:** Server-side filesystem sessions via `flask-session`.  
**PDF Export:** ReportLab — generates professional A4 guides.  
**Config Isolation:** All credentials in `.env`, never committed to VCS.

---

## Directory Structure

```
voyageintel-ai/
│
├── run.py                      # WSGI entry point
├── requirements.txt
├── .env.example                # Copy → .env and fill in credentials
│
├── app/
│   ├── __init__.py             # Flask application factory + logging
│   ├── config.py               # Config classes + AGENT_INSTRUCTIONS + SAMPLE_TEMPLATES
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   └── travel_agent.py     # TravelAgent singleton — all Watsonx.ai inference
│   │
│   ├── blueprints/
│   │   ├── __init__.py
│   │   ├── main.py             # Root page + health check
│   │   ├── chat.py             # Multi-turn chat API
│   │   ├── itinerary.py        # Structured itinerary generation
│   │   ├── history.py          # Session-based trip history
│   │   └── export.py           # PDF itinerary export
│   │
│   ├── utils/
│   │   └── __init__.py         # (Add shared helpers here)
│   │
│   ├── data/                   # (Add local JSON/CSV transit data here)
│   │
│   ├── templates/
│   │   └── index.html          # Single-page application shell
│   │
│   └── static/
│       ├── css/
│       │   └── styles.css      # Master stylesheet (dark cinematic theme)
│       └── js/
│           ├── app.js          # SPA logic, chat, itinerary, history
│           └── charts.js       # Chart.js dashboard visualisations
│
├── logs/                       # Rotating log files (auto-created)
├── exports/                    # PDF exports (auto-created)
└── .flask_sessions/            # Server-side session store (auto-created)
```

---

## Quick Start

### 1. Prerequisites
- Python 3.11+
- An IBM Cloud account with Watsonx.ai access
- An active Watsonx.ai project

### 2. Clone & Install

```bash
cd voyageintel-ai
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Description |
|---|---|
| `IBM_API_KEY` | Your IBM Cloud API Key |
| `WATSONX_PROJECT_ID` | Your Watsonx.ai project ID |
| `WATSONX_URL` | Regional endpoint (default: us-south) |
| `GRANITE_MODEL_ID` | Model ID (default: `ibm/granite-3-8b-instruct`) |
| `SECRET_KEY` | Long random string for Flask sessions |

### 4. Run (Development)

```bash
python run.py
```

Navigate to **http://localhost:5000**

---

## Environment Configuration

```dotenv
# IBM Watsonx.ai
IBM_API_KEY=your_ibm_cloud_api_key_here
WATSONX_PROJECT_ID=your_watsonx_project_id_here
WATSONX_URL=https://us-south.ml.cloud.ibm.com
GRANITE_MODEL_ID=ibm/granite-3-8b-instruct

# Flask
FLASK_ENV=development
SECRET_KEY=change-me-to-a-long-random-string

# Optional
MAX_REQUESTS_PER_MINUTE=30
```

**Supported Granite Models:**
- `ibm/granite-3-8b-instruct` — Recommended (balanced performance)
- `ibm/granite-3-2b-instruct` — Faster, lower cost

---

## Agent Instructions — Customization Guide

All AI behaviour is controlled by the `AGENT_INSTRUCTIONS` dictionary in [`app/config.py`](app/config.py). Edit freely without touching any routing or inference code.

### Sections

| Key | What it Controls |
|---|---|
| `identity` | Core persona and role of the AI agent |
| `interaction_style` | How the agent greets, asks follow-ups, and formats output |
| `personas` | Travel style definitions (Backpacker, Luxury, Adventure, Family, Corporate, Eco, Solo) |
| `optimisation_modes` | Route & scheduling strategy definitions |
| `output_format` | Exact structure of every itinerary response |
| `safety_guidelines` | Travel advisories, emergency info, insurance recommendations |
| `cultural_guidelines` | Dress codes, tipping norms, etiquette, festival calendars |
| `feasibility_rubric` | Mathematical scoring logic for the 0–100 Feasibility Score |

### Example: Adding a Custom Persona

```python
AGENT_INSTRUCTIONS["personas"]["digital_nomad"] = (
    "Prioritise co-working cafe availability, reliable high-speed WiFi, and "
    "month-to-month accommodation options. Balance productivity windows with "
    "local cultural immersion. Highlight visa-on-arrival and digital nomad "
    "visa programmes."
)
```

### Example: Adding a Custom Optimisation Mode

```python
AGENT_INSTRUCTIONS["optimisation_modes"]["photography_first"] = (
    "Schedule golden-hour (dawn/dusk) slots at iconic viewpoints as hard "
    "constraints. Build itinerary around lighting windows rather than "
    "proximity efficiency."
)
```

---

## API Reference

### Chat

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat/message` | Send a message; returns AI reply |
| `POST` | `/api/chat/reset` | Clear conversation history |
| `GET` | `/api/chat/history` | Get full conversation history |

**POST `/api/chat/message` body:**
```json
{
  "message": "Plan a 3-day trip from Mumbai to Goa",
  "region": "india"
}
```

### Itinerary

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/itinerary/generate` | Generate structured itinerary |
| `GET` | `/api/itinerary/<trip_id>` | Retrieve a specific trip |

**POST `/api/itinerary/generate` body:**
```json
{
  "destination": "Goa",
  "origin": "Pune",
  "duration_days": 3,
  "group_size": 3,
  "budget_total": "8000",
  "budget_currency": "₹",
  "persona": "backpacker",
  "optimisation_mode": "cost_efficient_route",
  "preferences": "street food, adventure sports",
  "constraints": "",
  "travel_dates": "20-22 Dec 2025",
  "region": "india"
}
```

### History

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/history/` | List all saved trips (summaries) |
| `DELETE` | `/api/history/<trip_id>` | Delete a specific trip |
| `DELETE` | `/api/history/` | Clear all history |

### Export

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/export/<trip_id>/pdf` | Download PDF itinerary guide |

---

## Frontend Features

| Feature | Description |
|---|---|
| **AI Travel Chat UI** | Async conversational interface with quick-start destination chips |
| **Trip Planner Form** | Full parameter form with persona + optimisation mode selectors |
| **Itinerary Matrix** | Markdown-rendered structured output with metric cards |
| **Travel Dashboard** | Budget doughnut, daily comfort bar, transit scatter chart |
| **Day Timeline** | Visual day-by-day timeline with morning/afternoon/evening slots |
| **Regional Climate Panel** | Seasonal risk indicators per destination region |
| **Trip History** | Persistent session history with PDF re-export |
| **Loading Overlay** | Cinematic full-screen overlay during AI processing |
| **Toast Notifications** | Non-intrusive status feedback |

---

## Production Deployment

### Gunicorn (Recommended)

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment
export FLASK_ENV=production
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Run with Gunicorn (4 workers)
gunicorn "run:app" \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log
```

### Nginx Reverse Proxy (Example)

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_read_timeout 120s;
    }

    location /static/ {
        alias /path/to/voyageintel-ai/app/static/;
        expires 30d;
    }
}
```

### Docker (Optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "run:app", "--workers=2", "--bind=0.0.0.0:8000", "--timeout=120"]
```

```bash
docker build -t voyageintel-ai .
docker run -p 8000:8000 --env-file .env voyageintel-ai
```

### Security Checklist for Production

- [ ] Set `FLASK_ENV=production`
- [ ] Set `SESSION_COOKIE_SECURE=True` (requires HTTPS)
- [ ] Use a strong, random `SECRET_KEY`
- [ ] Serve behind Nginx with HTTPS (Let's Encrypt)
- [ ] Restrict `.env` file permissions: `chmod 600 .env`
- [ ] Enable log rotation (already configured for 5MB × 5 backups)
- [ ] Set `MAX_REQUESTS_PER_MINUTE` appropriately

---

## Extending the Platform

### Adding a New Travel Micro-Agent

1. Create `app/agents/my_agent.py` with a class following the same pattern as `TravelAgent`.
2. Register it as a singleton: `my_agent = MyAgent()`.
3. Import and call it from a new blueprint in `app/blueprints/`.
4. Register the blueprint in `app/__init__.py`.
5. **No changes to core routing logic required.**

### Adding Third-Party Transit Data

1. Place static JSON/CSV files in `app/data/`.
2. Create a parser in `app/utils/` (e.g., `app/utils/transit_parser.py`).
3. Import and call `_build_context_block()` pattern in `travel_agent.py` to inject parsed data into the prompt payload.

### Adding a New Persona

Edit `AGENT_INSTRUCTIONS["personas"]` in `app/config.py` and add the corresponding `<option>` in the planner form in `app/templates/index.html`.

---

## License

MIT License — see LICENSE file for details.

---

*VoyageIntel AI — Powered by IBM Watsonx.ai · Granite Foundation Models*
