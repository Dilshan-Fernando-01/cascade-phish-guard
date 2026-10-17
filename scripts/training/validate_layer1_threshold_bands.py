import sys

sys.path.insert(0, "scripts/training")

import joblib
import pandas as pd
from common import prepare_features

CANDIDATE_BANDS = [(0.1, 0.9), (0.15, 0.85), (0.2, 0.8), (0.25, 0.75), (0.3, 0.7)]
DEPLOYED_BAND = (0.2, 0.8)


def main():
    artifact = joblib.load("data/models/layer1_winner.joblib")
    model = artifact["model"]
    median_age = artifact["median_domain_age"]

    test = pd.read_csv("data/processed/layer1_test_features.csv")
    X = prepare_features(test, median_age)
    test = test.copy()
    test["score"] = model.predict_proba(X)[:, 1]

    legit = test[test["label"] == 0]["score"]
    phish = test[test["label"] == 1]["score"]

    lo, hi = DEPLOYED_BAND
    print(f"Held-out test set: {len(test)} rows ({len(legit)} legitimate, {len(phish)} phishing)")
    print()
    print(f"At the deployed band ({lo}, {hi}):")
    print(f"  legitimate correctly < {lo} (Safe):      {(legit < lo).sum()} ({100*(legit < lo).mean():.2f}%)")
    print(f"  legitimate in {lo}-{hi} (Suspicious):     {((legit >= lo) & (legit <= hi)).sum()} ({100*((legit >= lo) & (legit <= hi)).mean():.2f}%)")
    print(f"  legitimate wrongly > {hi} (Phishing):     {(legit > hi).sum()} ({100*(legit > hi).mean():.2f}%)")
    print(f"  phishing wrongly < {lo} (Safe, missed):   {(phish < lo).sum()} ({100*(phish < lo).mean():.2f}%)")
    print(f"  phishing in {lo}-{hi} (Suspicious):        {((phish >= lo) & (phish <= hi)).sum()} ({100*((phish >= lo) & (phish <= hi)).mean():.2f}%)")
    print(f"  phishing correctly > {hi} (Phishing):     {(phish > hi).sum()} ({100*(phish > hi).mean():.2f}%)")
    print()
    print("Comparison against nearby alternative bands on the same data:")
    print(f"{'band':>14}  {'escalate %':>11}  {'legit false-Phishing':>21}  {'phishing false-Safe':>20}")
    for lo, hi in CANDIDATE_BANDS:
        n_escalate = ((test["score"] >= lo) & (test["score"] <= hi)).sum()
        legit_fp = 100 * (legit > hi).mean()
        phish_fn = 100 * (phish < lo).mean()
        marker = "  <- deployed" if (lo, hi) == DEPLOYED_BAND else ""
        print(f"({lo}, {hi})  {100*n_escalate/len(test):>10.2f}%  {legit_fp:>20.2f}%  {phish_fn:>19.2f}%{marker}")


if __name__ == "__main__":
    main()
