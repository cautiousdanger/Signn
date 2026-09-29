"""Download INCLUDE videos from Zenodo + HF metadata for INCLUDE-50.

Usage (from backend/):
  .\\.venv\\Scripts\\python.exe -m app.ml.temporal.download_include --subset include50

Videos land in datasets/INCLUDE/videos/
Metadata: datasets/INCLUDE/meta/
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # backend/
DATA_ROOT = ROOT.parent / "datasets" / "INCLUDE"
ZENODO_API = "https://zenodo.org/api/records/4010759"
HF_PARQUET_BASE = (
    "https://huggingface.co/datasets/ai4bharat/INCLUDE/resolve/main/data"
)


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    expected = 0
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=60) as resp:
            expected = int(resp.headers.get("Content-Length") or 0)
    except Exception:  # noqa: BLE001
        expected = 0

    existing = dest.stat().st_size if dest.exists() else 0
    if expected and existing >= expected and existing > 0:
        print(f"[skip] {dest.name} complete ({existing} bytes)")
        return
    if existing > 0 and expected and existing < expected:
        print(f"[resume] {dest.name} from {existing}/{expected}")
        req = urllib.request.Request(url)
        req.add_header("Range", f"bytes={existing}-")
        try:
            with urllib.request.urlopen(req, timeout=300) as resp, open(dest, "ab") as out:
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
            print(f"[ok] {dest} ({dest.stat().st_size} bytes)")
            return
        except Exception as err:  # noqa: BLE001
            print(f"[warn] resume failed ({type(err).__name__}); full re-download")
            dest.unlink(missing_ok=True)

    print(f"[get] {dest.name} …")
    urllib.request.urlretrieve(url, dest)
    print(f"[ok] {dest} ({dest.stat().st_size} bytes)")


def download_zenodo_archives(
    out_dir: Path,
    *,
    key_prefixes: list[str] | None = None,
    max_files: int = 0,
) -> list[Path]:
    """Download zip archives listed on the INCLUDE Zenodo record.

    key_prefixes: if set, only download keys that start with one of these
    (e.g. Greetings, Pronouns). Skips README / shell scripts automatically.
    """
    print(f"[zenodo] {ZENODO_API}")
    with urllib.request.urlopen(ZENODO_API, timeout=120) as resp:
        meta = json.loads(resp.read().decode("utf-8"))
    files = meta.get("files") or []
    saved: list[Path] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    prefixes = [p.lower() for p in (key_prefixes or []) if p.strip()]
    for item in files:
        key = str(item.get("key") or "file.bin")
        if not key.lower().endswith(".zip"):
            continue
        if prefixes and not any(key.lower().startswith(p.lower()) for p in prefixes):
            continue
        link = (item.get("links") or {}).get("self")
        if not link:
            continue
        dest = out_dir / key
        try:
            _download(link, dest)
            saved.append(dest)
        except Exception as err:  # noqa: BLE001
            print(f"[warn] failed {key}: {type(err).__name__}")
        if max_files and len(saved) >= max_files:
            break
    return saved


def write_readme(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    text = """# INCLUDE dataset workspace

1. Run: python -m app.ml.temporal.download_include --subset include50
2. Unzip archives under videos/ if not auto-unzipped
3. Extract MediaPipe keypoints (see AI4Bharat/INCLUDE generate_keypoints.py)
4. Train: python -m app.ml.temporal.train_isolated --dataset include50

Official code: https://github.com/AI4Bharat/INCLUDE
Zenodo: https://zenodo.org/records/4010759
HF metadata: https://huggingface.co/datasets/ai4bharat/INCLUDE
"""
    (out / "README.md").write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subset", choices=("include50", "include"), default="include50")
    parser.add_argument(
        "--skip-videos",
        action="store_true",
        help="Only create folders + README (no multi-GB Zenodo download)",
    )
    parser.add_argument(
        "--keys",
        type=str,
        default="",
        help="Comma-separated archive prefixes (e.g. Greetings,Pronouns). Empty=all zips.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="Stop after N matching zip downloads (0=all matched)",
    )
    args = parser.parse_args()

    write_readme(DATA_ROOT)
    key_prefixes = [p.strip() for p in args.keys.split(",") if p.strip()]
    status = {
        "subset": args.subset,
        "data_root": str(DATA_ROOT),
        "key_prefixes": key_prefixes,
        "videos": [],
    }
    if not args.skip_videos:
        archives = download_zenodo_archives(
            DATA_ROOT / "archives",
            key_prefixes=key_prefixes or None,
            max_files=args.max_files,
        )
        status["videos"] = [str(p) for p in archives]
    else:
        print("[info] skipped video download (--skip-videos)")

    (DATA_ROOT / "meta").mkdir(parents=True, exist_ok=True)
    (DATA_ROOT / "meta" / "download_status.json").write_text(
        json.dumps(status, indent=2), encoding="utf-8"
    )
    print("[done]", DATA_ROOT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
