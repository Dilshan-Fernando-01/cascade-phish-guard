import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app"))
from features.metadata_identity import metadata_identity  # noqa: E402

FAILURES = []


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


COPY = """<html><head><meta property="og:site_name" content="PayPal">
<link rel="canonical" href="https://www.paypal.com/login"></head><body></body></html>"""
OWN = """<html><head><meta property="og:site_name" content="Commercial Bank">
<link rel="canonical" href="https://www.combank.lk/"></head></html>"""
ARTICLE_SYNDICATED = """<html><head><meta property="og:site_name" content="The Verge">
<link rel="canonical" href="https://www.theverge.com/story"></head></html>"""
NO_META = "<html><head><title>Hello</title></head><body>Hi</body></html>"
JSONLD = """<html><head><script type="application/ld+json">
{"@type": "Organization", "name": "NIBM"}</script></head></html>"""

r = metadata_identity(COPY, "https://paypa1.com/login")
check("a copy declaring another address is an address mismatch", r["address_mismatch"] is True)
check("a copy whose name does not fit the address is strong", r["strong"] is True)

r = metadata_identity(OWN, "https://www.combank.lk/")
check("a page on its own address is not an address mismatch", r["address_mismatch"] is False)
check("own page is not strong", r["strong"] is False)

r = metadata_identity(ARTICLE_SYNDICATED, "https://news.example.org/article")
check("a syndicated article declaring another domain is reported, not counted alone",
      r["address_mismatch"] is True and r["strong"] is True)

r = metadata_identity(JSONLD, "https://nibm.ac.lk/")
check("JSON-LD organisation name is read", r["declared_name"] == "NIBM")
check("a short name matches its domain", r["name_fits_address"] is True)

check("no metadata gives None", metadata_identity(NO_META, "https://example.com/") is None)
check("no HTML gives None", metadata_identity(None, "https://example.com/") is None)

print()
if FAILURES:
    print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
    sys.exit(1)
print("All checks passed.")
