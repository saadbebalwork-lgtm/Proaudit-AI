import io
import os
from datetime import datetime
from typing import List, Dict, Optional

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from openai import OpenAI
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from supabase import Client, create_client

# =========================================
# PAGE CONFIG
# =========================================
st.set_page_config(
    page_title="ProAudit AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================
# SECRETS / CLIENTS
# =========================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", st.secrets.get("OPENAI_API_KEY", ""))
SUPABASE_URL = os.getenv("SUPABASE_URL", st.secrets.get("SUPABASE_URL", ""))
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", st.secrets.get("SUPABASE_ANON_KEY", ""))

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
supabase: Optional[Client] = (
    create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    if SUPABASE_URL and SUPABASE_ANON_KEY
    else None
)

# =========================================
# SESSION STATE
# =========================================
defaults = {
    "logged_in": False,
    "user_email": None,
    "user_id": None,
    "selected_client_id": None,
    "selected_client_name": None,
    "last_ai_text": None,
    "chat_history": [],
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# =========================================
# PREMIUM UI
# =========================================
st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(99,102,241,0.18), transparent 28%),
            radial-gradient(circle at top right, rgba(14,165,233,0.14), transparent 24%),
            linear-gradient(180deg, #081120 0%, #0B1220 45%, #0E1424 100%);
        color: #E5E7EB;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0B1220 0%, #0F172A 100%);
        border-right: 1px solid rgba(148,163,184,0.15);
    }

    .block-container {
        padding-top: 1.1rem;
        padding-bottom: 1.6rem;
        max-width: 1320px;
    }

    .hero-card {
        background: linear-gradient(135deg, rgba(17,24,39,0.88), rgba(15,23,42,0.78));
        border: 1px solid rgba(99,102,241,0.25);
        border-radius: 22px;
        padding: 24px 28px;
        box-shadow: 0 20px 50px rgba(0,0,0,0.28);
        margin-bottom: 0.65rem;
    }

    .section-card {
        background: linear-gradient(180deg, rgba(15,23,42,0.90), rgba(17,24,39,0.88));
        border: 1px solid rgba(148,163,184,0.14);
        border-radius: 18px;
        padding: 16px 16px 10px 16px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.20);
        margin-bottom: 0.55rem;
    }

    .mini-card {
        background: linear-gradient(135deg, rgba(17,24,39,0.92), rgba(30,41,59,0.82));
        border: 1px solid rgba(148,163,184,0.12);
        border-radius: 16px;
        padding: 14px 16px;
        margin-bottom: 0.55rem;
    }

    .insight-card {
        background: linear-gradient(135deg, rgba(30,41,59,0.95), rgba(17,24,39,0.92));
        border: 1px solid rgba(56,189,248,0.20);
        border-left: 4px solid #6366F1;
        border-radius: 16px;
        padding: 18px 20px;
        margin-top: 8px;
        margin-bottom: 8px;
    }

    .status-card {
        background: linear-gradient(135deg, rgba(17,24,39,0.92), rgba(15,23,42,0.92));
        border: 1px solid rgba(34,197,94,0.20);
        border-radius: 16px;
        padding: 14px 16px;
        margin-bottom: 0.6rem;
    }

    .small-muted {
        color: #94A3B8;
        font-size: 0.95rem;
        line-height: 1.55;
    }

    .auth-wrap {
        max-width: 1180px;
        margin: 1rem auto 0 auto;
    }

    .auth-title {
        text-align: center;
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 0.25rem;
    }

    .auth-subtitle {
        text-align: center;
        color: #94A3B8;
        margin-bottom: 1.5rem;
        font-size: 1.05rem;
    }

    .feature-bullet {
        color: #CBD5E1;
        margin-bottom: 0.65rem;
        font-size: 1rem;
    }

    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(17,24,39,0.92), rgba(30,41,59,0.82));
        border: 1px solid rgba(99,102,241,0.22);
        padding: 18px;
        border-radius: 18px;
        box-shadow: 0 10px 24px rgba(0,0,0,0.18);
    }

    div[data-testid="metric-container"] label {
        color: #A5B4FC !important;
    }

    .stButton > button, .stDownloadButton > button {
        border-radius: 12px !important;
        border: none !important;
        background: linear-gradient(90deg, #6366F1, #8B5CF6) !important;
        color: white !important;
        font-weight: 600 !important;
        box-shadow: 0 8px 20px rgba(99,102,241,0.28);
    }

    .stTextInput input, .stTextArea textarea {
        background-color: #1F2937 !important;
        border: 1px solid #374151 !important;
        border-radius: 10px !important;
        color: white !important;
    }

    div[data-testid="stFileUploader"] {
        background: rgba(17,24,39,0.78);
        border: 1px dashed rgba(99,102,241,0.35);
        border-radius: 16px;
        padding: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================
# HELPERS
# =========================================
def safe_date_column(df: pd.DataFrame) -> pd.DataFrame:
    date_cols = [col for col in df.columns if "date" in col.lower()]
    if date_cols:
        parsed = pd.to_datetime(df[date_cols[0]], errors="coerce")
        if parsed.notna().sum() > 0:
            df[date_cols[0]] = parsed
            df = df.rename(columns={date_cols[0]: "Date"})
        else:
            df["Date"] = range(len(df))
    else:
        df["Date"] = range(len(df))
    return df

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[:, ~df.columns.astype(str).str.contains(r"^Unnamed")]

def create_pdf_report(username: str, client_name: str, ai_text: str, selected_metric: str, anomaly_value, anomaly_zscore) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("ProAudit AI - Audit Insight Report", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Generated By: {username}", styles["Normal"]))
    story.append(Paragraph(f"Client: {client_name}", styles["Normal"]))
    story.append(Paragraph(f"Generated At: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Metric: {selected_metric}", styles["Normal"]))
    story.append(Paragraph(f"Anomalous Value: {anomaly_value}", styles["Normal"]))
    story.append(Paragraph(f"Z-Score: {round(float(anomaly_zscore), 2)}", styles["Normal"]))
    story.append(Spacer(1, 14))
    story.append(Paragraph("AI Audit Insight", styles["Heading2"]))
    story.append(Paragraph(ai_text.replace("\n", "<br/>"), styles["BodyText"]))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

def generate_ai_insight(metric_name: str, metric_value, z_score_value) -> str:
    if not openai_client:
        raise ValueError("OPENAI_API_KEY is missing.")

    prompt = f"""
You are a senior audit analytics assistant.

Analyze this anomaly:
Metric: {metric_name}
Value: {metric_value}
Z-score: {z_score_value}

Write a concise professional audit insight with:
1. Why this may be risky
2. What an auditor should check
3. A recommended next step

Use clear business language.
"""
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()

def generate_chat_response(question: str, df_summary: str, anomaly_summary: str) -> str:
    if not openai_client:
        raise ValueError("OPENAI_API_KEY is missing.")

    prompt = f"""
You are ProAudit AI, an audit analytics copilot.

Context:
Dataset summary:
{df_summary}

Anomaly summary:
{anomaly_summary}

User question:
{question}

Answer in concise, professional audit language.
"""
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()

def sign_up_user(email: str, password: str):
    if not supabase:
        raise ValueError("Supabase is not configured.")
    return supabase.auth.sign_up({"email": email, "password": password})

def sign_in_user(email: str, password: str):
    if not supabase:
        raise ValueError("Supabase is not configured.")
    return supabase.auth.sign_in_with_password({"email": email, "password": password})

def sign_out_user():
    if supabase:
        supabase.auth.sign_out()

def get_clients(user_id: str) -> List[Dict]:
    if not supabase or not user_id:
        return []
    try:
        response = (
            supabase.table("clients")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )
        return response.data or []
    except Exception:
        return []

def create_client_record(user_id: str, client_name: str, industry: str) -> bool:
    if not supabase or not user_id:
        return False
    try:
        supabase.table("clients").insert(
            {
                "user_id": user_id,
                "client_name": client_name,
                "industry": industry,
            }
        ).execute()
        return True
    except Exception:
        return False

def save_audit_run(user_id: str, client_id: str, file_name: str, selected_metrics: List[str], anomaly_count: int, risk_label: str) -> bool:
    if not supabase or not user_id or not client_id:
        return False
    try:
        supabase.table("audit_runs").insert(
            {
                "user_id": user_id,
                "client_id": client_id,
                "file_name": file_name,
                "selected_metrics": ", ".join(selected_metrics),
                "anomaly_count": anomaly_count,
                "risk_label": risk_label,
            }
        ).execute()
        return True
    except Exception:
        return False

def get_recent_runs(user_id: str, client_id: Optional[str] = None) -> List[Dict]:
    if not supabase or not user_id:
        return []
    try:
        query = (
            supabase.table("audit_runs")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
        )
        if client_id:
            query = query.eq("client_id", client_id)
        response = query.limit(8).execute()
        return response.data or []
    except Exception:
        return []

# =========================================
# AUTH SCREEN
# =========================================
if not st.session_state.logged_in:
    st.markdown('<div class="auth-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">🧠 ProAudit AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-subtitle">Premium audit intelligence platform with anomaly detection, AI insights, and downloadable workpapers.</div>', unsafe_allow_html=True)

    left, right = st.columns([1.1, 1], gap="large")

    with left:
        st.markdown(
            """
            <div class="hero-card">
                <h1 style="margin-top:0; line-height:1.15;">Enterprise-style<br>Audit Analytics</h1>
                <p class="small-muted">
                    Detect financial anomalies, generate AI-supported audit commentary,
                    and export professional PDF and Excel outputs from one dashboard.
                </p>
                <div class="feature-bullet">• Multi-client workspace</div>
                <div class="feature-bullet">• AI audit copilot</div>
                <div class="feature-bullet">• Excel workpapers + PDF reports</div>
                <div class="feature-bullet">• Secure user access with Supabase Auth</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        login_tab, signup_tab = st.tabs(["Login", "Create account"])

        with login_tab:
            email = st.text_input("Work email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login", use_container_width=True):
                try:
                    result = sign_in_user(email, password)
                    user = getattr(result, "user", None)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user_email = getattr(user, "email", email)
                        st.session_state.user_id = getattr(user, "id", None)
                        st.rerun()
                    else:
                        st.error("Login failed.")
                except Exception as e:
                    st.error(f"Login error: {e}")

        with signup_tab:
            new_email = st.text_input("Work email", key="signup_email")
            new_password = st.text_input("Password", type="password", key="signup_password")
            confirm_password = st.text_input("Confirm password", type="password", key="signup_confirm")
            if st.button("Create account", use_container_width=True):
                if not new_email or not new_password:
                    st.error("Email and password are required.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    try:
                        sign_up_user(new_email, new_password)
                        st.success("Account created. Verify your email first if confirmation is enabled.")
                    except Exception as e:
                        st.error(f"Signup error: {e}")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# =========================================
# SIDEBAR
# =========================================
st.sidebar.markdown("## 🧠 ProAudit AI")
st.sidebar.caption("Audit Intelligence Platform")

page = st.sidebar.radio("Go to", ["📊 Dashboard", "⚠️ Anomalies", "📄 Reports"])

st.sidebar.markdown("---")
st.sidebar.write(f"Logged in as: **{st.session_state.user_email}**")

st.sidebar.markdown("### 🏢 Workspace")
all_clients = get_clients(st.session_state.user_id)
client_name_map = {client["client_name"]: client["id"] for client in all_clients if "client_name" in client and "id" in client}

if all_clients:
    default_client_name = st.session_state.selected_client_name if st.session_state.selected_client_name in client_name_map else all_clients[0]["client_name"]
    selected_client_name = st.sidebar.selectbox("Select client", options=list(client_name_map.keys()), index=list(client_name_map.keys()).index(default_client_name))
    st.session_state.selected_client_name = selected_client_name
    st.session_state.selected_client_id = client_name_map[selected_client_name]
else:
    st.sidebar.info("No clients yet. Create your first client below.")

with st.sidebar.expander("➕ Create new client", expanded=False):
    new_client_name = st.text_input("Client name", key="new_client_name")
    new_client_industry = st.text_input("Industry", key="new_client_industry")
    if st.button("Add client", use_container_width=True):
        if not new_client_name.strip():
            st.error("Client name is required.")
        else:
            created = create_client_record(st.session_state.user_id, new_client_name.strip(), new_client_industry.strip())
            if created:
                st.success("Client created.")
                st.rerun()
            else:
                st.error("Could not create client.")

st.sidebar.markdown("---")
if st.sidebar.button("Logout", use_container_width=True):
    sign_out_user()
    st.session_state.logged_in = False
    st.session_state.user_email = None
    st.session_state.user_id = None
    st.session_state.selected_client_id = None
    st.session_state.selected_client_name = None
    st.rerun()

# =========================================
# HEADER
# =========================================
top_left, top_right = st.columns([6, 1])
with top_left:
    st.markdown(
        """
        <div class="hero-card">
            <div style="font-size:3rem;font-weight:800;line-height:1.05;">ProAudit AI</div>
            <div style="font-size:1.18rem;font-weight:700;margin-top:0.8rem;">Real-Time Audit Intelligence Platform</div>
            <div class="small-muted" style="margin-top:0.8rem;">
                Detect anomalies • Generate AI insights • Export audit-ready reports
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with top_right:
    st.markdown(
        f"""
        <div class="mini-card" style="text-align:center; margin-top:0.15rem;">
            <div class="small-muted">Workspace user</div>
            <div style="font-weight:700; margin-top:0.25rem; word-break:break-word;">{st.session_state.user_email}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

if not st.session_state.selected_client_id:
    st.warning("Create and select a client workspace from the sidebar to continue.")
    st.stop()

st.markdown(
    f"""
    <div class="mini-card">
        <b>Workspace:</b> {st.session_state.selected_client_name}
        &nbsp;&nbsp;|&nbsp;&nbsp;
        <b>User:</b> {st.session_state.user_email}
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================================
# FILE UPLOAD
# =========================================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("📂 Step 1: Upload Financial Data")
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])
st.markdown("</div>", unsafe_allow_html=True)

if not uploaded_file:
    recent_runs = get_recent_runs(st.session_state.user_id, st.session_state.selected_client_id)

    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("📌 Client Overview")
        st.markdown(
            f"""
            <div class="small-muted">
            Current client: <b>{st.session_state.selected_client_name}</b><br>
            Upload a CSV file to begin analysis for this workspace.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("🕒 Recent Activity")
        if recent_runs:
            for run in recent_runs[:5]:
                st.markdown(
                    f"""
                    <div class="mini-card">
                    <b>{run.get('file_name', 'Unknown file')}</b><br>
                    <span class="small-muted">Risk: {run.get('risk_label', 'N/A')} • {run.get('anomaly_count', 0)} anomalies</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("🚀 Upload a CSV to start audit analysis for this client workspace.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("📈 Financial Trends")
    st.info("Charts will appear here after data upload.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.stop()

# =========================================
# DATA PROCESSING
# =========================================
df = pd.read_csv(uploaded_file)
df = clean_dataframe(df)
df = safe_date_column(df)
df = df.sort_values(by="Date")

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("⚙️ Step 2: Select Financial Metrics")

numeric_cols = df.select_dtypes(include="number").columns.tolist()
if len(numeric_cols) == 0:
    st.error("No numeric columns found in this dataset.")
    st.stop()

default_metrics = numeric_cols[:2] if len(numeric_cols) >= 2 else numeric_cols[:1]
selected_cols = st.multiselect(
    "Choose one or more numeric columns to analyze",
    numeric_cols,
    default=default_metrics,
)
if len(selected_cols) == 0:
    st.warning("Please select at least one metric.")
    st.stop()
st.markdown("</div>", unsafe_allow_html=True)

results = []
for col in selected_cols:
    std_val = df[col].std()
    if pd.isna(std_val) or std_val == 0:
        df[f"{col}_z"] = 0
        df[f"{col}_anomaly"] = False
    else:
        df[f"{col}_z"] = (df[col] - df[col].mean()) / std_val
        df[f"{col}_anomaly"] = df[f"{col}_z"].abs() > 2

    temp = df[df[f"{col}_anomaly"]][["Date", col, f"{col}_z"]].copy()
    temp.columns = ["Date", "Value", "Z_Score"]
    temp["Metric"] = col
    results.append(temp)

anomalies = pd.concat(results, ignore_index=True) if results else pd.DataFrame(columns=["Date", "Value", "Z_Score", "Metric"])
risk_label = "High" if len(anomalies) > 10 else "Medium" if len(anomalies) > 3 else "Low"

save_audit_run(
    st.session_state.user_id,
    st.session_state.selected_client_id,
    uploaded_file.name,
    selected_cols,
    len(anomalies),
    risk_label,
)

st.markdown(
    f"""
    <div class="status-card">
        <span style="font-weight:700;">✅ System Ready</span>
        <span class="small-muted"> — File loaded successfully: {uploaded_file.name}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("📊 Records", f"{len(df):,}")
k2.metric("⚠️ Anomalies", len(anomalies), delta="High" if len(anomalies) > 10 else "Low")
k3.metric("📈 Metrics", len(selected_cols))
risk_icon = "🔴" if risk_label == "High" else "🟡" if risk_label == "Medium" else "🟢"
k4.metric("🔥 Risk Level", f"{risk_icon} {risk_label}")

# =========================================
# DASHBOARD
# =========================================
if page == "📊 Dashboard":
    d1, d2 = st.columns([1.05, 1], gap="large")

    with d1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Dataset Preview")
        st.dataframe(df.head(12), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with d2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Workspace Summary")
        st.markdown(
            f"""
            <div class="small-muted">
            Client: {st.session_state.selected_client_name}<br>
            File: {uploaded_file.name}<br>
            Rows: {len(df)}<br>
            Columns: {len(df.columns)}<br>
            Selected Metrics: {", ".join(selected_cols)}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    i1, i2 = st.columns(2, gap="large")
    with i1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("📌 Key Insights")
        highest_metric = selected_cols[0] if selected_cols else "N/A"
        st.markdown(
            f"""
            <div class="small-muted">
            • Total anomalies detected: <b>{len(anomalies)}</b><br>
            • Highest focus metric: <b>{highest_metric}</b><br>
            • Risk level: <b>{risk_label}</b><br>
            • Workspace: <b>{st.session_state.selected_client_name}</b>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with i2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("🕒 Recent Activity")
        recent_runs = get_recent_runs(st.session_state.user_id, st.session_state.selected_client_id)
        if recent_runs:
            for run in recent_runs[:5]:
                st.markdown(
                    f"""
                    <div class="mini-card">
                    <b>{run.get('file_name', 'Unknown file')}</b><br>
                    <span class="small-muted">Risk: {run.get('risk_label', 'N/A')} • {run.get('anomaly_count', 0)} anomalies</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("No saved runs yet.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("📈 Financial Trend Analysis")
    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor("#0B1220")
    ax.set_facecolor("#111827")
    colors = ["#6366F1", "#22C55E", "#F59E0B", "#EF4444", "#14B8A6", "#38BDF8"]

    for i, col in enumerate(selected_cols):
        ax.plot(df["Date"], df[col], linewidth=2.6, color=colors[i % len(colors)], label=col)

    ax.legend(facecolor="#111827", edgecolor="#374151", labelcolor="white")
    ax.set_title("Metric Trends Over Time", color="white", fontsize=14)
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("#374151")
    st.pyplot(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================
# ANOMALIES
# =========================================
elif page == "⚠️ Anomalies":
    a1, a2 = st.columns([1.3, 0.95], gap="large")

    with a1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Detected Anomalies")
        if anomalies.empty:
            st.success("No anomalies detected with the current threshold.")
        else:
            st.dataframe(anomalies, use_container_width=True)

            st.subheader("Metric-Level View")
            metric_choice = st.selectbox("Select metric for detailed view", selected_cols)
            metric_anomalies = anomalies[anomalies["Metric"] == metric_choice]

            fig, ax = plt.subplots(figsize=(12, 5))
            fig.patch.set_facecolor("#0B1220")
            ax.set_facecolor("#111827")
            ax.plot(df["Date"], df[metric_choice], label=metric_choice, linewidth=2.6, color="#6366F1")

            if not metric_anomalies.empty:
                ax.scatter(metric_anomalies["Date"], metric_anomalies["Value"], label="Anomalies", s=60, color="#EF4444")

            ax.legend(facecolor="#111827", edgecolor="#374151", labelcolor="white")
            ax.set_title(f"{metric_choice} - Trend and Anomalies", color="white", fontsize=14)
            ax.tick_params(colors="white")
            for spine in ax.spines.values():
                spine.set_color("#374151")
            st.pyplot(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with a2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("🤖 AI Audit Insight")

        if anomalies.empty:
            st.info("Upload data with anomalies to generate AI insight.")
        else:
            metric_choice = st.selectbox("AI metric focus", selected_cols, key="ai_metric_focus")
            metric_anomalies = anomalies[anomalies["Metric"] == metric_choice]
            insight_row = metric_anomalies.iloc[0] if not metric_anomalies.empty else anomalies.iloc[0]

            try:
                with st.spinner("Generating AI audit insight..."):
                    ai_text = generate_ai_insight(
                        metric_name=insight_row["Metric"],
                        metric_value=insight_row["Value"],
                        z_score_value=insight_row["Z_Score"],
                    )
                st.session_state.last_ai_text = ai_text

                st.markdown(
                    f"""
                    <div class="insight-card">
                        <h4 style="margin-top:0;">🤖 AI Audit Insight</h4>
                        <p style="margin-bottom:0;">{ai_text}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                pdf_bytes = create_pdf_report(
                    username=st.session_state.user_email or "Unknown User",
                    client_name=st.session_state.selected_client_name or "Unknown Client",
                    ai_text=ai_text,
                    selected_metric=insight_row["Metric"],
                    anomaly_value=insight_row["Value"],
                    anomaly_zscore=insight_row["Z_Score"],
                )

                st.download_button(
                    "📥 Download Audit Report (PDF)",
                    data=pdf_bytes,
                    file_name=f"{st.session_state.selected_client_name}_audit_report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"AI Error: {e}")

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("💬 Audit Assistant Chat")
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        for msg in st.session_state.chat_history:
            role = "You" if msg["role"] == "user" else "ProAudit AI"
            st.markdown(f"**{role}:** {msg['content']}")

        question = st.text_area("Ask about the uploaded data, anomalies, or audit risk", height=100)

        if st.button("Ask assistant", use_container_width=True):
            if not question.strip():
                st.warning("Enter a question first.")
            else:
                try:
                    df_summary = f"Rows={len(df)}, Columns={len(df.columns)}, Metrics={', '.join(selected_cols)}"
                    anomaly_summary = f"Anomaly count={len(anomalies)}, Risk={risk_label}"
                    with st.spinner("Thinking..."):
                        answer = generate_chat_response(question, df_summary, anomaly_summary)

                    st.session_state.chat_history.append({"role": "user", "content": question})
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
                    st.rerun()
                except Exception as e:
                    st.error(f"Assistant error: {e}")

        st.markdown("</div>", unsafe_allow_html=True)

# =========================================
# REPORTS
# =========================================
elif page == "📄 Reports":
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Export Reports")

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Full Data", index=False)
        anomalies.to_excel(writer, sheet_name="Anomalies", index=False)
        summary_df = pd.DataFrame(
            {
                "Metric": ["Client", "Total Records", "Total Anomalies", "Metrics Selected", "Risk Score"],
                "Value": [
                    st.session_state.selected_client_name,
                    len(df),
                    len(anomalies),
                    ", ".join(selected_cols),
                    risk_label,
                ],
            }
        )
        summary_df.to_excel(writer, sheet_name="Summary", index=False)

    st.download_button(
        "📥 Download Excel Workpaper",
        data=excel_buffer.getvalue(),
        file_name=f"{st.session_state.selected_client_name}_audit_workpaper.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    recent_runs = get_recent_runs(st.session_state.user_id, st.session_state.selected_client_id)
    if recent_runs:
        st.subheader("Saved Runs")
        recent_df = pd.DataFrame(recent_runs)
        show_cols = [c for c in ["file_name", "selected_metrics", "anomaly_count", "risk_label", "created_at"] if c in recent_df.columns]
        st.dataframe(recent_df[show_cols], use_container_width=True)

    if not anomalies.empty:
        st.info("Go to the Anomalies page to generate and download the AI PDF report.")

    st.markdown("</div>", unsafe_allow_html=True)