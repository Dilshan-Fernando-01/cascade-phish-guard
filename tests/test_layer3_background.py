import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app"))
import services.background_compare as bc  # noqa: E402

FAILURES = []


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


def fake_visit(outcomes):
    """outcomes maps "scheme://host/" -> {"screenshot": ..., "logo": ..., "reason": ...}"""
    from urllib.parse import urlparse

    def _visit(url):
        parsed = urlparse(url)
        return outcomes[f"{parsed.scheme}://{parsed.netloc}/"]
    return _visit


ORIGINAL_VISIT = bc._visit
ORIGINAL_COMPARE = bc.compare_logo_pair
SHOT = b"screenshot-bytes"
LOGO = b"logo-bytes"
REGION_RESULT = {"status": "checked", "both_match": True, "similarities": [0.9, 0.9]}


def fake_region(result):
    def _compare_patches(visited_png, brand_png):
        return result
    return _compare_patches


import services.region_compare as rc  # noqa: E402

ORIGINAL_REGION = rc.compare_patches



bc._visit = fake_visit({
    "https://paypa1.com/": {"screenshot": None, "logo": None, "reason": "the site's home page did not load"},
})
r = bc.background_check("https://paypa1.com/login", "paypal.com")
check("no screenshot on the visited home page gives could not confirm", r["status"] == "could not confirm")
check("the reason names the visited site", r["reason"].startswith("visited site:"))



bc._visit = fake_visit({
    "https://paypa1.com/": {"screenshot": SHOT, "logo": LOGO, "reason": None},
    "https://paypal.com/": {"screenshot": None, "logo": None, "reason": "the site showed a bot check"},
})
r = bc.background_check("https://paypa1.com/login", "paypal.com")
check("a blocked brand home page gives could not confirm", r["status"] == "could not confirm")
check("the reason names the brand's home page", r["reason"].startswith("brand's home page:"))



bc._visit = fake_visit({
    "https://paypa1.com/": {"screenshot": SHOT, "logo": LOGO, "reason": None},
    "https://paypal.com/": {"screenshot": SHOT, "logo": LOGO, "reason": None},
})
bc.compare_logo_pair = lambda a, b: {"band": "strong", "similarity": 0.95}
rc.compare_patches = fake_region(REGION_RESULT)
r = bc.background_check("https://paypa1.com/login", "paypal.com")
check("both logos found gives checked", r["status"] == "checked")
check("the result is live and names the brand", r["source"] == "live" and r["brand_domain"] == "paypal.com")
check("the band comes from the logo comparison", r["band"] == "strong" and r["similarity"] == 0.95)
check("the region result is carried through unchanged", r["region"] == REGION_RESULT)



bc._visit = fake_visit({
    "https://paypa1.com/": {"screenshot": SHOT, "logo": None, "reason": None},
    "https://paypal.com/": {"screenshot": SHOT, "logo": None, "reason": None},
})
r = bc.background_check("https://paypa1.com/login", "paypal.com")
check("no logo on either side still gives checked", r["status"] == "checked")
check("the band is None rather than a guess", r["band"] is None and r["similarity"] is None)
check("region is still compared from the pages already loaded", r["region"] == REGION_RESULT)


bc._visit = ORIGINAL_VISIT
bc.compare_logo_pair = ORIGINAL_COMPARE
rc.compare_patches = ORIGINAL_REGION



bc._visit = fake_visit({
    "https://paypal.com/": {"screenshot": SHOT, "logo": LOGO, "reason": None},
    "https://paypa1.com/": {"screenshot": SHOT, "logo": None, "reason": None},
    "https://blocked.example/": {"screenshot": None, "logo": None, "reason": "the site's home page did not load"},
})
check("a found logo is returned as before", bc.fetch_root_logo_png("https://paypal.com/")[0] == LOGO)
check(
    "a loaded page with no logo reports 'no logo found'",
    bc.fetch_root_logo_png("https://paypa1.com/") == (None, "no logo found on the site's home page"),
)
check(
    "a page that did not load passes its reason through",
    bc.fetch_root_logo_png("https://blocked.example/") == (None, "the site's home page did not load"),
)
bc._visit = ORIGINAL_VISIT

print()
if FAILURES:
    print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
    sys.exit(1)
print("All checks passed.")
