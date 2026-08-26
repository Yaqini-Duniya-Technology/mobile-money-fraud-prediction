# ============================================================
# FraudGuard AI
# Transaction Database + Enterprise Audit Logging
# database.py
# Version 3.7.0
# ============================================================

import secrets
import sqlite3
from datetime import datetime
from pathlib import Path

from core.config import DATABASE_PATH


# ============================================================
# DATABASE PATH
# ============================================================

def get_database_path() -> Path:
    """
    Return the absolute database path configured for FraudGuard AI.

    The parent directory is created automatically if it does
    not already exist.
    """

    database_path = Path(
        DATABASE_PATH
    )

    database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    return database_path.resolve()


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    """
    Create and return a SQLite database connection.

    Uses the configured database path and enables foreign keys.
    """

    database_path = get_database_path()

    conn = sqlite3.connect(
        str(database_path),
        timeout=30,
    )

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conn


# ============================================================
# TRANSACTION ID
# ============================================================

def generate_transaction_id():
    """
    Generate a unique FraudGuard transaction identifier.

    Example:
        FG-20260826084559-3D50155E
    """

    timestamp = datetime.now().strftime(
        "%Y%m%d%H%M%S"
    )

    random_part = secrets.token_hex(
        4
    ).upper()

    return (
        f"FG-{timestamp}-{random_part}"
    )


# ============================================================
# DATABASE INITIALIZATION / MIGRATION
# ============================================================

