import json
from collections import Counter
from pathlib import Path

import pandas as pd

DATASET = Path(__file__).resolve().parents[2] / "paysim dataset.csv"
OUTPUT = Path(__file__).resolve().parents[1] / "reports" / "dataset_profile.json"

required = {
    "step", "type", "amount",
    "oldbalanceOrg", "newbalanceOrig",
    "oldbalanceDest", "newbalanceDest",
    "isFraud", "isFlaggedFraud"
}

rows = 0
fraud_counts = Counter()
fraud_by_type = Counter()
step_counts = Counter()
step_fraud = Counter()

for chunk in pd.read_csv(DATASET, chunksize=100_000):
    missing = required - set(chunk.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    rows += len(chunk)

    fraud_counts.update(
        {str(k): int(v) for k, v in
         chunk["isFraud"].value_counts().items()}
    )

    fraud_rows = chunk.loc[chunk["isFraud"] == 1]

    fraud_by_type.update(
        fraud_rows["type"].value_counts().to_dict()
    )

    step_counts.update(
        {int(k): int(v) for k, v in
         chunk["step"].value_counts().items()}
    )

    step_fraud.update(
        {int(k): int(v) for k, v in
         fraud_rows["step"].value_counts().items()}
    )

report = {
    "dataset": DATASET.name,
    "total_rows": rows,
    "fraud_counts": dict(fraud_counts),
    "fraud_rate": fraud_counts["1"] / rows,
    "fraud_by_transaction_type": dict(fraud_by_type),
    "minimum_step": min(step_counts),
    "maximum_step": max(step_counts),
    "transactions_by_step": dict(sorted(step_counts.items())),
    "fraud_by_step": dict(sorted(step_fraud.items())),
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8"
)

print("Dataset profiling completed.")
print("Total rows:", rows)
print("Fraud rate:", round(report["fraud_rate"] * 100, 4), "%")
print("Fraud by transaction type:", dict(fraud_by_type))
print("Step range:", report["minimum_step"], "-", report["maximum_step"])
print("Profile saved:", OUTPUT)
