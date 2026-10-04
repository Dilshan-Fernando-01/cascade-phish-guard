

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


def compare_with_brand(logo_png, brand_domain):
    """Compare a logo with one brand's cached reference logos. Returns band and similarity."""
    import numpy as np

    from services import layer3_analyzer as l3

    state = l3._load_logo_state()
    ref_domains = l3._ref_brand_domains(state)
    l3._ensure_logo_path()
    from logo_identity import get_embedding

    indexes = [i for i, doms in enumerate(ref_domains) if brand_domain in doms]
    if not indexes:
        return {"band": "no reference logos", "similarity": None}
    embedding = get_embedding(Image.open(io.BytesIO(logo_png)), state["model"])
    sims = state["ref_embeddings"].dot(embedding)
    best = float(np.max(sims[indexes]))
    return {"band": l3._band(best), "similarity": round(best, 4)}


def background_check(url, brand_domain):
    """The full background check for one visited URL and one claimed brand domain."""
    logo_png, reason = fetch_root_logo_png(url)
    if logo_png is None:
        return {"status": STATUS_COULD_NOT_CONFIRM, "reason": reason, "brand_domain": brand_domain}
    result = compare_with_brand(logo_png, brand_domain)
    return {"status": STATUS_CHECKED, "brand_domain": brand_domain, **result}
