import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app"))
from services.cascade_analyzer import analyze  # noqa: E402

FAILURES = []
URL = "https://www.google.com/"
FAKE_SCREENSHOT = b"not-a-real-png-but-enough-to-trigger-the-layer3-path"


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


def main():
    quick = analyze(URL, full_scan=False)
    check("quick scan never runs layer3", "layer3" not in quick.layers_used)
    check("quick scan has no layer3_results", quick.layer3_results is None)

    full_no_shot = analyze(URL, full_scan=True)
    check("full scan without screenshot skips layer3", "layer3" not in full_no_shot.layers_used)

    full = analyze(URL, full_scan=True, screenshot_png=FAKE_SCREENSHOT)
    check("full scan with screenshot runs layer3", "layer3" in full.layers_used)
    check("layer3 reports logo_check separately", "logo_check" in (full.layer3_results or {}))
    check(
        "layer3 reports banner_wording_check separately",
        "banner_wording_check" in (full.layer3_results or {}),
    )
    check(
        "phase 1 leaves the verdict unchanged by layer3",
        full.verdict == full_no_shot.verdict and full.confidence == full_no_shot.confidence,
    )

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
        sys.exit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
