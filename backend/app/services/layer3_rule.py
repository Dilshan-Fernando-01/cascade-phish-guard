import re

from bs4 import BeautifulSoup


MISMATCH_LEVELS = {"closely resembles", "may be imitating"}


SUSPICIOUS_FLOOR = 0.5

CREDENTIAL_LINK_PATTERN = re.compile(
    r"log[\s-]?in|sign[\s-]?in|sign[\s-]?up|register|registration", re.IGNORECASE
)


def html_has_credential_signal(html):
    """True when the page has a password field or a sign-in / sign-up link.
    Only the structure is read. Nothing from the page is stored."""
    if not html:
        return False
    soup = BeautifulSoup(html, "html.parser")
    if soup.find("input", attrs={"type": "password"}) is not None:
        return True
    for anchor in soup.find_all("a"):
        text = anchor.get_text(" ", strip=True)
        href = anchor.get("href") or ""
        if CREDENTIAL_LINK_PATTERN.search(text) or CREDENTIAL_LINK_PATTERN.search(href):
            return True
    return False


def is_brand_mismatch(layer3_results):
    if not layer3_results or "error" in layer3_results:
        return False
    note = layer3_results.get("identity_note") or {}
    return note.get("level") in MISMATCH_LEVELS


def apply_layer3_rule(score, layer3_results, layer2_features, html):
    """Return (score, combination). combination is recorded in the response,
    so the popup and the log can say what happened."""
    mismatch = is_brand_mismatch(layer3_results)
    password_count = (layer2_features or {}).get("password_input_count") or 0
    credential = password_count > 0 or html_has_credential_signal(html)

    combination = {
        "brand_mismatch": mismatch,
        "credential_signal": credential,
        "raised": False,
        "notice": mismatch and not credential,
    }
    if mismatch and credential:
        raised = max(score, SUSPICIOUS_FLOOR)
        combination["raised"] = raised > score
        score = raised
    return score, combination
