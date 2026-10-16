# Amazon lookalike demo

## Why this design

- The "real" side is just the real `https://www.amazon.com/` — no local copy
  needed, nothing to keep in sync, and more reliable than hosting a clone
  (Amazon's own site is effectively never down).
- The "fake" side is a small local page reusing a freshly-captured real Amazon
  logo (`fake/logo.png`, captured directly from amazon.com via the same
  logo-finder logic the extension itself uses — not a stock image), served
  under a locally-only address via `/etc/hosts`, the same technique as the
  `fictional_brand` demo.
- The fake address is **`amaz0n-secure.com`** (zero instead of "o"). Checked
  first: the obvious single-character swaps (`amaz0n.com`, `amazzon.com`,
  `arnazon.com`, etc.) are all already real, long-registered domains — using
  one of those would make the demo's Layer 1 score unpredictable, since our
  own WHOIS/RDAP lookup goes out to the real internet regardless of the local
  hosts override. `amaz0n-secure.com` came back genuinely unregistered
  (`domain_age_days=None`), so its Layer 1 behaviour is fully predictable:
  it looks exactly like a freshly-registered phishing domain, because for
  every purpose except serving the page itself, it is unregistered.
- Worth mentioning live if it comes up: `amaz0n-secure.com` contains a zero,
  not the letters "a-m-a-z-o-n", so it evades Layer 1's simple
  brand-keyword-in-host check — but Layer 3's CNN-based visual match catches
  it anyway (verified below). A clean, real illustration of why the system
  has more than one layer.

## Verified already (2026-10-16, bypassing the hostname for this check only,

same pattern as the fictional_brand demo's own verification)
Ran the real logo-identification pipeline directly against a page served at
`http://127.0.0.1:5175/`, claiming the page URL `https://amaz0n-secure.com/`:

```
identified_brand: Amazon
known_domains: [amazon.com, amazon.se, amazon.fr]
similarity: 0.923  (threshold is 0.87)
page_domain: amaz0n-secure.com
mismatch: true
```

Confirms the CNN correctly identifies the logo as Amazon's and correctly flags
the domain mismatch. The real DNS path (`/etc/hosts` → Playwright → extension)
has not been tested yet — do that dry run before presenting.

## One-time setup (needs `sudo`)

```
sudo nano /etc/hosts
```

Add this line at the end, save (Ctrl+O, Enter, Ctrl+X):

```
127.0.0.1 amaz0n-secure.com
```

## Running it

```
python scripts/demo/amazon_lookalike/serve_demo.py
```

Leave that running, then in Chrome (extension loaded, Full scan):

- `https://www.amazon.com/` — the real site, should come back clean.
- `http://amaz0n-secure.com:5175/` — the lookalike. Expect: Layer 1 suspicious
  (unranked, no registration record — a realistic fresh-phishing-domain
  profile), Layer 3 identifies the Amazon logo and flags the domain mismatch,
  and because the page also has a password field, the combination rule should
  raise the final verdict accordingly.

## To undo the `/etc/hosts` change afterward

`sudo nano /etc/hosts`, delete the line added above, save.
