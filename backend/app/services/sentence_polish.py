"""Polish signed gloss tokens into a natural spoken sentence.

Primary: ElevenLabs polish agent.
Fallback: client template (composeSignSentence) — never blocks Speak.
Optional last resort: Ollama if ElevenLabs fails and Ollama is configured.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS
from app.services import elevenlabs_service as eleven

# Meaning → stems that must still appear in a polished sentence.
_TOKEN_STEMS: dict[str, tuple[str, ...]] = {
    "Hello": ("hello",),
    "Yes": ("yes",),
    "No": ("no",),
    "Help": ("help",),
    "Thank you": ("thank",),
    "Goodbye": ("goodbye", "bye"),
    "Please": ("please",),
    "You": ("you",),
    "Want": ("want",),
    "Okay": ("okay", "ok"),
    "Understood": ("understand", "understood"),
    "I love you": ("love",),
    "I": ("i",),
    "Food": ("food",),
    "Water": ("water",),
    "Direction": ("direction", "directions"),
    "Doctor": ("doctor",),
    "Sick": ("sick",),
    "Happy": ("happy",),
    "Today": ("today",),
    "Tomorrow": ("tomorrow",),
}


def _chat_url() -> str:
    base = (OLLAMA_BASE_URL or "").rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def _normalize_sentence(text: str) -> str:
    cleaned = text.strip().strip('"').strip("'")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _sanitize(text: str) -> str | None:
    cleaned = _normalize_sentence(text)
    if not cleaned:
        return None
    if len(cleaned) > 180 or "\n" in cleaned:
        first = cleaned.split("\n", 1)[0].strip()
        if not first or len(first) > 180:
            return None
        cleaned = first
    if cleaned[-1] not in ".!?":
        cleaned = f"{cleaned}."
    return cleaned


def _required_stems(words: list[str]) -> list[str]:
    stems: list[str] = []
    for word in words:
        for stem in _TOKEN_STEMS.get(word, ()):
            if stem not in stems:
                stems.append(stem)
        if word not in _TOKEN_STEMS:
            compact = re.sub(r"[^a-z]+", "", word.lower())
            if compact and compact not in stems:
                stems.append(compact)
    return stems


def _has_stem(haystack: str, stem: str) -> bool:
    return bool(re.search(rf"\b{re.escape(stem)}\b", haystack, flags=re.IGNORECASE))


def _template_already_good(words: list[str], template: str) -> bool:
    """Skip the LLM only for a single signed word (nothing to compose)."""
    if not template:
        return False
    return len(words) <= 1


def _reply_keeps_meaning(words: list[str], template: str, reply: str) -> bool:
    """Reject inventing/dropping meaning relative to signed words + draft."""
    stems = _required_stems(words)
    if stems and not all(_has_stem(reply, stem) for stem in stems):
        return False

    if template and len(reply) > max(len(template) + 40, int(len(template) * 1.8) + 12):
        return False

    banned = (
        "doctor",
        "hospital",
        "police",
        "teacher",
        "school",
        "friend",
        "mom",
        "dad",
        "mother",
        "father",
        "assist me",
        "can you",
        "could you",
    )
    reply_l = reply.lower()
    template_l = template.lower()
    for phrase in banned:
        if phrase in reply_l and phrase not in template_l:
            if not any(phrase.startswith(stem) or stem in phrase for stem in stems):
                return False
    return True


def _polish_with_ollama(words: list[str], template: str) -> dict[str, Any] | None:
    if not OLLAMA_BASE_URL:
        return None
    user_prompt = (
        "Signed words (already sorted toward natural English order): "
        + ", ".join(words)
        + ".\n"
        "Draft sentence (use this if unsure): "
        + template
        + "\n"
        "Reply with ONE natural spoken sentence only. "
        "Keep natural English order. "
        "Prefer the draft when it already uses the signed words."
    )
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You turn signed words into ONE natural spoken English sentence. "
                    "Keep the same meaning. Include every signed idea. "
                    "Do not invent people, places, or new actions. "
                    "No quotes, no markdown, no explanation."
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 60,
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
        sentence = _sanitize(str(content or ""))
        if not sentence:
            return None
        if not _reply_keeps_meaning(words, template, sentence):
            print(f"[ollama] polish rejected inventing/dropping: {sentence!r}")
            return None
        return {"sentence": sentence, "source": "ollama"}
    except Exception as err:  # noqa: BLE001
        print(f"[ollama] polish failed: {type(err).__name__}")
        return None


def polish_sentence_with_ollama(
    tokens: list[str],
    *,
    fallback: str,
) -> dict[str, Any]:
    """Compat alias — prefer polish_sentence()."""
    return polish_sentence(tokens, fallback=fallback)


def polish_sentence(
    tokens: list[str],
    *,
    fallback: str,
) -> dict[str, Any]:
    """ElevenLabs polish → Ollama → template fallback.

    Return {sentence, source: 'elevenlabs'|'ollama'|'template'|'fallback', detail?}.
    """
    template = _sanitize(fallback or "") or (fallback or "").strip()
    words = [str(token).strip() for token in tokens if str(token).strip()]
    if not words:
        return {"sentence": "", "source": "fallback", "detail": "empty"}

    if not template:
        template = _sanitize(", ".join(words)) or ", ".join(words)

    if _template_already_good(words, template):
        return {
            "sentence": template if template.endswith((".", "!", "?")) else f"{template}.",
            "source": "template",
            "detail": "single_word",
        }

    # 1) ElevenLabs polish agent
    eleven_result = eleven.polish_sentence_with_elevenlabs(words, fallback=template)
    if eleven_result.get("source") == "elevenlabs":
        sentence = _sanitize(str(eleven_result.get("sentence") or ""))
        if sentence and _reply_keeps_meaning(words, template, sentence):
            return {"sentence": sentence, "source": "elevenlabs"}
        print(
            f"[polish] elevenlabs rejected or empty: "
            f"{eleven_result.get('sentence')!r}"
        )

    eleven_detail = eleven_result.get("detail")

    # 2) Ollama (optional local backup)
    ollama_result = _polish_with_ollama(words, template)
    if ollama_result:
        if eleven_detail:
            ollama_result = {
                **ollama_result,
                "detail": f"elevenlabs:{eleven_detail}; used_ollama",
            }
        return ollama_result

    # 3) Template / client fallback — Speak always has a sentence
    detail_parts = []
    if eleven_detail:
        detail_parts.append(f"elevenlabs:{eleven_detail}")
    return {
        "sentence": template if template.endswith((".", "!", "?")) else f"{template}.",
        "source": "fallback",
        "detail": "; ".join(detail_parts) if detail_parts else "template_fallback",
    }
