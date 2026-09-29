"""Prepare MS-ASL100 download list and optionally fetch clips with yt-dlp.

Uses existing annotations, e.g.:
  C:\\Users\\...\\Documents\\MS-ASL\\MSASL_train.json

Usage:
  python -m app.ml.temporal.download_msasl --annotations-dir "...\\Documents\\MS-ASL" --max-per-class 5
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = ROOT.parent / "datasets" / "MS-ASL"


def load_split(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"expected list in {path}")
    return [row for row in data if isinstance(row, dict)]


def filter_msasl100(rows: list[dict]) -> list[dict]:
    return [r for r in rows if int(r.get("label") or 9999) < 100]


def write_manifest(rows: list[dict], dest: Path, max_per_class: int) -> list[dict]:
    by_label: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        label = int(row["label"])
        if len(by_label[label]) >= max_per_class:
            continue
        by_label[label].append(row)
    selected: list[dict] = []
    for label in sorted(by_label):
        selected.extend(by_label[label])
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(selected, indent=2), encoding="utf-8")
    return selected


def try_download_clip(url: str, out_path: Path) -> bool:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists() and out_path.stat().st_size > 10_000:
        return True
    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "-f",
        "mp4/best[height<=480]/best",
        "-o",
        str(out_path),
        "--no-playlist",
        url if url.startswith("http") else f"https://{url}",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return result.returncode == 0 and out_path.exists()
    except Exception:  # noqa: BLE001
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--annotations-dir",
        type=Path,
        default=Path.home()
        / "OneDrive - CACHE DIGITECH"
        / "Documents"
        / "MS-ASL",
    )
    parser.add_argument("--max-per-class", type=int, default=8)
    parser.add_argument(
        "--download",
        action="store_true",
        help="Actually download clips (requires yt-dlp)",
    )
    parser.add_argument("--limit", type=int, default=0, help="Max clips to download (0=all)")
    args = parser.parse_args()

    ann = args.annotations_dir
    train_path = ann / "MSASL_train.json"
    if not train_path.is_file():
        print(f"[error] missing {train_path}")
        return 1

    classes_path = ann / "MSASL_classes.json"
    classes = json.loads(classes_path.read_text(encoding="utf-8")) if classes_path.is_file() else []

    rows = filter_msasl100(load_split(train_path))
    manifest = write_manifest(rows, DATA_ROOT / "manifests" / "msasl100_train.json", args.max_per_class)
    (DATA_ROOT / "meta").mkdir(parents=True, exist_ok=True)
    (DATA_ROOT / "meta" / "classes100.json").write_text(
        json.dumps(classes[:100], indent=2), encoding="utf-8"
    )
    print(f"[ok] manifest clips={len(manifest)} classes~100 -> {DATA_ROOT}")

    if not args.download:
        print("[info] pass --download to fetch videos with yt-dlp")
        return 0

    ok = 0
    fail = 0
    for i, row in enumerate(manifest):
        if args.limit and i >= args.limit:
            break
        label = int(row["label"])
        text = str(row.get("text") or classes[label] if label < len(classes) else label)
        url = str(row.get("url") or "")
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in text)[:40]
        out = DATA_ROOT / "videos" / f"{label:03d}_{safe}" / f"clip_{i:05d}.mp4"
        if try_download_clip(url, out):
            ok += 1
            print(f"[ok] {out.name}")
        else:
            fail += 1
            print(f"[fail] label={label} url={url[:60]}")
    print(f"[done] ok={ok} fail={fail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
