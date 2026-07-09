"""
Chat Blueprint — /api/chat
Manages multi-turn conversation sessions backed by server-side sessions.
"""
from flask import Blueprint, request, jsonify, session
from app.agents import travel_agent
import logging, uuid

chat_bp = Blueprint("chat", __name__)
logger = logging.getLogger(__name__)


def _get_history() -> list[dict]:
    if "conversation" not in session:
        session["conversation"] = []
    return session["conversation"]


def _save_turn(role: str, content: str):
    history = _get_history()
    history.append({"role": role, "content": content})
    # Keep last 40 turns in session to avoid cookie overflow
    session["conversation"] = history[-40:]


@chat_bp.post("/message")
def message():
    data = request.get_json(silent=True) or {}
    user_msg = (data.get("message") or "").strip()
    if not user_msg:
        return jsonify({"error": "message is required"}), 400

    history = _get_history()
    user_params = {
        "region": data.get("region", "india"),
    }

    try:
        result = travel_agent.chat(
            user_message=user_msg,
            conversation_history=history,
            user_params=user_params,
        )
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        logger.exception("Chat inference failed: %s", exc)
        return jsonify({"error": "AI service temporarily unavailable."}), 502

    # Persist both turns
    _save_turn("user", user_msg)
    _save_turn("assistant", result["reply"])

    return jsonify({
        "reply": result["reply"],
        "tokens_used": result["tokens_used"],
        "model_id": result["model_id"],
        "turn_index": len(session["conversation"]) // 2,
    })


@chat_bp.post("/reset")
def reset():
    session.pop("conversation", None)
    return jsonify({"status": "cleared"})


@chat_bp.get("/history")
def get_history():
    return jsonify({"history": _get_history()})
