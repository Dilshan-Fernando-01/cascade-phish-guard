MAX_REASONS = 3


def _limit(reasons):
    return reasons[:MAX_REASONS]


def layer1_reasons(features):
    if not features:
        return []
    reasons = []
    if features.get("brand_keyword_in_host") == 1:
        reasons.append("The address contains the name of a known brand.")
    distance = features.get("brand_distance_score") or 0
    if 0 < distance <= 2 and not features.get("brand_keyword_in_host"):
        reasons.append("The address is a small spelling change from a known brand's name.")
    if features.get("is_punycode_or_homograph") == 1:
        reasons.append("The address uses look-alike characters.")
    if features.get("has_ip_host") == 1:
        reasons.append("The address uses a numeric IP instead of a name.")
    if (features.get("tld_risk_score") or 0) >= 1.0:
        reasons.append("The address uses an ending often used by suspicious sites.")
    if features.get("domain_age_days") is None:
        reasons.append("No registration date could be found for this domain.")
    if features.get("tranco_rank_bucket") == 0:
        reasons.append("This domain is not in a common site ranking list.")
    return _limit(reasons)


def layer2_reasons(features):
    if not features or "error" in features:
        return []
    reasons = []
    if (features.get("password_input_count") or 0) > 0:
        reasons.append("This page asks for a password.")
    if (features.get("external_form_action") or 0) > 0:
        reasons.append("A form on this page sends data to another site.")
    if (features.get("suspicious_embedded_url_count") or 0) > 0:
        reasons.append("Some links on this page lead to suspicious addresses.")
    if features.get("fake_browser_chrome_detected") == 1:
        reasons.append("The page imitates a browser window.")
    if features.get("overlay_detected") == 1:
        reasons.append("Part of the page is covered by an overlay.")
    if features.get("meta_redirect_present") == 1:
        reasons.append("The page redirects automatically.")
    return _limit(reasons)


def layer3_reasons(layer3_results):
    if not layer3_results or "error" in layer3_results:
        return []
    reasons = []
    combination = layer3_results.get("combination") or {}
    if combination.get("brand_mismatch"):
        reasons.append("The page shows a known brand's logo, but its address is not that brand's.")
    if combination.get("input_signal") and combination.get("brand_mismatch"):
        reasons.append("A page that copies a known brand's logo asks the visitor for information.")
    background = layer3_results.get("background") or {}
    if background.get("status") == "checked" and background.get("band") == "strong":
        reasons.append("The logo on the brand's own home page matches the logo on this page.")
    region = background.get("region") or {}
    if region.get("status") == "checked" and region.get("both_match"):
        reasons.append("This page's layout matches the brand's own home page.")
   
    wording = layer3_results.get("banner_wording_check") or {}
    if wording.get("status") == "checked" and wording.get("matched_phrases"):
        reasons.append("Urgent wording was found at the top of the page (provisional check).")
    return _limit(reasons)



PUBLIC_SUMMARY = {
    "layer1": "The web address needs a closer look.",
    "layer2": "The page content needs a closer look.",
    "layer3": "The page's visual identity needs a closer look.",
}


def public_reasons(detailed, verdict):
   
    if verdict == "safe" or not detailed:
        return {}
    return {layer: [PUBLIC_SUMMARY[layer]] for layer, items in detailed.items() if items}
