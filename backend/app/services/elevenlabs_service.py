"""ElevenLabs conversational Agents + TTS (backend-only API key).

Uses the official REST + WebSocket Agents protocol (xi-api-key), not a
browser-exposed key. The Python SDK is intentionally avoided here because it
fails to install on this Windows machine (path-length limits); the HTTP/WS
contracts below match ElevenLabs public docs.
"""

from __future__ import annotations

import asyncio
import json
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import websockets
from websockets.exceptions import WebSocketException

from app.config import (
    ELEVENLABS_AGENT_ID,
    ELEVENLABS_API_KEY,
    ELEVENLABS_BASE_URL,
    ELEVENLABS_TIMEOUT_SECONDS,
    ELEVENLABS_TTS_MODEL,
    ELEVENLABS_VOICE_ID,
)

FALLBACK_REPLY = "I heard you. Please sign that again."
MAX_HISTORY_TURNS = 8

_AAC_SYSTEM_PROMPT = (
    "You are an AAC conversational assistant for people who communicate with "
    "sign language. The user message may include recognized sign tokens and a "
    "reconstructed meaning sentence. Infer natural intent from those tokens "
    "and the sentence, then reply conversationally in English (usually 1–2 "
    "short sentences). Do not merely rewrite or repeat the user's sentence. "
    "Do not claim to see or hear anything that was not provided. "
    "Do not invent facts, people, places, actions, or context beyond what the "
    "tokens/sentence support. Ask a short clarification when meaning is unclear. "
    "No quotes, no markdown, no role labels."
)

_POLISH_SYSTEM_PROMPT = (
    "You turn signed AAC / ASL / ISL gloss words into ONE natural spoken "
    "English sentence. Keep the same meaning. Include every signed idea. "
    "You may reorder words into natural English. "
    "Do not invent people, places, or new actions. "
    "Do not ask questions. Do not reply as a chatbot. "
    "Output ONLY the spoken sentence — no quotes, no markdown, no explanation.\n"
    "Examples:\n"
    "Signed: Please, Want, Help → Please, I want help.\n"
    "Signed: Hello, You → Hello, how are you.\n"
    "Signed: Eat, Want → I want to eat.\n"
    "Signed: Strong, Clean → It is strong and clean."
)

_agent_id_lock = threading.Lock()
_cached_agent_id: str | None = None
_polish_agent_id_lock = threading.Lock()
_cached_polish_agent_id: str | None = None


def _normalize_text(text: str) -> str:
    cleaned = text.strip().strip('"').strip("'")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _sanitize_reply(text: str) -> str | None:
    cleaned = _normalize_text(text)
    if not cleaned:
        return None
    if len(cleaned) > 280 or "\n" in cleaned:
        first = cleaned.split("\n", 1)[0].strip()
        if not first:
            return None
        cleaned = first[:280].rstrip()
    if cleaned[-1] not in ".!?":
        cleaned = f"{cleaned}."
    return cleaned


def _normalize_history(history: list[Any] | None) -> list[dict[str, str]]:
    if not history:
        return []
    cleaned: list[dict[str, str]] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip().lower()
        content = _normalize_text(str(item.get("content") or ""))
        if role not in ("user", "assistant") or not content:
            continue
        cleaned.append({"role": role, "content": content})
    if len(cleaned) > MAX_HISTORY_TURNS:
        cleaned = cleaned[-MAX_HISTORY_TURNS:]
    return cleaned


def _api_headers(*, json_body: bool = True) -> dict[str, str]:
    headers = {"xi-api-key": ELEVENLABS_API_KEY}
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


def _api_configured() -> bool:
    return bool(ELEVENLABS_API_KEY)


