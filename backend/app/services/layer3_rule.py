import re

from bs4 import BeautifulSoup


MISMATCH_LEVELS = {"closely resembles", "may be imitating"}


LOW_THRESHOLD = 0.2
HIGH_THRESHOLD = 0.8

SUSPICIOUS_FLOOR = 0.5
STRONG_FLOOR = 0.7

NON_INPUT_TYPES = {"hidden", "submit", "button", "reset", "image", "checkbox", "radio"}

SIGNIN_LINK_PATTERN = re.compile(
    r"log[\s-]?in|sign[\s-]?in|sign[\s-]?up|register|registration", re.IGNORECASE
)


def html_has_user_input(html):
    """True when the page lets a visitor type or upload something, or links to a
    sign-in or sign-up area. Only the structure is read. Nothing is stored."""
    if not html:
        return False
    soup = BeautifulSoup(html, "html.parser")
    if soup.find("textarea") is not None:
        return True
    for field in soup.find_all("input"):
        if (field.get("type") or "text").lower() not in NON_INPUT_TYPES:
            return True
    for anchor in soup.find_all("a"):
        text = anchor.get_text(" ", strip=True)
        href = anchor.get("href") or ""
        if SIGNIN_LINK_PATTERN.search(text) or SIGNIN_LINK_PATTERN.search(href):
            return True
    return False


def is_brand_mismatch(layer3_results):
    if not layer3_results or "error" in layer3_results:
        return False
    note = layer3_results.get("identity_note") or {}
    return note.get("level") in MISMATCH_LEVELS


def apply_layer3_rule(score, layer3_results, layer2_features, layer2_score, html):
    """Return (score, combination). The combination is recorded in the response,
    so the popup and the log can say what happened."""
    mismatch = is_brand_mismatch(layer3_results)
    password_count = (layer2_features or {}).get("password_input_count") or 0
    input_signal = password_count > 0 or html_has_user_input(html)
    layer2_suspicious = layer2_score is not None and LOW_THRESHOLD <= layer2_score <= HIGH_THRESHOLD

    combination = {
        "brand_mismatch": mismatch,
        "input_signal": input_signal,
        "strength": "none",
        "raised": False,
        "notice": mismatch and not input_signal,
    }
    if mismatch and input_signal:
        floor = STRONG_FLOOR if layer2_suspicious else SUSPICIOUS_FLOOR
        combination["strength"] = "strong" if layer2_suspicious else "suspicious"
        raised = max(score, floor)
        combination["raised"] = raised > score
        score = raised
    return score, combination
