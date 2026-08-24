import json
import os
import sys

import joblib
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend", "app"))
from features.url_features import FEATURE_COLUMNS, prepare_features
from services.layer2_analyzer import LAYER2_FEATURE_COLUMNS


def load_train_val():
    train = pd.read_csv("data/processed/layer1_train_features.csv")
    val = pd.read_csv("data/processed/layer1_validation_features.csv")
    return train, val


def load_layer2_train_val():
    train = pd.read_csv("data/processed/layer2_train_features.csv")
    val = pd.read_csv("data/processed/layer2_validation_features.csv")
    return train, val


def prepare_layer2_features(df):
    return df[LAYER2_FEATURE_COLUMNS].copy()


def compute_metrics(y_val, y_pred, y_proba):
    has_both_classes = y_val.nunique() > 1
    return {
        "accuracy": accuracy_score(y_val, y_pred),
        "precision": precision_score(y_val, y_pred, zero_division=0),
        "recall": recall_score(y_val, y_pred, zero_division=0),
        "f1": f1_score(y_val, y_pred, zero_division=0),
        "auc_roc": roc_auc_score(y_val, y_proba) if has_both_classes else None,
    }, has_both_classes


def save_roc_curve(y_val, y_proba, model_name, auc):
    fpr, tpr, _ = roc_curve(y_val, y_proba)
    plt.figure(figsize=(5, 5))
    plt.plot(fpr, tpr, label=f"AUC = {auc:.3f}")
    plt.plot([0, 1], [0, 1], linestyle="--", color="gray")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title(f"ROC Curve -- {model_name}")
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"data/reports/figures/{model_name}_roc_curve.png", dpi=120)
    plt.close()


def save_confusion_matrix(cm, model_name):
    plt.figure(figsize=(4, 4))
    plt.imshow(cm, cmap="Blues")
    for i in range(2):
        for j in range(2):
            plt.text(j, i, cm[i][j], ha="center", va="center")
    plt.xticks([0, 1], ["legitimate", "phishing"])
    plt.yticks([0, 1], ["legitimate", "phishing"])
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.title(f"Confusion Matrix -- {model_name}")
    plt.tight_layout()
    plt.savefig(f"data/reports/figures/{model_name}_confusion_matrix.png", dpi=120)
    plt.close()


def save_results(model_name, train, val, metrics, cm, extra=None):
    os.makedirs("data/reports", exist_ok=True)
    results = {
        "model": model_name,
        "train_rows": len(train),
        "validation_rows": len(val),
        "metrics": metrics,
        "confusion_matrix": cm,
        **(extra or {}),
    }
    with open(f"data/reports/{model_name}_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(json.dumps({"model": model_name, "metrics": metrics}, indent=2))


def save_model(model_name, artifact):
    os.makedirs("data/models", exist_ok=True)
    joblib.dump(artifact, f"data/models/{model_name}.joblib")
