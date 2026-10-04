import argparse
import csv
import io
import os
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend", "app"))
from services.layer3_analyzer import analyze_layer3  # noqa: E402

MANIFEST_PATH = os.path.join(ROOT, "data", "layer3", "legit_manifest.csv")
OUTPUT_PATH = os.path.join(ROOT, "data", "layer3", "false_alarm_results.csv")
FINDER_SOURCE = os.path.join(ROOT, "extension", "layer3_capture.js")

VIEWPORT = {"width": 1280, "height": 800}
PAGE_TIMEOUT_MS = 45000
SETTLE_MS = 2000
FALSE_ALARM_LEVELS = {"closely resembles", "may be imitating"}
FIELDS = ["domain", "loaded", "logo_found", "logo_status", "identified_brand", "identity_level", "false_alarm"]


def load_finder_source():
    src = open(FINDER_SOURCE).read()
    return src[src.index("function findLogoCandidatesInPage"): src.index("function blobToBase64")].strip()


def legit_domains():
    with open(MANIFEST_PATH, newline="") as f:
        return [row["domain"] for row in csv.DictReader(f) if row["success"] == "True"]


def done_domains():
    if not os.path.exists(OUTPUT_PATH):
        return set()
    with open(OUTPUT_PATH, newline="") as f:
        return {row["domain"] for row in csv.DictReader(f)}


def check_one(page, finder_js, domain):
    url = f"https://{domain}/"
    row = {"domain": domain, "loaded": False, "logo_found": False, "logo_status": "",
           "identified_brand": "", "identity_level": "", "false_alarm": False}
    try:
        page.goto(url, wait_until="load", timeout=PAGE_TIMEOUT_MS)
        page.wait_for_timeout(SETTLE_MS)
    except Exception:
        return row
    row["loaded"] = True

    found = page.evaluate("(" + finder_js + ")()")
    best = found.get("best")
    logo_png = None
    if best:
        shot = Image.open(io.BytesIO(page.screenshot(full_page=False))).convert("RGB")
        x, y, w, h = int(best["x"]), int(best["y"]), int(best["w"]), int(best["h"])
        buf = io.BytesIO()
        shot.crop((x, y, x + w, y + h)).save(buf, "PNG")
        logo_png = buf.getvalue()
        row["logo_found"] = True

    result = analyze_layer3(url, None, logo_png=logo_png)
    logo = result["logo_check"]
    row["logo_status"] = logo.get("status", "")
    row["identified_brand"] = logo.get("identified_brand") or ""
    row["identity_level"] = result["identity_note"]["level"]
    row["false_alarm"] = row["identity_level"] in FALSE_ALARM_LEVELS
    return row


def summarise(rows):
    loaded = [r for r in rows if r["loaded"] == "True" or r["loaded"] is True]
    found = [r for r in loaded if r["logo_found"] in ("True", True)]
    alarms = [r for r in loaded if r["false_alarm"] in ("True", True)]
    print()
    print(f"attempted:            {len(rows)}")
    print(f"pages loaded:         {len(loaded)}  (not loaded: {len(rows) - len(loaded)})")
    print(f"logo found:           {len(found)}")
    print(f"false alarms:         {len(alarms)}")
    if loaded:
        print(f"false-alarm rate (of loaded pages): {100 * len(alarms) / len(loaded):.1f}%")
    if found:
        print(f"false-alarm rate (of pages with a logo): {100 * len(alarms) / len(found):.1f}%")
    for r in alarms:
        print(f"  false alarm: {r['domain']} -> {r['identity_level']} ({r['identified_brand'] or 'no brand'})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--domains", nargs="*", help="check only these domains (for a quick test)")
    args = parser.parse_args()

    global OUTPUT_PATH
    if args.domains:
        OUTPUT_PATH = os.path.join(ROOT, "data", "layer3", "false_alarm_test_run.csv")
    domains = args.domains or legit_domains()
    skip = done_domains() if not args.domains else set()
    todo = [d for d in domains if d not in skip]
    print(f"{len(todo)} domains to check ({len(skip)} already done)")

    finder_js = load_finder_source()
    new_file = not os.path.exists(OUTPUT_PATH) or os.path.getsize(OUTPUT_PATH) == 0
    rows_now = []
    with open(OUTPUT_PATH, "a", newline="") as out, sync_playwright() as p:
        writer = csv.DictWriter(out, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        browser = p.chromium.launch()
        context = browser.new_context(viewport=VIEWPORT, ignore_https_errors=True)
        page = context.new_page()
        for i, domain in enumerate(todo, 1):
            row = check_one(page, finder_js, domain)
            writer.writerow(row)
            out.flush()
            rows_now.append(row)
            print(f"[{i}/{len(todo)}] {domain} loaded={row['loaded']} logo={row['logo_found']} level={row['identity_level'] or '-'}")
        browser.close()

    with open(OUTPUT_PATH, newline="") as f:
        summarise(list(csv.DictReader(f)))


if __name__ == "__main__":
    main()
