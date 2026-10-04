import csv
import os
import sys
from urllib.parse import urlparse

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend", "app"))
from features.url_features import _is_shared_hosting  # noqa: E402

TRANCO_PATH = "data/raw/tranco.csv"
PHISHING_PATH = "data/processed/phishing_candidates_dual_confirmed.csv"
OUTPUT_PATH = "data/layer3/legit_domains.csv"
TOP_RANKS_TO_CONSIDER = 3000
CANDIDATES_TO_KEEP = 1500


def main():
    tranco = pd.read_csv(TRANCO_PATH, header=None, names=["rank", "domain"]).head(TOP_RANKS_TO_CONSIDER)

    phishing_hosts = set(
        urlparse(str(u)).netloc.lower().split(":")[0]
        for u in pd.read_csv(PHISHING_PATH)["url"]
    )

    kept = []
    for _, row in tranco.iterrows():
        domain = str(row["domain"]).lower()
        if domain in phishing_hosts:
            continue
        if _is_shared_hosting(domain):
            continue
        kept.append((int(row["rank"]), domain))
        if len(kept) >= CANDIDATES_TO_KEEP:
            break

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "domain"])
        writer.writerows(kept)

    print(f"wrote {len(kept)} candidate legitimate domains to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
