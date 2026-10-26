
import unittest
from pathlib import Path
from unittest.mock import patch

from dotenv import dotenv_values
from fastapi.testclient import TestClient

from training.risk_api import app
from training.risk_service import FraudRiskService


ROOT = Path(__file__).resolve().parents[1]

MODEL_PATH = (
    ROOT / "reports" / "xgb_ablation" / "model.joblib"
)

API_KEY = dotenv_values(ROOT / ".env").get(
    "FRAUDGUARD_API_KEY", ""
)


class TestRiskAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not MODEL_PATH.is_file():
            raise FileNotFoundError(
                f"Experimental model missing: {MODEL_PATH}"
            )

        cls.service = FraudRiskService(MODEL_PATH)

        cls.transaction = {
            "step": 10,
            "type": "TRANSFER",
            "amount": 250000,
            "oldbalanceOrg": 300000,
            "oldbalanceDest": 10000,
        }

        # The test API uses an isolated key rather than
        # relying on a developer's private .env credentials.
        cls.key_override = patch.dict(
            "os.environ",
            {"FRAUDGUARD_API_KEY": "local-test-key"},
        )

        cls.key_override.start()

        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)
        cls.key_override.stop()

    def send(self, payload, headers=None):
        if headers is None:
            headers = {
                "X-API-Key": "local-test-key"
            }

        return self.client.post(
            "/api/v1/risk/score",
            json=payload,
            headers=headers,
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

    def test_direct_and_http_predictions_match(self):
        direct = self.service.predict(self.transaction)

        response = self.send(self.transaction)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), direct)

    def test_invalid_api_key(self):
        response = self.send(
            self.transaction,
            headers={"X-API-Key": "invalid"},
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

        self.assertEqual(
            self.send(payload).status_code,
            422,
        )

    def test_negative_amount(self):
        payload = self.transaction.copy()
        payload["amount"] = -100

        self.assertEqual(
            self.send(payload).status_code,
            422,
        )

    def test_invalid_type(self):
        payload = self.transaction.copy()
        payload["type"] = "UNKNOWN"

        self.assertEqual(
            self.send(payload).status_code,
            422,
        )

    def test_extra_field_rejected(self):
        payload = self.transaction.copy()
        payload["isFlaggedFraud"] = 1

        self.assertEqual(
            self.send(payload).status_code,
            422,
        )

    def test_invalid_step(self):
        payload = self.transaction.copy()
        payload["step"] = 0

        self.assertEqual(
            self.send(payload).status_code,
            422,
        )

    def test_prediction_repeatability(self):
        first = self.send(self.transaction)
        second = self.send(self.transaction)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json(), second.json())


if __name__ == "__main__":
    unittest.main()
