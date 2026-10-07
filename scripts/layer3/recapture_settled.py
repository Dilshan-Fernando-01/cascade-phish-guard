import os
import re
import sys

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts", "layer3"))
sys.path.insert(0, os.path.join(ROOT, "backend", "app"))
import test_region_false_match as t  # noqa: E402
from services import layer3_analyzer as l3  # noqa: E402

OLD_DIR = os.path.join(ROOT, "data", "layer3", "region_test", "legit")
NEW_DIR = os.path.join(ROOT, "data", "layer3", "region_test", "settled")
NETWORK_IDLE_MS = 15000


def main():
    l3._load_logo_state()
    os.makedirs(NEW_DIR, exist_ok=True)
    skipped = []
    for f in sorted(os.listdir(OLD_DIR)):
        with open(os.path.join(OLD_DIR, f), "rb") as fh:
            from services import region_compare as rc
            if any(p is None for p in rc._patches(fh.read())):
                skipped.append(f[:-4])
    print(f"skipped before (too plain): {len(skipped)}")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for i, domain in enumerate(skipped, 1):
            try:
                context = browser.new_context(viewport={"width": 1280, "height": 720})
                page = context.new_page()
                page.goto(f"https://{domain}/", wait_until="load", timeout=45000)
                try:
                    page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_MS)
                except Exception:
                    pass  # some pages never go idle; keep what has loaded
                page.wait_for_timeout(1000)
                name = re.sub(r"[^A-Za-z0-9.-]+", "_", domain)
                page.screenshot(path=os.path.join(NEW_DIR, name + ".png"))
                context.close()
                print(f"[{i}/{len(skipped)}] {domain} saved")
            except Exception as exc:
                print(f"[{i}/{len(skipped)}] {domain} error: {type(exc).__name__}")
        browser.close()


if __name__ == "__main__":
    main()
