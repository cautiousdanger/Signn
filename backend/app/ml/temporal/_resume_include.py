import json, sys, time, urllib.request
from pathlib import Path

ROOT = Path(r"c:\Users\Akshay\OneDrive - CACHE DIGITECH\D\gesture\datasets\INCLUDE\archives")
ROOT.mkdir(parents=True, exist_ok=True)
meta = json.loads(urllib.request.urlopen("https://zenodo.org/api/records/4010759", timeout=60).read())
wanted = {"Adjectives_3of8.zip", "Greetings_1of2.zip"}
files = {f["key"]: (f["links"]["self"], int(f["size"])) for f in meta["files"] if f["key"] in wanted}

def download(key, url, size):
    dest = ROOT / key
    existing = dest.stat().st_size if dest.exists() else 0
    if existing >= size:
        print(f"[skip] {key} complete", flush=True)
        return
    print(f"[start] {key} {existing}/{size}", flush=True)
    while existing < size:
        req = urllib.request.Request(url)
        if existing:
            req.add_header("Range", f"bytes={existing}-")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "ab") as out:
                last = time.time()
                while True:
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    out.write(chunk)
                    existing += len(chunk)
                    if time.time() - last > 5:
                        out.flush()
                        pct = 100.0 * existing / size
                        print(f"[prog] {key} {existing}/{size} ({pct:.1f}%)", flush=True)
                        last = time.time()
        except Exception as err:
            print(f"[retry] {key} {type(err).__name__}: {err}", flush=True)
            time.sleep(3)
            existing = dest.stat().st_size if dest.exists() else 0
    print(f"[done] {key} {dest.stat().st_size}", flush=True)

for key, (url, size) in files.items():
    download(key, url, size)
print("[all done]", flush=True)
