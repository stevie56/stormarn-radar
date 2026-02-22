# 🎯 Stormarn KI-Radar

Ein modulares, themenagnostisches Radar-System zur Analyse von KI-Aktivitäten
in Unternehmen einer Region.

---

## 🚀 Schnellstart

### 1. Abhängigkeiten installieren
```bash
pip install -r requirements.txt
```

### 2. OpenAI API Key setzen
```bash
export OPENAI_API_KEY="sk-..."
```

### 3. Dashboard starten
```bash
streamlit run app.py
```

Öffnet sich automatisch unter: **http://localhost:8501**

---

## 📁 Projektstruktur

```
stormarn_radar/
│
├── app.py              # 📊 Streamlit Dashboard (Hauptanwendung)
├── config.yaml         # ⚙️  ZENTRALE KONFIGURATION – hier Thema ändern
├── requirements.txt    # 📦 Python-Abhängigkeiten
│
├── scraper.py          # 🌐 Website-Scraper
├── analyzer.py         # 🤖 LLM-Analyse (OpenAI)
├── geo_mapper.py       # 📍 Geocodierung (OpenStreetMap, kostenlos)
├── database.py         # 💾 SQLite-Datenbank
├── alert.py            # 📧 E-Mail-Alert-System
├── pdf_export.py       # 📄 PDF-Steckbriefe
├── config_loader.py    # 🔧 Konfigurations-Loader
│
├── data/
│   └── radar.db        # SQLite-Datenbank (wird automatisch erstellt)
│
└── exports/            # Generierte PDFs
```

---

## 🔄 Thema wechseln

Das gesamte System wird über `config.yaml` gesteuert.
Um das Thema zu wechseln, reichen wenige Zeilen:

```yaml
# Von KI...
radar:
  name: "Stormarn KI-Radar"
  topic: "Künstliche Intelligenz"
  keywords: ["KI", "Machine Learning", "AI"]

# ...zu Wasserstoff:
radar:
  name: "Hamburg Wasserstoff-Radar"
  region: "Hamburg"
  topic: "Wasserstofftechnologie"
  keywords: ["Elektrolyse", "Brennstoffzelle", "H2"]
```

Dann Streamlit neu starten – fertig!

---

## 📊 Features

| Feature | Beschreibung |
|---------|-------------|
| 🌐 Scraper | Liest Firmenwebseiten automatisch (bis zu 3 Unterseiten) |
| 🤖 LLM-Analyse | GPT klassifiziert KI-Reife: Echter Einsatz / Integration / Buzzword |
| ✍️ Biografie | KI schreibt professionelle Kurzportraits |
| 📍 Geocodierung | Kostenlos via OpenStreetMap/Nominatim |
| 🗺️ Karte | Interaktive Folium-Karte mit Farbkodierung |
| 📧 Alerts | E-Mail-Benachrichtigungen bei neuen Aktivitäten |
| 📄 PDF | Professionelle Steckbriefe & Übersichtsliste |
| 📋 Log | Vollständiger Aktivitäts-Log |

---

## ⚙️ E-Mail-Alerts konfigurieren

In `config.yaml`:
```yaml
alerts:
  enabled: true
  from_email: "deine@gmail.com"
  to_email: "empfaenger@example.com"
```

Bei Gmail: [App-Passwort erstellen](https://myaccount.google.com/apppasswords)
(nicht das normale Gmail-Passwort verwenden!)

---

## 💡 Kosten

- **OpenStreetMap/Nominatim**: kostenlos
- **OpenAI**: ca. 0,001–0,01 € pro Unternehmensanalyse (gpt-4o-mini)
- **Streamlit**: kostenlos (lokal)
