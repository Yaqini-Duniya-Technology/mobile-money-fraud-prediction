"""Model-independent HTTP contract tests for the experimental risk API.

These tests exercise authentication, request validation, responses, and
failure handling without loading a trained model or private credentials.
They do not establish predictive accuracy.
"""

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from training.risk_api import app


class FakeRiskService:
    def predict(self, transaction):
        return {
            "model_version": "xgb_ablation_v1",
            "risk_score": 0.75,
            "decision_threshold": 0.5,
            "flagged_for_review": True,
            "decision": "REVIEW",
            "score_calibrated": False,
        }


class ErrorRiskService:
    def __init__(self, error):
        self.error = error

    def predict(self, transaction):
        raise self.error


class RiskApiContractTests(unittest.TestCase):
    def setUp(self):
        self.key_patch = patch.dict(
            os.environ, {"FRAUDGUARD_API_KEY": "ci-test-key"}
        )
        self.key_patch.start()
        self.client = TestClient(app)
        self.previous = getattr(app.state, "risk_service", None)
        app.state.risk_service = FakeRiskService()
        self.transaction = {
            "step": 10,
            "type": "TRANSFER",
            "amount": 250000.0,
            "oldbalanceOrg": 300000.0,
            "oldbalanceDest": 10000.0,
        }

    def tearDown(self):
        app.state.risk_service = self.previous
        self.client.close()
        self.key_patch.stop()

    def post(self, payload=None, key="ci-test-key"):
        headers = {} if key is None else {"X-API-Key": key}
        return self.client.post(
            "/api/v1/risk/score",
            json=self.transaction if payload is None else payload,
            headers=headers,
        )

    def test_authenticated_response_contract(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["decision"], "REVIEW")
        self.assertFalse(response.json()["score_calibrated"])

    def test_missing_key_rejected(self):
        self.assertEqual(self.post(key=None).status_code, 401)

    def test_invalid_key_rejected(self):
        self.assertEqual(self.post(key="wrong").status_code, 401)

    def test_extra_fields_rejected(self):
        payload = dict(self.transaction, isFraud=1)
        self.assertEqual(self.post(payload).status_code, 422)

    def test_invalid_transaction_rejected(self):
        for changes in (
            {"step": 0},
            {"amount": -1.0},
            {"type": "UNKNOWN"},
        ):
            with self.subTest(changes=changes):
                self.assertEqual(
                    self.post(dict(self.transaction, **changes)).status_code,
                    422,
                )

    def test_unavailable_model_returns_503(self):
        app.state.risk_service = None
        self.assertEqual(self.post().status_code, 503)

    def test_model_validation_error_returns_422(self):
        app.state.risk_service = ErrorRiskService(ValueError("invalid"))
        self.assertEqual(self.post().status_code, 422)

    def test_unexpected_model_error_returns_500(self):
        app.state.risk_service = ErrorRiskService(RuntimeError("failure"))
        self.assertEqual(self.post().status_code, 500)

    def test_health_reports_model_unavailable(self):
        app.state.risk_service = None
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["model_loaded"])


if __name__ == "__main__":
    unittest.main()
