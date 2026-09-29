"""Unzip INCLUDE archives into datasets/INCLUDE/videos/.

Usage:
  python -m app.ml.temporal.unzip_include
  python -m app.ml.temporal.unzip_include --keys Greetings
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = ROOT.parent / "datasets" / "INCLUDE"


def unzip_archives(*, key_prefixes: list[str] | None = None) -> int:
    archives = DATA_ROOT / "archives"
    dest = DATA_ROOT / "videos"
    dest.mkdir(parents=True, exist_ok=True)
    if not archives.is_dir():
        print(f"[error] missing {archives}")
        return 1
    prefixes = [p.lower() for p in (key_prefixes or []) if p.strip()]
    count = 0
    for zpath in sorted(archives.glob("*.zip")):
        if prefixes and not any(zpath.name.lower().startswith(p) for p in prefixes):
            continue
        # Skip obviously incomplete downloads (< 50MB).
        if zpath.stat().st_size < 50_000_000:
            print(f"[skip] too small (incomplete?): {zpath.name}")
            continue
        print(f"[unzip] {zpath.name} …")
        try:
            with zipfile.ZipFile(zpath, "r") as zf:
                zf.extractall(dest)
            count += 1
            print(f"[ok] {zpath.name}")
        except zipfile.BadZipFile:
            print(f"[fail] bad zip {zpath.name}")
    print(f"[done] unzipped={count} -> {dest}")
    return 0 if count else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--keys",
        type=str,
        default="",
        help="Comma-separated archive prefixes (e.g. Greetings)",
    )
    args = parser.parse_args()
    prefixes = [p.strip() for p in args.keys.split(",") if p.strip()]
    return unzip_archives(key_prefixes=prefixes or None)


if __name__ == "__main__":
    sys.exit(main())
