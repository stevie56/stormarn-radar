"""
pages/02_analyse.py — Analyse · Charts · Benchmarks
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.db import load_standorte, load_snapshots
from utils.scoring import STATUS_COLOR

WAS_BLUE   = "#003064"
WAS_ORANGE = "#f29400"

st.title("📊 Analyse · Kreisgesamtbild")

standorte = load_standorte()
if not standorte:
    st.warning("Keine Daten vorhanden.")
    st.stop()

df = pd.DataFrame(standorte)

# ── Tab-Navigation ────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Übersicht", "🏆 Benchmark", "⏱ Score-Verlauf", "💰 Kosten-Nutzen"
])

# ══════════════════════════════════════════════════════════
# TAB 1 · ÜBERSICHT
# ══════════════════════════════════════════════════════════
with tab1:
    st.subheader("Versorgungsquoten Kreis Stormarn")

    c1, c2, c3 = st.columns(3)

    # Donut: Status-Verteilung
    status_counts = df["status"].value_counts().reset_index()
    status_counts.columns = ["status", "count"]
    status_counts["label"] = status_counts["status"].map({
        "grün": "Gut angebunden", "gelb": "Eingeschränkt", "rot": "Unterversorgt"
    })
    farben = [STATUS_COLOR.get(s, "#888") for s in status_counts["status"]]

    fig_donut = go.Figure(go.Pie(
        labels=status_counts["label"],
        values=status_counts["count"],
        hole=0.55,
        marker_colors=farben,
        textinfo="percent+label",
        textfont_size=11,
    ))
    fig_donut.update_layout(
        showlegend=False, margin=dict(t=20,b=20,l=10,r=10),
        height=260,
        annotations=[dict(text=f"<b>{len(df)}</b><br>GE", x=0.5, y=0.5,
                          font_size=14, showarrow=False)]
    )
    c1.plotly_chart(fig_donut, use_container_width=True)

    # Score-Verteilung
    score_order = ["A","B+","B","C+","C","C−","D+","D","D−"]
    score_counts = df["score"].value_counts().reindex(score_order, fill_value=0).reset_index()
    score_counts.columns = ["score", "count"]
    score_counts["color"] = score_counts["score"].apply(
        lambda s: "#16a34a" if s in ["A","B+","B"] else "#d97706" if s in ["C+","C","C−"] else "#dc2626"
    )

    fig_scores = px.bar(
        score_counts, x="score", y="count",
        color="color", color_discrete_map="identity",
        labels={"score":"Score","count":"Anzahl"},
        title="Score-Verteilung",
    )
    fig_scores.update_layout(showlegend=False, height=260,
                              margin=dict(t=40,b=20,l=10,r=10),
                              plot_bgcolor="#fff", paper_bgcolor="#fff")
    c2.plotly_chart(fig_scores, use_container_width=True)

    # Fahrten/Tag Histogram
    fig_fa = px.histogram(
        df, x="fahrten_tag", nbins=15,
        title="Fahrten/Tag Verteilung",
        color_discrete_sequence=[WAS_BLUE],
        labels={"fahrten_tag":"Fahrten/Tag"},
    )
    fig_fa.update_layout(height=260, margin=dict(t=40,b=20,l=10,r=10),
                         plot_bgcolor="#fff", paper_bgcolor="#fff")
    c3.plotly_chart(fig_fa, use_container_width=True)

    st.divider()

    # Tabelle: alle Standorte
    st.subheader("Alle Standorte")
    display_cols = ["name","ort","status","score","trend","fahrten_tag",
                    "beschaeftigte","daten_stand"]
    df_show = df[[c for c in display_cols if c in df.columns]].copy()
    df_show.columns = ["Name","Ort","Status","Score","Trend",
                       "Fahrten/Tag","Beschäftigte","Datenstand"][:len(df_show.columns)]

    def color_status(val):
        c = {"Gut angebunden":"background-color:#dcfce7",
             "grün":"background-color:#dcfce7",
             "gelb":"background-color:#fef9c3",
             "Eingeschränkt":"background-color:#fef9c3",
             "rot":"background-color:#fee2e2",
             "Unterversorgt":"background-color:#fee2e2"}.get(val,"")
        return c

    st.dataframe(
        df_show.style.applymap(color_status, subset=["Status"] if "Status" in df_show.columns else []),
        use_container_width=True, height=420,
    )

    # CSV-Export
    csv = df_show.to_csv(index=False).encode("utf-8")
    st.download_button("⬇ CSV exportieren", csv, "standorte.csv", "text/csv")


# ══════════════════════════════════════════════════════════
# TAB 2 · BENCHMARK
# ══════════════════════════════════════════════════════════
with tab2:
    st.subheader("Benchmark · Top & Flop Standorte")

    score_order_map = {"A":20,"B+":17,"B":15,"C+":13,"C":11,"C−":9,"D+":7,"D":5,"D−":3}
    df["_pts"] = df["score"].map(score_order_map).fillna(0)

    col_top, col_flop = st.columns(2)

    with col_top:
        st.markdown("**🏆 Top 10 · Beste Anbindung**")
        top10 = df.nlargest(10, "_pts")[["name","ort","score","fahrten_tag"]]
        for _, r in top10.iterrows():
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;padding:7px 10px;
                        border-radius:7px;border:1px solid #dde1e7;margin-bottom:5px;background:#fff">
              <div style="font-size:16px;font-weight:700;color:#16a34a;
                          font-family:'IBM Plex Mono';min-width:32px">{r['score']}</div>
              <div style="flex:1;min-width:0">
                <div style="font-weight:600;font-size:12px;color:#003064;
                            white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{r['name']}</div>
                <div style="font-size:10px;color:#6b7280">{r['ort']} · {r['fahrten_tag']} Fahr./Tag</div>
              </div>
            </div>""", unsafe_allow_html=True)

    with col_flop:
        st.markdown("**⚠ Flop 10 · Höchster Handlungsbedarf**")
        flop10 = df.nsmallest(10, "_pts")[["name","ort","score","fahrten_tag"]]
        for _, r in flop10.iterrows():
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;padding:7px 10px;
                        border-radius:7px;border:1px solid #fca5a5;margin-bottom:5px;background:#fff8f8">
              <div style="font-size:16px;font-weight:700;color:#dc2626;
                          font-family:'IBM Plex Mono';min-width:32px">{r['score']}</div>
              <div style="flex:1;min-width:0">
                <div style="font-weight:600;font-size:12px;color:#003064;
                            white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{r['name']}</div>
                <div style="font-size:10px;color:#6b7280">{r['ort']} · {r['fahrten_tag']} Fahr./Tag</div>
              </div>
            </div>""", unsafe_allow_html=True)

    st.divider()

    # Scatter: Beschäftigte vs. Score
    st.subheader("Beschäftigte vs. Score-Punkte")

    def parse_b(b):
        try: return int(str(b).replace(".","").replace(",","").replace(" ","").split("–")[0])
        except: return 0

    df["_besch"] = df["beschaeftigte"].apply(parse_b)
    fig_scatter = px.scatter(
        df, x="_besch", y="_pts",
        color="status",
        color_discrete_map={"grün":"#16a34a","gelb":"#d97706","rot":"#dc2626"},
        hover_name="name",
        hover_data={"_besch":True,"_pts":True,"score":True,"ort":True},
        labels={"_besch":"Beschäftigte","_pts":"Score-Punkte","status":"Status"},
        title="Je mehr Beschäftigte & je schlechter Score → höchster Handlungsdruck",
        size="_besch", size_max=30,
    )
    fig_scatter.update_layout(height=420, plot_bgcolor="#fff", paper_bgcolor="#fff")
    st.plotly_chart(fig_scatter, use_container_width=True)


# ══════════════════════════════════════════════════════════
# TAB 3 · SCORE-VERLAUF
# ══════════════════════════════════════════════════════════
with tab3:
    st.subheader("⏱ Score-Zeitachse · Snapshots")

    standort_auswahl = st.selectbox(
        "Standort wählen",
        options=sorted(df["name"].tolist()),
        key="snap_sel"
    )

    snaps = load_snapshots(standort_auswahl)
    if not snaps:
        st.info("Noch keine Snapshots für diesen Standort. Score-Automat ausführen um ersten Snapshot zu erstellen.")
    else:
        df_snap = pd.DataFrame(snaps)
        df_snap["snapshot_date"] = pd.to_datetime(df_snap["snapshot_date"])
        score_map = {"A":20,"B+":17,"B":15,"C+":13,"C":11,"C−":9,"D+":7,"D":5,"D−":3}
        df_snap["_pts"] = df_snap["score"].map(score_map).fillna(0)

        fig_line = px.line(
            df_snap, x="snapshot_date", y="fahrten_tag",
            markers=True,
            labels={"snapshot_date":"Datum","fahrten_tag":"Fahrten/Tag"},
            title=f"Fahrtenentwicklung · {standort_auswahl}",
            color_discrete_sequence=[WAS_BLUE],
        )
        fig_line.update_layout(height=300, plot_bgcolor="#fff", paper_bgcolor="#fff")
        st.plotly_chart(fig_line, use_container_width=True)

        st.dataframe(
            df_snap[["snapshot_date","score","status","fahrten_tag","gtfs_version"]].rename(columns={
                "snapshot_date":"Datum","score":"Score","status":"Status",
                "fahrten_tag":"Fahrten/Tag","gtfs_version":"GTFS-Version"
            }),
            use_container_width=True
        )


# ══════════════════════════════════════════════════════════
# TAB 4 · KOSTEN-NUTZEN
# ══════════════════════════════════════════════════════════
with tab4:
    st.subheader("💰 Kosten-Nutzen · Priorisierung")
    st.info("Grundannahmen: 1 neue Buslinie = ca. 280.000 €/Jahr · 1 Takt-Verbesserung = ca. 140.000 €/Jahr")

    df["_besch"] = df["beschaeftigte"].apply(
        lambda b: int(str(b).replace(".","").replace(",","").replace(" ","").split("–")[0]) if b else 0
    )
    df["_pts"] = df["score"].map({"A":20,"B+":17,"B":15,"C+":13,"C":11,"C−":9,"D+":7,"D":5,"D−":3}).fillna(0)
    df["_bedarf"] = (20 - df["_pts"]) * 14000  # €/Punkt ca.
    df["_nutzen"] = df["_besch"] * 0.12 * 52 * 2.5  # angenommene Zeitersparnis
    df["_kn"] = (df["_nutzen"] / df["_bedarf"].replace(0,1)).round(2)

    top_kn = df.nlargest(10, "_kn")[["name","ort","score","_besch","_bedarf","_kn"]]
    top_kn.columns = ["Standort","Ort","Score","Beschäftigte","Bedarf €/Jahr","K/N-Ratio"]

    fig_kn = px.bar(
        top_kn, x="K/N-Ratio", y="Standort",
        orientation="h",
        color="K/N-Ratio",
        color_continuous_scale=[[0,"#dc2626"],[0.5,"#d97706"],[1,"#16a34a"]],
        title="Top 10 · Kosten-Nutzen-Verhältnis (höher = besser priorisieren)",
        labels={"K/N-Ratio":"K/N-Ratio"},
    )
    fig_kn.update_layout(height=380, plot_bgcolor="#fff", paper_bgcolor="#fff", showlegend=False)
    st.plotly_chart(fig_kn, use_container_width=True)

    st.markdown("*Methodik: Vereinfachte Schätzung. Für belastbare Zahlen bitte Vollkostenrechnung mit FD52 abstimmen.*")
