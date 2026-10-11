import csv
import sys

FLAG_THRESHOLD = 0.2  


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return

    with open(sys.argv[1], newline="") as f:
        rows = list(csv.DictReader(f))

    loaded = [r for r in rows if r.get("loaded") == "True"]
    cascade_flagged = [r for r in loaded if r["verdict"] in ("phishing", "suspicious")]

    with_score = [r for r in loaded if r.get("layer1_score")]
    baseline_flagged = [r for r in with_score if float(r["layer1_score"]) > FLAG_THRESHOLD]

    print(f"loaded: {len(loaded)}")
    print(f"URL-only baseline (Layer 1 alone, score > {FLAG_THRESHOLD}): "
          f"{len(baseline_flagged)} of {len(with_score)} flagged "
          f"({100 * len(baseline_flagged) / len(with_score):.1f}%)")
    print(f"full cascade (actual deployed system): "
          f"{len(cascade_flagged)} of {len(loaded)} flagged "
          f"({100 * len(cascade_flagged) / len(loaded):.1f}%)")


    baseline_urls_flagged = {r["url"] for r in baseline_flagged}
    cascade_only = [r for r in cascade_flagged if r["url"] not in baseline_urls_flagged]
    print(f"caught by the full cascade but missed by the URL-only baseline: {len(cascade_only)}")


if __name__ == "__main__":
    main()
