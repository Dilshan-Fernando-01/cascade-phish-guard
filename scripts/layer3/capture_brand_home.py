import argparse
import csv
import os
import pickle
import re
import sys
import time
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend", "app"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "layer3"))

from services.layer2_analyzer import _looks_like_bot_challenge  # noqa: E402
from logo_identity import brand_converter  # noqa: E402

LOGO_CACHE_PATH = os.path.join(ROOT, "data", "external", "phishpedia", "logo_reference_embeddings.pkl")
DOMAIN_MAP_PATH = os.path.join(ROOT, "data", "external", "phishpedia", "domain_map.pkl")
OUT_DIR = os.path.join(ROOT, "data", "layer3", "brand_home")
MANIFEST_PATH = os.path.join(ROOT, "data", "layer3", "brand_home_manifest.csv")

VIEWPORT = {"width": 1280, "height": 800}
PAGE_TIMEOUT_MS = 45000
SETTLE_MS = 2000
PAUSE_BETWEEN_SITES_S = 3
MAX_CONSECUTIVE_BOT_CHECKS = 10

BAD_TITLE = re.compile(
    r"(error|access denied|forbidden|blocked|just a moment|attention required|are you a (robot|human)|"
    r"captcha|unusual traffic|not found|unavailable|temporarily|request rejected|incident|"
    r"system down|^loading|rejected)",
    re.IGNORECASE,
)

FIELDS = ["brand", "domain", "final_url", "success", "bot_challenge", "error", "captured_at"]


def brands_from_logo_cache():
    """Brands the logo check can identify, each with its primary domain."""
    cache = pickle.load(open(LOGO_CACHE_PATH, "rb"))
    domain_map = pickle.load(open(DOMAIN_MAP_PATH, "rb"))
    brands = {}
    for file_path in cache["file_paths"]:
        folder = os.path.basename(os.path.dirname(file_path))
        brand = brand_converter(folder)
        domains = domain_map.get(brand) or []
        if domains and brand not in brands:
            brands[brand] = domains[0]
    return brands


def load_done():
    if not os.path.exists(MANIFEST_PATH):
        return set()
    with open(MANIFEST_PATH, newline="") as f:
        return {row["brand"] for row in csv.DictReader(f) if row["success"] == "True"}


def safe_name(brand):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", brand).strip("_") or "brand"


def capture(browser, brand, domain):
    url = f"https://{domain}/"
    record = {
        "brand": brand,
        "domain": domain,
        "final_url": "",
        "success": False,
        "bot_challenge": False,
        "error": "",
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    context = browser.new_context(viewport=VIEWPORT, ignore_https_errors=False)
    try:
        page = context.new_page()
        try:
            page.goto(url, wait_until="load", timeout=PAGE_TIMEOUT_MS)
            page.wait_for_timeout(SETTLE_MS)
        except Exception as exc:
            record["error"] = f"load failed: {type(exc).__name__}"
            return record

        record["final_url"] = page.url
        try:
            html = page.content()
            title = page.title() or ""
        except Exception as exc:
            # The page kept navigating after load (for example a redirect). Record it, don't crash.
            record["error"] = f"page still changing: {type(exc).__name__}"
            return record
        if _looks_like_bot_challenge(html, None):
            record["bot_challenge"] = True
            record["error"] = "bot-verification page, not the real home page"
            return record
        if BAD_TITLE.search(title):
            record["error"] = "error or blocked page (title check)"
            return record

        os.makedirs(OUT_DIR, exist_ok=True)
        path = os.path.join(OUT_DIR, f"{safe_name(brand)}.png")
        page.screenshot(path=path, full_page=False)
        record["success"] = True
        return record
    finally:
        context.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--brands", nargs="*", help="only these brands (for a quick test)")
    args = parser.parse_args()

    global OUT_DIR, MANIFEST_PATH
    brands = brands_from_logo_cache()
    if args.brands:
        # Test runs use their own folder and manifest, so the real run is not affected
        OUT_DIR = os.path.join(ROOT, "data", "layer3", "brand_home_test")
        MANIFEST_PATH = os.path.join(ROOT, "data", "layer3", "brand_home_test_manifest.csv")
        if os.path.exists(MANIFEST_PATH):
            os.remove(MANIFEST_PATH)
        brands = {b: brands[b] for b in args.brands if b in brands}
    done = load_done() if not args.brands else set()
    todo = [(b, d) for b, d in brands.items() if b not in done]
    print(f"{len(todo)} brands to capture ({len(done)} already done)")

    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    new_file = not os.path.exists(MANIFEST_PATH) or os.path.getsize(MANIFEST_PATH) == 0
    consecutive_bot = 0
    with open(MANIFEST_PATH, "a", newline="") as mf, sync_playwright() as p:
        writer = csv.DictWriter(mf, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        browser = p.chromium.launch()
        for i, (brand, domain) in enumerate(todo, 1):
            try:
                record = capture(browser, brand, domain)
            except Exception as exc:
                record = {
                    "brand": brand, "domain": domain, "final_url": "", "success": False,
                    "bot_challenge": False, "error": f"unexpected: {type(exc).__name__}",
                    "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                }
            writer.writerow(record)
            mf.flush()
            status = "captured" if record["success"] else (record["error"] or "failed")
            print(f"[{i}/{len(todo)}] {brand} ({domain}): {status}")

            consecutive_bot = consecutive_bot + 1 if record["bot_challenge"] else 0
            if consecutive_bot >= MAX_CONSECUTIVE_BOT_CHECKS:
                print("Stopping: repeated bot-verification pages. Try again later; do not force it.")
                break
            time.sleep(PAUSE_BETWEEN_SITES_S)
        browser.close()


if __name__ == "__main__":
    main()
