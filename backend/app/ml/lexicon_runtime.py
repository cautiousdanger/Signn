"""ASL / ISL lexicon model readiness (ONNX or JSON Softmax artifacts)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

TEMPORAL_DIR = Path(__file__).resolve().parent / "temporal" / "artifacts"


def _model_ready(name: str) -> bool:
    folder = TEMPORAL_DIR / name
    labels = folder / "label_map.json"
    if not labels.is_file():
        return False
    # Ready when we have a trained weight file (ONNX preferred, JSON ok).
    if (folder / "model.onnx").is_file():
        return True
    if (folder / "model.json").is_file():
        return True
    return False


def get_lexicon_status() -> dict[str, Any]:
    asl_ready = _model_ready("asl_msasl100")
    isl_ready = _model_ready("isl_include50")
    parts = ["AAC live"]
    parts.append("ASL ready" if asl_ready else "ASL training pending")
    parts.append("ISL ready" if isl_ready else "ISL training pending")
    return {
        "aac_ready": True,
        "asl_ready": asl_ready,
        "isl_ready": isl_ready,
        "artifacts_dir": str(TEMPORAL_DIR),
        "note": " | ".join(parts),
    }
