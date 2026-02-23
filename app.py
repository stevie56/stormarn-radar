"""
app.py – Streamlit Dashboard für den Stormarn KI-Radar
Starte mit: streamlit run app.py
"""
import json
import os
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

import config_loader as cfg
import database as db
import scraper
import analyzer
import geo_mapper
import alert
import pdf_export

# ──────────────────────────────────────────────────────────
# Seitenkonfiguration
# ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title=cfg.get("radar.name", "Regional Radar"),
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Datenbank initialisieren
db.init_db()


@st.cache_resource
def _ensure_csv_imported():
    """Importiert die Adressliste einmalig beim Start (upsert, idempotent)."""
    csv_path = os.path.join(os.path.dirname(__file__), "data", "unternehmen_stormarn_beispiel.csv")
    if not os.path.exists(csv_path):
        return
    df_csv = pd.read_csv(csv_path, dtype=str).fillna("")
    for _, row in df_csv.iterrows():
        _name = (row.get("name") or "").strip()
        _web  = (row.get("website") or "").strip()
        if _name and _web:
            db.upsert_company(
                name=_name, website=_web,
                address=row.get("adresse", ""), city=row.get("ort", ""),
                postal_code=row.get("plz", ""), industry=row.get("branche", ""),
                employee_count=row.get("mitarbeiter", ""),
                linkedin=row.get("linkedin", ""), xing=row.get("xing", ""),
                twitter=row.get("twitter", ""), instagram=row.get("instagram", ""),
            )


_ensure_csv_imported()

# ──────────────────────────────────────────────────────────
# Styling
# ──────────────────────────────────────────────────────────
PRIMARY = cfg.get("radar.pdf.primary_color", "#1a5276")
ACCENT = cfg.get("radar.pdf.accent_color", "#2e86c1")

