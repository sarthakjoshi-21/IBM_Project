"""
VoyageIntel AI — Watsonx.ai / IBM Granite Travel Agent
=======================================================
All AI inference flows through this module. Blueprints import
`travel_agent` (the singleton TravelAgent instance) and call its methods.
"""
import json
import logging
from datetime import datetime
from typing import Any

from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

# Import the lazy getter — credentials are read from the environment at the
# moment _ensure_init() is first called, well after load_dotenv() has run.
from app.config import get_watsonx_config, AGENT_INSTRUCTIONS

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  Prompt Builder
# ─────────────────────────────────────────────────────────────────────────────
def _build_system_prompt() -> str:
    ai = AGENT_INSTRUCTIONS
    personas_block = "\n".join(
        f"  [{k.upper()}] {v}" for k, v in ai["personas"].items()
    )
    opt_block = "\n".join(
        f"  [{k.upper()}] {v}" for k, v in ai["optimisation_modes"].items()
    )
    return (
        f"{ai['identity']}\n\n"
        f"INTERACTION STYLE:\n{ai['interaction_style']}\n\n"
        f"TRAVEL PERSONAS:\n{personas_block}\n\n"
        f"OPTIMISATION STRATEGIES:\n{opt_block}\n\n"
        f"OUTPUT FORMAT:\n{ai['output_format']}\n\n"
        f"SAFETY GUIDELINES:\n{ai['safety_guidelines']}\n\n"
        f"CULTURAL GUIDELINES:\n{ai['cultural_guidelines']}\n\n"
        f"FEASIBILITY SCORING RUBRIC:\n{ai['feasibility_rubric']}\n\n"
        f"Today's date: {datetime.utcnow().strftime('%Y-%m-%d')} (UTC). "
        f"Always factor this into seasonal and scheduling logic."
    )


SYSTEM_PROMPT = _build_system_prompt()


# ─────────────────────────────────────────────────────────────────────────────
#  Localized Context Injection Helpers
# ─────────────────────────────────────────────────────────────────────────────
SEASONAL_CONTEXT = {
    "india": {
        "winter": "Oct–Feb: Best travel season. Cool, dry, ideal for most destinations.",
        "summer": "Mar–May: Extreme heat in plains. Hill stations (Manali, Shimla) preferred.",
        "monsoon": "Jun–Sep: Heavy rains. Coastal & Kerala backwaters peak. Mountain roads risky.",
    },
    "europe": {
        "summer": "Jun–Aug: Peak tourist season. Pre-book 3–6 months ahead. High prices.",
        "shoulder": "Apr–May, Sep–Oct: Best value. Mild weather. Fewer crowds.",
        "winter": "Nov–Mar: Cold. Budget flights available. Christmas markets in Dec.",
    },
}

TRANSIT_BENCHMARKS = {
    "india": {
        "rail_speed_kmph": 80,
        "bus_speed_kmph": 50,
        "flight_overhead_hours": 3.0,
        "auto_urban_kmph": 20,
    },
    "europe": {
        "rail_speed_kmph": 160,
        "bus_speed_kmph": 90,
        "flight_overhead_hours": 2.5,
    },
}


