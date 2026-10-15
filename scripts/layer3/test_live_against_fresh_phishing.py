import csv
import io
import os
import sys
import time

import requests
from dotenv import load_dotenv
from PIL import Image
from playwright.sync_api import sync_playwright

load_dotenv()
os.environ.setdefault("ENABLE_LAYER2", "true")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend", "app"))
from services.cascade_analyzer import analyze  # noqa: E402

OUTPUT_PATH = os.path.join(ROOT, "data", "layer3", "fresh_phishing_live_results.csv")
FINDER_SOURCE = os.path.join(ROOT, "extension", "layer3_capture.js")

VIEWPORT = {"width": 1280, "height": 800}
PAGE_TIMEOUT_MS = 30000
NETWORK_IDLE_MS = 8000
BANNER_BAND_PX = 300 

FIELDS = [
    "url", "loaded", "http_status", "html_length", "logo_found", "verdict", "layer1_score", "layer2_score",
    "layer3_level", "layer3_score", "combination_strength", "reasons", "sb_verdict", "status",
    "analysis_ms", "layer1_ms", "layer2_ms", "layer3_ms",
]

SB_API_KEY = os.environ.get("GOOGLE_SAFE_BROWSING_API_KEY")
SB_ENDPOINT = "https://safebrowsing.googleapis.com/v4/threatMatches:find"


def load_finder_js():
    src = open(FINDER_SOURCE).read()
    return src[src.index("function findLogoCandidatesInPage"): src.index("function blobToBase64")].strip()


def done_urls():
    if not os.path.exists(OUTPUT_PATH):
        return set()
    with open(OUTPUT_PATH, newline="") as f:
        return {row["url"] for row in csv.DictReader(f) if not row["status"].startswith("error:")}


def safe_browsing_lookup(url):
   
    if not SB_API_KEY:
        return None
    body = {
        "client": {"clientId": "cascade-phish-guard-research-eval", "clientVersion": "0.1.0"},
        "threatInfo": {
            "threatTypes": ["SOCIAL_ENGINEERING", "MALWARE", "UNWANTED_SOFTWARE"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}],
        },
    }
    try:
        resp = requests.post(SB_ENDPOINT, params={"key": SB_API_KEY}, json=body, timeout=10)
        if resp.status_code != 200:
            return None
        return "flagged" if resp.json().get("matches") else "clean"
    except Exception:
        return None


