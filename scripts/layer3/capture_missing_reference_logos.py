
import argparse
import io
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TARGETLIST = os.path.join(ROOT, "data", "external", "phishpedia", "expand_targetlist")
FINDER_SOURCE = os.path.join(ROOT, "extension", "layer3_capture.js")

VIEWPORT = {"width": 1280, "height": 800}
PAGE_TIMEOUT_MS = int(os.environ.get("CAPTURE_TIMEOUT_MS", "20000"))
MAX_WORKERS = 8


def load_finder_js():
    src = open(FINDER_SOURCE).read()
    return src[src.index("function findLogoCandidatesInPage"): src.index("function blobToBase64")].strip()


def capture_one(page, finder_js, candidate):
    domain, brand = candidate["domain"], candidate["brand"]
    url = f"https://{domain}"
    try:
        page.goto(url, wait_until="load", timeout=PAGE_TIMEOUT_MS)
        try:
            page.wait_for_load_state("networkidle", timeout=6000)
        except Exception:
            pass
        page.wait_for_timeout(800)
    except Exception as exc:
        return None, f"did_not_load: {exc}"

    found = page.evaluate("(" + finder_js + ")()")
    best = found.get("best")
    if not best:
        return None, "no_logo_found"

    full_png = page.screenshot(full_page=False)
    bitmap = Image.open(io.BytesIO(full_png)).convert("RGB")
    dpr = found.get("devicePixelRatio", 1)
    sx = max(0, int(best["x"] * dpr))
    sy = max(0, int(best["y"] * dpr))
    sw = min(bitmap.width - sx, int(best["w"] * dpr) + 1)
    sh = min(bitmap.height - sy, int(best["h"] * dpr) + 1)
    if sw <= 0 or sh <= 0:
        return None, "crop_failed"
    crop = bitmap.crop((sx, sy, sx + sw, sy + sh))

    brand_dir = os.path.join(TARGETLIST, brand)
    os.makedirs(brand_dir, exist_ok=True)
    out_path = os.path.join(brand_dir, "captured_1.png")
    crop.save(out_path)
    return out_path, "ok"


def worker(candidates, finder_js, results, lock):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport=VIEWPORT, ignore_https_errors=True)
        page = context.new_page()
        for candidate in candidates:
            try:
                path, status = capture_one(page, finder_js, candidate)
            except Exception as exc:
                path, status = None, f"error: {type(exc).__name__}"
            with lock:
                results.append({"domain": candidate["domain"], "brand": candidate["brand"], "status": status, "path": path})
        browser.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", default="/tmp/missing_brands_clean.json")
    parser.add_argument("--results-out", default="/tmp/missing_brands_capture_results.json")
    args = parser.parse_args()
    with open(args.candidates) as f:
        candidates = json.load(f)
    print(f"{len(candidates)} candidates queued")

    finder_js = load_finder_js()
    chunks = [candidates[i::MAX_WORKERS] for i in range(MAX_WORKERS)]
    results = []
    lock = __import__("threading").Lock()
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(worker, chunk, finder_js, results, lock) for chunk in chunks]
        done = 0
        total = len(candidates)
        while done < total:
            time.sleep(10)
            with lock:
                done = len(results)
            print(f"[{done}/{total}] done - {time.time()-t0:.0f}s elapsed")
        for f in futures:
            f.result()

    ok = [r for r in results if r["status"] == "ok"]
    print(f"\n{len(ok)} of {len(results)} new brand reference images successfully captured")
    from collections import Counter
    print("status breakdown:", Counter(r["status"] for r in results))

    with open(args.results_out, "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
