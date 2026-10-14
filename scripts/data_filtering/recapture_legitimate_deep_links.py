
import csv
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

if os.environ.get("ENABLE_LAYER2", "").lower() not in ("1", "true", "yes"):
    sys.exit("ENABLE_LAYER2 is not set, refusing to run. This script loads real pages.")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend", "app"))
from services.layer2_analyzer import LAYER2_FEATURE_COLUMNS, analyze_layer2  # noqa: E402

CHECKPOINT_PATH = "data/processed/legitimate_deep_links_recapture_checkpoint.csv"
FINAL_PATH = "data/processed/legitimate_deep_links_recaptured.csv"
SUMMARY_PATH = "data/reports/legitimate_deep_links_recapture_summary.json"

MAX_WORKERS = 8


def load_candidates():
    templated = pd.read_csv("data/processed/legitimate_deep_links_templated.csv")
    full = pd.read_csv("data/processed/legitimate_deep_links.csv")
    commoncrawl = full[full["source"] == "commoncrawl"]
    combined = pd.concat([templated, commoncrawl], ignore_index=True)
    return combined


def already_done():
    if not os.path.exists(CHECKPOINT_PATH):
        return set()
    return set(pd.read_csv(CHECKPOINT_PATH, usecols=["url"])["url"])


def capture_one(row):
    try:
        result = analyze_layer2(row["url"])
        if result["success"]:
            return {**row, **result["features"], "error": None}
        return {**row, "error": result["error"]}
    except Exception as exc:
        return {**row, "error": f"{type(exc).__name__}: {exc}"}


def main():
    candidates = load_candidates()
    done = already_done()
    remaining = candidates[~candidates["url"].isin(done)]
    print(f"{len(done)} already done, {len(remaining)} remaining out of {len(candidates)}")

    fieldnames = list(candidates.columns) + LAYER2_FEATURE_COLUMNS + ["error"]
    file_exists = os.path.exists(CHECKPOINT_PATH)

    rows = remaining.to_dict("records")
    t0 = time.time()
    succeeded = 0
    with open(CHECKPOINT_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futures = {ex.submit(capture_one, row): row for row in rows}
            for i, fut in enumerate(as_completed(futures), 1):
                result_row = fut.result()
                writer.writerow(result_row)
                f.flush()
                ok = result_row.get("error") is None
                succeeded += int(ok)
                if i % 25 == 0 or i == len(rows):
                    elapsed = time.time() - t0
                    print(f"[{i}/{len(rows)}] succeeded so far: {succeeded}/{i} "
                          f"({100*succeeded/i:.0f}%) - {elapsed:.0f}s elapsed")

    checked = pd.read_csv(CHECKPOINT_PATH)
    good = checked[checked["error"].isna()]
    good.drop(columns=["error"]).to_csv(FINAL_PATH, index=False)

    import json
    summary = {
        "total_candidates_attempted": len(checked),
        "succeeded": len(good),
        "failed": len(checked) - len(good),
        "success_rate": round(len(good) / len(checked), 4) if len(checked) else 0,
        "by_source": good["source"].value_counts().to_dict(),
    }
    os.makedirs("data/reports", exist_ok=True)
    with open(SUMMARY_PATH, "w") as f:
        json.dump(summary, f, indent=2)
    print()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
