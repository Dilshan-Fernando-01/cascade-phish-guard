import json

import pandas as pd

SAMPLE_PATH = "data/processed/virustotal_legit_sample.csv"


def main():
    df = pd.read_csv(SAMPLE_PATH)
    checked = df[df["vt_result"].notna()]
    conclusive = checked[~checked["vt_result"].isin(["not_found"]) & ~checked["vt_result"].astype(str).str.startswith("error_")]

    print(f"Legitimate-class sample validated: {len(df)} URLs sampled from the Tranco-sourced pool")
    print(f"  VirusTotal checked: {len(checked)}/{len(df)}")
    print(f"  Conclusive results (excludes not_found / API errors): {len(conclusive)}")
    print()

    clean = conclusive[conclusive["vt_result"] == "clean"]
    malicious = conclusive[conclusive["vt_result"] == "malicious"]
    print(f"  Clean: {len(clean)} ({100*len(clean)/len(conclusive):.2f}% of conclusive)")
    print(f"  Flagged malicious/suspicious by at least one engine: {len(malicious)} ({100*len(malicious)/len(conclusive):.2f}%)")
    print()

    if len(malicious):
        print("  Category breakdown of flagged URLs (engine -> label):")
        from collections import Counter
        cat_counter = Counter()
        for _, row in malicious.iterrows():
            try:
                cats = json.loads(row["vt_categories"]) if pd.notna(row["vt_categories"]) and row["vt_categories"] else {}
            except Exception:
                cats = {}
            for label in cats.values():
                cat_counter[str(label).lower()] += 1
        for label, count in cat_counter.most_common():
            print(f"    {label}: {count}")
        print()
        print("  NOTE: these flagged URLs should be removed from the legitimate")
        print("  training/test pool before the dataset is considered final - this")
        print("  script reports the finding, the removal is a separate, deliberate step.")


if __name__ == "__main__":
    main()
