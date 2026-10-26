
import unittest
from pathlib import Path

from training.risk_service import FraudRiskService


ROOT = Path(__file__).resolve().parents[1]

MODEL_PATH = (
    ROOT
    / "reports"
    / "xgb_ablation"
    / "model.joblib"
)

CONTRACT_PATH = MODEL_PATH.with_name("model_contract.json")

EXPECTED_FEATURES = [
    "step",
    "type",
    "amount",
    "oldbalanceOrg",
    "oldbalanceDest",
]


class TestFraudRiskService(unittest.TestCase):
    """Tests for FraudGuard's contract-driven risk service."""

    @classmethod
    def setUpClass(cls):
        if not MODEL_PATH.is_file():
            raise FileNotFoundError(
                f"Experimental model missing: {MODEL_PATH}"
            )

        if not CONTRACT_PATH.is_file():
            raise FileNotFoundError(
                f"Model contract missing: {CONTRACT_PATH}"
            )

        cls.service = FraudRiskService(MODEL_PATH)

        cls.transaction = {
            "step": 10,
            "type": "TRANSFER",
            "amount": 250000,
            "oldbalanceOrg": 300000,
            "oldbalanceDest": 10000,
        }

    def test_valid_prediction(self):
        result = self.service.predict(self.transaction)

        self.assertIn("risk_score", result)
        self.assertIn("decision", result)
        self.assertIn("flagged_for_review", result)
        self.assertIn("decision_threshold", result)

        self.assertGreaterEqual(result["risk_score"], 0)
        self.assertLessEqual(result["risk_score"], 1)

        self.assertEqual(
            result["model_version"],
            "xgb_ablation_v1",
        )

        self.assertFalse(result["score_calibrated"])

    def test_repeatable_prediction(self):
        first = self.service.predict(self.transaction)
        second = self.service.predict(self.transaction)

        self.assertEqual(first, second)

    def test_missing_feature(self):
        incomplete = self.transaction.copy()
        incomplete.pop("amount")

        with self.assertRaises(ValueError):
            self.service.predict(incomplete)

    def test_invalid_transaction_type(self):
        invalid = self.transaction.copy()
        invalid["type"] = "UNKNOWN"

        with self.assertRaises(ValueError):
            self.service.predict(invalid)

    def test_negative_amount(self):
        invalid = self.transaction.copy()
        invalid["amount"] = -100

        with self.assertRaises(ValueError):
            self.service.predict(invalid)

    def test_invalid_step(self):
        invalid = self.transaction.copy()
        invalid["step"] = 0

        with self.assertRaises(ValueError):
            self.service.predict(invalid)

    def test_threshold_validation(self):
        with self.assertRaises(ValueError):
            FraudRiskService(
                MODEL_PATH,
                threshold=1.5,
            )

    def test_feature_schema(self):
        self.assertEqual(
            self.service.features,
            EXPECTED_FEATURES,
        )

        self.assertEqual(
            self.service.contract["feature_names"],
            EXPECTED_FEATURES,
        )

    def test_decision_matches_threshold(self):
        result = self.service.predict(self.transaction)

        # The service makes its decision using the raw score,
        # while the returned score is rounded.
        # Check the exact decision using the underlying model.
        transaction_type = self.transaction["type"]

        values = {
            "step": self.transaction["step"],
            "type": self.service.type_mapping[
                transaction_type
            ],
            "amount": self.transaction["amount"],
            "oldbalanceOrg": self.transaction["oldbalanceOrg"],
            "oldbalanceDest": self.transaction["oldbalanceDest"],
        }

        import pandas as pd

        features = pd.DataFrame(
            [values],
            columns=self.service.features,
        ).astype("float32")

        raw_score = float(
            self.service.model.predict_proba(features)[0, 1]
        )

        expected = raw_score >= self.service.threshold

        self.assertEqual(
            result["flagged_for_review"],
            expected,
        )

        self.assertEqual(
            result["decision"],
            "REVIEW" if expected else "NO_ALERT",
        )

    def test_contract_threshold(self):
        self.assertAlmostEqual(
            self.service.threshold,
            float(self.service.contract["threshold"]),
            places=12,
        )

    def test_contract_model_version(self):
        result = self.service.predict(self.transaction)

        self.assertEqual(
            result["model_version"],
            self.service.contract["model_version"],
        )


if __name__ == "__main__":
    unittest.main()
