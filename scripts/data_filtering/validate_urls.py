import glob

import pandas as pd


openphish_single = pd.read_csv("data/raw/openphish.csv", header=None, names=["url"])
openphish_single["source"] = "openphish"

openphish_snapshot_files = glob.glob("data/raw/openphish/*.txt")
openphish_snapshots = pd.concat(
    [pd.read_csv(f, header=None, names=["url"]) for f in openphish_snapshot_files],
    ignore_index=True,
)
openphish_snapshots["source"] = "openphish"

phishtank_kaggle = pd.read_csv("data/raw/PhishTank.csv")
phishtank_kaggle = phishtank_kaggle.rename(columns={"URL": "url"})
phishtank_kaggle["source"] = "phishtank_kaggle"

phishtank_snapshot_files = glob.glob("data/raw/phishtank/*.txt")
phishtank_snapshots = pd.concat(
    [pd.read_csv(f)[["url"]] for f in phishtank_snapshot_files],
    ignore_index=True,
)
phishtank_snapshots["source"] = "phishtank"


tranco = pd.read_csv("data/raw/tranco.csv", header=None, names=["rank", "domain"])
tranco["url"] = "http://" + tranco["domain"]
tranco["source"] = "tranco"


phishing_candidates = pd.concat(
    [
        openphish_single[["url", "source"]],
        openphish_snapshots[["url", "source"]],
        phishtank_kaggle[["url", "source"]],
        phishtank_snapshots[["url", "source"]],
    ],
    ignore_index=True,
)

legitimate_candidates = tranco[["url", "source", "rank"]]

print("Phishing candidates by source:")
print(phishing_candidates["source"].value_counts())
print()
print("Legitimate candidates:", len(legitimate_candidates))


