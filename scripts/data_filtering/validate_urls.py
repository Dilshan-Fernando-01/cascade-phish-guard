import glob
import ipaddress
import json
import os
from urllib.parse import urlparse

import pandas as pd

openphish_single = pd.read_csv("data/raw/openphish.csv", header=None, names=["url"])
openphish_single["source"] = "openphish"

openphish_snapshot_files = glob.glob("data/raw/openphish/*.txt")
openphish_snapshots = pd.concat(
    [pd.read_csv(f, header=None, names=["url"]) for f in openphish_snapshot_files],
    ignore_index=True,
)
openphish_snapshots["source"] = "openphish"

phishtank_kaggle = pd.read_csv("data/raw/PhishTank.csv")
phishtank_kaggle = phishtank_kaggle.rename(columns={"URL": "url"})
phishtank_kaggle["source"] = "phishtank_kaggle"

phishtank_snapshot_files = glob.glob("data/raw/phishtank/*.txt")
phishtank_snapshots = pd.concat(
    [pd.read_csv(f)[["url"]] for f in phishtank_snapshot_files],
    ignore_index=True,
)
phishtank_snapshots["source"] = "phishtank"


tranco = pd.read_csv("data/raw/tranco.csv", header=None, names=["rank", "domain"])

tranco["url"] = "https://" + tranco["domain"]
tranco["source"] = "tranco"


phishing_candidates = pd.concat(
    [
        openphish_single[["url", "source"]],
        openphish_snapshots[["url", "source"]],
        phishtank_kaggle[["url", "source"]],
        phishtank_snapshots[["url", "source"]],
    ],
    ignore_index=True,
)

legitimate_candidates = tranco[["url", "source", "rank"]].copy()


MAX_URL_LENGTH = 2000
ALLOWED_SCHEMES = {"http", "https"}


def validate_url(url):

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


def apply_validation(df):
    results = df["url"].apply(validate_url)
    df = df.copy()
    df["is_valid"] = results.apply(lambda r: r[0])
    df["rejection_reason"] = results.apply(lambda r: r[1])
    return df


phishing_candidates = apply_validation(phishing_candidates)
legitimate_candidates = apply_validation(legitimate_candidates)


phishing_valid = phishing_candidates[phishing_candidates["is_valid"]]
legitimate_valid = legitimate_candidates[legitimate_candidates["is_valid"]]


os.makedirs("data/processed", exist_ok=True)
os.makedirs("data/reports", exist_ok=True)

phishing_valid[["url", "source"]].to_csv(
    "data/processed/phishing_candidates_valid.csv", index=False
)
legitimate_valid[["url", "source", "rank"]].to_csv(
    "data/processed/legitimate_candidates_valid.csv", index=False
)


def summarize(df):
    summary = {}
    for source, group in df.groupby("source"):
        total = len(group)
        valid = int(group["is_valid"].sum())
        rejected_reasons = (
            group.loc[~group["is_valid"], "rejection_reason"].value_counts().to_dict()
        )
        summary[source] = {
            "total": total,
            "valid": valid,
            "rejected": total - valid,
            "rejection_reasons": rejected_reasons,
        }
    return summary


validation_summary = {
    "phishing_candidates": summarize(phishing_candidates),
    "legitimate_candidates": summarize(legitimate_candidates),
}

with open("data/reports/validation_summary.json", "w") as f:
    json.dump(validation_summary, f, indent=2)


for label, summary in validation_summary.items():
    print(f"{label}:")
    for source, stats in summary.items():
        print(f"  {source}: total={stats['total']} valid={stats['valid']} rejected={stats['rejected']}")
        for reason, count in stats["rejection_reasons"].items():
            print(f"    - {reason}: {count}")
    print()
