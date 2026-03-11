"""
pages/01_karte.py — Interaktive Karte mit Sidebar-Filter
"""
import streamlit as st
import pandas as pd
from streamlit_folium import st_folium
from utils.db import load_standorte, load_firmen
from utils.map_utils import make_map
from utils.scoring import STATUS_COLOR, STATUS_EMOJI, schwachstellen

# ── Sidebar: WAS-Header ───────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="was-sidebar-header">
      <div class="was-eyebrow">Wirtschaftsatlas 2026</div>
      <div class="was-title">Mobilitätsatlas Stormarn</div>
      <div class="was-sub">ÖPNV-Erreichbarkeit · v1.0</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**Filter**")

    # Status-Filter
    status_filter = st.multiselect(
        "ÖPNV-Qualität",
        options=["grün", "gelb", "rot"],
        default=["grün", "gelb", "rot"],
        format_func=lambda x: f"{STATUS_EMOJI[x]} {'Gut' if x=='grün' else 'Eingeschränkt' if x=='gelb' else 'Unterversorgt'}",
    )

    # Freitext-Suche
    suche = st.text_input("🔍 Suchen", placeholder="Standort oder Stadt…")

    st.divider()

    # Daten laden
    standorte_raw = load_standorte()
    df_all = pd.DataFrame(standorte_raw)

    if df_all.empty:
        st.warning("Keine Standorte in der Datenbank. Bitte zuerst Daten importieren.")
        st.stop()

    # Gewerbegebiet-Dropdown
    orte = sorted(df_all["name"].dropna().unique().tolist())
    ort_filter = st.selectbox("Gewerbegebiet", ["— Alle —"] + orte)

    # Stadtfilter
    staedte = sorted(df_all["ort"].dropna().unique().tolist())
    stadt_filter = st.selectbox("Stadt", ["— Alle —"] + staedte)

    # Größenfilter
    groesse_filter = st.selectbox("Größe (Beschäftigte)", [
        "— Alle —", "≥ 2000", "1000–2000", "400–999", "< 400"
    ])

    # Score-Filter
    score_filter = st.selectbox("Score", ["— Alle —", "A", "B", "C", "D"])

    st.divider()

    # Firmen-Layer toggle
    show_firmen = st.toggle("🏭 Unternehmen einblenden", value=False)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:10px;color:#9ca3af;line-height:1.6">
    🟢 Gut &nbsp; 🟡 Eingeschränkt &nbsp; 🔴 Unterversorgt<br>
    Quelle: RNVP Stormarn 2022 · NAH.SH GTFS
    </div>
    """, unsafe_allow_html=True)

# ── Daten filtern ─────────────────────────────────────────
df = df_all.copy()

if status_filter:
    df = df[df["status"].isin(status_filter)]
if suche:
    q = suche.lower()
    df = df[df["name"].str.lower().str.contains(q, na=False) |
            df["ort"].str.lower().str.contains(q, na=False)]
if ort_filter != "— Alle —":
    df = df[df["name"] == ort_filter]
if stadt_filter != "— Alle —":
    df = df[df["ort"] == stadt_filter]
if score_filter != "— Alle —":
    df = df[df["score"].str.startswith(score_filter, na=False)]

# Größenfilter
if groesse_filter != "— Alle —":
    def parse_besch(b):
        try: return int(str(b).replace(".", "").replace(",", "").replace(" ", "").split("–")[0])
        except: return 0
    df["_b"] = df["beschaeftigte"].apply(parse_besch)
    if groesse_filter == "≥ 2000":    df = df[df["_b"] >= 2000]
    elif groesse_filter == "1000–2000": df = df[(df["_b"] >= 1000) & (df["_b"] < 2000)]
    elif groesse_filter == "400–999":   df = df[(df["_b"] >= 400)  & (df["_b"] < 1000)]
    elif groesse_filter == "< 400":     df = df[df["_b"] < 400]

standorte = df.to_dict("records")

# ── Haupt-Layout ──────────────────────────────────────────
st.markdown(f"### 🗺 Karte · {len(standorte)} Standorte")

# KPI-Zeile
c1, c2, c3, c4 = st.columns(4)
gruen = len(df[df["status"] == "grün"])
gelb  = len(df[df["status"] == "gelb"])
rot   = len(df[df["status"] == "rot"])
gesamt_fa = int(df["fahrten_tag"].fillna(0).sum())

c1.metric("🟢 Gut angebunden",  gruen)
c2.metric("🟡 Eingeschränkt",   gelb)
c3.metric("🔴 Unterversorgt",   rot)
c4.metric("🚌 Fahrten gesamt",  gesamt_fa)

# Karte + Liste nebeneinander
map_col, list_col = st.columns([3, 1])

with map_col:
    firmen = load_firmen() if show_firmen else None
    m = make_map(standorte, firmen)
    map_data = st_folium(m, height=580, use_container_width=True, returned_objects=["last_object_clicked"])

with list_col:
    st.markdown(f"**{len(standorte)} Standorte**")

    # Sortierung
    sort_by = st.selectbox("Sortieren nach", ["Score", "Fahrten/Tag", "Name"], label_visibility="collapsed")

    if sort_by == "Score":
        score_order = {"A":0,"B+":1,"B":2,"C+":3,"C":4,"C−":5,"D+":6,"D":7,"D−":8}
        df_sorted = df.copy()
        df_sorted["_so"] = df_sorted["score"].map(score_order).fillna(9)
        df_sorted = df_sorted.sort_values("_so")
        standorte_sorted = df_sorted.to_dict("records")
    elif sort_by == "Fahrten/Tag":
        standorte_sorted = sorted(standorte, key=lambda x: x.get("fahrten_tag") or 0, reverse=True)
    else:
        standorte_sorted = sorted(standorte, key=lambda x: x.get("name",""))

    for s in standorte_sorted:
        status = s.get("status","rot")
        color  = STATUS_COLOR.get(status, "#dc2626")
        score  = s.get("score","?")
        fa     = s.get("fahrten_tag", 0)
        issues = schwachstellen(s)
        issue_html = " ".join([f'<span style="font-size:9px;background:#f0f2f5;border-radius:3px;padding:1px 5px;color:#6b7280">{i}</span>' for i in issues])

        st.markdown(f"""
        <div class="ge-card">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
            <div style="width:4px;height:40px;border-radius:3px;background:{color};flex-shrink:0"></div>
            <div style="flex:1;min-width:0">
              <div class="ge-card-name" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{s.get('name','')}</div>
              <div class="ge-card-meta">{s.get('ort','')} · {fa} Fahrten/Tag</div>
              <div style="margin-top:4px">{issue_html}</div>
            </div>
            <div style="text-align:right;flex-shrink:0">
              <div style="font-size:18px;font-weight:700;color:{color};font-family:'IBM Plex Mono'">{score}</div>
              <div style="font-size:11px;color:#6b7280">{s.get('trend','=')}</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)
