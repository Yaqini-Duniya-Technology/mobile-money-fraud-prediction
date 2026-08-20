# ============================================================
# FraudGuard AI
# Application Configuration
# core/config.py
# Version 3.1.1
# ============================================================

import os
from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# PROJECT ROOT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# ENVIRONMENT FILE
# ============================================================

ENV_FILE = BASE_DIR / ".env"


# ============================================================
# LOAD .ENV
# ============================================================

load_dotenv(
    dotenv_path=ENV_FILE,
    override=False
)


# ============================================================
# APPLICATION
# ============================================================

APP_NAME = os.getenv(
    "APP_NAME",
    "FraudGuard AI"
).strip()


APP_ENV = os.getenv(
    "APP_ENV",
    "development"
).strip()


DEBUG = (
    os.getenv(
        "DEBUG",
        "False"
    )
    .strip()
    .lower()
    == "true"
)


# ============================================================
# FASTAPI
# ============================================================

API_HOST = os.getenv(
    "API_HOST",
    "127.0.0.1"
).strip()


try:

    API_PORT = int(
        os.getenv(
            "API_PORT",
            "8001"
        ).strip()
    )

except (TypeError, ValueError) as e:

    raise RuntimeError(
        "API_PORT must be a valid integer."
    ) from e


# ============================================================
# API SECURITY
# ============================================================

FRAUDGUARD_API_KEY = os.getenv(
    "FRAUDGUARD_API_KEY"
)


if FRAUDGUARD_API_KEY is None:

    raise RuntimeError(
        "FRAUDGUARD_API_KEY is missing from:\n"
        f"{ENV_FILE}"
    )


FRAUDGUARD_API_KEY = (
    FRAUDGUARD_API_KEY.strip()
)


if not FRAUDGUARD_API_KEY:

    raise RuntimeError(
        "FRAUDGUARD_API_KEY cannot be empty."
    )


# ============================================================
# MODEL PATHS
# ============================================================

MODEL_PATH = os.getenv(
    "MODEL_PATH",
    "fraud_detection_model/final_fraud_model.pkl"
).strip()


SCALER_PATH = os.getenv(
    "SCALER_PATH",
    "fraud_detection_model/scaler.pkl"
).strip()


FEATURES_PATH = os.getenv(
    "FEATURES_PATH",
    "fraud_detection_model/features.pkl"
).strip()


# ============================================================
# DATABASE
# ============================================================

DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    "transactions.db"
).strip()


# ============================================================
# PATH RESOLUTION
# ============================================================

def resolve_project_path(
    path_value: str
) -> str:

    path = Path(
        path_value
    )

    if path.is_absolute():

        return str(path)

    return str(
        BASE_DIR / path
    )


MODEL_PATH = resolve_project_path(
    MODEL_PATH
)


SCALER_PATH = resolve_project_path(
    SCALER_PATH
)


FEATURES_PATH = resolve_project_path(
    FEATURES_PATH
)


DATABASE_PATH = resolve_project_path(
    DATABASE_PATH
)


# ============================================================
# CONFIGURATION VALIDATION
# ============================================================

def validate_config():

    errors = []


    # --------------------------------------------------------
    # API KEY
    # --------------------------------------------------------

    if not FRAUDGUARD_API_KEY:

        errors.append(
            "FRAUDGUARD_API_KEY is empty."
        )


    # --------------------------------------------------------
    # MODEL
    # --------------------------------------------------------

    if not Path(
        MODEL_PATH
    ).exists():

        errors.append(
            f"MODEL_PATH does not exist: {MODEL_PATH}"
        )


    # --------------------------------------------------------
    # SCALER
    # --------------------------------------------------------

    if not Path(
        SCALER_PATH
    ).exists():

        errors.append(
            f"SCALER_PATH does not exist: {SCALER_PATH}"
        )


    # --------------------------------------------------------
    # FEATURES
    # --------------------------------------------------------

    if not Path(
        FEATURES_PATH
    ).exists():

        errors.append(
            f"FEATURES_PATH does not exist: {FEATURES_PATH}"
        )


    # --------------------------------------------------------
    # RAISE CONFIGURATION ERROR
    # --------------------------------------------------------

    if errors:

        raise RuntimeError(
            "FraudGuard AI configuration error:\n\n"
            + "\n".join(
                f"- {error}"
                for error in errors
            )
        )


# ============================================================
# DO NOT VALIDATE MODEL FILES DURING IMPORT
# ============================================================
#
# We intentionally do NOT call validate_config() automatically
# here.
#
# This prevents configuration imports from becoming fragile
# during Streamlit/FastAPI startup.
#
# The paths are still validated by the components that load
# the model.
# ============================================================