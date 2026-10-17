import argparse
import base64
import json
import os
import time
from datetime import datetime, timezone

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

TARGET_SAMPLE_SIZE = 500
RANDOM_SEED = 42
SECONDS_BETWEEN_REQUESTS = 16  

POOL_PATH = "data/processed/layer1_test_features.csv"
SAMPLE_PATH = "data/processed/virustotal_legit_sample.csv"
SAMPLE_COLUMNS = ["url", "vt_submitted", "vt_result", "vt_checked_at", "vt_stats", "vt_categories"]

API_KEY = os.environ.get("VIRUSTOTAL_API_KEY")


def url_id(url):
    return base64.urlsafe_b64encode(url.encode()).decode().strip("=")


def lookup(url):
    headers = {"x-apikey": API_KEY}
    resp = requests.get(
        f"https://www.virustotal.com/api/v3/urls/{url_id(url)}",
        headers=headers,
        timeout=30,
    )
    if resp.status_code == 200:
        attrs = resp.json()["data"]["attributes"]
        stats = attrs["last_analysis_stats"]
        results = attrs.get("last_analysis_results", {})

        flagged_by = {
            engine: r.get("result")
            for engine, r in results.items()
            if r.get("category") in ("malicious", "suspicious")
        }
        flagged = stats.get("malicious", 0) + stats.get("suspicious", 0)
        return ("malicious" if flagged > 0 else "clean"), stats, flagged_by
    if resp.status_code == 404:
        return "not_found", None, None
    return f"error_{resp.status_code}", None, None


def prepare_sample():
    pool = pd.read_csv(POOL_PATH)
    pool = pool[pool["label"] == 0]
    pool_size = len(pool)

    if os.path.exists(SAMPLE_PATH):
        existing = pd.read_csv(SAMPLE_PATH)
    else:
        existing = pd.DataFrame(columns=SAMPLE_COLUMNS)

    remaining_pool = pool[~pool["url"].isin(set(existing["url"]))]
    additional_needed = min(max(0, TARGET_SAMPLE_SIZE - len(existing)), len(remaining_pool))

    if additional_needed > 0:
        new_rows = remaining_pool.sample(n=additional_needed, random_state=RANDOM_SEED)[["url"]].copy()
        new_rows["vt_submitted"] = False
        new_rows["vt_result"] = None
        new_rows["vt_checked_at"] = None
        sample = pd.concat([existing, new_rows], ignore_index=True)
    else:
        sample = existing

    sample = sample.reindex(columns=SAMPLE_COLUMNS)
    os.makedirs("data/processed", exist_ok=True)
    sample.to_csv(SAMPLE_PATH, index=False)
    print(f"legitimate URL pool (held-out test set): {pool_size}")
    print(f"sample prepared: {len(sample)} rows -> {SAMPLE_PATH}")


def evaluate():
    if not API_KEY:
        raise SystemExit("VIRUSTOTAL_API_KEY not set")
    sample = pd.read_csv(SAMPLE_PATH)

    for idx, row in sample.iterrows():
        result_so_far = str(row.get("vt_result") or "")
        if bool(row.get("vt_submitted")) and not result_so_far.startswith("error_"):
            continue
        result, stats, flagged_by = lookup(row["url"])
        sample.at[idx, "vt_submitted"] = True
        sample.at[idx, "vt_result"] = result
        sample.at[idx, "vt_checked_at"] = datetime.now(timezone.utc).isoformat()
        sample.at[idx, "vt_stats"] = json.dumps(stats) if stats else ""
        sample.at[idx, "vt_categories"] = json.dumps(flagged_by) if flagged_by else ""
        sample.to_csv(SAMPLE_PATH, index=False)
        print(f"[{idx + 1}/{len(sample)}] {row['url'][:60]} -> {result} {flagged_by or ''}")
        time.sleep(SECONDS_BETWEEN_REQUESTS)

    checked = sample[sample["vt_result"].notna()]
    non_conclusive = checked["vt_result"].isin(["not_found"]) | checked["vt_result"].astype(str).str.startswith("error_")
    conclusive = checked[~non_conclusive]

    summary = {
        "total": len(sample),
        "checked": len(checked),
        "malicious": int((conclusive["vt_result"] == "malicious").sum()),
        "clean": int((conclusive["vt_result"] == "clean").sum()),
        "not_found": int((checked["vt_result"] == "not_found").sum()),
        "errors": int(checked["vt_result"].astype(str).str.startswith("error_").sum()),
    }
    summary["clean_rate"] = summary["clean"] / len(conclusive) if len(conclusive) else None

    os.makedirs("data/reports", exist_ok=True)
    with open("data/reports/virustotal_legitimate_evaluation_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--evaluate", action="store_true")
    args = parser.parse_args()
    if args.sample:
        prepare_sample()
    if args.evaluate:
        evaluate()
    if not args.sample and not args.evaluate:
        parser.print_help()
