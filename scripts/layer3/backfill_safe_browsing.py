import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_live_against_fresh_phishing import safe_browsing_lookup, SB_API_KEY  # noqa: E402


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return
    if not SB_API_KEY:
        print("GOOGLE_SAFE_BROWSING_API_KEY is not set in this shell - export it first.")
        return

    path = sys.argv[1]
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
        fieldnames = rows[0].keys() if rows else []

    todo = [r for r in rows if r.get("loaded") == "True" and not r.get("sb_verdict")]
    print(f"{len(todo)} loaded rows need a Safe Browsing lookup (of {len(rows)} total rows)")

    for i, row in enumerate(todo, 1):
        result = safe_browsing_lookup(row["url"])
        row["sb_verdict"] = result or ""
        print(f"[{i}/{len(todo)}] sb={result or '-'}")

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    loaded = [r for r in rows if r["loaded"] == "True"]
    sb_flagged = [r for r in loaded if r["sb_verdict"] == "flagged"]
    sb_checked = [r for r in loaded if r["sb_verdict"] in ("flagged", "clean")]
    we_flagged_sb_did_not = [
        r for r in loaded if r["sb_verdict"] == "clean" and r["verdict"] in ("phishing", "suspicious")
    ]
    print()
    print(f"Safe Browsing successfully checked: {len(sb_checked)} of {len(loaded)} loaded URLs")
    print(f"Safe Browsing flagged: {len(sb_flagged)} of {len(sb_checked)} checked")
    print(f"we flagged but Safe Browsing did not (zero-day-gap cases): {len(we_flagged_sb_did_not)}")


if __name__ == "__main__":
    main()
