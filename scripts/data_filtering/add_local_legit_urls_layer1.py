
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend", "app"))
from features.url_features import extract_all_features, FEATURE_COLUMNS  

NEW_URLS = [
    # Universities -- UGC official list (ugc.ac.lk 2024 statistics document)
    "https://cmb.ac.lk/",
    "https://www.pdn.ac.lk/",
    "https://www.sjp.ac.lk/",
    "https://www.kln.ac.lk/",
    "https://www.jfn.ac.lk/",
    "https://www.ruh.ac.lk/",
    "https://www.sab.ac.lk/",
    "https://www.wyb.ac.lk/",
    "https://www.ou.ac.lk/",
    # Banks/finance -- CBSL official notice, "LICENSED COMMERCIAL BANKS... as at 31.12.2025"
    "https://www.amanabank.lk/",
    "https://www.dfcc.lk/",
    "https://www.nationstrust.com/",
    "https://www.ndbbank.com/",
    "https://www.sampath.lk/",
    "https://www.combank.lk/",
    "https://www.hnb.lk/",
    "https://www.sc.com/lk/",
    "https://www.boc.lk/",
    "https://www.seylan.lk/",
    "https://www.lolcfinance.com/",
    "https://www.nsb.lk/",
]

OUT_PREFIX = "data/processed/layer1"


def main():
    print(f"extracting Layer 1 features for {len(NEW_URLS)} new legit URLs (no page loads)")
    rows = []
    for url in NEW_URLS:
        feats = extract_all_features(url)
        feats["url"] = url
        feats["label"] = 0
        rows.append(feats)
        print(f"  {url}  tranco_bucket={feats['tranco_rank_bucket']}  domain_age={feats['domain_age_days']}  tld_risk={feats['tld_risk_score']}")

    new_df = pd.DataFrame(rows)

    rng = np.random.RandomState(42)
    shuffled = new_df.sample(frac=1, random_state=42).reset_index(drop=True)
    n = len(shuffled)
    n_train = int(round(n * 0.70))
    n_val = int(round(n * 0.15))
    train_new = shuffled.iloc[:n_train]
    val_new = shuffled.iloc[n_train:n_train + n_val]
    test_new = shuffled.iloc[n_train + n_val:]
    print(f"\nsplit: {len(train_new)} train / {len(val_new)} val / {len(test_new)} test")

    for split_name, new_split in [("train", train_new), ("validation", val_new), ("test", test_new)]:
        path = f"{OUT_PREFIX}_{split_name}_features.csv"
        existing = pd.read_csv(path)
        cols = [c for c in existing.columns if c in new_split.columns]
        combined = pd.concat([existing, new_split[cols]], ignore_index=True)
        combined.to_csv(path, index=False)
        print(f"{path}: {len(existing)} -> {len(combined)} rows")


if __name__ == "__main__":
    main()
