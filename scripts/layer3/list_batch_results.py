import argparse
import csv
import sys

DEFAULT_PATH = "data/layer3/fresh_phishing_live_results.csv"


def is_real_content(row):
    try:
        status_ok = 200 <= int(row["http_status"]) < 300
    except (ValueError, TypeError, KeyError):
        status_ok = False
    try:
        big_enough = int(row["html_length"]) > 2000
    except (ValueError, TypeError, KeyError):
        big_enough = False
    return status_ok and big_enough


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=DEFAULT_PATH)
    parser.add_argument("--loaded", action="store_true", help="all loaded URLs")
    parser.add_argument("--missed", action="store_true", help="real content but verdict=safe")
    parser.add_argument("--blocked", action="store_true", help="loaded but not real content")
    parser.add_argument("--all", action="store_true", help="print all three groups")
    args = parser.parse_args()

    if not (args.loaded or args.missed or args.blocked or args.all):
        parser.print_help()
        sys.exit(0)

    rows = [r for r in csv.DictReader(open(args.path)) if r["loaded"] == "True"]

    if args.loaded or args.all:
        print(f"=== LOADED ({len(rows)}) ===")
        for r in rows:
            print(f"  [{r['verdict']}] {r['url']}")
        print()

    real = [r for r in rows if is_real_content(r)]
    blocked = [r for r in rows if not is_real_content(r)]
    missed = [r for r in real if r["verdict"] == "safe"]

    if args.missed or args.all:
        print(f"=== MISSED - real content, verdict=safe ({len(missed)}) ===")
        for r in missed:
            print(f"  {r['url']}  (layer1={r['layer1_score']} layer2={r['layer2_score']} layer3={r['layer3_score']})")
        print()

    if args.blocked or args.all:
        print(f"=== BLOCKED/DEAD - loaded but not real content ({len(blocked)}) ===")
        for r in blocked:
            print(f"  {r['url']}  (http_status={r['http_status']} html_length={r['html_length']})")


if __name__ == "__main__":
    main()
