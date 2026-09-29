"""Train isolated sign classifiers from extracted keypoints.

Usage (from backend/):
  .\\.venv\\Scripts\\python.exe -m app.ml.temporal.train_isolated --dataset msasl100
  .\\.venv\\Scripts\\python.exe -m app.ml.temporal.train_isolated --dataset include50

Keypoints come from extract_keypoints.py (.npz under temporal/keypoints/).
Writes model.onnx + model.json + label_map.json under temporal/artifacts/.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ml.numpy_clf import SoftmaxClassifier
from app.ml.temporal.export_onnx import export_softmax_onnx

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
KEYPOINTS = Path(__file__).resolve().parent / "keypoints"
DATASETS = ROOT.parent / "datasets"

POOL_DIM = 30  # mean(15) + std(15)
MIN_SAMPLES = 4
MIN_CLASSES = 2


def _pool_sequence(seq: np.ndarray) -> np.ndarray:
    """Collapse (T, 15) → 30-d mean+std."""
    x = np.asarray(seq, dtype=float)
    if x.ndim != 2 or x.shape[0] < 1:
        raise ValueError("bad sequence")
    mean = x.mean(axis=0)
    std = x.std(axis=0) if x.shape[0] > 1 else np.zeros_like(mean)
    return np.concatenate([mean, std], axis=0)


def _load_keypoints(folder: Path) -> tuple[np.ndarray, np.ndarray]:
    xs: list[np.ndarray] = []
    ys: list[str] = []
    for path in sorted(folder.glob("*.npz")):
        try:
            data = np.load(path, allow_pickle=True)
            seq = np.asarray(data["x"], dtype=float)
            label = str(data["label"].item() if data["label"].shape == () else data["label"])
            pooled = _pool_sequence(seq)
            if pooled.shape[0] != POOL_DIM:
                continue
            xs.append(pooled)
            ys.append(label.lower().strip())
        except Exception as err:  # noqa: BLE001
            print(f"[warn] skip {path.name}: {err}")
    if not xs:
        return np.zeros((0, POOL_DIM)), np.asarray([], dtype=object)
    return np.stack(xs, axis=0), np.asarray(ys, dtype=object)


def _stamp_pending(dataset_key: str, note: str, labels: list[str]) -> Path:
    out = ARTIFACTS / dataset_key
    out.mkdir(parents=True, exist_ok=True)
    meta = {
        "dataset": dataset_key,
        "status": "pending_data",
        "note": note,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "next_steps": [
            "Finish video download",
            "Extract keypoints: python -m app.ml.temporal.extract_keypoints",
            "Re-run this trainer",
        ],
    }
    (out / "training_status.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (out / "label_map.json").write_text(
        json.dumps({str(i): name for i, name in enumerate(labels)}, indent=2),
        encoding="utf-8",
    )
    return out


def train_from_keypoints(dataset_key: str, kp_dir: Path) -> Path:
    x, y = _load_keypoints(kp_dir)
    classes = sorted(set(y.tolist()))
    if len(classes) < MIN_CLASSES or x.shape[0] < MIN_SAMPLES:
        return _stamp_pending(
            dataset_key,
            f"Need ≥{MIN_CLASSES} classes and ≥{MIN_SAMPLES} clips; have "
            f"{len(classes)} classes / {x.shape[0]} samples in {kp_dir}",
            classes,
        )

    clf = SoftmaxClassifier(epochs=600, learning_rate=0.2)
    clf.fit(x, y)
    bundle = clf.to_dict()
    bundle["feature_dim"] = POOL_DIM
    bundle["pool"] = "mean_std"
    bundle["source"] = "keypoints"

    out = ARTIFACTS / dataset_key
    out.mkdir(parents=True, exist_ok=True)
    (out / "model.json").write_text(json.dumps(bundle), encoding="utf-8")
    label_map = {str(i): name for i, name in enumerate(clf.classes_.tolist())}
    (out / "label_map.json").write_text(json.dumps(label_map, indent=2), encoding="utf-8")

    try:
        export_softmax_onnx(np.asarray(bundle["weights"], dtype=np.float32), out / "model.onnx")
        onnx_ok = True
    except Exception as err:  # noqa: BLE001
        print(f"[warn] ONNX export failed: {err}")
        onnx_ok = False

    # Quick train accuracy
    preds = clf.predict(x)
    acc = float(np.mean(preds == y)) if len(y) else 0.0
    status = {
        "dataset": dataset_key,
        "status": "ready" if onnx_ok else "ready_json_only",
        "samples": int(x.shape[0]),
        "classes": classes,
        "train_accuracy": round(acc, 4),
        "feature_dim": POOL_DIM,
        "onnx": onnx_ok,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "note": (
            f"Trained Softmax on pooled MediaPipe hand features "
            f"({len(classes)} classes). Expand with more INCLUDE/MS-ASL clips then retrain."
        ),
    }
    (out / "training_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(f"[ok] {dataset_key} samples={x.shape[0]} classes={len(classes)} acc={acc:.3f}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=("include50", "msasl100"), required=True)
    args = parser.parse_args()

    if args.dataset == "include50":
        dataset_key = "isl_include50"
        kp = KEYPOINTS / "isl_include50"
        if not any(kp.glob("*.npz")):
            archive_dir = DATASETS / "INCLUDE" / "archives"
            has = archive_dir.is_dir() and any(archive_dir.glob("*.zip"))
            note = (
                "INCLUDE archives present — unzip + extract_keypoints then retrain"
                if has
                else "No INCLUDE archives — run download_include --keys Greetings"
            )
            classes_path = DATASETS / "INCLUDE" / "meta" / "classes50.json"
            labels = (
                json.loads(classes_path.read_text(encoding="utf-8"))
                if classes_path.is_file()
                else []
            )
            out = _stamp_pending(dataset_key, note, labels if isinstance(labels, list) else [])
            print(f"[pending] {out}")
            return 0
        out = train_from_keypoints(dataset_key, kp)
    else:
        dataset_key = "asl_msasl100"
        kp = KEYPOINTS / "asl_msasl100"
        if not any(kp.glob("*.npz")):
            classes_path = DATASETS / "MS-ASL" / "meta" / "classes100.json"
            labels = (
                json.loads(classes_path.read_text(encoding="utf-8"))
                if classes_path.is_file()
                else []
            )
            out = _stamp_pending(
                dataset_key,
                "No keypoints yet — run extract_keypoints --dataset msasl100",
                labels if isinstance(labels, list) else [],
            )
            print(f"[pending] {out}")
            return 0
        out = train_from_keypoints(dataset_key, kp)

    print(f"[done] artifacts -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
