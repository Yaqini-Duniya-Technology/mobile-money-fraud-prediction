# ============================================================
# FraudGuard AI Enterprise Platform
# app.py
# Streamlit + FastAPI Integration
# Version 3.0.0
# ============================================================

import pandas as pd
import streamlit as st

from api_client import predict_transaction

from alert_system import (
    generate_alert,
    classify_risk,
    get_transaction_status
)

from database import (
    create_database,
    save_transaction,
    get_all_transactions,
    get_database_statistics
)

from chatbot import fraud_assistant

from core.users import (
    authenticate_user,
    has_permission
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="FraudGuard AI Enterprise",
    page_icon="🛡️",
    layout="wide"
)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

try:

    create_database()

except Exception as e:

    st.error(
        "❌ Unable to initialize FraudGuard database."
    )

    st.exception(e)

    st.stop()


# ============================================================
# TRANSACTION TYPE MAPPING
# ============================================================
#
# MUST MATCH THE LABEL ENCODER USED DURING TRAINING
#
# CASH_IN   -> 0
# CASH_OUT  -> 1
# DEBIT     -> 2
# PAYMENT   -> 3
# TRANSFER  -> 4
#
# FastAPI receives the transaction type as text.
# The API/client/model pipeline handles the encoding.
# ============================================================

TRANSACTION_TYPE_MAPPING = {

    "CASH_IN": 0,

    "CASH_OUT": 1,

    "DEBIT": 2,

    "PAYMENT": 3,

    "TRANSFER": 4

}


# ============================================================
# SESSION STATE
# ============================================================

if "logged_in" not in st.session_state:

    st.session_state.logged_in = False


if "username" not in st.session_state:

    st.session_state.username = None


if "role" not in st.session_state:

    st.session_state.role = None


# ============================================================
# LOGIN PAGE
# ============================================================

if not st.session_state.logged_in:

    st.title(
        "🔐 FraudGuard AI Login"
    )

    st.write(
        "Secure access to the FraudGuard AI platform."
    )

    st.divider()


    username = st.text_input(

        "Username",

        key="login_username",

        placeholder="Enter username"

    )


    password = st.text_input(

        "Password",

        key="login_password",

        type="password",

        placeholder="Enter password"

    )


    if st.button(

        "🔑 Login",

        key="login_button",

        use_container_width=True

    ):

        clean_username = (
            username.strip()
        )


        if (
            clean_username == ""
            or password == ""
        ):

            st.warning(
                "Please enter both username and password."
            )

        else:

            try:

                user = authenticate_user(

                    clean_username,

                    password

                )


                if user is not None:

                    st.session_state.logged_in = True

                    st.session_state.username = (
                        user["username"]
                    )

                    st.session_state.role = (
                        user["role"]
                    )


                    st.success(
                        "✅ Login successful!"
                    )

                    st.rerun()


                else:

                    st.error(
                        "❌ Invalid username or password."
                    )


            except Exception as e:

                st.error(
                    "❌ Authentication system error."
                )

                st.exception(e)


    st.stop()


# ============================================================
# MAIN APPLICATION HEADER
# ============================================================

current_username = (
    st.session_state.username
)

current_role = (
    st.session_state.role
)


st.title(
    "🛡️ FraudGuard AI Enterprise"
)


st.write(
    f"""
Welcome **{current_username}** 👋

Role: **{str(current_role).title()}**

AI Powered Mobile Money Fraud Monitoring Platform
"""
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "Navigation"
)

st.sidebar.divider()


st.sidebar.write(
    f"👤 User: **{current_username}**"
)


st.sidebar.write(
    f"🔐 Role: **{str(current_role).title()}**"
)


role = current_role


# ============================================================
# ROLE-BASED NAVIGATION
# ============================================================

available_pages = []


if has_permission(

    role,

    "transaction_analysis"

):

    available_pages.append(
        "Transaction Analysis"
    )


if has_permission(

    role,

    "fraud_monitoring"

):

    available_pages.append(
        "Fraud Monitoring"
    )


if has_permission(

    role,

    "ai_assistant"

):

    available_pages.append(
        "AI Assistant"
    )


if not available_pages:

    st.error(
        "🚫 No pages are available for this account."
    )

    st.stop()


menu = st.sidebar.radio(

    "Navigation",

    available_pages,

    key="main_navigation"

)