def create_database():
    """
    Create all required FraudGuard AI database tables.

    Safely migrates an existing database by adding missing
    columns without deleting existing transaction or audit data.
    """

    conn = get_connection()

    try:

        cursor = conn.cursor()

        # ====================================================
        # TRANSACTIONS TABLE
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                timestamp TEXT,

                username TEXT,

                step INTEGER,

                transaction_type TEXT,

                amount REAL,

                oldbalanceOrg REAL,

                newbalanceOrig REAL,

                oldbalanceDest REAL,

                newbalanceDest REAL,

                isFlaggedFraud INTEGER,

                prediction INTEGER,

                probability REAL,

                risk_level TEXT,

                status TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                transaction_id TEXT

            )
            """
        )

        # ====================================================
        # TRANSACTION TABLE MIGRATION
        # ====================================================

        cursor.execute(
            "PRAGMA table_info(transactions)"
        )

        existing_transaction_columns = {
            row["name"]
            for row in cursor.fetchall()
        }

        required_transaction_columns = {
            "timestamp": "TEXT",
            "username": "TEXT",
            "step": "INTEGER",
            "transaction_type": "TEXT",
            "amount": "REAL",
            "oldbalanceOrg": "REAL",
            "newbalanceOrig": "REAL",
            "oldbalanceDest": "REAL",
            "newbalanceDest": "REAL",
            "isFlaggedFraud": "INTEGER",
            "prediction": "INTEGER",
            "probability": "REAL",
            "risk_level": "TEXT",
            "status": "TEXT",
            "created_at": "TIMESTAMP",
            "transaction_id": "TEXT",
        }

        for column, data_type in (
            required_transaction_columns.items()
        ):

            if column not in existing_transaction_columns:

                cursor.execute(
                    f"""
                    ALTER TABLE transactions
                    ADD COLUMN {column} {data_type}
                    """
                )

        # ====================================================
        # AUDIT LOG TABLE
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                timestamp TEXT NOT NULL,

                username TEXT,

                event_type TEXT NOT NULL,

                action TEXT NOT NULL,

                status TEXT NOT NULL,

                ip_address TEXT,

                details TEXT

            )
            """
        )

        # ====================================================
        # AUDIT LOG TABLE MIGRATION
        # ====================================================

        cursor.execute(
            "PRAGMA table_info(audit_logs)"
        )

        existing_audit_columns = {
            row["name"]
            for row in cursor.fetchall()
        }

        required_audit_columns = {
            "timestamp": "TEXT",
            "username": "TEXT",
            "event_type": "TEXT",
            "action": "TEXT",
            "status": "TEXT",
            "ip_address": "TEXT",
            "details": "TEXT",
        }

        for column, data_type in (
            required_audit_columns.items()
        ):

            if column not in existing_audit_columns:

                cursor.execute(
                    f"""
                    ALTER TABLE audit_logs
                    ADD COLUMN {column} {data_type}
                    """
                )

        # ====================================================
        # USERS TABLE
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                username TEXT NOT NULL UNIQUE,

                email TEXT NOT NULL UNIQUE,

                password_hash TEXT NOT NULL,

                role TEXT NOT NULL DEFAULT 'user',

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                is_active INTEGER NOT NULL DEFAULT 1

            )
            """
        )

        # ====================================================
        # USERS TABLE MIGRATION
        # ====================================================

        cursor.execute(
            "PRAGMA table_info(users)"
        )

        existing_user_columns = {
            row["name"]
            for row in cursor.fetchall()
        }

        required_user_columns = {
            "username": "TEXT",
            "email": "TEXT",
            "password_hash": "TEXT",
            "role": "TEXT",
            "created_at": "TIMESTAMP",
            "is_active": "INTEGER",
        }

        for column, data_type in (
            required_user_columns.items()
        ):

            if column not in existing_user_columns:

                cursor.execute(
                    f"""
                    ALTER TABLE users
                    ADD COLUMN {column} {data_type}
                    """
                )

        # ====================================================
        # USERS DATA NORMALIZATION
        # ====================================================

        cursor.execute(
            """
            UPDATE users
            SET role = 'user'
            WHERE role IS NULL
               OR TRIM(role) = ''
            """
        )

        cursor.execute(
            """
            UPDATE users
            SET is_active = 1
            WHERE is_active IS NULL
            """
        )

        # ====================================================
        # TRANSACTION INDEXES
        # ====================================================

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_transactions_timestamp
            ON transactions(timestamp)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_transactions_username
            ON transactions(username)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_transactions_prediction
            ON transactions(prediction)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_transactions_risk_level
            ON transactions(risk_level)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_transactions_transaction_id
            ON transactions(transaction_id)
            """
        )

        # ====================================================
        # AUDIT LOG INDEXES
        # ====================================================

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_audit_logs_timestamp
            ON audit_logs(timestamp)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_audit_logs_username
            ON audit_logs(username)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_audit_logs_event_type
            ON audit_logs(event_type)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_audit_logs_status
            ON audit_logs(status)
            """
        )

        # ====================================================
        # USER INDEXES
        # ====================================================

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_users_username
            ON users(username)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_users_email
            ON users(email)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_users_role
            ON users(role)
            """
        )

        # ====================================================
        # TRANSACTION DATA NORMALIZATION
        # ====================================================

        cursor.execute(
            """
            UPDATE transactions
            SET created_at = COALESCE(
                created_at,
                timestamp,
                CURRENT_TIMESTAMP
            )
            WHERE created_at IS NULL
            """
        )

        # ====================================================
        # GENERATE MISSING TRANSACTION IDS
        # ====================================================

        cursor.execute(
            """
            SELECT id
            FROM transactions
            WHERE transaction_id IS NULL
               OR TRIM(transaction_id) = ''
            ORDER BY id
            """
        )

        missing_transaction_ids = (
            cursor.fetchall()
        )

        for row in missing_transaction_ids:

            transaction_id = (
                generate_transaction_id()
            )

            cursor.execute(
                """
                UPDATE transactions
                SET transaction_id = ?
                WHERE id = ?
                """,
                (
                    transaction_id,
                    row["id"],
                ),
            )

        conn.commit()

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


# ============================================================
# DATABASE HEALTH CHECK
# ============================================================

