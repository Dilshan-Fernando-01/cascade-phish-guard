

OFFICIAL_DOMAINS = {
    "google.com": [
        "youtube.com", "youtu.be", "youtube-nocookie.com", "g.co", "goo.gl",
        "googlesyndication.com", "doubleclick.net", "google-analytics.com",
        "googledomains.com", "googlevideo.com", "gstatic.com", "googleapis.com",
        "googleusercontent.com", "safety.google", "labs.google", "share.google",
    ],
    "microsoft.com": [
        "windows.com", "windows.net", "azure.com", "azure.net", "azureedge.net",
        "visualstudio.com", "sharepoint.com", "onedrive.com", "live.com",
        "office.com", "msn.com", "cloud.microsoft", "xbox.com", "skype.com",
        "linkedin.com", "bing.com",
    ],
    "facebook.com": [
        "fb.com", "fb.me", "fbcdn.net", "instagram.com", "whatsapp.com", "messenger.com",
    ],
    "amazon.com": [
        "amazon.in", "amazon.com.au", "amazon.co.uk", "amazonaws.com", "amazonvideo.com",
        "amzn.to", "amzn.com", "primevideo.com", "audible.com", "twitch.tv",
    ],
    "yahoo.com": ["yahoo.co.jp"],
}


def is_official(registrable_domain, main_domain):
    """True when the page's registrable domain is one of the brand's official domains."""
    return bool(registrable_domain) and registrable_domain in OFFICIAL_DOMAINS.get(main_domain, [])
