import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend", "app"))
from features.url_features import extract_features_batch  # noqa: E402

SPLITS = {
    "train": "data/processed/layer1_train.csv",
    "validation": "data/processed/layer1_validation.csv",
    "test": "data/processed/layer1_test.csv",
}

# TEMPORARY
LEGITIMATE_SAMPLE_SIZE = 50
RANDOM_SEED = 42


def build_sample(df):
    phishing = df[df["label"] == 1]
    legitimate = df[df["label"] == 0]
    legitimate_sample = legitimate.sample(
        n=min(LEGITIMATE_SAMPLE_SIZE, len(legitimate)), random_state=RANDOM_SEED
    )
    return pd.concat([phishing, legitimate_sample], ignore_index=True)


def build_features_for_split(name, path):
    df = pd.read_csv(path)
    sample = build_sample(df).reset_index(drop=True)

    results = extract_features_batch(sample["url"].tolist())

    rows, errors = [], []
    for (features, error), (_, row) in zip(results, sample.iterrows()):
        if features is None:
            errors.append({"url": row["url"], "error": error})
            continue
        rows.append({**row.to_dict(), **features})

    out_df = pd.DataFrame(rows)
    out_path = f"data/processed/layer1_{name}_features.csv"
    out_df.to_csv(out_path, index=False)

    return {
        "split": name,
        "sampled": len(sample),
        "phishing_in_sample": int((sample["label"] == 1).sum()),
        "legitimate_in_sample": int((sample["label"] == 0).sum()),
        "succeeded": len(rows),
        "failed": len(errors),
        "errors": errors[:5],
    }


def main():
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("data/reports", exist_ok=True)

    summary = {
        "warning": (
            "TEMPORARY small-sample run"
        ),
        "splits": {},
    }

    for name, path in SPLITS.items():
        print(f"Processing {name} ({path})...")
        result = build_features_for_split(name, path)
        summary["splits"][name] = result
        print(json.dumps(result, indent=2))

    with open("data/reports/feature_build_summary.json", "w") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