st.sidebar.divider()


# ============================================================
# LOGOUT
# ============================================================

if st.sidebar.button(

    "🚪 Logout",

    key="logout_button",

    use_container_width=True

):

    st.session_state.logged_in = False

    st.session_state.username = None

    st.session_state.role = None

    st.rerun()


# ============================================================
# TRANSACTION ANALYSIS
# ============================================================

if menu == "Transaction Analysis":

    # --------------------------------------------------------
    # PERMISSION
    # --------------------------------------------------------

    if not has_permission(

        role,

        "transaction_analysis"

    ):

        st.error(
            "🚫 You do not have permission "
            "to access this section."
        )

        st.stop()


    # ========================================================
    # HEADER
    # ========================================================

    st.header(
        "🔍 Analyze Transaction"
    )


    st.write(
        "Enter transaction details below "
        "for AI-powered fraud analysis."
    )


    st.divider()


    # ========================================================
    # TRANSACTION AMOUNT
    # ========================================================

    amount = st.number_input(

        "Transaction Amount",

        min_value=0.0,

        value=10000.0,

        step=1000.0,

        format="%.2f",

        key="analysis_amount"

    )


    # ========================================================
    # TRANSACTION STEP
    # ========================================================

    step = st.number_input(

        "Transaction Step",

        min_value=1,

        value=1,

        step=1,

        key="analysis_step"

    )


    # ========================================================
    # TRANSACTION TYPE
    # ========================================================

    transaction_type = st.selectbox(

        "Transaction Type",

        list(
            TRANSACTION_TYPE_MAPPING.keys()
        ),

        key="analysis_transaction_type"

    )


    # ========================================================
    # SENDER BALANCE
    # ========================================================

    oldbalance_org = st.number_input(

        "Sender Balance Before Transaction",

        min_value=0.0,

        value=50000.0,

        step=1000.0,

        format="%.2f",

        key="analysis_oldbalance_org"

    )


    newbalance_orig = st.number_input(

        "Sender Balance After Transaction",

        min_value=0.0,

        value=max(

            0.0,

            oldbalance_org - amount

        ),

        step=1000.0,

        format="%.2f",

        key="analysis_newbalance_orig"

    )


    # ========================================================
    # RECEIVER BALANCE
    # ========================================================

    oldbalance_dest = st.number_input(

        "Receiver Balance Before Transaction",

        min_value=0.0,

        value=0.0,

        step=1000.0,

        format="%.2f",

        key="analysis_oldbalance_dest"

    )


    newbalance_dest = st.number_input(

        "Receiver Balance After Transaction",

        min_value=0.0,

        value=oldbalance_dest + amount,

        step=1000.0,

        format="%.2f",

        key="analysis_newbalance_dest"

    )


    # ========================================================
    # ORIGINAL FRAUD FLAG
    # ========================================================

    is_flagged_fraud = st.selectbox(

        "Original Fraud Flag",

        [0, 1],

        format_func=lambda x:

            "No (0)"
            if x == 0
            else "Yes (1)",

        key="analysis_flagged_fraud"

    )


    st.divider()


    # ========================================================
    # RUN AI DETECTION
    # ========================================================

    if st.button(

        "🤖 Run AI Detection",

        key="run_ai_detection",

        use_container_width=True

    ):

        # ====================================================
        # INPUT VALIDATION
        # ====================================================

        if amount <= 0:

            st.error(
                "❌ Transaction amount must be greater than zero."
            )

            st.stop()


        if step < 1:

            st.error(
                "❌ Transaction step must be at least 1."
            )

            st.stop()


        if newbalance_orig < 0:

            st.error(
                "❌ Sender balance cannot be negative."
            )

            st.stop()


        if newbalance_orig > oldbalance_org:

            st.error(
                "❌ Sender's ending balance cannot "
                "be greater than the starting balance."
            )

            st.stop()


        if oldbalance_dest < 0:

            st.error(
                "❌ Receiver balance cannot be negative."
            )

            st.stop()


        if newbalance_dest < 0:

            st.error(
                "❌ Receiver balance cannot be negative."
            )

            st.stop()


        if newbalance_dest < oldbalance_dest:

            st.error(
                "❌ Receiver's ending balance cannot "
                "be lower than the starting balance."
            )

            st.stop()


        # ====================================================
        # FASTAPI PAYLOAD
        # ====================================================
        #
        # IMPORTANT:
        #
        # API expects:
        #
        # type
        #
        # NOT:
        #
        # transaction_type
        # ====================================================

        transaction_data = {

            "step": int(
                step
            ),

            "type": str(
                transaction_type
            ),

            "amount": float(
                amount
            ),

            "oldbalanceOrg": float(
                oldbalance_org
            ),

            "newbalanceOrig": float(
                newbalance_orig
            ),

            "oldbalanceDest": float(
                oldbalance_dest
            ),

            "newbalanceDest": float(
                newbalance_dest
            ),

            "isFlaggedFraud": int(
                is_flagged_fraud
            )

        }


        # ====================================================
        # CALL FASTAPI
        # ====================================================

        with st.spinner(

            "🤖 FraudGuard AI is analyzing "
            "the transaction..."

        ):

            try:

                result = predict_transaction(

                    transaction_data

                )


            except ConnectionError as e:

                st.error(
                    "❌ Unable to connect to "
                    "FraudGuard AI API."
                )

                st.warning(
                    "Make sure FastAPI is running on "
                    "http://127.0.0.1:8000"
                )

                st.exception(e)

                st.stop()


            except PermissionError as e:

                st.error(
                    "🔐 FraudGuard API authentication failed."
                )

                st.exception(e)

                st.stop()


            except ValueError as e:

                st.error(
                    "❌ FraudGuard API rejected "
                    "the transaction."
                )

                st.exception(e)

                st.stop()


            except TimeoutError as e:

                st.error(
                    "⏱️ FraudGuard API request timed out."
                )

                st.exception(e)

                st.stop()


            except Exception as e:

                st.error(
                    "❌ FraudGuard API prediction failed."
                )

                st.exception(e)

                st.stop()


        # ====================================================
        # VALIDATE API RESPONSE
        # ====================================================

        try:

            if not isinstance(

                result,

                dict

            ):

                raise ValueError(
                    "API response is not a JSON object."
                )


            if "prediction" not in result:

                raise ValueError(
                    "API response is missing 'prediction'."
                )


            if "fraud_probability" not in result:

                raise ValueError(
                    "API response is missing "
                    "'fraud_probability'."
                )


            prediction = int(

                result[
                    "prediction"
                ]

            )


            probability = float(

                result[
                    "fraud_probability"
                ]

            )


            probability = max(

                0.0,

                min(
                    1.0,
                    probability
                )

            )


        except Exception as e:

            st.error(
                "❌ Invalid response received "
                "from FraudGuard AI API."
            )

            st.exception(e)

            st.stop()


        # ====================================================
        # RISK CLASSIFICATION
        # ====================================================

        risk_level = classify_risk(

            probability

        )


        # ====================================================
        # ALERT GENERATION
        # ====================================================

        try:

            alert = generate_alert(

                probability

            )

        except Exception as e:

            alert = {

                "status": (
                    "HIGH_RISK"
                    if risk_level == "High"
                    else
                    "MEDIUM_RISK"
                    if risk_level == "Medium"
                    else
                    "LOW_RISK"
                ),

                "risk_level": risk_level,

                "message":
                    "Prediction completed."

            }


            st.warning(
                "⚠️ Prediction completed, "
                "but alert generation failed."
            )


        # ====================================================
        # TRANSACTION STATUS
        # ====================================================

        try:

            transaction_status = (
                get_transaction_status(
                    prediction
                )
            )

        except Exception:

            transaction_status = (

                "FRAUD"

                if prediction == 1

                else "LEGITIMATE"

            )


        # ====================================================
        # AI RESULT
        # ====================================================

        st.subheader(
            "🤖 AI Result"
        )


        if prediction == 1:

            st.error(
                "🚨 FRAUD DETECTED"
            )

        else:

            st.success(
                "✅ LEGITIMATE TRANSACTION"
            )


        # ====================================================
        # RESULT METRICS
        # ====================================================

        result_col1, result_col2, result_col3 = (
            st.columns(3)
        )


        result_col1.metric(

            "Fraud Probability",

            f"{probability * 100:.2f}%"

        )


        result_col2.metric(

            "Risk Level",

            risk_level

        )


        result_col3.metric(

            "Prediction",

            "Fraud"

            if prediction == 1

            else "Legitimate"

        )


        # ====================================================
        # API MESSAGE
        # ====================================================

        api_message = result.get(

            "message",

            None

        )


        if api_message:

            st.info(
                str(api_message)
            )


        # ====================================================
        # ALERT MESSAGE
        # ====================================================

        alert_message = (

            alert.get(
                "message"
            )

            if isinstance(
                alert,
                dict
            )

            else None

        )


        if alert_message:

            if risk_level == "High":

                st.error(
                    alert_message
                )

            elif risk_level == "Medium":

                st.warning(
                    alert_message
                )

            else:

                st.info(
                    alert_message
                )


        # ====================================================
        # SAVE TRANSACTION
        # ====================================================

        try:

            transaction_id = save_transaction(

                step=int(
                    step
                ),

                transaction_type=str(
                    transaction_type
                ),

                amount=float(
                    amount
                ),

                oldbalance_org=float(
                    oldbalance_org
                ),

                newbalance_orig=float(
                    newbalance_orig
                ),

                oldbalance_dest=float(
                    oldbalance_dest
                ),

                newbalance_dest=float(
                    newbalance_dest
                ),

                is_flagged_fraud=int(
                    is_flagged_fraud
                ),

                prediction=int(
                    prediction
                ),

                probability=float(
                    probability
                ),

                risk_level=str(
                    risk_level
                ),

                status=str(
                    alert.get(
                        "status",
                        transaction_status
                    )
                ),

                username=str(
                    current_username
                )

            )


            st.success(

                "✅ Transaction recorded successfully. "

                f"Transaction ID: {transaction_id}"

            )


            st.caption(

                f"Transaction ID: **{transaction_id}**"

            )


        except Exception as e:

            st.warning(

                "⚠️ Prediction completed, "
                "but transaction could not be saved."

            )

            st.exception(e)


