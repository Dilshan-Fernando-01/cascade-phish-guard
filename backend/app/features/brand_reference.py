import os

BRAND_DOMAINS = {
    "allegro.pl", "irs.gov", "facebook.com", "microsoft.com", "amazon.com",
    "bradesco.com.br", "netflix.com", "optus.com.au", "societegenerale.com",
    "paypal.com", "adobe.com", "att.com", "americanexpress.com", "docusign.com",
    "comcast.com", "google.com", "ebay.com", "apple.com", "bankofamerica.com",
    "hsbc.com", "dhl.com", "chase.com", "coinbase.com", "orange.fr", "bt.com",
    "wetransfer.com", "santander.com", "ing.com", "steamcommunity.com",
    "steampowered.com", "visa.com", "outlook.com", "interactivebrokers.com",
    "free.fr", "navyfederal.org", "whatsapp.com", "abnamro.com", "dbs.com",
    "bb.com.br", "instagram.com", "dropbox.com", "unicredit.eu",
    "wellsfargo.com", "binance.com", "revolut.com",

    "linkedin.com", "icloud.com", "yahoo.com", "twitter.com", "x.com",
    "ups.com", "fedex.com", "citibank.com", "usbank.com", "capitalone.com",
    "discover.com",
}

if os.environ.get("DEMO_FICTIONAL_BRAND", "").lower() in ("1", "true", "yes"):
    BRAND_DOMAINS = BRAND_DOMAINS | {"corvanetrust.test"}
