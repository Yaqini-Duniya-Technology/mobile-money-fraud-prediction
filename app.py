# ============================================================
# FraudGuard AI Enterprise Platform
# app.py
# Streamlit + FastAPI Integration
# Version 3.5.0
# ============================================================

import pandas as pd
import streamlit as st

from api_client import predict_transaction
from alert_system import generate_alert, classify_risk, get_transaction_status
from database import (
    create_database,
    save_transaction,
    get_all_transactions,
    save_audit_log,
    get_audit_logs,
    get_audit_statistics,
)
from chatbot import fraud_assistant
from core.users import (
    authenticate_user,
    register_user,
    has_permission,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="FraudGuard AI Enterprise",
    page_icon="🛡️",
    layout="wide",
)


TRANSACTION_TYPE_MAPPING = {
    "CASH_IN": 0,
    "CASH_OUT": 1,
    "DEBIT": 2,
    "PAYMENT": 3,
    "TRANSFER": 4,
}


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

try:
    create_database()
except Exception as exc:
    st.error("❌ Unable to initialize FraudGuard database.")
    st.exception(exc)
    st.stop()


# ============================================================
# HELPERS
# ============================================================

def audit_event(username, event_type, action, status, details=None):
    """Write an audit event without interrupting the application."""
    try:
        save_audit_log(
            username=username,
            event_type=event_type,
            action=action,
            status=status,
            details=details,
        )
    except Exception:
        pass


def load_transaction_dataframe():
    """Load SQLite rows into one consistent dashboard DataFrame."""
    try:
        transactions = get_all_transactions()
    except Exception as exc:
        st.error("❌ Unable to load transaction history.")
        st.exception(exc)
        return pd.DataFrame()

    if not transactions:
        return pd.DataFrame()

    rows = [dict(row) if hasattr(row, "keys") else row for row in transactions]
    data = pd.DataFrame(rows)

    if data.empty:
        return data

    data = data.loc[:, ~data.columns.duplicated(keep="first")].copy()

    aliases = {
        "oldbalanceOrg": "oldbalance_org",
        "newbalanceOrig": "newbalance_orig",
        "oldbalanceDest": "oldbalance_dest",
        "newbalanceDest": "newbalance_dest",
        "isFlaggedFraud": "is_flagged_fraud",
        "transactionType": "transaction_type",
        "riskLevel": "risk_level",
        "fraud_probability": "probability",
    }

    rename_map = {
        old: new
        for old, new in aliases.items()
        if old in data.columns and new not in data.columns
    }

    if rename_map:
        data = data.rename(columns=rename_map)

    data = data.loc[:, ~data.columns.duplicated(keep="first")].copy()

    required = {
        "id": 0,
        "timestamp": "",
        "username": "Unknown",
        "step": 0,
        "transaction_type": "Unknown",
        "amount": 0.0,
        "oldbalance_org": 0.0,
        "newbalance_orig": 0.0,
        "oldbalance_dest": 0.0,
        "newbalance_dest": 0.0,
        "is_flagged_fraud": 0,
        "prediction": 0,
        "probability": 0.0,
        "risk_level": "Low",
        "status": "UNKNOWN",
    }

    for column, default in required.items():
        if column not in data.columns:
            data[column] = default

    numeric_columns = [
        "id", "step", "amount", "oldbalance_org", "newbalance_orig",
        "oldbalance_dest", "newbalance_dest", "is_flagged_fraud",
        "prediction", "probability",
    ]

    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data["id"] = data["id"].fillna(0).astype(int)
    data["step"] = data["step"].fillna(0).astype(int)
    data["amount"] = data["amount"].fillna(0.0).astype(float)
    data["oldbalance_org"] = data["oldbalance_org"].fillna(0.0).astype(float)
    data["newbalance_orig"] = data["newbalance_orig"].fillna(0.0).astype(float)
    data["oldbalance_dest"] = data["oldbalance_dest"].fillna(0.0).astype(float)
    data["newbalance_dest"] = data["newbalance_dest"].fillna(0.0).astype(float)
    data["is_flagged_fraud"] = data["is_flagged_fraud"].fillna(0).astype(int).clip(0, 1)
    data["prediction"] = data["prediction"].fillna(0).astype(int).clip(0, 1)
    data["probability"] = data["probability"].fillna(0.0).astype(float)

    # Handle accidental percentage-style probabilities.
    mask = data["probability"] > 1.0
    data.loc[mask, "probability"] = data.loc[mask, "probability"] / 100.0
    data["probability"] = data["probability"].clip(0.0, 1.0)

    for column in ["timestamp", "username", "transaction_type", "status"]:
        data[column] = data[column].fillna("").astype(str).str.strip()

    data["username"] = data["username"].replace("", "Unknown")
    data["transaction_type"] = data["transaction_type"].replace("", "Unknown").str.upper()
    data["status"] = data["status"].replace("", "UNKNOWN").str.upper()

    data["risk_level"] = data["probability"].apply(classify_risk)
    data["prediction_label"] = data["prediction"].map({0: "Legitimate", 1: "Fraud"})

    return data.sort_values("id", ascending=False, kind="stable").reset_index(drop=True)


