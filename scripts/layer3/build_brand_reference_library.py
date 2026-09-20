import csv
import os
import sys
import time
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend", "app"))
from services.layer2_analyzer import _looks_like_bot_challenge

TOP_20_BRANDS = [
    "allegro.pl", "irs.gov", "facebook.com", "microsoft.com", "amazon.com",
    "bradesco.com.br", "netflix.com", "optus.com.au", "societegenerale.com",
    "paypal.com", "adobe.com", "att.com", "americanexpress.com", "docusign.com",
    "comcast.com", "google.com", "ebay.com", "apple.com", "bankofamerica.com",
    "hsbc.com",
]

OUTPUT_DIR = "data/reference_brands"
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
MANIFEST_PATH = os.path.join(OUTPUT_DIR, "manifest.csv")
VIEWPORT = {"width": 1280, "height": 800}
TIMEOUT_MS = 20000


def capture_brand(domain, browser):
    url = f"https://{domain}"
    context = browser.new_context(viewport=VIEWPORT, ignore_https_errors=True)
    page = context.new_page()
    result = {
        "domain": domain,
        "url": url,
        "final_url": None,
        "image_path": None,
        "success": False,
        "flagged_bot_challenge": False,
        "error": None,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        page.goto(url, timeout=TIMEOUT_MS, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)  # let above-the-fold content/lazy images settle
        html = page.content()
        if _looks_like_bot_challenge(html, None):
            result["flagged_bot_challenge"] = True
            result["error"] = "page appears to be a bot-verification challenge, not the real homepage"
        else:
            image_path = os.path.join(IMAGES_DIR, f"{domain}.png")
            page.screenshot(path=image_path)
            result["image_path"] = image_path
            result["final_url"] = page.url
            result["success"] = True
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        context.close()
    return result


def main():
    os.makedirs(IMAGES_DIR, exist_ok=True)
    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for domain in TOP_20_BRANDS:
            print(f"Capturing {domain}...")
            row = capture_brand(domain, browser)
            rows.append(row)
            status = "OK" if row["success"] else f"FAILED ({row['error']})"
            print(f"  -> {status}")
            time.sleep(1)
        browser.close()

    with open(MANIFEST_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    succeeded = sum(1 for r in rows if r["success"])
    print(f"\n{succeeded}/{len(rows)} brand references captured successfully.")
    print(f"Manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
