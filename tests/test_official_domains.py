import ast
import collections
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app"))
from features.official_domains import OFFICIAL_DOMAINS, is_official  # noqa: E402

FAILURES = []


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app", "features", "official_domains.py")).read()
for node in ast.parse(src).body:
    if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "OFFICIAL_DOMAINS":
        keys = [k.value for k in node.value.keys]
        check("no duplicate brand keys", not [k for k, n in collections.Counter(keys).items() if n > 1])

check("YouTube is a Google-owned domain", is_official("youtube.com", "google.com"))
check("Google's video host is official", is_official("googlevideo.com", "google.com"))
check("AWS hosting is official for Amazon", is_official("amazonaws.com", "amazon.com"))
check("an unrelated domain is not official", not is_official("paypa1.com", "google.com"))
check("an empty domain is not official", not is_official("", "google.com"))

print()
if FAILURES:
    print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
    sys.exit(1)
print("All checks passed.")
