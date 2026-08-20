# ==========================================
# FraudGuard AI
# User Configuration & RBAC
# ==========================================

from core.security import verify_password


# ==========================================
# USER ACCOUNTS
# ==========================================

USERS = {
    "admin": {
        "password_hash": "$2b$12$bFspPJZazLp8rrPU/l/X4e1ApnBHC206hOEOyWv9xpSmqRNt1LZ7K",
        "role": "admin"
    },

    "analyst": {
        "password_hash": "$2b$12$jYl.lbAsHkvHaBNOaveOoODGv.ElXXBPbzzwnOvTMYWJN52TjXlpS",
        "role": "analyst"
    },

    "user": {
        "password_hash": "$2b$12$oxxKOzOB3YqA5f88X.G10eO2.BxWldB1.uxjvA1BLaNtqXkfIESxa",
        "role": "user"
    }
}


# ==========================================
# ROLE PERMISSIONS
# ==========================================

ROLE_PERMISSIONS = {
    "admin": [
        "transaction_analysis",
        "fraud_monitoring",
        "ai_assistant",
        "system_management"
    ],

    "analyst": [
        "transaction_analysis",
        "fraud_monitoring",
        "ai_assistant"
    ],

    "user": [
        "transaction_analysis"
    ]
}


# ==========================================
# AUTHENTICATE USER
# ==========================================

def authenticate_user(
    username: str,
    password: str
):
    """
    Authenticate a user using bcrypt.
    """

    if not username or not password:
        return None

    username = username.strip().lower()

    user = USERS.get(username)

    if user is None:
        return None

    if not verify_password(
        password,
        user["password_hash"]
    ):
        return None

    return {
        "username": username,
        "role": user["role"]
    }


# ==========================================
# CHECK USER PERMISSION
# ==========================================

def has_permission(
    role: str,
    permission: str
) -> bool:
    """
    Check whether a role has a specific permission.
    """

    if not role or not permission:
        return False

    permissions = ROLE_PERMISSIONS.get(
        role.lower(),
        []
    )

    return permission in permissions