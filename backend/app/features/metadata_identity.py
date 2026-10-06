import json
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .url_features import _registrable_domain_guess


def _declared_name(soup):
    for attrs in ({"property": "og:site_name"}, {"name": "application-name"}):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            return tag["content"].strip()
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
        except (ValueError, TypeError):
            continue
        for item in data if isinstance(data, list) else [data]:
            if isinstance(item, dict) and item.get("@type") == "Organization" and item.get("name"):
                return str(item["name"]).strip()
    return None


def _declared_address(soup):
    link = soup.find("link", attrs={"rel": "canonical"})
    if link and link.get("href"):
        return link["href"].strip()
    tag = soup.find("meta", attrs={"property": "og:url"})
    if tag and tag.get("content"):
        return tag["content"].strip()
    return None


def _name_matches_domain(name, registrable):
    if not name or not registrable:
        return None
    domain_name = registrable.split(".")[0].lower()
    words = [w.lower() for w in re.findall(r"[A-Za-z]+", name)]
    if any(len(w) >= 3 and w in domain_name for w in words):
        return True
    initials = "".join(w[0] for w in words if w)
    return len(initials) >= 3 and (initials == domain_name or domain_name.startswith(initials))


def metadata_identity(html, page_url):
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    name = _declared_name(soup)
    address = _declared_address(soup)
    if not name and not address:
        return None

    page_domain = _registrable_domain_guess(urlparse(page_url).netloc.split(":")[0])
    declared_domain = None
    if address:
        host = urlparse(address).netloc.split(":")[0]
        declared_domain = _registrable_domain_guess(host) if host else None

    address_mismatch = bool(declared_domain) and bool(page_domain) and declared_domain != page_domain
    name_fits_address = _name_matches_domain(name, page_domain)

    return {
        "declared_name": name,
        "declared_address_domain": declared_domain,
        "address_mismatch": address_mismatch,
        "name_fits_address": name_fits_address,
        "strong": address_mismatch and name_fits_address is False,
    }
