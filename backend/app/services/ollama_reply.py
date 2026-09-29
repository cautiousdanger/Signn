"""Ollama conversational reply — secondary fallback after ElevenLabs.

Kept isolated so ElevenLabs stays the primary provider. Same prompt semantics
as the previous Phase-1 Ollama path.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS
from app.services.elevenlabs_service import (
    FALLBACK_REPLY,
    _normalize_history,
    _normalize_text,
    _sanitize_reply,
)

_SYSTEM = (
    "You are an AAC conversational assistant. "
    "The user's message may come from sign-language recognition, "
    "so preserve the user's intended meaning. "
    "Respond naturally and concisely in English, usually 1–2 short sentences. "
    "Do not claim to see or hear anything that was not provided. "
    "Do not invent facts, people, places, actions, or context. "
    "Do not rewrite the user's sentence; answer it. "
    "Do not provide unnecessary explanations. "
    "Ask a short clarification question when the user's meaning is unclear. "
    "No quotes, no markdown, no role labels."
)


def _chat_url() -> str:
    base = (OLLAMA_BASE_URL or "").rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def generate_ollama_reply(
    sentence: str,
    *,
    tokens: list[str] | None = None,
    history: list[Any] | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    """Return {reply, source: 'ollama'|'fallback', detail?}."""
    user_sentence = _normalize_text(sentence or "")
    if not user_sentence:
        return {
            "reply": FALLBACK_REPLY,
            "source": "fallback",
            "detail": "empty_sentence",
        }

    if not OLLAMA_BASE_URL:
        return {
            "reply": FALLBACK_REPLY,
            "source": "fallback",
            "detail": "OLLAMA_BASE_URL not set",
        }

    words = [str(token).strip() for token in (tokens or []) if str(token).strip()]
    prior = _normalize_history(history)
    locale_hint = (locale or "").strip() or "en"

    user_content_parts = [
        f"User said: {user_sentence}",
    ]
    if words:
        user_content_parts.append("Signed words: " + ", ".join(words) + ".")
    if locale_hint:
        user_content_parts.append(f"Locale hint: {locale_hint}.")
    user_content_parts.append("Respond as the assistant only.")

    messages: list[dict[str, str]] = [{"role": "system", "content": _SYSTEM}]
    messages.extend(prior)
    messages.append({"role": "user", "content": "\n".join(user_content_parts)})

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 80,
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        _chat_url(),
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=OLLAMA_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
        data = json.loads(raw)
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        reply = _sanitize_reply(str(content or ""))
        if not reply:
            return {
                "reply": FALLBACK_REPLY,
                "source": "fallback",
                "detail": "empty_or_invalid_llm_reply",
            }
        return {"reply": reply, "source": "ollama"}
    except urllib.error.HTTPError as err:
        detail = f"http_{err.code}"
        print(f"[ollama] reply failed: {detail}")
        return {"reply": FALLBACK_REPLY, "source": "fallback", "detail": detail}
    except Exception as err:  # noqa: BLE001
        detail = type(err).__name__
        print(f"[ollama] reply failed: {detail}")
        return {"reply": FALLBACK_REPLY, "source": "fallback", "detail": detail}
