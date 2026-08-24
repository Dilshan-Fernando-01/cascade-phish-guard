import os
import sys

from sklearn.ensemble import RandomForestClassifier

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    compute_metrics,
    confusion_matrix,
    load_layer2_train_val,
    prepare_layer2_features,
    save_confusion_matrix,
    save_model,
    save_results,
    save_roc_curve,
)

MODEL_NAME = "layer2_random_forest"


def main():
    train, val = load_layer2_train_val()

    X_train = prepare_layer2_features(train)
    X_val = prepare_layer2_features(val)
    y_train, y_val = train["label"], val["label"]

    model = RandomForestClassifier(
        n_estimators=200,
        class_weight="balanced",
        random_state=42,
        min_samples_leaf=5,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_val)
    y_proba = model.predict_proba(X_val)[:, 1]

    metrics, has_both_classes = compute_metrics(y_val, y_pred, y_proba)
    cm = confusion_matrix(y_val, y_pred, labels=[0, 1]).tolist()
    feature_importances = dict(zip(X_train.columns, model.feature_importances_.tolist()))

    save_model(
        MODEL_NAME,
        {
            "model": model,
            "feature_columns": list(X_train.columns),
        },
    )
    if has_both_classes:
        save_roc_curve(y_val, y_proba, MODEL_NAME, metrics["auc_roc"])
    save_confusion_matrix(cm, MODEL_NAME)
    save_results(MODEL_NAME, train, val, metrics, cm, extra={"feature_importances": feature_importances})


if __name__ == "__main__":
    main()
