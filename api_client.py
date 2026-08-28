# ============================================================
# FraudGuard AI
# FastAPI Client
# api_client.py
# Version 3.2.0
# ============================================================

import hashlib
import os
import requests

from core.config import (
    API_HOST,
    API_PORT,
    FRAUDGUARD_API_KEY
)


# ============================================================
# API CONFIGURATION
# ============================================================

API_URL = os.getenv(
    "FRAUDGUARD_API_URL",
    f"http://{API_HOST}:{API_PORT}"
).rstrip("/")


# ============================================================
# API KEY FINGERPRINT
# ============================================================

def get_client_key_fingerprint():

    return hashlib.sha256(

        FRAUDGUARD_API_KEY.encode(
            "utf-8"
        )

    ).hexdigest()[:12]


# ============================================================
# PREDICT TRANSACTION
# ============================================================

def predict_transaction(
    transaction_data: dict
):

    # ========================================================
    # VALIDATE INPUT
    # ========================================================

    if not isinstance(
        transaction_data,
        dict
    ):

        raise TypeError(
            "transaction_data must be a dictionary."
        )


    # ========================================================
    # REQUIRED FIELDS
    # ========================================================

    required_fields = [

        "step",
        "type",
        "amount",
        "oldbalanceOrg",
        "newbalanceOrig",
        "oldbalanceDest",
        "newbalanceDest",
        "isFlaggedFraud"

    ]


    missing = [

        field

        for field in required_fields

        if field not in transaction_data

    ]


    if missing:

        raise ValueError(

            "Missing required fields: "

            + ", ".join(
                missing
            )

        )


    # ========================================================
    # BUILD PAYLOAD
    # ========================================================

    try:

        payload = {

            "step":
                int(
                    transaction_data[
                        "step"
                    ]
                ),

            "type":
                str(
                    transaction_data[
                        "type"
                    ]
                )
                .strip()
                .upper(),

            "amount":
                float(
                    transaction_data[
                        "amount"
                    ]
                ),

            "oldbalanceOrg":
                float(
                    transaction_data[
                        "oldbalanceOrg"
                    ]
                ),

            "newbalanceOrig":
                float(
                    transaction_data[
                        "newbalanceOrig"
                    ]
                ),

            "oldbalanceDest":
                float(
                    transaction_data[
                        "oldbalanceDest"
                    ]
                ),

            "newbalanceDest":
                float(
                    transaction_data[
                        "newbalanceDest"
                    ]
                ),

            "isFlaggedFraud":
                int(
                    transaction_data[
                        "isFlaggedFraud"
                    ]
                )

        }

    except (
        TypeError,
        ValueError,
        KeyError
    ) as e:

        raise ValueError(
            f"Invalid transaction data: {e}"
        ) from e


    # ========================================================
    # VALIDATE TRANSACTION TYPE
    # ========================================================

    allowed_types = {

        "CASH_IN",
        "CASH_OUT",
        "DEBIT",
        "PAYMENT",
        "TRANSFER"

    }


    if payload["type"] not in allowed_types:

        raise ValueError(

            "Invalid transaction type: "

            f"{payload['type']}"

        )


    # ========================================================
    # API KEY VALIDATION
    # ========================================================

    if not FRAUDGUARD_API_KEY:

        raise RuntimeError(

            "FRAUDGUARD_API_KEY is missing. "
            "Check the project's .env file."

        )


    # ========================================================
    # REQUEST
    # ========================================================
    print("=== FraudGuard API DEBUG ===")
print("API_URL:", API_URL)
print("API_KEY_EXISTS:", bool(FRAUDGUARD_API_KEY))
print("API_KEY_LENGTH:", len(FRAUDGUARD_API_KEY) if FRAUDGUARD_API_KEY else 0)
print("API_KEY_FINGERPRINT:", get_client_key_fingerprint())
print("============================")

    try:

        response = requests.post(

            f"{API_URL}/predict",

            json=payload,

            headers={

                "Accept":
                    "application/json",

                "Content-Type":
                    "application/json",

                "X-API-Key":
                    FRAUDGUARD_API_KEY

            },

            timeout=60

        )


    except requests.exceptions.ConnectionError as e:

        raise ConnectionError(

            "\n"
            "❌ Cannot connect to FraudGuard AI API.\n\n"

            f"API URL: {API_URL}\n\n"

            "Start FastAPI with:\n"

            f"uvicorn api:app "
            f"--host {API_HOST} "
            f"--port {API_PORT}"

        ) from e


    except requests.exceptions.Timeout as e:

        raise TimeoutError(

            "\n"
            "❌ FraudGuard AI API request timed out.\n\n"

            f"API URL: {API_URL}"

        ) from e


    except requests.exceptions.RequestException as e:

        raise RuntimeError(

            f"❌ API request failed: {e}"

        ) from e


    # ========================================================
    # READ RESPONSE
    # ========================================================

    try:

        response_data = response.json()

    except ValueError:

        raise RuntimeError(

            "FastAPI returned an invalid response:\n"
            + response.text

        )


    # ========================================================
    # SUCCESS
    # ========================================================

    if response.status_code == 200:

        return response_data


    # ========================================================
    # AUTHENTICATION ERROR
    # ========================================================

    if response.status_code in (
        401,
        403
    ):

        detail = response_data.get(

            "detail",

            "Invalid or missing API key."

        )


        raise PermissionError(

            "🔐 FraudGuard AI API authentication failed.\n\n"

            f"FastAPI response: {detail}\n\n"

            f"API URL: {API_URL}\n"

            f"Client API-key fingerprint: "
            f"{get_client_key_fingerprint()}\n\n"

            "The client and FastAPI server must load "
            "the same FRAUDGUARD_API_KEY."

        )


    # ========================================================
    # VALIDATION ERROR
    # ========================================================

    if response.status_code == 422:

        detail = response_data.get(

            "detail",

            "FastAPI validation failed."

        )


        raise ValueError(

            "❌ FastAPI rejected the transaction.\n\n"

            f"Details: {detail}"

        )


    # ========================================================
    # SERVER ERROR
    # ========================================================

    detail = response_data.get(

        "detail",

        "Unknown API error."

    )


    raise RuntimeError(

        "FastAPI returned HTTP "

        f"{response.status_code}: "

        f"{detail}"

    )


# ============================================================
# HEALTH CHECK
# ============================================================

def check_api_health():

    try:

        response = requests.get(

            f"{API_URL}/health",

            timeout=10

        )


        if response.status_code == 200:

            return response.json()


        return None


    except requests.exceptions.RequestException:

        return None


# ============================================================
# API INFORMATION
# ============================================================

def get_api_info():

    try:

        response = requests.get(

            f"{API_URL}/model-info",

            timeout=10

        )


        if response.status_code == 200:

            return response.json()


        return None


    except requests.exceptions.RequestException:

        return None