def check_database_health():
    """
    Check the FraudGuard AI database and schema.
    """

    database_path = (
        get_database_path()
    )

    result = {
        "healthy": False,
        "database": str(database_path),
        "transactions_table": False,
        "audit_logs_table": False,
        "users_table": False,
        "transaction_columns": [],
        "audit_columns": [],
        "user_columns": [],
        "transactions": 0,
        "audit_logs": 0,
        "users": 0,
        "error": None,
    }

    conn = None

    try:

        conn = get_connection()

        cursor = conn.cursor()

        # ----------------------------------------------------
        # TRANSACTIONS TABLE
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name = 'transactions'
            """
        )

        if cursor.fetchone():

            result["transactions_table"] = True

            cursor.execute(
                "PRAGMA table_info(transactions)"
            )

            result["transaction_columns"] = [
                row["name"]
                for row in cursor.fetchall()
            ]

            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM transactions
                """
            )

            result["transactions"] = int(
                cursor.fetchone()["count"]
            )

        # ----------------------------------------------------
        # AUDIT LOGS TABLE
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name = 'audit_logs'
            """
        )

        if cursor.fetchone():

            result["audit_logs_table"] = True

            cursor.execute(
                "PRAGMA table_info(audit_logs)"
            )

            result["audit_columns"] = [
                row["name"]
                for row in cursor.fetchall()
            ]

            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM audit_logs
                """
            )

            result["audit_logs"] = int(
                cursor.fetchone()["count"]
            )

        # ----------------------------------------------------
        # USERS TABLE
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name = 'users'
            """
        )

        if cursor.fetchone():

            result["users_table"] = True

            cursor.execute(
                "PRAGMA table_info(users)"
            )

            result["user_columns"] = [
                row["name"]
                for row in cursor.fetchall()
            ]

            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM users
                """
            )

            result["users"] = int(
                cursor.fetchone()["count"]
            )

        required_transaction_columns = {
            "id",
            "timestamp",
            "username",
            "step",
            "transaction_type",
            "amount",
            "oldbalanceOrg",
            "newbalanceOrig",
            "oldbalanceDest",
            "newbalanceDest",
            "isFlaggedFraud",
            "prediction",
            "probability",
            "risk_level",
            "status",
            "created_at",
            "transaction_id",
        }

        required_audit_columns = {
            "id",
            "timestamp",
            "username",
            "event_type",
            "action",
            "status",
            "ip_address",
            "details",
        }

        required_user_columns = {
            "id",
            "username",
            "email",
            "password_hash",
            "role",
            "created_at",
            "is_active",
        }

        transaction_schema_ok = (
            required_transaction_columns
            .issubset(
                set(
                    result[
                        "transaction_columns"
                    ]
                )
            )
        )

        audit_schema_ok = (
            required_audit_columns
            .issubset(
                set(
                    result[
                        "audit_columns"
                    ]
                )
            )
        )

        user_schema_ok = (
            required_user_columns
            .issubset(
                set(
                    result[
                        "user_columns"
                    ]
                )
            )
        )

        result["healthy"] = (
            result["transactions_table"]
            and result["audit_logs_table"]
            and result["users_table"]
            and transaction_schema_ok
            and audit_schema_ok
            and user_schema_ok
        )

    except Exception as exc:

        result["error"] = str(exc)

    finally:

        if conn is not None:

            conn.close()

    return result


# ============================================================
# SAVE TRANSACTION
# ============================================================

def save_transaction(
    step,
    transaction_type,
    amount,
    oldbalance_org,
    newbalance_orig,
    oldbalance_dest,
    newbalance_dest,
    is_flagged_fraud,
    prediction,
    probability,
    risk_level,
    status,
    username=None,
):
    """
    Save a fraud-analysis transaction.

    Returns:
        int: Newly created database row ID.
    """

    conn = get_connection()

    try:

        cursor = conn.cursor()

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        transaction_id = (
            generate_transaction_id()
        )

        cursor.execute(
            """
            INSERT INTO transactions (

                timestamp,
                username,
                step,
                transaction_type,
                amount,
                oldbalanceOrg,
                newbalanceOrig,
                oldbalanceDest,
                newbalanceDest,
                isFlaggedFraud,
                prediction,
                probability,
                risk_level,
                status,
                created_at,
                transaction_id

            )

            VALUES (

                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?

            )
            """,
            (
                timestamp,
                username,
                step,
                transaction_type,
                amount,
                oldbalance_org,
                newbalance_orig,
                oldbalance_dest,
                newbalance_dest,
                is_flagged_fraud,
                prediction,
                probability,
                risk_level,
                status,
                timestamp,
                transaction_id,
            ),
        )

        database_id = cursor.lastrowid

        conn.commit()

        return database_id

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


