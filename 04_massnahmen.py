"""
pages/04_massnahmen.py — Maßnahmen-Tracker
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.db import load_massnahmen, load_standorte, upsert_massnahme

st.title("⚡ Maßnahmen-Tracker")
st.markdown("Verfolgt den Status aller ÖPNV-Maßnahmen von *offen* bis *umgesetzt*.")

massnahmen = load_massnahmen()
standorte  = load_standorte()
standort_namen = ["—"] + sorted([s["name"] for s in standorte])

# ── Kanban-Board ──────────────────────────────────────────
STATUS_COLS = {
    "offen":         ("📋 Offen",         "#fee2e2", "#dc2626"),
    "in_bearbeitung":("🔄 In Bearbeitung", "#fef9c3", "#d97706"),
    "beschlossen":   ("✅ Beschlossen",    "#dcfce7", "#16a34a"),
    "umgesetzt":     ("🏆 Umgesetzt",      "#dbeafe", "#2563eb"),
}

df = pd.DataFrame(massnahmen) if massnahmen else pd.DataFrame()

# KPIs
c1, c2, c3, c4 = st.columns(4)
for (st_key, (lbl, bg, fg)), col in zip(STATUS_COLS.items(), [c1, c2, c3, c4]):
    n = len(df[df["status"] == st_key]) if not df.empty else 0
    col.metric(lbl, n)

st.divider()

tab_board, tab_neu, tab_charts = st.tabs(["📋 Board", "➕ Neue Maßnahme", "📊 Auswertung"])

# ══════════════════════════════════════════════════════════
# KANBAN BOARD
# ══════════════════════════════════════════════════════════
with tab_board:
    if df.empty:
        st.info("Noch keine Maßnahmen erfasst.")
    else:
        # Filter
        f_col1, f_col2, f_col3 = st.columns(3)
        flt_kat  = f_col1.selectbox("Kategorie", ["Alle","Linie","Takt","Haltestelle","Rad","Sonstiges"])
        flt_prio = f_col2.selectbox("Priorität", ["Alle","hoch","mittel","niedrig"])
        flt_ge   = f_col3.selectbox("Standort", ["Alle"] + standort_namen[1:])

        df_f = df.copy()
        if flt_kat  != "Alle": df_f = df_f[df_f["kategorie"] == flt_kat]
        if flt_prio != "Alle": df_f = df_f[df_f["prioritaet"] == flt_prio]
        if flt_ge   != "Alle": df_f = df_f[df_f["standort_name"] == flt_ge]

        cols = st.columns(4)
        prio_colors = {"hoch":"#dc2626","mittel":"#d97706","niedrig":"#6b7280"}

        for (st_key, (lbl, bg, fg)), col in zip(STATUS_COLS.items(), cols):
            with col:
                st.markdown(f"**{lbl}**")
                subset = df_f[df_f["status"] == st_key]
                if subset.empty:
                    st.markdown(f'<div style="padding:12px;border:1px dashed #dde1e7;border-radius:8px;color:#9ca3af;font-size:11px;text-align:center">Keine Einträge</div>', unsafe_allow_html=True)
                for _, row in subset.iterrows():
                    prio_col = prio_colors.get(row.get("prioritaet","niedrig"),"#6b7280")
                    kosten = f"€ {row['kosten_euro']:,.0f}" if row.get("kosten_euro") else "—"
                    st.markdown(f"""
                    <div style="background:{bg};border:1px solid {fg}33;border-left:4px solid {fg};
                                border-radius:8px;padding:10px 12px;margin-bottom:8px">
                      <div style="font-weight:700;font-size:12px;color:#111827;margin-bottom:4px">{row.get('titel','')}</div>
                      <div style="font-size:10px;color:#6b7280;margin-bottom:6px">{row.get('standort_name','') or '—'}</div>
                      <div style="display:flex;gap:5px;flex-wrap:wrap">
                        <span style="font-size:9px;background:{prio_col}22;color:{prio_col};border:1px solid {prio_col}44;
                                     border-radius:3px;padding:1px 6px;font-weight:600">{row.get('prioritaet','')}</span>
                        <span style="font-size:9px;background:#f0f2f5;color:#6b7280;border-radius:3px;padding:1px 6px">{row.get('kategorie','')}</span>
                        <span style="font-size:9px;background:#f0f2f5;color:#6b7280;border-radius:3px;padding:1px 6px">{kosten}</span>
                      </div>
                    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# NEUE MASSNAHME
