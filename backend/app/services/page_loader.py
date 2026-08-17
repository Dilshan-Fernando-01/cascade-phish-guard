from playwright.sync_api import sync_playwright

DEFAULT_TIMEOUT_MS = 15000
MAX_REDIRECTS = 5


def load_page(url, timeout_ms=DEFAULT_TIMEOUT_MS, max_redirects=MAX_REDIRECTS):
    """Loads a URL headlessly and returns its DOM content.

    Returns a dict:
        {"success": True, "html": str, "final_url": str, "status": int, "error": None}
        {"success": False, "html": None, "final_url": None, "status": None, "error": str}
    """
    result = {"success": False, "html": None, "final_url": None, "status": None, "error": None}
    abort_reason = {"reason": None}
    visited = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        page.on("dialog", lambda dialog: dialog.dismiss())

        page.on("download", lambda download: download.cancel())

        def track_navigation(frame):
            if frame != page.main_frame:
                return
            visited.append(frame.url)
            if visited.count(frame.url) > 1:
                abort_reason["reason"] = "redirect loop detected"
                page.close()
            elif len(visited) > max_redirects + 1:
                abort_reason["reason"] = "too many redirects"
                page.close()

        page.on("framenavigated", track_navigation)

        try:
            response = page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            result["success"] = True
            result["html"] = page.content()
            result["final_url"] = page.url
            result["status"] = response.status if response else None
        except Exception as exc:
            result["error"] = abort_reason["reason"] or f"{type(exc).__name__}: {exc}"
        finally:
            browser.close()

    return result
