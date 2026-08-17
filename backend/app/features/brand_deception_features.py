import re

from bs4 import BeautifulSoup

from .brand_reference import BRAND_DOMAINS
from .dom_features import _hostname, _is_external

_OVERLAY_PATTERN = re.compile(r"position\s*:\s*fixed[^;\"']*", re.IGNORECASE)
_HIGH_ZINDEX_PATTERN = re.compile(r"z-index\s*:\s*(\d+)", re.IGNORECASE)
_HIDDEN_PATTERN = re.compile(
    r"(opacity\s*:\s*0(?:\.0*)?\b|display\s*:\s*none|visibility\s*:\s*hidden)",
    re.IGNORECASE,
)
_URL_TEXT_PATTERN = re.compile(r"https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/\S*)?")


def _all_style_text(soup):
    chunks = [tag.get("style", "") for tag in soup.find_all(style=True)]
    chunks += [tag.get_text() for tag in soup.find_all("style")]
    return chunks


def _has_icon_rel(tag):
    rel = tag.get("rel")
    if rel is None:
        return False
    if isinstance(rel, list):
        return any("icon" in r.lower() for r in rel)
    return "icon" in str(rel).lower()


def _brand_mentioned(text):
    lowered = text.lower()
    for domain in BRAND_DOMAINS:
        brand_name = domain.split(".")[0]
        if len(brand_name) >= 4 and brand_name in lowered:
            return domain
    return None


def extract_brand_features(html, final_url):
    """Extracts CPG-21's brand-mismatch and fake-overlay features."""
    soup = BeautifulSoup(html or "", "html.parser")
    page_host = _hostname(final_url)
    page_registrable = ".".join(page_host.split(".")[-2:]) if page_host else ""

    # --- Favicon domain mismatch ---
    favicon = next(
        (tag for tag in soup.find_all("link", href=True) if _has_icon_rel(tag)), None
    )
    favicon_href = favicon.get("href") if favicon else None
    favicon_domain_mismatch = int(_is_external(favicon_href, page_host))

    # --- Title / body brand mismatch ---
    title_tag = soup.find("title")
    title_text = title_tag.get_text() if title_tag else ""
    title_brand_domain = _brand_mentioned(title_text)
    title_domain_mismatch = int(bool(title_brand_domain) and title_brand_domain != page_registrable)

    body_text = soup.get_text(separator=" ", strip=True)
    body_brand_domain = _brand_mentioned(body_text)
    brand_keyword_mismatch = int(bool(body_brand_domain) and body_brand_domain != page_registrable)

    # --- Fake overlay / click-hijack pattern ---
    style_chunks = _all_style_text(soup)
    overlay_detected = 0
    css_anomaly_score = 0
    for chunk in style_chunks:
        is_fixed = bool(_OVERLAY_PATTERN.search(chunk))
        zindex_match = _HIGH_ZINDEX_PATTERN.search(chunk)
        is_high_z = bool(zindex_match) and int(zindex_match.group(1)) >= 999
        is_hidden = bool(_HIDDEN_PATTERN.search(chunk))
        if is_fixed and is_hidden:
            css_anomaly_score += 1
        if is_fixed and is_high_z and is_hidden:
            overlay_detected = 1
            css_anomaly_score += 1

    # --- Fake browser chrome ("browser-in-the-browser") heuristic ---
    fake_browser_chrome_detected = 0
    for text_node in soup.find_all(string=_URL_TEXT_PATTERN):
        parent = text_node.parent
        if parent is not None and parent.name != "a":
            fake_browser_chrome_detected = 1
            break

    return {
        "favicon_domain_mismatch": favicon_domain_mismatch,
        "title_domain_mismatch": title_domain_mismatch,
        "brand_keyword_mismatch": brand_keyword_mismatch,
        "overlay_detected": overlay_detected,
        "css_anomaly_score": css_anomaly_score,
        "fake_browser_chrome_detected": fake_browser_chrome_detected,
    }
