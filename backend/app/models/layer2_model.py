import os
import sys
from pathlib import Path

import joblib
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.layer2_analyzer import LAYER2_FEATURE_COLUMNS

_MODEL_PATH = Path(__file__).resolve().parents[3] / "data" / "models" / "layer2_winner.joblib"
_artifact = None


def _load_artifact():
    global _artifact
    if _artifact is None:
        _artifact = joblib.load(_MODEL_PATH)
    return _artifact


def predict_from_features(features):
    artifact = _load_artifact()
    model = artifact["model"]

    X = pd.DataFrame([features])[LAYER2_FEATURE_COLUMNS]
    if "scaler" in artifact:
        X = artifact["scaler"].transform(X)

    return float(model.predict_proba(X)[0][1])
