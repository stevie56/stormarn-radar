"""
utils/db.py — Supabase Datenbankverbindung
"""
import os
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

@st.cache_resource
def get_client() -> Client:
    url  = os.getenv("SUPABASE_URL")  or st.secrets.get("SUPABASE_URL", "")
    key  = os.getenv("SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        st.error("⚠ Supabase-Zugangsdaten fehlen. Bitte .env oder st.secrets konfigurieren.")
        st.stop()
    return create_client(url, key)

# ── Standorte ────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_standorte() -> list[dict]:
    db = get_client()
    res = db.table("standorte").select("*").order("name").execute()
    return res.data or []

@st.cache_data(ttl=60)
def load_firmen() -> list[dict]:
    db = get_client()
    res = db.table("firmen").select("*").order("name").execute()
    return res.data or []

@st.cache_data(ttl=60)
def load_haltestellen() -> list[dict]:
    db = get_client()
    res = db.table("haltestellen").select("*").execute()
    return res.data or []

@st.cache_data(ttl=60)
def load_massnahmen() -> list[dict]:
    db = get_client()
    res = db.table("massnahmen").select("*").order("created_at", desc=True).execute()
    return res.data or []

@st.cache_data(ttl=300)
def load_snapshots(standort_name: str | None = None) -> list[dict]:
    db = get_client()
    q = db.table("score_snapshots").select("*").order("snapshot_date")
    if standort_name:
        q = q.eq("standort_name", standort_name)
    return q.execute().data or []

@st.cache_data(ttl=60)
def load_feedback() -> list[dict]:
    db = get_client()
    res = db.table("feedback").select("*").order("created_at", desc=True).execute()
    return res.data or []

# ── Schreiben ─────────────────────────────────────────────
def upsert_standort(data: dict):
    db = get_client()
    db.table("standorte").upsert(data, on_conflict="name").execute()
    st.cache_data.clear()

def insert_feedback(data: dict):
    db = get_client()
    db.table("feedback").insert(data).execute()

def upsert_massnahme(data: dict):
    db = get_client()
    if data.get("id"):
        db.table("massnahmen").update(data).eq("id", data["id"]).execute()
    else:
        db.table("massnahmen").insert(data).execute()
    st.cache_data.clear()

def save_snapshot(standort_name: str, score: str, status: str, fahrten: int, gtfs_version: str = ""):
    db = get_client()
    db.table("score_snapshots").insert({
        "standort_name": standort_name,
        "score": score,
        "status": status,
        "fahrten_tag": fahrten,
        "gtfs_version": gtfs_version,
    }).execute()
    st.cache_data.clear()
