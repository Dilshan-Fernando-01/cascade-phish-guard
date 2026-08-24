import csv
import json
import os
import sys

import pandas as pd

if os.environ.get("ENABLE_LAYER2", "").lower() not in ("1", "true", "yes"):
    sys.exit(
        "ENABLE_LAYER2 is not set, refusing to run. This script loads real "
    )

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend", "app"))
from services.layer2_analyzer import LAYER2_FEATURE_COLUMNS, analyze_layer2  # noqa: E402

SPLITS = {
    "train": "data/processed/layer2_train.csv",
    "validation": "data/processed/layer2_validation.csv",
    "test": "data/processed/layer2_test.csv",
}


def _checkpoint_path(name):
    return f"data/processed/layer2_{name}_features_checkpoint.csv"


def _final_path(name):
    return f"data/processed/layer2_{name}_features.csv"


def _load_done_urls(checkpoint_path):
    if not os.path.exists(checkpoint_path):
        return set()
    return set(pd.read_csv(checkpoint_path, usecols=["url"])["url"])


def _regenerate_final(name, checkpoint_path, total):
    if not os.path.exists(checkpoint_path):
        return {"split": name, "total": total, "succeeded": 0, "failed": 0, "complete": total == 0}
    checked = pd.read_csv(checkpoint_path)
    succeeded = checked[checked["error"].isna()]
    succeeded.drop(columns=["error"]).to_csv(_final_path(name), index=False)
    return {
        "split": name,
        "total": total,
        "succeeded": len(succeeded),
        "failed": len(checked) - len(succeeded),
        "complete": len(checked) >= total,
    }


def build_features_for_split(name, path):
    df = pd.read_csv(path)
    checkpoint_path = _checkpoint_path(name)
    done_urls = _load_done_urls(checkpoint_path)
    remaining = df[~df["url"].isin(done_urls)]

    print(f"[{name}] {len(done_urls)} already done, {len(remaining)} remaining out of {len(df)}")

    if len(remaining) == 0:
        return _regenerate_final(name, checkpoint_path, len(df))

    fieldnames = list(df.columns) + LAYER2_FEATURE_COLUMNS + ["error"]

    file_exists = os.path.exists(checkpoint_path)
    with open(checkpoint_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        for i, (_, row) in enumerate(remaining.iterrows()):
            row_dict = row.to_dict()
            try:
                result = analyze_layer2(row["url"])
                if result["success"]:
                    writer.writerow({**row_dict, **result["features"], "error": None})
                else:
                    writer.writerow({**row_dict, "error": result["error"]})
            except Exception as exc:
                writer.writerow({**row_dict, "error": f"{type(exc).__name__}: {exc}"})
            f.flush()

            if (i + 1) % 25 == 0 or (i + 1) == len(remaining):
                print(f"[{name}] {i + 1}/{len(remaining)} URLs processed")

    return _regenerate_final(name, checkpoint_path, len(df))


def main():
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("data/reports", exist_ok=True)

    summary = [build_features_for_split(name, path) for name, path in SPLITS.items()]

    with open("data/reports/layer2_feature_build_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
