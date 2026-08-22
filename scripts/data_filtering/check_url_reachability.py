import csv
import json
import os
import time

import pandas as pd
import requests

TIMEOUT_SECONDS = 10
DELAY_BETWEEN_REQUESTS = 0.5

HEADERS = {"User-Agent": "cascade-phish-guard-research/1.0"}

# Every URL checked (reachable or not) gets appended here immediately,
# not just at the very end -- so an interruption (closing the laptop,
# losing wifi, anything) never loses progress. Re-running this script
# picks up wherever it left off instead of starting over from zero.
CHECKED_PATH = "data/processed/phishing_candidates_reachability_checked.csv"
REACHABLE_PATH = "data/processed/phishing_candidates_reachable.csv"
SUMMARY_PATH = "data/reports/reachability_summary.json"

CHECKED_FIELDNAMES = [
    "url", "source", "collected_date", "confirmation_method",
    "is_reachable", "http_status", "reachability_error",
]


def check_reachable(url):
    try:
        resp = requests.get(
            url, headers=HEADERS, timeout=TIMEOUT_SECONDS, stream=True, allow_redirects=True
        )
        resp.close()
        return True, resp.status_code, None
    except requests.exceptions.RequestException as exc:
        return False, None, type(exc).__name__


def load_already_checked():
    if not os.path.exists(CHECKED_PATH):
        return set()
    checked = pd.read_csv(CHECKED_PATH)
    return set(checked["url"])


def main():
    confirmed = pd.read_csv("data/processed/phishing_candidates_dual_confirmed.csv")

    already_checked = load_already_checked()
    remaining = confirmed[~confirmed["url"].isin(already_checked)]

    print(
        f"{len(already_checked)} already checked in a previous run, "
        f"{len(remaining)} remaining out of {len(confirmed)} total."
    )

    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("data/reports", exist_ok=True)

    file_exists = os.path.exists(CHECKED_PATH)
    with open(CHECKED_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CHECKED_FIELDNAMES)
        if not file_exists:
            writer.writeheader()

        for i, (_, row) in enumerate(remaining.iterrows()):
            reachable, status, error = check_reachable(row["url"])
            writer.writerow({
                "url": row["url"],
                "source": row["source"],
                "collected_date": row["collected_date"],
                "confirmation_method": row["confirmation_method"],
                "is_reachable": reachable,
                "http_status": status,
                "reachability_error": error,
            })
            f.flush()
            print(
                f"[{len(already_checked) + i + 1}/{len(confirmed)}] "
                f"{row['url'][:60]} -> reachable={reachable} status={status} error={error}"
            )
            time.sleep(DELAY_BETWEEN_REQUESTS)

    all_checked = pd.read_csv(CHECKED_PATH)
   
    is_reachable = all_checked["is_reachable"].astype(str).map({"True": True, "False": False})

    reachable_df = all_checked[is_reachable]
    reachable_df.to_csv(REACHABLE_PATH, index=False)

    summary = {
        "total_confirmed": len(confirmed),
        "checked_so_far": len(all_checked),
        "remaining": len(confirmed) - len(all_checked),
        "reachable": int(is_reachable.sum()),
        "unreachable": int((~is_reachable).sum()),
        "reachability_rate": float(is_reachable.mean()) if len(all_checked) else 0.0,
        "error_breakdown": all_checked.loc[~is_reachable, "reachability_error"].value_counts().to_dict(),
        "complete": len(all_checked) >= len(confirmed),
    }

    with open(SUMMARY_PATH, "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
