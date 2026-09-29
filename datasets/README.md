# Sign-language datasets workspace

ASL (MS-ASL100) and ISL (INCLUDE) video downloads land here. They are gitignored.

## Quick pipeline

From `backend/` with Python 3.12 venv (`.venv312` — MediaPipe + torch):

```powershell
# ASL clips (YouTube; many URLs die)
.\.venv\Scripts\python.exe -m app.ml.temporal.download_msasl --download --max-per-class 3 --limit 80

# ISL archives (Zenodo; prefer small prefixes first)
.\.venv\Scripts\python.exe -m app.ml.temporal.download_include --keys Greetings --max-files 2
.\.venv\Scripts\python.exe -m app.ml.temporal.unzip_include --keys Greetings

# Keypoints + train
..\.venv312\Scripts\python.exe -m app.ml.temporal.extract_keypoints --dataset msasl100
..\.venv312\Scripts\python.exe -m app.ml.temporal.extract_keypoints --dataset include50
.\.venv312\Scripts\python.exe -m app.ml.temporal.train_isolated --dataset msasl100
.\.venv312\Scripts\python.exe -m app.ml.temporal.train_isolated --dataset include50
```

Artifacts appear under `backend/app/ml/temporal/artifacts/{asl_msasl100,isl_include50}/`.
`GET /ml/lexicon-status` flips `asl_ready` / `isl_ready` when `model.onnx` (or `model.json`) + `label_map.json` exist.

Talk lexicon mode (ASL / ISL) uses those models; AAC mode stays on the 13-gesture heuristics.
