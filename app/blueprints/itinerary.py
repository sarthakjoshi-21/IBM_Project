"""
Itinerary Blueprint — /api/itinerary
Generates structured itineraries from form parameters.
"""
import uuid
import json
import logging
import os
from datetime import datetime

from flask import Blueprint, request, jsonify, session, current_app

from app.agents import travel_agent

itinerary_bp = Blueprint("itinerary", __name__)
logger = logging.getLogger(__name__)


def _trips_store() -> list:
    if "trips" not in session:
        session["trips"] = []
    return session["trips"]


@itinerary_bp.post("/generate")
def generate():
    data = request.get_json(silent=True) or {}

    required = ["destination"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    trip_params = {
        "origin": data.get("origin", "Not specified"),
        "destination": data.get("destination"),
        "duration_days": data.get("duration_days", 3),
        "persona": data.get("persona", "balanced"),
        "group_size": data.get("group_size", 1),
        "budget_total": data.get("budget_total", "flexible"),
        "budget_currency": data.get("budget_currency", "₹"),
        "preferences": data.get("preferences", ""),
        "constraints": data.get("constraints", ""),
        "optimisation_mode": data.get("optimisation_mode", "balanced"),
        "travel_dates": data.get("travel_dates", ""),
        "region": data.get("region", "india"),
    }

    try:
        result = travel_agent.generate_itinerary(trip_params)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        logger.exception("Itinerary generation failed: %s", exc)
        return jsonify({"error": "AI service temporarily unavailable."}), 502

    trip_id = str(uuid.uuid4())[:8]
    trip_record = {
        "id": trip_id,
        "created_at": datetime.utcnow().isoformat(),
        "params": trip_params,
        "itinerary": result["reply"],
        "tokens_used": result["tokens_used"],
    }

    trips = _trips_store()
    trips.append(trip_record)
    session["trips"] = trips[-20:]  # Keep last 20 trips

    return jsonify({
        "trip_id": trip_id,
        "itinerary": result["reply"],
        "tokens_used": result["tokens_used"],
        "model_id": result["model_id"],
    })


@itinerary_bp.get("/<trip_id>")
def get_trip(trip_id: str):
    trips = _trips_store()
    trip = next((t for t in trips if t["id"] == trip_id), None)
    if not trip:
        return jsonify({"error": "Trip not found"}), 404
    return jsonify(trip)
