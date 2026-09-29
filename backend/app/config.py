"""App-level configuration. Switch COACHING_PROVIDER to "bedrock" later."""

from __future__ import annotations

import os
from pathlib import Path

# Load backend/.env if present (does nothing when the file or package is missing).
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
except ImportError:
    pass

# Active coaching backend. Change to "bedrock" when AWS credentials are ready.
COACHING_PROVIDER = os.environ.get("COACHING_PROVIDER", "gemini")  # change to "bedrock" later

# Fallback shown if the live provider errors (bad key, rate limit, network).
COACHING_FALLBACK_TEXT = "Adjust your arm position and try again."

# Gemini model id used by gemini_provider.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

# Bedrock defaults for the stub provider (override via env when wiring AWS).
BEDROCK_REGION = os.environ.get("AWS_REGION") or os.environ.get(
    "AWS_DEFAULT_REGION", "us-east-1"
)
BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0"
)

# Local / LAN Ollama (OpenAI-compatible) — sentence polish + conversational fallback.
_raw_ollama = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1/").strip()
OLLAMA_BASE_URL = _raw_ollama.rstrip("/") + "/" if _raw_ollama else ""
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:latest")
OLLAMA_TIMEOUT_SECONDS = float(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "45"))

# ElevenLabs — primary conversational AI (Agents) + assistant TTS.
# API key must stay backend-only. Never expose to the browser.
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()
ELEVENLABS_BASE_URL = os.environ.get(
    "ELEVENLABS_BASE_URL", "https://api.elevenlabs.io"
).strip().rstrip("/")
ELEVENLABS_TTS_MODEL = os.environ.get(
    "ELEVENLABS_TTS_MODEL", "eleven_flash_v2_5"
).strip()
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "").strip()
# Optional: reuse a pre-created text-only ConvAI agent. If empty, one is created
# lazily on first reply and cached in-process.
ELEVENLABS_AGENT_ID = os.environ.get("ELEVENLABS_AGENT_ID", "").strip()
ELEVENLABS_TIMEOUT_SECONDS = float(
    os.environ.get("ELEVENLABS_TIMEOUT_SECONDS", "45")
)
