
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


class FraudRiskService:
    """Contract-driven experimental fraud risk scoring."""

    def __init__(self, model_path, threshold=None):
        model_path = Path(model_path)

        contract_path = model_path.with_name(
            "model_contract.json"
        )

        if not contract_path.is_file():
            raise FileNotFoundError(
                f"Model contract missing: {contract_path}"
            )

        self.contract = json.loads(
            contract_path.read_text(encoding="utf-8")
        )

        if self.contract["schema_version"] != 1:
            raise ValueError("Unsupported contract version")

        if self.contract["model_file"] != model_path.name:
            raise ValueError("Model filename mismatch")

        self.features = self.contract["feature_names"]
        self.type_mapping = self.contract[
            "transaction_type_encoding"
        ]

        self.threshold = float(
            self.contract["threshold"]
            if threshold is None
            else threshold
        )

        if not np.isfinite(self.threshold) or not (
            0 <= self.threshold <= 1
        ):
            raise ValueError("Invalid decision threshold")

        self.model = joblib.load(model_path)

        model_features = getattr(
            self.model, "feature_names_in_", None
        )

        if model_features is None:
            raise ValueError(
                "Saved model does not expose feature names"
            )

        if list(model_features) != self.features:
            raise ValueError(
                "Model and contract feature schemas differ"
            )

    def predict(self, transaction):
        missing = [
            name for name in self.features
            if name not in transaction
        ]

        if missing:
            raise ValueError(
                f"Missing transaction fields: {missing}"
            )

        transaction_type = str(
            transaction["type"]
        ).strip().upper()

        if transaction_type not in self.type_mapping:
            raise ValueError("Unsupported transaction type")

        values = {}

        for name in self.features:
            if name == "type":
                values[name] = self.type_mapping[
                    transaction_type
                ]
                continue

            value = float(transaction[name])

            if not np.isfinite(value) or value < 0:
                raise ValueError(
                    f"Invalid value for {name}"
                )

            values[name] = value

        if (
            not values["step"].is_integer()
            or values["step"] < 1
        ):
            raise ValueError("step must be a positive integer")

        features = pd.DataFrame(
            [values],
            columns=self.features,
        ).astype("float32")

        score = float(
            self.model.predict_proba(features)[0, 1]
        )

        flagged = score >= self.threshold

        return {
            "model_version": self.contract["model_version"],
            "risk_score": round(score, 6),
            "decision_threshold": self.threshold,
            "flagged_for_review": bool(flagged),
            "decision": (
                "REVIEW" if flagged else "NO_ALERT"
            ),
            "score_calibrated": self.contract[
                "score_calibrated"
            ],
        }


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]

    service = FraudRiskService(
        root / "reports" / "xgb_ablation" / "model.joblib"
    )

    sample = {
        "step": 10,
        "type": "TRANSFER",
        "amount": 250000,
        "oldbalanceOrg": 300000,
        "oldbalanceDest": 10000,
    }

    print(service.predict(sample))
