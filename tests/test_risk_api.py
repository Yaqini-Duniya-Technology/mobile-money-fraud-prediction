import unittest
from pathlib import Path

import requests
from dotenv import dotenv_values

from training.risk_service import FraudRiskService


ROOT = Path(__file__).resolve().parents[1]
API_URL = "http://127.0.0.1:8002/api/v1/risk/score"
MODEL_PATH = ROOT / "reports" / "xgb_ablation" / "model.joblib"

API_KEY = dotenv_values(ROOT / ".env").get(
    "FRAUDGUARD_API_KEY", ""
)


class TestRiskAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not API_KEY or not API_KEY.strip():
            raise RuntimeError(
                "FRAUDGUARD_API_KEY is missing from .env"
            )

        cls.headers = {
            "X-API-Key": API_KEY
        }

        cls.transaction = {
            "step": 10,
            "type": "TRANSFER",
            "amount": 250000,
            "oldbalanceOrg": 300000,
            "oldbalanceDest": 10000,
        }

        cls.service = FraudRiskService(MODEL_PATH)

    def send(self, payload, headers=None):
        return requests.post(
            API_URL,
            json=payload,
            headers=(
                self.headers
                if headers is None
                else headers
            ),
            timeout=10,
        )

    def test_valid_prediction(self):
        response = self.send(self.transaction)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(
            data["model_version"],
            "xgb_ablation_v1",
        )

        self.assertIn("risk_score", data)
        self.assertIn("decision", data)

    def test_direct_and_http_predictions_match(self):
        direct = self.service.predict(self.transaction)

        response = self.send(self.transaction)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), direct)

    def test_invalid_api_key(self):
        response = self.send(
            self.transaction,
            headers={"X-API-Key": "invalid-test-key"},
        )

        self.assertEqual(response.status_code, 401)

    def test_missing_api_key(self):
        response = self.send(
            self.transaction,
            headers={},
        )

        self.assertEqual(response.status_code, 401)

    def test_missing_field(self):
        payload = self.transaction.copy()
        payload.pop("amount")

        response = self.send(payload)

        self.assertEqual(response.status_code, 422)

    def test_negative_amount(self):
        payload = self.transaction.copy()
        payload["amount"] = -100

        response = self.send(payload)

        self.assertEqual(response.status_code, 422)

    def test_invalid_type(self):
        payload = self.transaction.copy()
        payload["type"] = "UNKNOWN"

        response = self.send(payload)

        self.assertEqual(response.status_code, 422)

    def test_extra_field_rejected(self):
        payload = self.transaction.copy()
        payload["isFlaggedFraud"] = 1

        response = self.send(payload)

        self.assertEqual(response.status_code, 422)

    def test_invalid_step(self):
        payload = self.transaction.copy()
        payload["step"] = 0

        response = self.send(payload)

        self.assertEqual(response.status_code, 422)

    def test_prediction_repeatability(self):
        first = self.send(self.transaction)
        second = self.send(self.transaction)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)

        self.assertEqual(first.json(), second.json())


if __name__ == "__main__":
    unittest.main()
