import csv
import json
import os
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend", "app"))
from features.url_features import (  # noqa: E402
    extract_basic_features,
    tranco_rank_bucket,
    brand_distance_score,
    brand_keyword_in_host,
    domain_age_days,
)

SPLITS = {
    "train": "data/processed/layer1_train.csv",
    "validation": "data/processed/layer1_validation.csv",
    "test": "data/processed/layer1_test.csv",
}


MAX_WORKERS = 15

DOMAIN_FEATURE_COLUMNS = [
    "tranco_rank_bucket", "brand_distance_score", "brand_keyword_in_host", "domain_age_days",
]

FEATURE_COLUMNS = [
    "url_length", "subdomain_count", "has_https", "special_char_count",
    "keyword_score", "character_entropy", "tld_risk_score", "has_ip_host",
    "has_at_symbol", "path_depth", "query_param_count", "digit_ratio",
    "is_punycode_or_homograph",
] + DOMAIN_FEATURE_COLUMNS


def _host_of(url):
    return urlparse(str(url)).netloc.split(":")[0]


def _domain_features(host):
    return {
        "tranco_rank_bucket": tranco_rank_bucket(host),
        "brand_distance_score": brand_distance_score(host),
        "brand_keyword_in_host": brand_keyword_in_host(host),
        "domain_age_days": domain_age_days(host),
    }


def _checkpoint_path(name):
    # Every URL processed (success or failure) gets appended here
    # immediately -- so closing the laptop mid-run never loses progress.
    # Re-running this script picks up wherever it left off.
    return f"data/processed/layer1_{name}_features_checkpoint.csv"


def _final_path(name):
    return f"data/processed/layer1_{name}_features.csv"


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

    fieldnames = list(df.columns) + FEATURE_COLUMNS + ["error"]

    rows_by_host = defaultdict(list)
    for _, row in remaining.iterrows():
        rows_by_host[_host_of(row["url"])].append(row)
    hosts = list(rows_by_host.keys())

    file_exists = os.path.exists(checkpoint_path)
    with open(checkpoint_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_host = {executor.submit(_domain_features, host): host for host in hosts}
            completed = 0
            for future in as_completed(future_to_host):
                host = future_to_host[future]
                try:
                    domain_feats = future.result()
                except Exception:
                    domain_feats = {c: None for c in DOMAIN_FEATURE_COLUMNS}

                for row in rows_by_host[host]:
                    row_dict = row.to_dict()
                    try:
                        features = extract_basic_features(row["url"])
                        features.update(domain_feats)
                        writer.writerow({**row_dict, **features, "error": None})
                    except Exception as exc:
                        writer.writerow({**row_dict, "error": f"{type(exc).__name__}: {exc}"})
                f.flush()

                completed += 1
                if completed % 25 == 0 or completed == len(hosts):
                    print(f"[{name}] {completed}/{len(hosts)} unique hosts looked up")

    return _regenerate_final(name, checkpoint_path, len(df))


def main():
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("data/reports", exist_ok=True)

    summary = [build_features_for_split(name, path) for name, path in SPLITS.items()]

    with open("data/reports/layer1_feature_build_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
