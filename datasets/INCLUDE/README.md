# INCLUDE dataset workspace

1. Run: python -m app.ml.temporal.download_include --subset include50
2. Unzip archives under videos/ if not auto-unzipped
3. Extract MediaPipe keypoints (see AI4Bharat/INCLUDE generate_keypoints.py)
4. Train: python -m app.ml.temporal.train_isolated --dataset include50

Official code: https://github.com/AI4Bharat/INCLUDE
Zenodo: https://zenodo.org/records/4010759
HF metadata: https://huggingface.co/datasets/ai4bharat/INCLUDE
