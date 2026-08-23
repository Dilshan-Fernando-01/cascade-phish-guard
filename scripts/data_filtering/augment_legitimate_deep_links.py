import csv
import json
import os
import random
import sys
import time
from urllib.parse import urlparse

import pandas as pd
import requests

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend", "app"))
from features.brand_reference import BRAND_DOMAINS  
from features.url_features import validate_url  

random.seed(42)



TRANCO_PATH = "data/processed/legitimate_candidates_deduped.csv"

CC_COLLINFO_URL = "https://index.commoncrawl.org/collinfo.json"
CC_TIMEOUT = 15
CC_URLS_PER_DOMAIN = 6
CC_DOMAIN_POOL_TOP_N = 200_000
CC_DOMAIN_SAMPLE_SIZE = 900
CC_TARGET_COUNT = 3450
CC_REQUEST_DELAY_SECONDS = 0.3

TEMPLATE_TARGET_COUNT = 1475
TEMPLATE_EXTRA_DOMAIN_SAMPLE_SIZE = 300
TEMPLATE_EXTRA_DOMAIN_POOL_TOP_N = 20_000

CC_CHECKPOINT_PATH = "data/processed/legitimate_deep_links_commoncrawl_checkpoint.csv"
TEMPLATE_OUTPUT_PATH = "data/processed/legitimate_deep_links_templated.csv"
FINAL_OUTPUT_PATH = "data/processed/legitimate_deep_links.csv"
SUMMARY_PATH = "data/reports/deep_link_augmentation_summary.json"

COLLECTED_DATE = "2026-08-23"

CHECKPOINT_FIELDNAMES = ["domain", "url", "source", "collected_date"]

OAUTH_TEMPLATES = [
    "/oauth/authorize?client_id={cid}&redirect_uri=https%3A%2F%2F{domain}%2Fcallback&response_type=code&state={state}",
    "/saml/sso?SAMLRequest={token}&RelayState={state}",
]

GENERIC_TEMPLATES = [
    "/login",
    "/signin",
    "/account/login",
    "/account/settings",
    "/account/security",
    "/password/reset?token={token}",
    "/verify-email?token={token}",
    "/checkout",
    "/checkout/payment",
    "/cart",
    "/search?q={query}",
    "/dashboard",
    "/orders/confirmation?order_id={order_id}",
    "/two-factor/verify",
]

QUERY_WORDS = ["order status", "reset password", "help center", "billing", "invoice", "support"]


def _random_token(length=24):
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(random.choice(alphabet) for _ in range(length))


def _render_template(template, domain):
    path = template.format(
        domain=domain,
        cid=_random_token(16),
        state=_random_token(12),
        token=_random_token(32),
        query=random.choice(QUERY_WORDS).replace(" ", "+"),
        order_id=random.randint(100000, 999999),
    )
    return f"https://{domain}{path}"


# --- Source A: Common Crawl organic deep links ---------------------------

def _cc_index_endpoint():
    resp = requests.get(CC_COLLINFO_URL, timeout=CC_TIMEOUT)
    resp.raise_for_status()
    return resp.json()[0]["cdx-api"]  # most recent index


NON_CONTENT_PATH_SUFFIXES = (
    "/robots.txt", "/sitemap.xml", "/favicon.ico", "/ads.txt", "/humans.txt",
    ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2",
)


def _is_content_url(url):
    lowered = url.lower()
    return not any(lowered.endswith(suffix) for suffix in NON_CONTENT_PATH_SUFFIXES)


def _query_common_crawl(cdx_api, domain, limit=CC_URLS_PER_DOMAIN):
    try:
        resp = requests.get(
            cdx_api,
            params={"url": f"{domain}/*", "output": "json", "limit": limit * 5},
            timeout=CC_TIMEOUT,
        )
        if resp.status_code != 200:
            return []
    except requests.exceptions.RequestException:
        return []

    urls = {}
    for line in resp.text.strip().split("\n"):
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        url = record.get("url", "")
        if not _is_content_url(url):
            continue
        parsed = urlparse(url)
        if not parsed.path or parsed.path == "/":
            continue
        dedup_key = (parsed.path, parsed.query)
        urls.setdefault(dedup_key, url)
    return list(urls.values())[:limit]


def _load_cc_progress():
    if not os.path.exists(CC_CHECKPOINT_PATH):
        return set(), 0
    done = pd.read_csv(CC_CHECKPOINT_PATH)
    return set(done["domain"]), len(done)


