import ipaddress
import math
import unicodedata
from collections import Counter
from urllib.parse import urlparse

SUSPICIOUS_KEYWORDS = {"login", "verify", "secure", "update", "account"}
SPECIAL_CHARS = set("-_@%=?&")


HIGH_RISK_TLDS = {
    "tk", "ml", "ga", "cf", "gq", "xyz", "top", "club", "work",
    "click", "loan", "men", "date", "racing", "review", "win", "bid", "stream",
}
LOW_RISK_TLDS = {"com", "org", "net", "edu", "gov"}


def shannon_entropy(s):
    if not s:
        return 0.0
    counts = Counter(s)
    length = len(s)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())


def tld_risk_score(host):
    tld = host.rsplit(".", 1)[-1].lower() if "." in host else ""
    if tld in HIGH_RISK_TLDS:
        return 1.0
    if tld in LOW_RISK_TLDS:
        return 0.0
    return 0.5


def _decode_punycode_label(label):
    if label.startswith("xn--"):
        try:
            return label.encode("ascii").decode("idna")
        except Exception:
            return label
    return label


def _label_script_names(label):
    
    scripts = set()
    for ch in label:
        if ch.isalpha():
            try:
                scripts.add(unicodedata.name(ch).split()[0])
            except ValueError:
                pass
    return scripts


def punycode_homograph_flag(host):
    labels = host.split(".")
    is_punycode = any(label.startswith("xn--") for label in labels)
    mixed_script = any(len(_label_script_names(_decode_punycode_label(label))) > 1 for label in labels)
    return int(is_punycode or mixed_script)


def extract_features(url):
    url = str(url)
    parsed = urlparse(url)
    host = parsed.netloc.split(":")[0]

    try:
        ipaddress.ip_address(host)
        is_ip = True
    except ValueError:
        is_ip = False

    return {
        "url_length": len(url),
        "subdomain_count": host.count("."),
        "has_https": int(parsed.scheme == "https"),
        "special_char_count": sum(1 for c in url if c in SPECIAL_CHARS),
        "keyword_score": sum(1 for kw in SUSPICIOUS_KEYWORDS if kw in url.lower()),
        "character_entropy": shannon_entropy(url),
        "tld_risk_score": tld_risk_score(host),
        "has_ip_host": int(is_ip),
        "has_at_symbol": int("@" in url),
        "path_depth": len([p for p in parsed.path.split("/") if p]),
        "query_param_count": len(parsed.query.split("&")) if parsed.query else 0,
        "digit_ratio": (sum(c.isdigit() for c in url) / len(url)) if url else 0.0,
        "is_punycode_or_homograph": punycode_homograph_flag(host),
    }
