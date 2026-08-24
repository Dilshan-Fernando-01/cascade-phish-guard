import os
import sys

from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ( 
    compute_metrics,
    confusion_matrix,
    load_layer2_train_val,
    prepare_layer2_features,
    save_confusion_matrix,
    save_model,
    save_results,
    save_roc_curve,
)

MODEL_NAME = "layer2_mlp"


def main():
    train, val = load_layer2_train_val()

    X_train = prepare_layer2_features(train)
    X_val = prepare_layer2_features(val)
    y_train, y_val = train["label"], val["label"]

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)

    model = MLPClassifier(
        hidden_layer_sizes=(64, 32),
        max_iter=2000,
        early_stopping=True,
        random_state=42,
    )
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_val_scaled)
    y_proba = model.predict_proba(X_val_scaled)[:, 1]

    metrics, has_both_classes = compute_metrics(y_val, y_pred, y_proba)
    cm = confusion_matrix(y_val, y_pred, labels=[0, 1]).tolist()

    architecture = {
        "hidden_layer_sizes": list(model.hidden_layer_sizes),
        "n_iterations_run": model.n_iter_,
        "final_training_loss": model.loss_,
    }

    save_model(
        MODEL_NAME,
        {
            "model": model,
            "scaler": scaler,
            "feature_columns": list(X_train.columns),
        },
    )
    if has_both_classes:
        save_roc_curve(y_val, y_proba, MODEL_NAME, metrics["auc_roc"])
    save_confusion_matrix(cm, MODEL_NAME)
    save_results(MODEL_NAME, train, val, metrics, cm, extra={"architecture": architecture})


if __name__ == "__main__":
    main()
