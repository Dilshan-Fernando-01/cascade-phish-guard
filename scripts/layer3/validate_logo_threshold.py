
import argparse
import csv
import io
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend", "app"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "layer3"))

from services.layer2_analyzer import _looks_like_bot_challenge  # noqa: E402
from logo_identity import get_embedding, load_model, load_reference_cache  # noqa: E402

WEIGHTS_PATH = os.path.join(ROOT, "data", "external", "phishpedia", "resnetv2_rgb_new.pth.tar")
OLD_CACHE_PATH = os.path.join(ROOT, "data", "backups", "layer3_pre_threshold_work_2026-10-15", "logo_reference_embeddings.pkl")
NEW_CACHE_PATH = os.path.join(ROOT, "data", "external", "phishpedia", "logo_reference_embeddings_whitebg.pkl")
FINDER_SOURCE = os.path.join(ROOT, "extension", "layer3_capture.js")
OUTPUT_PATH = os.path.join(ROOT, "data", "reports", "logo_threshold_validation.csv")

VIEWPORT = {"width": 1280, "height": 800}
PAGE_TIMEOUT_MS = 20000
MAX_WORKERS = 8
BANNER_BAND_PX = 300

FIELDS = ["rank", "domain", "brand", "status", "found_logo", "old_best_sim", "new_best_sim"]


def load_finder_js():
    src = open(FINDER_SOURCE).read()
    return src[src.index("function findLogoCandidatesInPage"): src.index("function blobToBase64")].strip()


def best_similarity(crop_bitmap, model, embeddings, file_paths, brand):
    emb = get_embedding(crop_bitmap, model)
    best = None
    brand_lower = brand.lower()
    for i, p in enumerate(file_paths):
        folder = os.path.basename(os.path.dirname(p))
        if folder.lower() != brand_lower:
            continue
        ref = embeddings[i]
        sim = float(np.dot(emb, ref) / (np.linalg.norm(emb) * np.linalg.norm(ref)))
        if best is None or sim > best:
            best = sim
    return best


def check_one(page, finder_js, candidate, model, old_embeddings, old_paths, new_embeddings, new_paths):
    row = {k: "" for k in FIELDS}
    row["rank"] = candidate["rank"]
    row["domain"] = candidate["domain"]
    row["brand"] = candidate["brand"]
    url = f"https://{candidate['domain']}"
    try:
        response = page.goto(url, wait_until="load", timeout=PAGE_TIMEOUT_MS)
        try:
            page.wait_for_load_state("networkidle", timeout=6000)
        except Exception:
            pass
        page.wait_for_timeout(800)
        html = page.content()
    except Exception:
        row["status"] = "did_not_load"
        return row

    status = response.status if response is not None else None
    if status is not None and not (200 <= status < 300):
        row["status"] = f"http_{status}"
        return row

    if _looks_like_bot_challenge(html, None):
        row["status"] = "bot_blocked"
        return row

    found = page.evaluate("(" + finder_js + ")()")
    best = found.get("best")
    row["found_logo"] = bool(best)
    if not best:
        row["status"] = "no_logo_found"
        return row

    full_png = page.screenshot(full_page=False)
    bitmap = Image.open(io.BytesIO(full_png)).convert("RGB")
    dpr = found.get("devicePixelRatio", 1)
    sx = max(0, int(best["x"] * dpr))
    sy = max(0, int(best["y"] * dpr))
    sw = min(bitmap.width - sx, int(best["w"] * dpr) + 1)
    sh = min(bitmap.height - sy, int(best["h"] * dpr) + 1)
    if sw <= 0 or sh <= 0:
        row["status"] = "crop_failed"
        return row
    crop = bitmap.crop((sx, sy, sx + sw, sy + sh))

    try:
        row["old_best_sim"] = best_similarity(crop, model, old_embeddings, old_paths, candidate["brand"])
        row["new_best_sim"] = best_similarity(crop, model, new_embeddings, new_paths, candidate["brand"])
        row["status"] = "ok"
    except Exception as exc:
        row["status"] = f"embedding_error: {type(exc).__name__}"
    return row


def worker(candidates, finder_js, model, old_embeddings, old_paths, new_embeddings, new_paths, results, lock):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport=VIEWPORT, ignore_https_errors=True)
        page = context.new_page()
        count = 0
        for candidate in candidates:
            if count > 0 and count % 40 == 0:
                page.close()
                browser.close()
                browser = p.chromium.launch()
                context = browser.new_context(viewport=VIEWPORT, ignore_https_errors=True)
                page = context.new_page()
            count += 1
            try:
                row = check_one(page, finder_js, candidate, model, old_embeddings, old_paths, new_embeddings, new_paths)
            except Exception as exc:
                row = {k: "" for k in FIELDS}
                row["rank"] = candidate["rank"]
                row["domain"] = candidate["domain"]
                row["brand"] = candidate["brand"]
                row["status"] = f"error: {type(exc).__name__}"
            with lock:
                results.append(row)
        browser.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=450)
    parser.add_argument("--candidates", default="/tmp/legit_logo_candidates.json")
    args = parser.parse_args()

    with open(args.candidates) as f:
        candidates = json.load(f)[: args.limit]
    print(f"{len(candidates)} candidates queued")

    finder_js = load_finder_js()
    model = load_model(WEIGHTS_PATH)
    old_embeddings, old_paths = load_reference_cache(OLD_CACHE_PATH)
    new_embeddings, new_paths = load_reference_cache(NEW_CACHE_PATH)
    print("model and reference caches loaded")

    chunks = [candidates[i::MAX_WORKERS] for i in range(MAX_WORKERS)]
    results = []
    lock = __import__("threading").Lock()
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [
            ex.submit(worker, chunk, finder_js, model, old_embeddings, old_paths, new_embeddings, new_paths, results, lock)
            for chunk in chunks
        ]
        done = 0
        total = len(candidates)
        while done < total:
            time.sleep(10)
            with lock:
                done = len(results)
            print(f"[{done}/{total}] done - {time.time()-t0:.0f}s elapsed")
        for f in futures:
            f.result()

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in results:
            writer.writerow(row)
    print(f"\nwrote {len(results)} rows to {OUTPUT_PATH}")

    ok = [r for r in results if r["status"] == "ok"]
    print(f"\nsummary: {len(results)} attempted, {len(ok)} successfully captured+matched")
    from collections import Counter
    print("status breakdown:", Counter(r["status"] for r in results))


if __name__ == "__main__":
    main()
