import numpy as np
import pandas as pd

TRANSACTION_TYPES = {
    "CASH_IN": 0,
    "CASH_OUT": 1,
    "DEBIT": 2,
    "PAYMENT": 3,
    "TRANSFER": 4,
}

FEATURE_COLUMNS = [
    "step",
    "type",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "sender_balance_change",
    "receiver_balance_change",
    "sender_balance_error",
    "receiver_balance_error",
    "amount_balance_ratio",
]

REQUIRED_COLUMNS = [
    "step",
    "type",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
]


def engineer_features(data: pd.DataFrame) -> pd.DataFrame:
    """Produce deterministic post-transaction fraud features."""

    missing = set(REQUIRED_COLUMNS) - set(data.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    result = data.copy()

    transaction_types = (
        result["type"].astype(str).str.strip().str.upper()
    )

    invalid = set(transaction_types) - set(TRANSACTION_TYPES)

    if invalid:
        raise ValueError(
            f"Unsupported transaction types: {sorted(invalid)}"
        )

    result["type"] = transaction_types.map(TRANSACTION_TYPES)

    numeric_columns = [
        column for column in REQUIRED_COLUMNS
        if column != "type"
    ]

    for column in numeric_columns:
        result[column] = pd.to_numeric(
            result[column], errors="raise"
        )

    result["sender_balance_change"] = (
        result["oldbalanceOrg"] - result["newbalanceOrig"]
    )

    result["receiver_balance_change"] = (
        result["newbalanceDest"] - result["oldbalanceDest"]
    )

    result["sender_balance_error"] = (
        result["oldbalanceOrg"]
        - result["amount"]
        - result["newbalanceOrig"]
    )

    result["receiver_balance_error"] = (
        result["oldbalanceDest"]
        + result["amount"]
        - result["newbalanceDest"]
    )

    result["amount_balance_ratio"] = (
        result["amount"]
        / result["oldbalanceOrg"].replace(0, np.nan)
    ).fillna(0)

    features = result[FEATURE_COLUMNS].copy()

    if not np.isfinite(features.to_numpy(dtype=float)).all():
        raise ValueError("Feature matrix contains invalid values")

    return features