def render_transaction_analysis(current_username, role):
    if not has_permission(role, "transaction_analysis"):
        st.error("🚫 You do not have permission to access this section.")
        st.stop()

    st.header("🔍 Analyze Transaction")
    st.write("Enter transaction details below for AI-powered fraud analysis.")
    st.divider()

    amount = st.number_input(
        "Transaction Amount", min_value=0.0, value=10000.0,
        step=1000.0, format="%.2f", key="analysis_amount",
    )

    step = st.number_input(
        "Transaction Step", min_value=1, value=1, step=1,
        key="analysis_step",
    )

    transaction_type = st.selectbox(
        "Transaction Type", list(TRANSACTION_TYPE_MAPPING.keys()),
        key="analysis_transaction_type",
    )

    oldbalance_org = st.number_input(
        "Sender Balance Before Transaction", min_value=0.0, value=50000.0,
        step=1000.0, format="%.2f", key="analysis_oldbalance_org",
    )

    newbalance_orig = st.number_input(
        "Sender Balance After Transaction", min_value=0.0,
        value=max(0.0, oldbalance_org - amount), step=1000.0,
        format="%.2f", key="analysis_newbalance_orig",
    )

    oldbalance_dest = st.number_input(
        "Receiver Balance Before Transaction", min_value=0.0, value=0.0,
        step=1000.0, format="%.2f", key="analysis_oldbalance_dest",
    )

    newbalance_dest = st.number_input(
        "Receiver Balance After Transaction", min_value=0.0,
        value=oldbalance_dest + amount, step=1000.0,
        format="%.2f", key="analysis_newbalance_dest",
    )

    is_flagged_fraud = st.selectbox(
        "Original Fraud Flag", [0, 1],
        format_func=lambda value: "No (0)" if value == 0 else "Yes (1)",
        key="analysis_flagged_fraud",
    )

    st.divider()

    if not st.button("🤖 Run AI Detection", key="run_ai_detection", use_container_width=True):
        return

    if amount <= 0:
        st.error("❌ Transaction amount must be greater than zero.")
        return
    if step < 1:
        st.error("❌ Transaction step must be at least 1.")
        return
    if newbalance_orig < 0:
        st.error("❌ Sender balance cannot be negative.")
        return
    if newbalance_orig > oldbalance_org:
        st.error("❌ Sender's ending balance cannot be greater than the starting balance.")
        return
    if oldbalance_dest < 0 or newbalance_dest < 0:
        st.error("❌ Receiver balance cannot be negative.")
        return
    if newbalance_dest < oldbalance_dest:
        st.error("❌ Receiver's ending balance cannot be lower than the starting balance.")
        return

    payload = {
        "step": int(step),
        "type": str(transaction_type),
        "amount": float(amount),
        "oldbalanceOrg": float(oldbalance_org),
        "newbalanceOrig": float(newbalance_orig),
        "oldbalanceDest": float(oldbalance_dest),
        "newbalanceDest": float(newbalance_dest),
        "isFlaggedFraud": int(is_flagged_fraud),
    }

    with st.spinner("🤖 FraudGuard AI is analyzing the transaction..."):
        try:
            result = predict_transaction(payload)
        except ConnectionError as exc:
            st.error("❌ Unable to connect to FraudGuard AI API.")
            st.warning("Make sure FastAPI is running on http://127.0.0.1:8001")
            st.exception(exc)
            return
        except PermissionError as exc:
            st.error("🔐 FraudGuard API authentication failed.")
            st.exception(exc)
            return
        except ValueError as exc:
            st.error("❌ FraudGuard API rejected the transaction.")
            st.exception(exc)
            return
        except TimeoutError as exc:
            st.error("⏱️ FraudGuard API request timed out.")
            st.exception(exc)
            return
        except Exception as exc:
            st.error("❌ FraudGuard API prediction failed.")
            st.exception(exc)
            return

    try:
        if not isinstance(result, dict):
            raise ValueError("API response is not a JSON object.")
        if "prediction" not in result:
            raise ValueError("API response is missing 'prediction'.")
        if "fraud_probability" not in result:
            raise ValueError("API response is missing 'fraud_probability'.")

        prediction = int(result["prediction"])
        probability = max(0.0, min(1.0, float(result["fraud_probability"])))
        risk_level = classify_risk(probability)
    except Exception as exc:
        st.error("❌ Invalid response received from FraudGuard AI API.")
        st.exception(exc)
        return

    # Audit the successful prediction only after validation succeeds.
    audit_event(
        username=current_username,
        event_type="PREDICTION",
        action="FRAUD_ANALYSIS",
        status="SUCCESS",
        details=(
            f"Prediction={prediction}; "
            f"Probability={probability:.6f}; "
            f"Risk={risk_level}; "
            f"Type={transaction_type}"
        ),
    )

    if prediction == 1:
        audit_event(
            username=current_username,
            event_type="PREDICTION",
            action="FRAUD_DETECTED",
            status="WARNING",
            details=(
                f"High-risk transaction detected; "
                f"Probability={probability:.6f}"
            ),
        )

    try:
        alert = generate_alert(probability)
        if not isinstance(alert, dict):
            alert = {}
    except Exception:
        alert = {
            "status": (
                "HIGH_RISK" if risk_level == "High"
                else "MEDIUM_RISK" if risk_level == "Medium"
                else "LOW_RISK"
            ),
            "risk_level": risk_level,
            "message": "Prediction completed.",
        }
        st.warning("⚠️ Prediction completed, but alert generation failed.")

    try:
        transaction_status = get_transaction_status(prediction)
    except Exception:
        transaction_status = "FRAUD" if prediction == 1 else "LEGITIMATE"

    st.subheader("🤖 AI Result")
    if prediction == 1:
        st.error("🚨 FRAUD DETECTED")
    else:
        st.success("✅ LEGITIMATE TRANSACTION")

    col1, col2, col3 = st.columns(3)
    col1.metric("Fraud Probability", f"{probability * 100:.2f}%")
    col2.metric("Risk Level", risk_level)
    col3.metric("Prediction", "Fraud" if prediction == 1 else "Legitimate")

    if result.get("message"):
        st.info(str(result["message"]))

    alert_message = alert.get("message")
    if alert_message:
        if risk_level == "High":
            st.error(str(alert_message))
        elif risk_level == "Medium":
            st.warning(str(alert_message))
        else:
            st.info(str(alert_message))

    try:
        transaction_id = save_transaction(
            step=int(step),
            transaction_type=str(transaction_type),
            amount=float(amount),
            oldbalance_org=float(oldbalance_org),
            newbalance_orig=float(newbalance_orig),
            oldbalance_dest=float(oldbalance_dest),
            newbalance_dest=float(newbalance_dest),
            is_flagged_fraud=int(is_flagged_fraud),
            prediction=int(prediction),
            probability=float(probability),
            risk_level=str(risk_level),
            status=str(alert.get("status", transaction_status)),
            username=str(current_username),
        )

        st.success(
            "✅ Transaction recorded successfully. "
            f"Transaction ID: {transaction_id}"
        )
        st.caption(f"Transaction ID: **{transaction_id}**")
    except Exception as exc:
        st.warning("⚠️ Prediction completed, but transaction could not be saved.")
        st.exception(exc)


