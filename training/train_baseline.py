import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    fbeta_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from xgboost import XGBClassifier

from training.features import FEATURE_COLUMNS, engineer_features


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT.parent / "paysim dataset.csv"
OUTPUT = ROOT / "reports" / "xgb_baseline"

TRAIN_END = 354
VALIDATION_END = 398
NEGATIVE_SAMPLE_RATE = 0.03
SEED = 42

RAW_COLUMNS = [
    "step", "type", "amount",
    "oldbalanceOrg", "newbalanceOrig",
    "oldbalanceDest", "newbalanceDest",
    "isFraud",
]

DTYPES = {
    "step": "int32",
    "type": "category",
    "amount": "float32",
    "oldbalanceOrg": "float32",
    "newbalanceOrig": "float32",
    "oldbalanceDest": "float32",
    "newbalanceDest": "float32",
    "isFraud": "int8",
}


def load_partitions():
    train_parts = []
    validation_parts = []
    test_parts = []

    rng = np.random.default_rng(SEED)

    for chunk in pd.read_csv(
        DATASET,
        usecols=RAW_COLUMNS,
        dtype=DTYPES,
        chunksize=100_000,
    ):
        train = chunk.loc[
            chunk["step"] <= TRAIN_END
        ]

        positives = train.loc[
            train["isFraud"] == 1
        ]

        negatives = train.loc[
            train["isFraud"] == 0
        ]

        mask = (
            rng.random(len(negatives))
            < NEGATIVE_SAMPLE_RATE
        )

        sampled_negatives = negatives.loc[mask]

        train_parts.extend([
            positives.copy(),
            sampled_negatives.copy(),
        ])

        validation_parts.append(
            chunk.loc[
                (chunk["step"] > TRAIN_END)
                & (chunk["step"] <= VALIDATION_END)
            ].copy()
        )

        test_parts.append(
            chunk.loc[
                chunk["step"] > VALIDATION_END
            ].copy()
        )

    return (
        pd.concat(train_parts, ignore_index=True),
        pd.concat(validation_parts, ignore_index=True),
        pd.concat(test_parts, ignore_index=True),
    )


def prepare(frame):
    X = engineer_features(frame).astype("float32")
    y = frame["isFraud"].to_numpy(dtype=np.int8)
    return X, y


def metrics(y_true, probability, threshold):
    predicted = (probability >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(
        y_true, predicted, labels=[0, 1]
    ).ravel()

    return {
        "accuracy": float(
            accuracy_score(y_true, predicted)
        ),
        "precision": float(
            precision_score(
                y_true, predicted, zero_division=0
            )
        ),
        "recall": float(
            recall_score(
                y_true, predicted, zero_division=0
            )
        ),
        "f1": float(
            f1_score(y_true, predicted, zero_division=0)
        ),
        "f2": float(
            fbeta_score(
                y_true, predicted,
                beta=2,
                zero_division=0,
            )
        ),
        "average_precision": float(
            average_precision_score(y_true, probability)
        ),
        "roc_auc": float(
            roc_auc_score(y_true, probability)
        ),
        "true_positives": int(tp),
        "false_positives": int(fp),
        "true_negatives": int(tn),
        "false_negatives": int(fn),
        "fraud_prevalence": float(np.mean(y_true)),
        "alert_rate": float(np.mean(predicted)),
    }


def choose_threshold(y_true, probability):
    precision, recall, thresholds = (
        precision_recall_curve(y_true, probability)
    )

    # Last precision/recall point has no threshold.
    p = precision[:-1]
    r = recall[:-1]

    beta_squared = 4.0

    scores = (
        (1 + beta_squared) * p * r
        / np.maximum(beta_squared * p + r, 1e-12)
    )

    best_index = int(np.argmax(scores))

    return float(thresholds[best_index])


def main():
    if not DATASET.is_file():
        raise FileNotFoundError(DATASET)

    OUTPUT.mkdir(parents=True, exist_ok=True)

    print("Loading chronological partitions...")
    train, validation, test = load_partitions()

    for name, frame in [
        ("TRAIN SAMPLED", train),
        ("VALIDATION FULL", validation),
        ("TEST FULL", test),
    ]:
        fraud = int(frame["isFraud"].sum())
        print(
            f"{name}: rows={len(frame):,}, "
            f"fraud={fraud:,}"
        )

        if frame["isFraud"].nunique() != 2:
            raise ValueError(
                f"{name} does not contain both classes"
            )

    X_train, y_train = prepare(train)
    X_val, y_val = prepare(validation)
    X_test, y_test = prepare(test)

    negative_count = int(np.sum(y_train == 0))
    positive_count = int(np.sum(y_train == 1))

    weight = negative_count / positive_count

    print("Training XGBoost...")
    print("Training scale_pos_weight:", round(weight, 3))

    model = XGBClassifier(
        n_estimators=250,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        tree_method="hist",
        device="cpu",
        scale_pos_weight=weight,
        eval_metric="logloss",
        random_state=SEED,
        n_jobs=4,
    )

    model.fit(X_train, y_train)

    print("Evaluating validation partition...")
    val_probability = model.predict_proba(X_val)[:, 1]

    threshold = choose_threshold(
        y_val, val_probability
    )

    print("Selected validation F2 threshold:", threshold)

    validation_metrics = metrics(
        y_val, val_probability, threshold
    )

    print("Evaluating untouched chronological test...")
    test_probability = model.predict_proba(X_test)[:, 1]

    test_metrics = metrics(
        y_test, test_probability, threshold
    )

    report = {
        "created_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "experiment": "xgboost_temporal_baseline_v1",
        "status": "experimental",
        "prediction_timing": "post_transaction",
        "dataset": DATASET.name,
        "xgboost_version": xgboost.__version__,
        "features": FEATURE_COLUMNS,
        "train_steps": [1, TRAIN_END],
        "validation_steps": [
            TRAIN_END + 1, VALIDATION_END
        ],
        "test_steps": [
            VALIDATION_END + 1, 743
        ],
        "negative_training_sample_rate": (
            NEGATIVE_SAMPLE_RATE
        ),
        "training_rows": len(train),
        "validation_rows": len(validation),
        "test_rows": len(test),
        "scale_pos_weight": weight,
        "threshold_selection": "validation_max_f2",
        "decision_threshold": threshold,
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "limitations": [
            "Training negatives were subsampled.",
            "Predicted probabilities are not calibrated.",
            "Post-transaction balances are used.",
            "No independent external dataset was evaluated.",
        ],
    }

    joblib.dump(model, OUTPUT / "model.joblib")

    (OUTPUT / "metrics.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\nVALIDATION RESULTS")
    print(json.dumps(validation_metrics, indent=2))

    print("\nTEST RESULTS")
    print(json.dumps(test_metrics, indent=2))

    print("\nArtifacts saved to:", OUTPUT)
    print("Existing deployed model was not modified.")


if __name__ == "__main__":
    main()
