import json
import os

import pandas as pd

TARGET_SAMPLE_SIZE = 500
RANDOM_SEED = 42

POOL_PATH = "data/processed/phishing_candidates_dual_confirmed.csv"
SAMPLE_PATH = "data/processed/virustotal_sample.csv"
SAMPLE_COLUMNS = ["url", "source", "confirmation_method", "vt_submitted", "vt_result", "vt_checked_at"]


def main():
    pool = pd.read_csv(POOL_PATH)
    pool_size = len(pool)

    if os.path.exists(SAMPLE_PATH):
        existing = pd.read_csv(SAMPLE_PATH)
    else:
        existing = pd.DataFrame(columns=SAMPLE_COLUMNS)

    existing_size = len(existing)
    already_completed = int(existing["vt_submitted"].sum()) if existing_size else 0

   
    remaining_pool = pool[~pool["url"].isin(set(existing["url"]))]
    additional_needed = min(max(0, TARGET_SAMPLE_SIZE - existing_size), len(remaining_pool))

    if additional_needed > 0:
        new_rows = remaining_pool.sample(n=additional_needed, random_state=RANDOM_SEED)[
            ["url", "source", "confirmation_method"]
        ].copy()
        new_rows["vt_submitted"] = False
        new_rows["vt_result"] = None
        new_rows["vt_checked_at"] = None
        sample = pd.concat([existing, new_rows], ignore_index=True)
    else:
        sample = existing

    sample = sample.reindex(columns=SAMPLE_COLUMNS)

    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("data/reports", exist_ok=True)

    sample.to_csv(SAMPLE_PATH, index=False)

    report = {
        "pool_size": pool_size,
        "target_sample_size": TARGET_SAMPLE_SIZE,
        "existing_sample_size_before_this_run": existing_size,
        "already_completed_before_this_run": already_completed,
        "newly_added_this_run": additional_needed,
        "actual_sample_size": len(sample),
        "reached_target": len(sample) >= TARGET_SAMPLE_SIZE,
        "random_seed": RANDOM_SEED,
    }

    with open("data/reports/virustotal_sample_summary.json", "w") as f:
        json.dump(report, f, indent=2)

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
