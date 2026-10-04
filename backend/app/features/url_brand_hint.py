from rapidfuzz.distance import Levenshtein

from .brand_reference import BRAND_DOMAINS
from .url_features import _registrable_domain_guess

MIN_KEYWORD_LEN = 4
MIN_FUZZY_LEN = 5
MAX_EDIT_DISTANCE = 2


def _name(domain):
    return domain.split(".")[0]


def url_brand_hints(host, top_k=3):

    registrable = _registrable_domain_guess(host)
    if not registrable:
        return []
    own_name = _name(registrable)

    hints = []
    for brand in BRAND_DOMAINS:
        if registrable == brand:
            continue
        brand_name = _name(brand)
        if len(brand_name) < MIN_KEYWORD_LEN:
            continue
        if brand_name in host.lower():
            hints.append({"brand": brand, "reason": "brand name appears in the address", "distance": 0})
            continue
        if len(own_name) >= MIN_FUZZY_LEN and len(brand_name) >= MIN_FUZZY_LEN:
            distance = Levenshtein.distance(own_name, brand_name)
            if 0 < distance <= MAX_EDIT_DISTANCE:
                hints.append({"brand": brand, "reason": "address name is a very small spelling change of the brand", "distance": distance})

    hints.sort(key=lambda h: (h["distance"], h["brand"]))
    return hints[:top_k]
