import json
import os

import pandas as pd

TARGET_SAMPLE_SIZE = 500
RANDOM_SEED = 42 

pool = pd.read_csv("data/processed/phishing_candidates_dual_confirmed.csv")
pool_size = len(pool)


sample_size = min(TARGET_SAMPLE_SIZE, pool_size)
sample = pool.sample(n=sample_size, random_state=RANDOM_SEED).copy()


sample["vt_submitted"] = False
sample["vt_result"] = None
sample["vt_checked_at"] = None

os.makedirs("data/processed", exist_ok=True)
os.makedirs("data/reports", exist_ok=True)

sample.to_csv("data/processed/virustotal_sample.csv", index=False)

report = {
    "pool_size": pool_size,
    "target_sample_size": TARGET_SAMPLE_SIZE,
    "actual_sample_size": sample_size,
    "sampled_entire_pool": pool_size <= TARGET_SAMPLE_SIZE,
    "random_seed": RANDOM_SEED,
}

with open("data/reports/virustotal_sample_summary.json", "w") as f:
    json.dump(report, f, indent=2)

print(json.dumps(report, indent=2))