# ============================================================
# GET ALL TRANSACTIONS
# ============================================================

def get_all_transactions():
    """
    Return all transactions ordered newest first.
    """

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM transactions
            ORDER BY id DESC
            """
        )

        return cursor.fetchall()

    finally:

        conn.close()


# ============================================================
# DATABASE STATISTICS
# ============================================================

def get_database_statistics():
    """
    Return aggregate statistics for the monitoring dashboard.
    """

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT

                COUNT(*) AS total_transactions,

                COALESCE(
                    SUM(
                        CASE
                            WHEN prediction = 1
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS fraud_transactions,

                COALESCE(
                    SUM(
                        CASE
                            WHEN risk_level = 'High'
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS high_risk_transactions,

                COALESCE(
                    SUM(amount),
                    0
                ) AS total_amount,

                COALESCE(
                    AVG(probability),
                    0
                ) AS average_probability

            FROM transactions
            """
        )

        row = cursor.fetchone()

        total_transactions = int(
            row[
                "total_transactions"
            ] or 0
        )

        fraud_transactions = int(
            row[
                "fraud_transactions"
            ] or 0
        )

        high_risk_transactions = int(
            row[
                "high_risk_transactions"
            ] or 0
        )

        total_amount = float(
            row[
                "total_amount"
            ] or 0.0
        )

        average_probability = float(
            row[
                "average_probability"
            ] or 0.0
        )

        fraud_rate = (
            fraud_transactions
            / total_transactions
            if total_transactions > 0
            else 0.0
        )

        return {
            "total_transactions":
                total_transactions,

            "fraud_transactions":
                fraud_transactions,

            "high_risk_transactions":
                high_risk_transactions,

            "fraud_rate":
                fraud_rate,

            "total_amount":
                total_amount,

            "average_probability":
                average_probability,
        }

    finally:

        conn.close()


# ============================================================
# SAVE AUDIT LOG
# ============================================================

def save_audit_log(
    username,
    event_type,
    action,
    status,
    ip_address=None,
    details=None,
):
    """
    Save an enterprise audit/security event.

    Returns:
        int: Newly created audit log ID.
    """

    conn = get_connection()

    try:

        cursor = conn.cursor()

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        cursor.execute(
            """
            INSERT INTO audit_logs (

                timestamp,
                username,
                event_type,
                action,
                status,
                ip_address,
                details

            )

            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                username,
                event_type,
                action,
                status,
                ip_address,
                details,
            ),
        )

        audit_id = cursor.lastrowid

        conn.commit()

        return audit_id

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


# ============================================================
# GET AUDIT LOGS
# ============================================================

def get_audit_logs(
    limit=500,
):
    """
    Return recent audit events.

    Results are ordered newest first.
    """

    conn = get_connection()

    try:

        cursor = conn.cursor()

        safe_limit = max(
            1,
            min(
                int(limit),
                5000,
            ),
        )

        cursor.execute(
            """
            SELECT *
            FROM audit_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                safe_limit,
            ),
        )

        return cursor.fetchall()

    finally:

        conn.close()


# ============================================================
# AUDIT STATISTICS
# ============================================================

