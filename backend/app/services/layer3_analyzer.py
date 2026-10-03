import os
import pickle
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
LAYER3_SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts", "layer3")
PHISHPEDIA_DIR = os.path.join(PROJECT_ROOT, "data", "external", "phishpedia")
WEIGHTS_PATH = os.path.join(PHISHPEDIA_DIR, "resnetv2_rgb_new.pth.tar")
CACHE_PATH = os.path.join(PHISHPEDIA_DIR, "logo_reference_embeddings.pkl")
DOMAIN_MAP_PATH = os.path.join(PHISHPEDIA_DIR, "domain_map.pkl")

LOGO_CHECK = "logo_check"
BANNER_WORDING_CHECK = "banner_wording_check"

STATUS_CHECKED = "checked"
STATUS_NO_LOGO = "no_logo_provided"
STATUS_UNAVAILABLE = "unavailable"
STATUS_NO_SCREENSHOT = "no_screenshot_provided"
STATUS_UNREADABLE = "unreadable"

_logo_state = None


def _ensure_logo_path():
    if LAYER3_SCRIPTS_DIR not in sys.path:
        sys.path.insert(0, LAYER3_SCRIPTS_DIR)


def _load_logo_state():
    global _logo_state
    if _logo_state is not None:
        return _logo_state
    _ensure_logo_path()
    from logo_identity import load_model, load_reference_cache

    with open(DOMAIN_MAP_PATH, "rb") as f:
        domain_map = pickle.load(f)
    model = load_model(WEIGHTS_PATH)
    ref_embeddings, ref_file_paths = load_reference_cache(CACHE_PATH)
    _logo_state = {
        "model": model,
        "domain_map": domain_map,
        "ref_embeddings": ref_embeddings,
        "ref_file_paths": ref_file_paths,
    }
    return _logo_state


def _logo_check(url, logo_png):
    if logo_png is None:
        return {"status": STATUS_NO_LOGO}
    if not os.path.exists(WEIGHTS_PATH) or not os.path.exists(CACHE_PATH):
        return {"status": STATUS_UNAVAILABLE, "reason": "reference model or logo cache missing on this machine"}

    import io

    from PIL import Image

    _ensure_logo_path()
    from logo_identity import check_domain_brand_mismatch

    state = _load_logo_state()
    crop = Image.open(io.BytesIO(logo_png))
    result = check_domain_brand_mismatch(
        crop,
        url,
        state["model"],
        state["ref_embeddings"],
        state["ref_file_paths"],
        state["domain_map"],
    )
    return {"status": STATUS_CHECKED, **result}


def _banner_wording_check(screenshot_png):
    if screenshot_png is None:
        return {"status": STATUS_NO_SCREENSHOT}
    if not _ocr_available():
        return {"status": STATUS_UNAVAILABLE, "reason": "text recognition (tesseract) not installed on this machine"}

    from features.banner_wording import banner_wording_features

    try:
        return {"status": STATUS_CHECKED, **banner_wording_features(screenshot_png)}
    except Exception:
        return {"status": STATUS_UNREADABLE, "reason": "screenshot could not be read as an image"}


def _ocr_available():
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def analyze_layer3(url, screenshot_png, html=None, logo_png=None):

    return {
        LOGO_CHECK: _logo_check(url, logo_png),
        BANNER_WORDING_CHECK: _banner_wording_check(screenshot_png),
    }