def render_fraud_monitoring(role):
    if not has_permission(role, "fraud_monitoring"):
        st.error("🚫 You do not have permission to access this section.")
        return

    st.header("📊 Fraud Monitoring Dashboard")
    st.write("Enterprise monitoring center for mobile money transaction fraud detection.")

    if st.button("🔄 Refresh Dashboard", key="refresh_monitoring_dashboard"):
        st.rerun()

    st.divider()
    data = load_transaction_dataframe()

    total_transactions = len(data)
    fraud_transactions = int(data["prediction"].sum()) if total_transactions else 0
    high_risk_transactions = int((data["risk_level"] == "High").sum()) if total_transactions else 0
    total_amount = float(data["amount"].sum()) if total_transactions else 0.0
    average_probability = float(data["probability"].mean()) if total_transactions else 0.0
    fraud_rate = fraud_transactions / total_transactions if total_transactions else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Transactions", f"{total_transactions:,}")
    c2.metric("Fraud Cases", f"{fraud_transactions:,}")
    c3.metric("High Risk", f"{high_risk_transactions:,}")
    c4.metric("Fraud Rate", f"{fraud_rate * 100:.2f}%")

    st.divider()
    f1, f2 = st.columns(2)
    f1.metric("Total Transaction Value", f"₦{total_amount:,.2f}")
    f2.metric("Average Fraud Probability", f"{average_probability * 100:.2f}%")
    st.divider()

    st.subheader("🔎 Transaction Search & Filtering")

    if data.empty:
        st.info("📭 No transactions have been analyzed yet.")
        return

    q1, q2, q3, q4 = st.columns(4)
    with q1:
        search_text = st.text_input(
            "🔍 Search",
            placeholder="Username, type, status or transaction ID...",
            key="monitoring_search",
        )
    with q2:
        risk_filter = st.selectbox(
            "Risk Level", ["All", "Low", "Medium", "High"],
            key="monitoring_risk_filter",
        )
    with q3:
        prediction_filter = st.selectbox(
            "Prediction", ["All", "Fraud", "Legitimate"],
            key="monitoring_prediction_filter",
        )
    with q4:
        type_filter = st.selectbox(
            "Transaction Type",
            ["All"] + sorted(data["transaction_type"].unique().tolist()),
            key="monitoring_transaction_type_filter",
        )

    user_filter = st.selectbox(
        "👤 User",
        ["All"] + sorted(data["username"].unique().tolist()),
        key="monitoring_user_filter",
    )

    filtered = data.copy()

    if search_text.strip():
        search_value = search_text.strip().lower()
        mask = pd.Series(False, index=filtered.index)
        for column in ["id", "timestamp", "username", "transaction_type", "status", "risk_level"]:
            mask |= filtered[column].astype(str).str.lower().str.contains(
                search_value, na=False, regex=False
            )
        filtered = filtered[mask]

    if risk_filter != "All":
        filtered = filtered[filtered["risk_level"] == risk_filter]
    if prediction_filter == "Fraud":
        filtered = filtered[filtered["prediction"] == 1]
    elif prediction_filter == "Legitimate":
        filtered = filtered[filtered["prediction"] == 0]
    if type_filter != "All":
        filtered = filtered[filtered["transaction_type"] == type_filter]
    if user_filter != "All":
        filtered = filtered[filtered["username"] == user_filter]

    st.divider()
    st.write(f"Showing **{len(filtered):,}** of **{len(data):,}** transactions.")

    fc1, fc2, fc3, fc4 = st.columns(4)
    fc1.metric("Transactions", f"{len(filtered):,}")
    fc2.metric("Fraud Cases", f"{int(filtered['prediction'].sum()):,}")
    fc3.metric("High Risk", f"{int((filtered['risk_level'] == 'High').sum()):,}")
    fc4.metric("Transaction Value", f"₦{float(filtered['amount'].sum()):,.2f}")

    st.subheader("📋 Transaction Records")

    if filtered.empty:
        st.info("No transaction records match the selected filters.")
    else:
        display = filtered[[
            "id", "timestamp", "username", "step", "transaction_type",
            "amount", "prediction_label", "probability", "risk_level", "status",
        ]].copy()

        display["amount"] = display["amount"].round(2)
        display["probability"] = (display["probability"] * 100).round(2)
        display = display.rename(columns={
            "id": "ID",
            "timestamp": "Timestamp",
            "username": "User",
            "step": "Step",
            "transaction_type": "Type",
            "amount": "Amount",
            "prediction_label": "Prediction",
            "probability": "Fraud Probability (%)",
            "risk_level": "Risk Level",
            "status": "Status",
        })

        st.dataframe(display, use_container_width=True, hide_index=True)
        st.download_button(
            "📥 Download Filtered Transactions",
            data=filtered.to_csv(index=False),
            file_name="fraudguard_transactions.csv",
            mime="text/csv",
            key="download_monitoring_csv",
        )

    st.subheader("📈 Fraud Analytics")

    if filtered.empty:
        st.info("No analytics available for the selected filters.")
    else:
      a1, a2 = st.columns(2)
    with a1:
        st.write("**Risk Distribution**")
        risk_distribution = filtered["risk_level"].value_counts().reindex(
            ["Low", "Medium", "High"], fill_value=0
        )
        st.bar_chart(risk_distribution)

    with a2:
        st.write("**Transaction Type Distribution**")
        st.bar_chart(filtered["transaction_type"].value_counts())

    st.write("**Fraud Probability Distribution**")
    probability_chart = filtered[["id", "probability"]].drop_duplicates("id").set_index("id").sort_index()
    probability_chart["probability"] = probability_chart["probability"] * 100
    st.line_chart(probability_chart)

    st.write("**Fraud Distribution**")
    fraud_distribution = filtered["prediction"].map({0: "Legitimate", 1: "Fraud"}).value_counts().reindex(
        ["Legitimate", "Fraud"], fill_value=0
    )
    st.bar_chart(fraud_distribution)

        # ========================================================
    # AUDIT & SECURITY LOGS
    # ========================================================

    st.divider()

    st.subheader(
        "🔐 Audit & Security Logs"
    )

    try:
        audit_stats = get_audit_statistics()
    except Exception:
        audit_stats = {
            "total_events": 0,
            "failed_events": 0,
            "successful_logins": 0,
            "failed_logins": 0,
            "api_security_events": 0,
            "prediction_events": 0,
        }

    audit_col1, audit_col2, audit_col3, audit_col4 = st.columns(4)

    audit_col1.metric(
        "Total Events",
        f"{audit_stats.get('total_events', 0):,}",
    )

    audit_col2.metric(
        "Successful Logins",
        f"{audit_stats.get('successful_logins', 0):,}",
    )

    audit_col3.metric(
        "Failed Logins",
        f"{audit_stats.get('failed_logins', 0):,}",
    )

    audit_col4.metric(
        "Prediction Events",
        f"{audit_stats.get('prediction_events', 0):,}",
    )

    try:
        audit_logs = get_audit_logs(limit=100)
    except Exception:
        audit_logs = []

    if audit_logs:

        audit_data = pd.DataFrame(
            [
                dict(row)
                if hasattr(row, "keys")
                else row
                for row in audit_logs
            ]
        )

        audit_data = audit_data.loc[
            :,
            ~audit_data.columns.duplicated(
                keep="first"
            ),
        ].copy()

        audit_columns = [
            "id",
            "timestamp",
            "username",
            "event_type",
            "action",
            "status",
            "ip_address",
            "details",
        ]

        audit_data = audit_data[
            [
                column
                for column in audit_columns
                if column in audit_data.columns
            ]
        ].rename(
            columns={
                "id": "ID",
                "timestamp": "Timestamp",
                "username": "User",
                "event_type": "Event Type",
                "action": "Action",
                "status": "Status",
                "ip_address": "IP Address",
                "details": "Details",
            }
        )

        st.dataframe(
            audit_data,
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.info(
            "📭 No audit events have been recorded yet."
        )
        

def render_ai_assistant(role):
    if not has_permission(role, "ai_assistant"):
        st.error("🚫 You do not have permission to access this section.")
        return

    st.header("🤖 FraudGuard AI Assistant")
    st.write("Ask questions about fraud detection, risk levels and suspicious transactions.")
    st.divider()

    question = st.text_input(
        "Ask a fraud-related question",
        placeholder="e.g. Why was this transaction flagged?",
        key="assistant_question",
    )

    if st.button("Ask AI", key="assistant_button", use_container_width=True):
        if not question.strip():
            st.warning("Please enter a question first.")
            return
        try:
            st.write(fraud_assistant(question))
        except Exception as exc:
            st.error("❌ AI Assistant encountered an error.")
            st.exception(exc)


# ============================================================
# SESSION / NAVIGATION
# ============================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None


# ============================================================
# LOGIN / REGISTRATION
# ============================================================

if not st.session_state.logged_in:

    st.title(
        "🔐 FraudGuard AI"
    )

    st.write(
        "Secure access to the FraudGuard AI platform."
    )

    st.divider()

    auth_mode = st.radio(
        "Choose an option",
        [
            "Login",
            "Create Account",
        ],
        horizontal=True,
        key="auth_mode",
    )

    # ========================================================
    # LOGIN
    # ========================================================

    if auth_mode == "Login":

        username = st.text_input(
            "Username",
            key="login_username",
            placeholder="Enter username",
        )

        password = st.text_input(
            "Password",
            key="login_password",
            type="password",
            placeholder="Enter password",
        )

        if st.button(
            "🔑 Login",
            key="login_button",
            use_container_width=True,
        ):

            clean_username = (
                username
                .strip()
                .lower()
            )

            if (
                not clean_username
                or not password
            ):

                st.warning(
                    "Please enter both username and password."
                )

            else:

                try:

                    user = authenticate_user(
                        clean_username,
                        password,
                    )

                    if user is not None:

                        st.session_state.logged_in = True

                        st.session_state.username = (
                            user["username"]
                        )

                        st.session_state.role = (
                            user["role"]
                        )

                        audit_event(
                            user["username"],
                            "AUTHENTICATION",
                            "LOGIN",
                            "SUCCESS",
                            "User logged into FraudGuard AI",
                        )

                        st.success(
                            "✅ Login successful!"
                        )

                        st.rerun()

                    else:

                        st.error(
                            "❌ Invalid username or password."
                        )

                        audit_event(
                            clean_username,
                            "AUTHENTICATION",
                            "LOGIN",
                            "FAILED",
                            "Invalid username or password",
                        )

                except Exception as exc:

                    st.error(
                        "❌ Authentication system error."
                    )

                    st.exception(exc)

    # ========================================================
    # CREATE ACCOUNT
    # ========================================================

    else:

        st.subheader(
            "📝 Create Your FraudGuard AI Account"
        )

        st.caption(
            "New public accounts are created with standard User access."
        )

        new_username = st.text_input(
            "Username",
            key="register_username",
            placeholder="Choose a username",
        )

        new_email = st.text_input(
            "Email",
            key="register_email",
            placeholder="you@example.com",
        )

        new_password = st.text_input(
            "Password",
            key="register_password",
            type="password",
            placeholder="At least 8 characters",
        )

        confirm_password = st.text_input(
            "Confirm Password",
            key="register_confirm_password",
            type="password",
            placeholder="Re-enter your password",
        )

        if st.button(
            "📝 Create Account",
            key="register_button",
            use_container_width=True,
        ):

            clean_username = (
                new_username
                .strip()
                .lower()
            )

            clean_email = (
                new_email
                .strip()
                .lower()
            )

            if not clean_username:

                st.warning(
                    "Please enter a username."
                )

            elif not clean_email:

                st.warning(
                    "Please enter your email."
                )

            elif not new_password:

                st.warning(
                    "Please create a password."
                )

            elif new_password != confirm_password:

                st.error(
                    "❌ Passwords do not match."
                )

            else:

                try:

                    registered_user = register_user(
                        username=clean_username,
                        email=clean_email,
                        password=new_password,
                    )

                    audit_event(
                        registered_user["username"],
                        "AUTHENTICATION",
                        "REGISTRATION",
                        "SUCCESS",
                        "New user account created",
                    )

                    st.success(
                        "✅ Account created successfully!"
                    )

                    st.info(
                        "You can now switch to Login and sign in."
                    )

                except ValueError as exc:

                    st.error(
                        f"❌ {exc}"
                    )

                except Exception as exc:

                    st.error(
                        "❌ Unable to create your account."
                    )

                    st.exception(exc)

    st.stop()


current_username = st.session_state.username
role = st.session_state.role

st.title("🛡️ FraudGuard AI Enterprise")
st.write(
    f"Welcome **{current_username}** 👋\n\n"
    f"Role: **{str(role).title()}**\n\n"
    "AI Powered Mobile Money Fraud Monitoring Platform"
)

st.sidebar.title("Navigation")
st.sidebar.divider()
st.sidebar.write(f"👤 User: **{current_username}**")
st.sidebar.write(f"🔐 Role: **{str(role).title()}**")

available_pages = []
if has_permission(role, "transaction_analysis"):
    available_pages.append("Transaction Analysis")
if has_permission(role, "fraud_monitoring"):
    available_pages.append("Fraud Monitoring")
if has_permission(role, "ai_assistant"):
    available_pages.append("AI Assistant")

if not available_pages:
    st.error("🚫 No pages are available for this account.")
    st.stop()

menu = st.sidebar.radio("Navigation", available_pages, key="main_navigation")
st.sidebar.divider()

if st.sidebar.button("🚪 Logout", key="logout_button", use_container_width=True):
    audit_event(
        current_username,
        "AUTHENTICATION",
        "LOGOUT",
        "SUCCESS",
        "User logged out of FraudGuard AI",
    )
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.rerun()


# ============================================================
# PAGE ROUTER
# ============================================================

if menu == "Transaction Analysis":
    render_transaction_analysis(current_username, role)
elif menu == "Fraud Monitoring":
    render_fraud_monitoring(role)
elif menu == "AI Assistant":
    render_ai_assistant(role)
