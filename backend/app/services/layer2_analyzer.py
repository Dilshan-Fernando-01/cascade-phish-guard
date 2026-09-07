from urllib.parse import urlparse

from bs4 import BeautifulSoup

from features.brand_deception_features import extract_brand_features
from features.behavioral_features import extract_behavioral_features
from features.dom_features import extract_structural_features
from services.embedded_url_analyzer import _is_known_waf_vendor, analyze_embedded_urls
from services.page_loader import load_page


LAYER2_FEATURE_COLUMNS = [
    "form_count", "password_input_count", "hidden_input_count",
    "external_script_count", "external_form_action", "external_resource_ratio",
    "iframe_count", "meta_redirect_present", "link_to_text_ratio", "dom_tree_depth",
    "favicon_domain_mismatch", "title_domain_mismatch", "brand_keyword_mismatch",
    "overlay_detected", "css_anomaly_score", "fake_browser_chrome_detected",
    "script_obfuscation_score", "suspicious_js_pattern_count", "social_engineering_score",
    "suspicious_embedded_url_count", "max_embedded_url_risk", "avg_embedded_url_risk",
]

SPARSE_PAGE_BYTE_LIMIT = 5000


def _looks_like_bot_challenge(html, network_urls=None):
    if not html or len(html) > SPARSE_PAGE_BYTE_LIMIT:
        return False
    soup = BeautifulSoup(html, "html.parser")
    script_srcs = [tag.get("src") for tag in soup.find_all("script", src=True)]
    for candidate in script_srcs + list(network_urls or []):
        if not candidate:
            continue
        host = urlparse(candidate).netloc.split(":")[0]
        if _is_known_waf_vendor(host):
            return True
    return False


def analyze_layer2(url):
    loaded = load_page(url)
    if not loaded["success"]:
        return {"success": False, "features": None, "error": loaded["error"]}

    html = loaded["html"]
    final_url = loaded["final_url"]

    if _looks_like_bot_challenge(html, loaded["network_urls"]):
        return {
            "success": False,
            "features": None,
            "error": "page appears to be a bot-verification challenge, not the site's real content",
        }

    features = {}
    features.update(extract_structural_features(html, final_url))
    features.update(extract_brand_features(html, final_url))
    features.update(extract_behavioral_features(html))
    features.update(analyze_embedded_urls(html, final_url, loaded["network_urls"]))

    return {"success": True, "features": features, "error": None}
