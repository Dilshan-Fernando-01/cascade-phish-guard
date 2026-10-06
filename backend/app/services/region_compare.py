import io

import numpy as np
from PIL import Image

PATCH = 224
SPOTS = [(120, 120), (936, 120)]  
MIN_SPREAD = 12.0  
THRESHOLD = 0.87 


def _patches(png_bytes):
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    out = []
    for x, y in SPOTS:
        patch = img.crop((x, y, x + PATCH, y + PATCH))
        grey = np.asarray(patch.convert("L"), dtype=float)
        out.append(patch if grey.std() >= MIN_SPREAD else None)
    return out


def compare_patches(visited_png, brand_png):
    from services import layer3_analyzer as l3

    v_patches = _patches(visited_png)
    b_patches = _patches(brand_png)
    if any(p is None for p in v_patches + b_patches):
        return {"status": "not enough detail", "both_match": False, "similarities": []}

    l3._ensure_logo_path()
    from logo_identity import get_embedding

    model = l3._load_logo_state()["model"]
    sims = []
    for v, b in zip(v_patches, b_patches):
        ev = get_embedding(v, model)
        eb = get_embedding(b, model)
        sims.append(round(float(np.dot(ev, eb)), 4))
    return {
        "status": "checked",
        "both_match": all(s >= THRESHOLD for s in sims),
        "similarities": sims,
    }
