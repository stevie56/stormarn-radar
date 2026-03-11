# 🚌 Mobilitätsatlas Stormarn — Streamlit + Supabase

Interaktiver ÖPNV-Atlas für den Kreis Stormarn.  
Gebaut mit **Streamlit** (Frontend) + **Supabase** (Datenbank).

---

## 📁 Projektstruktur

```
mobilitaetsatlas/
├── app.py                    # Hauptdatei — hier starten
├── requirements.txt          # Python-Abhängigkeiten
├── .env.example              # Umgebungsvariablen Vorlage
├── supabase_schema.sql       # Datenbankschema → in Supabase ausführen
│
├── pages/
│   ├── 01_karte.py           # Interaktive Karte mit Filtern
│   ├── 02_analyse.py         # Charts · Benchmark · Score-Verlauf · KN
│   ├── 03_feedback.py        # Betriebsfeedback-Formular + Auswertung
│   ├── 04_massnahmen.py      # Maßnahmen-Tracker (Kanban)
│   └── 05_admin.py           # Score-Automat · Import · Export
│
├── utils/
│   ├── db.py                 # Supabase-Verbindung + alle DB-Funktionen
│   ├── scoring.py            # RNVP Score-Algorithmus
│   └── map_utils.py          # Folium-Karte
│
└── .streamlit/
    ├── config.toml           # WAS-Theme (Blau/Orange)
    └── secrets.toml          # Supabase-Keys (nicht ins Git!)
```

---

## 🚀 Setup — Schritt für Schritt

### 1. Supabase einrichten (10 Minuten)

1. Kostenlosen Account anlegen: **https://supabase.com**
2. Neues Projekt erstellen: `mobilitaetsatlas-stormarn`
3. Im Dashboard → **SQL Editor** → Inhalt von `supabase_schema.sql` einfügen → **Run**
4. Unter **Project Settings → API** die zwei Werte kopieren:
   - `Project URL` → z.B. `https://abc123.supabase.co`
   - `anon public` Key

### 2. Lokale Umgebung einrichten

```bash
# Repository klonen / Ordner öffnen
cd mobilitaetsatlas

# Python-Umgebung erstellen
python -m venv .venv
source .venv/bin/activate        # Mac/Linux
# oder: .venv\Scripts\activate   # Windows

# Abhängigkeiten installieren
pip install -r requirements.txt

# .env Datei anlegen
cp .env.example .env
# Dann .env öffnen und Supabase-URL + Key eintragen
```

### 3. App starten

```bash
streamlit run app.py
```

Browser öffnet automatisch: **http://localhost:8501**

---

## ☁️ Deployment auf Streamlit Cloud (kostenlos)

1. Code auf GitHub pushen (`.env` **nicht** committen — steht in `.gitignore`)
2. **https://share.streamlit.io** → New app → GitHub-Repo wählen
3. Unter **Advanced settings → Secrets** eintragen:
   ```toml
   SUPABASE_URL = "https://dein-projekt.supabase.co"
   SUPABASE_ANON_KEY = "dein-key"
   ```
4. Deploy → fertig. App läuft unter `https://dein-name.streamlit.app`

---

## 📊 Seiten-Übersicht

| Seite | Beschreibung | Zielgruppe |
|-------|-------------|------------|
| 🗺 Karte | Interaktive Karte aller GE-Standorte mit Filtern | Alle |
| 📊 Analyse | Score-Verteilung, Benchmark, Zeitachse, Kosten-Nutzen | Planer, Politik |
| 📋 Feedback | Betriebsfeedback-Formular (→ direkt Supabase) | Betriebe |
| ⚡ Maßnahmen | Kanban-Board für Maßnahmen-Tracking | WAS-Team |
| ⚙ Admin | Score-Automat, Daten bearbeiten, Import/Export | WAS-Team |

---

## 🗄️ Datenbank-Tabellen

| Tabelle | Inhalt |
|---------|--------|
| `standorte` | Alle 20 GE-Standorte mit Scores, Koordinaten, ÖPNV-Daten |
| `firmen` | Unternehmen mit MA-Zahlen, Branche, Koordinaten |
| `feedback` | Betriebseingaben aus dem Feedback-Formular |
| `haltestellen` | Bus/Bahn-Haltestellen mit OSM-Qualitätsdaten |
| `ge_stops` | Zuordnung GE ↔ Haltestellen (mit Distanz) |
| `massnahmen` | Maßnahmen-Tracker mit Status-Workflow |
| `score_snapshots` | Historische Scores für Zeitachse |
| `gtfs_log` | Import-Protokoll für GTFS-Feeds |

---

## 🔧 Erste Daten einspielen

Nach dem Setup die Standortdaten importieren:

1. **Admin** → **Import** → JSON hochladen
2. Oder direkt in Supabase: **Table Editor** → `standorte` → Rows einfügen
3. Dann: **Admin** → **Score-Automat** → alle Scores berechnen

---

## 📦 Technologie-Stack

- **Streamlit** `1.35+` — Web-Framework
- **Supabase** `2.4+` — PostgreSQL-Datenbank as a Service
- **Folium** — Interaktive Leaflet-Karte in Python
- **Plotly** — Charts und Visualisierungen
- **Pandas** — Datenverarbeitung

---

*WAS Wirtschaftsförderung Kreis Stormarn · Mobilitätsatlas v1.0*
