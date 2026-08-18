
from features.brand_deception_features import extract_brand_features
from features.behavioral_features import extract_behavioral_features
from features.dom_features import extract_structural_features
from services.embedded_url_analyzer import analyze_embedded_urls
from services.page_loader import load_page


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
