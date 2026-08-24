import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _splitting import class_counts, split_dataset  # noqa: E402

SPLIT_MODE = "domain_grouped__temporal_phishing__random_legitimate"


def main():
    combined = pd.read_csv("data/processed/layer2_labelled_dataset.csv")
    train, val, test = split_dataset(combined)

    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("data/reports", exist_ok=True)

    train.to_csv("data/processed/layer2_train.csv", index=False)
    val.to_csv("data/processed/layer2_validation.csv", index=False)
    test.to_csv("data/processed/layer2_test.csv", index=False)

    summary = {
        "split_mode": SPLIT_MODE,
        "train": class_counts(train),
        "validation": class_counts(val),
        "test": class_counts(test),
    }

    with open("data/reports/layer2_split_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
