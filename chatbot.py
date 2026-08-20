# ============================================================
# FraudGuard AI Assistant
# ============================================================


def fraud_assistant(question):

    if question is None:

        return (
            "Please enter a question "
            "so I can assist you."
        )


    question = str(
        question
    ).strip().lower()


    if not question:

        return (
            "Please enter a question "
            "so I can assist you."
        )


    if (
        "why" in question
        and "fraud" in question
    ):

        return (
            "A transaction may be flagged because "
            "the machine-learning model detected "
            "patterns associated with fraudulent "
            "transactions, such as unusual amounts, "
            "transaction types or abnormal balance "
            "movements."
        )


    if "risk" in question:

        return (
            "FraudGuard AI classifies risk using "
            "fraud probability: below 30% is Low, "
            "30%–69.99% is Medium, and 70% or "
            "above is High."
        )


    if (
        "transaction" in question
        or "analyse" in question
        or "analyze" in question
    ):

        return (
            "FraudGuard AI analyzes transaction "
            "features and uses the trained machine "
            "learning model to estimate the "
            "probability of fraud."
        )


    if (
        "alert" in question
        or "flagged" in question
    ):

        return (
            "Fraud alerts are generated from the "
            "model's fraud probability and risk "
            "classification."
        )


    return (
        "I am FraudGuard AI Assistant 🛡️\n\n"
        "I can help explain:\n"
        "• Fraud predictions\n"
        "• Risk levels\n"
        "• Fraud alerts\n"
        "• Transaction analysis\n"
        "• Suspicious transaction patterns"
    )