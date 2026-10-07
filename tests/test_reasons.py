import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app"))
from services.reasons import MAX_REASONS, layer1_reasons, layer2_reasons, layer3_reasons, public_reasons  # noqa: E402

FAILURES = []


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


PLAIN_L1 = {"brand_keyword_in_host": 0, "brand_distance_score": 9, "is_punycode_or_homograph": 0,
            "has_ip_host": 0, "tld_risk_score": 0.0, "domain_age_days": 5000, "tranco_rank_bucket": 3}
check("a plain, known site gives no layer 1 reasons", layer1_reasons(PLAIN_L1) == [])
check("missing features give no reasons", layer1_reasons(None) == [])
check("a brand name in the address is a reason",
      any("known brand" in r for r in layer1_reasons({**PLAIN_L1, "brand_keyword_in_host": 1})))
check("a missing registration date is a reason",
      any("registration date" in r for r in layer1_reasons({**PLAIN_L1, "domain_age_days": None})))
check("layer 1 never lists more than the maximum",
      len(layer1_reasons({"brand_keyword_in_host": 1, "brand_distance_score": 1, "is_punycode_or_homograph": 1,
                          "has_ip_host": 1, "tld_risk_score": 1.0, "domain_age_days": None,
                          "tranco_rank_bucket": 0})) <= MAX_REASONS)

check("a password field is a layer 2 reason", "This page asks for a password." in layer2_reasons({"password_input_count": 1}))
check("no password and no other signal gives no layer 2 reasons", layer2_reasons({"password_input_count": 0}) == [])
check("an error in layer 2 gives no reasons", layer2_reasons({"error": "could not load"}) == [])

L3_COPY = {"identity_note": {"level": "closely resembles"},
           "combination": {"brand_mismatch": True, "input_signal": True},
           "background": {"status": "checked", "band": "strong"}}
check("a copy with input lists the mismatch", any("not that brand" in r for r in layer3_reasons(L3_COPY)))
check("a copy with input lists the input request", any("asks the visitor" in r for r in layer3_reasons(L3_COPY)))
check("input alone (no mismatch) is not a reason",
      layer3_reasons({"combination": {"brand_mismatch": False, "input_signal": True}, "identity_note": {"level": "could not confirm"}}) == [])
check("a strong home-page match is a reason", any("home page" in r for r in layer3_reasons(L3_COPY)))
check("a layer 3 error gives no reasons", layer3_reasons({"error": "could not run"}) == [])
check("no layer 3 result gives no reasons", layer3_reasons(None) == [])


L3_MATCHES_OWN_BRAND = {"identity_note": {"level": "matches"}, "combination": {"brand_mismatch": False, "input_signal": True}}
check("a brand matching its own address gives no layer 3 reasons", layer3_reasons(L3_MATCHES_OWN_BRAND) == [])
check(
    "so a suspicious verdict from layer 2 alone does not also blame layer 3",
    "layer3" not in public_reasons({"layer1": [], "layer2": ["x"], "layer3": layer3_reasons(L3_MATCHES_OWN_BRAND)}, "suspicious"),
)

# No reason should expose a threshold, a score or a feature name
all_text = " ".join(layer1_reasons({**PLAIN_L1, "brand_keyword_in_host": 1}) + layer2_reasons({"password_input_count": 1})
                    + layer3_reasons(L3_COPY))
check("reasons contain no numbers or feature names",
      not any(ch.isdigit() for ch in all_text) and "_" not in all_text)

DETAILED = {"layer1": ["The address contains the name of a known brand."], "layer2": [], "layer3": ["x"]}
check("a safe result shows no reasons at all", public_reasons(DETAILED, "safe") == {})
check("a suspicious result shows one general sentence per layer with a signal",
      public_reasons(DETAILED, "suspicious") == {"layer1": ["The web address needs a closer look."],
                                                  "layer3": ["The page's visual identity needs a closer look."]})
check("public sentences name no check", all("brand" not in t and "password" not in t
      for v in public_reasons(DETAILED, "phishing").values() for t in v))

print()
if FAILURES:
    print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
    sys.exit(1)
print("All checks passed.")
