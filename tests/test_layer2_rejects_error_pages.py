import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app"))
import services.layer2_analyzer as l2a  # noqa: E402
import services.page_loader as pl  # noqa: E402

FAILURES = []


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


ORIGINAL_LOAD_PAGE = pl.load_page


def fake_load_page(status):
    def _fake(url, screenshot_path=None):
        return {
            "success": True, "html": "<html><body>page content</body></html>",
            "final_url": url, "status": status, "network_urls": [], "headers": {},
            "all_requests": [], "error": None,
        }
    return _fake



l2a.load_page = fake_load_page(404)
result = l2a.analyze_layer2("https://example.com/made-up-path")
check("a 404 page is rejected as a capture failure", result["success"] is False)
check("the rejection reason names the real status code", "404" in (result.get("error") or ""))


l2a.load_page = fake_load_page(200)
result2 = l2a.analyze_layer2("https://example.com/real-page")
check("a 200 page still succeeds and produces features", result2["success"] is True and result2["features"] is not None)


l2a.load_page = fake_load_page(503)
result3 = l2a.analyze_layer2("https://example.com/down-for-maintenance")
check("a 503 page is also rejected", result3["success"] is False)

l2a.load_page = ORIGINAL_LOAD_PAGE

print()
if FAILURES:
    print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
    sys.exit(1)
print("All checks passed.")
