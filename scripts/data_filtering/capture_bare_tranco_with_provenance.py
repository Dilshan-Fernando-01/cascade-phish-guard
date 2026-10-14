
import csv
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import pandas as pd

if os.environ.get("ENABLE_LAYER2", "").lower() not in ("1", "true", "yes"):
    sys.exit("ENABLE_LAYER2 is not set, refusing to run. This script loads real pages.")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend", "app"))
from services.layer2_analyzer import LAYER2_FEATURE_COLUMNS, analyze_layer2  # noqa: E402

CANDIDATES_PATH = "/tmp/bare_tranco_candidates.csv"
CHECKPOINT_PATH = "data/processed/bare_tranco_recapture_checkpoint.csv"
FINAL_PATH = "data/processed/bare_tranco_recaptured.csv"

MAX_WORKERS = 8


def capture_one(row):
    try:
        result = analyze_layer2(row["url"])
        if result["success"]:
            return {**row, **result["features"], "error": None}
        return {**row, "error": result["error"]}
    except Exception as exc:
        return {**row, "error": f"{type(exc).__name__}: {exc}"}


def main():
    candidates = pd.read_csv(CANDIDATES_PATH)
    candidates["domain"] = candidates["url"].apply(lambda u: urlparse(str(u)).netloc)
    candidates["source"] = "tranco"
    rows = candidates.to_dict("records")

    fieldnames = ["domain", "url", "source", "collected_date"] + LAYER2_FEATURE_COLUMNS + ["error"]
    t0 = time.time()
    succeeded = 0
    with open(CHECKPOINT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futures = {ex.submit(capture_one, row): row for row in rows}
            for i, fut in enumerate(as_completed(futures), 1):
                result_row = fut.result()
                writer.writerow(result_row)
                f.flush()
                ok = result_row.get("error") is None
                succeeded += int(ok)
                if i % 50 == 0 or i == len(rows):
                    print(f"[{i}/{len(rows)}] succeeded so far: {succeeded}/{i} "
                          f"({100*succeeded/i:.0f}%) - {time.time()-t0:.0f}s elapsed")

    checked = pd.read_csv(CHECKPOINT_PATH)
    good = checked[checked["error"].isna()]
    good.drop(columns=["error"]).to_csv(FINAL_PATH, index=False)
    print(f"\nfinal: {len(good)} of {len(checked)} succeeded, written to {FINAL_PATH}")


if __name__ == "__main__":
    main()
