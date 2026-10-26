
"""
FraudGuard AI — Experimental Risk Scoring API.

Model: xgb_ablation_v1
Framework: FastAPI
Purpose: Experimental pre-transaction risk scoring.

The API:
- Loads a versioned model and its JSON contract.
- Uses the decision threshold from the model contract.
- Requires API-key authentication for predictions.
- Validates transaction inputs.
- Returns uncalibrated model scores.
- Does not modify the existing FraudGuard prediction API.

Not intended for public production deployment.
"""

import hmac
import logging
import os

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from training.risk_service import FraudRiskService


# ============================================================
# 1. CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

ENV_PATH = ROOT / ".env"

load_dotenv(ENV_PATH)

MODEL_DIRECTORY = ROOT / "reports" / "xgb_ablation"

MODEL_PATH = MODEL_DIRECTORY / "model.joblib"

CONTRACT_PATH = MODEL_DIRECTORY / "model_contract.json"

logger = logging.getLogger("fraudguard.risk_api")


# ============================================================
# 2. APPLICATION LIFECYCLE
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Load the model during application startup.

    The FraudRiskService reads its feature schema, transaction
    encoding, model version and threshold from model_contract.json.
    """

    api_key = os.getenv("FRAUDGUARD_API_KEY", "")

    if not api_key.strip():
        raise RuntimeError(
            "FRAUDGUARD_API_KEY is missing or empty. "
            "Configure it in the repository .env file."
        )

    if not MODEL_PATH.is_file():
        raise RuntimeError(
            f"Experimental model not found: {MODEL_PATH}"
        )

    if not CONTRACT_PATH.is_file():
        raise RuntimeError(
            f"Model contract not found: {CONTRACT_PATH}"
        )

    logger.info("Loading experimental FraudGuard model")

    app.state.risk_service = FraudRiskService(MODEL_PATH)

    logger.info(
        "Experimental model loaded: %s",
        app.state.risk_service.contract["model_version"],
    )

    try:
        yield

    finally:
        app.state.risk_service = None
        logger.info("Experimental FraudGuard API stopped")


# ============================================================
# 3. FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="FraudGuard Experimental Risk API",
    version="0.2.0",
    description=(
        "Experimental pre-transaction fraud risk-scoring API. "
        "Uses a versioned XGBoost model contract. "
        "Risk scores are not calibrated fraud probabilities. "
        "Decisions are advisory and require appropriate oversight."
    ),
    lifespan=lifespan,
)


# ============================================================
# 4. REQUEST SCHEMA
# ============================================================

class TransactionRequest(BaseModel):
    """
    Transaction data available for experimental risk scoring.
    """

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
    )

    step: int = Field(
        ge=1,
        description="Positive PaySim transaction time step",
    )

    type: Literal[
        "CASH_IN",
        "CASH_OUT",
        "DEBIT",
        "PAYMENT",
        "TRANSFER",
    ]

    amount: float = Field(
        ge=0,
        allow_inf_nan=False,
        description="Transaction amount",
    )

    oldbalanceOrg: float = Field(
        ge=0,
        allow_inf_nan=False,
        description="Sender balance before transaction",
    )

    oldbalanceDest: float = Field(
        ge=0,
        allow_inf_nan=False,
        description="Receiver balance before transaction",
    )


# ============================================================
# 5. RESPONSE SCHEMA
# ============================================================

class RiskResponse(BaseModel):
    model_version: str
    risk_score: float
    decision_threshold: float
    flagged_for_review: bool
    decision: Literal["REVIEW", "NO_ALERT"]
    score_calibrated: bool


# ============================================================
# 6. API-KEY AUTHENTICATION
# ============================================================

def verify_api_key(
    x_api_key: str | None = Header(default=None),
):
    """
    Reject requests with missing or invalid API keys.
    """

    expected = os.getenv("FRAUDGUARD_API_KEY", "")

    if not expected or x_api_key is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
        )

    valid = hmac.compare_digest(
        x_api_key.encode("utf-8"),
        expected.encode("utf-8"),
    )

    if not valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
        )


# ============================================================
# 7. HEALTH ENDPOINT
# ============================================================

@app.get("/health")
def health(request: Request):
    service = getattr(
        request.app.state,
        "risk_service",
        None,
    )

    return {
        "status": "ok" if service is not None else "unavailable",
        "service": "fraudguard-experimental-risk",
        "model_loaded": service is not None,
    }


# ============================================================
# 8. TRANSACTION RISK-SCORING ENDPOINT
# ============================================================

@app.post(
    "/api/v1/risk/score",
    response_model=RiskResponse,
    dependencies=[Depends(verify_api_key)],
)
def score_transaction(
    transaction: TransactionRequest,
    request: Request,
):
    """
    Score a transaction using the experimental five-feature model.

    Returns:
        - Model version
        - Raw risk score
        - Contract-defined threshold
        - Review decision
        - Score calibration status
    """

    service = getattr(
        request.app.state,
        "risk_service",
        None,
    )

    if service is None:
        raise HTTPException(
            status_code=503,
            detail="Fraud risk model is unavailable",
        )

    try:
        result = service.predict(
            transaction.model_dump()
        )

        return result

    except (ValueError, TypeError, OverflowError) as exc:
        logger.warning(
            "Transaction validation failed: %s",
            type(exc).__name__,
        )

        raise HTTPException(
            status_code=422,
            detail="Invalid transaction values",
        ) from exc

    except Exception:
        logger.exception(
            "Unexpected error during fraud risk scoring"
        )

        raise HTTPException(
            status_code=500,
            detail="Risk scoring failed",
        )
