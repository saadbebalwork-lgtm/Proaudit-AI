import io
import os
import hashlib
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from openai import OpenAI
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from db import (
    supabase,
    set_auth,
    sign_in_user,
    sign_out_user,
    sign_up_user,
    get_clients,
    create_client_db,
    delete_client,
    save_audit,
    get_recent_runs,
    get_team_members,
    invite_team_member,
    delete_team_member,
    get_billing_status,
    update_billing,
)

# =========================================
# PAGE CONFIG
# =========================================
st.set_page_config(
    page_title="ProAudit AI",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================
# OPENAI / STRIPE
# =========================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", st.secrets.get("OPENAI_API_KEY", ""))
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

STRIPE_PAYMENT_LINK = os.getenv(
    "STRIPE_PAYMENT_LINK",
    st.secrets.get("STRIPE_PAYMENT_LINK", "")
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
    "last_saved_run_key": None,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

active_user = set_auth()
if active_user and not st.session_state.logged_in:
    st.session_state.logged_in = True
    st.session_state.user_email = getattr(active_user, "email", None)
    st.session_state.user_id = getattr(active_user, "id", None)

# =========================================
# UI DESIGN
# =========================================
st.markdown(
    """
    <style>
    :root {
        --bg: #0B1220;
        --panel: #0F172A;
        --panel-2: #111827;
        --panel-3: #172554;
        --line: rgba(148,163,184,0.16);
        --text: #E5E7EB;
        --muted: #94A3B8;
        --primary: #2563EB;
        --primary-2: #1D4ED8;
        --success: #16A34A;
        --danger: #DC2626;
    }

    .stApp {
        background:
            radial-gradient(circle at top right, rgba(37,99,235,0.16), transparent 22%),
            radial-gradient(circle at top left, rgba(59,130,246,0.12), transparent 18%),
            linear-gradient(180deg, #08101D 0%, #0B1220 45%, #0E1728 100%);
        color: var(--text);
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0A1020 0%, #0D1528 100%);
        border-right: 1px solid var(--line);
    }

    .block-container {
        max-width: 1340px;
        padding-top: 1.1rem;
        padding-bottom: 2rem;
    }

    .app-shell {
        padding-top: 0.35rem;
    }

    .hero-shell {
        background: linear-gradient(135deg, rgba(15,23,42,0.94), rgba(10,16,32,0.88));
        border: 1px solid rgba(59,130,246,0.18);
        border-radius: 22px;
        padding: 28px 30px 22px 30px;
        box-shadow: 0 24px 60px rgba(0,0,0,0.28);
        margin-bottom: 16px;
    }

    .hero-eyebrow {
        display: inline-block;
        font-size: 0.83rem;
        font-weight: 600;
        color: #BFDBFE;
        background: rgba(37,99,235,0.14);
        border: 1px solid rgba(59,130,246,0.20);
        padding: 6px 10px;
        border-radius: 999px;
        margin-bottom: 14px;
    }

    .hero-title {
        font-size: 3rem;
        line-height: 1.02;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #F8FAFC;
        margin-bottom: 10px;
    }

    .hero-subtitle {
        color: var(--muted);
        font-size: 1rem;
        line-height: 1.65;
        max-width: 920px;
    }

    .toolbar-card {
        background: linear-gradient(180deg, rgba(15,23,42,0.96), rgba(17,24,39,0.94));
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 14px 18px;
        margin-bottom: 14px;
    }

    .toolbar-grid {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        flex-wrap: wrap;
    }

    .toolbar-meta {
        color: #E2E8F0;
        font-size: 0.98rem;
        font-weight: 600;
    }

    .toolbar-meta span {
        color: var(--muted);
        font-weight: 500;
    }

    .section-wrap {
        background: linear-gradient(180deg, rgba(15,23,42,0.96), rgba(17,24,39,0.94));
        border: 1px solid var(--line);
        border-radius: 18px;
        box-shadow: 0 14px 34px rgba(0,0,0,0.18);
        overflow: hidden;
        margin-bottom: 14px;
    }

    .section-head {
        padding: 16px 18px;
        border-bottom: 1px solid rgba(148,163,184,0.10);
        background: linear-gradient(180deg, rgba(30,41,59,0.35), rgba(15,23,42,0.18));
    }

    .section-title {
        font-size: 1.08rem;
        font-weight: 700;
        color: #F8FAFC;
        margin: 0;
    }

    .section-subtitle {
        margin-top: 5px;
        color: var(--muted);
        font-size: 0.92rem;
    }

    .section-body {
        padding: 16px 18px 18px 18px;
    }

    .stack-item {
        background: linear-gradient(180deg, rgba(17,24,39,0.98), rgba(15,23,42,0.92));
        border: 1px solid rgba(148,163,184,0.10);
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 10px;
    }

    .stack-title {
        color: #F8FAFC;
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .stack-meta {
        color: var(--muted);
        font-size: 0.93rem;
        line-height: 1.55;
    }

    .metric-box {
        background: linear-gradient(180deg, rgba(15,23,42,0.98), rgba(17,24,39,0.95));
        border: 1px solid rgba(148,163,184,0.12);
        border-radius: 16px;
        padding: 16px 16px 14px 16px;
        min-height: 108px;
    }

    .metric-label {
        color: var(--muted);
        font-size: 0.9rem;
        margin-bottom: 8px;
        font-weight: 600;
    }

    .metric-value {
        color: #F8FAFC;
        font-size: 2.1rem;
        line-height: 1;
        font-weight: 800;
    }

    .metric-note {
        margin-top: 10px;
        color: #BFDBFE;
        font-size: 0.85rem;
        font-weight: 600;
    }

    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(22,163,74,0.12);
        color: #DCFCE7;
        border: 1px solid rgba(22,163,74,0.18);
        border-radius: 999px;
        padding: 8px 12px;
        font-size: 0.9rem;
        font-weight: 600;
    }

    .small-muted {
        color: var(--muted);
        font-size: 0.95rem;
        line-height: 1.6;
    }

    .auth-shell {
        max-width: 1160px;
        margin: 1rem auto 0 auto;
    }

    .auth-title {
        text-align: center;
        font-size: 2.9rem;
        font-weight: 800;
        margin-bottom: 0.35rem;
        color: #F8FAFC;
    }

    .auth-subtitle {
        text-align: center;
        color: var(--muted);
        margin-bottom: 1.6rem;
        font-size: 1.02rem;
    }

    .auth-feature {
        color: #CBD5E1;
        margin-bottom: 0.7rem;
        font-size: 0.98rem;
    }

    .top-user-card {
        background: linear-gradient(180deg, rgba(15,23,42,0.96), rgba(17,24,39,0.94));
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 16px;
        min-height: 126px;
    }

    .top-user-label {
        color: var(--muted);
        font-size: 0.86rem;
        margin-bottom: 10px;
    }

    .top-user-email {
        color: #F8FAFC;
        font-size: 1rem;
        font-weight: 700;
        word-break: break-word;
    }

    .stButton > button, .stDownloadButton > button {
        border-radius: 10px !important;
        border: 1px solid rgba(37,99,235,0.18) !important;
        background: linear-gradient(180deg, #2563EB, #1D4ED8) !important;
        color: white !important;
        font-weight: 600 !important;
        box-shadow: 0 10px 24px rgba(37,99,235,0.22);
        padding-top: 0.55rem !important;
        padding-bottom: 0.55rem !important;
    }

    .stButton > button:hover, .stDownloadButton > button:hover {
        background: linear-gradient(180deg, #1D4ED8, #1E40AF) !important;
    }

    .stLinkButton > a {
        border-radius: 10px !important;
        border: 1px solid rgba(37,99,235,0.18) !important;
        background: linear-gradient(180deg, #2563EB, #1D4ED8) !important;
        color: white !important;
        font-weight: 600 !important;
        text-decoration: none !important;
        padding: 0.72rem 1rem !important;
        display: inline-block !important;
    }

    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
        background-color: #0F172A !important;
        border: 1px solid #223046 !important;
        border-radius: 10px !important;
        color: white !important;
    }

    div[data-testid="stFileUploader"] {
        background: rgba(15,23,42,0.82);
        border: 1px dashed rgba(59,130,246,0.28);
        border-radius: 16px;
        padding: 10px;
    }

    .sidebar-brand {
        font-size: 1.3rem;
        font-weight: 800;
        color: #F8FAFC;
        margin-bottom: 4px;
    }

    .sidebar-caption {
        color: var(--muted);
        font-size: 0.92rem;
        margin-bottom: 14px;
    }

    .danger-btn button {
        background: linear-gradient(180deg, #B91C1C, #991B1B) !important;
        border-color: rgba(239,68,68,0.22) !important;
    }

    .st-emotion-cache-13ln4jf, .st-emotion-cache-1gulkj5 {
        border-radius: 12px !important;
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


def file_run_key(client_id: str, filename: str, selected_cols: list[str], anomaly_count: int, risk_label: str) -> str:
    raw = f"{client_id}|{filename}|{','.join(selected_cols)}|{anomaly_count}|{risk_label}"
    return hashlib.md5(raw.encode()).hexdigest()


def get_team_members(client_id: str):
    try:
        res = (
            supabase.table("client_members")
            .select("*")
            .eq("client_id", client_id)
            .order("created_at", desc=False)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def invite_team_member(client_id: str, owner_user_id: str, email: str, role: str):
    return (
        supabase.table("client_members")
        .insert(
            {
                "client_id": client_id,
                "owner_user_id": owner_user_id,
                "member_email": email,
                "role": role,
            }
        )
        .execute()
    )


def get_billing_status(user_id: str):
    try:
        res = (
            supabase.table("billing_customers")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        data = res.data or []
        return data[0] if data else None
    except Exception:
        return None


def render_section_start(title: str, subtitle: str = ""):
    st.markdown(
        f"""
        <div class="section-wrap">
            <div class="section-head">
                <div class="section-title">{title}</div>
                {f'<div class="section-subtitle">{subtitle}</div>' if subtitle else ''}
            </div>
            <div class="section-body">
        """,
        unsafe_allow_html=True,
    )


def render_section_end():
    st.markdown("</div></div>", unsafe_allow_html=True)


def render_stack_item(title: str, body: str):
    st.markdown(
        f"""
        <div class="stack-item">
            <div class="stack-title">{title}</div>
            <div class="stack-meta">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================
# AUTH SCREEN
# =========================================
if not st.session_state.logged_in:
    st.markdown('<div class="auth-shell">', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">ProAudit AI</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="auth-subtitle">Modern audit intelligence for collaborative analytics, insights, and export-ready workpapers.</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.15, 1], gap="large")

    with left:
        st.markdown(
            """
            <div class="hero-shell">
                <div class="hero-eyebrow">Trusted workflow for modern audit teams</div>
                <div class="hero-title">Audit Smarter,<br>Not Harder</div>
                <div class="hero-subtitle">
                    Manage client workspaces, detect anomalies, generate GPT-based audit commentary,
                    and export professional reports from a secure, collaboration-ready environment.
                </div>
                <div style="margin-top:18px;">
                    <div class="auth-feature">• Multi-client workspaces</div>
                    <div class="auth-feature">• AI-supported audit analysis</div>
                    <div class="auth-feature">• Team collaboration and billing</div>
                    <div class="auth-feature">• Exportable PDF and Excel reports</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        render_section_start("Account Access", "Sign in or create a workspace account")
        login_tab, signup_tab = st.tabs(["Sign in", "Create account"])

        with login_tab:
            email = st.text_input("Work email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Sign in", use_container_width=True):
                try:
                    result = sign_in_user(email, password)
                    user = getattr(result, "user", None)
                    if user:
                        active_user = set_auth()
                        st.session_state.logged_in = True
                        st.session_state.user_email = getattr(active_user, "email", email) if active_user else getattr(user, "email", email)
                        st.session_state.user_id = getattr(active_user, "id", None) if active_user else getattr(user, "id", None)
                        st.rerun()
                    else:
                        st.error("Sign-in failed.")
                except Exception as e:
                    st.error(f"Sign-in error: {e}")

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
                        st.success("Account created. Verify your email if confirmation is enabled.")
                    except Exception as e:
                        st.error(f"Signup error: {e}")
        render_section_end()

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# refresh auth for RLS
active_user = set_auth()
if not active_user:
    st.warning("Session expired. Please login again.")
    st.session_state.clear()
    st.rerun()

st.session_state.user_email = getattr(active_user, "email", st.session_state.user_email)
st.session_state.user_id = getattr(active_user, "id", st.session_state.user_id)

# =========================================
# SIDEBAR
# =========================================
st.sidebar.markdown('<div class="sidebar-brand">ProAudit AI</div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="sidebar-caption">Audit Intelligence Platform</div>', unsafe_allow_html=True)

page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Anomalies", "Reports", "Team", "Billing"]
)

st.sidebar.markdown("---")
st.sidebar.write(f"Logged in as: **{st.session_state.user_email}**")
st.sidebar.markdown("### Workspace")

clients = get_clients(st.session_state.user_id)

if clients:
    client_map = {c["client_name"]: c["id"] for c in clients}
    selected_names = list(client_map.keys())

    default_index = 0
    if st.session_state.selected_client_name in selected_names:
        default_index = selected_names.index(st.session_state.selected_client_name)

    selected = st.sidebar.selectbox("Client", selected_names, index=default_index)
    st.session_state.selected_client_id = client_map[selected]
    st.session_state.selected_client_name = selected

    col1, col2 = st.sidebar.columns([3, 1])
    with col2:
        if st.button("Delete", key="delete_selected_client"):
            delete_client(st.session_state.selected_client_id)
            st.session_state.selected_client_id = None
            st.session_state.selected_client_name = None
            st.success("Client deleted")
            st.rerun()
else:
    st.sidebar.info("No clients found")

with st.sidebar.expander("Create client", expanded=False):
    name = st.text_input("Name", key="client_name_input")
    ind = st.text_input("Industry", key="client_industry_input")

    if st.button("Add client", key="add_client_btn"):
        if not name.strip():
            st.error("Enter a client name")
        else:
            create_client_db(st.session_state.user_id, name.strip(), ind.strip())
            st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("Logout", key="sidebar_logout"):
    sign_out_user()
    st.session_state.clear()
    st.rerun()

# =========================================
# HEADER
# =========================================
st.markdown('<div class="app-shell">', unsafe_allow_html=True)

top_left, top_right = st.columns([5.2, 1.2], gap="large")
with top_left:
    st.markdown(
        """
        <div class="hero-shell">
            <div class="hero-eyebrow">Real-time audit intelligence for modern firms</div>
            <div class="hero-title">Audit Smarter,<br>Not Harder</div>
            <div class="hero-subtitle">
                Detect anomalies, generate GPT insights, manage collaboration, and produce
                export-ready audit outputs from a single enterprise workspace.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with top_right:
    st.markdown(
        f"""
        <div class="top-user-card">
            <div class="top-user-label">Workspace user</div>
            <div class="top-user-email">{st.session_state.user_email}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

if not st.session_state.selected_client_id and page in ["Dashboard", "Anomalies", "Reports", "Team"]:
    render_section_start("No workspace selected", "Create or select a client from the sidebar to continue")
    st.info("Select a workspace before using analysis, collaboration, or reporting features.")
    render_section_end()
    st.stop()

if st.session_state.selected_client_name:
    st.markdown(
        f"""
        <div class="toolbar-card">
            <div class="toolbar-grid">
                <div class="toolbar-meta">Workspace <span>{st.session_state.selected_client_name}</span></div>
                <div class="toolbar-meta">User <span>{st.session_state.user_email}</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# =========================================
# TEAM PAGE
# =========================================
if page == "Team":
    render_section_start("Team Collaboration", "Manage member access for the selected workspace")
    col1, col2 = st.columns([1.1, 1], gap="large")

    members = get_team_members(st.session_state.selected_client_id)

    with col1:
        st.subheader("Current Members")
        if members:
            for m in members:
                a, b = st.columns([4, 1], gap="small")
                with a:
                    render_stack_item(m["member_email"], f"Role: {m['role']}")
                with b:
                    st.write("")
                    st.write("")
                    if st.button("Remove", key=f"remove_member_{m['id']}"):
                        delete_team_member(m["id"])
                        st.rerun()
        else:
            st.info("No team members added yet.")

    with col2:
        st.subheader("Invite Member")
        invite_email = st.text_input("Email address", key="invite_email")
        invite_role = st.selectbox("Role", ["viewer", "auditor", "admin"], key="invite_role")

        if st.button("Add member", use_container_width=True, key="invite_member_btn"):
            if not invite_email.strip():
                st.error("Enter an email address.")
            else:
                invite_team_member(
                    st.session_state.selected_client_id,
                    st.session_state.user_id,
                    invite_email.strip(),
                    invite_role,
                )
                st.success("Member added")
                st.rerun()

        st.caption("This currently stores collaboration access in the database. Email delivery needs SMTP or auth invite flow.")

    render_section_end()
    st.stop()

# =========================================
# BILLING PAGE
# =========================================
if page == "Billing":
    render_section_start("Billing and Plan", "Workspace subscription and upgrade path")

    billing = get_billing_status(st.session_state.user_id)
    plan_name = billing.get("plan_name", "Free") if billing else "Free"
    plan_status = billing.get("status", "inactive") if billing else "inactive"

    b1, b2 = st.columns([1.05, 1], gap="large")

    with b1:
        render_stack_item("Current Plan", f"Plan: {plan_name}<br>Status: {plan_status}")

    with b2:
        render_stack_item(
            "Upgrade Features",
            "Unlimited audit runs<br>Team collaboration<br>Priority GPT insights<br>Advanced exports"
        )

    if STRIPE_PAYMENT_LINK:
        st.link_button("Upgrade with Stripe", STRIPE_PAYMENT_LINK, use_container_width=True)
    else:
        st.info("Add STRIPE_PAYMENT_LINK to Streamlit secrets to enable hosted checkout.")

    render_section_end()
    st.stop()

# =========================================
# FILE UPLOAD
# =========================================
render_section_start("Upload Financial Data", "Start a new analysis run for the selected workspace")
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])
render_section_end()

if not uploaded_file:
    recent_runs = get_recent_runs(st.session_state.user_id, st.session_state.selected_client_id)

    c1, c2 = st.columns(2, gap="large")

    with c1:
        render_section_start("Client Overview", "Selected workspace summary")
        st.markdown(
            f"""
            <div class="small-muted">
            Current client: <b>{st.session_state.selected_client_name}</b><br>
            Upload a CSV file to begin analysis for this workspace.
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_section_end()

    with c2:
        render_section_start("Recent Activity", "Latest saved audit runs")
        if recent_runs:
            for run in recent_runs[:5]:
                render_stack_item(
                    run.get("file_name", "Unknown file"),
                    f"Risk: {run.get('risk_label', 'N/A')} • {run.get('anomaly_count', 0)} anomalies",
                )
        else:
            st.info("Upload a CSV to start audit analysis for this workspace.")
        render_section_end()

    render_section_start("Financial Trends", "Charts will appear after data upload")
    st.info("Upload a dataset to visualize trend and anomaly behavior.")
    render_section_end()
    st.stop()

# =========================================
# DATA PROCESSING
# =========================================
df = pd.read_csv(uploaded_file)
df = clean_dataframe(df)
df = safe_date_column(df)
df = df.sort_values(by="Date")

render_section_start("Select Financial Metrics", "Choose the columns to analyze")
numeric_cols = df.select_dtypes(include="number").columns.tolist()
if len(numeric_cols) == 0:
    st.error("No numeric columns found in this dataset.")
    render_section_end()
    st.stop()

default_metrics = numeric_cols[:2] if len(numeric_cols) >= 2 else numeric_cols[:1]
selected_cols = st.multiselect(
    "Choose one or more numeric columns to analyze",
    numeric_cols,
    default=default_metrics,
)
if len(selected_cols) == 0:
    st.warning("Please select at least one metric.")
    render_section_end()
    st.stop()
render_section_end()

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

current_run_key = file_run_key(
    st.session_state.selected_client_id,
    uploaded_file.name,
    selected_cols,
    len(anomalies),
    risk_label,
)

if st.session_state.last_saved_run_key != current_run_key:
    try:
        save_audit(
            st.session_state.user_id,
            st.session_state.selected_client_id,
            uploaded_file.name,
            ", ".join(selected_cols),
            len(anomalies),
            risk_label,
        )
        st.session_state.last_saved_run_key = current_run_key
    except Exception as e:
        st.warning(f"Run not saved: {e}")

st.markdown(
    """
    <div class="status-pill">
        Analysis Ready
    </div>
    """,
    unsafe_allow_html=True,
)

m1, m2, m3, m4 = st.columns(4, gap="medium")
with m1:
    st.markdown(
        f"""
        <div class="metric-box">
            <div class="metric-label">Records</div>
            <div class="metric-value">{len(df):,}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with m2:
    st.markdown(
        f"""
        <div class="metric-box">
            <div class="metric-label">Anomalies</div>
            <div class="metric-value">{len(anomalies):,}</div>
            <div class="metric-note">{'Elevated risk' if len(anomalies) > 10 else 'Under control'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with m3:
    st.markdown(
        f"""
        <div class="metric-box">
            <div class="metric-label">Metrics Selected</div>
            <div class="metric-value">{len(selected_cols)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with m4:
    st.markdown(
        f"""
        <div class="metric-box">
            <div class="metric-label">Risk Level</div>
            <div class="metric-value">{risk_label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# =========================================
# DASHBOARD
# =========================================
if page == "Dashboard":
    d1, d2 = st.columns([1.05, 1], gap="large")

    with d1:
        render_section_start("Dataset Preview", "Source rows loaded for analysis")
        st.dataframe(df.head(12), use_container_width=True)
        render_section_end()

    with d2:
        render_section_start("Workspace Summary", "Active file and selection context")
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
        render_section_end()

    i1, i2 = st.columns(2, gap="large")
    with i1:
        render_section_start("Key Insights", "High-level interpretation of the current run")
        highest_metric = selected_cols[0] if selected_cols else "N/A"
        st.markdown(
            f"""
            <div class="small-muted">
            Total anomalies detected: <b>{len(anomalies)}</b><br>
            Highest focus metric: <b>{highest_metric}</b><br>
            Risk level: <b>{risk_label}</b><br>
            Workspace: <b>{st.session_state.selected_client_name}</b>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_section_end()

    with i2:
        render_section_start("Recent Activity", "Most recent saved audit runs")
        recent_runs = get_recent_runs(st.session_state.user_id, st.session_state.selected_client_id)
        if recent_runs:
            for run in recent_runs[:5]:
                render_stack_item(
                    run.get("file_name", "Unknown file"),
                    f"Risk: {run.get('risk_label', 'N/A')} • {run.get('anomaly_count', 0)} anomalies"
                )
        else:
            st.info("No saved runs yet.")
        render_section_end()

    render_section_start("Financial Trend Analysis", "Trend comparison across selected metrics")
    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor("#0B1220")
    ax.set_facecolor("#111827")
    colors = ["#2563EB", "#06B6D4", "#22C55E", "#F59E0B", "#EF4444", "#8B5CF6"]

    for i, col in enumerate(selected_cols):
        ax.plot(df["Date"], df[col], linewidth=2.3, color=colors[i % len(colors)], label=col)

    ax.legend(facecolor="#111827", edgecolor="#374151", labelcolor="white")
    ax.set_title("Metric Trends Over Time", color="white", fontsize=14)
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("#374151")
    st.pyplot(fig, use_container_width=True)
    render_section_end()

# =========================================
# ANOMALIES
# =========================================
elif page == "Anomalies":
    a1, a2 = st.columns([1.3, 0.95], gap="large")

    with a1:
        render_section_start("Detected Anomalies", "Flagged outliers based on z-score threshold")
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
            ax.plot(df["Date"], df[metric_choice], label=metric_choice, linewidth=2.4, color="#2563EB")

            if not metric_anomalies.empty:
                ax.scatter(metric_anomalies["Date"], metric_anomalies["Value"], label="Anomalies", s=60, color="#EF4444")

            ax.legend(facecolor="#111827", edgecolor="#374151", labelcolor="white")
            ax.set_title(f"{metric_choice} - Trend and Anomalies", color="white", fontsize=14)
            ax.tick_params(colors="white")
            for spine in ax.spines.values():
                spine.set_color("#374151")
            st.pyplot(fig, use_container_width=True)
        render_section_end()

    with a2:
        render_section_start("GPT Audit Insight", "AI-generated commentary for the selected anomaly focus")
        if anomalies.empty:
            st.info("Upload data with anomalies to generate AI insight.")
        else:
            metric_choice = st.selectbox("AI metric focus", selected_cols, key="ai_metric_focus")
            metric_anomalies = anomalies[anomalies["Metric"] == metric_choice]
            insight_row = metric_anomalies.iloc[0] if not metric_anomalies.empty else anomalies.iloc[0]

            try:
                with st.spinner("Generating GPT audit insight..."):
                    ai_text = generate_ai_insight(
                        metric_name=insight_row["Metric"],
                        metric_value=insight_row["Value"],
                        z_score_value=insight_row["Z_Score"],
                    )
                st.session_state.last_ai_text = ai_text

                render_stack_item("AI Commentary", ai_text.replace("\n", "<br>"))

                pdf_bytes = create_pdf_report(
                    username=st.session_state.user_email or "Unknown User",
                    client_name=st.session_state.selected_client_name or "Unknown Client",
                    ai_text=ai_text,
                    selected_metric=insight_row["Metric"],
                    anomaly_value=insight_row["Value"],
                    anomaly_zscore=insight_row["Z_Score"],
                )

                st.download_button(
                    "Download Audit Report (PDF)",
                    data=pdf_bytes,
                    file_name=f"{st.session_state.selected_client_name}_audit_report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"AI Error: {e}")
        render_section_end()

        render_section_start("Audit Assistant", "Ask questions about the uploaded dataset and risk profile")
        for msg in st.session_state.chat_history:
            role = "You" if msg["role"] == "user" else "ProAudit AI"
            st.markdown(f"**{role}:** {msg['content']}")

        question = st.text_area("Question", height=100)

        if st.button("Ask Assistant", use_container_width=True):
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
        render_section_end()

# =========================================
# REPORTS
# =========================================
elif page == "Reports":
    render_section_start("Export Reports", "Download structured outputs for audit documentation")

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
        "Download Excel Workpaper",
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
        st.info("Use the Anomalies page to generate and download the AI PDF report.")

    render_section_end()