import json
import os

import joblib
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.preprocessing import StandardScaler

MODEL_NAME = "logistic_regression"

FEATURE_COLUMNS = [
    "url_length", "subdomain_count", "has_https", "special_char_count",
    "keyword_score", "character_entropy", "tld_risk_score", "has_ip_host",
    "has_at_symbol", "path_depth", "query_param_count", "digit_ratio",
    "is_punycode_or_homograph", "tranco_rank_bucket", "brand_distance_score",
    "brand_keyword_in_host", "domain_age_days",
]


def prepare_features(df, median_domain_age):

    X = df[FEATURE_COLUMNS].copy()
    X["domain_age_missing"] = X["domain_age_days"].isna().astype(int)
    X["domain_age_days"] = X["domain_age_days"].fillna(median_domain_age)
    return X


def main():
    train = pd.read_csv("data/processed/layer1_train_features.csv")
    val = pd.read_csv("data/processed/layer1_validation_features.csv")

    median_domain_age = train["domain_age_days"].median()

    X_train = prepare_features(train, median_domain_age)
    X_val = prepare_features(val, median_domain_age)
    y_train = train["label"]
    y_val = val["label"]


    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)

    model = LogisticRegression(max_iter=1000, random_state=42)
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_val_scaled)
    y_proba = model.predict_proba(X_val_scaled)[:, 1]

    has_both_classes = y_val.nunique() > 1
    metrics = {
        "accuracy": accuracy_score(y_val, y_pred),
        "precision": precision_score(y_val, y_pred, zero_division=0),
        "recall": recall_score(y_val, y_pred, zero_division=0),
        "f1": f1_score(y_val, y_pred, zero_division=0),
        "auc_roc": roc_auc_score(y_val, y_proba) if has_both_classes else None,
    }

    cm = confusion_matrix(y_val, y_pred, labels=[0, 1]).tolist()

    coefficients = dict(zip(X_train.columns, model.coef_[0].tolist()))

    os.makedirs("data/models", exist_ok=True)
    os.makedirs("data/reports/figures", exist_ok=True)

    joblib.dump(
        {
            "model": model,
            "scaler": scaler,
            "feature_columns": FEATURE_COLUMNS,
            "median_domain_age": median_domain_age,
        },
        f"data/models/{MODEL_NAME}.joblib",
    )

    if has_both_classes:
        fpr, tpr, _ = roc_curve(y_val, y_proba)
        plt.figure(figsize=(5, 5))
        plt.plot(fpr, tpr, label=f"AUC = {metrics['auc_roc']:.3f}")
        plt.plot([0, 1], [0, 1], linestyle="--", color="gray")
        plt.xlabel("False Positive Rate")
        plt.ylabel("True Positive Rate")
        plt.title(f"ROC Curve -- {MODEL_NAME}")
        plt.legend()
        plt.tight_layout()
        plt.savefig(f"data/reports/figures/{MODEL_NAME}_roc_curve.png", dpi=120)
        plt.close()

    plt.figure(figsize=(4, 4))
    plt.imshow(cm, cmap="Blues")
    for i in range(2):
        for j in range(2):
            plt.text(j, i, cm[i][j], ha="center", va="center")
    plt.xticks([0, 1], ["legitimate", "phishing"])
    plt.yticks([0, 1], ["legitimate", "phishing"])
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.title(f"Confusion Matrix -- {MODEL_NAME}")
    plt.tight_layout()
    plt.savefig(f"data/reports/figures/{MODEL_NAME}_confusion_matrix.png", dpi=120)
    plt.close()

    results = {
        "model": MODEL_NAME,
        "train_rows": len(train),
        "validation_rows": len(val),
        "metrics": metrics,
        "confusion_matrix": cm,
        "coefficients": coefficients,
    }

    with open(f"data/reports/{MODEL_NAME}_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(json.dumps({"model": MODEL_NAME, "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
