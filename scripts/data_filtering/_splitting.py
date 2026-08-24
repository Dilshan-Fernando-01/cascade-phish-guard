from urllib.parse import urlparse

import pandas as pd

TRAIN_FRACTION = 0.70
VAL_FRACTION = 0.15
RANDOM_SEED = 42

SHARED_HOSTNAME_URL_THRESHOLD = 20


def add_group_column(df):
    df = df.copy()
    df["_host"] = df["url"].apply(lambda u: urlparse(str(u)).netloc.split(":")[0])
    host_counts = df["_host"].value_counts()
    shared_hosts = set(host_counts[host_counts > SHARED_HOSTNAME_URL_THRESHOLD].index)
    df["_group"] = df.apply(
        lambda r: r["url"] if r["_host"] in shared_hosts else r["_host"], axis=1
    )
    return df.drop(columns=["_host"])


def group_split(group_order, train_frac=TRAIN_FRACTION, val_frac=VAL_FRACTION):
    n = len(group_order)
    train_end = int(n * train_frac)
    val_end = train_end + int(n * val_frac)
    return (
        set(group_order[:train_end]),
        set(group_order[train_end:val_end]),
        set(group_order[val_end:]),
    )


def split_phishing(df):
    df = add_group_column(df)
    df["_date"] = pd.to_datetime(df["collected_date"], errors="coerce")

    group_has_undated = df.groupby("_group")["_date"].apply(lambda s: s.isna().any())
    always_train_groups = set(group_has_undated[group_has_undated].index)

    dated_only = df[~df["_group"].isin(always_train_groups)]
    group_earliest = dated_only.groupby("_group")["_date"].min().sort_values()

    train_groups, val_groups, test_groups = group_split(list(group_earliest.index))
    train_groups |= always_train_groups

    train = df[df["_group"].isin(train_groups)]
    val = df[df["_group"].isin(val_groups)]
    test = df[df["_group"].isin(test_groups)]

    return (
        train.drop(columns=["_group", "_date"]),
        val.drop(columns=["_group", "_date"]),
        test.drop(columns=["_group", "_date"]),
    )


def split_legitimate(df, random_seed=RANDOM_SEED):
    df = add_group_column(df)

    groups = df["_group"].unique().tolist()
    shuffled_groups = pd.Series(groups).sample(frac=1.0, random_state=random_seed).tolist()

    train_groups, val_groups, test_groups = group_split(shuffled_groups)

    train = df[df["_group"].isin(train_groups)]
    val = df[df["_group"].isin(val_groups)]
    test = df[df["_group"].isin(test_groups)]

    return (
        train.drop(columns=["_group"]),
        val.drop(columns=["_group"]),
        test.drop(columns=["_group"]),
    )


def split_dataset(combined):
    phishing = combined[combined["label"] == 1]
    legitimate = combined[combined["label"] == 0]

    p_train, p_val, p_test = split_phishing(phishing)
    l_train, l_val, l_test = split_legitimate(legitimate)

    train = pd.concat([p_train, l_train], ignore_index=True)
    val = pd.concat([p_val, l_val], ignore_index=True)
    test = pd.concat([p_test, l_test], ignore_index=True)
    return train, val, test


def class_counts(df):
    return {
        "total": len(df),
        "phishing": int((df["label"] == 1).sum()),
        "legitimate": int((df["label"] == 0).sum()),
    }
