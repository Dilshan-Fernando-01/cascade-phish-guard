import csv
import os
import re
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend", "app"))
from services import layer3_analyzer as l3  # noqa: E402
from services import region_compare as rc  # noqa: E402
from features.url_features import _registrable_domain_guess  # noqa: E402

LEGIT_DIR = os.path.join(ROOT, "data", "layer3", "region_test", "legit")
BRAND_DIR = os.path.join(ROOT, "data", "layer3", "brand_home")
BRAND_MANIFEST = os.path.join(ROOT, "data", "layer3", "brand_home_manifest.csv")
PASS_RATE = 0.03


def embed_page(path):
    """Two patch embeddings for one page, or None if a patch has too little detail."""
    with open(path, "rb") as f:
        patches = rc._patches(f.read())
    if any(p is None for p in patches):
        return None
    l3._ensure_logo_path()
    from logo_identity import get_embedding
    model = l3._load_logo_state()["model"]
    return [get_embedding(p, model) for p in patches]


def main():
    l3._load_logo_state()
    brand_rows = [r for r in csv.DictReader(open(BRAND_MANIFEST)) if r["success"] == "True"]
    brands = {}
    for r in brand_rows:
        # same file-name rule as capture_brand_home.safe_name
        file_name = re.sub(r"[^A-Za-z0-9._-]+", "_", r["brand"]).strip("_") or "brand"
        brands[r["domain"]] = os.path.join(BRAND_DIR, file_name + ".png")
    brand_emb = {}
    for domain, path in brands.items():
        if os.path.exists(path):
            e = embed_page(path)
            if e is not None:
                brand_emb[domain] = e

    legit_files = sorted(os.listdir(LEGIT_DIR))
    legit_emb = {}
    for f in legit_files:
        e = embed_page(os.path.join(LEGIT_DIR, f))
        if e is not None:
            legit_emb[f[:-4]] = e

    pairs = both = 0
    for legit_name, le in legit_emb.items():
        legit_root = _registrable_domain_guess(legit_name)
        for brand_domain, be in brand_emb.items():
            if legit_root == _registrable_domain_guess(brand_domain):
                continue  # the legitimate page is that brand's own site
            pairs += 1
            sims = [float(np.dot(a, b)) for a, b in zip(le, be)]
            if all(s >= rc.THRESHOLD for s in sims):
                both += 1
    rate = both / pairs if pairs else 0.0
    print(f"legitimate screenshots usable: {len(legit_emb)} of {len(legit_files)}")
    print(f"brand homepages usable: {len(brand_emb)}")
    print(f"unrelated pairs compared: {pairs}")
    print(f"both patches match: {both} ({100 * rate:.2f}%)")
    print(f"pass rule (under {100 * PASS_RATE:.0f}%): {'PASS' if rate < PASS_RATE else 'FAIL'}")


if __name__ == "__main__":
    main()
