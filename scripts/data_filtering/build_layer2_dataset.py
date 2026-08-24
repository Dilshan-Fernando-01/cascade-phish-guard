import json
import os

import pandas as pd

PHISHING_PATH = "data/processed/phishing_candidates_reachable.csv"
LEGITIMATE_BARE_PATH = "data/processed/legitimate_candidates_deduped.csv"
LEGITIMATE_DEEP_LINKS_PATH = "data/processed/legitimate_deep_links.csv"

OUTPUT_PATH = "data/processed/layer2_labelled_dataset.csv"
SUMMARY_PATH = "data/reports/layer2_combined_dataset_summary.json"

TARGET_PHISHING = 500
TARGET_LEGITIMATE = 500

DEEP_LINK_FRACTION = 0.40

RANDOM_SEED = 42


def main():
    phishing = pd.read_csv(PHISHING_PATH)
    phishing_sample = phishing.sample(n=min(TARGET_PHISHING, len(phishing)), random_state=RANDOM_SEED)
    phishing_sample = phishing_sample.copy()
    phishing_sample["label"] = 1

    deep_links = pd.read_csv(LEGITIMATE_DEEP_LINKS_PATH)
    bare = pd.read_csv(LEGITIMATE_BARE_PATH)

    deep_link_target = round(TARGET_LEGITIMATE * DEEP_LINK_FRACTION)
    bare_target = TARGET_LEGITIMATE - deep_link_target

    deep_link_sample = deep_links.sample(n=min(deep_link_target, len(deep_links)), random_state=RANDOM_SEED)
    bare_sample = bare.sample(n=min(bare_target, len(bare)), random_state=RANDOM_SEED)

    legitimate_sample = pd.concat([deep_link_sample, bare_sample], ignore_index=True)
    legitimate_sample["label"] = 0

    combined = pd.concat([phishing_sample, legitimate_sample], ignore_index=True)

    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("data/reports", exist_ok=True)
    combined.to_csv(OUTPUT_PATH, index=False)

    summary = {
        "total": len(combined),
        "phishing": int((combined["label"] == 1).sum()),
        "legitimate": int((combined["label"] == 0).sum()),
        "legitimate_breakdown": legitimate_sample["source"].value_counts().to_dict(),
    }

    with open(SUMMARY_PATH, "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
