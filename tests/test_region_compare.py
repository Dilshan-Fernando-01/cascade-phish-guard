import io
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app"))
from services import region_compare as rc  # noqa: E402

FAILURES = []


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


def png(arr):
    buf = io.BytesIO()
    Image.fromarray(arr.astype(np.uint8)).save(buf, "PNG")
    return buf.getvalue()


rng = np.random.default_rng(7)
texture = rng.integers(0, 255, (800, 1280, 3))
plain = np.full((800, 1280, 3), 200)

check("the fixed spots are inside the top 600px and the page", all(y + rc.PATCH <= 600 for _, y in rc.SPOTS))
check("a nearly one-colour page gives no patches", all(p is None for p in rc._patches(png(plain))))
check("a textured page gives two patches", all(p is not None for p in rc._patches(png(texture))))

same = rc.compare_patches(png(texture), png(texture))
check("identical pages: both patches match", same["status"] == "checked" and same["both_match"] is True)

blank = rc.compare_patches(png(plain), png(texture))
check("a one-colour page is 'not enough detail', never a match",
      blank["status"] == "not enough detail" and blank["both_match"] is False)

print()
if FAILURES:
    print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
    sys.exit(1)
print("All checks passed.")
