import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app"))
from features.page_quality import compute_page_quality  # noqa: E402

FAILURES = []


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


GOOD_HTML = "<html><body><p>hello</p></body></html>"
GOOD_HEADERS = {
    "strict-transport-security": "max-age=63072000",
    "content-security-policy": "default-src 'self'",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
}

good = compute_page_quality(GOOD_HTML, GOOD_HEADERS, [], "https://example.com/")
check("a clean page with every header scores 100", good["score"] == 100)
check("a clean page is banded 'good'", good["band"] == "good")
check("a clean page has no findings", good["findings"] == [])

bare_http = compute_page_quality(GOOD_HTML, {}, [], "http://example.com/")
check("no HTTPS deducts points", bare_http["score"] < 100)
check(
    "no HTTPS is the specific finding",
    any("HTTPS" in f["label"] for f in bare_http["findings"]),
)

no_headers = compute_page_quality(GOOD_HTML, {}, [], "https://example.com/")
one_missing_headers = {k: v for k, v in GOOD_HEADERS.items() if k != "strict-transport-security"}
one_missing = compute_page_quality(GOOD_HTML, one_missing_headers, [], "https://example.com/")
check("missing all headers deducts more than missing just one", no_headers["score"] < one_missing["score"])
check("missing headers alone still reaches 'fair' or worse", no_headers["band"] in ("fair", "poor"))

mixed_requests = [
    {"url": "http://evil.example/track.js", "resource_type": "script"},
    {"url": "https://example.com/style.css", "resource_type": "stylesheet"},
]
mixed = compute_page_quality(GOOD_HTML, GOOD_HEADERS, mixed_requests, "https://example.com/")
check("active mixed content is deducted even with good headers", mixed["score"] < good["score"])

passive_only = compute_page_quality(
    GOOD_HTML, GOOD_HEADERS, [{"url": "http://example.com/photo.jpg", "resource_type": "image"}], "https://example.com/"
)
check(
    "passive mixed content costs less than active mixed content",
    (good["score"] - passive_only["score"]) < (good["score"] - mixed["score"]),
)

exposure_html = "<html><body>Traceback (most recent call last):\n  File x</body></html>"
exposure_headers = {**GOOD_HEADERS, "server": "Apache/2.4.41 (Ubuntu)", "x-powered-by": "PHP/7.2.1"}
exposed = compute_page_quality(exposure_html, exposure_headers, [], "https://example.com/")
check("leaked server version is flagged", any("Server" in f["label"] for f in exposed["findings"]))
check("X-Powered-By is flagged", any("X-Powered-By" in f["label"] for f in exposed["findings"]))
check("visible debug output is flagged", any("Debug" in f["label"] for f in exposed["findings"]))

listing_html = "<html><head><title>Index of /uploads</title></head><body>Index of /uploads</body></html>"
listing = compute_page_quality(listing_html, GOOD_HEADERS, [], "https://example.com/")
check("directory listing is flagged", any("directory listing" in f["label"].lower() for f in listing["findings"]))

many_inline = "<html><body>" + "".join(f'<div style="color:red">{i}</div>' for i in range(30)) + "</body></html>"
inline = compute_page_quality(many_inline, GOOD_HEADERS, [], "https://example.com/")
check("heavy inline-style use is flagged", any("inline styles" in f["label"].lower() for f in inline["findings"]))

few_inline = "<html><body>" + "".join(f"<div>{i}</div>" for i in range(30)) + '<span style="color:red">one</span></body></html>'
few = compute_page_quality(few_inline, GOOD_HEADERS, [], "https://example.com/")
check("one inline style in a large page is NOT flagged", not any("inline styles" in f["label"].lower() for f in few["findings"]))

console_html = "<html><body><script>console.log('debug', user.email);</script></body></html>"
console = compute_page_quality(console_html, GOOD_HEADERS, [], "https://example.com/")
check("console.log in an inline script is flagged", any("console" in f["label"].lower() for f in console["findings"]))

external_console_html = '<html><body><script src="main.js"></script></body></html>'
external = compute_page_quality(external_console_html, GOOD_HEADERS, [], "https://example.com/")
check("external script content is not inspected (no new fetch)", not any("console" in f["label"].lower() for f in external["findings"]))

worst_headers = {}
worst_html = "<html><body>" + "".join(f'<div style="color:red">{i}</div>' for i in range(30)) + "Traceback (most recent call last):</body></html>"
worst = compute_page_quality(worst_html, worst_headers, mixed_requests, "http://example.com/")
check("score never goes below 0", worst["score"] >= 0)
check("a page failing almost everything is banded 'poor'", worst["band"] == "poor")

print()
if FAILURES:
    print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
    sys.exit(1)
print("All checks passed.")
