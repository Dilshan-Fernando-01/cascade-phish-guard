import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from features.url_features import validate_url
from models.layer1_model import predict as layer1_predict
from schemas.analyze import AnalyzeResponse, Verdict

LOW_THRESHOLD = 0.2
HIGH_THRESHOLD = 0.8

LAYER2_ENABLED = os.environ.get("ENABLE_LAYER2", "").lower() in ("1", "true", "yes")


def analyze(url):
    is_valid, reason = validate_url(url)
    if not is_valid:
        raise ValueError(f"invalid URL ({reason})")

    layer1_score, _features = layer1_predict(url)
    would_escalate = LOW_THRESHOLD <= layer1_score <= HIGH_THRESHOLD

    layers_used = ["layer1"]
    layer_scores = {"layer1": layer1_score}
    layer2_features = None

    if would_escalate and LAYER2_ENABLED:
        from services.layer2_analyzer import analyze_layer2

        layer2_result = analyze_layer2(url)
        layers_used.append("layer2")
        if layer2_result["success"]:
            layer2_features = layer2_result["features"]
        else:
            layer2_features = {"error": layer2_result["error"]}

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
        layers_used=layers_used,
        layer_scores=layer_scores,
        would_escalate=would_escalate,
        layer2_features=layer2_features,
    )