def get_audit_statistics():
    """
    Return aggregate security/audit statistics.
    """

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT

                COUNT(*) AS total_events,

                COALESCE(
                    SUM(
                        CASE
                            WHEN status = 'FAILED'
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS failed_events,

                COALESCE(
                    SUM(
                        CASE
                            WHEN event_type = 'AUTHENTICATION'
                            AND action = 'LOGIN'
                            AND status = 'SUCCESS'
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS successful_logins,

                COALESCE(
                    SUM(
                        CASE
                            WHEN event_type = 'AUTHENTICATION'
                            AND action = 'LOGIN'
                            AND status = 'FAILED'
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS failed_logins,

                COALESCE(
                    SUM(
                        CASE
                            WHEN event_type = 'API_SECURITY'
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS api_security_events,

                COALESCE(
                    SUM(
                        CASE
                            WHEN event_type = 'PREDICTION'
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS prediction_events

            FROM audit_logs
            """
        )

        row = cursor.fetchone()

        return {
            "total_events":
                int(
                    row[
                        "total_events"
                    ] or 0
                ),

            "failed_events":
                int(
                    row[
                        "failed_events"
                    ] or 0
                ),

            "successful_logins":
                int(
                    row[
                        "successful_logins"
                    ] or 0
                ),

            "failed_logins":
                int(
                    row[
                        "failed_logins"
                    ] or 0
                ),

            "api_security_events":
                int(
                    row[
                        "api_security_events"
                    ] or 0
                ),

            "prediction_events":
                int(
                    row[
                        "prediction_events"
                    ] or 0
                ),
        }

    finally:

        conn.close()


# ============================================================
# CREATE REGISTERED USER
# ============================================================

def create_user(
    username,
    email,
    password_hash,
    role="user",
):
    """
    Create a persistent application user.

    Public registration is always forced to role='user'.
    """

    username = str(
        username
    ).strip().lower()

    email = str(
        email
    ).strip().lower()

    if not username:

        raise ValueError(
            "Username cannot be empty."
        )

    if not email:

        raise ValueError(
            "Email cannot be empty."
        )

    if not password_hash:

        raise ValueError(
            "Password hash cannot be empty."
        )

    # Never allow public registration to create
    # admin or analyst accounts.
    role = "user"

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO users (

                username,
                email,
                password_hash,
                role

            )

            VALUES (?, ?, ?, ?)
            """,
            (
                username,
                email,
                password_hash,
                role,
            ),
        )

        user_id = cursor.lastrowid

        conn.commit()

        return user_id

    except sqlite3.IntegrityError as exc:

        conn.rollback()

        message = str(
            exc
        ).lower()

        if "username" in message:

            raise ValueError(
                "Username already exists."
            ) from exc

        if "email" in message:

            raise ValueError(
                "Email already exists."
            ) from exc

        raise

    finally:

        conn.close()


# ============================================================
# GET REGISTERED USER BY USERNAME
# ============================================================

def get_user_by_username(
    username,
):
    """
    Return a registered database user by username.
    """

    username = str(
        username
    ).strip().lower()

    if not username:

        return None

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT

                id,
                username,
                email,
                password_hash,
                role,
                created_at,
                is_active

            FROM users

            WHERE LOWER(username) = ?

            LIMIT 1
            """,
            (
                username,
            ),
        )

        return cursor.fetchone()

    finally:

        conn.close()


# ============================================================
# GET REGISTERED USER BY EMAIL
# ============================================================

def get_user_by_email(
    email,
):
    """
    Return a registered database user by email.
    """

    email = str(
        email
    ).strip().lower()

    if not email:

        return None

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT

                id,
                username,
                email,
                password_hash,
                role,
                created_at,
                is_active

            FROM users

            WHERE LOWER(email) = ?

            LIMIT 1
            """,
            (
                email,
            ),
        )

        return cursor.fetchone()

    finally:

        conn.close()


# ============================================================
# CHECK USERNAME OR EMAIL
# ============================================================

def user_exists(
    username=None,
    email=None,
):
    """
    Check whether a username or email already exists
    in the registered-users table.
    """

    conn = get_connection()

    try:

        cursor = conn.cursor()

        if username:

            username = str(
                username
            ).strip().lower()

            cursor.execute(
                """
                SELECT 1
                FROM users
                WHERE LOWER(username) = ?
                LIMIT 1
                """,
                (
                    username,
                ),
            )

            if cursor.fetchone():

                return True

        if email:

            email = str(
                email
            ).strip().lower()

            cursor.execute(
                """
                SELECT 1
                FROM users
                WHERE LOWER(email) = ?
                LIMIT 1
                """,
                (
                    email,
                ),
            )

            if cursor.fetchone():

                return True

        return False

    finally:

        conn.close()