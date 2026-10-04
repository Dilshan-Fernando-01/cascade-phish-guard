import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app"))
from services.layer3_analyzer import ORIGINAL_COMPARISON, analyze_layer3  # noqa: E402

CROP_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "temp", "backups", "logo_identity_test_crops", "www.microsoft.com.png"
)
FAILURES = []


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


def candidate_for(result, domain):
    for c in result["candidates"]:
        if c["domain"] == domain:
            return c
    return None


def main():
    with open(CROP_PATH, "rb") as f:
        logo_png = f.read()

    same = analyze_layer3("https://microsoft-account-verify.tk/login", b"", logo_png=logo_png)[ORIGINAL_COMPARISON]
    print(f"  lookalike with Microsoft logo: {same}")
    check("comparison runs with a logo and a candidate", same["status"] == "checked")
    ms = candidate_for(same, "microsoft.com")
    check("Microsoft logo vs microsoft.com candidate is strong", ms is not None and ms["band"] == "strong")

    other = analyze_layer3("https://paypa1.com/login", b"", logo_png=logo_png)[ORIGINAL_COMPARISON]
    print(f"  paypa1 with Microsoft logo: {other}")
    pp = candidate_for(other, "paypal.com")
    check("Microsoft logo vs paypal.com candidate is weak", pp is not None and pp["band"] == "weak")

    none = analyze_layer3("https://microsoft-account-verify.tk/login", b"", logo_png=None)[ORIGINAL_COMPARISON]
    check("no logo gives no_logo_provided", none["status"] == "no_logo_provided")

    no_hint = analyze_layer3("https://nibm.ac.lk/", b"", logo_png=logo_png)[ORIGINAL_COMPARISON]
    check("no candidate brand gives no_candidates", no_hint["status"] == "no_candidates")

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
        sys.exit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
