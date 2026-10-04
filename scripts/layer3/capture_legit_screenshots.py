import csv
import os
import re

import pandas as pd
from playwright.sync_api import sync_playwright

DOMAIN_LIST_PATH = "data/layer3/legit_domains.csv"
SCREENSHOT_DIR = "data/layer3/legit_screenshots"
MANIFEST_PATH = "data/layer3/legit_manifest.csv"
TARGET_SUCCESSES = 1000

VIEWPORT = {"width": 1280, "height": 800}
TIMEOUT_MS = 20000
SETTLE_MS = 2000
MIN_VISIBLE_TEXT = 50

BAD_TITLE = re.compile(
    r"(error|access denied|forbidden|blocked|just a moment|attention required|are you a (robot|human)|"
    r"captcha|unusual traffic|not found|403|404|unavailable|temporarily|request rejected|incident|"
    r"system down|^loading|rejected)",
    re.I,
)

MANIFEST_FIELDS = ["domain", "success", "title", "text_length", "error"]


def load_done():
    if not os.path.exists(MANIFEST_PATH):
        return {}, 0
    done = {}
    successes = 0
    with open(MANIFEST_PATH, newline="") as f:
        for row in csv.DictReader(f):
            done[row["domain"]] = row
            if row["success"] == "True":
                successes += 1
    return done, successes


def main():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    candidates = pd.read_csv(DOMAIN_LIST_PATH)["domain"].tolist()
    done, successes = load_done()
    print(f"{successes} already captured, {len(done)} attempted, target {TARGET_SUCCESSES}")

    file_exists = os.path.exists(MANIFEST_PATH)
    with open(MANIFEST_PATH, "a", newline="") as mf, sync_playwright() as p:
        writer = csv.DictWriter(mf, fieldnames=MANIFEST_FIELDS)
        if not file_exists:
            writer.writeheader()
        browser = p.chromium.launch()
        for domain in candidates:
            if successes >= TARGET_SUCCESSES:
                break
            if domain in done:
                continue

            context = browser.new_context(viewport=VIEWPORT, accept_downloads=False, ignore_https_errors=True)
            page = context.new_page()
            page.on("dialog", lambda dialog: dialog.dismiss())
            record = {"domain": domain, "success": False, "title": "", "text_length": 0, "error": ""}
            try:
                page.goto(f"https://{domain}", timeout=TIMEOUT_MS, wait_until="domcontentloaded")
                page.wait_for_timeout(SETTLE_MS)
                record["title"] = page.title()[:80]
                record["text_length"] = len((page.inner_text("body") or "").strip())
                if BAD_TITLE.search(record["title"]):
                    record["error"] = "error-like title"
                elif record["text_length"] < MIN_VISIBLE_TEXT:
                    record["error"] = "almost no visible text"
                else:
                    page.screenshot(path=os.path.join(SCREENSHOT_DIR, f"{domain}.png"))
                    record["success"] = True
                    successes += 1
            except Exception as exc:
                record["error"] = type(exc).__name__
            finally:
                context.close()

            writer.writerow(record)
            mf.flush()
            print(f"[{successes}/{TARGET_SUCCESSES}] {domain} success={record['success']} {record['error']}")
        browser.close()

    print(f"done: {successes} successful captures")


if __name__ == "__main__":
    main()
