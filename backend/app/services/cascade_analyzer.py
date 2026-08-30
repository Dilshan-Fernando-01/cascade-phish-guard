import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from features.url_features import validate_url
from models.layer1_model import predict as layer1_predict
from schemas.analyze import AnalyzeResponse, Verdict

LOW_THRESHOLD = 0.2
HIGH_THRESHOLD = 0.8

LAYER2_ENABLED = os.environ.get("ENABLE_LAYER2", "").lower() in ("1", "true", "yes")


_progress_store = {}
_progress_lock = threading.Lock()
_PROGRESS_TTL_SECONDS = 300


STAGE_CHECKING_ADDRESS = "checking_address"
STAGE_REVIEWING_CONTENT = "reviewing_content"
STAGE_DONE = "done"


def _set_progress(request_id, data):
    if request_id is None:
        return
    with _progress_lock:
        _progress_store[request_id] = {**data, "_ts": time.monotonic()}
        cutoff = time.monotonic() - _PROGRESS_TTL_SECONDS
        stale = [rid for rid, v in _progress_store.items() if v["_ts"] < cutoff]
        for rid in stale:
            del _progress_store[rid]


def get_progress(request_id):
    with _progress_lock:
        entry = _progress_store.get(request_id)
        return None if entry is None else {k: v for k, v in entry.items() if k != "_ts"}


def analyze(url, full_scan=False, request_id=None):
    is_valid, reason = validate_url(url)
    if not is_valid:
        raise ValueError(f"invalid URL ({reason})")

    _set_progress(request_id, {"stage": STAGE_CHECKING_ADDRESS})

    layer1_score, _features = layer1_predict(url)
    would_escalate = LOW_THRESHOLD <= layer1_score <= HIGH_THRESHOLD

    layers_used = ["layer1"]
    layer_scores = {"layer1": layer1_score}
    layer2_features = None
    layer2_score = None

    will_run_layer2 = (would_escalate or full_scan) and LAYER2_ENABLED
    _set_progress(
        request_id,
        {
            "stage": STAGE_REVIEWING_CONTENT if will_run_layer2 else STAGE_DONE,
            "layer1_score": layer1_score,
        },
    )

    if will_run_layer2:
        from services.layer2_analyzer import analyze_layer2
        from models.layer2_model import predict_from_features

        layer2_result = analyze_layer2(url)
        layers_used.append("layer2")
        if layer2_result["success"]:
            layer2_features = layer2_result["features"]
            layer2_score = predict_from_features(layer2_features)
            layer_scores["layer2"] = layer2_score
        else:
            layer2_features = {"error": layer2_result["error"]}

    if layer2_score is not None:
        score_for_verdict = layer2_score
    else:
        score_for_verdict = layer1_score

    if score_for_verdict > HIGH_THRESHOLD:
        verdict = Verdict.phishing
    elif score_for_verdict < LOW_THRESHOLD:
        verdict = Verdict.safe
    else:
        verdict = Verdict.suspicious

    result = AnalyzeResponse(
        url=url,
        verdict=verdict,
        confidence=score_for_verdict,
        layers_used=layers_used,
        layer_scores=layer_scores,
        would_escalate=would_escalate,
        layer2_features=layer2_features,
    )
    _set_progress(request_id, {"stage": STAGE_DONE, "result": result.model_dump(mode="json")})
    return result
