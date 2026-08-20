# ============================================================
# FraudGuard AI
# Transaction Database
# ============================================================

import sqlite3
from datetime import datetime

from pathlib import Path

from core.config import DATABASE_PATH


def get_connection():
    database_path = Path(DATABASE_PATH)

    database_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    conn = sqlite3.connect(
        str(database_path)
    )

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():

    conn = sqlite3.connect(
        DATABASE_PATH
    )

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# CREATE / MIGRATE DATABASE
# ============================================================

def create_database():

    conn = get_connection()

    cursor = conn.cursor()

    # --------------------------------------------------------
    # Create transactions table
    # --------------------------------------------------------

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

    conn.commit()


    # ========================================================
    # DATABASE MIGRATION
    # ========================================================

    cursor.execute(
        "PRAGMA table_info(transactions)"
    )

    existing_columns = [

        row["name"]

        for row in cursor.fetchall()

    ]


    required_columns = {

        "timestamp":
            "TEXT",

        "username":
            "TEXT",

        "step":
            "INTEGER",

        "transaction_type":
            "TEXT",

        "amount":
            "REAL",

        "oldbalanceOrg":
            "REAL",

        "newbalanceOrig":
            "REAL",

        "oldbalanceDest":
            "REAL",

        "newbalanceDest":
            "REAL",

        "isFlaggedFraud":
            "INTEGER",

        "prediction":
            "INTEGER",

        "probability":
            "REAL",

        "risk_level":
            "TEXT",

        "status":
            "TEXT"

    }


    # --------------------------------------------------------
    # Add missing columns
    # --------------------------------------------------------

    for column, data_type in required_columns.items():

        if column not in existing_columns:

            cursor.execute(

                f"""
                ALTER TABLE transactions
                ADD COLUMN {column} {data_type}
                """

            )


    conn.commit()

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

    conn = get_connection()

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

    conn.close()


    return transaction_id


# ============================================================
# GET ALL TRANSACTIONS
# ============================================================

def get_all_transactions():

    conn = get_connection()


    cursor = conn.cursor()


    cursor.execute(

        """
        SELECT *

        FROM transactions

        ORDER BY id DESC
        """

    )


    rows = cursor.fetchall()


    conn.close()


    return rows


# ============================================================
# DATABASE STATISTICS
# ============================================================

def get_database_statistics():

    conn = get_connection()

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


    total_transactions = (
        row["total_transactions"]
    )


    fraud_transactions = (
        row["fraud_transactions"]
    )


    if total_transactions > 0:

        fraud_rate = (

            fraud_transactions
            /
            total_transactions

        )

    else:

        fraud_rate = 0.0


    statistics = {

        "total_transactions":
            total_transactions,

        "fraud_transactions":
            fraud_transactions,

        "high_risk_transactions":
            row["high_risk_transactions"],

        "fraud_rate":
            fraud_rate,

        "total_amount":
            row["total_amount"],

        "average_probability":
            row["average_probability"]

    }


    conn.close()


    return statistics