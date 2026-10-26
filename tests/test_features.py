import unittest

import pandas as pd

from training.features import (
    FEATURE_COLUMNS,
    engineer_features,
)


class TestFeatureEngineering(unittest.TestCase):

    def setUp(self):
        self.transaction = pd.DataFrame([{
            "step": 1,
            "type": "TRANSFER",
            "amount": 250000,
            "oldbalanceOrg": 300000,
            "newbalanceOrig": 50000,
            "oldbalanceDest": 10000,
            "newbalanceDest": 260000,
        }])

    def test_feature_schema(self):
        features = engineer_features(self.transaction)

        self.assertEqual(
            features.columns.tolist(),
            FEATURE_COLUMNS,
        )

        self.assertEqual(len(features.columns), 12)

    def test_transaction_encoding(self):
        features = engineer_features(self.transaction)

        self.assertEqual(
            int(features.iloc[0]["type"]),
            4,
        )

    def test_sender_balance_change(self):
        features = engineer_features(self.transaction)

        self.assertEqual(
            features.iloc[0]["sender_balance_change"],
            250000,
        )

    def test_receiver_balance_change(self):
        features = engineer_features(self.transaction)

        self.assertEqual(
            features.iloc[0]["receiver_balance_change"],
            250000,
        )

    def test_balance_errors(self):
        features = engineer_features(self.transaction)

        self.assertEqual(
            features.iloc[0]["sender_balance_error"],
            0,
        )

        self.assertEqual(
            features.iloc[0]["receiver_balance_error"],
            0,
        )

    def test_amount_balance_ratio(self):
        features = engineer_features(self.transaction)

        self.assertAlmostEqual(
            features.iloc[0]["amount_balance_ratio"],
            250000 / 300000,
        )

    def test_missing_columns_rejected(self):
        incomplete = self.transaction.drop(
            columns=["amount"]
        )

        with self.assertRaises(ValueError):
            engineer_features(incomplete)

    def test_unknown_transaction_type_rejected(self):
        invalid = self.transaction.copy()
        invalid["type"] = "UNKNOWN"

        with self.assertRaises(ValueError):
            engineer_features(invalid)

    def test_zero_balance_handling(self):
        transaction = self.transaction.copy()
        transaction["oldbalanceOrg"] = 0

        features = engineer_features(transaction)

        self.assertEqual(
            features.iloc[0]["amount_balance_ratio"],
            0,
        )

    def test_original_dataframe_unchanged(self):
        original = self.transaction.copy(deep=True)

        engineer_features(self.transaction)

        pd.testing.assert_frame_equal(
            self.transaction,
            original,
        )


if __name__ == "__main__":
    unittest.main()
