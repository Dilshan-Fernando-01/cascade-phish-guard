import os
import sys
from pathlib import Path

import joblib
import pandas as pd


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from features.url_features import extract_all_features, prepare_features 

_MODEL_PATH = Path(__file__).resolve().parents[3] / "data" / "models" / "layer1_winner.joblib"
_artifact = None


def _load_artifact():

    global _artifact
    if _artifact is None:
        _artifact = joblib.load(_MODEL_PATH)
    return _artifact


def predict(url):

    artifact = _load_artifact()
    model = artifact["model"]
    median_domain_age = artifact["median_domain_age"]

    raw_features = extract_all_features(url)
    X = prepare_features(pd.DataFrame([raw_features]), median_domain_age)

    if "scaler" in artifact:
        X = artifact["scaler"].transform(X)

    phishing_probability = float(model.predict_proba(X)[0][1])
    return phishing_probability, raw_features
