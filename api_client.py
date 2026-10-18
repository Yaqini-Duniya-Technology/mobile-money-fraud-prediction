
"""FraudGuard AI Enterprise — authenticated FastAPI client.

The public function names and prediction payload/return contract are preserved.
HTTP errors are evaluated before parsing the body as JSON, so upstream
plain-text or HTML 429 responses are reported accurately.
"""

import hashlib
import os

import requests

from core.config import API_HOST, API_PORT, FRAUDGUARD_API_KEY


API_URL = (
    os.getenv("FRAUDGUARD_API_URL") or f"http://{API_HOST}:{API_PORT}"
).strip().rstrip("/")

REQUIRED_FIELDS = (
    "step",
    "type",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "isFlaggedFraud",
)

ALLOWED_TYPES = {"CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"}


def get_client_key_fingerprint():
    """Return a short diagnostic fingerprint; never return the secret key."""
    return hashlib.sha256(
        str(FRAUDGUARD_API_KEY or "").encode("utf-8")
    ).hexdigest()[:12]


def _build_payload(transaction_data):
    if not isinstance(transaction_data, dict):
        raise TypeError("transaction_data must be a dictionary.")

    missing = [
        field for field in REQUIRED_FIELDS
        if field not in transaction_data
    ]

    if missing:
        raise ValueError(
            "Missing required fields: " + ", ".join(missing)
        )

    try:
        payload = {
            "step": int(transaction_data["step"]),
            "type": str(
                transaction_data["type"]
            ).strip().upper(),
            "amount": float(transaction_data["amount"]),
            "oldbalanceOrg": float(
                transaction_data["oldbalanceOrg"]
            ),
            "newbalanceOrig": float(
                transaction_data["newbalanceOrig"]
            ),
            "oldbalanceDest": float(
                transaction_data["oldbalanceDest"]
            ),
            "newbalanceDest": float(
                transaction_data["newbalanceDest"]
            ),
            "isFlaggedFraud": int(
                transaction_data["isFlaggedFraud"]
            ),
        }

    except (
        TypeError,
        ValueError,
        KeyError,
        OverflowError
    ) as exc:
        raise ValueError(
            f"Invalid transaction data: {exc}"
        ) from exc

    if payload["type"] not in ALLOWED_TYPES:
        raise ValueError(
            f"Invalid transaction type: {payload['type']}"
        )

    return payload


def _response_detail(response):
    """Extract a bounded error description from JSON or plain text."""
    try:
        data = response.json()
    except ValueError:
        data = None

    if isinstance(data, dict):
        detail = data.get(
            "detail",
            data.get("message", "")
        )

        if detail:
            return str(detail)[:300]

    # Do not show entire upstream HTML error pages.
    content_type = response.headers.get(
        "Content-Type", ""
    ).lower()

    if "text/html" in content_type:
        return (
            "HTML error page returned "
            "by an upstream service"
        )

    return (
        response.text
        or response.reason
        or "No error details"
    )[:300]


def predict_transaction(transaction_data: dict):
    """Send one prediction and return the existing FastAPI JSON result.

    Automatic retries are disabled because POST /predict
    may generate alerts or audit records.
    """

    payload = _build_payload(transaction_data)

    if not FRAUDGUARD_API_KEY:
        raise RuntimeError(
            "FRAUDGUARD_API_KEY is missing. "
            "Configure it for this environment."
        )

    try:
        response = requests.post(
            f"{API_URL}/predict",
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-API-Key": FRAUDGUARD_API_KEY,
            },
            timeout=60,
        )

    except requests.exceptions.Timeout as exc:
        raise TimeoutError(
            "FraudGuard AI API request timed out. "
            f"API URL: {API_URL}"
        ) from exc

    except requests.exceptions.ConnectionError as exc:
        raise ConnectionError(
            "Cannot connect to FraudGuard AI API at "
            f"{API_URL}. Confirm that the configured "
            "backend is reachable."
        ) from exc

    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            f"FraudGuard AI API request failed: {exc}"
        ) from exc

    # ========================================================
    # HTTP 429 — RATE LIMIT
    # ========================================================

    if response.status_code == 429:
        retry_after = response.headers.get(
            "Retry-After", "not provided"
        )

        render_id = response.headers.get(
            "Rndr-Id", "not provided"
        )

        content_type = response.headers.get(
            "Content-Type", "not provided"
        )

        raise RuntimeError(
            "FraudGuard API request was rate-limited "
            "(HTTP 429).\n"
            f"API URL: {API_URL}\n"
            f"Content-Type: {content_type}\n"
            f"Retry-After: {retry_after}\n"
            f"Render Request ID: {render_id}\n"
            f"Response: {_response_detail(response)}\n"
            "Check Streamlit and FastAPI logs "
            "before retrying."
        )

    # ========================================================
    # HTTP 401 / 403 — AUTHENTICATION
    # ========================================================

    if response.status_code in (401, 403):
        raise PermissionError(
            "FraudGuard AI API authentication failed "
            f"(HTTP {response.status_code}).\n"
            f"FastAPI response: "
            f"{_response_detail(response)}\n"
            f"API URL: {API_URL}\n"
            f"Client API-key fingerprint: "
            f"{get_client_key_fingerprint()}\n"
            "The Streamlit client and FastAPI server "
            "must use the same FRAUDGUARD_API_KEY "
            "for this deployment."
        )

    # ========================================================
    # HTTP 400 / 422 — VALIDATION
    # ========================================================

    if response.status_code in (400, 422):
        raise ValueError(
            "FastAPI rejected the transaction "
            f"(HTTP {response.status_code}): "
            f"{_response_detail(response)}"
        )

    # ========================================================
    # OTHER HTTP ERRORS
    # ========================================================

    if response.status_code != 200:
        raise RuntimeError(
            "FraudGuard API returned HTTP "
            f"{response.status_code}: "
            f"{_response_detail(response)}"
        )

    # ========================================================
    # SUCCESSFUL JSON RESPONSE
    # ========================================================

    try:
        response_data = response.json()

    except ValueError as exc:
        raise RuntimeError(
            "FraudGuard API returned HTTP 200 "
            "but its response was not valid JSON. "
            f"Content-Type: "
            f"{response.headers.get('Content-Type', 'not provided')}"
        ) from exc

    if not isinstance(response_data, dict):
        raise RuntimeError(
            "FraudGuard API returned JSON "
            "in an unexpected format."
        )

    return response_data


# ============================================================
# API HEALTH CHECK
# ============================================================

def check_api_health():
    """Return health JSON on success, otherwise None."""

    try:
        response = requests.get(
            f"{API_URL}/health",
            timeout=10
        )

        if response.status_code == 200:
            return response.json()

    except (
        requests.exceptions.RequestException,
        ValueError
    ):
        pass

    return None


# ============================================================
# MODEL INFORMATION
# ============================================================

def get_api_info():
    """Return model information on success, otherwise None."""

    try:
        response = requests.get(
            f"{API_URL}/model-info",
            timeout=10
        )

        if response.status_code == 200:
            return response.json()

    except (
        requests.exceptions.RequestException,
        ValueError
    ):
        pass

    return None
