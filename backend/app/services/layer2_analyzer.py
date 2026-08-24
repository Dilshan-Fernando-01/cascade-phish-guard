
from features.brand_deception_features import extract_brand_features
from features.behavioral_features import extract_behavioral_features
from features.dom_features import extract_structural_features
from services.embedded_url_analyzer import analyze_embedded_urls
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


def analyze_layer2(url):
    loaded = load_page(url)
    if not loaded["success"]:
        return {"success": False, "features": None, "error": loaded["error"]}

    html = loaded["html"]
    final_url = loaded["final_url"]

    features = {}
    features.update(extract_structural_features(html, final_url))
    features.update(extract_brand_features(html, final_url))
    features.update(extract_behavioral_features(html))
    features.update(analyze_embedded_urls(html, final_url, loaded["network_urls"]))

    return {"success": True, "features": features, "error": None}
