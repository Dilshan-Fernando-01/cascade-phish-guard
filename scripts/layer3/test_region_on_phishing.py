import csv
import os
import re
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend", "app"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "layer3"))
import test_region_false_match as t  
from services import layer3_analyzer as l3  
from services import region_compare as rc  

OUT_DIR = os.path.join(ROOT, "data", "layer3", "region_review")


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return
    shots_dir = sys.argv[1]
    l3._load_logo_state()
    os.makedirs(OUT_DIR, exist_ok=True)

    brand_files = {}
    for r in csv.DictReader(open(t.BRAND_MANIFEST)):
        if r["success"] != "True":
            continue
        fn = re.sub(r"[^A-Za-z0-9._-]+", "_", r["brand"]).strip("_") or "brand"
        path = os.path.join(t.BRAND_DIR, fn + ".png")
        if os.path.exists(path):
            brand_files[(r["brand"], r["domain"])] = path
    brand_emb = {}
    for key, path in brand_files.items():
        e = t.embed_page(path)
        if e is not None:
            brand_emb[key] = e

    matches = []
    checked = skipped = 0
    for name in sorted(os.listdir(shots_dir)):
        if not name.lower().endswith(".png"):
            continue
        path = os.path.join(shots_dir, name)
        if Image.open(path).size[0] != 1280:
            skipped += 1
            continue
        e = t.embed_page(path)
        if e is None:
            skipped += 1
            continue
        checked += 1
        for key, be in brand_emb.items():
            sims = [float(np.dot(a, b)) for a, b in zip(e, be)]
            if all(s >= rc.THRESHOLD for s in sims):
                matches.append({"screenshot": name, "brand": key[0], "domain": key[1],
                                "sim_1": round(sims[0], 4), "sim_2": round(sims[1], 4)})
                side_by_side(path, brand_files[key], name, key[0])

    with open(os.path.join(OUT_DIR, "region_matches.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["screenshot", "brand", "domain", "sim_1", "sim_2"])
        w.writeheader()
        w.writerows(matches)
    print(f"screenshots checked: {checked} (skipped: {skipped}); brand homepages: {len(brand_emb)}")
    print(f"matches on both patches: {len(matches)}; see {OUT_DIR}")


def side_by_side(left_path, right_path, name, brand):
    left = Image.open(left_path).convert("RGB").crop((0, 0, 1280, 600))
    right = Image.open(right_path).convert("RGB").crop((0, 0, 1280, 600))
    canvas = Image.new("RGB", (1280, 1210), (255, 255, 255))
    canvas.paste(left, (0, 0))
    canvas.paste(right, (0, 610))
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", f"{name}__{brand}")[:150]
    canvas.save(os.path.join(OUT_DIR, safe + ".png"))


if __name__ == "__main__":
    main()
