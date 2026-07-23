from datetime import datetime, timezone
from urllib.error import HTTPError, URLError

from common import fetch_text, save_snapshot

SOURCE = "phishtank"
URL = "https://data.phishtank.com/data/online-valid.csv"


def main():
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        text = fetch_text(URL)
    except (HTTPError, URLError) as exc:
        print(f"[{timestamp}] {SOURCE}: fetch failed ({exc}) -- likely still rate-limited, will retry next run")
        return

    if "exceeded the request rate limit" in text.lower():
        print(f"[{timestamp}] {SOURCE}: still rate-limited (message in response body), will retry next run")
        return

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    path, count = save_snapshot(SOURCE, URL, lines, timestamp)
    print(f"[{timestamp}] {SOURCE}: saved {count} rows -> {path}")


if __name__ == "__main__":
    main()
