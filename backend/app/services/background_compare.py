

import io
import os
from urllib.parse import urlparse

from PIL import Image
from playwright.sync_api import sync_playwright

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
FINDER_SOURCE = os.path.join(PROJECT_ROOT, "extension", "layer3_capture.js")

VIEWPORT = {"width": 1280, "height": 800}
PAGE_TIMEOUT_MS = 15000
SETTLE_MS = 1500

STATUS_CHECKED = "checked"
STATUS_COULD_NOT_CONFIRM = "could not confirm"


def _finder_js():
    src = open(FINDER_SOURCE).read()
    return src[src.index("function findLogoCandidatesInPage"): src.index("function blobToBase64")].strip()


def _root_url(url):
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}/"


def fetch_root_logo_png(url):
    """Return (logo_png_bytes, None) on success, or (None, reason)."""
    # Imported here so that importing this module never loads the model
    from services.layer2_analyzer import _looks_like_bot_challenge

    finder = _finder_js()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                context = browser.new_context(viewport=VIEWPORT, ignore_https_errors=False)
                page = context.new_page()
                try:
                    page.goto(_root_url(url), wait_until="load", timeout=PAGE_TIMEOUT_MS)
                    page.wait_for_timeout(SETTLE_MS)
                    html = page.content()
                except Exception:
                    return None, "the site's home page did not load"
                if _looks_like_bot_challenge(html, None):
                    return None, "the site showed a bot check"

                best = page.evaluate("(" + finder + ")()").get("best")
                if not best:
                    return None, "no logo found on the site's home page"

                shot = Image.open(io.BytesIO(page.screenshot(full_page=False))).convert("RGB")
                x, y, w, h = int(best["x"]), int(best["y"]), int(best["w"]), int(best["h"])
                buf = io.BytesIO()
                shot.crop((x, y, x + w, y + h)).save(buf, "PNG")
                return buf.getvalue(), None
            finally:
                browser.close()
    except Exception as exc:
        return None, f"background check unavailable ({type(exc).__name__})"


def compare_logo_pair(visited_png, brand_png):

    import numpy as np

    from services import layer3_analyzer as l3

    state = l3._load_logo_state()
    l3._ensure_logo_path()
    from logo_identity import get_embedding

    model = state["model"]
    visited = get_embedding(Image.open(io.BytesIO(visited_png)), model)
    brand = get_embedding(Image.open(io.BytesIO(brand_png)), model)
    similarity = float(np.dot(visited, brand))
    return {"band": l3._band(similarity), "similarity": round(similarity, 4)}


def background_check(url, brand_domain):

    visited_png, reason = fetch_root_logo_png(url)
    if visited_png is None:
        return {"status": STATUS_COULD_NOT_CONFIRM, "reason": f"visited site: {reason}", "brand_domain": brand_domain}
    brand_png, reason = fetch_root_logo_png(f"https://{brand_domain}/")
    if brand_png is None:
        return {"status": STATUS_COULD_NOT_CONFIRM, "reason": f"brand's home page: {reason}", "brand_domain": brand_domain}
    result = compare_logo_pair(visited_png, brand_png)
    return {"status": STATUS_CHECKED, "brand_domain": brand_domain, "source": "live", **result}
