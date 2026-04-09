import os
import streamlit as st
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL", st.secrets.get("SUPABASE_URL", ""))
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", st.secrets.get("SUPABASE_ANON_KEY", ""))

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_ANON_KEY in environment/secrets.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def set_auth():
    session = supabase.auth.get_session()
    if session and getattr(session, "access_token", None):
        supabase.postgrest.auth(session.access_token)
        user_res = supabase.auth.get_user()
        return getattr(user_res, "user", None)
    return None


def sign_up_user(email: str, password: str):
    return supabase.auth.sign_up({"email": email, "password": password})


def sign_in_user(email: str, password: str):
    return supabase.auth.sign_in_with_password({"email": email, "password": password})


def sign_out_user():
    return supabase.auth.sign_out()


def get_clients(user_id: str):
    if not user_id:
        return []
    res = (
        supabase.table("clients")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
    )
    return res.data or []


def create_client_db(user_id: str, client_name: str, industry: str):
    if not user_id:
        raise ValueError("Missing user_id")
    return (
        supabase.table("clients")
        .insert(
            {
                "user_id": user_id,
                "client_name": client_name,
                "industry": industry,
            }
        )
        .execute()
    )


def save_audit(user_id: str, client_id: str, file_name: str, metrics: str, anomaly_count: int, risk_label: str):
    if not user_id or not client_id:
        raise ValueError("Missing user_id or client_id")
    return (
        supabase.table("audit_runs")
        .insert(
            {
                "user_id": user_id,
                "client_id": client_id,
                "file_name": file_name,
                "selected_metrics": metrics,
                "anomaly_count": anomaly_count,
                "risk_label": risk_label,
            }
        )
        .execute()
    )


def get_recent_runs(user_id: str, client_id: str | None = None):
    if not user_id:
        return []
    query = (
        supabase.table("audit_runs")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
    )
    if client_id:
        query = query.eq("client_id", client_id)
    res = query.limit(8).execute()
    return res.data or []