import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

ACTIVE_MIXED_TYPES = {"script", "stylesheet", "xhr", "fetch"}
PASSIVE_MIXED_TYPES = {"image", "media", "font"}

SERVER_VERSION_PATTERN = re.compile(r"/\d")

DEBUG_TEXT_PATTERNS = [
    re.compile(r"traceback \(most recent call last\)", re.IGNORECASE),
    re.compile(r"fatal error:", re.IGNORECASE),
    re.compile(r"warning:\s+\S+\(\)", re.IGNORECASE),
    re.compile(r"exception in thread", re.IGNORECASE),
    re.compile(r"stack trace:", re.IGNORECASE),
    re.compile(r"at System\.\w+\(", re.IGNORECASE),
]

DIRECTORY_LISTING_PATTERN = re.compile(r"index of /", re.IGNORECASE)

CONSOLE_CALL_PATTERN = re.compile(r"console\.(log|debug|info)\s*\(")

INLINE_STYLE_MIN_COUNT = 10
INLINE_STYLE_MIN_RATIO = 0.10


def _check_https(page_url):
    """Foundational: a page not served over HTTPS at all offers visitors no
    transport security regardless of anything else checked here."""
    return urlparse(page_url).scheme == "https"


def _check_mixed_content(all_requests, page_url):
    """W3C Mixed Content spec (https://www.w3.org/TR/mixed-content/)"""
    if urlparse(page_url).scheme != "https":
        return {"active": [], "passive": []}
    active, passive = [], []
    for req in all_requests:
        if not req["url"].startswith("http://"):
            continue
        rtype = req["resource_type"]
        if rtype in ACTIVE_MIXED_TYPES:
            active.append(req["url"])
        elif rtype in PASSIVE_MIXED_TYPES:
            passive.append(req["url"])
    return {"active": active, "passive": passive}


def _check_security_headers(headers):
    """OWASP Secure Headers Project (https://owasp.org/www-project-secure-headers/)"""
    headers = {k.lower(): v for k, v in (headers or {}).items()}
    return {
        "hsts": "strict-transport-security" in headers,
        "csp": "content-security-policy" in headers,
        "x_content_type_options": headers.get("x-content-type-options", "").lower() == "nosniff",
        "x_frame_options": "x-frame-options" in headers
        or "frame-ancestors" in headers.get("content-security-policy", "").lower(),
        "referrer_policy": "referrer-policy" in headers,
    }


def _check_information_exposure(headers, html):
    """OWASP Top 10 - Security Misconfiguration
    (https://owasp.org/Top10/A05_2021-Security_Misconfiguration/)"""
    headers = {k.lower(): v for k, v in (headers or {}).items()}
    server = headers.get("server", "")
    text = html or ""
    return {
        "server_version_leaked": bool(SERVER_VERSION_PATTERN.search(server)),
        "x_powered_by_present": "x-powered-by" in headers,
        "debug_text_found": any(p.search(text) for p in DEBUG_TEXT_PATTERNS),
        "directory_listing": bool(DIRECTORY_LISTING_PATTERN.search(text[:2000])),
    }


def _check_inline_style_ratio(html):
    soup = BeautifulSoup(html or "", "html.parser")
    all_elements = soup.find_all(True)
    if not all_elements:
        return {"flagged": False, "inline_count": 0, "ratio": 0.0}
    inline_count = sum(1 for el in all_elements if el.has_attr("style"))
    ratio = inline_count / len(all_elements)
    flagged = inline_count > INLINE_STYLE_MIN_COUNT and ratio > INLINE_STYLE_MIN_RATIO
    return {"flagged": flagged, "inline_count": inline_count, "ratio": round(ratio, 3)}


def _check_console_logs(html):
    """ESLint's own official `no-console` rule (https://eslint.org/docs/rules/no-console)"""
    soup = BeautifulSoup(html or "", "html.parser")
    count = 0
    for tag in soup.find_all("script"):
        if tag.get("src"):
            continue
        count += len(CONSOLE_CALL_PATTERN.findall(tag.string or ""))
    return {"flagged": count > 0, "count": count}


def compute_page_quality(html, headers, all_requests, page_url):
    https = _check_https(page_url)
    mixed = _check_mixed_content(all_requests, page_url)
    sec_headers = _check_security_headers(headers)
    exposure = _check_information_exposure(headers, html)
    inline_style = _check_inline_style_ratio(html)
    console_logs = _check_console_logs(html)

    score = 100
    findings = []

    def deduct(points, flagged, label):
        nonlocal score
        if flagged:
            score -= points
            findings.append({"label": label, "points": points})

    deduct(15, not https, "Page is not served over HTTPS")
    deduct(15, bool(mixed["active"]), "Insecure (HTTP) scripts/styles loaded on an HTTPS page")
    deduct(10, not sec_headers["hsts"], "Missing HSTS header")
    deduct(10, not sec_headers["csp"], "Missing Content-Security-Policy header")
    deduct(5, bool(mixed["passive"]), "Insecure (HTTP) images/media loaded on an HTTPS page")
    deduct(5, not sec_headers["x_content_type_options"], "Missing X-Content-Type-Options header")
    deduct(5, not sec_headers["x_frame_options"], "Missing X-Frame-Options protection")
    deduct(5, not sec_headers["referrer_policy"], "Missing Referrer-Policy header")
    deduct(5, exposure["server_version_leaked"], "Server header reveals detailed version info")
    deduct(5, exposure["x_powered_by_present"], "X-Powered-By header reveals the framework used")
    deduct(10, exposure["debug_text_found"], "Debug/error output visible on the page")
    deduct(10, exposure["directory_listing"], "A directory listing is exposed")
    deduct(5, inline_style["flagged"], "Heavy use of inline styles instead of stylesheets")
    deduct(5, console_logs["flagged"], "Developer console logging left in production code")

    score = max(0, score)
    if score >= 85:
        band = "good"
    elif score >= 60:
        band = "fair"
    else:
        band = "poor"

    return {
        "score": score,
        "band": band,
        "findings": findings,
        "disclaimer": "Production-readiness context, not a phishing judgement - a page can fail these and still be legitimate, or pass them and still be unsafe.",
    }
