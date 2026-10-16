import csv
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "data/layer3/fresh_phishing_live_results.csv"


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
    rows = [r for r in csv.DictReader(open(PATH)) if r["loaded"] == "True"]
    attempted = len(rows)

    real = [r for r in rows if is_real_content(r)]
    blocked = [r for r in rows if not is_real_content(r)]

    flagged_real = [r for r in real if r["verdict"] in ("suspicious", "phishing")]

    print(f"attempted (reported as loaded): {attempted}")
    print(f"  genuinely rendered real content: {len(real)}")
    print(f"  blocked/dead/error pages (browser already protected the user): {len(blocked)}")
    print()
    if real:
        tool_rate = len(flagged_real) / len(real) * 100
        print(f"TOOL DETECTION RATE (only on pages it actually got to see): "
              f"{len(flagged_real)}/{len(real)} = {tool_rate:.1f}%")
    end_to_end_protected = len(flagged_real) + len(blocked)
    if attempted:
        e2e_rate = end_to_end_protected / attempted * 100
        print(f"END-TO-END PROTECTION RATE (tool catches + browser already blocked): "
              f"{end_to_end_protected}/{attempted} = {e2e_rate:.1f}%")


if __name__ == "__main__":
    main()
