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

CC_DOMAIN_POOL_TOP_N = 1_000_000
CC_DOMAIN_SAMPLE_SIZE = 6000
CC_TARGET_COUNT = 1500
CC_REQUEST_DELAY_SECONDS = 1.5


TEMPLATE_TARGET_COUNT = 4700
TEMPLATE_EXTRA_DOMAIN_SAMPLE_SIZE = 550
TEMPLATE_EXTRA_DOMAIN_POOL_TOP_N = 20_000


REAL_AUTH_TEMPLATES = {
    "accounts.google.com": [
        "/signin/v2/identifier?service=mail&continue=https%3A%2F%2Fmail.google.com%2Fmail%2F",
        "/signin/v2/challenge/pwd?TL={token}",
        "/o/oauth2/v2/auth?client_id={cid}&redirect_uri=https%3A%2F%2Fexample.com%2Fcallback&response_type=code&scope=email",
        "/ServiceLogin?service=accountsettings&continue=https%3A%2F%2Fmyaccount.google.com%2F",
    ],
    "login.microsoftonline.com": [
        "/common/oauth2/v2.0/authorize?client_id={cid}&response_type=code&redirect_uri=https%3A%2F%2Fexample.com%2Fcallback",
        "/consumers/oauth2/v2.0/authorize?client_id={cid}&scope=openid",
        "/common/login?response_type=code&client_id={cid}",
    ],
    "login.live.com": [
        "/oauth20_authorize.srf?client_id={cid}&scope=service%3A%3Aaccount.microsoft.com&response_type=code",
    ],
    "www.facebook.com": [
        "/login.php?next=https%3A%2F%2Fwww.facebook.com%2Fhome.php",
        "/v18.0/dialog/oauth?client_id={cid}&redirect_uri=https%3A%2F%2Fexample.com%2Fcallback",
    ],
    "appleid.apple.com": [
        "/auth/authorize?client_id={cid}&redirect_uri=https%3A%2F%2Fexample.com%2Fcallback&response_type=code",
        "/sign-in?widgetKey={token}",
    ],
    "www.amazon.com": [
        "/ap/signin?openid.return_to=https%3A%2F%2Fwww.amazon.com%2F&openid.pape.max_auth_age=0",
        "/ap/oa?client_id={cid}&scope=profile",
    ],
    "www.paypal.com": [
        "/signin?returnUri=https%3A%2F%2Fwww.paypal.com%2Fmyaccount%2Fsummary",
        "/connect?flowEntry=static&client_id={cid}",
    ],
    "github.com": [
        "/login?return_to=%2Fsettings%2Fprofile",
        "/login/oauth/authorize?client_id={cid}&redirect_uri=https%3A%2F%2Fexample.com%2Fcallback",
    ],
    "www.linkedin.com": [
        "/uas/login?session_redirect=%2Ffeed%2F",
        "/oauth/v2/authorization?client_id={cid}&response_type=code",
    ],
    "www.dropbox.com": [
        "/login?cont=https%3A%2F%2Fwww.dropbox.com%2Fhome",
        "/oauth2/authorize?client_id={cid}&response_type=code",
    ],
    "auth.services.adobe.com": [
        "/en_US/index.html?callback=https%3A%2F%2Fadobe.com%2Fcallback&client_id={cid}",
    ],
    "login.yahoo.com": [
        "/?.src=fp&.intl=us&.done=https%3A%2F%2Fwww.yahoo.com%2F",
    ],
    "www.netflix.com": [
        "/login?nextpage=https%3A%2F%2Fwww.netflix.com%2Fbrowse",
    ],
    "www.instagram.com": [
        "/accounts/login/?next=%2F",
    ],
    "x.com": [
        "/i/flow/login",
    ],
    "api.twitter.com": [
        "/oauth/authorize?oauth_token={token}",
    ],
    "www.chase.com": [
        "/web/auth/dashboard/",
        "/logon/#/logon/logon/chaseonline",
    ],
    "www.bankofamerica.com": [
        "/login/sign-in/signOnV2Screen.go",
    ],
    "www.wellsfargo.com": [
        "/signon/",
    ],
    "www.hsbc.com": [
        "/1/2/logon",
    ],
}
REAL_AUTH_INSTANCES_PER_TEMPLATE = 15

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

FALLBACK_CDX_API = "https://index.commoncrawl.org/CC-MAIN-2026-25-index"


def _cc_index_endpoint():
    for attempt in range(3):
        try:
            resp = requests.get(CC_COLLINFO_URL, timeout=CC_TIMEOUT)
            resp.raise_for_status()
            return resp.json()[0]["cdx-api"]  # most recent index
        except requests.exceptions.RequestException:
            if attempt < 2:
                time.sleep(3)
    print("[commoncrawl] collinfo.json unreachable after retries, using fallback index")
    return FALLBACK_CDX_API


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


def _build_real_auth_candidates():
    candidates = set()
    for hostname, templates in REAL_AUTH_TEMPLATES.items():
        for template in templates:
            for _ in range(REAL_AUTH_INSTANCES_PER_TEMPLATE):
                candidates.add(_render_template(template, hostname))
    return list(candidates)


def build_templated_urls():
    tranco = pd.read_csv(TRANCO_PATH)
    pool = tranco.sort_values("rank").head(TEMPLATE_EXTRA_DOMAIN_POOL_TOP_N)
    extra_hosts = [urlparse(u).netloc for u in pool["url"] if urlparse(u).netloc not in BRAND_DOMAINS]
    rng = random.Random(42)
    rng.shuffle(extra_hosts)
    extra_hosts = extra_hosts[:TEMPLATE_EXTRA_DOMAIN_SAMPLE_SIZE]


    real_auth_candidates = _build_real_auth_candidates()

    other_candidates = set()
    for domain in BRAND_DOMAINS:
        for template in OAUTH_TEMPLATES + GENERIC_TEMPLATES:
            other_candidates.add(_render_template(template, domain))
    for domain in extra_hosts:
        for template in GENERIC_TEMPLATES:
            other_candidates.add(_render_template(template, domain))
    other_candidates = list(other_candidates)
    rng.shuffle(other_candidates)

    all_candidates = real_auth_candidates + other_candidates

    rows = []
    seen_urls = set()
    for url in all_candidates:
        if len(rows) >= TEMPLATE_TARGET_COUNT:
            break
        if url in seen_urls:
            continue
        is_valid, _reason = validate_url(url)
        if not is_valid:
            continue
        seen_urls.add(url)
        rows.append({
            "domain": urlparse(url).netloc, "url": url,
            "source": "templated_authflow", "collected_date": COLLECTED_DATE,
        })

    out_df = pd.DataFrame(rows)
    out_df.to_csv(TEMPLATE_OUTPUT_PATH, index=False)
    real_auth_kept = sum(1 for u in real_auth_candidates if u in seen_urls)
    print(f"[templated] wrote {len(out_df)} URLs to {TEMPLATE_OUTPUT_PATH} "
          f"({real_auth_kept} from real-provider auth templates)")


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
