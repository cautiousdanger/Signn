"""Unit tests for AAC conversation reply (ElevenLabs primary).

Run from the backend directory:
  python -m unittest tests.test_conversation_reply
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from app.services import conversation_reply as cr
from app.services import elevenlabs_service as eleven
from app.services import ollama_reply as ollama


class ConversationReplyTests(unittest.TestCase):
    def test_empty_sentence_returns_fallback(self) -> None:
        result = cr.generate_conversation_reply("")
        self.assertEqual(result["source"], "fallback")
        self.assertEqual(result["reply"], cr.FALLBACK_REPLY)
        self.assertIn("empty_sentence", str(result.get("detail")))

    def test_elevenlabs_success_want_help(self) -> None:
        with patch.object(
            eleven,
            "generate_elevenlabs_reply",
            return_value={
                "reply": "Of course. What do you need help with?",
                "source": "elevenlabs",
            },
        ):
            result = cr.generate_conversation_reply(
                "I want help.",
                tokens=["Want", "Help"],
                history=[],
            )
        self.assertEqual(result["source"], "elevenlabs")
        self.assertEqual(result["reply"], "Of course. What do you need help with?")

    def test_history_is_capped(self) -> None:
        history = [
            {
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"msg {i}",
            }
            for i in range(20)
        ]
        cleaned = cr._normalize_history(history)
        self.assertEqual(len(cleaned), cr.MAX_HISTORY_TURNS)
        self.assertEqual(cleaned[0]["content"], "msg 12")

    def test_elevenlabs_failure_falls_back_to_ollama(self) -> None:
        with patch.object(
            eleven,
            "generate_elevenlabs_reply",
            return_value={
                "reply": cr.FALLBACK_REPLY,
                "source": "fallback",
                "detail": "http_503",
            },
        ):
            with patch.object(
                ollama,
                "generate_ollama_reply",
                return_value={
                    "reply": "Sure. How can I help?",
                    "source": "ollama",
                },
            ):
                result = cr.generate_conversation_reply(
                    "I want help.",
                    tokens=["Want", "Help"],
                )
        self.assertEqual(result["source"], "ollama")
        self.assertEqual(result["reply"], "Sure. How can I help?")
        self.assertIn("elevenlabs:http_503", str(result.get("detail")))

    def test_both_providers_unavailable_local_fallback(self) -> None:
        with patch.object(
            eleven,
            "generate_elevenlabs_reply",
            return_value={
                "reply": cr.FALLBACK_REPLY,
                "source": "fallback",
                "detail": "ELEVENLABS_API_KEY not set",
            },
        ):
            with patch.object(
                ollama,
                "generate_ollama_reply",
                return_value={
                    "reply": cr.FALLBACK_REPLY,
                    "source": "fallback",
                    "detail": "OLLAMA_BASE_URL not set",
                },
            ):
                result = cr.generate_conversation_reply("Hello.")
        self.assertEqual(result["source"], "fallback")
        self.assertEqual(result["reply"], cr.FALLBACK_REPLY)
        self.assertIn("elevenlabs:", str(result.get("detail")))
        self.assertIn("ollama:", str(result.get("detail")))

    def test_ollama_success_direct(self) -> None:
        fake_body = {
            "choices": [
                {"message": {"content": "Sure. What do you need help with?"}}
            ]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(fake_body).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = False

        with patch.object(ollama, "OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1/"):
            with patch.object(
                ollama.urllib.request, "urlopen", return_value=mock_response
            ):
                result = ollama.generate_ollama_reply(
                    "I want help.",
                    tokens=["Want", "Help"],
                    history=[
                        {"role": "user", "content": "Hello, how are you?"},
                        {
                            "role": "assistant",
                            "content": "Hello. I am here to help.",
                        },
                    ],
                )
        self.assertEqual(result["source"], "ollama")
        self.assertEqual(result["reply"], "Sure. What do you need help with?")


class ElevenLabsServiceTests(unittest.TestCase):
    def test_missing_api_key_returns_fallback(self) -> None:
        with patch.object(eleven, "ELEVENLABS_API_KEY", ""):
            result = eleven.generate_elevenlabs_reply("I want help.")
        self.assertEqual(result["source"], "fallback")
        self.assertIn("ELEVENLABS_API_KEY", str(result.get("detail")))

    def test_tts_requires_voice_id(self) -> None:
        with patch.object(eleven, "ELEVENLABS_API_KEY", "test-key"):
            with patch.object(eleven, "ELEVENLABS_VOICE_ID", ""):
                result = eleven.synthesize_speech("Hello there.")
        self.assertFalse(result.get("ok"))
        self.assertEqual(result.get("detail"), "ELEVENLABS_VOICE_ID not configured")

    def test_tts_success_mocked(self) -> None:
        mock_response = MagicMock()
        mock_response.read.return_value = b"FAKEMP3"
        mock_response.headers = {"Content-Type": "audio/mpeg"}
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = False

        with patch.object(eleven, "ELEVENLABS_API_KEY", "test-key"):
            with patch.object(eleven, "ELEVENLABS_VOICE_ID", "voice123"):
                with patch.object(
                    eleven.urllib.request, "urlopen", return_value=mock_response
                ):
                    result = eleven.synthesize_speech("Of course.")
        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("audio_bytes"), b"FAKEMP3")

    def test_tts_http_error_does_not_raise(self) -> None:
        with patch.object(eleven, "ELEVENLABS_API_KEY", "test-key"):
            with patch.object(eleven, "ELEVENLABS_VOICE_ID", "voice123"):
                with patch.object(
                    eleven.urllib.request,
                    "urlopen",
                    side_effect=eleven.urllib.error.HTTPError(
                        url="http://x",
                        code=401,
                        msg="unauthorized",
                        hdrs=None,
                        fp=None,
                    ),
                ):
                    result = eleven.synthesize_speech("Hello.")
        self.assertFalse(result.get("ok"))
        self.assertEqual(result.get("detail"), "http_401")


class ConversationReplyRouteSmoke(unittest.TestCase):
    """Import-level smoke: request models and route exist on the app."""

    def test_route_registered(self) -> None:
        from main import app

        paths = {route.path for route in app.routes}
        self.assertIn("/ml/reply", paths)
        self.assertIn("/ml/polish-sentence", paths)
        self.assertIn("/ml/tts", paths)

    def test_reply_empty_sentence_http_422(self) -> None:
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app)
        response = client.post("/ml/reply", json={"sentence": ""})
        self.assertEqual(response.status_code, 422)

    def test_tts_failure_does_not_break_reply(self) -> None:
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app)
        with patch(
            "main.generate_conversation_reply",
            return_value={
                "reply": "Of course. What do you need help with?",
                "source": "elevenlabs",
            },
        ):
            reply_response = client.post(
                "/ml/reply",
                json={
                    "sentence": "I want help.",
                    "tokens": ["Want", "Help"],
                    "history": [],
                },
            )
        self.assertEqual(reply_response.status_code, 200)
        body = reply_response.json()
        self.assertEqual(body["source"], "elevenlabs")
        self.assertIn("help", body["reply"].lower())

        with patch(
            "main.synthesize_speech",
            return_value={"ok": False, "detail": "http_503"},
        ):
            tts_response = client.post("/ml/tts", json={"text": body["reply"]})
        self.assertEqual(tts_response.status_code, 503)
        # Reply endpoint remains independent of TTS.
        with patch(
            "main.generate_conversation_reply",
            return_value={
                "reply": "Still here.",
                "source": "fallback",
                "detail": "all_providers_unavailable",
            },
        ):
            again = client.post(
                "/ml/reply",
                json={"sentence": "I want help.", "tokens": ["Want", "Help"]},
            )
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.json()["status"], "ok")


if __name__ == "__main__":
    unittest.main()
