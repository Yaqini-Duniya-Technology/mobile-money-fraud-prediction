# ============================================================
# FraudGuard AI
# Alert & Risk Classification System
# ============================================================


# ============================================================
# RISK CLASSIFICATION
# ============================================================

def classify_risk(probability):
    """
    Classify a transaction based on its fraud probability.

    Parameters
    ----------
    probability : float
        Fraud probability between 0 and 1.

    Returns
    -------
    str
        Low, Medium, or High
    """

    # --------------------------------------------------------
    # Handle missing probability
    # --------------------------------------------------------

    if probability is None:
        probability = 0.0

    # --------------------------------------------------------
    # Convert probability to float
    # --------------------------------------------------------

    try:

        probability = float(
            probability
        )

    except (
        TypeError,
        ValueError
    ):

        probability = 0.0

    # --------------------------------------------------------
    # Keep probability within valid range
    # --------------------------------------------------------

    probability = max(
        0.0,
        min(
            probability,
            1.0
        )
    )

    # --------------------------------------------------------
    # Risk Classification
    # --------------------------------------------------------

    if probability < 0.30:

        return "Low"

    elif probability < 0.70:

        return "Medium"

    else:

        return "High"


# ============================================================
# FRAUD ALERT GENERATION
# ============================================================

def generate_alert(probability):
    """
    Generate a fraud-risk alert based on
    the model's fraud probability.

    Parameters
    ----------
    probability : float
        Fraud probability between 0 and 1.

    Returns
    -------
    dict
        Alert status, risk level and message.
    """

    # --------------------------------------------------------
    # Validate probability
    # --------------------------------------------------------

    if probability is None:

        probability = 0.0

    try:

        probability = float(
            probability
        )

    except (
        TypeError,
        ValueError
    ):

        probability = 0.0

    # --------------------------------------------------------
    # Keep probability within valid range
    # --------------------------------------------------------

    probability = max(
        0.0,
        min(
            probability,
            1.0
        )
    )

    # --------------------------------------------------------
    # Get Risk Level
    # --------------------------------------------------------

    risk_level = classify_risk(
        probability
    )

    # ========================================================
    # HIGH RISK
    # ========================================================

    if risk_level == "High":

        return {

            "status": "HIGH_RISK",

            "risk_level": "High",

            "message": (
                "🚨 High-risk transaction detected. "
                "The AI model identified a strong "
                "pattern associated with fraudulent activity."
            )

        }

    # ========================================================
    # MEDIUM RISK
    # ========================================================

    elif risk_level == "Medium":

        return {

            "status": "MEDIUM_RISK",

            "risk_level": "Medium",

            "message": (
                "⚠️ Medium-risk transaction detected. "
                "Additional verification is recommended "
                "before completing the transaction."
            )

        }

    # ========================================================
    # LOW RISK
    # ========================================================

    else:

        return {

            "status": "LOW_RISK",

            "risk_level": "Low",

            "message": (
                "✅ Transaction appears legitimate. "
                "The AI model detected a low probability "
                "of fraud."
            )

        }


# ============================================================
# FRAUD STATUS
# ============================================================

def get_transaction_status(prediction):
    """
    Convert the model prediction into a readable
    transaction status.

    Parameters
    ----------
    prediction : int
        0 = legitimate
        1 = fraud

    Returns
    -------
    str
        LEGITIMATE or FRAUD
    """

    try:

        prediction = int(
            prediction
        )

    except (
        TypeError,
        ValueError
    ):

        prediction = 0

    if prediction == 1:

        return "FRAUD"

    return "LEGITIMATE"