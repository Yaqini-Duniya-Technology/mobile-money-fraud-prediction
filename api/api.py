# ============================================================
# FraudGuard AI
# FastAPI AI Backend
# api.py
# Version 3.2.0
# ============================================================

import hashlib
import hmac

import pandas as pd

from fastapi import (
    FastAPI,
    HTTPException,
    Header
)

from pydantic import (
    BaseModel,
    Field
)

from core.config import (
    APP_NAME,
    API_HOST,
    API_PORT,
    FRAUDGUARD_API_KEY
)

from fraud_engine import detect_fraud

from alert_system import (
    classify_risk,
    generate_alert,
    get_transaction_status
)


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(

    title="FraudGuard AI API",

    description=(
        "AI-powered mobile money "
        "fraud detection backend"
    ),

    version="3.2.0"

)


# ============================================================
# TRANSACTION TYPES
# ============================================================

TRANSACTION_TYPES = {

    "CASH_IN": 0,
    "CASH_OUT": 1,
    "DEBIT": 2,
    "PAYMENT": 3,
    "TRANSFER": 4

}


# ============================================================
# TRANSACTION REQUEST
# ============================================================

class TransactionRequest(BaseModel):

    step: int = Field(
        ...,
        ge=1,
        description="Transaction time step"
    )

    type: str = Field(
        ...,
        description=(
            "Transaction type: "
            "CASH_IN, CASH_OUT, DEBIT, "
            "PAYMENT or TRANSFER"
        )
    )

    amount: float = Field(
        ...,
        ge=0,
        description="Transaction amount"
    )

    oldbalanceOrg: float = Field(
        ...,
        ge=0,
        description="Sender balance before transaction"
    )

    newbalanceOrig: float = Field(
        ...,
        ge=0,
        description="Sender balance after transaction"
    )

    oldbalanceDest: float = Field(
        ...,
        ge=0,
        description="Receiver balance before transaction"
    )

    newbalanceDest: float = Field(
        ...,
        ge=0,
        description="Receiver balance after transaction"
    )

    isFlaggedFraud: int = Field(
        default=0,
        ge=0,
        le=1,
        description="Original fraud flag"
    )


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {

        "message":
            f"{APP_NAME} API is running",

        "status":
            "online",

        "version":
            "3.2.0",

        "host":
            API_HOST,

        "port":
            API_PORT

    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():

    return {

        "status":
            "healthy",

        "service":
            "FraudGuard AI API",

        "authentication":
            "API key configured",

        "api_host":
            API_HOST,

        "api_port":
            API_PORT

    }


# ============================================================
# MODEL / API INFORMATION
# ============================================================

@app.get("/model-info")
def model_info():

    key_fingerprint = hashlib.sha256(

        FRAUDGUARD_API_KEY.encode(
            "utf-8"
        )

    ).hexdigest()[:12]


    return {

        "service":
            "FraudGuard AI",

        "api_version":
            "3.2.0",

        "authentication":
            "API key",

        "api_key_configured":
            bool(
                FRAUDGUARD_API_KEY
            ),

        "api_key_fingerprint":
            key_fingerprint,

        "supported_transaction_types":
            list(
                TRANSACTION_TYPES.keys()
            )

    }


# ============================================================
# API KEY VALIDATION
# ============================================================

def verify_api_key(
    x_api_key: str | None
):

    if not x_api_key:

        raise HTTPException(

            status_code=401,

            detail=(
                "Invalid or missing API key."
            )

        )


    supplied_key = (
        x_api_key.strip()
    )


    configured_key = (
        FRAUDGUARD_API_KEY.strip()
    )


    if not hmac.compare_digest(
        supplied_key,
        configured_key
    ):

        raise HTTPException(

            status_code=401,

            detail=(
                "Invalid or missing API key."
            )

        )


    return True


# ============================================================
# FEATURE ENGINEERING
# ============================================================

def engineer_features(
    transaction: TransactionRequest
):

    transaction_type = (

        str(
            transaction.type
        )
        .strip()
        .upper()

    )


    if transaction_type not in TRANSACTION_TYPES:

        raise HTTPException(

            status_code=400,

            detail=(

                f"Invalid transaction type: "
                f"{transaction_type}. "

                "Allowed types: "

                + ", ".join(
                    TRANSACTION_TYPES.keys()
                )

            )

        )


    encoded_type = TRANSACTION_TYPES[
        transaction_type
    ]


    data = pd.DataFrame({

        "step": [
            transaction.step
        ],

        "type": [
            encoded_type
        ],

        "amount": [
            transaction.amount
        ],

        "oldbalanceOrg": [
            transaction.oldbalanceOrg
        ],

        "newbalanceOrig": [
            transaction.newbalanceOrig
        ],

        "oldbalanceDest": [
            transaction.oldbalanceDest
        ],

        "newbalanceDest": [
            transaction.newbalanceDest
        ],

        "isFlaggedFraud": [
            transaction.isFlaggedFraud
        ]

    })


    # ========================================================
    # FEATURE ENGINEERING
    # ========================================================

    data[
        "sender_balance_change"
    ] = (

        data["oldbalanceOrg"]
        -
        data["newbalanceOrig"]

    )


    data[
        "receiver_balance_change"
    ] = (

        data["newbalanceDest"]
        -
        data["oldbalanceDest"]

    )


    data[
        "sender_balance_error"
    ] = (

        data["oldbalanceOrg"]
        -
        data["amount"]
        -
        data["newbalanceOrig"]

    )


    data[
        "receiver_balance_error"
    ] = (

        data["oldbalanceDest"]
        +
        data["amount"]
        -
        data["newbalanceDest"]

    )


    data[
        "amount_balance_ratio"
    ] = (

        data["amount"]
        /
        (
            data["oldbalanceOrg"]
            +
            1
        )

    )


    data[
        "large_transaction"
    ] = (

        data["amount"] > 200000

    ).astype(int)


    # ========================================================
    # MODEL FEATURES
    # ========================================================

    model_features = [

        "step",
        "type",
        "amount",
        "oldbalanceOrg",
        "newbalanceOrig",
        "oldbalanceDest",
        "newbalanceDest",
        "isFlaggedFraud",
        "sender_balance_change",
        "receiver_balance_change",
        "sender_balance_error",
        "receiver_balance_error",
        "amount_balance_ratio",
        "large_transaction"

    ]


    return data[
        model_features
    ]


# ============================================================
# PREDICTION
# ============================================================

@app.post("/predict")
def predict_fraud(

    transaction: TransactionRequest,

    x_api_key: str | None = Header(

        default=None,

        alias="X-API-Key"

    )

):

    # ========================================================
    # AUTHENTICATION
    # ========================================================

    verify_api_key(
        x_api_key
    )


    # ========================================================
    # FEATURE ENGINEERING
    # ========================================================

    try:

        data = engineer_features(
            transaction
        )

    except HTTPException:

        raise

    except Exception as e:

        raise HTTPException(

            status_code=400,

            detail=(
                "Feature engineering failed: "
                f"{str(e)}"
            )

        )


    # ========================================================
    # ML PREDICTION
    # ========================================================

    try:

        result = detect_fraud(
            data
        )

    except Exception as e:

        raise HTTPException(

            status_code=500,

            detail=(
                "AI prediction failed: "
                f"{str(e)}"
            )

        )


    # ========================================================
    # EXTRACT RESULT
    # ========================================================

    try:

        prediction = int(
            result[
                "fraud_prediction"
            ]
        )


        probability = float(
            result[
                "fraud_probability"
            ]
        )

    except (
        KeyError,
        TypeError,
        ValueError
    ) as e:

        raise HTTPException(

            status_code=500,

            detail=(
                "Invalid model response: "
                f"{str(e)}"
            )

        )


    # ========================================================
    # VALIDATE PROBABILITY
    # ========================================================

    probability = max(

        0.0,

        min(
            probability,
            1.0
        )

    )


    # ========================================================
    # RISK
    # ========================================================

    risk_level = classify_risk(
        probability
    )


    # ========================================================
    # ALERT
    # ========================================================

    alert = generate_alert(
        probability
    )


    # ========================================================
    # STATUS
    # ========================================================

    transaction_status = (
        get_transaction_status(
            prediction
        )
    )


    # ========================================================
    # RESPONSE
    # ========================================================

    return {

        "success":
            True,

        "prediction":
            prediction,

        "fraud_prediction":
            prediction,

        "fraud_probability":
            round(
                probability,
                4
            ),

        "risk_level":
            risk_level,

        "transaction_status":
            transaction_status,

        "alert_status":
            alert.get(
                "status",
                "UNKNOWN"
            ),

        "alert_message":
            alert.get(
                "message",
                ""
            )

    }