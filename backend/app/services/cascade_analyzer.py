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

LAYER1_CONFIDENT_FLOOR = 0.5


def _layer1_confidence_floor(layer1_score, score_for_verdict):
    if layer1_score > HIGH_THRESHOLD:
        return max(score_for_verdict, LAYER1_CONFIDENT_FLOOR)
    return score_for_verdict


_progress_store = {}
_progress_lock = threading.Lock()
_PROGRESS_TTL_SECONDS = 300


STAGE_CHECKING_ADDRESS = "checking_address"
STAGE_REVIEWING_CONTENT = "reviewing_content"
STAGE_COMPARING_VISUAL_IDENTITY = "comparing_visual_identity"
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


def analyze(url, full_scan=False, request_id=None, html=None, skip_layer2=False, screenshot_png=None, logo_png=None):
    is_valid, reason = validate_url(url)
    if not is_valid:
        raise ValueError(f"invalid URL ({reason})")

    _set_progress(request_id, {"stage": STAGE_CHECKING_ADDRESS})

    layer1_score, layer1_features = layer1_predict(url)
    would_escalate = LOW_THRESHOLD <= layer1_score <= HIGH_THRESHOLD

    layers_used = ["layer1"]
    layer_scores = {"layer1": layer1_score}
    layer2_features = None
    layer2_score = None

    will_run_layer2 = (would_escalate or full_scan) and LAYER2_ENABLED and not skip_layer2
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

        layer2_result = analyze_layer2(url, html=html)
        layers_used.append("layer2")
        if layer2_result["success"]:
            layer2_features = layer2_result["features"]
            layer2_score = predict_from_features(layer2_features)
            layer_scores["layer2"] = layer2_score
        else:
            layer2_features = {"error": layer2_result["error"]}

    layer3_results = None
    if full_scan and (screenshot_png is not None or logo_png is not None):
        from services.layer3_analyzer import analyze_layer3

        _set_progress(
            request_id,
            {"stage": STAGE_COMPARING_VISUAL_IDENTITY, "layer1_score": layer1_score, "layer2_score": layer2_score},
        )
        try:
            layer3_results = analyze_layer3(
                url, screenshot_png, html=html, logo_png=logo_png, background=True
            )
        except Exception as exc:
            layer3_results = {"error": f"Layer 3 could not run on this machine: {exc}"}
        layers_used.append("layer3")

    if layer2_score is not None:
        score_for_verdict = layer2_score
    else:
        score_for_verdict = layer1_score

    score_for_verdict = _layer1_confidence_floor(layer1_score, score_for_verdict)

    if layer3_results is not None and "error" not in layer3_results:
        from services.layer3_rule import apply_layer3_rule, identity_level_score

        score_for_verdict, combination = apply_layer3_rule(
            score_for_verdict, layer3_results, layer2_features, layer2_score, html
        )
        layer3_results["combination"] = combination
        layer3_score = identity_level_score(layer3_results)
        if layer3_score is not None:
            layer_scores["layer3"] = layer3_score

    if score_for_verdict > HIGH_THRESHOLD:
        verdict = Verdict.phishing
    elif score_for_verdict < LOW_THRESHOLD:
        verdict = Verdict.safe
    else:
        verdict = Verdict.suspicious

    from services.reasons import layer1_reasons, layer2_reasons, layer3_reasons, public_reasons

   
    layer1_safe = layer1_score < LOW_THRESHOLD
    layer2_safe = layer2_score is None or layer2_score < LOW_THRESHOLD
    detailed_reasons = {
        "layer1": [] if layer1_safe else layer1_reasons(layer1_features),
        "layer2": [] if layer2_safe else layer2_reasons(layer2_features),
        "layer3": layer3_reasons(layer3_results),
    }
    reasons = public_reasons(detailed_reasons, verdict.value)

    result = AnalyzeResponse(
        url=url,
        verdict=verdict,
        confidence=score_for_verdict,
        layers_used=layers_used,
        layer_scores=layer_scores,
        would_escalate=would_escalate,
        layer1_features=layer1_features,
        layer2_features=layer2_features,
        layer3_results=layer3_results,
        reasons=reasons,
    )
    _set_progress(request_id, {"stage": STAGE_DONE, "result": result.model_dump(mode="json")})
    return result
