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
    if features.get("has_at_symbol") == 1:
        reasons.append("The address contains an '@' symbol, which can hide the real destination.")
    if (features.get("tld_risk_score") or 0) >= 1.0:
        reasons.append("The address uses an ending often used by suspicious sites.")
    if features.get("domain_age_days") is None:
        reasons.append("No registration date could be found for this domain.")
    if features.get("tranco_rank_bucket") == 0:
        reasons.append("This domain is not in a common site ranking list.")
    return _limit(reasons)


def layer1_reassurances(features):

    if not features:
        return []
    reasons = []
    age = features.get("domain_age_days")
    if age is not None and age >= 365:
        years = age / 365
        reasons.append(f"This domain has a registration history of about {years:.0f} year{'s' if years >= 2 else ''}.")
    if features.get("tranco_rank_bucket", 0) and features.get("tranco_rank_bucket") > 0:
        reasons.append("This domain appears in a recognized site popularity ranking.")
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
        reasons.append("The page draws a fake address bar or browser toolbar as part of its own content, to look more trustworthy than it is.")
    if features.get("overlay_detected") == 1:
        reasons.append("Part of the page is covered by an overlay.")
    if features.get("meta_redirect_present") == 1:
        reasons.append("The page redirects automatically.")
    if features.get("favicon_domain_mismatch") == 1:
        reasons.append("The page's icon is loaded from a different site than the one you're on.")
    if features.get("brand_keyword_mismatch") == 1:
        reasons.append("The page's text names a well-known brand (e.g. \"Roblox\", \"Amazon\"), but the web address isn't that brand's real site.")
    return _limit(reasons)


def layer2_reassurances(features):
    if not features or "error" in features:
        return []
    reasons = []
    checked = features.get("checked_embedded_url_count") or 0
    suspicious = features.get("suspicious_embedded_url_count") or 0
    if checked > 0 and suspicious == 0:
        reasons.append(f"{checked} link(s) found on this page were checked and showed no suspicious pattern.")
    if (features.get("password_input_count") or 0) == 0 and (features.get("form_count") or 0) > 0:
        reasons.append("This page has forms, but none of them ask for a password.")
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


def layer3_reassurances(layer3_results):
    if not layer3_results or "error" in layer3_results:
        return []
    reasons = []
    logo_check = layer3_results.get("logo_check") or {}
    if logo_check.get("status") == "checked" and not logo_check.get("mismatch"):
        reasons.append("The logo found on this page matched the address it's hosted on.")
    if logo_check.get("status") == "not_found":
        reasons.append("No clear brand logo was found on this page to compare.")
    return _limit(reasons)


def dev_explanation(layer1_features, layer2_features, layer3_results):


    def _combine(concerns, reassurances, nothing_found_text):
        if not concerns and not reassurances:
            return [nothing_found_text]
        return concerns + reassurances

    return {
        "layer1": _combine(
            layer1_reasons(layer1_features),
            layer1_reassurances(layer1_features),
            "No notable address-based signals were detected for this site.",
        ),
        "layer2": _combine(
            layer2_reasons(layer2_features),
            layer2_reassurances(layer2_features),
            "No notable page-content signals were detected for this site.",
        ),
        "layer3": _combine(
            layer3_reasons(layer3_results),
            layer3_reassurances(layer3_results),
            "Visual identity comparison did not run or found nothing to report.",
        ),
    }



PUBLIC_SUMMARY = {
    "layer1": "The web address needs a closer look.",
    "layer2": "The page content needs a closer look.",
    "layer3": "The page's visual identity needs a closer look.",
}


def public_reasons(detailed, verdict):
   
    if verdict == "safe" or not detailed:
        return {}
    return {layer: [PUBLIC_SUMMARY[layer]] for layer, items in detailed.items() if items}
