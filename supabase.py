import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="ProAudit AI", layout="wide")

SUPABASE_URL = "YOUR_SUPABASE_URL"
SUPABASE_KEY = "YOUR_SUPABASE_ANON_KEY"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# 🔥 AUTH SESSION FIX (CRITICAL)
# =========================
def set_auth():
    session = supabase.auth.get_session()
    if session:
        supabase.postgrest.auth(session.access_token)
        return supabase.auth.get_user().user
    return None

# =========================
# UI STYLE
# =========================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #0b1220, #111827);
    color: white;
}
.block-container {
    padding: 2rem;
}
button {
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)

# =========================
# AUTH SCREEN
# =========================
if "user" not in st.session_state:

    st.title("🧠 ProAudit AI")
    st.subheader("Enterprise Audit Intelligence Platform")

    tab1, tab2 = st.tabs(["Login", "Signup"])

    # LOGIN
    with tab1:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if res.user:
                st.session_state["user"] = res.user

                # 🔥 FIX AUTH CONTEXT
                set_auth()

                st.success("Logged in successfully")
                st.rerun()
            else:
                st.error("Invalid login")

    # SIGNUP
    with tab2:
        email = st.text_input("Signup Email")
        password = st.text_input("Signup Password", type="password")

        if st.button("Create Account"):
            supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            st.success("Account created. Check email.")

    st.stop()

# =========================
# AUTH ACTIVE
# =========================
user = set_auth()

if not user:
    st.warning("Session expired. Please login again.")
    st.session_state.clear()
    st.rerun()

# =========================
# SIDEBAR
# =========================
st.sidebar.title("🧠 ProAudit AI")
st.sidebar.write(user.email)

if st.sidebar.button("Logout"):
    supabase.auth.sign_out()
    st.session_state.clear()
    st.rerun()

# =========================
# CLIENT WORKSPACE
# =========================
st.sidebar.subheader("🏢 Workspace")

clients_res = supabase.table("clients").select("*").execute()
clients = clients_res.data if clients_res.data else []

client_names = [c["client_name"] for c in clients]

selected_client = st.sidebar.selectbox("Select Client", client_names if client_names else ["No Clients"])

# Create client
new_client = st.sidebar.text_input("New Client Name")

if st.sidebar.button("Create Client"):
    if new_client.strip() == "":
        st.warning("Enter client name")
    else:
        supabase.table("clients").insert({
            "user_id": user.id,
            "client_name": new_client
        }).execute()

        st.success("Client created")
        st.rerun()

# Get selected client_id
client_id = None
for c in clients:
    if c["client_name"] == selected_client:
        client_id = c["id"]

# =========================
# MAIN DASHBOARD
# =========================
st.title("📊 Dashboard")

uploaded_file = st.file_uploader("Upload CSV")

if uploaded_file:

    df = pd.read_csv(uploaded_file)

    st.success("File uploaded successfully")

    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    selected_cols = st.multiselect("Select Metrics", numeric_cols)

    if selected_cols:

        # =========================
        # KPI CARDS
        # =========================
        col1, col2, col3 = st.columns(3)

        col1.metric("Records", len(df))
        col2.metric("Metrics", len(selected_cols))
        col3.metric("Risk", "High")

        # =========================
        # CHART
        # =========================
        st.subheader("📈 Trend Analysis")

        fig = px.line(df, y=selected_cols)
        st.plotly_chart(fig, use_container_width=True)

        # =========================
        # SAVE AUDIT RUN
        # =========================
        if st.button("Save Audit Run"):

            supabase.table("audit_runs").insert({
                "user_id": user.id,
                "client_id": client_id,
                "file_name": uploaded_file.name,
                "selected_metrics": ", ".join(selected_cols),
                "anomaly_count": 10,
                "risk_label": "High"
            }).execute()

            st.success("Audit saved")

# =========================
# RECENT ACTIVITY
# =========================
st.subheader("🕒 Recent Activity")

runs_res = supabase.table("audit_runs").select("*").execute()
runs = runs_res.data if runs_res.data else []

if runs:
    for r in runs:
        st.write(f"{r['file_name']} → {r['risk_label']} risk")
else:
    st.info("No activity yet")