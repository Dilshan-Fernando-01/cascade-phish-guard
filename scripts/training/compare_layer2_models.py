import json
import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import prepare_layer2_features  # noqa: E402

MODELS = ["layer2_logistic_regression", "layer2_random_forest", "layer2_xgboost", "layer2_mlp"]

TIE_BREAK_PREFERENCE = ["layer2_logistic_regression", "layer2_random_forest", "layer2_xgboost", "layer2_mlp"]

PRIMARY_METRIC = "f1"

THRESHOLD_CANDIDATES = np.round(np.arange(0.01, 1.00, 0.01), 2)


def _predict_proba(artifact, X):
    if "scaler" in artifact:
        X = artifact["scaler"].transform(X)
    return artifact["model"].predict_proba(X)[:, 1]


def _metrics_at_threshold(y_true, y_proba, threshold):
    y_pred = (y_proba >= threshold).astype(int)
    has_both = y_true.nunique() > 1
    metrics = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "auc_roc": roc_auc_score(y_true, y_proba) if has_both else None,
    }
    return metrics, confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist()


def find_best_threshold(y_val, y_proba_val):
    best_threshold, best_f1 = 0.5, -1.0
    for t in THRESHOLD_CANDIDATES:
        f1 = f1_score(y_val, (y_proba_val >= t).astype(int), zero_division=0)
        if f1 > best_f1:
            best_f1, best_threshold = f1, t
    return float(best_threshold)


def select_winner(rows):
    best_score = max(r[PRIMARY_METRIC] for r in rows)
    tied = [r["model"] for r in rows if r[PRIMARY_METRIC] == best_score]
    if len(tied) == 1:
        return tied[0], False
    for candidate in TIE_BREAK_PREFERENCE:
        if candidate in tied:
            return candidate, True
    return tied[0], True


def main():
    val = pd.read_csv("data/processed/layer2_validation_features.csv")
    test = pd.read_csv("data/processed/layer2_test_features.csv")
    X_val, y_val = prepare_layer2_features(val), val["label"]
    X_test, y_test = prepare_layer2_features(test), test["label"]

    comparison_rows = []
    test_metrics_by_model = {}
    test_cm_by_model = {}
    threshold_by_model = {}

    for model_name in MODELS:
        artifact = joblib.load(f"data/models/{model_name}.joblib")

        proba_val = _predict_proba(artifact, X_val)
        threshold = find_best_threshold(y_val, proba_val)
        val_metrics, _ = _metrics_at_threshold(y_val, proba_val, threshold)

        proba_test = _predict_proba(artifact, X_test)
        test_metrics, test_cm = _metrics_at_threshold(y_test, proba_test, threshold)

        threshold_by_model[model_name] = threshold
        test_metrics_by_model[model_name] = test_metrics
        test_cm_by_model[model_name] = test_cm
        comparison_rows.append({"model": model_name, "threshold": threshold, **val_metrics})

    winner, was_tied = select_winner(comparison_rows)

    os.makedirs("data/models", exist_ok=True)
    os.makedirs("data/reports", exist_ok=True)

    artifact = joblib.load(f"data/models/{winner}.joblib")
    joblib.dump(artifact, "data/models/layer2_winner.joblib")

    summary = {
        "comparison_table": comparison_rows,
        "primary_metric": PRIMARY_METRIC,
        "thresholds_tuned_on": (
            "Each model's own classification threshold was swept 0.01-0.99 on "
            "the validation set only (never the test set) to find its "
            "individual best-F1 cutoff, since predict_proba() outputs aren't "
            "comparable across model types at a flat 0.5 -- see "
            "data/reports/layer2_threshold_tuning.json for the full "
            "before/after breakdown per model."
        ),
        "winner": winner,
        "winner_selected_via_tiebreak": was_tied,
        "tie_break_reasoning": (
            "Occam's razor when validation performance ties, prefer the "
            "simpler/more interpretable model (order: logistic_regression > "
            "random_forest > xgboost > mlp)."
            if was_tied
            else None
        ),
        "test_set_confirmation": {
            "threshold": threshold_by_model[winner],
            "metrics": test_metrics_by_model[winner],
            "confusion_matrix": test_cm_by_model[winner],
        },
    }

    with open("data/reports/layer2_model_comparison.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(
        {
            "winner": winner,
            "was_tied": was_tied,
            "validation_comparison": comparison_rows,
            "test_confirmation": summary["test_set_confirmation"],
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
