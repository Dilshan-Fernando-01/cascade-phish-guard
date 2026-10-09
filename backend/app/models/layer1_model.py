import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import joblib
import pandas as pd


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from features.url_features import extract_all_features, is_institutional_suffix, prepare_features

_MODEL_PATH = Path(__file__).resolve().parents[3] / "data" / "models" / "layer1_winner.joblib"
_artifact = None


INSTITUTIONAL_UNRANKED_CAP = 0.15


def _load_artifact():

    global _artifact
    if _artifact is None:
        _artifact = joblib.load(_MODEL_PATH)
    return _artifact


def _institutional_unranked_adjustment(url, raw_features, score):
    """The model leans heavily on "not in the popularity ranking" and "no public
    registration-date record" - rightly so in general, real phishing domains are almost
    never on Tranco and almost never have old WHOIS records, so the model learned a true
    pattern. The edge case it has too few training examples of is a small, genuine
    institutional site that is unranked and has no WHOIS data for entirely innocent
    reasons. When the address itself carries a real, registry-verified institutional
    suffix (is_institutional_suffix - not gameable by naming a domain cleverly, only a
    suffix the registry actually assigned counts) AND every other independent signal is
    clean, the absence of ranking/age data is better explained by "small legitimate site"
    than "throwaway site", so it should not carry the score into suspicious territory on
    its own. Never fires if any other red flag is present, so it only ever narrows what
    the missing ranking/age data explains - it cannot mask a genuine warning sign."""
    host = urlparse(url).netloc.split(":")[0]
    if not is_institutional_suffix(host):
        return score
    if raw_features.get("tranco_rank_bucket") != 0:
        return score
    if raw_features.get("domain_age_days") is not None:
        return score
    if raw_features.get("has_ip_host") or raw_features.get("is_punycode_or_homograph"):
        return score
    if raw_features.get("has_at_symbol"):
        return score
    brand_distance = raw_features.get("brand_distance_score")
    if brand_distance is not None and brand_distance <= 2:
        return score
    if (raw_features.get("keyword_score") or 0) > 0:
        return score
    return min(score, INSTITUTIONAL_UNRANKED_CAP)


def predict(url):

    artifact = _load_artifact()
    model = artifact["model"]
    median_domain_age = artifact["median_domain_age"]

    raw_features = extract_all_features(url)
    X = prepare_features(pd.DataFrame([raw_features]), median_domain_age)

    if "scaler" in artifact:
        X = artifact["scaler"].transform(X)

    phishing_probability = float(model.predict_proba(X)[0][1])
    phishing_probability = _institutional_unranked_adjustment(url, raw_features, phishing_probability)
    return phishing_probability, raw_features
