import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app"))
import services.cascade_analyzer as ca  
import services.layer2_analyzer as l2a 
import models.layer2_model as l2m  

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


l2a.analyze_layer2 = lambda url, html=None: {
    "success": True,
    "features": {
        "password_input_count": 0,
        "checked_embedded_url_count": 5,
        "suspicious_embedded_url_count": 4,
        "max_embedded_url_risk": 0.7851,
        "flagged_embedded_urls": [
            {"url": "https://risky-one.example/x", "score": 0.7851},
            {"url": "https://risky-two.example/y", "score": 0.71},
        ],
    },
}
l2m.predict_from_features = lambda features: 0.18

result = ca.analyze("https://example.com/", full_scan=True, skip_layer2=False, html="<html></html>")
check("verdict is safe (page itself scored low)", result.verdict.value == "safe")
check("embedded_url_warning is present even though verdict is safe", result.embedded_url_warning is not None)
if result.embedded_url_warning:
    check("checked_count matches", result.embedded_url_warning["checked_count"] == 5)
    check("suspicious_count matches", result.embedded_url_warning["suspicious_count"] == 4)
    check("flagged list carried through", len(result.embedded_url_warning["flagged"]) == 2)


l2a.analyze_layer2 = lambda url, html=None: {
    "success": True,
    "features": {
        "password_input_count": 0,
        "checked_embedded_url_count": 3,
        "suspicious_embedded_url_count": 0,
        "max_embedded_url_risk": 0.1,
        "flagged_embedded_urls": [],
    },
}
result2 = ca.analyze("https://example.com/", full_scan=True, skip_layer2=False, html="<html></html>")
check("no embedded_url_warning when nothing was flagged", result2.embedded_url_warning is None)

ca.layer1_predict = ORIGINAL_LAYER1_PREDICT
ca.LAYER2_ENABLED = ORIGINAL_LAYER2_ENABLED
l2a.analyze_layer2 = ORIGINAL_ANALYZE_LAYER2
l2m.predict_from_features = ORIGINAL_PREDICT_FROM_FEATURES

print()
if FAILURES:
    print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
    sys.exit(1)
print("All checks passed.")