# ══════════════════════════════════════════════════════════
with tab_neu:
    with st.form("massnahme_form"):
        st.subheader("Neue Maßnahme erfassen")

        titel = st.text_input("Titel*", placeholder="z.B. Neue Buslinie 1234 GE Reinbek-Süd")
        st_name = st.selectbox("Gewerbestandort", standort_namen)
        c1, c2 = st.columns(2)
        kat  = c1.selectbox("Kategorie", ["Linie","Takt","Haltestelle","Rad","Sonstiges"])
        prio = c2.selectbox("Priorität", ["hoch","mittel","niedrig"])
        c3, c4 = st.columns(2)
        akteur  = c3.text_input("Zuständiger Akteur", placeholder="z.B. NAH.SH, FD52, WAS")
        kosten  = c4.number_input("Kosten €/Jahr (Schätzung)", min_value=0, step=10000)
        beschr  = st.text_area("Beschreibung", height=80)
        deadline = st.date_input("Zieldatum", value=None)

        submit = st.form_submit_button("➕ Maßnahme speichern", use_container_width=True)
        if submit:
            if not titel:
                st.error("Titel ist Pflichtfeld.")
            else:
                upsert_massnahme({
                    "titel":         titel,
                    "standort_name": None if st_name == "—" else st_name,
                    "kategorie":     kat,
                    "prioritaet":    prio,
                    "akteur":        akteur or None,
                    "kosten_euro":   int(kosten) if kosten else None,
                    "beschreibung":  beschr or None,
                    "deadline":      str(deadline) if deadline else None,
                    "status":        "offen",
                })
                st.success("✅ Maßnahme gespeichert!")
                st.rerun()

# ══════════════════════════════════════════════════════════
# AUSWERTUNG
# ══════════════════════════════════════════════════════════
with tab_charts:
    if df.empty:
        st.info("Keine Daten.")
    else:
        c1, c2 = st.columns(2)

        # Status-Donut
        status_df = df["status"].value_counts().reset_index()
        status_df.columns = ["status","count"]
        lbl_map = {"offen":"Offen","in_bearbeitung":"In Bearbeitung",
                   "beschlossen":"Beschlossen","umgesetzt":"Umgesetzt"}
        status_df["label"] = status_df["status"].map(lbl_map)
        col_map = {"offen":"#dc2626","in_bearbeitung":"#d97706",
                   "beschlossen":"#16a34a","umgesetzt":"#2563eb"}
        fig1 = px.pie(status_df, names="label", values="count",
                      color="status", color_discrete_map=col_map,
                      title="Maßnahmen nach Status", hole=0.5)
        fig1.update_layout(height=300, margin=dict(t=40,b=10))
        c1.plotly_chart(fig1, use_container_width=True)

        # Kosten nach Kategorie
        kosten_df = df.groupby("kategorie")["kosten_euro"].sum().reset_index()
        fig2 = px.bar(kosten_df, x="kategorie", y="kosten_euro",
                      color_discrete_sequence=["#003064"],
                      title="Geschätzte Kosten nach Kategorie",
                      labels={"kosten_euro":"€/Jahr","kategorie":"Kategorie"})
        fig2.update_layout(height=300, plot_bgcolor="#fff", paper_bgcolor="#fff",
                           margin=dict(t=40,b=10))
        c2.plotly_chart(fig2, use_container_width=True)
