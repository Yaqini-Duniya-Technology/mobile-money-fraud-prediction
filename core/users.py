# ==========================================
# FraudGuard AI
# User Configuration & RBAC
# ==========================================

from core.security import (
    verify_password,
    hash_password,
)

from database import (
    create_user,
    get_user_by_username,
    user_exists,
)


# ==========================================
# BUILT-IN USER ACCOUNTS
# ==========================================

USERS = {
    "admin": {
        "password_hash": "$2b$12$bFspPJZazLp8rrPU/l/X4e1ApnBHC206hOEOyWv9xpSmqRNt1LZ7K",
        "role": "admin",
    },

    "analyst": {
        "password_hash": "$2b$12$jYl.lbAsHkvHaBNOaveOoODGv.ElXXBPbzzwnOvTMYWJN52TjXlpS",
        "role": "analyst",
    },

    "user": {
        "password_hash": "$2b$12$oxxKOzOB3YqA5f88X.G10eO2.BxWldB1.uxjvA1BLaNtqXkfIESxa",
        "role": "user",
    },
}


# ==========================================
# ROLE PERMISSIONS
# ==========================================

ROLE_PERMISSIONS = {
    "admin": [
        "transaction_analysis",
        "fraud_monitoring",
        "ai_assistant",
        "system_management",
    ],

    "analyst": [
        "transaction_analysis",
        "fraud_monitoring",
        "ai_assistant",
    ],

    "user": [
        "transaction_analysis",
    ],
}


# ==========================================
# AUTHENTICATE USER
# ==========================================

def authenticate_user(
    username: str,
    password: str,
):
    """
    Authenticate both built-in and registered users.
    """

    if not username or not password:

        return None

    username = (
        username
        .strip()
        .lower()
    )

    # ------------------------------------------
    # BUILT-IN ACCOUNTS
    # ------------------------------------------

    built_in_user = USERS.get(
        username
    )

    if built_in_user is not None:

        if verify_password(
            password,
            built_in_user["password_hash"],
        ):

            return {
                "username": username,
                "role": built_in_user["role"],
            }

        return None

    # ------------------------------------------
    # REGISTERED DATABASE USERS
    # ------------------------------------------

    try:

        user = get_user_by_username(
            username
        )

    except Exception:

        return None

    if user is None:

        return None

    if int(
        user["is_active"]
    ) != 1:

        return None

    if not verify_password(
        password,
        user["password_hash"],
    ):

        return None

    return {
        "username": user["username"],
        "role": user["role"],
    }


# ==========================================
# REGISTER USER
# ==========================================

def register_user(
    username: str,
    email: str,
    password: str,
):
    """
    Register a new public user.

    Every public registration receives role='user'.
    """

    username = (
        str(username)
        .strip()
        .lower()
    )

    email = (
        str(email)
        .strip()
        .lower()
    )

    password = str(
        password
    )

    # ------------------------------------------
    # BASIC VALIDATION
    # ------------------------------------------

    if not username:

        raise ValueError(
            "Username is required."
        )

    if not email:

        raise ValueError(
            "Email is required."
        )

    if not password:

        raise ValueError(
            "Password is required."
        )

    if len(username) < 3:

        raise ValueError(
            "Username must contain at least 3 characters."
        )

    if len(password) < 8:

        raise ValueError(
            "Password must contain at least 8 characters."
        )

    if "@" not in email or "." not in email:

        raise ValueError(
            "Enter a valid email address."
        )

    # ------------------------------------------
    # RESERVED BUILT-IN USERNAMES
    # ------------------------------------------

    if username in USERS:

        raise ValueError(
            "This username is reserved."
        )

    # ------------------------------------------
    # DUPLICATE CHECK
    # ------------------------------------------

    if user_exists(
        username=username,
        email=email,
    ):

        raise ValueError(
            "Username or email is already registered."
        )

    # ------------------------------------------
    # HASH PASSWORD
    # ------------------------------------------

    password_hash = hash_password(
        password
    )

    # ------------------------------------------
    # CREATE USER
    # ------------------------------------------

    user_id = create_user(
        username=username,
        email=email,
        password_hash=password_hash,
        role="user",
    )

    return {
        "id": user_id,
        "username": username,
        "email": email,
        "role": "user",
    }


# ==========================================
# CHECK USER PERMISSION
# ==========================================

def has_permission(
    role: str,
    permission: str,
) -> bool:
    """
    Check whether a role has a specific permission.
    """

    if not role or not permission:

        return False

    permissions = ROLE_PERMISSIONS.get(
        role.lower(),
        [],
    )

    return permission in permissions