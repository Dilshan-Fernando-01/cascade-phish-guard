import argparse
import csv
import os
import re

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CANDIDATES = os.path.join(ROOT, "data", "layer3", "legit_domains.csv")
OUT_DIR = os.path.join(ROOT, "data", "layer3", "html_test", "legit")
PAGE_TIMEOUT_MS = 45000


def legit_domains():
    with open(CANDIDATES, newline="") as f:
        return [row["domain"] for row in csv.DictReader(f)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=300)
    args = parser.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    domains = legit_domains()[: args.limit]
    todo = [d for d in domains if not os.path.exists(os.path.join(OUT_DIR, safe(d) + ".html"))]
    print(f"{len(todo)} pages to save ({len(domains) - len(todo)} already saved)")
    with sync_playwright() as p:
        for i, domain in enumerate(todo, 1):
            browser = p.chromium.launch()
            try:
                context = browser.new_context()
                page = context.new_page()
                page.goto(f"https://{domain}/", wait_until="load", timeout=PAGE_TIMEOUT_MS)
                page.wait_for_timeout(2000)
                html = page.content()
                with open(os.path.join(OUT_DIR, safe(domain) + ".html"), "w") as f:
                    f.write(html)
                print(f"[{i}/{len(todo)}] {domain} saved")
            except Exception as exc:
                print(f"[{i}/{len(todo)}] {domain} error: {type(exc).__name__}")
            finally:
                browser.close()


def safe(domain):
    return re.sub(r"[^A-Za-z0-9.-]+", "_", domain)


if __name__ == "__main__":
    main()
