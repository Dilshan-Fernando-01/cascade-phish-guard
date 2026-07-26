import base64
import json
import os
import time
from datetime import datetime, timezone

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("VIRUSTOTAL_API_KEY")
if not API_KEY:
    raise SystemExit("VIRUSTOTAL_API_KEY not set")

SAMPLE_PATH = "data/processed/virustotal_sample.csv"
SECONDS_BETWEEN_REQUESTS = 16  


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
        stats = resp.json()["data"]["attributes"]["last_analysis_stats"]
        flagged = stats.get("malicious", 0) + stats.get("suspicious", 0)
        return ("malicious" if flagged > 0 else "clean"), stats
    if resp.status_code == 404:
        return "not_found", None
    return f"error_{resp.status_code}", None


def main():
    sample = pd.read_csv(SAMPLE_PATH)

    for idx, row in sample.iterrows():
        if bool(row.get("vt_submitted")):
            continue 

        result, _stats = lookup(row["url"])
        sample.at[idx, "vt_submitted"] = True
        sample.at[idx, "vt_result"] = result
        sample.at[idx, "vt_checked_at"] = datetime.now(timezone.utc).isoformat()

        sample.to_csv(SAMPLE_PATH, index=False)  

        print(f"[{idx + 1}/{len(sample)}] {row['url'][:60]} -> {result}")
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
    summary["agreement_rate"] = (
        summary["malicious"] / len(conclusive) if len(conclusive) else None
    )

    os.makedirs("data/reports", exist_ok=True)
    with open("data/reports/virustotal_evaluation_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