st.markdown(f"""
<style>
    .main-header {{
        background: linear-gradient(135deg, {PRIMARY} 0%, {ACCENT} 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
    }}
    .metric-card {{
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }}
    .badge {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
        color: white;
    }}
    .badge-echt {{ background: #1e8449; }}
    .badge-int {{ background: #d4ac0d; }}
    .badge-buzz {{ background: #e67e22; }}
    .badge-kein {{ background: #95a5a6; }}
    .stButton>button {{
        background-color: {PRIMARY};
        color: white;
        border: none;
        border-radius: 8px;
    }}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────────────────
radar_name = cfg.get("radar.name", "Regional Radar")
region = cfg.get("radar.region", "")
topic = cfg.get("radar.topic", "")

st.markdown(f"""
<div class="main-header">
    <h1 style="margin:0;font-size:2rem;">🎯 {radar_name}</h1>
    <p style="margin:0.3rem 0 0 0;opacity:0.85;">{region} · {topic} · Live-Dashboard</p>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────
# Sidebar – Navigation
# ──────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://via.placeholder.com/250x60/1a5276/ffffff?text=Stormarn+Radar",
             use_column_width=True)
    st.markdown("---")
    page = st.radio(
        "Navigation",
        ["📊 Dashboard", "🏢 Unternehmen", "🗺️ Karte",
         "➕ Neu analysieren", "📈 Trends", "🔄 Monitoring",
         "📋 Aktivitätslog", "📄 PDF-Export", "⚙️ Einstellungen"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    api_key = st.text_input("OpenAI API Key", type="password",
                             value=os.getenv("OPENAI_API_KEY", ""),
                             help="Wird nur für die Analyse benötigt")
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key

# ──────────────────────────────────────────────────────────
# Hilfsfunktionen
# ──────────────────────────────────────────────────────────
CATEGORY_COLORS_HEX = {
    "ECHTER_EINSATZ": "#1e8449",
    "INTEGRATION":    "#d4ac0d",
    "BUZZWORD":       "#e67e22",
    "KEIN_KI":        "#95a5a6",
    "UNBEKANNT":      "#bdc3c7",
}
CATEGORY_LABELS = {
    "ECHTER_EINSATZ": "✅ Echter Einsatz",
    "INTEGRATION":    "🔗 Integration",
    "BUZZWORD":       "⚠️ Buzzword",
    "KEIN_KI":        "❌ Kein KI-Bezug",
    "UNBEKANNT":      "❓ Unbekannt",
}


def category_badge(kat):
    color = CATEGORY_COLORS_HEX.get(kat, "#ccc")
    label = CATEGORY_LABELS.get(kat, kat)
    return f'<span style="background:{color};padding:3px 10px;border-radius:12px;color:white;font-size:0.8rem;font-weight:bold;">{label}</span>'


# ──────────────────────────────────────────────────────────
# PAGE: Dashboard
# ──────────────────────────────────────────────────────────
if page == "📊 Dashboard":
    stats = db.get_stats()
    companies = db.get_all_companies()
    events = db.get_recent_events(5)

    # KPI-Reihe
    col1, col2, col3, col4, col5 = st.columns(5)
    total = stats["total_companies"]
    by_cat = stats["by_category"]

    with col1:
        st.metric("Unternehmen gesamt", total)
    with col2:
        st.metric("✅ Echter Einsatz", by_cat.get("ECHTER_EINSATZ", 0))
    with col3:
        st.metric("🔗 Integration", by_cat.get("INTEGRATION", 0))
    with col4:
        st.metric("⚠️ Buzzword", by_cat.get("BUZZWORD", 0))
    with col5:
        st.metric("❌ Kein KI", by_cat.get("KEIN_KI", 0))

    st.markdown("---")
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("🏢 Zuletzt analysierte Unternehmen")
        if companies:
            recent = sorted(companies,
                            key=lambda x: x.get("updated_at", ""),
                            reverse=True)[:8]
            for c in recent:
                with st.container():
                    c1, c2, c3 = st.columns([3, 2, 1])
                    with c1:
                        st.write(f"**{c['name']}**")
                        st.caption(f"{c.get('city', '')} · {c.get('industry', '')}")
                    with c2:
                        kat = c.get("kategorie", "UNBEKANNT")
                        st.markdown(category_badge(kat), unsafe_allow_html=True)
                    with c3:
                        st.write(f"Score: {c.get('vertrauen', '–')}")
        else:
            st.info("Noch keine Unternehmen analysiert. Gehe zu **➕ Neu analysieren**.")

    with col_right:
        st.subheader("📋 Letzte Aktivitäten")
        if events:
            for e in events:
                icon = "🆕" if e["event_type"] == "NEU" else "🔄"
                st.markdown(f"{icon} **{e.get('company_name', '')}**")
                st.caption(f"{e['message']} · {e['created_at'][:16]}")
                st.markdown("---")
        else:
            st.info("Keine Aktivitäten")

        # Tag-Verteilung
        tag_stats = db.get_tag_stats()
        if tag_stats:
            st.subheader("🏷️ Top-Tags")
            top_tags = dict(list(tag_stats.items())[:8])
            tag_df = pd.DataFrame(
                {"Tag": list(top_tags.keys()), "Unternehmen": list(top_tags.values())}
            )
            st.bar_chart(tag_df.set_index("Tag"))

# ──────────────────────────────────────────────────────────
# PAGE: Unternehmen
# ──────────────────────────────────────────────────────────
elif page == "🏢 Unternehmen":
    st.header("Unternehmensverzeichnis")
    companies = db.get_all_companies()

    if not companies:
        st.info("Noch keine Unternehmen. Füge sie unter **➕ Neu analysieren** hinzu.")
        st.stop()

    # Filter – Zeile 1
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        search = st.text_input("🔍 Suche", placeholder="Firmenname...")
    with col_f2:
        all_cats = ["Alle"] + list(CATEGORY_LABELS.values())
        cat_filter = st.selectbox("Kategorie", all_cats)
    with col_f3:
        industries = ["Alle"] + list({c.get("industry", "") for c in companies if c.get("industry")})
        ind_filter = st.selectbox("Branche", industries)

    # Filter – Zeile 2: KI-aktiv + Tags
    col_f4, col_f5 = st.columns([1, 2])
    with col_f4:
        ki_aktiv_only = st.checkbox("Nur KI-aktive Unternehmen")
    with col_f5:
        available_tags = db.get_all_tags()
        tag_filter = st.multiselect("Nach Tags filtern", available_tags)

    # Filtern
    filtered = companies
    if search:
        filtered = [c for c in filtered if search.lower() in c["name"].lower()]
    if cat_filter != "Alle":
        kat_key = {v: k for k, v in CATEGORY_LABELS.items()}.get(cat_filter)
        if kat_key:
            filtered = [c for c in filtered if c.get("kategorie") == kat_key]
    if ind_filter != "Alle":
        filtered = [c for c in filtered if c.get("industry") == ind_filter]
    if ki_aktiv_only:
        filtered = [c for c in filtered if c.get("ki_aktiv") == 1]
    if tag_filter:
        def _has_tags(c):
            try:
                ctags = json.loads(c.get("tags") or "[]")
            except Exception:
                ctags = []
            return any(t in ctags for t in tag_filter)
        filtered = [c for c in filtered if _has_tags(c)]

    st.markdown(f"**{len(filtered)}** Unternehmen gefunden")
    st.markdown("---")

    for c in filtered:
        with st.expander(f"🏢 {c['name']} · {CATEGORY_LABELS.get(c.get('kategorie',''), '?')}"):
            col1, col2 = st.columns([3, 1])
            with col1:
                if c.get("biografie"):
                    st.markdown(f"*{c['biografie']}*")
                st.markdown(f"**Website:** [{c.get('website','')}]({c.get('website','')})")
                st.markdown(f"**Adresse:** {c.get('address','')}, {c.get('city','')}")
                st.markdown(f"**Branche:** {c.get('industry', '–')}")

                # Social-Media-Links
                sm_links = []
                if c.get("linkedin"):
                    sm_links.append(f"[LinkedIn]({c['linkedin']})")
                if c.get("xing"):
                    sm_links.append(f"[XING]({c['xing']})")
                if c.get("twitter"):
                    sm_links.append(f"[X/Twitter]({c['twitter']})")
                if c.get("instagram"):
                    sm_links.append(f"[Instagram]({c['instagram']})")
                if sm_links:
                    st.markdown("**Social Media:** " + " · ".join(sm_links))

                try:
                    ctags = json.loads(c.get("tags") or "[]")
                except Exception:
                    ctags = []
                if ctags:
                    st.markdown("**Tags:** " + " ".join(f"`{t}`" for t in ctags))

                ki_apps = c.get("ki_anwendungen", [])
                if isinstance(ki_apps, str):
                    try:
                        ki_apps = json.loads(ki_apps)
                    except Exception:
                        ki_apps = []
                if ki_apps:
                    st.markdown("**KI-Anwendungen:** " + " · ".join([f"`{a}`" for a in ki_apps]))
            with col2:
                kat = c.get("kategorie", "UNBEKANNT")
                st.markdown(category_badge(kat), unsafe_allow_html=True)
                st.metric("Vertrauen", f"{c.get('vertrauen', '–')}/100")
                if c.get("lat") and c.get("lng"):
                    st.caption(f"📍 {c['lat']:.4f}, {c['lng']:.4f}")

# ──────────────────────────────────────────────────────────
# PAGE: Karte
# ──────────────────────────────────────────────────────────
elif page == "🗺️ Karte":
    st.header("🗺️ KI-Akteure in der Region")
    companies = db.get_all_companies()

    geo_companies = [c for c in companies if c.get("lat") and c.get("lng")]

    if not geo_companies:
        st.warning("Keine Unternehmen mit Koordinaten. Füge Adressen hinzu und analysiere erneut.")
        st.stop()

    # Karte zentrieren
    bounds = cfg.get("radar.region_bounds", {})
    center_lat = (bounds.get("north", 53.7) + bounds.get("south", 53.6)) / 2
    center_lng = (bounds.get("east", 10.25) + bounds.get("west", 10.1)) / 2

    m = folium.Map(location=[center_lat, center_lng], zoom_start=11,
                   tiles="CartoDB positron")

    # Marker-Farbe nach Kategorie
    COLOR_MAP = {
        "ECHTER_EINSATZ": "green",
        "INTEGRATION":    "orange",
        "BUZZWORD":       "red",
        "KEIN_KI":        "gray",
        "UNBEKANNT":      "lightgray",
    }

    for c in geo_companies:
        kat = c.get("kategorie", "UNBEKANNT")
        color = COLOR_MAP.get(kat, "blue")
        ki_apps = c.get("ki_anwendungen", [])
        if isinstance(ki_apps, str):
            try:
                ki_apps = json.loads(ki_apps)
            except Exception:
                ki_apps = []

        popup_html = f"""
        <b>{c['name']}</b><br>
        {CATEGORY_LABELS.get(kat, kat)}<br>
        {c.get('city', '')}<br>
        {'<br>'.join(ki_apps[:3]) if ki_apps else ''}
        <br><a href="{c.get('website','')}" target="_blank">Website öffnen</a>
        """

        folium.CircleMarker(
            location=[c["lat"], c["lng"]],
            radius=10,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=c["name"]
        ).add_to(m)

    # Legende
    legend_html = """
    <div style="position: fixed; bottom: 30px; left: 30px; z-index: 1000;
                background: white; padding: 15px; border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-size: 13px;">
        <b>Legende</b><br>
        🟢 Echter KI-Einsatz<br>
        🟠 KI-Integration<br>
        🔴 KI-Buzzword<br>
        ⚫ Kein KI-Bezug
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    st_folium(m, width=None, height=550, returned_objects=[])

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Unternehmen auf der Karte", len(geo_companies))
    with col2:
        st.metric("Davon mit echtem KI-Einsatz",
                  len([c for c in geo_companies if c.get("kategorie") == "ECHTER_EINSATZ"]))

# ──────────────────────────────────────────────────────────
# PAGE: Neu analysieren
# ──────────────────────────────────────────────────────────
elif page == "➕ Neu analysieren":
    st.header("➕ Unternehmen hinzufügen & analysieren")

    tab_single, tab_csv = st.tabs(["📝 Einzeln", "📂 CSV-Import"])

    # ── Tab 1: Einzelnes Unternehmen ──────────────────────
    with tab_single:
        with st.form("new_company_form"):
            st.subheader("Unternehmensdaten")
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input("Firmenname *", placeholder="Musterfirma GmbH")
                website = st.text_input("Website *", placeholder="https://musterfirma.de")
                industry = st.text_input("Branche", placeholder="IT / Logistik / Handel...")
            with col2:
                address = st.text_input("Straße & Hausnummer", placeholder="Hauptstraße 1")
                postal_code = st.text_input("PLZ", placeholder="23843")
                city = st.text_input("Stadt", placeholder="Bad Oldesloe")
                employee_count = st.selectbox("Mitarbeiter",
                    ["–", "1-9", "10-49", "50-249", "250-999", "1000+"])

            st.subheader("Social Media")
            linkedin = st.text_input("LinkedIn", placeholder="https://linkedin.com/company/...")

            st.subheader("Tags")
            tags_input = st.text_input(
                "Branchen-Tags (kommagetrennt)",
                placeholder="IT, Logistik, Automatisierung...",
                help="Eigene Tags für Filterung und Visualisierung. "
                     "Werden nach der Analyse automatisch um erkannte KI-Anwendungen ergänzt."
            )

            col_opt1, col_opt2 = st.columns(2)
            with col_opt1:
                do_geo = st.checkbox("Geocodierung (Adresse → Koordinaten)", value=True)
            with col_opt2:
                do_bio = st.checkbox("Biografie generieren", value=True)

            submitted = st.form_submit_button("🚀 Analysieren", type="primary")

        if submitted:
            if not name or not website:
                st.error("Bitte Firmenname und Website angeben.")
            elif not os.getenv("OPENAI_API_KEY"):
                st.error("OpenAI API Key fehlt. Bitte in der Sidebar eingeben.")
            else:
                progress = st.progress(0, "Starte Analyse...")

                # 1. Scraping
                progress.progress(20, "🌐 Website wird gelesen...")
                scrape_result = scraper.scrape_website(website)

                if scrape_result["error"]:
                    st.warning(f"Scraping-Warnung: {scrape_result['error']}")
                    website_text = f"Firmenname: {name}"
                else:
                    website_text = scrape_result["text"]
                    st.success(f"✅ {scrape_result['pages_scraped']} Seiten gelesen · "
                               f"{len(scrape_result['keyword_hits'])} Keyword-Treffer: "
                               f"{', '.join(scrape_result['keyword_hits'][:5])}")

                # 1.5. Social-Media-Erkennung
                progress.progress(35, "🔗 Social-Media-Profile werden erkannt...")
                detected_sm = scrape_result.get("social_media", {})

                # Manuelle Eingabe hat Vorrang; erkanntes LinkedIn-Profil füllt leeres Feld
                final_linkedin = linkedin or detected_sm.get("linkedin", "")

                if not linkedin and final_linkedin:
                    st.info(f"🔗 LinkedIn automatisch erkannt: [{final_linkedin}]({final_linkedin})")
                elif not scrape_result["error"]:
                    st.caption("🔗 Kein LinkedIn-Profil auf der Website gefunden.")

                # 2. Geocodierung
                lat, lng = None, None
                if do_geo and (address or city):
                    progress.progress(45, "📍 Geocodierung...")
                    lat, lng = geo_mapper.geocode_address(address, city, postal_code)
                    if lat:
                        st.success(f"📍 Koordinaten: {lat:.4f}, {lng:.4f}")
                    else:
                        st.info("Adresse konnte nicht geocodiert werden.")

                # 3. Company speichern
                company_id = db.upsert_company(
                    name=name, website=website, address=address,
                    city=city, postal_code=postal_code,
                    lat=lat, lng=lng, industry=industry,
                    employee_count=employee_count,
                    linkedin=final_linkedin
                )

                # 4. LLM-Analyse
                progress.progress(60, "🤖 KI-Analyse...")
                try:
                    classification = analyzer.classify_company(name, website_text)

                    biografie = ""
                    if do_bio:
                        progress.progress(80, "✍️ Biografie wird geschrieben...")
                        biografie = analyzer.generate_biography(name, website_text, classification)

                    db.save_analysis(
                        company_id=company_id,
                        kategorie=classification["kategorie"],
                        begruendung=classification["begruendung"],
                        ki_anwendungen=classification["ki_anwendungen"],
                        vertrauen=classification["vertrauen"],
                        biografie=biografie,
                        raw_text=website_text[:2000]
                    )

                    db.log_event(company_id, "NEU",
                                 f"Analysiert: {classification['kategorie']} (Score: {classification['vertrauen']})")

                    # Auto-Tags: manuelle + Branche + KI-Anwendungen (dedupliziert)
                    manual_tags = [t.strip() for t in tags_input.split(",") if t.strip()]
                    industry_tag = industry.split("/")[0].strip() if industry else ""
                    ki_tags = [a for a in classification.get("ki_anwendungen", [])[:3]]
                    combined = ([industry_tag] if industry_tag else []) + ki_tags
                    final_tags = list(dict.fromkeys(manual_tags + combined))
                    if final_tags:
                        db.update_company_tags(company_id, final_tags)

                    progress.progress(100, "✅ Fertig!")

                    # Ergebnis anzeigen
                    st.markdown("---")
                    st.subheader("📊 Analyseergebnis")

                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(f"### {name}")
                        kat = classification["kategorie"]
                        st.markdown(category_badge(kat), unsafe_allow_html=True)
                        st.markdown(f"\n**Begründung:** {classification['begruendung']}")

                        if classification.get("ki_anwendungen"):
                            st.markdown("**KI-Anwendungen:**")
                            for app in classification["ki_anwendungen"]:
                                st.markdown(f"• {app}")

                        if biografie:
                            st.markdown("---")
                            st.markdown("**Biografie:**")
                            st.markdown(f"*{biografie}*")

                    with col2:
                        st.metric("Vertrauens-Score", f"{classification['vertrauen']}/100")
                        if final_tags:
                            st.markdown("**Tags:**")
                            st.markdown(" ".join(f"`{t}`" for t in final_tags))

                except Exception as e:
                    st.error(f"LLM-Analyse fehlgeschlagen: {e}")
                    progress.empty()

    # ── Tab 2: CSV-Massenimport ───────────────────────────
    with tab_csv:
        st.subheader("Unternehmen per CSV importieren")
        st.markdown("""
Lade eine CSV-Datei hoch um mehrere Unternehmen auf einmal in die Datenbank zu importieren.
Die Unternehmen werden **ohne** KI-Analyse gespeichert – du kannst sie danach einzeln analysieren.

**Pflichtfelder:** `name`, `website`
**Optionale Felder:** `adresse`, `plz`, `ort`, `branche`, `mitarbeiter`, `linkedin`, `xing`, `twitter`, `instagram`
        """)

        # Beispiel-CSV zum Download
        beispiel_csv_path = os.path.join(os.path.dirname(__file__), "data", "unternehmen_stormarn_beispiel.csv")
        if os.path.exists(beispiel_csv_path):
            with open(beispiel_csv_path, "rb") as f:
                st.download_button(
                    label="⬇️ Beispiel-CSV herunterladen",
                    data=f,
                    file_name="unternehmen_stormarn_beispiel.csv",
                    mime="text/csv",
                    help="Lade diese Vorlage herunter, fülle sie mit echten Unternehmensdaten und lade sie hoch."
                )

        st.markdown("---")
        uploaded_file = st.file_uploader(
            "CSV- oder Excel-Datei hochladen",
            type=["csv", "xlsx", "xls"],
            help="CSV: Trennzeichen Komma, UTF-8. Excel: .xlsx oder .xls, erste Zeile = Spaltenköpfe."
        )

        if uploaded_file is not None:
            try:
                fname = uploaded_file.name.lower()
                if fname.endswith(".csv"):
                    df_import = pd.read_csv(uploaded_file, dtype=str).fillna("")
                else:
                    df_import = pd.read_excel(uploaded_file, dtype=str).fillna("")

                # Pflichtfelder prüfen
                missing_cols = [c for c in ["name", "website"] if c not in df_import.columns]
                if missing_cols:
                    st.error(f"Fehlende Pflichtfelder in der CSV: {', '.join(missing_cols)}")
                else:
                    st.success(f"✅ {len(df_import)} Zeilen erkannt")
                    st.dataframe(df_import, use_container_width=True, hide_index=True)

                    col_geo, col_btn = st.columns([1, 1])
                    with col_geo:
                        do_geo_csv = st.checkbox(
                            "Geocodierung beim Import (langsamer)",
                            value=False,
                            help="Für jede Adresse werden Koordinaten via Nominatim abgefragt."
                        )

                    with col_btn:
                        do_import = st.button("📥 Import starten", type="primary")

                    if do_import:
                        progress_bar = st.progress(0)
                        imported, skipped, errors = 0, 0, 0
                        status_box = st.empty()

                        for i, row in df_import.iterrows():
                            pct = int((i + 1) / len(df_import) * 100)
                            progress_bar.progress(pct, f"Importiere {i+1}/{len(df_import)}: {row.get('name', '')}")

                            row_name = row.get("name", "").strip()
                            row_website = row.get("website", "").strip()

                            if not row_name or not row_website:
                                skipped += 1
                                continue

                            lat, lng = None, None
                            if do_geo_csv:
                                row_address = row.get("adresse", "")
                                row_city = row.get("ort", "")
                                row_plz = row.get("plz", "")
                                if row_address or row_city:
                                    lat, lng = geo_mapper.geocode_address(
                                        row_address, row_city, row_plz
                                    )

                            try:
                                db.upsert_company(
                                    name=row_name,
                                    website=row_website,
                                    address=row.get("adresse", ""),
                                    city=row.get("ort", ""),
                                    postal_code=row.get("plz", ""),
                                    lat=lat,
                                    lng=lng,
                                    industry=row.get("branche", ""),
                                    employee_count=row.get("mitarbeiter", ""),
                                    linkedin=row.get("linkedin", ""),
                                    xing=row.get("xing", ""),
                                    twitter=row.get("twitter", ""),
                                    instagram=row.get("instagram", "")
                                )
                                imported += 1
                            except Exception as e:
                                errors += 1

                        progress_bar.progress(100, "Fertig!")
                        st.success(f"Import abgeschlossen: **{imported}** importiert · "
                                   f"**{skipped}** übersprungen · **{errors}** Fehler")
                        if imported > 0:
                            st.info("Die Unternehmen sind jetzt unter **🏢 Unternehmen** sichtbar. "
                                    "Analysiere sie einzeln unter **📝 Einzeln**.")

            except Exception as e:
                st.error(f"Fehler beim Lesen der CSV: {e}")

# ──────────────────────────────────────────────────────────
# PAGE: Trends
# ──────────────────────────────────────────────────────────
elif page == "📈 Trends":
    st.header("📈 Trend-Analyse")

    companies = db.get_all_companies()
    analyzed = [c for c in companies if c.get("kategorie")]

    if not analyzed:
        st.info("Noch zu wenig Daten für eine Trend-Analyse.")
        st.stop()

    # Verteilungs-Chart
    st.subheader("Kategorie-Verteilung")
    stats = db.get_stats()
    by_cat = stats["by_category"]

    chart_data = pd.DataFrame({
        "Kategorie": [CATEGORY_LABELS.get(k, k) for k in by_cat.keys()],
        "Anzahl": list(by_cat.values())
    })
    st.bar_chart(chart_data.set_index("Kategorie"))

    # Branchen-Übersicht
    st.subheader("Branchen-Verteilung")
    industries = {}
    for c in analyzed:
        ind = c.get("industry", "Unbekannt") or "Unbekannt"
        industries[ind] = industries.get(ind, 0) + 1

    if industries:
        ind_df = pd.DataFrame(
            {"Branche": list(industries.keys()), "Anzahl": list(industries.values())}
        ).sort_values("Anzahl", ascending=False)
        st.bar_chart(ind_df.set_index("Branche"))

    # LLM-Trend-Report
    st.subheader("🤖 KI-Trend-Report")
    existing = db.get_latest_trend_report()
    if existing:
        st.info(f"Letzter Report: {existing['created_at'][:16]}")
        st.markdown(existing["report_text"])

    if st.button("Neuen Trend-Report generieren"):
        if not os.getenv("OPENAI_API_KEY"):
            st.error("OpenAI API Key fehlt.")
        else:
            with st.spinner("Analysiere Trends..."):
                report = analyzer.generate_trend_report(analyzed)
                db.save_trend_report(report, len(analyzed))
                st.markdown(report)
                st.success("Report gespeichert!")

# ──────────────────────────────────────────────────────────
# PAGE: Monitoring
# ──────────────────────────────────────────────────────────
elif page == "🔄 Monitoring":
    from datetime import datetime as _dt

    STALE_DAYS = 30

    def _freshness(c):
        """Gibt (status, tage_alt) zurück: 'aktuell' | 'veraltet' | 'ausstehend'."""
        at = c.get("analyzed_at")
        if not at:
            return "ausstehend", None
        try:
            delta = (_dt.now() - _dt.fromisoformat(at)).days
            return ("aktuell" if delta <= STALE_DAYS else "veraltet"), delta
        except Exception:
            return "ausstehend", None

    def _run_analysis(c):
        """Analysiert ein Unternehmen und speichert das Ergebnis. Gibt classification zurück."""
        sr = scraper.scrape_website(c["website"])
        wtext = sr["text"] if not sr["error"] else f"Firmenname: {c['name']}"
        cl = analyzer.classify_company(c["name"], wtext)
        old_kat = c.get("kategorie")
        db.save_analysis(
            company_id=c["id"],
            kategorie=cl["kategorie"],
            begruendung=cl["begruendung"],
            ki_anwendungen=cl["ki_anwendungen"],
            vertrauen=cl["vertrauen"],
            biografie="",
            raw_text=wtext[:2000],
        )
        evt = "ÄNDERUNG" if old_kat and old_kat != cl["kategorie"] else "UPDATE"
        note = f" · Vorher: {old_kat}" if evt == "ÄNDERUNG" else ""
        db.log_event(c["id"], evt,
                     f"Monitoring: {cl['kategorie']} (Score: {cl['vertrauen']}){note}")
        return cl

    st.header("🔄 KI-Aktivitäts-Monitoring")
    st.caption(f"Alle Unternehmen aus der Adressliste auf einen Blick · "
               f"Ampel: 🟢 < {STALE_DAYS} Tage · 🟡 veraltet · 🔴 noch nicht analysiert")

    companies = db.get_all_companies()

    if not companies:
        st.info("Keine Unternehmen in der Datenbank.")
        st.stop()

    fresh_list   = [c for c in companies if _freshness(c)[0] == "aktuell"]
    stale_list   = [c for c in companies if _freshness(c)[0] == "veraltet"]
    pending_list = [c for c in companies if _freshness(c)[0] == "ausstehend"]

    # ── KPI-Zeile ─────────────────────────────────────────
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Unternehmen gesamt", len(companies))
    kpi2.metric("🟢 Aktuell analysiert", len(fresh_list))
    kpi3.metric("🟡 Veraltet (>30 Tage)", len(stale_list))
    kpi4.metric("🔴 Noch ausstehend", len(pending_list))

    st.markdown("---")

    has_api   = bool(os.getenv("OPENAI_API_KEY"))
    to_update = pending_list + stale_list

    # ── Filter + Bulk-Button ───────────────────────────────
    col_flt, col_bulk = st.columns([2, 2])
    with col_flt:
        status_filter = st.selectbox(
            "Anzeigen",
            ["Alle", "🔴 Noch ausstehend", "🟡 Veraltet (>30 Tage)", "🟢 Aktuell analysiert"],
        )
    with col_bulk:
        st.write("")  # vertical align
        do_bulk = st.button(
            f"🚀 {len(to_update)} ausstehende / veraltete jetzt analysieren",
            type="primary",
            disabled=not has_api or len(to_update) == 0,
            help="Analysiert alle noch nicht oder veraltet analysierten Unternehmen per KI.",
        )

    # ── Bulk-Analyse ──────────────────────────────────────
    if do_bulk:
        if not has_api:
            st.error("OpenAI API Key fehlt (Sidebar).")
        else:
            bulk_prog = st.progress(0, "Starte Bulk-Analyse…")
            ok, fail = 0, 0
            for i, c in enumerate(to_update):
                pct = int((i + 1) / len(to_update) * 100)
                bulk_prog.progress(pct, f"Analysiere {c['name']} ({i+1}/{len(to_update)})…")
                try:
                    _run_analysis(c)
                    ok += 1
                except Exception as exc:
                    fail += 1
                    db.log_event(c["id"], "FEHLER",
                                 f"Monitoring-Analyse fehlgeschlagen: {exc}")
            bulk_prog.progress(100, "Fertig!")
            st.success(f"Bulk-Analyse abgeschlossen: **{ok}** aktualisiert"
                       + (f" · **{fail}** Fehler" if fail else ""))
            st.rerun()

    st.markdown("---")

    # ── Filteranwendung ───────────────────────────────────
    display = companies
    if status_filter == "🔴 Noch ausstehend":
        display = pending_list
    elif status_filter == "🟡 Veraltet (>30 Tage)":
        display = stale_list
    elif status_filter == "🟢 Aktuell analysiert":
        display = fresh_list

    if not display:
        st.info("Keine Unternehmen für diesen Filter.")
        st.stop()

    # ── Spaltenköpfe ──────────────────────────────────────
    h1, h2, h3, h4, h5 = st.columns([3, 2, 2, 2, 1])
    h1.markdown("**Unternehmen**")
    h2.markdown("**Stadt · Branche**")
    h3.markdown("**KI-Status**")
    h4.markdown("**Letzte Analyse**")
    h5.markdown("**Prüfen**")
    st.markdown('<hr style="margin:4px 0">', unsafe_allow_html=True)

    # ── Unternehmenszeilen ────────────────────────────────
    ICON = {"aktuell": "🟢", "veraltet": "🟡", "ausstehend": "🔴"}
    for c in display:
        fstatus, delta = _freshness(c)
        icon = ICON.get(fstatus, "⚪")

        col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
        with col1:
            st.write(f"{icon} **{c['name']}**")
        with col2:
            st.caption(f"{c.get('city', '–')} · {c.get('industry', '–')}")
        with col3:
            if c.get("kategorie"):
                st.markdown(category_badge(c["kategorie"]), unsafe_allow_html=True)
            else:
                st.caption("–")
        with col4:
            if c.get("analyzed_at"):
                st.caption(f"{c['analyzed_at'][:10]}  ({delta}d)")
            else:
                st.caption("–")
        with col5:
            if st.button("🔄", key=f"mon_{c['id']}",
                         help=f"{c['name']} jetzt per KI analysieren",
                         disabled=not has_api):
                with st.spinner(f"Analysiere {c['name']}…"):
                    try:
                        _run_analysis(c)
                    except Exception as e:
                        st.error(f"Fehler: {e}")
                st.rerun()

        st.markdown('<hr style="margin:2px 0;opacity:0.15">', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────
# PAGE: Aktivitätslog
# ──────────────────────────────────────────────────────────
elif page == "📋 Aktivitätslog":
    st.header("📋 Aktivitäts-Log")

    events = db.get_recent_events(100)

    if not events:
        st.info("Noch keine Aktivitäten")
    else:
        # DataFrame
        df = pd.DataFrame(events)
        df = df[["created_at", "company_name", "event_type", "message", "alerted"]]
        df.columns = ["Zeitpunkt", "Unternehmen", "Typ", "Details", "Gemeldet"]
        df["Gemeldet"] = df["Gemeldet"].map({0: "❌", 1: "✅"})
        st.dataframe(df, use_container_width=True, hide_index=True)

    # Alert-Bereich
    st.markdown("---")
    st.subheader("📧 E-Mail-Alert")
    alert_enabled = cfg.get("radar.alerts.enabled", False)

    if not alert_enabled:
        st.warning("Alerts sind in der config.yaml deaktiviert.")
    else:
        from_email = cfg.get("radar.alerts.from_email", "")
        to_email = cfg.get("radar.alerts.to_email", "")

        if not from_email or not to_email:
            st.warning("E-Mail nicht konfiguriert. Bitte `from_email` und `to_email` in config.yaml setzen.")
        else:
            st.info(f"Von: {from_email} → An: {to_email}")
            smtp_password = st.text_input("SMTP-Passwort (Gmail App-Passwort)", type="password")

            if st.button("🔔 Alert jetzt senden"):
                result = alert.check_and_alert(smtp_password)
                if result["status"] == "sent":
                    st.success(f"Alert gesendet: {result['count']} Ereignisse")
                elif result["status"] == "no_new_events":
                    st.info("Keine neuen Ereignisse")
                else:
                    st.warning(f"Status: {result['status']}")

# ──────────────────────────────────────────────────────────
# PAGE: PDF-Export
# ──────────────────────────────────────────────────────────
elif page == "📄 PDF-Export":
    st.header("📄 PDF-Steckbriefe exportieren")

    companies = db.get_all_companies()
    analyzed = [c for c in companies if c.get("kategorie")]

    if not analyzed:
        st.info("Noch keine analysierten Unternehmen.")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["Einzelner Steckbrief", "Übersichts-PDF", "📂 Gespeicherte PDFs"])

    with tab1:
        company_names = {c["name"]: c["id"] for c in analyzed}
        selected_name = st.selectbox("Unternehmen wählen", list(company_names.keys()))

        if st.button("📄 Steckbrief generieren"):
            company_id = company_names[selected_name]
            company = db.get_company_by_id(company_id)
            analyses = db.get_analyses_for_company(company_id)

            if not analyses:
                st.error("Keine Analyse vorhanden.")
            else:
                analysis = analyses[0]
                with st.spinner("PDF wird erstellt..."):
                    path = pdf_export.generate_company_profile(company, analysis)
                with open(path, "rb") as f:
                    st.download_button(
                        label=f"⬇️ {selected_name} – Steckbrief.pdf",
                        data=f,
                        file_name=f"Steckbrief_{selected_name.replace(' ','_')}.pdf",
                        mime="application/pdf"
                    )

    with tab2:
        st.write(f"{len(analyzed)} Unternehmen werden ins Übersichts-PDF aufgenommen.")
        cat_filter = st.multiselect(
            "Nur diese Kategorien:",
            list(CATEGORY_LABELS.values()),
            default=list(CATEGORY_LABELS.values())
        )

        if st.button("📊 Übersichts-PDF generieren"):
            cat_keys = {v: k for k, v in CATEGORY_LABELS.items()}
            selected_keys = [cat_keys[c] for c in cat_filter if c in cat_keys]
            filtered = [c for c in analyzed if c.get("kategorie") in selected_keys]

            with st.spinner("PDF wird erstellt..."):
                path = pdf_export.generate_overview_pdf(filtered)
            with open(path, "rb") as f:
                st.download_button(
                    label="⬇️ Übersicht herunterladen",
                    data=f,
                    file_name="Stormarn_KI_Uebersicht.pdf",
                    mime="application/pdf"
                )

    with tab3:
        st.subheader("📂 Gespeicherte PDF-Steckbriefe")
        from pathlib import Path
        exports_dir = Path(__file__).parent / "exports"
        pdf_files = sorted(exports_dir.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)

        if not pdf_files:
            st.info("Noch keine PDFs vorhanden. Erstelle zunächst einen Steckbrief.")
        else:
            st.caption(f"{len(pdf_files)} PDF(s) verfügbar")
            for pdf_path in pdf_files:
                size_kb = pdf_path.stat().st_size // 1024
                col_name, col_size, col_btn = st.columns([4, 1, 2])
                with col_name:
                    st.write(f"📄 **{pdf_path.stem.replace('_', ' ')}**")
                with col_size:
                    st.caption(f"{size_kb} KB")
                with col_btn:
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Download",
                            data=f,
                            file_name=pdf_path.name,
                            mime="application/pdf",
                            key=f"dl_{pdf_path.name}"
                        )
                st.markdown("---")

# ──────────────────────────────────────────────────────────
# PAGE: Einstellungen
# ──────────────────────────────────────────────────────────
elif page == "⚙️ Einstellungen":
    st.header("⚙️ Konfiguration")

    st.subheader("Aktuelle config.yaml")
    config_path = "config.yaml"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config_content = f.read()
        st.code(config_content, language="yaml")

        st.info("💡 Um das Thema zu wechseln (z.B. auf 'Wasserstoff'), "
                "einfach die config.yaml bearbeiten und `streamlit run app.py` neu starten.")
    else:
        st.error("config.yaml nicht gefunden.")

    st.markdown("---")
    st.subheader("🔄 Themen-Presets")
    st.markdown("""
Lade eine dieser Beispiel-Konfigurationen um das Radar-Thema zu wechseln:

| Preset | Thema | Region |
|--------|-------|--------|
| `config_ki_stormarn.yaml` | Künstliche Intelligenz | Kreis Stormarn |
| `config_h2_hamburg.yaml` | Wasserstofftechnologie | Hamburg |
| `config_startup.yaml` | Tech-Startups | Berlin |
| `config_nachhaltigkeit.yaml` | Nachhaltigkeit | Schleswig-Holstein |

Einfach umbenennen in `config.yaml` und Streamlit neu starten.
    """)

    st.markdown("---")
    st.subheader("🗑️ Datenbank zurücksetzen")
    if st.checkbox("Ich bin sicher, dass ich alle Daten löschen möchte"):
        if st.button("🗑️ Alle Daten löschen", type="secondary"):
            db_path = "data/radar.db"
            if os.path.exists(db_path):
                os.remove(db_path)
                db.init_db()
                st.success("Datenbank zurückgesetzt.")
            else:
                st.info("Keine Datenbank gefunden.")
