import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app"))
from services.layer3_analyzer import LOGO_CHECK, analyze_layer3  # noqa: E402

CROP_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "temp", "backups", "logo_identity_test_crops", "www.microsoft.com.png"
)
FAILURES = []


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


def main():
    with open(CROP_PATH, "rb") as f:
        logo_png = f.read()
    dummy_screenshot = b""

    real = analyze_layer3("https://www.microsoft.com/", dummy_screenshot, logo_png=logo_png)[LOGO_CHECK]
    print(f"  real domain result: {real}")
    check("logo check runs with a logo supplied", real["status"] == "checked")
    check("real Microsoft logo identified as Microsoft", real.get("identified_brand") == "Microsoft")
    check("real domain is not flagged", real.get("mismatch") is False)

    fake = analyze_layer3(
        "https://microsoft-account-verify-secure.tk/login", dummy_screenshot, logo_png=logo_png
    )[LOGO_CHECK]
    print(f"  fake domain result: {fake}")
    check("lookalike domain is flagged as mismatch", fake.get("mismatch") is True)

    none = analyze_layer3("https://www.microsoft.com/", dummy_screenshot, logo_png=None)[LOGO_CHECK]
    check("no logo supplied is reported, not penalized", none["status"] == "no_logo_provided")
    check("no logo supplied never sets mismatch", "mismatch" not in none)

    note_real = analyze_layer3("https://www.microsoft.com/", dummy_screenshot, logo_png=logo_png)["identity_note"]
    check("real domain gives the 'matches' level", note_real["level"] == "matches")

    note_fake = analyze_layer3(
        "https://microsoft-account-verify.tk/login", dummy_screenshot, logo_png=logo_png
    )["identity_note"]
    check("lookalike gives the 'closely resembles' level", note_fake["level"] == "closely resembles")
    check("note never uses the word phishing", "phishing" not in note_fake["text"].lower())
    check("note always carries the disclaimer", note_fake["disclaimer"].startswith("This is an automated analysis"))

    note_none = analyze_layer3("https://www.microsoft.com/", dummy_screenshot, logo_png=None)["identity_note"]
    check("no logo gives the 'could not confirm' level", note_none["level"] == "could not confirm")

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
        sys.exit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
