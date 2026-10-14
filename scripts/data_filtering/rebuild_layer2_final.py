
import argparse
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _splitting import split_legitimate  # noqa: E402

CURRENT_FEATURE_FILES = {
    "train": "data/processed/layer2_train_features.csv",
    "validation": "data/processed/layer2_validation_features.csv",
    "test": "data/processed/layer2_test_features.csv",
}

BARE_RECAPTURED = "data/processed/bare_tranco_recaptured.csv"
DEEP_LINK_RECAPTURED = "data/processed/legitimate_deep_links_recaptured.csv"

OUT_PREFIX = "data/processed/layer2"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cap", type=int, required=True)
    args = parser.parse_args()

   
    phishing_by_split = {}
    for name, path in CURRENT_FEATURE_FILES.items():
        df = pd.read_csv(path)
        phishing_by_split[name] = df[df["label"] == 1].reset_index(drop=True)
        print(f"phishing {name}: {len(phishing_by_split[name])} rows (untouched)")


    bare = pd.read_csv(BARE_RECAPTURED)
    bare["label"] = 0
    deep = pd.read_csv(DEEP_LINK_RECAPTURED)
    deep["label"] = 0
    legit_all = pd.concat([bare, deep], ignore_index=True)
    print(f"\nlegitimate available: {len(bare)} bare + {len(deep)} deep-link = {len(legit_all)} total")

    if len(legit_all) > args.cap:
        legit_all = legit_all.sample(n=args.cap, random_state=42).reset_index(drop=True)
    print(f"legitimate after cap ({args.cap}): {len(legit_all)}")

    l_train, l_val, l_test = split_legitimate(legit_all)
    legit_by_split = {"train": l_train, "validation": l_val, "test": l_test}

    summary = {}
    for name in ("train", "validation", "test"):
        combined = pd.concat([phishing_by_split[name], legit_by_split[name]], ignore_index=True)
        combined.to_csv(f"{OUT_PREFIX}_{name}_features_v2.csv", index=False)
        summary[name] = {
            "total": len(combined),
            "phishing": int((combined["label"] == 1).sum()),
            "legitimate": int((combined["label"] == 0).sum()),
        }

    os.makedirs("data/reports", exist_ok=True)
    with open("data/reports/layer2_rebuild_final_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
