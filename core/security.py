# ============================================================
# FraudGuard AI
# Security Utilities
# ============================================================

import bcrypt


def hash_password(password: str) -> str:

    if not isinstance(password, str):
        raise TypeError("Password must be a string.")

    if not password:
        raise ValueError("Password cannot be empty.")

    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(
    password: str,
    hashed_password: str
) -> bool:

    if not isinstance(password, str):
        return False

    if not isinstance(hashed_password, str):
        return False

    if not password or not hashed_password:
        return False

    try:

        return bcrypt.checkpw(
            password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )

    except (ValueError, TypeError):
        return False