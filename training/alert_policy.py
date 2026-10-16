import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT.parent / "paysim dataset.csv"
MODEL_DIR = ROOT / "reports" / "xgb_ablation"

FEATURES = [
    "step", "type", "amount",
    "oldbalanceOrg", "oldbalanceDest",
]

TYPE_MAPPING = {
    "CASH_IN": 0,
    "CASH_OUT": 1,
    "DEBIT": 2,
    "PAYMENT": 3,
    "TRANSFER": 4,
}

THRESHOLDS = [0.80, 0.90, 0.95, 0.96549, 0.98]

model = joblib.load(MODEL_DIR / "model.joblib")

counts = {
    threshold: {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    for threshold in THRESHOLDS
}

validation_rows = 0

for chunk in pd.read_csv(
    DATASET,
    usecols=[*FEATURES, "isFraud"],
    chunksize=100_000,
):
    validation = chunk.loc[
        chunk["step"].between(355, 398)
    ].copy()

    if validation.empty:
        continue

    X = validation[FEATURES].copy()

    encoded = (
        X["type"].astype(str).str.upper()
        .map(TYPE_MAPPING)
    )

    if encoded.isna().any():
        raise ValueError("Unknown transaction type")

    X["type"] = encoded
    X = X.astype("float32")

    y = validation["isFraud"].to_numpy()
    probabilities = model.predict_proba(X)[:, 1]

    validation_rows += len(y)

    for threshold in THRESHOLDS:
        predicted = probabilities >= threshold

        result = counts[threshold]

        result["tp"] += int(((y == 1) & predicted).sum())
        result["fp"] += int(((y == 0) & predicted).sum())
        result["tn"] += int(((y == 0) & ~predicted).sum())
        result["fn"] += int(((y == 1) & ~predicted).sum())

policies = []

for threshold, c in counts.items():
    alerts = c["tp"] + c["fp"]
    fraud = c["tp"] + c["fn"]

    policies.append({
        "threshold": threshold,
        "alerts": alerts,
        "alerts_per_10000": round(
            alerts / validation_rows * 10000, 2
        ),
        "precision": round(
            c["tp"] / alerts, 6
        ) if alerts else 0,
        "recall": round(
            c["tp"] / fraud, 6
        ) if fraud else 0,
        "fraud_detected": c["tp"],
        "fraud_missed": c["fn"],
        "false_alarms": c["fp"],
    })

report = {
    "dataset": "PaySim",
    "validation_steps": [355, 398],
    "validation_rows": validation_rows,
    "purpose": "Experimental alert capacity planning",
    "policies": policies,
}

output = MODEL_DIR / "alert_policy.json"
output.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8",
)

print("\nFRAUDGUARD ALERT POLICY REPORT")
print("Validation transactions:", validation_rows)

print(
    pd.DataFrame(policies).to_string(index=False)
)

print("\nSaved:", output)
