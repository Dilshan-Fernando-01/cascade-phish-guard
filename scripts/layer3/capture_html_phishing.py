import argparse
import csv
import os
import re

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOURCE = os.path.join(ROOT, "data", "processed", "layer2_test.csv")
OUT_DIR = os.path.join(ROOT, "data", "layer3", "html_test", "phishing")
PAGE_TIMEOUT_MS = 30000


def phishing_urls():
    with open(SOURCE, newline="") as f:
        return [row["url"] for row in csv.DictReader(f) if row["label"] == "1"]


def safe(url):
    return re.sub(r"[^A-Za-z0-9.-]+", "_", url)[:120]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=300)
    args = parser.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    urls = phishing_urls()[: args.limit]
    todo = [u for u in urls if not os.path.exists(os.path.join(OUT_DIR, safe(u) + ".html"))]
    print(f"{len(todo)} pages to save ({len(urls) - len(todo)} already saved)")
    with sync_playwright() as p:
        for i, url in enumerate(todo, 1):
            browser = p.chromium.launch()
            try:
                context = browser.new_context()
                page = context.new_page()
                page.goto(url, wait_until="load", timeout=PAGE_TIMEOUT_MS)
                page.wait_for_timeout(2000)
                with open(os.path.join(OUT_DIR, safe(url) + ".html"), "w") as f:
                    f.write(page.content())
                print(f"[{i}/{len(todo)}] saved")
            except Exception as exc:
                print(f"[{i}/{len(todo)}] error: {type(exc).__name__}")
            finally:
                browser.close()


if __name__ == "__main__":
    main()
