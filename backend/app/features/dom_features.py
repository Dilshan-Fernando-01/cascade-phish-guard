from urllib.parse import urlparse

from bs4 import BeautifulSoup


def _hostname(url):
    if not url:
        return ""
    try:
        return urlparse(url).netloc.split(":")[0].lower()
    except Exception:
        return ""


def _is_external(resource_url, page_host):
    if not resource_url or not page_host:
        return False
    if resource_url.startswith(("data:", "javascript:", "#", "mailto:")):
        return False
    resource_host = _hostname(resource_url) if "//" in resource_url else ""
    return bool(resource_host) and resource_host != page_host


def _dom_depth(tag, depth=0):
    children = [c for c in getattr(tag, "children", []) if getattr(c, "name", None)]
    if not children:
        return depth
    return max(_dom_depth(child, depth + 1) for child in children)


def extract_structural_features(html, final_url):

    soup = BeautifulSoup(html or "", "html.parser")
    page_host = _hostname(final_url)

    forms = soup.find_all("form")
    password_inputs = soup.find_all("input", attrs={"type": "password"})
    hidden_inputs = soup.find_all("input", attrs={"type": "hidden"})
    scripts = soup.find_all("script", src=True)
    iframes = soup.find_all("iframe")
    images = soup.find_all("img", src=True)
    stylesheets = soup.find_all("link", href=True)

    external_script_count = sum(1 for s in scripts if _is_external(s.get("src"), page_host))
    external_form_action = sum(1 for f in forms if _is_external(f.get("action"), page_host))

    resource_tags = scripts + images + stylesheets + iframes
    resource_urls = [t.get("src") or t.get("href") for t in resource_tags]
    external_resource_count = sum(1 for u in resource_urls if _is_external(u, page_host))
    external_resource_ratio = (
        external_resource_count / len(resource_urls) if resource_urls else 0.0
    )

    meta_redirect_present = int(
        bool(soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"}))
    )

    links = soup.find_all("a")
    visible_text = soup.get_text(separator=" ", strip=True)
    word_count = len(visible_text.split())
    link_to_text_ratio = len(links) / word_count if word_count else float(len(links))

    body = soup.find("body") or soup
    try:
        dom_tree_depth = _dom_depth(body)
    except RecursionError:
       
        dom_tree_depth = 9999

    return {
        "form_count": len(forms),
        "password_input_count": len(password_inputs),
        "hidden_input_count": len(hidden_inputs),
        "external_script_count": external_script_count,
        "external_form_action": external_form_action,
        "external_resource_ratio": round(external_resource_ratio, 4),
        "iframe_count": len(iframes),
        "meta_redirect_present": meta_redirect_present,
        "link_to_text_ratio": round(link_to_text_ratio, 4),
        "dom_tree_depth": dom_tree_depth,
    }
