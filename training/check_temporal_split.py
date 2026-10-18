import json
from pathlib import Path

PROFILE = Path("reports/dataset_profile.json")

data = json.loads(PROFILE.read_text(encoding="utf-8"))

transactions = {
    int(k): int(v)
    for k, v in data["transactions_by_step"].items()
}

fraud = {
    int(k): int(v)
    for k, v in data["fraud_by_step"].items()
}

steps = sorted(transactions)
total = sum(transactions.values())

cutoff_train = total * 0.80
cutoff_val = total * 0.90

cumulative = 0
train_steps = []
val_steps = []
test_steps = []

for step in steps:
    # Assign complete time steps to the same partition.
    midpoint = cumulative + transactions[step] / 2

    if midpoint < cutoff_train:
        train_steps.append(step)
    elif midpoint < cutoff_val:
        val_steps.append(step)
    else:
        test_steps.append(step)

    cumulative += transactions[step]

def summarize(name, selected_steps):
    rows = sum(transactions[s] for s in selected_steps)
    fraud_cases = sum(fraud.get(s, 0) for s in selected_steps)

    result = {
        "partition": name,
        "step_start": min(selected_steps),
        "step_end": max(selected_steps),
        "transactions": rows,
        "fraud_cases": fraud_cases,
        "fraud_rate_pct": round(100 * fraud_cases / rows, 6),
    }

    print(
        f"{name}: steps {result['step_start']}-{result['step_end']}, "
        f"rows={rows:,}, fraud={fraud_cases:,}, "
        f"fraud_rate={result['fraud_rate_pct']:.6f}%"
    )
    return result

report = {
    "strategy": "chronological_non_overlapping_steps",
    "partitions": [
        summarize("TRAIN", train_steps),
        summarize("VALIDATION", val_steps),
        summarize("TEST", test_steps),
    ],
}

output = Path("reports/temporal_split_report.json")
output.write_text(json.dumps(report, indent=2), encoding="utf-8")

print("Report saved:", output)
