import csv
import os
import sys
import time
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend", "app"))
from services.layer2_analyzer import _looks_like_bot_challenge


CANDIDATE_BRANDS = [
    "allegro.pl", "irs.gov", "facebook.com", "microsoft.com", "amazon.com",
    "bradesco.com.br", "netflix.com", "optus.com.au", "societegenerale.com",
    "paypal.com", "adobe.com", "att.com", "americanexpress.com", "docusign.com",
    "comcast.com", "google.com", "ebay.com", "apple.com", "bankofamerica.com",
    "hsbc.com",
    "dhl.com", "chase.com", "coinbase.com", "orange.fr", "bt.com",
    "wetransfer.com", "santander.com", "ing.com", "steamcommunity.com",
    "steampowered.com", "visa.com", "outlook.com", "interactivebrokers.com",
    "free.fr", "navyfederal.org", "whatsapp.com", "abnamro.com", "dbs.com",
    "bb.com.br", "instagram.com", "dropbox.com", "unicredit.eu",
    "wellsfargo.com", "binance.com", "revolut.com",
    "linkedin.com", "icloud.com", "yahoo.com", "twitter.com", "x.com",
    "ups.com", "fedex.com", "citibank.com", "usbank.com", "capitalone.com",
    "discover.com",
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


def load_existing_manifest():
    if not os.path.exists(MANIFEST_PATH):
        return {}
    with open(MANIFEST_PATH, newline="") as f:
        return {row["domain"]: row for row in csv.DictReader(f)}


def main():
    os.makedirs(IMAGES_DIR, exist_ok=True)
    existing = load_existing_manifest()

    already_ok = {d for d, r in existing.items() if r["success"] == "True"}
    to_capture = [d for d in CANDIDATE_BRANDS if d not in already_ok]

    print(f"{len(already_ok)} already captured successfully -- skipping those.")
    print(f"{len(to_capture)} to attempt this run.\n")

    new_rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for domain in to_capture:
            print(f"Capturing {domain}...")
            row = capture_brand(domain, browser)
            new_rows.append(row)
            status = "OK" if row["success"] else f"FAILED ({row['error']})"
            print(f"  -> {status}")
            time.sleep(1)
        browser.close()

    # Merge: keep every existing row untouched except ones we just retried, plus all new rows.
    merged = {d: r for d, r in existing.items()}
    for row in new_rows:
        merged[row["domain"]] = row

    fieldnames = list(new_rows[0].keys()) if new_rows else list(next(iter(existing.values())).keys())
    with open(MANIFEST_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for domain in CANDIDATE_BRANDS:
            if domain in merged:
                writer.writerow(merged[domain])

    total_ok = sum(1 for d in CANDIDATE_BRANDS if merged.get(d, {}).get("success") in (True, "True"))
    print(f"\n{total_ok}/{len(CANDIDATE_BRANDS)} brand references captured successfully overall.")
    print(f"Manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
