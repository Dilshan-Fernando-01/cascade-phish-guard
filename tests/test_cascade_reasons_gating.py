

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app"))
import services.cascade_analyzer as ca  # noqa: E402
import services.layer2_analyzer as l2a  # noqa: E402
import models.layer2_model as l2m  # noqa: E402

FAILURES = []


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


ORIGINAL_LAYER1_PREDICT = ca.layer1_predict
ORIGINAL_LAYER2_ENABLED = ca.LAYER2_ENABLED
ORIGINAL_ANALYZE_LAYER2 = l2a.analyze_layer2
ORIGINAL_PREDICT_FROM_FEATURES = l2m.predict_from_features


ca.layer1_predict = lambda url: (0.05, {
    "brand_keyword_in_host": 0, "brand_distance_score": 9, "is_punycode_or_homograph": 0,
    "has_ip_host": 0, "tld_risk_score": 0.0, "domain_age_days": None, "tranco_rank_bucket": 5,
})

ca.LAYER2_ENABLED = True
l2a.analyze_layer2 = lambda url, html=None: {"success": True, "features": {"password_input_count": 1}}
l2m.predict_from_features = lambda features: 0.5

result = ca.analyze("https://example.com/", full_scan=True, skip_layer2=False, html="<html></html>")
check("the overall verdict is suspicious", result.verdict.value == "suspicious")
check("a safe layer 1 is not blamed even though one of its features was flagged", "layer1" not in result.reasons)
check("a genuinely suspicious layer 2 is still named", "layer2" in result.reasons)

ca.layer1_predict = ORIGINAL_LAYER1_PREDICT
ca.LAYER2_ENABLED = ORIGINAL_LAYER2_ENABLED
l2a.analyze_layer2 = ORIGINAL_ANALYZE_LAYER2
l2m.predict_from_features = ORIGINAL_PREDICT_FROM_FEATURES

print()
if FAILURES:
    print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
    sys.exit(1)
print("All checks passed.")
