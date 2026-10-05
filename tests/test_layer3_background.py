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


def fake_fetch(outcomes):

    from urllib.parse import urlparse

    def _fetch(url):
        parsed = urlparse(url)
        return outcomes[f"{parsed.scheme}://{parsed.netloc}/"]
    return _fetch


ORIGINAL_FETCH = bc.fetch_root_logo_png
ORIGINAL_COMPARE = bc.compare_logo_pair
LOGO = b"logo-bytes"


bc.fetch_root_logo_png = fake_fetch({
    "https://paypa1.com/": (None, "no logo found on the site's home page"),
    "https://paypal.com/": (LOGO, None),
})
bc.compare_logo_pair = lambda a, b: {"band": "should not run", "similarity": 0.0}
r = bc.background_check("https://paypa1.com/login", "paypal.com")
check("no logo on the visited home page gives could not confirm", r["status"] == "could not confirm")
check("the reason names the visited site", r["reason"].startswith("visited site:"))


bc.fetch_root_logo_png = fake_fetch({
    "https://paypa1.com/": (LOGO, None),
    "https://paypal.com/": (None, "the site showed a bot check"),
})
r = bc.background_check("https://paypa1.com/login", "paypal.com")
check("a blocked brand home page gives could not confirm", r["status"] == "could not confirm")
check("the reason names the brand's home page", r["reason"].startswith("brand's home page:"))


bc.fetch_root_logo_png = fake_fetch({
    "https://paypa1.com/": (LOGO, None),
    "https://paypal.com/": (LOGO, None),
})
bc.compare_logo_pair = lambda a, b: {"band": "strong", "similarity": 0.95}
r = bc.background_check("https://paypa1.com/login", "paypal.com")
check("both logos found gives checked", r["status"] == "checked")
check("the result is live and names the brand", r["source"] == "live" and r["brand_domain"] == "paypal.com")
check("the band comes from the comparison", r["band"] == "strong" and r["similarity"] == 0.95)

bc.fetch_root_logo_png = ORIGINAL_FETCH
bc.compare_logo_pair = ORIGINAL_COMPARE

print()
if FAILURES:
    print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
    sys.exit(1)
print("All checks passed.")
