# Fictional-brand demo pair

A controlled, local-only test of the Layer 3 visual-identity check: a fictional bank
("Corvane Trust" - invented for this demo, not a real company, never published anywhere)
and a copycat page that deliberately reuses its logo and banner on a different address.

This exists for two reasons:
1. Every other Layer 3 test so far has compared either unrelated real sites (which
   obviously don't match - an easy test) or real phishing screenshots that were mostly
   already dead by the time they were tested. This is the first controlled case of an
   actual visual copy, confirmed to work end-to-end (see PROJECT_LOG.md, 2026-10-08).
2. It gives a reliable demo for the viva that doesn't depend on a real phishing site
   still being online at that exact moment.

## What's here
- `real/` - the "real" Corvane Trust homepage (`index.html`, `logo.png`, `hero.png`)
- `copy/` - the copycat page: the same logo and banner image, on a different fake
  address, with a login form (so the "asks for information" part of the rule also
  fires)
- `generate_demo_images.py` - regenerates the two shared images (PIL, no network)
- `serve_demo.py` - serves both pages locally, one per port

## One-time setup
Add these two lines to `/etc/hosts` (needs `sudo`, since it's a system file):

```
127.0.0.1 corvanetrust.test
127.0.0.1 corvanetrust-secure-login.test
```

`sudo nano /etc/hosts`, add the two lines at the end, save (Ctrl+O, Enter, Ctrl+X).
Both hostnames are made up, on the IANA-reserved `.test` TLD, and only exist on this
computer - nothing is published or reachable from outside it. To undo later, delete the
two lines the same way.

## Running it
```
python scripts/demo/fictional_brand/serve_demo.py
```
Leave that running, then open in Chrome (extension loaded, Full scan):
- `http://corvanetrust.test:5173/` - should come back clean (matches its own brand hint
  trivially, since the address and the brand are the same).
- `http://corvanetrust-secure-login.test:5174/` - the copycat. The address names
  "corvanetrust.test" as a brand but isn't that domain, so Layer 3 should reach "closely
  resembles" (logo band: strong, region patches: both match) and, because the page also
  asks for a password, the combination rule should raise the verdict to at least
  suspicious.

The backend needs `DEMO_FICTIONAL_BRAND=1` set so it recognizes the fictional brand name
at all - without it, the address just looks like an ordinary, unrecognized domain and
nothing is flagged. This is off by default on purpose, so no real measurement (the
false-alarm rate, etc.) is ever affected by it:
```
export DEMO_FICTIONAL_BRAND=1
```
set alongside the backend's usual `API_KEY`/`ENABLE_LAYER2` before starting uvicorn.

## Verified already (2026-10-08, without /etc/hosts, using the real captured images)
Both pages were rendered and captured locally (via 127.0.0.1, bypassing the hostname
for this check only) and run through the real comparison code:
- Region comparison: both patches matched (similarity 1.0 on both - the images are
  identical files on purpose).
- Logo comparison: strong match (similarity 1.0).
- Full `analyze_layer3()` on the copycat page: identity level correctly reached
  "closely resembles".
- `apply_layer3_rule()`: brand_mismatch + input_signal (the password field) correctly
  raised the score to the suspicious floor (0.5).

What hasn't been verified yet is the real DNS path (an actual Playwright visit to
`corvanetrust.test` resolving via `/etc/hosts`) - that needs the hosts-file step above,
which only a human with `sudo` can do.
