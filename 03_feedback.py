"""
pages/03_feedback.py — Betriebsfeedback · direkt in Supabase
"""
import streamlit as st
import pandas as pd
from utils.db import load_standorte, insert_feedback, load_feedback

st.title("📋 Betriebsfeedback")
st.markdown("Ihre Angaben fließen direkt in die Atlas-Datenbasis ein und stärken die Argumentation gegenüber NAH.SH und Kreispolitik.")

standorte = load_standorte()
standort_namen = sorted([s["name"] for s in standorte])

tab_form, tab_uebersicht = st.tabs(["✏ Feedback geben", "📊 Übersicht"])

# ══════════════════════════════════════════════════════════
# FORMULAR
# ══════════════════════════════════════════════════════════
with tab_form:
    with st.form("feedback_form", clear_on_submit=True):
        st.subheader("1. Ihr Gewerbestandort")
        standort = st.selectbox("Standort*", ["— bitte wählen —"] + standort_namen)

        st.subheader("2. Schichtzeiten")
        schicht = st.radio("Wann beginnt die Frühschicht?", [
            "vor 6:00", "6:00–7:00", "7:00–8:00", "nach 8:00", "kein Schichtbetrieb"
        ], horizontal=True)

        st.subheader("3. ÖPNV-Erreichbarkeit")
        puenktl = st.radio("Kommen Mitarbeiter pünktlich zur Frühschicht per ÖPNV?", [
            "Ja, gut möglich", "Nur mit Umstieg", "Kaum möglich", "Nicht möglich"
        ], horizontal=True)

        st.subheader("4. Größtes Problem")
        problem = st.radio("Was ist das größte ÖPNV-Problem?", [
            "Zu wenig Fahrten", "Kein Abendverkehr", "Kein Wochenende",
            "Zu weiter Fußweg", "Ferienausfälle", "Kein ÖPNV vorhanden"
        ], horizontal=True)

        st.subheader("5. ÖPNV-Nutzung heute")
        anteil = st.select_slider("Wie viele Mitarbeiter kommen per ÖPNV?", [
            "0–5%", "5–15%", "15–30%", "über 30%"
        ])

        st.subheader("5b. ⭐ Potenzial")
        st.caption("Diese Antwort ist die stärkste Begründung für neue Buslinien gegenüber Kreispolitik und NAH.SH.")
        potenzial = st.radio("Wie viele Mitarbeiter würden ÖPNV nutzen — wenn es ein gutes Angebot gäbe?", [
            "weniger als 10", "10–30", "30–100", "100–300", "über 300", "schwer zu sagen"
        ], horizontal=True)

        st.subheader("6. Freitext")
        freitext = st.text_area(
            "Was würde am meisten helfen?",
            placeholder='z.B. "Eine frühe Verbindung ab Ahrensburg um 5:30 würde 12 Mitarbeitern helfen…"',
            height=80,
        )

        st.subheader("7. Kontakt")
        email = st.text_input("E-Mail für Rückfragen (optional, nur WAS-intern)",
                              placeholder="vorname.nachname@unternehmen.de")

        submitted = st.form_submit_button("✓ Feedback einsenden", use_container_width=True)

        if submitted:
            if standort == "— bitte wählen —":
                st.error("Bitte wählen Sie einen Standort.")
            else:
                insert_feedback({
                    "standort_name":  standort,
                    "schichtbeginn":  schicht,
                    "puenktlichkeit": puenktl,
                    "hauptproblem":   problem,
                    "anteil_oepnv":   anteil,
                    "potenzial":      potenzial,
                    "freitext":       freitext or None,
                    "kontakt_email":  email or None,
                })
                st.success("✅ Feedback gespeichert — vielen Dank! Ihre Angaben werden beim nächsten Atlas-Update berücksichtigt.")
                st.balloons()

# ══════════════════════════════════════════════════════════
# ÜBERSICHT (nur für WAS-Team)
# ══════════════════════════════════════════════════════════
with tab_uebersicht:
    st.subheader("Alle eingegangenen Feedbacks")

    feedbacks = load_feedback()
    if not feedbacks:
        st.info("Noch kein Feedback eingegangen.")
    else:
        df = pd.DataFrame(feedbacks)

        # KPIs
        c1, c2, c3 = st.columns(3)
        c1.metric("Feedbacks gesamt", len(df))
        c2.metric("Standorte abgedeckt", df["standort_name"].nunique())

        # Potenzial-Auswertung
        pot_map = {
            "weniger als 10": 5, "10–30": 20, "30–100": 65,
            "100–300": 200, "über 300": 350, "schwer zu sagen": 0
        }
        df["_pot"] = df["potenzial"].map(pot_map).fillna(0)
        c3.metric("⭐ Geschätztes Potenzial gesamt", f"{int(df['_pot'].sum())} MA")

        # Potenzial nach Standort
        st.subheader("Potenzial nach Standort")
        pot_df = df.groupby("standort_name")["_pot"].sum().sort_values(ascending=False).reset_index()
        pot_df.columns = ["Standort","Potenzial (MA)"]

        import plotly.express as px
        fig = px.bar(pot_df.head(15), x="Potenzial (MA)", y="Standort",
                     orientation="h", color_discrete_sequence=["#003064"],
                     title="ÖPNV-Potenzial · Angaben aus Betriebsfeedback")
        fig.update_layout(height=400, plot_bgcolor="#fff", paper_bgcolor="#fff")
        st.plotly_chart(fig, use_container_width=True)

        # Rohdaten
        st.subheader("Rohdaten")
        show_cols = ["standort_name","schichtbeginn","puenktlichkeit",
                     "hauptproblem","anteil_oepnv","potenzial","created_at"]
        st.dataframe(df[[c for c in show_cols if c in df.columns]],
                     use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇ CSV exportieren", csv, "feedback.csv", "text/csv")
