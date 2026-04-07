import io
import os
from datetime import datetime

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
supabase: Client | None = (
    create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    if SUPABASE_URL and SUPABASE_ANON_KEY
    else None
)

# =========================================
# PREMIUM UI
# =========================================
st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(99,102,241,0.20), transparent 28%),
            radial-gradient(circle at top right, rgba(14,165,233,0.14), transparent 24%),
            linear-gradient(180deg, #081120 0%, #0B1220 45%, #0E1424 100%);
        color: #E5E7EB;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0B1220 0%, #0F172A 100%);
        border-right: 1px solid rgba(148,163,184,0.18);
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1250px;
    }

    .hero-card {
        background: linear-gradient(135deg, rgba(17,24,39,0.88), rgba(15,23,42,0.78));
        border: 1px solid rgba(99,102,241,0.25);
        border-radius: 22px;
        padding: 28px 30px;
        box-shadow: 0 20px 50px rgba(0,0,0,0.28);
        margin-bottom: 1rem;
    }

    .section-card {
        background: linear-gradient(180deg, rgba(15,23,42,0.90), rgba(17,24,39,0.88));
        border: 1px solid rgba(148,163,184,0.14);
        border-radius: 18px;
        padding: 18px 18px 10px 18px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.20);
        margin-bottom: 1rem;
    }

    .small-muted {
        color: #94A3B8;
        font-size: 0.95rem;
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

    .insight-card {
        background: linear-gradient(135deg, rgba(30,41,59,0.95), rgba(17,24,39,0.92));
        border: 1px solid rgba(56,189,248,0.20);
        border-left: 4px solid #6366F1;
        border-radius: 16px;
        padding: 18px 20px;
        margin-top: 8px;
        margin-bottom: 8px;
    }

    .auth-wrap {
        max-width: 760px;
        margin: 2rem auto 0 auto;
    }

    .auth-title {
        text-align: center;
        font-size: 2.6rem;
        font-weight: 800;
        margin-bottom: 0.35rem;
    }

    .auth-subtitle {
        text-align: center;
        color: #94A3B8;
        margin-bottom: 1.5rem;
    }

    .stButton>button, .stDownloadButton>button {
        border-radius: 12px !important;
        border: none !important;
        background: linear-gradient(90deg, #6366F1, #8B5CF6) !important;
        color: white !important;
        font-weight: 600 !important;
        box-shadow: 0 8px 20px rgba(99,102,241,0.25);
    }

    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stMultiSelect div[data-baseweb="select"] {
        border-radius: 12px !important;
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
# SESSION STATE
# =========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None

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


def create_pdf_report(
    username: str,
    ai_text: str,
    selected_metric: str,
    anomaly_value,
    anomaly_zscore,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("ProAudit AI - Audit Insight Report", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Generated For: {username}", styles["Normal"]))
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
        raise ValueError("Missing OPENAI_API_KEY")

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


def sign_up_user(email: str, password: str):
    if not supabase:
        raise ValueError("Supabase is not configured")
    return supabase.auth.sign_up({"email": email, "password": password})


def sign_in_user(email: str, password: str):
    if not supabase:
        raise ValueError("Supabase is not configured")
    return supabase.auth.sign_in_with_password({"email": email, "password": password})


def sign_out_user():
    if supabase:
        supabase.auth.sign_out()


# =========================================
# AUTH SCREEN
# =========================================
if not st.session_state.logged_in:
    st.markdown('<div class="auth-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">🧠 ProAudit AI</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="auth-subtitle">Premium audit intelligence platform with anomaly detection, AI insights, and downloadable workpapers.</div>',
        unsafe_allow_html=True,
    )

    auth_left, auth_right = st.columns([1.15, 1], gap="large")

    with auth_left:
        st.markdown(
            """
            <div class="hero-card">
                <h2 style="margin-top:0;">Enterprise-style Audit Analytics</h2>
                <p class="small-muted">
                Detect financial anomalies, generate AI-supported audit commentary,
                and export professional PDF and Excel outputs from one dashboard.
                </p>
                <ul class="small-muted">
                    <li>Multi-metric anomaly analysis</li>
                    <li>AI-generated audit explanations</li>
                    <li>Excel workpapers + PDF reports</li>
                    <li>Secure user access with Supabase Auth</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with auth_right:
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
                        st.success("Account created. Check your email if confirmation is enabled, then login.")
                    except Exception as e:
                        st.error(f"Signup error: {e}")

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# =========================================
# SIDEBAR
# =========================================
st.sidebar.markdown("## 🧭 Navigation")
page = st.sidebar.radio(
    "Go to",
    ["📊 Dashboard", "⚠️ Anomalies", "📄 Reports"],
)
st.sidebar.markdown("---")
st.sidebar.write(f"Logged in as: **{st.session_state.user_email}**")

if st.sidebar.button("Logout", use_container_width=True):
    sign_out_user()
    st.session_state.logged_in = False
    st.session_state.user_email = None
    st.session_state.user_id = None
    st.rerun()

# =========================================
# HERO
# =========================================
st.markdown(
    """
    <div class="hero-card">
        <div style="font-size:3rem;font-weight:800;line-height:1.05;">ProAudit AI</div>
        <div style="font-size:1.15rem;font-weight:700;margin-top:0.8rem;">Real-Time Audit Intelligence Platform</div>
        <div class="small-muted" style="margin-top:0.8rem;">
            Detect anomalies • Generate AI insights • Export audit-ready reports
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================================
# FILE UPLOAD
# =========================================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])
st.markdown("</div>", unsafe_allow_html=True)

if not uploaded_file:
    st.info("📂 Upload a CSV file to begin analysis.")
    st.stop()

# =========================================
# READ DATA
# =========================================
df = pd.read_csv(uploaded_file)
df = safe_date_column(df)
df = df.sort_values(by="Date")

# =========================================
# METRIC SELECTION
# =========================================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("⚙️ Select Financial Metrics")
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

# =========================================
# ANOMALY DETECTION
# =========================================
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

anomalies = (
    pd.concat(results, ignore_index=True)
    if results
    else pd.DataFrame(columns=["Date", "Value", "Z_Score", "Metric"])
)

risk_label = "High" if len(anomalies) > 10 else "Medium" if len(anomalies) > 3 else "Low"

# =========================================
# KPI CARDS
# =========================================
k1, k2, k3, k4 = st.columns(4)
k1.metric("📊 Records", len(df))
k2.metric("⚠️ Anomalies", len(anomalies))
k3.metric("📈 Metrics", len(selected_cols))
k4.metric("🔥 Risk Level", risk_label)

# =========================================
# DASHBOARD
# =========================================
if page == "📊 Dashboard":
    left, right = st.columns([1.15, 1], gap="large")

    with left:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Dataset Preview")
        st.dataframe(df.head(12), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Dataset Summary")
        st.markdown(
            f"""
            <div class="small-muted">
            File: {uploaded_file.name}<br>
            Rows: {len(df)}<br>
            Columns: {len(df.columns)}<br>
            Selected Metrics: {", ".join(selected_cols)}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("📈 Financial Trend Analysis")

    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor("#0B1220")
    ax.set_facecolor("#111827")

    colors = ["#6366F1", "#22C55E", "#F59E0B", "#EF4444", "#14B8A6", "#38BDF8"]

    for i, col in enumerate(selected_cols):
        ax.plot(
            df["Date"],
            df[col],
            linewidth=2.6,
            color=colors[i % len(colors)],
            label=col,
        )

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
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Detected Anomalies")

    if anomalies.empty:
        st.success("No anomalies detected with the current threshold.")
        st.markdown("</div>", unsafe_allow_html=True)
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
            ax.scatter(
                metric_anomalies["Date"],
                metric_anomalies["Value"],
                label="Anomalies",
                s=60,
                color="#EF4444",
            )

        ax.legend(facecolor="#111827", edgecolor="#374151", labelcolor="white")
        ax.set_title(f"{metric_choice} - Trend and Anomalies", color="white", fontsize=14)
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_color("#374151")

        st.pyplot(fig, use_container_width=True)

        st.subheader("🤖 AI Audit Insight")
        insight_row = metric_anomalies.iloc[0] if not metric_anomalies.empty else anomalies.iloc[0]

        try:
            with st.spinner("Generating AI audit insight..."):
                ai_text = generate_ai_insight(
                    metric_name=insight_row["Metric"],
                    metric_value=insight_row["Value"],
                    z_score_value=insight_row["Z_Score"],
                )

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
                ai_text=ai_text,
                selected_metric=insight_row["Metric"],
                anomaly_value=insight_row["Value"],
                anomaly_zscore=insight_row["Z_Score"],
            )

            st.download_button(
                "📥 Download Audit Report (PDF)",
                data=pdf_bytes,
                file_name="audit_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        except Exception as e:
            st.error(f"AI Error: {e}")

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
                "Metric": ["Total Records", "Total Anomalies", "Metrics Selected", "Risk Score"],
                "Value": [len(df), len(anomalies), ", ".join(selected_cols), risk_label],
            }
        )
        summary_df.to_excel(writer, sheet_name="Summary", index=False)

    st.download_button(
        "📥 Download Excel Workpaper",
        data=excel_buffer.getvalue(),
        file_name="audit_workpaper.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    if not anomalies.empty:
        st.info("Go to the Anomalies page to generate and download the AI PDF report.")
    st.markdown("</div>", unsafe_allow_html=True)