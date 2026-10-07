

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app"))
from features.url_features import (  # noqa: E402
    _registrable_domain_guess,
    brand_distance_score,
    brand_keyword_in_host,
    tranco_rank_bucket,
)

FAILURES = []


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


for host in ["amazon.com", "Amazon.com", "AMAZON.COM", "WWW.AMAZON.COM", "www.Amazon.com"]:
    check(f"tranco rank for {host!r} matches the lowercase lookup", tranco_rank_bucket(host) == tranco_rank_bucket("amazon.com"))

check("registrable domain guess ignores case", _registrable_domain_guess("PayPal.com") == "paypal.com")
check(
    "a brand-name lookalike is still caught regardless of case",
    brand_keyword_in_host("Secure-PayPal-Login.tk") == brand_keyword_in_host("secure-paypal-login.tk"),
)
check(
    "brand distance is the same regardless of case",
    brand_distance_score("Paypa1.com") == brand_distance_score("paypa1.com"),
)

print()
if FAILURES:
    print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
    sys.exit(1)
print("All checks passed.")
