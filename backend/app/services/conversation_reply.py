"""Conversational AAC reply: ElevenLabs primary, Ollama fallback, then local.

Answers the user's signed sentence. Does not rewrite or polish it.
"""

from __future__ import annotations

from typing import Any

from app.services import elevenlabs_service as eleven
from app.services import ollama_reply as ollama

FALLBACK_REPLY = eleven.FALLBACK_REPLY
MAX_HISTORY_TURNS = eleven.MAX_HISTORY_TURNS


def _normalize_history(history: list[Any] | None) -> list[dict[str, str]]:
    return eleven._normalize_history(history)


def generate_conversation_reply(
    sentence: str,
    *,
    tokens: list[str] | None = None,
    history: list[Any] | None = None,
    session_id: str | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    """Return {reply, source: 'elevenlabs'|'ollama'|'fallback', detail?}."""
    del session_id  # Reserved for later persistence.

    # 1) ElevenLabs Agents (primary)
    eleven_result = eleven.generate_elevenlabs_reply(
        sentence,
        tokens=tokens,
        history=history,
        locale=locale,
    )
    if eleven_result.get("source") == "elevenlabs":
        return eleven_result

    eleven_detail = eleven_result.get("detail")

    # 2) Ollama (secondary fallback — never silently primary when ElevenLabs works)
    ollama_result = ollama.generate_ollama_reply(
        sentence,
        tokens=tokens,
        history=history,
        locale=locale,
    )
    if ollama_result.get("source") == "ollama":
        if eleven_detail:
            ollama_result = {
                **ollama_result,
                "detail": f"elevenlabs:{eleven_detail}; used_ollama",
            }
        return ollama_result

    # 3) Local canned reply
    detail_parts = []
    if eleven_detail:
        detail_parts.append(f"elevenlabs:{eleven_detail}")
    ollama_detail = ollama_result.get("detail")
    if ollama_detail:
        detail_parts.append(f"ollama:{ollama_detail}")
    return {
        "reply": FALLBACK_REPLY,
        "source": "fallback",
        "detail": "; ".join(detail_parts) if detail_parts else "all_providers_unavailable",
    }
