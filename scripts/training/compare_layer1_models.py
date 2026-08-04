import json
import os
import sys

import joblib
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
from common import prepare_features 

MODELS = ["logistic_regression", "random_forest", "xgboost", "mlp"]


TIE_BREAK_PREFERENCE = ["logistic_regression", "random_forest", "xgboost", "mlp"]

PRIMARY_METRIC = "f1"  


def load_all_results():
    results = {}
    for model_name in MODELS:
        with open(f"data/reports/{model_name}_results.json") as f:
            results[model_name] = json.load(f)
    return results


def build_comparison_table(results):
    rows = [{"model": name, **r["metrics"]} for name, r in results.items()]
    return pd.DataFrame(rows)


def select_winner(comparison_df):
    best_score = comparison_df[PRIMARY_METRIC].max()
    tied = comparison_df.loc[comparison_df[PRIMARY_METRIC] == best_score, "model"].tolist()
    if len(tied) == 1:
        return tied[0], False
    for candidate in TIE_BREAK_PREFERENCE:
        if candidate in tied:
            return candidate, True
    return tied[0], True


def evaluate_on_test(model_name):

    artifact = joblib.load(f"data/models/{model_name}.joblib")
    model = artifact["model"]
    median_domain_age = artifact["median_domain_age"]

    test = pd.read_csv("data/processed/layer1_test_features.csv")
    X_test = prepare_features(test, median_domain_age)
    y_test = test["label"]

    if "scaler" in artifact:
        X_test = artifact["scaler"].transform(X_test)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    has_both = y_test.nunique() > 1
    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1": f1_score(y_test, y_pred, zero_division=0),
        "auc_roc": roc_auc_score(y_test, y_proba) if has_both else None,
    }
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1]).tolist()
    return metrics, cm


def main():
    results = load_all_results()
    comparison_df = build_comparison_table(results)

    winner, was_tied = select_winner(comparison_df)
    test_metrics, test_cm = evaluate_on_test(winner)

    os.makedirs("data/models", exist_ok=True)
    os.makedirs("data/reports", exist_ok=True)


    artifact = joblib.load(f"data/models/{winner}.joblib")
    joblib.dump(artifact, "data/models/layer1_winner.joblib")

    summary = {
        "comparison_table": comparison_df.to_dict(orient="records"),
        "primary_metric": PRIMARY_METRIC,
        "winner": winner,
        "winner_selected_via_tiebreak": was_tied,
        "tie_break_reasoning": (
            "Occam's razor when validation performance ties, prefer the "
            "simpler/more interpretable model (order: logistic_regression > "
            "random_forest > xgboost > mlp)."
            if was_tied
            else None
        ),
        "test_set_confirmation": {"metrics": test_metrics, "confusion_matrix": test_cm},
    }

    with open("data/reports/layer1_model_comparison.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(
        {
            "winner": winner,
            "was_tied": was_tied,
            "validation_comparison": comparison_df.to_dict(orient="records"),
            "test_confirmation": test_metrics,
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
