import ipaddress
import json
import math
import os
from collections import Counter
from urllib.parse import urlparse

import pandas as pd

SUSPICIOUS_KEYWORDS = {"login", "verify", "secure", "update", "account"}
SPECIAL_CHARS = set("-_@%=?&")


def shannon_entropy(s):
    if not s:
        return 0.0
    counts = Counter(s)
    length = len(s)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())


def extract_features(url):
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
        "has_ip_host": int(is_ip),
        "has_at_symbol": int("@" in url),
        "path_depth": len([p for p in parsed.path.split("/") if p]),
        "query_param_count": len(parsed.query.split("&")) if parsed.query else 0,
        "digit_ratio": (sum(c.isdigit() for c in url) / len(url)) if url else 0.0,
        "is_punycode": int("xn--" in host),
    }


def check_extractable(url):
    try:
        extract_features(str(url))
        return True, None
    except Exception as exc:
        return False, type(exc).__name__


def apply_check(df):
    results = df["url"].apply(check_extractable)
    df = df.copy()
    df["is_extractable"] = results.apply(lambda r: r[0])
    df["extraction_error"] = results.apply(lambda r: r[1])
    return df


def summarize(df):
    return {
        "total": len(df),
        "extractable": int(df["is_extractable"].sum()),
        "failed": int((~df["is_extractable"]).sum()),
        "error_breakdown": df.loc[~df["is_extractable"], "extraction_error"].value_counts().to_dict(),
    }


def main():
    phishing = pd.read_csv("data/processed/phishing_candidates_reachable.csv")
    legitimate = pd.read_csv("data/processed/legitimate_candidates_valid.csv")

    phishing = apply_check(phishing)
    legitimate = apply_check(legitimate)

    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("data/reports", exist_ok=True)

    phishing[phishing["is_extractable"]].drop(columns=["is_extractable", "extraction_error"]).to_csv(
        "data/processed/phishing_candidates_extractable.csv", index=False
    )
    legitimate[legitimate["is_extractable"]].drop(columns=["is_extractable", "extraction_error"]).to_csv(
        "data/processed/legitimate_candidates_extractable.csv", index=False
    )

    summary = {
        "phishing_candidates": summarize(phishing),
        "legitimate_candidates": summarize(legitimate),
        "note": (
            "Only cheap, string-only Layer 1 features tested (no network calls). "
            "domain_age_days, tranco_rank_bucket, and brand_distance_score are "
            "excluded -- they require Phase 4 infrastructure not yet built."
        ),
    }

    with open("data/reports/feature_extractability_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
