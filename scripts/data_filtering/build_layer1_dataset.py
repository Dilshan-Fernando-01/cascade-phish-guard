import json
import os

import pandas as pd

PHISHING_PATH = "data/processed/phishing_candidates_reachable.csv"
LEGITIMATE_BARE_PATH = "data/processed/legitimate_candidates_deduped.csv"
LEGITIMATE_DEEP_LINKS_PATH = "data/processed/legitimate_deep_links.csv"

OUTPUT_PATH = "data/processed/layer1_labelled_dataset.csv"
SUMMARY_PATH = "data/reports/combined_dataset_summary.json"


RANDOM_SEED = 42


def main():
    phishing = pd.read_csv(PHISHING_PATH)
    phishing["label"] = 1

    deep_links = pd.read_csv(LEGITIMATE_DEEP_LINKS_PATH)
    bare = pd.read_csv(LEGITIMATE_BARE_PATH)

    target_legitimate = len(phishing)
    n_bare_needed = target_legitimate - len(deep_links)
    if n_bare_needed < 0:
        raise ValueError(
            f"deep-link count ({len(deep_links)}) already exceeds the phishing "
            f"count ({target_legitimate}) -- ratio math assumes deep links stay a minority"
        )

    bare_sample = bare.sample(n=n_bare_needed, random_state=RANDOM_SEED)

    legitimate = pd.concat([deep_links, bare_sample], ignore_index=True)
    legitimate["label"] = 0

    combined = pd.concat([phishing, legitimate], ignore_index=True)

    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("data/reports", exist_ok=True)
    combined.to_csv(OUTPUT_PATH, index=False)

    summary = {
        "total": len(combined),
        "phishing": int((combined["label"] == 1).sum()),
        "legitimate": int((combined["label"] == 0).sum()),
        "legitimate_breakdown": legitimate["source"].value_counts().to_dict(),
        "class_ratio_legitimate_to_phishing": (
            (combined["label"] == 0).sum() / (combined["label"] == 1).sum()
        ),
    }

    with open(SUMMARY_PATH, "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
