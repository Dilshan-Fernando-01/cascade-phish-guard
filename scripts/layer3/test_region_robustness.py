import csv
import io
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend", "app"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "layer3"))
import test_region_false_match as t  
from services import layer3_analyzer as l3 
from services import region_compare as rc 

MANIFEST = t.BRAND_MANIFEST
LIMIT_BRANDS = 40


def variant(img, kind):
    out = img.copy()
    if kind == "shift":
        canvas = Image.new("RGB", img.size, (255, 255, 255))
        canvas.paste(img, (8, 6))
        return canvas
    if kind == "tint":
        return Image.eval(out, lambda v: int(v * 0.9))
    if kind == "banner":
        draw = ImageDraw.Draw(out)
        draw.rectangle((0, 480, img.size[0], 560), fill=(60, 60, 60))
        return out
    if kind == "text":
        draw = ImageDraw.Draw(out)
        draw.rectangle((100, 100, 420, 240), fill=(255, 255, 255))
        return out
    raise ValueError(kind)


def both_match(a_img, b_img):
   
    buf_a, buf_b = io.BytesIO(), io.BytesIO()
    a_img.save(buf_a, "PNG")
    b_img.save(buf_b, "PNG")
    pa, pb = rc._patches(buf_a.getvalue()), rc._patches(buf_b.getvalue())
    if any(p is None for p in pa + pb):
        return None
    from logo_identity import get_embedding
    model = l3._load_logo_state()["model"]
    sims = [float(np.dot(get_embedding(x, model), get_embedding(y, model))) for x, y in zip(pa, pb)]
    return all(s >= rc.THRESHOLD for s in sims), sims


def main():
    l3._load_logo_state()
    l3._ensure_logo_path()
    rows = [r for r in csv.DictReader(open(MANIFEST)) if r["success"] == "True"][:LIMIT_BRANDS]
    kinds = ["shift", "tint", "banner", "text"]
    counts = {k: {"tested": 0, "still_match": 0, "no_detail": 0} for k in kinds}
    for r in rows:
        fn = re.sub(r"[^A-Za-z0-9._-]+", "_", r["brand"]).strip("_") or "brand"
        path = os.path.join(t.BRAND_DIR, fn + ".png")
        if not os.path.exists(path):
            continue
        original = Image.open(path).convert("RGB")
        for kind in kinds:
            result = both_match(original, variant(original, kind))
            if result is None:
                counts[kind]["no_detail"] += 1
                continue
            counts[kind]["tested"] += 1
            counts[kind]["still_match"] += int(result[0])
    print(f"brands tested: up to {LIMIT_BRANDS}")
    for kind in kinds:
        c = counts[kind]
        rate = 100 * c["still_match"] / c["tested"] if c["tested"] else 0.0
        print(f"{kind:7s} still matches: {c['still_match']} of {c['tested']} ({rate:.0f}%); too plain: {c['no_detail']}")


if __name__ == "__main__":
    main()
