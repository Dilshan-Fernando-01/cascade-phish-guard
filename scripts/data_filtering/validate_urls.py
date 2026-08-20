import glob
import json
import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend", "app"))
from features.url_features import validate_url  


OPENPHISH_SINGLE_DATE = "2026-07-22"
TRANCO_DATE = "2026-07-22"


def load_openphish_snapshot_dates():
    """Maps each snapshot filename to its real collection date, from the
    manifest OpenPhish's own collection script already writes."""
    with open("data/raw/openphish/manifest.json") as f:
        manifest = json.load(f)
    dates = {}
    for entry in manifest:
        timestamp = datetime.strptime(entry["timestamp"], "%Y%m%dT%H%M%SZ")
        dates[entry["file"]] = timestamp.date().isoformat()
    return dates


openphish_single = pd.read_csv("data/raw/openphish.csv", header=None, names=["url"])
openphish_single["source"] = "openphish"
openphish_single["collected_date"] = OPENPHISH_SINGLE_DATE

openphish_snapshot_dates = load_openphish_snapshot_dates()
openphish_snapshot_files = glob.glob("data/raw/openphish/*.txt")
openphish_snapshot_frames = []
for f in openphish_snapshot_files:
    frame = pd.read_csv(f, header=None, names=["url"])
    frame["collected_date"] = openphish_snapshot_dates.get(os.path.basename(f))
    openphish_snapshot_frames.append(frame)
openphish_snapshots = pd.concat(openphish_snapshot_frames, ignore_index=True)
openphish_snapshots["source"] = "openphish"

phishtank_kaggle = pd.read_csv("data/raw/PhishTank.csv")
phishtank_kaggle = phishtank_kaggle.rename(columns={"URL": "url"})
phishtank_kaggle["source"] = "phishtank_kaggle"
phishtank_kaggle["collected_date"] = pd.NA

phishtank_snapshot_files = glob.glob("data/raw/phishtank/*.txt")
phishtank_snapshot_frames = []
for f in phishtank_snapshot_files:

    frame = pd.read_csv(f, usecols=["url", "submission_time"])
    frame["collected_date"] = pd.to_datetime(frame["submission_time"], errors="coerce", utc=True).dt.date
    phishtank_snapshot_frames.append(frame[["url", "collected_date"]])
phishtank_snapshots = pd.concat(phishtank_snapshot_frames, ignore_index=True)
phishtank_snapshots["source"] = "phishtank"


tranco = pd.read_csv("data/raw/tranco.csv", header=None, names=["rank", "domain"])

tranco["url"] = "https://" + tranco["domain"]
tranco["source"] = "tranco"
tranco["collected_date"] = TRANCO_DATE


phishing_candidates = pd.concat(
    [
        openphish_single[["url", "source", "collected_date"]],
        openphish_snapshots[["url", "source", "collected_date"]],
        phishtank_kaggle[["url", "source", "collected_date"]],
        phishtank_snapshots[["url", "source", "collected_date"]],
    ],
    ignore_index=True,
)

legitimate_candidates = tranco[["url", "source", "rank", "collected_date"]].copy()


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

phishing_valid[["url", "source", "collected_date"]].to_csv(
    "data/processed/phishing_candidates_valid.csv", index=False
)
legitimate_valid[["url", "source", "rank", "collected_date"]].to_csv(
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
        undated = int(group["collected_date"].isna().sum())
        summary[source] = {
            "total": total,
            "valid": valid,
            "rejected": total - valid,
            "rejection_reasons": rejected_reasons,
            "undated": undated,
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
        print(
            f"  {source}: total={stats['total']} valid={stats['valid']} "
            f"rejected={stats['rejected']} undated={stats['undated']}"
        )
        for reason, count in stats["rejection_reasons"].items():
            print(f"    - {reason}: {count}")
    print()
