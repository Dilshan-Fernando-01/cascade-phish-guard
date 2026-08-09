import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from features.url_features import validate_url
from models.layer1_model import predict as layer1_predict
from schemas.analyze import AnalyzeResponse, Verdict


LOW_THRESHOLD = 0.2
HIGH_THRESHOLD = 0.8


def analyze(url):

    is_valid, reason = validate_url(url)
    if not is_valid:
        raise ValueError(f"invalid URL ({reason})")

    layer1_score, _features = layer1_predict(url)

    would_escalate = LOW_THRESHOLD <= layer1_score <= HIGH_THRESHOLD

    if layer1_score > HIGH_THRESHOLD:
        verdict = Verdict.phishing
    elif layer1_score < LOW_THRESHOLD:
        verdict = Verdict.safe
    else:
        verdict = Verdict.suspicious

    return AnalyzeResponse(
        url=url,
        verdict=verdict,
        confidence=layer1_score,
        layers_used=["layer1"],
        layer_scores={"layer1": layer1_score},
        would_escalate=would_escalate,
    )
