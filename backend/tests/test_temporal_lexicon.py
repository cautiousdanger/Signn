"""Smoke tests for temporal ASL/ISL train + infer readiness."""

from __future__ import annotations

from pathlib import Path

from app.ml.lexicon_runtime import get_lexicon_status
from app.ml.temporal.infer import model_ready, pool_landmark_buffer


def test_lexicon_status_reports_ready_when_artifacts_present() -> None:
    status = get_lexicon_status()
    assert status["aac_ready"] is True
    # Artifacts may exist after local training in this workspace.
    asl_dir = Path(__file__).resolve().parents[1] / "app" / "ml" / "temporal" / "artifacts" / "asl_msasl100"
    if (asl_dir / "model.json").is_file() or (asl_dir / "model.onnx").is_file():
        assert status["asl_ready"] is True
        assert model_ready("asl") is True


def test_pool_landmark_buffer_needs_enough_frames() -> None:
    assert pool_landmark_buffer([]) is None
    frame = {
        "wrist": {"x": 0.5, "y": 0.5, "z": 0.0},
        "middle_mcp": {"x": 0.5, "y": 0.4, "z": 0.0},
        "thumb_tip": {"x": 0.45, "y": 0.35, "z": 0.0},
        "index_tip": {"x": 0.48, "y": 0.3, "z": 0.0},
        "middle_tip": {"x": 0.5, "y": 0.28, "z": 0.0},
        "ring_tip": {"x": 0.52, "y": 0.3, "z": 0.0},
        "pinky_tip": {"x": 0.54, "y": 0.32, "z": 0.0},
        "thumb_mcp": {"x": 0.46, "y": 0.42, "z": 0.0},
        "index_mcp": {"x": 0.48, "y": 0.4, "z": 0.0},
        "ring_mcp": {"x": 0.52, "y": 0.4, "z": 0.0},
        "pinky_mcp": {"x": 0.54, "y": 0.41, "z": 0.0},
    }
    pooled = pool_landmark_buffer([frame] * 8)
    assert pooled is not None
    assert pooled.shape == (30,)
