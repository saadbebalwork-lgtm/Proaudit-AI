import os
import streamlit as st
from supabase import create_client, Client

# =========================
# CONFIG
# =========================
SUPABASE_URL = os.getenv("SUPABASE_URL", st.secrets.get("SUPABASE_URL", ""))
SUPABASE_KEY = os.getenv("SUPABASE_KEY", st.secrets.get("SUPABASE_KEY", ""))  # anon key
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", st.secrets.get("SUPABASE_SERVICE_KEY", ""))  # 🔥 required for invites

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY.")

if not SUPABASE_SERVICE_KEY:
    raise ValueError("Missing SUPABASE_SERVICE_KEY (needed for team invites).")

# ✅ Public client (used everywhere)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🔥 Admin client (used ONLY for secure operations like invite)
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# =========================
# AUTH
# =========================
def set_auth():
    try:
        session_response = supabase.auth.get_session()
        session = getattr(session_response, "session", None) or session_response

        if session and getattr(session, "access_token", None):
            try:
                supabase.postgrest.auth(session.access_token)
            except Exception:
                pass

            user_res = supabase.auth.get_user()
            return getattr(user_res, "user", None)

    except Exception:
        return None

    return None


def sign_up_user(email, password):
    return supabase.auth.sign_up(
        {
            "email": email,
            "password": password,
        }
    )


def sign_in_user(email, password):
    return supabase.auth.sign_in_with_password(
        {
            "email": email,
            "password": password,
        }
    )


def sign_out_user():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass


# =========================
# CLIENTS
# =========================
def get_clients(user_id):
    try:
        res = (
            supabase.table("clients")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def create_client_db(user_id, name, industry):
    return (
        supabase.table("clients")
        .insert(
            {
                "user_id": user_id,
                "client_name": name,
                "industry": industry,
            }
        )
        .execute()
    )


def delete_client(client_id):
    return (
        supabase.table("clients")
        .delete()
        .eq("id", client_id)
        .execute()
    )


# =========================
# AUDIT RUNS
# =========================
def save_audit(user_id, client_id, file_name, selected_metrics, anomaly_count, risk_label):
    return (
        supabase.table("audit_runs")
        .insert(
            {
                "user_id": user_id,
                "client_id": client_id,
                "file_name": file_name,
                "selected_metrics": selected_metrics,
                "anomaly_count": anomaly_count,
                "risk_label": risk_label,
            }
        )
        .execute()
    )


def get_recent_runs(user_id, client_id=None):
    try:
        query = (
            supabase.table("audit_runs")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
        )

        if client_id:
            query = query.eq("client_id", client_id)

        res = query.limit(10).execute()
        return res.data or []

    except Exception:
        return []


# =========================
# TEAM MEMBERS
# =========================
def get_team_members(client_id):
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


def invite_team_member(client_id, owner_user_id, email, role):
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


# 🔥 REAL EMAIL INVITE (IMPORTANT)
def invite_user_by_email(email):
    try:
        return supabase_admin.auth.admin.invite_user_by_email(email)
    except Exception as e:
        raise Exception(f"Invite failed: {e}")


def delete_team_member(member_id):
    return (
        supabase.table("client_members")
        .delete()
        .eq("id", member_id)
        .execute()
    )


# =========================
# BILLING
# =========================
def get_billing_status(user_id):
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


def update_billing(user_id, plan_name, status):
    return (
        supabase.table("billing_customers")
        .upsert(
            {
                "user_id": user_id,
                "plan_name": plan_name,
                "status": status,
            }
        )
        .execute()
    )