def _build_context_block(user_params: dict) -> str:
    """Inject localised seasonal + transit context into the prompt payload."""
    region = user_params.get("region", "india").lower()
    month = datetime.utcnow().month
    if month in (10, 11, 12, 1, 2):
        season = "winter"
    elif month in (3, 4, 5):
        season = "summer"
    else:
        season = "monsoon"

    season_info = SEASONAL_CONTEXT.get(region, SEASONAL_CONTEXT["india"]).get(
        season, ""
    )
    transit_info = json.dumps(
        TRANSIT_BENCHMARKS.get(region, TRANSIT_BENCHMARKS["india"]), indent=2
    )

    return (
        f"\n\n[LOCALISED CONTEXT INJECTION]\n"
        f"Region: {region.title()} | Current season: {season.title()}\n"
        f"Seasonal note: {season_info}\n"
        f"Transit benchmarks (km/h): {transit_info}"
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Model capability helpers
# ─────────────────────────────────────────────────────────────────────────────

# Models that support the /chat/completions-style .chat() API.
# Everything else falls back to .generate_text() with a formatted prompt string.
_CHAT_API_PATTERNS = (
    "granite-3",
    "granite-2",
    "llama-3-1-instruct",
    "llama-3-2-instruct",
    "llama-3-3-instruct",
    "llama-3-instruct",
    "mistral",
    "mixtral",
)


def _uses_chat_api(model_id: str) -> bool:
    """Return True if this model supports the .chat() messages API."""
    lower = model_id.lower()
    return any(p in lower for p in _CHAT_API_PATTERNS)


def _messages_to_prompt(messages: list[dict], model_id: str) -> str:
    """
    Serialise a list of {"role": ..., "content": ...} dicts into a single
    prompt string suitable for .generate_text().

    Uses the Llama-3 special-token template for any llama model;
    falls back to a clean <ROLE>: content\n format for everything else.
    """
    lower = model_id.lower()

    if "llama-3" in lower:
        # Llama-3 base / instruct prompt template
        parts = ["<|begin_of_text|>"]
        for msg in messages:
            role = msg["role"]        # system | user | assistant
            content = msg["content"]
            parts.append(
                f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
            )
        parts.append("<|start_header_id|>assistant<|end_header_id|>\n\n")
        return "".join(parts)

    # Generic plain-text fallback (works well for most completion models)
    lines = []
    for msg in messages:
        role = msg["role"].upper()
        lines.append(f"[{role}]\n{msg['content']}\n")
    lines.append("[ASSISTANT]\n")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
#  Travel Agent Singleton
# ─────────────────────────────────────────────────────────────────────────────
class TravelAgent:
    """Wraps IBM Watsonx.ai ModelInference with conversation context management."""

    def __init__(self):
        self._model: ModelInference | None = None
        self._initialised = False

    # ── Lazy initialisation (avoids import-time failures when .env is absent) ─
    def _ensure_init(self):
        if self._initialised:
            return
        # Call get_watsonx_config() here — at this point load_dotenv() has
        # already run in run.py, so os.getenv() returns the correct values.
        cfg = get_watsonx_config()

        # ── DEBUG: confirm env vars are loaded correctly ──────────────────────
        api_key = cfg["api_key"]
        project_id = cfg["project_id"]
        masked_key = (api_key[:6] + "..." + api_key[-4:]) if len(api_key) >= 10 else ("[EMPTY]" if not api_key else api_key)
        print("=" * 60, flush=True)
        print("[VoyageIntel DEBUG] TravelAgent._ensure_init() called", flush=True)
        print(f"  IBM_API_KEY      : {masked_key}", flush=True)
        print(f"  WATSONX_PROJECT_ID: {project_id if project_id else '[EMPTY]'}", flush=True)
        print(f"  WATSONX_URL      : {cfg['url']}", flush=True)
        print(f"  GRANITE_MODEL_ID : {cfg['model_id']}", flush=True)
        print("=" * 60, flush=True)
        # ── END DEBUG ─────────────────────────────────────────────────────────

        if not cfg["api_key"] or not cfg["project_id"]:
            raise RuntimeError(
                "IBM_API_KEY and WATSONX_PROJECT_ID must be set in the "
                "project.env (or .env) file."
            )

        # Build Credentials with the exact URL and API key from config.
        # Pass credentials directly into ModelInference — this bypasses any
        # internal URL resolution in APIClient and forces the SDK to use the
        # exact endpoint specified in project.env.
        credentials = Credentials(
            url=cfg["url"],
            api_key=cfg["api_key"],
        )
        print(f"[VoyageIntel DEBUG] Credentials object built — url={credentials.url}", flush=True)

        self._model = ModelInference(
            model_id=cfg["model_id"],
            credentials=credentials,
            project_id=cfg["project_id"],
            params=cfg["parameters"],
        )

        # Cache config so we don't re-read env on every request
        self._cfg = cfg
        self._use_chat_api = _uses_chat_api(cfg["model_id"])
        self._initialised = True
        print(
            f"[VoyageIntel DEBUG] TravelAgent initialised OK — "
            f"model: {cfg['model_id']}  |  "
            f"inference_mode: {'chat()' if self._use_chat_api else 'generate_text()'}",
            flush=True,
        )
        logger.info("TravelAgent initialised with model: %s", cfg["model_id"])

    # ── Build the full message list from conversation history ─────────────────
    def _format_conversation(
        self, history: list[dict], user_params: dict
    ) -> list[dict]:
        messages = [{"role": "system", "content": SYSTEM_PROMPT + _build_context_block(user_params)}]
        for turn in history:
            messages.append({"role": turn["role"], "content": turn["content"]})
        return messages

    # ── Public inference entry-point ───────────────────────────────────────────
    def chat(
        self,
        user_message: str,
        conversation_history: list[dict],
        user_params: dict | None = None,
    ) -> dict[str, Any]:
        """
        Send a message to the model and return a structured response dict.
        Automatically uses .chat() for chat-API models (Granite instruct, etc.)
        and .generate_text() for base completion models (Llama base, etc.).

        Args:
            user_message: The latest user message.
            conversation_history: List of {"role": ..., "content": ...} dicts
                                   representing prior turns (excluding the latest).
            user_params: Optional dict with hints like {"region": "india"}.

        Returns:
            dict with keys: reply, tokens_used, model_id
        """
        self._ensure_init()
        params = user_params or {}

        # Build the full message list (used by both paths)
        full_history = conversation_history + [
            {"role": "user", "content": user_message}
        ]
        messages = self._format_conversation(full_history, params)

        logger.info(
            "Sending to %s via %s",
            self._cfg["model_id"],
            "chat()" if self._use_chat_api else "generate_text()",
        )

        try:
            if self._use_chat_api:
                # ── Chat-completions path (Granite instruct, Llama-instruct, …) ──
                response = self._model.chat(messages=messages)
                reply_text = (
                    response.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
                tokens_used = response.get("usage", {}).get("total_tokens", 0)

            else:
                # ── Text-generation path (Llama base, plain completion models) ──
                prompt = _messages_to_prompt(messages, self._cfg["model_id"])
                response = self._model.generate_text(prompt=prompt)
                # generate_text() returns the generated string directly
                reply_text = response.strip() if isinstance(response, str) else (
                    response.get("results", [{}])[0].get("generated_text", "").strip()
                )
                tokens_used = 0
                if isinstance(response, dict):
                    tokens_used = (
                        response.get("results", [{}])[0]
                        .get("generated_token_count", 0)
                    )

            return {
                "reply": reply_text,
                "tokens_used": tokens_used,
                "model_id": self._cfg["model_id"],
            }

        except Exception as exc:
            import traceback
            print("[VoyageIntel DEBUG] Watsonx.ai inference FAILED:", flush=True)
            print(traceback.format_exc(), flush=True)
            logger.exception("Watsonx.ai inference error: %s", exc)
            raise

    # ── Structured itinerary generation ───────────────────────────────────────
    def generate_itinerary(self, trip_params: dict) -> dict[str, Any]:
        """
        Generate a structured itinerary from a rich parameter dict.
        trip_params keys: destination, origin, duration_days, persona,
                          budget_total, budget_currency, group_size,
                          preferences, constraints, optimisation_mode
        """
        prompt = self._build_itinerary_prompt(trip_params)
        result = self.chat(
            user_message=prompt,
            conversation_history=[],
            user_params={"region": trip_params.get("region", "india")},
        )
        return result

    @staticmethod
    def _build_itinerary_prompt(p: dict) -> str:
        lines = [
            f"Generate a complete travel itinerary with the following parameters:",
            f"- Origin: {p.get('origin', 'Not specified')}",
            f"- Destination: {p.get('destination', 'Not specified')}",
            f"- Duration: {p.get('duration_days', 'Not specified')} days",
            f"- Travel Persona: {p.get('persona', 'balanced')}",
            f"- Group Size: {p.get('group_size', 1)} person(s)",
            f"- Total Budget: {p.get('budget_currency', '₹')}{p.get('budget_total', 'flexible')}",
            f"- Special Preferences: {p.get('preferences', 'None')}",
            f"- Constraints / Accessibility: {p.get('constraints', 'None')}",
            f"- Optimisation Mode: {p.get('optimisation_mode', 'balanced')}",
        ]
        if p.get("travel_dates"):
            lines.append(f"- Travel Dates: {p['travel_dates']}")
        lines.append(
            "\nProduce the full itinerary matrix, feasibility score, comfort weights, "
            "packing index, contingency plans, cultural notes, and budget summary "
            "as specified in your output format guidelines."
        )
        return "\n".join(lines)


# ── Singleton instance imported by blueprints ──────────────────────────────
travel_agent = TravelAgent()
