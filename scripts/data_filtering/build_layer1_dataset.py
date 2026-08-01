import json
import os

import pandas as pd

phishing = pd.read_csv("data/processed/phishing_candidates_extractable.csv")
legitimate = pd.read_csv("data/processed/legitimate_candidates_extractable.csv")

phishing["label"] = 1
legitimate["label"] = 0


combined = pd.concat([phishing, legitimate], ignore_index=True)

os.makedirs("data/processed", exist_ok=True)
os.makedirs("data/reports", exist_ok=True)

combined.to_csv("data/processed/layer1_labelled_dataset.csv", index=False)

summary = {
    "total": len(combined),
    "phishing": int((combined["label"] == 1).sum()),
    "legitimate": int((combined["label"] == 0).sum()),
    "class_ratio_legitimate_to_phishing": (
        (combined["label"] == 0).sum() / (combined["label"] == 1).sum()
        if (combined["label"] == 1).sum()
        else None
    ),
    "by_source": combined["source"].value_counts().to_dict(),
}

with open("data/reports/combined_dataset_summary.json", "w") as f:
    json.dump(summary, f, indent=2)

print(json.dumps(summary, indent=2))
