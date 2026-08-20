import json
import os
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd


MATCH_MODE = "domain"


PHISHTANK_GROUP = {"phishtank", "phishtank_kaggle"}


def source_groups(source_field):
    sources = set(source_field.split(","))
    groups = set()
    if "openphish" in sources:
        groups.add("openphish")
    if sources & PHISHTANK_GROUP:
        groups.add("phishtank")
    return groups


def domain_of(url):
    return urlparse(str(url)).netloc.lower().split(":")[0]


phishing_candidates = pd.read_csv("data/processed/phishing_candidates_deduped.csv")
phishing_candidates["domain"] = phishing_candidates["url"].apply(domain_of)
phishing_candidates["source_groups"] = phishing_candidates["source"].apply(source_groups)

total_candidates = len(phishing_candidates)


exact_match_mask = phishing_candidates["source_groups"].apply(
    lambda g: {"openphish", "phishtank"} <= g
)
exact_match_count = int(exact_match_mask.sum())

domain_groups = phishing_candidates.groupby("domain")["source_groups"].apply(
    lambda series: set().union(*series)
)
dual_domains = set(domain_groups[domain_groups.apply(lambda g: {"openphish", "phishtank"} <= g)].index)
domain_match_mask = phishing_candidates["domain"].isin(dual_domains)
domain_match_count = int(domain_match_mask.sum())

feed_match_mask = domain_match_mask if MATCH_MODE == "domain" else exact_match_mask


manual_log_path = Path("temp/manual_verification_log.csv")
if manual_log_path.exists():
    manual_log = pd.read_csv(manual_log_path)
    manual_confirmed_urls = set(
        manual_log.loc[manual_log["decision"] == "CONFIRMED PHISHING", "url"]
    )
else:
    manual_confirmed_urls = set()

manual_match_mask = phishing_candidates["url"].isin(manual_confirmed_urls)
manual_match_count = int(manual_match_mask.sum())


confirmed_mask = feed_match_mask | manual_match_mask
confirmed = phishing_candidates[confirmed_mask].copy()

confirmed["confirmation_method"] = [
    ",".join(
        ([f"feed_{MATCH_MODE}"] if f else []) + (["manual"] if m else [])
    )
    for f, m in zip(feed_match_mask[confirmed_mask], manual_match_mask[confirmed_mask])
]

os.makedirs("data/processed", exist_ok=True)
os.makedirs("data/reports", exist_ok=True)

confirmed[["url", "source", "collected_date", "confirmation_method"]].to_csv(
    "data/processed/phishing_candidates_dual_confirmed.csv", index=False
)

overlap_feed_and_manual = int((feed_match_mask & manual_match_mask).sum())

summary = {
    "match_mode": MATCH_MODE,
    "total_candidates": total_candidates,
    "exact_url_agreement_count": exact_match_count,
    "domain_level_agreement_count": domain_match_count,
    "manual_verification_count": manual_match_count,
    "overlap_between_feed_and_manual": overlap_feed_and_manual,
    "final_confirmed_count": len(confirmed),
    "agreement_rate_exact": exact_match_count / total_candidates if total_candidates else 0,
    "agreement_rate_domain": domain_match_count / total_candidates if total_candidates else 0,
}

with open("data/reports/dual_source_agreement_summary.json", "w") as f:
    json.dump(summary, f, indent=2)

print(json.dumps(summary, indent=2))