def _safe_http_detail(err: BaseException) -> str:
    if isinstance(err, urllib.error.HTTPError):
        status = f"http_{err.code}"
        try:
            raw = err.read().decode("utf-8", errors="replace")
            data = json.loads(raw) if raw.strip() else {}
            detail = data.get("detail") if isinstance(data, dict) else None
            if isinstance(detail, dict):
                code = str(detail.get("code") or detail.get("status") or "").strip()
                # Keep detail short and non-sensitive (no key material).
                if code:
                    return f"{status}:{code}"
                msg = str(detail.get("message") or "").strip().lower()
                if "permission" in msg or "missing" in msg:
                    return f"{status}:missing_permissions"
            elif isinstance(detail, str) and detail:
                compact = detail.strip().replace("\n", " ")[:80]
                return f"{status}:{compact}"
        except Exception:  # noqa: BLE001
            pass
        return status
    return type(err).__name__


def _http_json(
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    base = ELEVENLABS_BASE_URL.rstrip("/")
    url = f"{base}{path}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers=_api_headers(json_body=payload is not None),
        method=method,
    )
    with urllib.request.urlopen(
        request, timeout=timeout or ELEVENLABS_TIMEOUT_SECONDS
    ) as response:
        raw = response.read().decode("utf-8")
    if not raw.strip():
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("unexpected_elevenlabs_payload")
    return data


def _build_user_turn(
    sentence: str,
    *,
    tokens: list[str] | None,
    history: list[dict[str, str]],
    locale: str | None,
) -> str:
    words = [str(token).strip() for token in (tokens or []) if str(token).strip()]
    parts = [
        "Recognized sign tokens (raw AAC): "
        + (", ".join(words) if words else "(none)"),
        f"Reconstructed user meaning: {sentence}",
    ]
    if history:
        hist_lines = []
        for turn in history:
            label = "User" if turn["role"] == "user" else "Assistant"
            hist_lines.append(f"{label}: {turn['content']}")
        parts.append("Recent conversation:\n" + "\n".join(hist_lines))
    locale_hint = (locale or "").strip() or "en"
    parts.append(f"Locale hint: {locale_hint}.")
    parts.append(
        "Respond as the assistant only. Answer the user's meaning; "
        "do not rewrite their sentence."
    )
    return "\n".join(parts)


def _create_text_agent(
    *,
    name: str = "Gesture AAC Assistant",
    system_prompt: str | None = None,
) -> str:
    """Create a text-only ConvAI agent via the official Agents create API."""
    prompt = system_prompt or _AAC_SYSTEM_PROMPT
    payload: dict[str, Any] = {
        "name": name,
        "conversation_config": {
            "agent": {
                "prompt": {
                    "prompt": prompt,
                    "llm": "gemini-2.0-flash",
                },
                "first_message": "",
                "language": "en",
            },
            "conversation": {"text_only": True},
        },
    }
    # Voice is optional for text_only agents; include only when configured.
    if ELEVENLABS_VOICE_ID:
        payload["conversation_config"]["tts"] = {"voice_id": ELEVENLABS_VOICE_ID}

    data = _http_json("POST", "/v1/convai/agents/create", payload=payload)
    agent_id = str(data.get("agent_id") or "").strip()
    if not agent_id:
        raise RuntimeError("agent_create_missing_id")
    print(f"[elevenlabs] created text agent id={agent_id[:12]}… name={name}")
    return agent_id


def resolve_agent_id() -> str:
    """Return configured or lazily created reply agent id (process-cached)."""
    global _cached_agent_id
    if ELEVENLABS_AGENT_ID:
        return ELEVENLABS_AGENT_ID
    with _agent_id_lock:
        if _cached_agent_id:
            return _cached_agent_id
        _cached_agent_id = _create_text_agent()
        return _cached_agent_id


def resolve_polish_agent_id() -> str:
    """Lazily create a sentence-polish agent (separate from chat reply)."""
    global _cached_polish_agent_id
    with _polish_agent_id_lock:
        if _cached_polish_agent_id:
            return _cached_polish_agent_id
        _cached_polish_agent_id = _create_text_agent(
            name="Gesture Sentence Polish",
            system_prompt=_POLISH_SYSTEM_PROMPT,
        )
        return _cached_polish_agent_id


