import json
import os
from urllib.parse import urlparse, urlunparse

import pandas as pd


def normalize_url(url):
    parsed = urlparse(str(url))
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    return urlunparse((scheme, netloc, path, parsed.params, parsed.query, parsed.fragment))


def deduplicate_with_report(df):
    df = df.copy()
    df["normalized_url"] = df["url"].apply(normalize_url)

    total_before = len(df)
    total_before_by_source = df["source"].value_counts().to_dict()

   
    is_duplicate_row = df.duplicated(subset="normalized_url", keep="first")
    removed_by_source = df.loc[is_duplicate_row, "source"].value_counts().to_dict()

    merged_sources = (
        df.groupby("normalized_url")["source"]
        .apply(lambda s: ",".join(sorted(set(s))))
    )

    deduped = df.drop_duplicates(subset="normalized_url", keep="first").set_index("normalized_url")
    deduped["source"] = merged_sources
    deduped = deduped.reset_index(drop=True)

    report = {
        "total_before": total_before,
        "total_after": len(deduped),
        "duplicates_removed": total_before - len(deduped),
        "total_before_by_source": total_before_by_source,
        "removed_by_source": removed_by_source,
    }

    return deduped, report


phishing_candidates = pd.read_csv("data/processed/phishing_candidates_valid.csv")
legitimate_candidates = pd.read_csv("data/processed/legitimate_candidates_valid.csv")

phishing_deduped, phishing_report = deduplicate_with_report(phishing_candidates)
legitimate_deduped, legitimate_report = deduplicate_with_report(legitimate_candidates)

os.makedirs("data/processed", exist_ok=True)
os.makedirs("data/reports", exist_ok=True)

phishing_deduped[["url", "source"]].to_csv(
    "data/processed/phishing_candidates_deduped.csv", index=False
)
legitimate_deduped[["url", "source", "rank"]].to_csv(
    "data/processed/legitimate_candidates_deduped.csv", index=False
)

deduplication_summary = {
    "phishing_candidates": phishing_report,
    "legitimate_candidates": legitimate_report,
}

with open("data/reports/deduplication_summary.json", "w") as f:
    json.dump(deduplication_summary, f, indent=2)

for label, report in deduplication_summary.items():
    print(f"{label}:")
    print(
        f"  total_before={report['total_before']} "
        f"total_after={report['total_after']} "
        f"duplicates_removed={report['duplicates_removed']}"
    )
    print(f"  removed_by_source={report['removed_by_source']}")
    print()


multi_source = phishing_deduped[phishing_deduped["source"].str.contains(",")]
print("Phishing URLs seen in more than one source (dual-source overlap preview):")
print(multi_source["source"].value_counts())