def check_one(page, finder_js, url):
    row = {k: "" for k in FIELDS}
    row["url"] = url
    row["loaded"] = False
    try:
        response = page.goto(url, wait_until="load", timeout=PAGE_TIMEOUT_MS)
        try:
            page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_MS)
        except Exception:
            pass
        page.wait_for_timeout(1000)
        html = page.content()
    except Exception:
        row["status"] = "did not load"
        return row
    row["loaded"] = True
    
    row["http_status"] = response.status if response is not None else ""
    row["html_length"] = len(html)

    full_png = page.screenshot(full_page=False)
    shot = Image.open(io.BytesIO(full_png)).convert("RGB")

    found = page.evaluate("(" + finder_js + ")()")
    best = found.get("best")
    logo_png = None
    if best:
        x, y, w, h = int(best["x"]), int(best["y"]), int(best["w"]), int(best["h"])
        buf = io.BytesIO()
        shot.crop((x, y, x + w, y + h)).save(buf, "PNG")
        logo_png = buf.getvalue()
    row["logo_found"] = bool(best)

    banner_buf = io.BytesIO()
    shot.crop((0, 0, shot.width, min(BANNER_BAND_PX, shot.height))).save(banner_buf, "PNG")
    banner_png = banner_buf.getvalue()

    t0 = time.time()
    result = analyze(url, full_scan=True, html=html, skip_layer2=False, screenshot_png=banner_png, logo_png=logo_png)
    row["analysis_ms"] = round((time.time() - t0) * 1000)
    row["layer1_ms"] = result.layer_timings_ms.get("layer1", "")
    row["layer2_ms"] = result.layer_timings_ms.get("layer2", "")
    row["layer3_ms"] = result.layer_timings_ms.get("layer3", "")
    row["verdict"] = result.verdict.value
    row["layer1_score"] = round(result.layer_scores.get("layer1", 0), 4)
    row["layer2_score"] = round(result.layer_scores["layer2"], 4) if "layer2" in result.layer_scores else ""
    row["layer3_score"] = round(result.layer_scores["layer3"], 4) if "layer3" in result.layer_scores else ""
    if result.layer3_results and "error" not in result.layer3_results:
        row["layer3_level"] = result.layer3_results.get("identity_note", {}).get("level", "")
        row["combination_strength"] = result.layer3_results.get("combination", {}).get("strength", "")
    row["reasons"] = "; ".join(sum(result.reasons.values(), [])) if result.reasons else ""
    row["sb_verdict"] = safe_browsing_lookup(url) or ""
    row["status"] = "ok"
    return row


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return
    urls = [r["url"] for r in csv.DictReader(open(sys.argv[1]))]
    skip = done_urls()
    todo = [u for u in urls if u not in skip]
    print(f"{len(todo)} URLs to check ({len(skip)} already done)")
    if SB_API_KEY:
        print("Safe Browsing comparison: ON")
    else:
        print("Safe Browsing comparison: OFF (set GOOGLE_SAFE_BROWSING_API_KEY to enable)")

    finder_js = load_finder_js()
    new_file = not os.path.exists(OUTPUT_PATH) or os.path.getsize(OUTPUT_PATH) == 0
    with open(OUTPUT_PATH, "a", newline="") as out, sync_playwright() as p:
        writer = csv.DictWriter(out, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        browser = p.chromium.launch()
        context = browser.new_context(viewport=VIEWPORT, ignore_https_errors=True)
        page = context.new_page()
        for i, url in enumerate(todo, 1):
            if i > 1 and (i - 1) % 50 == 0:
                page.close()
                browser.close()
                browser = p.chromium.launch()
                context = browser.new_context(viewport=VIEWPORT, ignore_https_errors=True)
                page = context.new_page()
            try:
                row = check_one(page, finder_js, url)
            except Exception as exc:
                row = {k: "" for k in FIELDS}
                row["url"] = url
                row["loaded"] = False
                row["status"] = f"error: {type(exc).__name__}"
                try:
                    page.close()
                    page = context.new_page()
                except Exception:
                    browser.close()
                    browser = p.chromium.launch()
                    context = browser.new_context(viewport=VIEWPORT, ignore_https_errors=True)
                    page = context.new_page()
            writer.writerow(row)
            out.flush()
            print(f"[{i}/{len(todo)}] {url[:70]} -> loaded={row['loaded']} verdict={row.get('verdict') or '-'} sb={row.get('sb_verdict') or '-'}")
        browser.close()

    with open(OUTPUT_PATH, newline="") as f:
        rows = list(csv.DictReader(f))
    loaded = [r for r in rows if r["loaded"] == "True"]
    phishing_or_susp = [r for r in loaded if r["verdict"] in ("phishing", "suspicious")]
    print()
    print(f"attempted: {len(rows)}  loaded: {len(loaded)}  flagged (suspicious+phishing): {len(phishing_or_susp)}")
    if loaded:
        print(f"detection rate on live phishing URLs: {100 * len(phishing_or_susp) / len(loaded):.1f}%")
    timed = sorted(float(r["analysis_ms"]) for r in loaded if r.get("analysis_ms"))
    if timed:
        mid = timed[len(timed) // 2]
        print(f"end-to-end full-scan time (Layer 1+2+3 together): "
              f"min={timed[0]:.0f}ms  median={mid:.0f}ms  max={timed[-1]:.0f}ms  n={len(timed)}")
    for layer_key, layer_label in (("layer1_ms", "Layer 1"), ("layer2_ms", "Layer 2"), ("layer3_ms", "Layer 3")):
        vals = sorted(float(r[layer_key]) for r in loaded if r.get(layer_key))
        if vals:
            vmid = vals[len(vals) // 2]
            print(f"  {layer_label} alone: min={vals[0]:.0f}ms  median={vmid:.0f}ms  max={vals[-1]:.0f}ms  n={len(vals)}")
    if SB_API_KEY:
        sb_flagged = [r for r in loaded if r["sb_verdict"] == "flagged"]
        we_flagged_sb_did_not = [r for r in loaded if r["sb_verdict"] == "clean" and r["verdict"] in ("phishing", "suspicious")]
        print(f"Safe Browsing flagged: {len(sb_flagged)} of {len(loaded)}")
        print(f"we flagged but Safe Browsing did not (the zero-day-gap cases - recheck these tomorrow to see if SB catches up): {len(we_flagged_sb_did_not)}")
        for r in we_flagged_sb_did_not:
            print(f"  {r['url']}")


if __name__ == "__main__":
    main()