def build_common_crawl_urls():
    tranco = pd.read_csv(TRANCO_PATH)
    pool = tranco.sort_values("rank").head(CC_DOMAIN_POOL_TOP_N)
    hosts = [urlparse(u).netloc for u in pool["url"]]

    already_queried, already_collected = _load_cc_progress()
    print(f"[commoncrawl] {already_collected} URLs from {len(already_queried)} domains already done")

    if already_collected >= CC_TARGET_COUNT:
        print("[commoncrawl] target already reached, skipping")
        return

    rng = random.Random(42)
    shuffled_hosts = hosts[:]
    rng.shuffle(shuffled_hosts)
    remaining_hosts = [h for h in shuffled_hosts if h not in already_queried][:CC_DOMAIN_SAMPLE_SIZE]

    if not remaining_hosts:
        print("[commoncrawl] no more domains left to sample")
        return

    cdx_api = _cc_index_endpoint()
    print(f"[commoncrawl] using index {cdx_api}")

    file_exists = os.path.exists(CC_CHECKPOINT_PATH)
    collected = already_collected
    with open(CC_CHECKPOINT_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CHECKPOINT_FIELDNAMES)
        if not file_exists:
            writer.writeheader()

        for i, host in enumerate(remaining_hosts):
            urls = _query_common_crawl(cdx_api, host)
            for url in urls:
                is_valid, _reason = validate_url(url)
                if not is_valid:
                    continue
                writer.writerow({
                    "domain": host, "url": url,
                    "source": "commoncrawl", "collected_date": COLLECTED_DATE,
                })
                collected += 1
            if not urls:
                writer.writerow({"domain": host, "url": "", "source": "commoncrawl", "collected_date": COLLECTED_DATE})
            f.flush()

            if (i + 1) % 25 == 0:
                print(f"[commoncrawl] {i + 1}/{len(remaining_hosts)} domains queried, {collected} URLs collected so far")
            if collected >= CC_TARGET_COUNT:
                print(f"[commoncrawl] target of {CC_TARGET_COUNT} reached")
                break

            time.sleep(CC_REQUEST_DELAY_SECONDS)


def build_templated_urls():
    tranco = pd.read_csv(TRANCO_PATH)
    pool = tranco.sort_values("rank").head(TEMPLATE_EXTRA_DOMAIN_POOL_TOP_N)
    extra_hosts = [urlparse(u).netloc for u in pool["url"] if urlparse(u).netloc not in BRAND_DOMAINS]
    rng = random.Random(42)
    rng.shuffle(extra_hosts)
    extra_hosts = extra_hosts[:TEMPLATE_EXTRA_DOMAIN_SAMPLE_SIZE]

    candidates = set()
    for domain in BRAND_DOMAINS:
        for template in OAUTH_TEMPLATES + GENERIC_TEMPLATES:
            candidates.add(_render_template(template, domain))
    for domain in extra_hosts:
        for template in GENERIC_TEMPLATES:
            candidates.add(_render_template(template, domain))

    candidates = list(candidates)
    rng.shuffle(candidates)

    rows = []
    for url in candidates:
        if len(rows) >= TEMPLATE_TARGET_COUNT:
            break
        is_valid, _reason = validate_url(url)
        if not is_valid:
            continue
        rows.append({
            "domain": urlparse(url).netloc, "url": url,
            "source": "templated_authflow", "collected_date": COLLECTED_DATE,
        })

    out_df = pd.DataFrame(rows)
    out_df.to_csv(TEMPLATE_OUTPUT_PATH, index=False)
    print(f"[templated] wrote {len(out_df)} URLs to {TEMPLATE_OUTPUT_PATH}")


def combine_final_output():
    frames = []
    if os.path.exists(CC_CHECKPOINT_PATH):
        cc = pd.read_csv(CC_CHECKPOINT_PATH)
        cc = cc[cc["url"].notna() & (cc["url"] != "")]
        frames.append(cc[["url", "source", "collected_date"]])
    if os.path.exists(TEMPLATE_OUTPUT_PATH):
        templated = pd.read_csv(TEMPLATE_OUTPUT_PATH)
        frames.append(templated[["url", "source", "collected_date"]])

    if not frames:
        print("no sources produced output yet")
        return {"total": 0}

    combined = pd.concat(frames, ignore_index=True).drop_duplicates(subset="url")
    combined.to_csv(FINAL_OUTPUT_PATH, index=False)

    summary = {
        "total": len(combined),
        "by_source": combined["source"].value_counts().to_dict(),
    }
    with open(SUMMARY_PATH, "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))
    return summary


def main():
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("data/reports", exist_ok=True)

    build_common_crawl_urls()
    build_templated_urls()
    combine_final_output()


if __name__ == "__main__":
    main()
