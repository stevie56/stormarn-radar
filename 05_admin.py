"""
pages/05_admin.py — Datenverwaltung · Score-Automat · Import
"""
import streamlit as st
import pandas as pd
import json
from utils.db import (load_standorte, upsert_standort,
                      load_firmen, save_snapshot, get_client)
from utils.scoring import calc_score, schwachstellen

st.title("⚙ Admin · Datenverwaltung")
st.caption("Nur für WAS-Projektteam. Änderungen werden sofort in Supabase gespeichert.")

tab_score, tab_edit, tab_import, tab_export = st.tabs([
    "⚖ Score-Automat", "✏ Standorte bearbeiten", "⬆ Import", "⬇ Export"
])

# ══════════════════════════════════════════════════════════
# TAB 1 · SCORE-AUTOMAT
# ══════════════════════════════════════════════════════════
with tab_score:
    st.subheader("⚖ Alle Scores neu berechnen")
    st.markdown("Berechnet Scores aus den aktuellen Fahrten-/Taktdaten und speichert einen Snapshot.")

    standorte = load_standorte()
    if not standorte:
        st.warning("Keine Standorte vorhanden.")
    else:
        if st.button("▶ Score-Automat starten", use_container_width=True):
            progress = st.progress(0)
            results = []

            for i, s in enumerate(standorte):
                label, status, pts = calc_score(s)
                old_score  = s.get("score","—")
                old_status = s.get("status","—")

                changed = (label != old_score) or (status != old_status)

                # In Supabase speichern
                upsert_standort({"name": s["name"], "score": label, "status": status})
                save_snapshot(s["name"], label, status, s.get("fahrten_tag",0))

                results.append({
                    "Standort": s["name"],
                    "Alt": old_score,
                    "Neu": label,
                    "Status": status,
                    "Punkte": pts,
                    "Geändert": "✓" if changed else "",
                })
                progress.progress((i+1)/len(standorte))

            st.success(f"✅ {len(standorte)} Scores berechnet und gespeichert.")

            df_res = pd.DataFrame(results)
            changed_df = df_res[df_res["Geändert"] == "✓"]
            if not changed_df.empty:
                st.subheader(f"🔄 {len(changed_df)} Änderungen")
                st.dataframe(changed_df, use_container_width=True)
            else:
                st.info("Keine Score-Änderungen.")

            st.dataframe(df_res, use_container_width=True)

# ══════════════════════════════════════════════════════════
# TAB 2 · STANDORTE BEARBEITEN
# ══════════════════════════════════════════════════════════
with tab_edit:
    st.subheader("✏ Standort-Kerndaten bearbeiten")

    standorte = load_standorte()
    namen = [s["name"] for s in standorte]
    auswahl = st.selectbox("Standort wählen", namen)

    s = next((x for x in standorte if x["name"] == auswahl), None)
    if s:
        with st.form("edit_form"):
            c1, c2 = st.columns(2)
            fahrten   = c1.number_input("Fahrten/Tag",       value=int(s.get("fahrten_tag") or 0), step=1)
            takt      = c2.number_input("HVZ-Takt (Minuten)",value=int(s.get("takt_hvz") or 0), step=1)
            c3, c4 = st.columns(2)
            erste     = c3.text_input("Erste Abfahrt", value=s.get("erste_abfahrt","") or "")
            letzte    = c4.text_input("Letzte Abfahrt", value=s.get("letzte_abfahrt","") or "")
            c5, c6 = st.columns(2)
            abend     = c5.checkbox("Abendverkehr", value=bool(s.get("abend")))
            woche     = c6.checkbox("Wochenendverkehr", value=bool(s.get("wochenende")))
            besch     = st.text_input("Beschäftigte", value=s.get("beschaeftigte","") or "")
            daten_std = st.text_input("Datenstand", value=s.get("daten_stand","") or "")

            if st.form_submit_button("💾 Speichern", use_container_width=True):
                upsert_standort({
                    "name":            s["name"],
                    "fahrten_tag":     int(fahrten),
                    "takt_hvz":        int(takt) if takt else None,
                    "erste_abfahrt":   erste or None,
                    "letzte_abfahrt":  letzte or None,
                    "abend":           abend,
                    "wochenende":      woche,
                    "beschaeftigte":   besch or None,
                    "daten_stand":     daten_std or None,
                })
                st.success("✅ Gespeichert!")
                st.rerun()

        # Schwachstellen-Vorschau
        st.markdown("**Schwachstellen-Analyse:**")
        issues = schwachstellen(s)
        for issue in issues:
            st.warning(issue)
        if not issues:
            st.success("Keine kritischen Schwachstellen.")

