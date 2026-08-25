# ============================================================
# FraudGuard AI
# Transaction Database + Enterprise Audit Logging
# database.py
# Version 3.5.0
# ============================================================

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

    database_path = Path(DATABASE_PATH)

    database_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    return database_path


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    """
    Create and return a SQLite database connection.

    Uses the configured database path and ensures that the
    database directory exists before connecting.
    """

    database_path = get_database_path()

    conn = sqlite3.connect(
        str(database_path),
        timeout=30
    )

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# DATABASE INITIALIZATION / MIGRATION
# ============================================================

def create_database():
    """
    Create all required FraudGuard AI database tables.

    Also performs safe migrations for existing databases by
    adding missing columns when necessary.
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

                status TEXT

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

            "status": "TEXT"

        }

        for column, data_type in required_transaction_columns.items():

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

            "details": "TEXT"

        }

        for column, data_type in required_audit_columns.items():

            if column not in existing_audit_columns:

                cursor.execute(
                    f"""
                    ALTER TABLE audit_logs
                    ADD COLUMN {column} {data_type}
                    """
                )

        # ====================================================
        # INDEXES
        # ====================================================
        #
        # Indexes improve dashboard and audit-log searches.
        # IF NOT EXISTS makes this safe for existing databases.
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

        conn.commit()

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


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

    username=None

):
    """
    Save a fraud-analysis transaction.

    Returns:
        int: Newly created transaction ID.
    """

    conn = get_connection()

    try:

        cursor = conn.cursor()

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
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

                status

            )

            VALUES (

                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?

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

                status

            )
        )

        transaction_id = cursor.lastrowid

        conn.commit()

        return transaction_id

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
    Return all transactions ordered from newest to oldest.
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
    Return aggregate statistics for the fraud monitoring
    dashboard.
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
            row["total_transactions"] or 0
        )

        fraud_transactions = int(
            row["fraud_transactions"] or 0
        )

        high_risk_transactions = int(
            row["high_risk_transactions"] or 0
        )

        total_amount = float(
            row["total_amount"] or 0.0
        )

        average_probability = float(
            row["average_probability"] or 0.0
        )

        if total_transactions > 0:

            fraud_rate = (
                fraud_transactions
                /
                total_transactions
            )

        else:

            fraud_rate = 0.0

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
                average_probability

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

    details=None

):
    """
    Save an enterprise audit/security event.

    Parameters:
        username:
            User associated with the event.

        event_type:
            Category of event, for example:
            AUTHENTICATION, PREDICTION, API_SECURITY,
            DATABASE, SYSTEM.

        action:
            Specific action such as:
            LOGIN, LOGOUT, FRAUD_ANALYSIS,
            INVALID_API_KEY, DATABASE_ERROR.

        status:
            Event result, for example:
            SUCCESS, FAILED, WARNING.

        ip_address:
            Optional client IP address.

        details:
            Optional safe descriptive information.

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

            VALUES (

                ?, ?, ?, ?, ?, ?, ?

            )
            """,

            (

                timestamp,

                username,

                event_type,

                action,

                status,

                ip_address,

                details

            )
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
    limit=500
):
    """
    Return recent audit events.

    Results are ordered from newest to oldest.
    """

    conn = get_connection()

    try:

        cursor = conn.cursor()

        safe_limit = max(
            1,
            min(
                int(limit),
                5000
            )
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
            )
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
                    row["total_events"] or 0
                ),

            "failed_events":
                int(
                    row["failed_events"] or 0
                ),

            "successful_logins":
                int(
                    row["successful_logins"] or 0
                ),

            "failed_logins":
                int(
                    row["failed_logins"] or 0
                ),

            "api_security_events":
                int(
                    row["api_security_events"] or 0
                ),

            "prediction_events":
                int(
                    row["prediction_events"] or 0
                )

        }

    finally:

        conn.close()