import json
import os
import time

import pandas as pd
import requests

TIMEOUT_SECONDS = 10
DELAY_BETWEEN_REQUESTS = 0.5 

HEADERS = {"User-Agent": "cascade-phish-guard-research/1.0"}


def check_reachable(url):
   
    try:
        resp = requests.get(
            url, headers=HEADERS, timeout=TIMEOUT_SECONDS, stream=True, allow_redirects=True
        )
        resp.close()
        return True, resp.status_code, None
    except requests.exceptions.RequestException as exc:
        return False, None, type(exc).__name__


def main():
    confirmed = pd.read_csv("data/processed/phishing_candidates_dual_confirmed.csv")

    is_reachable, http_status, reachability_error = [], [], []

    for i, row in confirmed.iterrows():
        reachable, status, error = check_reachable(row["url"])
        is_reachable.append(reachable)
        http_status.append(status)
        reachability_error.append(error)
        print(f"[{i + 1}/{len(confirmed)}] {row['url'][:60]} -> reachable={reachable} status={status} error={error}")
        time.sleep(DELAY_BETWEEN_REQUESTS)

    confirmed["is_reachable"] = is_reachable
    confirmed["http_status"] = http_status
    confirmed["reachability_error"] = reachability_error

    reachable_df = confirmed[confirmed["is_reachable"]]

    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("data/reports", exist_ok=True)

    reachable_df.to_csv("data/processed/phishing_candidates_reachable.csv", index=False)

    summary = {
        "total": len(confirmed),
        "reachable": int(confirmed["is_reachable"].sum()),
        "unreachable": int((~confirmed["is_reachable"]).sum()),
        "reachability_rate": float(confirmed["is_reachable"].mean()),
        "error_breakdown": confirmed.loc[~confirmed["is_reachable"], "reachability_error"]
        .value_counts()
        .to_dict(),
    }

    with open("data/reports/reachability_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
