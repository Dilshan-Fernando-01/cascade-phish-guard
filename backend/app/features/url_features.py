import concurrent.futures
import ipaddress
import math
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests
import tldextract
from rapidfuzz.distance import Levenshtein

from .brand_reference import BRAND_DOMAINS

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


def extract_basic_features(url):

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


_TRANCO_PATH = Path(__file__).resolve().parents[3] / "data" / "raw" / "tranco.csv"
_tranco_lookup = None


def _load_tranco():
    global _tranco_lookup
    if _tranco_lookup is None:
        df = pd.read_csv(_TRANCO_PATH, header=None, names=["rank", "domain"])
        _tranco_lookup = dict(zip(df["domain"], df["rank"]))
    return _tranco_lookup


_icann_extract = tldextract.TLDExtract(include_psl_private_domains=False)
_private_extract = tldextract.TLDExtract(include_psl_private_domains=True)

KNOWN_SHARED_HOSTS_NOT_IN_PSL = {
    "000webhostapp.com", "contabostorage.com", "did.li", "dweb.link",
    "ead.me", "edgeone.dev", "glitch.me", "ipfs.io", "qrco.de",
    "rebrand.ly", "s4w.in", "sites.google.com", "surge.sh", "surl.li",
    "tinyurl.com", "tr.ee", "webcindario.com", "weebly.com", "weeblysite.com",
}


def _is_shared_hosting(host):
    if _private_extract(host).suffix != _icann_extract(host).suffix:
        return True
    return any(
        host == suffix or host.endswith("." + suffix)
        for suffix in KNOWN_SHARED_HOSTS_NOT_IN_PSL
    )


def tranco_rank_bucket(host):
    if _is_shared_hosting(host):

        return 0

    lookup = _load_tranco()
    rank = lookup.get(host)
    if rank is None:
        rank = lookup.get(_registrable_domain_guess(host))
    if rank is None:
        return 0
    if rank <= 1000:
        return 5
    if rank <= 10000:
        return 4
    if rank <= 100000:
        return 3
    if rank <= 500000:
        return 2
    return 1


def _registrable_domain_guess(host):
    return _icann_extract(host).registered_domain or host


def brand_distance_score(host):

    candidate = _registrable_domain_guess(host)
    return min(Levenshtein.distance(candidate, brand) for brand in BRAND_DOMAINS)


def brand_keyword_in_host(host):
 
    registrable = _registrable_domain_guess(host)
    for brand in BRAND_DOMAINS:
        brand_name = brand.split(".")[0]
        if len(brand_name) >= 4 and brand_name in host and registrable != brand:
            return 1
    return 0


def domain_age_days(host):
    if _is_shared_hosting(host):

        return None

    
    try:
        resp = requests.get(f"https://rdap.org/domain/{host}", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            for event in data.get("events", []):
                if event.get("eventAction") == "registration":
                    reg_date = datetime.fromisoformat(event["eventDate"].replace("Z", "+00:00"))
                    return (datetime.now(timezone.utc) - reg_date).days
    except Exception:
        pass

    try:
        import whois

        w = whois.whois(host, timeout=5)
        creation = w.creation_date
        if isinstance(creation, list):
            creation = creation[0]
        if creation:
            if creation.tzinfo is None:
                creation = creation.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - creation).days
    except Exception:
        pass

    return None


def extract_all_features(url):

    url = str(url)
    host = urlparse(url).netloc.split(":")[0]

    features = extract_basic_features(url)
    features["tranco_rank_bucket"] = tranco_rank_bucket(host)
    features["brand_distance_score"] = brand_distance_score(host)
    features["brand_keyword_in_host"] = brand_keyword_in_host(host)
    features["domain_age_days"] = domain_age_days(host)
    return features


def _domain_features(host):
    return {
        "tranco_rank_bucket": tranco_rank_bucket(host),
        "brand_distance_score": brand_distance_score(host),
        "brand_keyword_in_host": brand_keyword_in_host(host),
        "domain_age_days": domain_age_days(host),
    }


def extract_features_batch(urls, max_workers=15):
    hosts = []
    seen = set()
    for url in urls:
        host = urlparse(str(url)).netloc.split(":")[0]
        if host not in seen:
            seen.add(host)
            hosts.append(host)

    domain_cache = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_host = {executor.submit(_domain_features, host): host for host in hosts}
        for future in concurrent.futures.as_completed(future_to_host):
            host = future_to_host[future]
            try:
                domain_cache[host] = future.result()
            except Exception:
                domain_cache[host] = {
                    "tranco_rank_bucket": None,
                    "brand_distance_score": None,
                    "brand_keyword_in_host": None,
                    "domain_age_days": None,
                }

    results = []
    for url in urls:
        try:
            url = str(url)
            host = urlparse(url).netloc.split(":")[0]
            features = extract_basic_features(url)
            features.update(domain_cache[host])
            results.append((features, None))
        except Exception as exc:
            results.append((None, f"{type(exc).__name__}: {exc}"))
    return results



FEATURE_COLUMNS = [
    "url_length", "subdomain_count", "has_https", "special_char_count",
    "keyword_score", "character_entropy", "tld_risk_score", "has_ip_host",
    "has_at_symbol", "path_depth", "query_param_count", "digit_ratio",
    "is_punycode_or_homograph", "tranco_rank_bucket", "brand_distance_score",
    "brand_keyword_in_host", "domain_age_days",
]


def prepare_features(df, median_domain_age):

    X = df[FEATURE_COLUMNS].copy()
    X["domain_age_missing"] = X["domain_age_days"].isna().astype(int)
    X["domain_age_days"] = X["domain_age_days"].fillna(median_domain_age)
    return X




MAX_URL_LENGTH = 2000
ALLOWED_SCHEMES = {"http", "https"}


def validate_url(url):
    """Returns (is_valid, rejection_reason)."""
    if pd.isna(url) or not str(url).strip():
        return False, "empty"

    url = str(url).strip()

    if len(url) > MAX_URL_LENGTH:
        return False, "too_long"

    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        return False, "invalid_scheme"

    host = parsed.netloc.split(":")[0]
    if not host:
        return False, "missing_domain"

    try:
        ipaddress.ip_address(host)
        is_ip = True
    except ValueError:
        is_ip = False

    if not is_ip and "." not in host:
        return False, "malformed_domain"

    return True, None
