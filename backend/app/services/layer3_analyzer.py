LOGO_CHECK = "logo_check"
BANNER_WORDING_CHECK = "banner_wording_check"

STATUS_PENDING = "pending"


def analyze_layer3(url, screenshot_png, html=None):
    return {
        LOGO_CHECK: {"status": STATUS_PENDING},
        BANNER_WORDING_CHECK: {"status": STATUS_PENDING},
    }
