
from playwright.sync_api import sync_playwright

DEFAULT_TIMEOUT_MS = 15000
MAX_REDIRECTS = 5


def load_page(url, timeout_ms=DEFAULT_TIMEOUT_MS, max_redirects=MAX_REDIRECTS, screenshot_path=None):
    """Loads a URL headlessly and returns its DOM content.

    Returns a dict:
        {"success": True, "html": str, "final_url": str, "status": int,
         "network_urls": list[str], "error": None}
        {"success": False, "html": None, "final_url": None, "status": None,
         "network_urls": [], "error": str}

   
    """
    result = {
        "success": False,
        "html": None,
        "final_url": None,
        "status": None,
        "network_urls": [],
        "error": None,
    }
    abort_reason = {"reason": None}
    network_urls = []
    browser = None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            page.on("dialog", lambda dialog: dialog.dismiss())

            page.on("download", lambda download: download.cancel())

            def track_request(request):
                if request.resource_type in ("xhr", "fetch"):
                    network_urls.append(request.url)

            page.on("request", track_request)

          
            response = page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass  

            hop_count = 0
            req = response.request if response else None
            while req is not None and req.redirected_from is not None:
                hop_count += 1
                req = req.redirected_from

            if hop_count > max_redirects:
                abort_reason["reason"] = "too many redirects"
            elif abort_reason["reason"] is None:
                result["success"] = True
                result["html"] = page.content()
                result["final_url"] = page.url
                result["status"] = response.status if response else None
                if screenshot_path:
                    try:
                        page.screenshot(path=screenshot_path)
                    except Exception:
                        pass  
    except Exception as exc:
        if abort_reason["reason"] is None:
            abort_reason["reason"] = f"{type(exc).__name__}: {exc}"
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass

    result["network_urls"] = network_urls
    if not result["success"]:
        result["error"] = abort_reason["reason"]

    return result
