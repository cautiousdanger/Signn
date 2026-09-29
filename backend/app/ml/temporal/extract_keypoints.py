"""Extract MediaPipe Hands keypoints from dataset videos → .npz sequences.

Uses MediaPipe Tasks HandLandmarker (mp 1.x). Requires backend/.venv312.

Usage (from backend/):
  ..\\.venv312\\Scripts\\python.exe -m app.ml.temporal.extract_keypoints --dataset msasl100
  ..\\.venv312\\Scripts\\python.exe -m app.ml.temporal.extract_keypoints --dataset include50
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

ROOT = Path(__file__).resolve().parents[3]
DATASETS = ROOT.parent / "datasets"
KEYPOINTS = Path(__file__).resolve().parent / "keypoints"
MODEL_PATH = Path(__file__).resolve().parent / "models" / "hand_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)

_MP_TO_KEY = {
    0: "wrist",
    2: "thumb_mcp",
    3: "thumb_ip",
    4: "thumb_tip",
    5: "index_mcp",
    6: "index_pip",
    8: "index_tip",
    9: "middle_mcp",
    10: "middle_pip",
    12: "middle_tip",
    13: "ring_mcp",
    14: "ring_pip",
    16: "ring_tip",
    17: "pinky_mcp",
    18: "pinky_pip",
    20: "pinky_tip",
}

HAND_TIP_KEYS = (
    "thumb_tip",
    "index_tip",
    "middle_tip",
    "ring_tip",
    "pinky_tip",
)
HAND_MCP_KEYS = (
    "thumb_mcp",
    "index_mcp",
    "middle_mcp",
    "ring_mcp",
    "pinky_mcp",
)


def ensure_model() -> Path:
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if MODEL_PATH.is_file() and MODEL_PATH.stat().st_size > 1_000_000:
        return MODEL_PATH
    print(f"[get] hand_landmarker.task …")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print(f"[ok] {MODEL_PATH} ({MODEL_PATH.stat().st_size} bytes)")
    return MODEL_PATH


def _dist2(a: dict[str, float], b: dict[str, float]) -> float:
    return float(((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5)


def landmarks_to_features(landmarks: dict[str, dict[str, float]]) -> list[float] | None:
    wrist = landmarks.get("wrist")
    middle_mcp = landmarks.get("middle_mcp")
    if not wrist or not middle_mcp:
        return None
    scale = _dist2(wrist, middle_mcp) + 1e-6
    features: list[float] = []
    for tip_key in HAND_TIP_KEYS:
        tip = landmarks.get(tip_key)
        if not tip:
            return None
        features.append((tip["x"] - wrist["x"]) / scale)
        features.append((tip["y"] - wrist["y"]) / scale)
    for tip_key, mcp_key in zip(HAND_TIP_KEYS, HAND_MCP_KEYS, strict=True):
        tip = landmarks.get(tip_key)
        mcp = landmarks.get(mcp_key)
        if not tip or not mcp:
            return None
        features.append(_dist2(wrist, tip) / (_dist2(wrist, mcp) + 1e-6))
    return features


def hand_lms_to_dict(hand_landmarks) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for idx, key in _MP_TO_KEY.items():
        lm = hand_landmarks[idx]
        out[key] = {"x": float(lm.x), "y": float(lm.y), "z": float(lm.z)}
    return out


def create_landmarker() -> mp_vision.HandLandmarker:
    ensure_model()
    options = mp_vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=mp_vision.RunningMode.IMAGE,
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return mp_vision.HandLandmarker.create_from_options(options)


def extract_video(
    path: Path,
    landmarker: mp_vision.HandLandmarker,
    max_frames: int = 64,
) -> np.ndarray | None:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return None
    seq: list[list[float]] = []
    frame_i = 0
    try:
        while len(seq) < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            frame_i += 1
            if frame_i % 2 == 0 and frame_i > 2:
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = landmarker.detect(mp_image)
            if not result.hand_landmarks:
                continue
            best = None
            best_area = -1.0
            for hand_lms in result.hand_landmarks:
                xs = [lm.x for lm in hand_lms]
                ys = [lm.y for lm in hand_lms]
                area = (max(xs) - min(xs)) * (max(ys) - min(ys))
                if area > best_area:
                    best_area = area
                    best = hand_lms
            if best is None:
                continue
            feats = landmarks_to_features(hand_lms_to_dict(best))
            if feats is not None:
                seq.append(feats)
    finally:
        cap.release()
    if len(seq) < 4:
        return None
    return np.asarray(seq, dtype=np.float32)


def _label_from_msasl_dir(dirname: str) -> str:
    parts = dirname.split("_", 1)
    return parts[1] if len(parts) == 2 else dirname


def _label_from_include_path(video: Path, videos_root: Path) -> str:
    try:
        rel = video.relative_to(videos_root)
    except ValueError:
        return video.parent.name
    parts = rel.parts
    # INCLUDE: Adjectives/23. high/MVI_….MOV → "high"
    if len(parts) >= 2:
        raw = parts[-2]
        if ". " in raw:
            return raw.split(". ", 1)[1].strip().lower()
        return raw.strip().lower()
    return video.stem.lower()


def collect_msasl_videos() -> list[tuple[Path, str]]:
    root = DATASETS / "MS-ASL" / "videos"
    if not root.is_dir():
        return []
    items: list[tuple[Path, str]] = []
    for folder in sorted(root.iterdir()):
        if not folder.is_dir():
            continue
        label = _label_from_msasl_dir(folder.name)
        for video in sorted(folder.glob("*.mp4")):
            if video.stat().st_size > 20_000:
                items.append((video, label))
    return items


def collect_include_videos() -> list[tuple[Path, str]]:
    root = DATASETS / "INCLUDE" / "videos"
    if not root.is_dir():
        return []
    items: list[tuple[Path, str]] = []
    patterns = ("*.mp4", "*.MOV", "*.mov", "*.avi", "*.mkv")
    seen: set[Path] = set()
    for pattern in patterns:
        for video in sorted(root.rglob(pattern)):
            if video in seen or video.stat().st_size < 20_000:
                continue
            seen.add(video)
            items.append((video, _label_from_include_path(video, root)))
    return items


def run(dataset: str, max_clips: int = 0) -> int:
    if dataset == "msasl100":
        clips = collect_msasl_videos()
        out_dir = KEYPOINTS / "asl_msasl100"
    else:
        clips = collect_include_videos()
        out_dir = KEYPOINTS / "isl_include50"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not clips:
        print(f"[error] no videos found for {dataset}")
        return 1

    landmarker = create_landmarker()
    ok = 0
    fail = 0
    labels_seen: dict[str, int] = {}
    try:
        for i, (video, label) in enumerate(clips):
            if max_clips and i >= max_clips:
                break
            dest = out_dir / f"{i:05d}_{label}.npz"
            if dest.is_file():
                ok += 1
                labels_seen[label] = labels_seen.get(label, 0) + 1
                print(f"[skip] {dest.name}")
                continue
            seq = extract_video(video, landmarker)
            if seq is None:
                fail += 1
                print(f"[fail] {video.name} label={label}")
                continue
            np.savez_compressed(dest, x=seq, label=np.asarray(label))
            ok += 1
            labels_seen[label] = labels_seen.get(label, 0) + 1
            print(f"[ok] {dest.name} T={seq.shape[0]}")
    finally:
        landmarker.close()

    meta = {
        "dataset": dataset,
        "ok": ok,
        "fail": fail,
        "labels": labels_seen,
        "out_dir": str(out_dir),
    }
    (out_dir / "extract_status.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    print(f"[done] ok={ok} fail={fail} classes={len(labels_seen)}")
    return 0 if ok >= 2 else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=("msasl100", "include50"), required=True)
    parser.add_argument("--max-clips", type=int, default=0)
    args = parser.parse_args()
    return run(args.dataset, max_clips=args.max_clips)


if __name__ == "__main__":
    sys.exit(main())
