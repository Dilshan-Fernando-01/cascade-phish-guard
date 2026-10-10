import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_live_against_fresh_phishing import safe_browsing_lookup  # noqa: E402

load_dotenv()


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return
    if not os.environ.get("GOOGLE_SAFE_BROWSING_API_KEY"):
        print("Set GOOGLE_SAFE_BROWSING_API_KEY first.")
        return

    with open(sys.argv[1]) as f:
        urls = [line.strip() for line in f if line.strip()]

    for i, url in enumerate(urls, 1):
        result = safe_browsing_lookup(url)
        label = result or "lookup failed (check the key/network)"
        print(f"[{i}/{len(urls)}] Safe Browsing says: {label}")


if __name__ == "__main__":
    main()
