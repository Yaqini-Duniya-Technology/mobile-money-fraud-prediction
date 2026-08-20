# ============================================================
# FraudGuard AI
# AI Fraud Prediction Engine
# ============================================================

import joblib
import pandas as pd

from core.config import (
    MODEL_PATH,
    SCALER_PATH,
    FEATURES_PATH
)


# ============================================================
# LOAD MODEL ARTIFACTS
# ============================================================

model = joblib.load(
    MODEL_PATH
)

scaler = joblib.load(
    SCALER_PATH
)

features = joblib.load(
    FEATURES_PATH
)


# ============================================================
# FRAUD DETECTION
# ============================================================

def detect_fraud(transaction):

    """
    Run fraud detection using the trained ML model.

    Parameters
    ----------
    transaction : pandas.DataFrame
        Transaction containing the required model features.

    Returns
    -------
    dict
        Fraud prediction and probability.
    """

    # --------------------------------------------------------
    # Validate input
    # --------------------------------------------------------

    if not isinstance(
        transaction,
        pd.DataFrame
    ):

        raise TypeError(
            "Transaction must be a pandas DataFrame."
        )


    # --------------------------------------------------------
    # Check required features
    # --------------------------------------------------------

    missing_features = [

        feature

        for feature in features

        if feature not in transaction.columns

    ]


    if missing_features:

        raise ValueError(

            "Missing model features: "

            + ", ".join(
                missing_features
            )

        )


    # --------------------------------------------------------
    # Select features in exact training order
    # --------------------------------------------------------

    transaction = transaction[
        features
    ].copy()


    # --------------------------------------------------------
    # Check for missing values
    # --------------------------------------------------------

    if transaction.isnull().any().any():

        raise ValueError(
            "Transaction contains missing values."
        )


    # --------------------------------------------------------
    # Scale features
    # --------------------------------------------------------

    scaled_data = scaler.transform(
        transaction
    )


    # --------------------------------------------------------
    # Prediction
    # --------------------------------------------------------

    prediction = model.predict(
        scaled_data
    )


    # --------------------------------------------------------
    # Fraud probability
    # --------------------------------------------------------

    probability = model.predict_proba(
        scaled_data
    )[0][1]


    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return {

        "fraud_prediction": int(
            prediction[0]
        ),

        "fraud_probability": round(
            float(probability),
            4
        )

    }