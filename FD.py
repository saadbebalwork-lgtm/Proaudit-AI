import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
import os
import json
import hashlib
from openai import OpenAI
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# =========================================
# PAGE CONFIG
# =========================================
st.set_page_config(page_title="ProAudit AI", layout="wide")

# =========================================
# OPENAI SETUP
# =========================================
client = OpenAI(api_key=os.getenv("YOUR-API-KEY"))

# =========================================
# STYLING
# =========================================
st.markdown("""
<style>
    /* Background */
    .stApp {
        background: linear-gradient(135deg, #0E1117, #111827);
        color: #E6EDF3;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #111827;
        border-right: 1px solid #1F2937;
    }

    /* Titles */
    h1 {
        font-size: 36px;
        font-weight: 700;
    }

    h2, h3 {
        color: #E6EDF3;
    }

    /* Cards */
    div[data-testid="metric-container"] {
        background: linear-gradient(145deg, #111827, #1F2937);
        border: 1px solid #374151;
        padding: 18px;
        border-radius: 14px;
        box-shadow: 0 0 20px rgba(0,0,0,0.3);
    }

    /* Buttons */
    button {
        border-radius: 10px !important;
        background: linear-gradient(90deg, #6366F1, #8B5CF6);
        color: white;
        border: none;
    }

    /* Dataframe */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }

    /* Alert boxes */
    .stAlert {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# =========================================
# USER AUTH
# =========================================
USER_FILE = "users.json"

def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

users = load_users()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = None

# =========================================
# LOGIN / SIGNUP SCREEN
# =========================================
if not st.session_state.logged_in:
    st.markdown("# 🧠 ProAudit AI")
    st.markdown("### AI-Powered Audit Intelligence Platform")
    st.caption("Secure sign in to access analytics, anomaly detection, and report generation.")

    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])

    with login_tab:
        st.subheader("🔐 Login")
        login_user = st.text_input("Username", key="login_user")
        login_pass = st.text_input("Password", type="password", key="login_pass")

        if st.button("Login", use_container_width=True):
            if login_user in users and users[login_user] == hash_password(login_pass):
                st.session_state.logged_in = True
                st.session_state.username = login_user
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with signup_tab:
        st.subheader("🆕 Create Account")
        signup_user = st.text_input("New Username", key="signup_user")
        signup_pass = st.text_input("New Password", type="password", key="signup_pass")
        signup_confirm = st.text_input("Confirm Password", type="password", key="signup_confirm")

        if st.button("Create Account", use_container_width=True):
            if not signup_user or not signup_pass:
                st.error("Username and password are required.")
            elif signup_user in users:
                st.error("Username already exists.")
            elif signup_pass != signup_confirm:
                st.error("Passwords do not match.")
            else:
                users[signup_user] = hash_password(signup_pass)
                save_users(users)
                st.success("Account created successfully. Please login.")

    st.stop()

# =========================================
# HELPERS
# =========================================
def safe_date_column(df: pd.DataFrame) -> pd.DataFrame:
    date_cols = [col for col in df.columns if "date" in col.lower()]
    if date_cols:
        try:
            df[date_cols[0]] = pd.to_datetime(df[date_cols[0]], errors="coerce")
            df = df.rename(columns={date_cols[0]: "Date"})
        except Exception:
            df["Date"] = range(len(df))
    else:
        df["Date"] = range(len(df))
    return df

def create_pdf_report(username: str, ai_text: str, selected_metric: str, anomaly_value, anomaly_zscore) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("ProAudit AI - Audit Insight Report", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"User: {username}", styles["Normal"]))
    story.append(Paragraph(f"Metric: {selected_metric}", styles["Normal"]))
    story.append(Paragraph(f"Anomalous Value: {anomaly_value}", styles["Normal"]))
    story.append(Paragraph(f"Z-Score: {round(float(anomaly_zscore), 2)}", styles["Normal"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("AI Audit Insight", styles["Heading2"]))
    story.append(Paragraph(ai_text.replace("\n", "<br/>"), styles["BodyText"]))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

def generate_ai_insight(metric_name: str, metric_value, z_score_value):
    prompt = f"""
You are an audit assistant.

Analyze this anomaly:
Metric: {metric_name}
Value: {metric_value}
Z-score: {z_score_value}

Write a concise professional audit insight covering:
1. Why this may be risky
2. What an auditor should check
3. A short recommended next step
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# =========================================
# SIDEBAR
# =========================================
st.sidebar.markdown("## 🧭 Navigation")
page = st.sidebar.radio(
    "Go to",
    ["📊 Dashboard", "⚠️ Anomalies", "📄 Reports"]
)

st.sidebar.markdown("---")
st.sidebar.write(f"Logged in as: **{st.session_state.username}**")

if st.sidebar.button("Logout", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.rerun()

# =========================================
# HEADER
# =========================================
st.markdown("""
# ProAudit AI
### Real-Time Audit Intelligence Platform

<span style='color:#9CA3AF'>
Detect anomalies • Generate AI insights • Export audit-ready reports
</span>
""", unsafe_allow_html=True)

st.divider()

# =========================================
# FILE UPLOAD
# =========================================
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

if not uploaded_file:
    st.info("Upload a CSV file to begin.")
    st.stop()

# =========================================
# READ DATA
# =========================================
df = pd.read_csv(uploaded_file)
df = safe_date_column(df)
df = df.sort_values(by="Date")

# =========================================
# COLUMN SELECTION
# =========================================
st.subheader("⚙️ Select Financial Metrics")
numeric_cols = df.select_dtypes(include="number").columns.tolist()

if len(numeric_cols) == 0:
    st.error("No numeric columns found in this dataset.")
    st.stop()

selected_cols = st.multiselect(
    "Choose one or more numeric columns to analyze",
    numeric_cols,
    default=numeric_cols[:2] if len(numeric_cols) >= 2 else numeric_cols[:1]
)

if len(selected_cols) == 0:
    st.warning("Please select at least one metric.")
    st.stop()

# =========================================
# MULTI-METRIC ANOMALY DETECTION
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

anomalies = pd.concat(results, ignore_index=True) if results else pd.DataFrame(columns=["Date", "Value", "Z_Score", "Metric"])

risk_label = "High" if len(anomalies) > 10 else "Medium" if len(anomalies) > 3 else "Low"

# =========================================
# KPI CARDS
# =========================================
col1, col2, col3, col4 = st.columns(4)

col1.metric("📊 Records", len(df))
col2.metric("⚠️ Anomalies", len(anomalies))
col3.metric("📈 Metrics", len(selected_cols))
col4.metric("🔥 Risk Level", risk_label)

# =========================================
# PAGE: DASHBOARD
# =========================================
if page == "📊 Dashboard":
    left, right = st.columns([1.1, 1])

    with left:
        st.subheader("Dataset Preview")
        st.dataframe(df.head(10), use_container_width=True)

    with right:
        st.subheader("Dataset Summary")
        st.markdown(f"""
<div class="small-muted">
File: {uploaded_file.name}<br>
Rows: {len(df)}<br>
Columns: {len(df.columns)}<br>
Selected Metrics: {", ".join(selected_cols)}
</div>
""", unsafe_allow_html=True)

# Plotting
    st.subheader("📈 Financial Trend Analysis")
    fig, ax = plt.subplots(figsize=(12, 5))

 # Dark theme styling
    fig.patch.set_facecolor("#0E1117")
    ax.set_facecolor("#111827")

    colors = ["#6366F1", "#22C55E", "#F59E0B", "#EF4444", "#14B8A6"]

    for i, col in enumerate(selected_cols):
      ax.plot(
        df["Date"],
        df[col],
        linewidth=2.5,
        color=colors[i % len(colors)],
        label=col
    )
# Styling
    ax.legend(facecolor="#111827", edgecolor="#374151")
    ax.set_title("Metric Trends Over Time", color="white", fontsize=14)
    ax.tick_params(colors='white')

    for spine in ax.spines.values():
     spine.set_color("#374151")
    st.pyplot(fig)

# =========================================
# PAGE: ANOMALIES
# =========================================
elif page == "⚠️ Anomalies":
    st.subheader("Detected Anomalies")

    if anomalies.empty:
        st.success("No anomalies detected with the current threshold.")
    else:
        st.dataframe(anomalies, use_container_width=True)

        st.subheader("Metric-Level Trend with Anomalies")
        metric_choice = st.selectbox("Select metric for detailed view", selected_cols)

        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(df["Date"], df[metric_choice], label=metric_choice)

        metric_anomalies = anomalies[anomalies["Metric"] == metric_choice]
        if not metric_anomalies.empty:
            ax.scatter(metric_anomalies["Date"], metric_anomalies["Value"], label="Anomalies")

        ax.legend()
        ax.set_title(f"{metric_choice} - Trend and Anomalies")
        st.pyplot(fig)

        st.subheader("🤖 AI Audit Insight")
        insight_row = metric_anomalies.iloc[0] if not metric_anomalies.empty else anomalies.iloc[0]

        try:
            ai_text = generate_ai_insight(
                metric_name=insight_row["Metric"],
                metric_value=insight_row["Value"],
                z_score_value=insight_row["Z_Score"]
            )
            st.markdown(f"""
            <div style="
            background: linear-gradient(145deg, #1F2937, #111827); 
            padding:20px;
            border-radius:12px;
            border:1px solid #374151;
            ">
            <h4>🤖 AI Audit Insight</h4>
            <p>{ai_text}</p>
            </div>
            """, unsafe_allow_html=True)

            pdf_bytes = create_pdf_report(
                username=st.session_state.username,
                ai_text=ai_text,
                selected_metric=insight_row["Metric"],
                anomaly_value=insight_row["Value"],
                anomaly_zscore=insight_row["Z_Score"]
            )

            st.download_button(
                "📥 Download Audit Report",
                data=pdf_bytes,
                file_name="audit_report.pdf",
                use_container_width=True
            )

        except Exception as e:
            st.error(f"AI Error: {e}")

# =========================================
# PAGE: REPORTS
# =========================================
elif page == "📄 Reports":
    st.subheader("Export Reports")

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Full Data", index=False)
        anomalies.to_excel(writer, sheet_name="Anomalies", index=False)

        summary_df = pd.DataFrame({
            "Metric": ["Total Records", "Total Anomalies", "Metrics Selected", "Risk Score"],
            "Value": [len(df), len(anomalies), ", ".join(selected_cols), risk_label]
        })
        summary_df.to_excel(writer, sheet_name="Summary", index=False)

    st.download_button(
        "📥 Download Excel Workpaper",
        data=excel_buffer.getvalue(),
        file_name="audit_workpaper.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    if not anomalies.empty:
        st.info("Go to the Anomalies page to generate and download the AI PDF report.")