def _get_signed_conversation_url(agent_id: str) -> str:
    query = urllib.parse.urlencode({"agent_id": agent_id})
    data = _http_json(
        "GET",
        f"/v1/convai/conversation/get-signed-url?{query}",
        payload=None,
    )
    signed = str(data.get("signed_url") or "").strip()
    if not signed:
        raise RuntimeError("missing_signed_url")
    return signed


async def _ask_agent_once(
    user_text: str,
    agent_id: str,
    *,
    system_prompt: str | None = None,
) -> str:
    """One-shot text chat over the official ConvAI WebSocket protocol."""
    prompt = system_prompt or _AAC_SYSTEM_PROMPT
    signed_url = await asyncio.to_thread(_get_signed_conversation_url, agent_id)
    reply_text = ""
    timeout = ELEVENLABS_TIMEOUT_SECONDS

    async with websockets.connect(
        signed_url,
        open_timeout=timeout,
        close_timeout=5,
        max_size=4 * 1024 * 1024,
    ) as ws:
        initiation = {
            "type": "conversation_initiation_client_data",
            "conversation_config_override": {
                "agent": {
                    "prompt": {"prompt": prompt},
                    "first_message": "",
                    "language": "en",
                },
                "conversation": {"text_only": True},
            },
        }
        await ws.send(json.dumps(initiation))
        await ws.send(json.dumps({"type": "user_message", "text": user_text}))

        deadline = asyncio.get_running_loop().time() + timeout
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise TimeoutError("elevenlabs_agent_timeout")
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            etype = event.get("type")
            if etype == "ping":
                ping = event.get("ping_event") or {}
                event_id = ping.get("event_id")
                if event_id is not None:
                    await ws.send(
                        json.dumps({"type": "pong", "event_id": event_id})
                    )
                continue
            if etype == "agent_response":
                payload = event.get("agent_response_event") or {}
                reply_text = str(payload.get("agent_response") or "")
                break
            if etype == "agent_chat_response_part":
                part = event.get("text_response_part") or {}
                if part.get("type") == "delta":
                    reply_text += str(part.get("text") or "")
                elif part.get("type") == "stop" and reply_text:
                    break

    cleaned = _sanitize_reply(reply_text)
    if not cleaned:
        raise RuntimeError("empty_or_invalid_agent_reply")
    return cleaned


