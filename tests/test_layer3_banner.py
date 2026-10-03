import io
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app"))
from services.layer3_analyzer import BANNER_WORDING_CHECK, analyze_layer3 

FAILURES = []


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


def make_png(lines):
    image = Image.new("RGB", (900, 120 + 70 * len(lines)), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=44)
    for i, line in enumerate(lines):
        draw.text((40, 40 + 70 * i), line, fill="black", font=font)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def main():
    phishing_like = make_png(["SECURITY ALERT", "Your account has been suspended", "VERIFY NOW", "VERIFY NOW"])
    result = analyze_layer3("https://example.com/", phishing_like)[BANNER_WORDING_CHECK]
    print(f"  phishing-like result: {result}")
    check("banner check runs on a screenshot", result["status"] == "checked")
    check("urgency phrase is matched", "security alert" in result.get("matched_phrases", []))
    check("call-to-action phrase is matched", "verify now" in result.get("matched_phrases", []))
    check("repeated call-to-action is counted as duplicate", result.get("duplicate_cta_count", 0) >= 1)
    check("score is above zero for phishing-like text", result.get("score", 0) > 0)

    ordinary = make_png(["Welcome to our gardening blog", "Read about tomatoes this week"])
    calm = analyze_layer3("https://example.com/", ordinary)[BANNER_WORDING_CHECK]
    print(f"  ordinary result: {calm}")
    check("ordinary page has no matched phrases", calm.get("matched_phrases") == [])
    check("ordinary page scores zero", calm.get("score") == 0)

    none = analyze_layer3("https://example.com/", None)[BANNER_WORDING_CHECK]
    check("no screenshot is reported, not penalized", none["status"] == "no_screenshot_provided")

    check("result never includes the full page text", "text" not in result and "raw_text" not in result)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
        sys.exit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
