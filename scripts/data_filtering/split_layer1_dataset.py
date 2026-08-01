import json
import os

import pandas as pd


SPLIT_MODE = "random_stratified_TEMPORARY"

TRAIN_FRACTION = 0.70
VAL_FRACTION = 0.15
# remainder (0.15) goes to test
RANDOM_SEED = 42


def stratified_split(df, label_col):
    train_parts, val_parts, test_parts = [], [], []
    for _label, group in df.groupby(label_col):
        shuffled = group.sample(frac=1.0, random_state=RANDOM_SEED)
        n = len(shuffled)
        train_end = int(n * TRAIN_FRACTION)
        val_end = train_end + int(n * VAL_FRACTION)
        train_parts.append(shuffled.iloc[:train_end])
        val_parts.append(shuffled.iloc[train_end:val_end])
        test_parts.append(shuffled.iloc[val_end:])
    return (
        pd.concat(train_parts, ignore_index=True),
        pd.concat(val_parts, ignore_index=True),
        pd.concat(test_parts, ignore_index=True),
    )


def main():
    combined = pd.read_csv("data/processed/layer1_labelled_dataset.csv")

    train, val, test = stratified_split(combined, "label")

    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("data/reports", exist_ok=True)

    train.to_csv("data/processed/layer1_train.csv", index=False)
    val.to_csv("data/processed/layer1_validation.csv", index=False)
    test.to_csv("data/processed/layer1_test.csv", index=False)

    def class_counts(df):
        return {
            "total": len(df),
            "phishing": int((df["label"] == 1).sum()),
            "legitimate": int((df["label"] == 0).sum()),
        }

    summary = {
        "split_mode": SPLIT_MODE,
        "warning": (
            "TEMPORARY random-stratified split "
        ),
        "train": class_counts(train),
        "validation": class_counts(val),
        "test": class_counts(test),
    }

    with open("data/reports/split_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
