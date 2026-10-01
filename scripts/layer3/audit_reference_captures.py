import csv
import os
import re
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from logo_candidates import find_logo_candidates

MANIFEST = "data/reference_brands/manifest.csv"
OUT = "data/reference_brands/audit.csv"

BAD_TITLE = re.compile(
    r"(error|access denied|forbidden|blocked|just a moment|attention required|are you a (robot|human)|"
    r"captcha|unusual traffic|not found|403|404|unavailable|temporarily|request rejected|incident|"
    r"system down|^loading|rejected)", re.I)


def main():
    with open(MANIFEST, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["success"] == "True"]
    print(f"auditing {len(rows)} captured brands...\n")

    results = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for r in rows:
            d = r["domain"]
            ctx = b.new_context(viewport={"width": 1280, "height": 800}, color_scheme="light",
                                ignore_https_errors=True)
            pg = ctx.new_page()
            rec = {"domain": d, "title": "", "text_len": 0, "bad_title": False, "top_logo_score": None,
                   "suspect": False, "note": ""}
            try:
                pg.goto(f"https://{d}", timeout=25000, wait_until="domcontentloaded")
                pg.wait_for_timeout(2000)
                rec["title"] = pg.title()[:80]
                rec["text_len"] = len((pg.inner_text("body") or "").strip())
                rec["bad_title"] = bool(BAD_TITLE.search(rec["title"]))
                cands = find_logo_candidates(pg, top_n=1, min_score=-99)
                rec["top_logo_score"] = cands[0]["score"] if cands else None
                if rec["bad_title"]:
                    rec["note"] = "error-like title"
                elif rec["text_len"] < 200:
                    rec["note"] = "almost no visible text"
                elif rec["top_logo_score"] is None:
                    rec["note"] = "no logo-like element found"
                rec["suspect"] = bool(rec["note"])
            except Exception as e:
                rec["note"] = f"revisit failed: {type(e).__name__}"
                rec["suspect"] = True
            finally:
                ctx.close()
            flag = "  <-- SUSPECT" if rec["suspect"] else ""
            print(f"{d:24s} score={str(rec['top_logo_score']):>4} text={rec['text_len']:>6} | {rec['title'][:50]!r}{flag} {rec['note']}")
            results.append(rec)
        b.close()

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)

    bad = [r for r in results if r["suspect"]]
    print(f"\n{len(bad)}/{len(results)} suspect. Wrote {OUT}")


if __name__ == "__main__":
    main()
