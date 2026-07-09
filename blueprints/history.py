"""
History Blueprint — /api/history
Returns and manages the session-persisted trip history timeline.
"""
from flask import Blueprint, jsonify, session

history_bp = Blueprint("history", __name__)


@history_bp.get("/")
def get_history():
    trips = session.get("trips", [])
    # Return lightweight summaries for the timeline
    summaries = [
        {
            "id": t["id"],
            "created_at": t["created_at"],
            "destination": t["params"].get("destination"),
            "origin": t["params"].get("origin"),
            "duration_days": t["params"].get("duration_days"),
            "persona": t["params"].get("persona"),
            "group_size": t["params"].get("group_size"),
        }
        for t in trips
    ]
    return jsonify({"trips": summaries[::-1]})  # newest first


@history_bp.delete("/<trip_id>")
def delete_trip(trip_id: str):
    trips = session.get("trips", [])
    session["trips"] = [t for t in trips if t["id"] != trip_id]
    return jsonify({"status": "deleted"})


@history_bp.delete("/")
def clear_history():
    session.pop("trips", None)
    return jsonify({"status": "cleared"})
