"""Live ASL/ISL temporal inference from landmark frame buffers."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import numpy as np

from app.ml.numpy_clf import SoftmaxClassifier
from app.scoring.engine import hand_pose_features

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
POOL_DIM = 30
MIN_FRAMES = 6
CONFIDENCE_THRESHOLD = 0.35

_lock = threading.Lock()
_models: dict[str, SoftmaxClassifier | None] = {
    "asl": None,
    "isl": None,
}
_loaded: dict[str, bool] = {"asl": False, "isl": False}


def _artifact_dir(mode: str) -> Path:
    if mode == "asl":
        return ARTIFACTS / "asl_msasl100"
    return ARTIFACTS / "isl_include50"


def model_ready(mode: str) -> bool:
    folder = _artifact_dir(mode)
    labels = folder / "label_map.json"
    has_onnx = (folder / "model.onnx").is_file()
    has_json = (folder / "model.json").is_file()
    return labels.is_file() and (has_onnx or has_json)


def _load(mode: str) -> SoftmaxClassifier | None:
    with _lock:
        if _loaded[mode]:
            return _models[mode]
        folder = _artifact_dir(mode)
        json_path = folder / "model.json"
        clf = None
        if json_path.is_file():
            try:
                bundle = json.loads(json_path.read_text(encoding="utf-8"))
                clf = SoftmaxClassifier.from_dict(bundle)
            except Exception as err:  # noqa: BLE001
                print(f"[temporal] failed to load {mode}: {err}")
                clf = None
        _models[mode] = clf
        _loaded[mode] = True
        if clf is not None:
            print(f"[temporal] loaded {mode} classes={list(clf.classes_)}")
        return clf


def reload_models() -> None:
    with _lock:
        for key in _models:
            _models[key] = None
            _loaded[key] = False


def pool_landmark_buffer(frames: list[dict[str, Any]]) -> np.ndarray | None:
    vectors: list[list[float]] = []
    for frame in frames:
        vec = hand_pose_features(frame)
        if vec is not None:
            vectors.append(vec)
    if len(vectors) < MIN_FRAMES:
        return None
    x = np.asarray(vectors, dtype=float)
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    pooled = np.concatenate([mean, std], axis=0)
    if pooled.shape[0] != POOL_DIM:
        return None
    return pooled


def predict_lexicon(
    mode: str,
    frames: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return {available, label, prob, meaning} for asl|isl."""
    empty = {
        "available": False,
        "label": None,
        "prob": None,
        "meaning": None,
        "mode": mode,
    }
    if mode not in ("asl", "isl"):
        return empty
    if not model_ready(mode):
        return empty
    clf = _load(mode)
    if clf is None:
        return empty
    pooled = pool_landmark_buffer(list(frames))
    if pooled is None:
        empty["available"] = True
        return empty
    try:
        x = pooled.reshape(1, -1)
        label = str(clf.predict(x)[0])
        probs = clf.predict_proba(x)[0]
        classes = list(clf.classes_)
        prob = float(probs[classes.index(label)]) if label in classes else float(max(probs))
    except Exception as err:  # noqa: BLE001
        print(f"[temporal] predict failed: {err}")
        empty["available"] = True
        return empty

    meaning = label.replace("_", " ").strip().title()
    return {
        "available": True,
        "label": label,
        "prob": round(prob, 4),
        "meaning": meaning,
        "mode": mode,
        "confident": prob >= CONFIDENCE_THRESHOLD,
    }


def apply_lexicon_to_sign_result(
    heuristic: dict[str, Any],
    frames: list[dict[str, Any]],
    lexicon_mode: str,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    """If ASL/ISL model is ready and confident, replace AAC heuristic label."""
    prediction = predict_lexicon(lexicon_mode, frames)
    if lexicon_mode not in ("asl", "isl"):
        return heuristic, prediction, "heuristic"
    if not prediction.get("available"):
        return heuristic, prediction, "lexicon_pending"
    if not prediction.get("confident") or not prediction.get("label"):
        return heuristic, prediction, "lexicon_fallback"

    label = str(prediction["label"])
    meaning = str(prediction.get("meaning") or label)
    # Map control words that collide with AAC clear/undo semantics carefully.
    control = {"clear", "undo", "fist"}
    if label.lower() in control:
        return heuristic, prediction, "lexicon_control_skip"

    result = dict(heuristic)
    result["gesture"] = label
    result["score"] = float(prediction.get("prob") or 0.0)
    result["correct"] = True
    result["meaning"] = meaning
    result["reason"] = None
    result["classified_as"] = label
    result["attempted_gesture"] = label
    return result, prediction, f"lexicon_{lexicon_mode}"
