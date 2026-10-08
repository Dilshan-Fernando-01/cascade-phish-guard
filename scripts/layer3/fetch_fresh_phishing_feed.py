import argparse
import csv
import os
from datetime import datetime, timezone

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(ROOT, "data", "layer3", "fresh_phishing")
OPENPHISH_FEED_URL = "https://openphish.com/feed.txt"
FIELDS = ["url", "source", "collected_date", "confirmation_method", "label"]


def fetch_openphish():
    resp = requests.get(OPENPHISH_FEED_URL, timeout=30)
    resp.raise_for_status()
    return [line.strip() for line in resp.text.splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=150, help="how many URLs to keep (a Saturday test session is a few hours, not all day)")
    args = parser.parse_args()

    urls = fetch_openphish()
    print(f"OpenPhish feed: {len(urls)} URLs currently listed")

    urls = urls[: args.limit]

    os.makedirs(OUT_DIR, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = os.path.join(OUT_DIR, f"fresh_phishing_{today}.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for url in urls:
            writer.writerow({
                "url": url,
                "source": "openphish",
                "collected_date": today,
                "confirmation_method": "feed",
                "label": 1,
            })

    print(f"saved {len(urls)} URLs to {out_path}")
    print("next: copy this file to the VM (same Drive -> Downloads -> shared-folder route as always),")
    print("then run test_live_against_fresh_phishing.py there.")


if __name__ == "__main__":
    main()
