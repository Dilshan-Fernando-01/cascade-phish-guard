from datetime import datetime, timezone

from common import fetch_text, save_snapshot

SOURCE = "openphish"
URL = "https://openphish.com/feed.txt"


def main():
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    text = fetch_text(URL)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    path, count = save_snapshot(SOURCE, URL, lines, timestamp)
    print(f"[{timestamp}] {SOURCE}: saved {count} URLs -> {path}")


if __name__ == "__main__":
    main()
