from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

DATASET = Path(__file__).resolve().parents[2] / "paysim dataset.csv"

counts = Counter()

for chunk in pd.read_csv(
    DATASET,
    chunksize=100_000,
    usecols=[
        "step", "type", "amount", "oldbalanceOrg",
        "newbalanceOrig", "oldbalanceDest",
        "newbalanceDest", "isFraud",
    ],
):
    # Diagnostic uses training and validation only.
    chunk = chunk.loc[chunk["step"] <= 398]

    relevant_type = chunk["type"].isin(
        ["TRANSFER", "CASH_OUT"]
    )

    sender_error = (
        chunk["oldbalanceOrg"]
        - chunk["amount"]
        - chunk["newbalanceOrig"]
    )

    receiver_error = (
        chunk["oldbalanceDest"]
        + chunk["amount"]
        - chunk["newbalanceDest"]
    )

    # Inspect exact balance consistency patterns.
    sender_mismatch = ~np.isclose(
        sender_error, 0, atol=0.01, rtol=0
    )

    receiver_mismatch = ~np.isclose(
        receiver_error, 0, atol=0.01, rtol=0
    )

    for label in [0, 1]:
        mask = relevant_type & (chunk["isFraud"] == label)

        counts[(label, "total")] += int(mask.sum())
        counts[(label, "sender_mismatch")] += int(
            (mask & sender_mismatch).sum()
        )
        counts[(label, "receiver_mismatch")] += int(
            (mask & receiver_mismatch).sum()
        )
        counts[(label, "both_mismatch")] += int(
            (
                mask
                & sender_mismatch
                & receiver_mismatch
            ).sum()
        )

for label, name in [
    (0, "LEGITIMATE"),
    (1, "FRAUD"),
]:
    total = counts[(label, "total")]

    print(f"\n{name} TRANSACTIONS")
    print("Total:", f"{total:,}")

    for key in [
        "sender_mismatch",
        "receiver_mismatch",
        "both_mismatch",
    ]:
        count = counts[(label, key)]
        rate = count / total * 100 if total else 0

        print(
            f"{key}: {count:,} ({rate:.2f}%)"
        )
