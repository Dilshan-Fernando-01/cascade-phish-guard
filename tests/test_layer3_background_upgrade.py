import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app"))
import services.background_compare as bc  # noqa: E402
from services.layer3_analyzer import analyze_layer3  # noqa: E402

FAILURES = []


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


def fake_background(result):
    def _check(url, brand_domain):
        return result
    return _check


ORIGINAL = bc.background_check


bc.background_check = fake_background(
    {"status": "checked", "brand_domain": "paypal.com", "source": "live", "band": "strong", "similarity": 0.95,
     "region": {"status": "checked", "both_match": True, "similarities": [0.9, 0.9]}}
)
note = analyze_layer3("https://paypa1.com/login", b"", background=True)["identity_note"]
check("the live check runs and a logo match upgrades the note", note["level"] == "closely resembles")
check("the upgraded note still never says phishing", "phishing" not in note["text"].lower())


note_off = analyze_layer3("https://paypa1.com/login", b"", background=False)["identity_note"]
check("background=False never upgrades the note", note_off["level"] == "may be imitating")


bc.background_check = fake_background(
    {"status": "checked", "brand_domain": "paypal.com", "source": "live", "band": None, "similarity": None,
     "region": {"status": "checked", "both_match": True, "similarities": [0.9, 0.9]}}
)
note = analyze_layer3("https://paypa1.com/login", b"", background=True)["identity_note"]
check("a region match alone also upgrades the note", note["level"] == "closely resembles")
check("region-based upgrade text mentions layout, not a specific method", "layout" in note["text"])


bc.background_check = fake_background(
    {"status": "checked", "brand_domain": "paypal.com", "source": "live", "band": "weak", "similarity": 0.3,
     "region": {"status": "checked", "both_match": False, "similarities": [0.2, 0.3]}}
)
result = analyze_layer3("https://paypa1.com/login", b"", background=True)
check("no confirmation leaves the note as 'may be imitating'", result["identity_note"]["level"] == "may be imitating")
check("the background result is still recorded for the reasons/log", result["background"]["region"]["both_match"] is False)


bc.background_check = fake_background({"status": "could not confirm", "reason": "visited site: blocked", "brand_domain": "paypal.com"})
result = analyze_layer3("https://paypa1.com/login", b"", background=True)
check("a failed fetch leaves the note as 'may be imitating'", result["identity_note"]["level"] == "may be imitating")
check("the failed fetch's reason is still recorded", result["background"]["status"] == "could not confirm")

bc.background_check = ORIGINAL


def fail_if_called(url, brand_domain):
    raise AssertionError("background_check should not run when the address is not imitating anything")


bc.background_check = fail_if_called
same_domain_note = analyze_layer3("https://nibm.ac.lk/", b"", background=True)["identity_note"]
check("an address with no brand hint never calls the live check", same_domain_note["level"] == "could not confirm")
bc.background_check = ORIGINAL

print()
if FAILURES:
    print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
    sys.exit(1)
print("All checks passed.")