# ══════════════════════════════════════════════════════════
# TAB 3 · IMPORT
# ══════════════════════════════════════════════════════════
with tab_import:
    st.subheader("⬆ Daten importieren")

    import_type = st.radio("Was importieren?",
                           ["Standorte (JSON)", "Firmen (CSV)"], horizontal=True)

    if import_type == "Standorte (JSON)":
        st.markdown("**Format:** Liste von Objekten mit den Feldern `name`, `ort`, `lat`, `lng`, `fahrten_tag`, …")
        example = json.dumps([{
            "name": "GE Beispiel", "ort": "Musterhausen",
            "lat": 53.68, "lng": 10.23,
            "fahrten_tag": 12, "takt_hvz": 30,
            "beschaeftigte": "450", "daten_stand": "Jan 2025"
        }], indent=2, ensure_ascii=False)
        with st.expander("Beispiel-JSON anzeigen"):
            st.code(example, language="json")

        uploaded = st.file_uploader("JSON-Datei hochladen", type=["json"])
        if uploaded:
            try:
                data = json.loads(uploaded.read())
                st.dataframe(pd.DataFrame(data).head(5))
                if st.button("⬆ Importieren", use_container_width=True):
                    for item in data:
                        upsert_standort(item)
                    st.success(f"✅ {len(data)} Standorte importiert!")
                    st.rerun()
            except Exception as e:
                st.error(f"Fehler: {e}")

    else:
        st.markdown("**CSV-Format:** `name, ort, beschaeftigte, branche, lat, lng, fruehschicht`")
        uploaded = st.file_uploader("CSV-Datei hochladen", type=["csv"])
        if uploaded:
            try:
                df = pd.read_csv(uploaded)
                st.dataframe(df.head(10))
                if st.button("⬆ Importieren", use_container_width=True):
                    db = get_client()
                    records = df.to_dict("records")
                    db.table("firmen").upsert(records, on_conflict="name").execute()
                    st.success(f"✅ {len(records)} Firmen importiert!")
            except Exception as e:
                st.error(f"Fehler: {e}")

# ══════════════════════════════════════════════════════════
# TAB 4 · EXPORT
# ══════════════════════════════════════════════════════════
with tab_export:
    st.subheader("⬇ Daten exportieren")

    standorte = load_standorte()
    firmen    = load_firmen()

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**Standorte**")
        if standorte:
            df_s = pd.DataFrame(standorte)
            csv_s = df_s.to_csv(index=False).encode("utf-8")
            json_s = json.dumps(standorte, ensure_ascii=False, indent=2).encode("utf-8")
            st.download_button("⬇ CSV",  csv_s,  "standorte.csv",  "text/csv",         use_container_width=True)
            st.download_button("⬇ JSON", json_s, "standorte.json", "application/json", use_container_width=True)

    with c2:
        st.markdown("**Firmen**")
        if firmen:
            df_f = pd.DataFrame(firmen)
            csv_f = df_f.to_csv(index=False).encode("utf-8")
            st.download_button("⬇ CSV", csv_f, "firmen.csv", "text/csv", use_container_width=True)