def _run_coro_sync(coro: Any) -> Any:
    """Run an async coroutine from sync FastAPI handlers safely."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, Any] = {}
    error: dict[str, BaseException] = {}

    def _target() -> None:
        try:
            result["value"] = asyncio.run(coro)
        except BaseException as err:  # noqa: BLE001
            error["err"] = err

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join(timeout=ELEVENLABS_TIMEOUT_SECONDS + 5)
    if thread.is_alive():
        raise TimeoutError("elevenlabs_agent_thread_timeout")
    if "err" in error:
        raise error["err"]
    return result.get("value")


def generate_elevenlabs_reply(
    sentence: str,
    *,
    tokens: list[str] | None = None,
    history: list[Any] | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    """Return {reply, source: 'elevenlabs'|'fallback', detail?}."""
    user_sentence = _normalize_text(sentence or "")
    if not user_sentence:
        return {
            "reply": FALLBACK_REPLY,
            "source": "fallback",
            "detail": "empty_sentence",
        }
    if not _api_configured():
        return {
            "reply": FALLBACK_REPLY,
            "source": "fallback",
            "detail": "ELEVENLABS_API_KEY not set",
        }

    prior = _normalize_history(history)
    user_turn = _build_user_turn(
        user_sentence, tokens=tokens, history=prior, locale=locale
    )
    try:
        agent_id = resolve_agent_id()
        reply = _run_coro_sync(_ask_agent_once(user_turn, agent_id))
        return {"reply": reply, "source": "elevenlabs"}
    except urllib.error.HTTPError as err:
        detail = _safe_http_detail(err)
        print(f"[elevenlabs] reply failed: {detail}")
        return {"reply": FALLBACK_REPLY, "source": "fallback", "detail": detail}
    except (TimeoutError, WebSocketException, OSError, RuntimeError, ValueError) as err:
        detail = type(err).__name__
        print(f"[elevenlabs] reply failed: {detail}")
        return {"reply": FALLBACK_REPLY, "source": "fallback", "detail": detail}
    except Exception as err:  # noqa: BLE001
        detail = type(err).__name__
        print(f"[elevenlabs] reply failed: {detail}")
        return {"reply": FALLBACK_REPLY, "source": "fallback", "detail": detail}


def polish_sentence_with_elevenlabs(
    tokens: list[str],
    *,
    fallback: str,
) -> dict[str, Any]:
    """Rewrite signed glosses into one spoken sentence via a polish agent.

    Return {sentence, source: 'elevenlabs'|'fallback', detail?}.
    """
    words = [str(token).strip() for token in tokens if str(token).strip()]
    template = _sanitize_reply(fallback or "") or (fallback or "").strip()
    if not words:
        return {"sentence": "", "source": "fallback", "detail": "empty"}
    if not template:
        template = _sanitize_reply(", ".join(words)) or ", ".join(words)
    if not _api_configured():
        return {
            "sentence": template,
            "source": "fallback",
            "detail": "ELEVENLABS_API_KEY not set",
        }

    user_turn = (
        "Signed words: "
        + ", ".join(words)
        + ".\n"
        "Draft sentence (prefer if already good): "
        + template
        + "\n"
        "Reply with ONE natural spoken English sentence only."
    )
    try:
        agent_id = resolve_polish_agent_id()
        sentence = _run_coro_sync(
            _ask_agent_once(
                user_turn,
                agent_id,
                system_prompt=_POLISH_SYSTEM_PROMPT,
            )
        )
        return {"sentence": sentence, "source": "elevenlabs"}
    except urllib.error.HTTPError as err:
        detail = _safe_http_detail(err)
        print(f"[elevenlabs] polish failed: {detail}")
        return {"sentence": template, "source": "fallback", "detail": detail}
    except (TimeoutError, WebSocketException, OSError, RuntimeError, ValueError) as err:
        detail = type(err).__name__
        print(f"[elevenlabs] polish failed: {detail}")
        return {"sentence": template, "source": "fallback", "detail": detail}
    except Exception as err:  # noqa: BLE001
        detail = type(err).__name__
        print(f"[elevenlabs] polish failed: {detail}")
        return {"sentence": template, "source": "fallback", "detail": detail}


def synthesize_speech(text: str) -> dict[str, Any]:
    """Return {ok, audio_bytes?, content_type?, detail?} for TTS.

    Never raises with secrets. Callers must not log audio content as text.
    """
    spoken = _normalize_text(text or "")
    if not spoken:
        return {"ok": False, "detail": "empty_text"}
    if not _api_configured():
        return {"ok": False, "detail": "ELEVENLABS_API_KEY not set"}
    if not ELEVENLABS_VOICE_ID:
        return {"ok": False, "detail": "ELEVENLABS_VOICE_ID not configured"}

    voice_id = urllib.parse.quote(ELEVENLABS_VOICE_ID, safe="")
    query = urllib.parse.urlencode({"output_format": "mp3_44100_128"})
    url = (
        f"{ELEVENLABS_BASE_URL.rstrip('/')}/v1/text-to-speech/{voice_id}?{query}"
    )
    payload = {
        "text": spoken,
        "model_id": ELEVENLABS_TTS_MODEL or "eleven_flash_v2_5",
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers=_api_headers(json_body=True),
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request, timeout=ELEVENLABS_TIMEOUT_SECONDS
        ) as response:
            audio = response.read()
            content_type = response.headers.get("Content-Type") or "audio/mpeg"
        if not audio:
            return {"ok": False, "detail": "empty_audio"}
        return {
            "ok": True,
            "audio_bytes": audio,
            "content_type": content_type,
        }
    except urllib.error.HTTPError as err:
        detail = _safe_http_detail(err)
        print(f"[elevenlabs] tts failed: {detail}")
        return {"ok": False, "detail": detail}
    except Exception as err:  # noqa: BLE001
        detail = type(err).__name__
        print(f"[elevenlabs] tts failed: {detail}")
        return {"ok": False, "detail": detail}
