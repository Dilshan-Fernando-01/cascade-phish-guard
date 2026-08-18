import re

from bs4 import BeautifulSoup

_OBFUSCATION_PATTERNS = [
    re.compile(r"\beval\s*\(", re.IGNORECASE),
    re.compile(r"\batob\s*\(", re.IGNORECASE),
    re.compile(r"fromCharCode\s*\(", re.IGNORECASE),
    re.compile(r"\bunescape\s*\(", re.IGNORECASE),
]

_JS_PATTERNS = [
    re.compile(r"window\.location", re.IGNORECASE),
    re.compile(r"location\.(href|replace|assign)\s*[=(]", re.IGNORECASE),
    re.compile(r"setTimeout\s*\(", re.IGNORECASE),
    re.compile(r"document\.write\s*\(", re.IGNORECASE),
]

_URGENCY_PHRASES = [
    "verify your account", "verify immediately", "account suspended",
    "account has been suspended", "will be suspended", "unusual activity",
    "confirm your identity", "urgent action required",
    "immediate action required", "account will be locked",
    "account will be closed", "limited time", "act now",
    "click here immediately", "security alert", "unauthorized access",
    "expires today", "expiring soon", "verify now", "action required",
]


def _inline_script_text(soup):
    return " ".join(
        tag.get_text() for tag in soup.find_all("script") if not tag.get("src")
    )


def extract_behavioral_features(html):
    """Extracts CPG-22's behavioral features from raw page HTML."""
    soup = BeautifulSoup(html or "", "html.parser")
    script_text = _inline_script_text(soup)
    visible_text = soup.get_text(separator=" ", strip=True).lower()

    script_obfuscation_score = sum(
        len(pattern.findall(script_text)) for pattern in _OBFUSCATION_PATTERNS
    )
    suspicious_js_pattern_count = sum(
        len(pattern.findall(script_text)) for pattern in _JS_PATTERNS
    )
    social_engineering_score = sum(
        visible_text.count(phrase) for phrase in _URGENCY_PHRASES
    )

    return {
        "script_obfuscation_score": script_obfuscation_score,
        "suspicious_js_pattern_count": suspicious_js_pattern_count,
        "social_engineering_score": social_engineering_score,
    }
