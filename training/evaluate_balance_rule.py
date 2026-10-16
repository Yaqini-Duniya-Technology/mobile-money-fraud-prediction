from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
)

DATASET = (
    Path(__file__).resolve().parents[2]
    / "paysim dataset.csv"
)

tp = fp = tn = fn = 0

for chunk in pd.read_csv(
    DATASET,
    chunksize=100_000,
    usecols=[
        "step",
        "type",
        "amount",
        "oldbalanceOrg",
        "newbalanceOrig",
        "isFraud",
    ],
):
    # Use validation period only.
    chunk = chunk.loc[
        (chunk["step"] >= 355)
        & (chunk["step"] <= 398)
    ]

    if chunk.empty:
        continue

    relevant_type = chunk["type"].isin(
        ["TRANSFER", "CASH_OUT"]
    )

    sender_error = (
        chunk["oldbalanceOrg"]
        - chunk["amount"]
        - chunk["newbalanceOrig"]
    )

    sender_consistent = np.isclose(
        sender_error,
        0,
        atol=0.01,
        rtol=0,
    )

    prediction = (
        relevant_type & sender_consistent
    ).astype(int)

    actual = chunk["isFraud"].to_numpy()
    predicted = prediction.to_numpy()

    batch_tn, batch_fp, batch_fn, batch_tp = (
        confusion_matrix(
            actual,
            predicted,
            labels=[0, 1],
        ).ravel()
    )

    tn += int(batch_tn)
    fp += int(batch_fp)
    fn += int(batch_fn)
    tp += int(batch_tp)

precision = tp / (tp + fp) if tp + fp else 0
recall = tp / (tp + fn) if tp + fn else 0
f1 = (
    2 * precision * recall / (precision + recall)
    if precision + recall else 0
)

print("BALANCE RULE — VALIDATION RESULTS")
print("True positives:", tp)
print("False positives:", fp)
print("True negatives:", tn)
print("False negatives:", fn)
print(f"Precision: {precision:.6f}")
print(f"Recall: {recall:.6f}")
print(f"F1-score: {f1:.6f}")