# ============================================================
# FRAUD MONITORING
# ============================================================

elif menu == "Fraud Monitoring":

    # --------------------------------------------------------
    # PERMISSION
    # --------------------------------------------------------

    if not has_permission(

        role,

        "fraud_monitoring"

    ):

        st.error(

            "🚫 You do not have permission "
            "to access this section."

        )

        st.stop()


    # ========================================================
    # HEADER
    # ========================================================

    st.header(

        "📊 Fraud Monitoring Dashboard"

    )


    st.write(

        "Enterprise monitoring center for "
        "mobile money transaction fraud detection."

    )


    # ========================================================
    # REFRESH BUTTON
    # ========================================================

    if st.button(

        "🔄 Refresh Dashboard",

        key="refresh_monitoring_dashboard"

    ):

        st.rerun()


    st.divider()


    # ========================================================
    # DATABASE STATISTICS
    # ========================================================

    try:

        stats = get_database_statistics()


    except Exception as e:

        st.error(

            "❌ Unable to load database statistics."

        )

        st.exception(e)


        stats = {

            "total_transactions": 0,

            "fraud_transactions": 0,

            "high_risk_transactions": 0,

            "fraud_rate": 0.0,

            "total_amount": 0.0,

            "average_probability": 0.0

        }


    # ========================================================
    # KPI ROW
    # ========================================================

    monitor_col1, monitor_col2, monitor_col3, monitor_col4 = (
        st.columns(4)
    )


    monitor_col1.metric(

        "Total Transactions",

        f"{int(stats.get('total_transactions', 0)):,}"

    )


    monitor_col2.metric(

        "Fraud Cases",

        f"{int(stats.get('fraud_transactions', 0)):,}"

    )


    monitor_col3.metric(

        "High Risk",

        f"{int(stats.get('high_risk_transactions', 0)):,}"

    )


    monitor_col4.metric(

        "Fraud Rate",

        f"{float(stats.get('fraud_rate', 0.0)) * 100:.2f}%"

    )


    # ========================================================
    # FINANCIAL KPI
    # ========================================================

    st.divider()


    financial_col1, financial_col2 = (
        st.columns(2)
    )


    financial_col1.metric(

        "Total Transaction Value",

        f"₦{float(stats.get('total_amount', 0.0)):,.2f}"

    )


    financial_col2.metric(

        "Average Fraud Probability",

        f"{float(stats.get('average_probability', 0.0)) * 100:.2f}%"

    )


    st.divider()


    # ========================================================
    # LOAD TRANSACTION HISTORY
    # ========================================================

    try:

        transactions = get_all_transactions()


    except Exception as e:

        st.error(

            "❌ Unable to load transaction history."

        )

        st.exception(e)

        transactions = []


    # ========================================================
    # CREATE DATAFRAME
    # ========================================================

    if transactions:

        data = pd.DataFrame(
            transactions
        )

    else:

        data = pd.DataFrame()


    # ========================================================
    # REMOVE DUPLICATE COLUMNS
    # ========================================================
    #
    # This protects against an old/incorrect DataFrame
    # containing the same column name more than once.
    # ========================================================

    if not data.empty:

        data = data.loc[

            :,

            ~data.columns.duplicated()

        ].copy()


    # ========================================================
    # REQUIRED COLUMNS
    # ========================================================

    required_columns = {

        "id": None,

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

        "status": "UNKNOWN"

    }


    for column, default_value in required_columns.items():

        if column not in data.columns:

            data[column] = default_value


    # ========================================================
    # NORMALIZE COLUMNS
    # ========================================================

    if not data.empty:

        data["amount"] = pd.to_numeric(

            data["amount"],

            errors="coerce"

        ).fillna(0.0)


        data["probability"] = pd.to_numeric(

            data["probability"],

            errors="coerce"

        ).fillna(0.0)


        data["prediction"] = pd.to_numeric(

            data["prediction"],

            errors="coerce"

        ).fillna(0).astype(int)


        data["step"] = pd.to_numeric(

            data["step"],

            errors="coerce"

        ).fillna(0).astype(int)


        data["transaction_type"] = (

            data["transaction_type"]

            .fillna("Unknown")

            .astype(str)

            .str.strip()

        )


        data["username"] = (

            data["username"]

            .fillna("Unknown")

            .astype(str)

            .str.strip()

        )


        data["status"] = (

            data["status"]

            .fillna("UNKNOWN")

            .astype(str)

            .str.strip()

        )


        # ----------------------------------------------------
        # Keep probability valid
        # ----------------------------------------------------

        data["probability"] = (

            data["probability"]

            .clip(
                lower=0.0,
                upper=1.0
            )

        )


        # ----------------------------------------------------
        # Canonical risk level
        # ----------------------------------------------------
        #
        # We deliberately rebuild risk_level from probability.
        # This prevents old/inconsistent database values from
        # breaking the dashboard.
        # ----------------------------------------------------

        data["risk_level"] = (

            data["probability"]

            .apply(
                classify_risk
            )

        )


    # ========================================================
    # TRANSACTION SEARCH & FILTERING
    # ========================================================

    st.subheader(

        "🔎 Transaction Search & Filtering"

    )


    if data.empty:

        st.info(

            "📭 No transactions have been analyzed yet."

        )


    else:

        # ====================================================
        # FILTER ROW
        # ====================================================

        filter_col1, filter_col2, filter_col3, filter_col4 = (
            st.columns(4)
        )


        # ====================================================
        # SEARCH
        # ====================================================

        with filter_col1:

            search_text = st.text_input(

                "🔍 Search",

                placeholder=(

                    "Search by username, "
                    "transaction type, status "
                    "or transaction ID..."

                ),

                key="monitoring_search"

            )


        # ====================================================
        # RISK FILTER
        # ====================================================

        with filter_col2:

            risk_filter = st.selectbox(

                "Risk Level",

                [
                    "All",
                    "Low",
                    "Medium",
                    "High"
                ],

                key="monitoring_risk_filter"

            )


        # ====================================================
        # PREDICTION FILTER
        # ====================================================

        with filter_col3:

            prediction_filter = st.selectbox(

                "Prediction",

                [
                    "All",
                    "Fraud",
                    "Legitimate"
                ],

                key="monitoring_prediction_filter"

            )


        # ====================================================
        # TRANSACTION TYPE FILTER
        # ====================================================

        with filter_col4:

            transaction_type_options = (

                ["All"]

                +

                sorted(

                    data[
                        "transaction_type"
                    ]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()

                )

            )


            transaction_type_filter = st.selectbox(

                "Transaction Type",

                transaction_type_options,

                key="monitoring_transaction_type_filter"

            )


        # ====================================================
        # USER FILTER
        # ====================================================

        user_options = (

            ["All"]

            +

            sorted(

                data[
                    "username"
                ]
                .dropna()
                .astype(str)
                .unique()
                .tolist()

            )

        )


        user_filter = st.selectbox(

            "👤 User",

            user_options,

            key="monitoring_user_filter"

        )


        # ====================================================
        # CREATE FILTERED DATA
        # ====================================================

        filtered_data = data.copy()


        # ====================================================
        # SEARCH FILTER
        # ====================================================

        if search_text.strip():

            search_value = (

                search_text

                .strip()

                .lower()

            )


            searchable_columns = [

                "id",

                "timestamp",

                "username",

                "transaction_type",

                "status",

                "risk_level"

            ]


            search_mask = pd.Series(

                False,

                index=filtered_data.index

            )


            for column in searchable_columns:

                if column in filtered_data.columns:

                    search_mask |= (

                        filtered_data[
                            column
                        ]
                        .astype(str)
                        .str.lower()
                        .str.contains(

                            search_value,

                            na=False,

                            regex=False

                        )

                    )


            filtered_data = filtered_data[
                search_mask
            ]


        # ====================================================
        # RISK FILTER
        # ====================================================

        if risk_filter != "All":

            filtered_data = filtered_data[

                filtered_data[
                    "risk_level"
                ]

                == risk_filter

            ]


        # ====================================================
        # PREDICTION FILTER
        # ====================================================

        if prediction_filter == "Fraud":

            filtered_data = filtered_data[

                filtered_data[
                    "prediction"
                ]

                == 1

            ]


        elif prediction_filter == "Legitimate":

            filtered_data = filtered_data[

                filtered_data[
                    "prediction"
                ]

                == 0

            ]


        # ====================================================
        # TRANSACTION TYPE FILTER
        # ====================================================

        if transaction_type_filter != "All":

            filtered_data = filtered_data[

                filtered_data[
                    "transaction_type"
                ]

                == transaction_type_filter

            ]


        # ====================================================
        # USER FILTER
        # ====================================================

        if user_filter != "All":

            filtered_data = filtered_data[

                filtered_data[
                    "username"
                ]

                == user_filter

            ]


        # ====================================================
        # ADD DISPLAY PREDICTION
        # ====================================================

        filtered_data = filtered_data.copy()


        filtered_data["prediction_label"] = (

            filtered_data[
                "prediction"
            ]

            .apply(

                lambda value:

                    "Fraud"

                    if int(value) == 1

                    else "Legitimate"

            )

        )


        # ====================================================
        # FILTER SUMMARY
        # ====================================================

        st.divider()


        st.write(

            f"Showing **{len(filtered_data):,}** "

            f"of **{len(data):,}** transactions."

        )


        # ====================================================
        # FILTERED KPI
        # ====================================================

        fcol1, fcol2, fcol3, fcol4 = (
            st.columns(4)
        )


        if not filtered_data.empty:

            filtered_fraud = int(

                filtered_data[
                    "prediction"
                ].sum()

            )


            filtered_high_risk = int(

                (

                    filtered_data[
                        "risk_level"
                    ]

                    == "High"

                ).sum()

            )


            filtered_amount = float(

                filtered_data[
                    "amount"
                ].sum()

            )

        else:

            filtered_fraud = 0

            filtered_high_risk = 0

            filtered_amount = 0.0


        fcol1.metric(

            "Transactions",

            f"{len(filtered_data):,}"

        )


        fcol2.metric(

            "Fraud Cases",

            f"{filtered_fraud:,}"

        )


        fcol3.metric(

            "High Risk",

            f"{filtered_high_risk:,}"

        )


        fcol4.metric(

            "Transaction Value",

            f"₦{filtered_amount:,.2f}"

        )


        # ====================================================
        # TRANSACTION RECORDS
        # ====================================================

        st.subheader(

            "📋 Transaction Records"

        )


        if filtered_data.empty:

            st.info(

                "No transaction records match "
                "the selected filters."

            )

        else:

            display_columns = [

                "id",

                "timestamp",

                "username",

                "step",

                "transaction_type",

                "amount",

                "prediction_label",

                "probability",

                "risk_level",

                "status"

            ]


            display_data = filtered_data[

                [

                    column

                    for column in display_columns

                    if column in filtered_data.columns

                ]

            ].copy()


            # ------------------------------------------------
            # Format probability
            # ------------------------------------------------

            display_data["probability"] = (

                display_data[
                    "probability"
                ]

                * 100

            ).round(2)


            # ------------------------------------------------
            # Rename columns
            # ------------------------------------------------

            display_data = display_data.rename(

                columns={

                    "id":
                        "ID",

                    "timestamp":
                        "Timestamp",

                    "username":
                        "User",

                    "step":
                        "Step",

                    "transaction_type":
                        "Type",

                    "amount":
                        "Amount",

                    "prediction_label":
                        "Prediction",

                    "probability":
                        "Fraud Probability (%)",

                    "risk_level":
                        "Risk Level",

                    "status":
                        "Status"

                }

            )


            st.dataframe(

                display_data,

                use_container_width=True,

                hide_index=True

            )


            # =================================================
            # CSV EXPORT
            # =================================================

            csv_data = filtered_data.to_csv(

                index=False

            )


            st.download_button(

                label=(
                    "📥 Download Filtered Transactions"
                ),

                data=csv_data,

                file_name=(
                    "fraudguard_transactions.csv"
                ),

                mime="text/csv",

                key="download_monitoring_csv"

            )


        # ====================================================
        # FRAUD ANALYTICS
        # ====================================================

        st.subheader(

            "📈 Fraud Analytics"

        )


        if filtered_data.empty:

            st.info(

                "No analytics available for "
                "the selected filters."

            )

        else:

            analytics_col1, analytics_col2 = (
                st.columns(2)
            )


            # =================================================
            # RISK DISTRIBUTION
            # =================================================

            with analytics_col1:

                st.write(
                    "**Risk Distribution**"
                )


                risk_distribution = (

                    filtered_data[
                        "risk_level"
                    ]
                    .value_counts()
                    .reindex(

                        [
                            "Low",
                            "Medium",
                            "High"
                        ],

                        fill_value=0

                    )

                )


                st.bar_chart(

                    risk_distribution

                )


            # =================================================
            # TRANSACTION TYPE
            # =================================================

            with analytics_col2:

                st.write(
                    "**Transaction Type Distribution**"
                )


                type_distribution = (

                    filtered_data[
                        "transaction_type"
                    ]
                    .value_counts()

                )


                st.bar_chart(

                    type_distribution

                )


            # =================================================
            # FRAUD PROBABILITY
            # =================================================

            st.write(

                "**Fraud Probability Distribution**"

            )


            probability_chart = (

                filtered_data[
                    [
                        "id",
                        "probability"
                    ]
                ]
                .copy()

            )


            probability_chart["probability"] = (

                probability_chart[
                    "probability"
                ]

                * 100

            )


            probability_chart = (

                probability_chart

                .set_index(
                    "id"
                )

            )


            st.line_chart(

                probability_chart

            )


            # =================================================
            # FRAUD DISTRIBUTION
            # =================================================

            st.write(

                "**Fraud Distribution**"

            )


            fraud_distribution = (

                filtered_data[
                    "prediction"
                ]
                .map({

                    0:
                        "Legitimate",

                    1:
                        "Fraud"

                })
                .value_counts()

            )


            st.bar_chart(

                fraud_distribution

            )


# ============================================================
# AI ASSISTANT
# ============================================================

elif menu == "AI Assistant":

    # --------------------------------------------------------
    # PERMISSION
    # --------------------------------------------------------

    if not has_permission(

        role,

        "ai_assistant"

    ):

        st.error(

            "🚫 You do not have permission "
            "to access this section."

        )

        st.stop()


    # ========================================================
    # HEADER
    # ========================================================

    st.header(

        "🤖 FraudGuard AI Assistant"

    )


    st.write(

        "Ask questions about fraud detection, "
        "risk levels and suspicious transactions."

    )


    st.divider()


    # ========================================================
    # QUESTION
    # ========================================================

    question = st.text_input(

        "Ask a fraud-related question",

        placeholder=(
            "e.g. Why was this transaction flagged?"
        ),

        key="assistant_question"

    )


    # ========================================================
    # ASK BUTTON
    # ========================================================

    if st.button(

        "Ask AI",

        key="assistant_button",

        use_container_width=True

    ):

        try:

            response = fraud_assistant(

                question

            )


            st.write(
                response
            )


        except Exception as e:

            st.error(
                "❌ AI Assistant encountered an error."
            )

            st.exception(e)