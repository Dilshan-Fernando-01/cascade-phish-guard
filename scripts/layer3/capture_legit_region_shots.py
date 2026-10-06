
import os
import re

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HTML_DIR = os.path.join(ROOT, "data", "layer3", "html_test", "legit")
OUT_DIR = os.path.join(ROOT, "data", "layer3", "region_test", "legit")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    names = sorted(f[:-5] for f in os.listdir(HTML_DIR) if f.endswith(".html"))
    todo = [n for n in names if not os.path.exists(os.path.join(OUT_DIR, n + ".png"))]
    print(f"{len(todo)} screenshots to take")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for i, domain in enumerate(todo, 1):
            try:
                context = browser.new_context(viewport={"width": 1280, "height": 800})
                page = context.new_page()
                page.goto(f"https://{domain}/", wait_until="load", timeout=45000)
                page.wait_for_timeout(2000)
                page.screenshot(path=os.path.join(OUT_DIR, re.sub(r"[^A-Za-z0-9.-]+", "_", domain) + ".png"))
                context.close()
                print(f"[{i}/{len(todo)}] {domain} saved")
            except Exception as exc:
                print(f"[{i}/{len(todo)}] {domain} error: {type(exc).__name__}")
        browser.close()


if __name__ == "__main__":
    main()
