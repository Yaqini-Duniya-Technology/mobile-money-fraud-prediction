import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from xgboost import XGBClassifier

from training.train_baseline import (
    load_partitions,
    choose_threshold,
    SEED,
)

FEATURES = [
    "step",
    "type",
    "amount",
    "oldbalanceOrg",
    "oldbalanceDest",
]

TYPE_MAPPING = {
    "CASH_IN": 0,
    "CASH_OUT": 1,
    "DEBIT": 2,
    "PAYMENT": 3,
    "TRANSFER": 4,
}

OUTPUT = Path("reports/xgb_ablation")
OUTPUT.mkdir(parents=True, exist_ok=True)


def prepare(frame):
    X = frame[FEATURES].copy()

    X["type"] = (
        X["type"]
        .astype(str)
        .str.strip()
        .str.upper()
        .map(TYPE_MAPPING)
    )

    if X.isna().any().any():
        raise ValueError("Missing or invalid features")

    X = X.astype("float32")
    y = frame["isFraud"].to_numpy(dtype=np.int8)

    return X, y


def evaluate(y, probabilities, threshold):
    predictions = (probabilities >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(
        y, predictions, labels=[0, 1]
    ).ravel()

    return {
        "precision": float(
            precision_score(y, predictions, zero_division=0)
        ),
        "recall": float(
            recall_score(y, predictions, zero_division=0)
        ),
        "f1": float(
            f1_score(y, predictions, zero_division=0)
        ),
        "average_precision": float(
            average_precision_score(y, probabilities)
        ),
        "roc_auc": float(
            roc_auc_score(y, probabilities)
        ),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
    }


def main():
    print("Loading chronological data...")
    train, validation, test = load_partitions()

    X_train, y_train = prepare(train)
    X_val, y_val = prepare(validation)
    X_test, y_test = prepare(test)

    positive = int(np.sum(y_train == 1))
    negative = int(np.sum(y_train == 0))

    model = XGBClassifier(
        n_estimators=250,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        tree_method="hist",
        device="cpu",
        scale_pos_weight=negative / positive,
        eval_metric="logloss",
        random_state=SEED,
        n_jobs=4,
    )

    print("Training conservative feature baseline...")
    model.fit(X_train, y_train)

    validation_probabilities = (
        model.predict_proba(X_val)[:, 1]
    )

    threshold = choose_threshold(
        y_val, validation_probabilities
    )

    print("Validation-selected threshold:", threshold)

    test_probabilities = (
        model.predict_proba(X_test)[:, 1]
    )

    report = {
        "experiment": "xgboost_feature_ablation_v1",
        "features": FEATURES,
        "threshold": threshold,
        "validation": evaluate(
            y_val, validation_probabilities, threshold
        ),
        "test": evaluate(
            y_test, test_probabilities, threshold
        ),
    }

    joblib.dump(model, OUTPUT / "model.joblib")

    (OUTPUT / "metrics.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\nVALIDATION RESULTS")
    print(json.dumps(report["validation"], indent=2))

    print("\nTEST RESULTS")
    print(json.dumps(report["test"], indent=2))

    print("\nSaved to:", OUTPUT)


if __name__ == "__main__":
    main()
