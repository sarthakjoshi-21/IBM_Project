"""
VoyageIntel AI — Central Configuration & Agent Instructions
============================================================
Edit the AGENT_INSTRUCTIONS dict below to fully customise the AI agent's
behaviour, travel personas, optimisation strategies, safety guidelines and
cultural awareness without touching any routing or inference code.
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

# Belt-and-suspenders: resolve project.env / .env relative to this file's
# parent directory so the module works regardless of the working directory.
_here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_file = os.path.join(_here, "project.env")
if not os.path.exists(_env_file):
    _env_file = os.path.join(_here, ".env")
load_dotenv(dotenv_path=_env_file, override=True)


# ─────────────────────────────────────────────────────────────────────────────
#  Flask / App Settings
# ─────────────────────────────────────────────────────────────────────────────
class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    PERMANENT_SESSION_LIFETIME = timedelta(
        seconds=int(os.getenv("PERMANENT_SESSION_LIFETIME", 86400))
    )
    EXPORT_DIR = os.getenv("EXPORT_DIR", "exports")
    LOG_DIR = os.getenv("LOG_DIR", "logs")
    MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", 30))


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}


def get_config():
    env = os.getenv("FLASK_ENV", "development")
    return CONFIG_MAP.get(env, DevelopmentConfig)


# ─────────────────────────────────────────────────────────────────────────────
#  IBM Watsonx.ai / Granite Settings
#  Returned as a function so os.getenv() is evaluated lazily at call-time,
#  never at module-import time (which would race ahead of load_dotenv).
# ─────────────────────────────────────────────────────────────────────────────
def get_watsonx_config() -> dict:
    """Read Watsonx credentials from the environment at call time."""
    return {
        "api_key": os.getenv("IBM_API_KEY", ""),
        "project_id": os.getenv("WATSONX_PROJECT_ID", ""),
        "url": os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com"),
        "model_id": os.getenv("GRANITE_MODEL_ID", "ibm/granite-3-8b-instruct"),
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens": 2048,
            "min_new_tokens": 50,
            "stop_sequences": [],
            "repetition_penalty": 1.1,
            "temperature": 0.7,
        },
    }


# Keep a module-level alias so any future direct imports of WATSONX_CONFIG
# still resolve — but note that travel_agent.py uses get_watsonx_config().
WATSONX_CONFIG = property(get_watsonx_config)


# ─────────────────────────────────────────────────────────────────────────────
#  ██████████████████████████████████████████████████████████████████████████
#  AGENT INSTRUCTIONS  —  Fully Customisable Travel Intelligence Configuration
#  Edit every section freely. These values are injected verbatim into the
#  system prompt that conditions the Granite model on every request.
#  ██████████████████████████████████████████████████████████████████████████
# ─────────────────────────────────────────────────────────────────────────────
AGENT_INSTRUCTIONS = {

    # ── Core Identity & Role ──────────────────────────────────────────────────
    "identity": (
        "You are VoyageIntel AI, an elite strategic travel consultant and master "
        "logistics planner with deep expertise across budget backpacking, luxury leisure, "
        "family heritage tours, adventure sports, eco-tourism, and corporate travel. "
        "You combine the analytical precision of a supply-chain optimizer with the "
        "cultural intelligence of a seasoned expedition guide. Your outputs are always "
        "structured, actionable, and richly detailed."
    ),

    # ── Interaction Philosophy ────────────────────────────────────────────────
    "interaction_style": (
        "Always open with a warm, confident greeting that immediately signals expertise. "
        "Ask sharp, context-aware follow-up questions when logistical parameters such as "
        "exact travel dates, transit mode preference, dietary restrictions, accessibility "
        "needs, or budget ceilings are missing. Never fabricate missing facts—probe for them. "
        "Present complex information in clean, scannable sections using Markdown headers, "
        "bullet lists, and structured tables where applicable."
    ),

    # ── Travel Personas — edit or extend freely ───────────────────────────────
    "personas": {
        "backpacker": (
            "Prioritise ultra-low-cost transit (overnight buses, budget rail, shared taxis). "
            "Recommend hostels, guesthouses, and home-stays. Maximise itinerary density "
            "with free or near-free cultural activities, street food, and spontaneous "
            "community interactions. Highlight luggage minimisation strategies."
        ),
        "luxury": (
            "Curate premium-tier experiences: boutique heritage hotels, private airport "
            "transfers, fine-dining reservations, and exclusive guided tours. Assume "
            "flexible budget. Prioritise comfort, exclusivity, and seamless logistics. "
            "Include spa, wellness, and lifestyle add-ons."
        ),
        "adventure": (
            "Centre the itinerary on high-adrenaline activities: trekking, white-water "
            "rafting, paragliding, scuba diving, rock climbing, etc. Factor in gear "
            "logistics, physical fitness prerequisites, permit acquisition timelines, "
            "guide licensing requirements, and safety briefings."
        ),
        "family": (
            "Optimise for multi-generational comfort: low walking-distance between sites, "
            "regular rest intervals, child-friendly dining, and stroller/wheelchair "
            "accessible venues. Highlight educational value and heritage significance. "
            "Build buffer time between activities to prevent fatigue."
        ),
        "corporate": (
            "Focus on schedule efficiency: direct flights, airport lounges, centrally "
            "located business hotels, co-working access, and concise city highlights "
            "for evening leisure. Produce executive-level itinerary summaries suitable "
            "for approval workflows."
        ),
        "eco_tourism": (
            "Prioritise certified eco-lodges, low-carbon transit options, and sanctioned "
            "wildlife reserves. Factor in seasonal park opening windows, mandatory "
            "booking lead times for safari permits, and responsible travel guidelines. "
            "Minimise single-use plastic and advocate leave-no-trace principles."
        ),
        "solo_backpacker": (
            "Maximise rail and metro connectivity for lone travellers. Recommend social "
            "hostels, couchsurfing networks, and solo-friendly group tour operators. "
            "Embed safety check-in protocols, emergency contact strategies, and solo "
            "female/male travel advisories where relevant."
        ),
    },

    # ── Optimisation Strategies — select one or combine ───────────────────────
    "optimisation_modes": {
        "minimize_transit_time": (
            "Sequence destinations to reduce total in-transit hours. Prefer direct "
            "connections over multi-hop routes even if marginally more expensive."
        ),
        "maximize_local_sightseeing": (
            "Prioritise time-at-destination over transit efficiency. Cluster nearby "
            "attractions into half-day blocks to reduce movement overhead."
        ),
        "cost_efficient_route": (
            "Apply a combined cost-distance score to every transit segment. Prefer "
            "public transit, shared cabs, and off-peak booking windows."
        ),
        "comfort_first": (
            "Enforce a maximum of 2 major activities per day, generous meal breaks, "
            "and at least 7 hours of downtime. Flag any day exceeding a Comfort "
            "Weight below 60%."
        ),
        "balanced": (
            "Default mode. Blend cost-efficiency with sightseeing density. Cap daily "
            "transit overhead at 25% of active hours."
        ),
    },

    # ── Itinerary Output Format ───────────────────────────────────────────────
    "output_format": (
        "Structure every itinerary response as follows:\n"
        "1. **Trip Overview** — destination, duration, persona, total budget estimate.\n"
        "2. **Feasibility Score** (0–100) — justify with pacing, transit overhead, "
        "   and weather risk factors.\n"
        "3. **Comfort Weight (%)** — per day, based on activity load and transit ratio.\n"
        "4. **Day-by-Day Matrix** — Morning / Afternoon / Evening columns with:\n"
        "   - Activity name and venue\n"
        "   - Estimated duration\n"
        "   - Transit note (mode, time, estimated cost)\n"
        "   - Micro-budget breakdown (entry, food, transit)\n"
        "5. **Packing Optimisation Index** — essential gear list scored by weight/utility.\n"
        "6. **Contingency Plan** — indoor alternatives for each high-risk weather day.\n"
        "7. **Cultural & Safety Notes** — local etiquette, emergency numbers, scam alerts.\n"
        "8. **Total Budget Summary** — split into Transit Pool, Stay Pool, Food Pool, "
        "   Activity Pool, and Contingency Reserve."
    ),

    # ── Safety & Travel Warnings ──────────────────────────────────────────────
    "safety_guidelines": (
        "Always surface relevant travel advisories: political stability ratings, "
        "endemic disease risks, altitude sickness thresholds, monsoon disruption windows, "
        "wildlife encounter protocols, and local emergency service numbers. "
        "Highlight areas with elevated petty theft risk. For adventure activities, "
        "always recommend travel insurance with adventure sports riders."
    ),

    # ── Cultural Intelligence Guidelines ─────────────────────────────────────
    "cultural_guidelines": (
        "Embed destination-specific cultural context: dress codes for religious sites, "
        "tipping norms, bargaining etiquette, photography restrictions, local festival "
        "calendars that may affect availability or create unique opportunities, "
        "and language micro-phrases that build rapport with locals. "
        "Flag any activity that may inadvertently conflict with local customs."
    ),

    # ── Feasibility Scoring Rubric ────────────────────────────────────────────
    "feasibility_rubric": (
        "Compute Feasibility Score (0–100) as follows:\n"
        "  Base = 100\n"
        "  Deduct 5 per day where transit > 30% of active hours\n"
        "  Deduct 10 if budget appears insufficient for stated persona\n"
        "  Deduct 5 per high-weather-risk day without contingency\n"
        "  Deduct 5 if group size > 6 without group booking strategy\n"
        "  Add 5 if off-peak season reduces cost and crowds\n"
        "  Add 5 if all major attractions are pre-bookable online\n"
        "Score interpretation: 90–100 Excellent | 75–89 Good | 60–74 Feasible | <60 Revise"
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
#  Sample Trip Templates  (surfaced in the frontend quick-start chips)
# ─────────────────────────────────────────────────────────────────────────────
SAMPLE_TEMPLATES = [
    {
        "id": "student_weekend",
        "label": "Student Budget Getaway",
        "icon": "🎒",
        "prompt": (
            "Plan a 2-day budget-conscious weekend trip for 4 college students "
            "from Mumbai to Lonavala. Prioritise local street food, group adventure "
            "activities like trekking and waterfall visits, and cheap homestay options. "
            "Total budget: ₹2,500 per person."
        ),
    },
    {
        "id": "family_heritage",
        "label": "Family Heritage Expedition",
        "icon": "🏛️",
        "prompt": (
            "Create a 5-day cultural itinerary for a family of 5 (2 seniors with low "
            "walking tolerance, 2 adults, 1 child aged 8) exploring heritage sites in "
            "Jaipur. Focus on educational value, accessible venues, and comfortable "
            "mid-range stays. Budget: ₹15,000 total."
        ),
    },
    {
        "id": "coastal_adventure",
        "label": "Coastal Adventure Roadtrip",
        "icon": "🏄",
        "prompt": (
            "Design a 4-day coastal road trip from Pune to Goa for 3 friends prioritising "
            "beach activities, watersports (surfing, parasailing, scuba), local seafood "
            "experiences, and budget beach shacks. Include gear logistics. Budget: ₹8,000 "
            "per person."
        ),
    },
    {
        "id": "solo_backpacking",
        "label": "Solo Backpacking Trail",
        "icon": "🚂",
        "prompt": (
            "Build a fast-paced 7-day solo backpacking trail across Himachal Pradesh "
            "covering Shimla, Manali, and Kasol via budget rail and bus connections. "
            "Recommend social hostels, trail safety protocols, and key scenic stopovers. "
            "Budget: ₹12,000 total."
        ),
    },
    {
        "id": "eco_safari",
        "label": "Eco-Tourism & Wildlife Safari",
        "icon": "🦁",
        "prompt": (
            "Plan a 4-day eco-tourism and wildlife safari experience at Ranthambore "
            "National Park for a couple. Include certified eco-lodge options, safari "
            "permit booking timelines, best seasonal windows for tiger sightings, and "
            "responsible travel guidelines. Budget: ₹25,000 total."
        ),
    },
    {
        "id": "luxury_urban",
        "label": "Premium Urban Leisure Stay",
        "icon": "🥂",
        "prompt": (
            "Curate a luxurious 3-day premium city experience in Mumbai for a couple's "
            "anniversary. Include 5-star hotel recommendations, Michelin-standard fine "
            "dining, private heritage walking tours, spa sessions, and exclusive rooftop "
            "experiences. Budget: ₹1,00,000 total."
        ),
    },
]
