import os
import sys

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app"))
from features.dom_features import duplicate_button_text_count, extract_structural_features  # noqa: E402

FAILURES = []


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


def count_for(html):
    return duplicate_button_text_count(BeautifulSoup(html, "html.parser"))


def main():
    duplicate_html = """
        <html><body>
            <button>Verify Now</button>
            <a href="/x">verify now</a>
            <input type="submit" value="VERIFY NOW">
        </body></html>
    """
    check("duplicate CTA text across button/a/input counted correctly", count_for(duplicate_html) == 2)

   
    distinct_html = """
        <html><body>
            <button>Submit</button>
            <a href="/x">Learn More</a>
            <input type="submit" value="Continue">
        </body></html>
    """
    check("distinct button text is never falsely flagged as duplicate", count_for(distinct_html) == 0)

    icon_html = """
        <html><body>
            <button>&gt;</button>
            <button>&gt;</button>
            <a href="/x"></a>
        </body></html>
    """
    check("trivially short/icon-only button text is ignored", count_for(icon_html) == 0)

    two_groups_html = """
        <html><body>
            <button>Download Now</button>
            <button>Download Now</button>
            <a href="/x">Click Here</a>
            <a href="/y">Click Here</a>
        </body></html>
    """
    check("multiple independent duplicate groups are all counted", count_for(two_groups_html) == 2)

    features = extract_structural_features(duplicate_html, "https://example.com/")
    check("extract_structural_features includes the new field", "duplicate_button_text_count" in features)
    check("extract_structural_features new field value is correct", features["duplicate_button_text_count"] == 2)
    check(
        "extract_structural_features still returns all prior fields",
        {"form_count", "password_input_count", "dom_tree_depth"} <= features.keys(),
    )

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
        sys.exit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
