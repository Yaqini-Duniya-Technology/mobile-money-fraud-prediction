from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
)

from training.train_ablation import (
    load_partitions,
    prepare,
)

MODEL_PATH = Path("reports/xgb_ablation/model.joblib")

model = joblib.load(MODEL_PATH)

print("Loading validation transactions...")

_, validation, _ = load_partitions()

X_val, y_val = prepare(validation)

probabilities = model.predict_proba(X_val)[:, 1]

thresholds = [
    0.10,
    0.30,
    0.50,
    0.70,
    0.80,
    0.90,
    0.95,
    0.96549,
    0.98,
]

results = []

for threshold in thresholds:
    predictions = (
        probabilities >= threshold
    ).astype(int)

    tn, fp, fn, tp = confusion_matrix(
        y_val, predictions, labels=[0, 1]
    ).ravel()

    results.append({
        "threshold": threshold,
        "precision": precision_score(
            y_val, predictions, zero_division=0
        ),
        "recall": recall_score(
            y_val, predictions, zero_division=0
        ),
        "f1": f1_score(
            y_val, predictions, zero_division=0
        ),
        "true_positives": int(tp),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "alert_count": int(tp + fp),
    })

report = pd.DataFrame(results)

print("\nTHRESHOLD ANALYSIS — VALIDATION SET")
print(report.to_string(index=False))

output = Path("reports/xgb_ablation/threshold_analysis.csv")

report.to_csv(output, index=False)

print("\nReport saved:", output)
