
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "backend", "app"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PIL import Image
from playwright.sync_api import sync_playwright

from services.layer3_analyzer import _logo_check

SITES = [
    "https://www.microsoft.com",
    "https://www.cloudflare.com",
    "https://github.com",
    "https://www.apple.com",
    "https://www.google.com",
]
FAKE_DOMAIN = "http://{brand}-account-verify.tk/secure"


def load_finder_js():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    src = open(os.path.join(root, "extension", "layer3_capture.js")).read()
    return src[src.index("function findLogoCandidatesInPage"): src.index("function blobToBase64")].strip()


def capture_logo(page, finder_js):
    try:
        page.wait_for_load_state("networkidle", timeout=6000)
    except Exception:
        pass
    page.wait_for_timeout(1000)
    found = page.evaluate("(" + finder_js + ")()")
    best = found.get("best")
    if not best:
        return None, found
    full_png = page.screenshot(full_page=False)
    bitmap = Image.open(io.BytesIO(full_png)).convert("RGB")
    dpr = found.get("devicePixelRatio", 1)
    sx, sy = max(0, int(best["x"] * dpr)), max(0, int(best["y"] * dpr))
    sw = min(bitmap.width - sx, int(best["w"] * dpr) + 1)
    sh = min(bitmap.height - sy, int(best["h"] * dpr) + 1)
    crop = bitmap.crop((sx, sy, sx + sw, sy + sh))
    buf = io.BytesIO()
    crop.save(buf, "PNG")
    return buf.getvalue(), found


def main():
    finder_js = load_finder_js()
    failures = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width": 1280, "height": 800}, ignore_https_errors=True).new_page()
        for url in SITES:
            try:
                page.goto(url, wait_until="load", timeout=20000)
            except Exception as exc:
                print(f"[SKIP] {url} did not load: {exc}")
                continue
            logo_png, found = capture_logo(page, finder_js)
            if logo_png is None:
                print(f"[FAIL] {url}: no logo found at all (considered={found.get('considered')}, kept={found.get('kept')})")
                failures.append(url)
                continue

            own = _logo_check(url, logo_png)
            own_ok = own["identified_brand"] is not None and own["mismatch"] is False
            status = "PASS" if own_ok else "FAIL"
            print(f"[{status}] {url}: self-match -> brand={own['identified_brand']} similarity={own['similarity']:.4f} mismatch={own['mismatch']}")
            if not own_ok:
                failures.append(url + " (self-match)")

            brand_slug = (own["identified_brand"] or "test").lower().replace(" ", "")
            fake_url = FAKE_DOMAIN.format(brand=brand_slug)
            mismatch_result = _logo_check(fake_url, logo_png)
            mismatch_ok = mismatch_result["mismatch"] is True
            status = "PASS" if mismatch_ok else "FAIL"
            print(f"[{status}] same logo on a fake domain -> mismatch={mismatch_result['mismatch']} (expected True)")
            if not mismatch_ok:
                failures.append(url + " (mismatch-detection)")
        browser.close()

    print()
    if failures:
        print(f"{len(failures)} check(s) failed:")
        for f in failures:
            print(" -", f)
    else:
        print("All checks passed.")


if __name__ == "__main__":
    main()
