"""
Stormarn KI-Radar – Komplette Single-File Version
Alles in einer Datei – kein Import-Fehler möglich!
"""
import os
import io
import json
import re
import time
import sqlite3
import smtplib
import requests
import pandas as pd
import streamlit as st
import folium
from datetime import datetime, timedelta
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, quote_plus
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from streamlit_folium import st_folium
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas as rl_canvas

# ══════════════════════════════════════════════════════════════
# KONFIGURATION
# ══════════════════════════════════════════════════════════════

RADAR_NAME    = "Stormarn KI-Radar"
RADAR_REGION  = "Kreis Stormarn"
RADAR_TOPIC   = "Künstliche Intelligenz"
LLM_MODEL     = "gpt-4o-mini"
DB_PATH       = "stormarn_radar.db"

KI_KEYWORDS = [
    "Künstliche Intelligenz", "Machine Learning", "Deep Learning",
    "AI", " KI ", "Automatisierung", "neuronale Netze",
    "Natural Language Processing", "Computer Vision",
    "Predictive Analytics", "ChatGPT", "Large Language Model", "LLM"
]

CLASSIFICATION_PROMPT = """Du analysierst Unternehmenswebseiten auf echten KI-Einsatz im Kreis Stormarn.

Klassifiziere das Unternehmen in eine der folgenden Kategorien:
- "ECHTER_EINSATZ": Konkretes KI-Produkt, Eigenentwicklung oder nachweisbarer produktiver Einsatz
- "INTEGRATION": Nutzt KI-Tools von Drittanbietern (z.B. ChatGPT, Copilot, KI-Software)
- "BUZZWORD": Erwähnt KI, ohne konkreten nachweisbaren Einsatz
- "KEIN_KI": Kein KI-Bezug gefunden

Antworte NUR als JSON:
{"kategorie": "...", "begruendung": "...", "ki_anwendungen": ["...", "..."], "vertrauen": 0-100}"""

BIOGRAPHY_PROMPT = """Schreibe eine professionelle Kurzbiografie (max. 120 Wörter) eines Unternehmens 
aus dem Kreis Stormarn mit Fokus auf dessen KI-Aktivitäten.
Stil: sachlich, informativ. Beginne direkt mit dem Firmennamen."""

# Farben
C_BLUE   = colors.Color(0.102, 0.322, 0.463)
C_BMID   = colors.Color(0.18, 0.45, 0.65)
C_BLIGHT = colors.Color(0.87, 0.93, 0.97)
C_ORANGE = colors.Color(0.93, 0.58, 0.10)
C_GREEN  = colors.Color(0.13, 0.63, 0.30)
C_RED    = colors.Color(0.85, 0.25, 0.25)
C_GDARK  = colors.Color(0.25, 0.25, 0.25)
C_GMID   = colors.Color(0.55, 0.55, 0.55)
C_GLIGHT = colors.Color(0.95, 0.95, 0.95)
C_WHITE  = colors.white

KAT_COLORS = {
    "ECHTER_EINSATZ": C_GREEN,
    "INTEGRATION":    C_BMID,
    "BUZZWORD":       C_ORANGE,
    "KEIN_KI":        C_GMID,
}
KAT_LABELS = {
    "ECHTER_EINSATZ": "✅ Echter KI-Einsatz",
    "INTEGRATION":    "🔗 KI-Integration",
    "BUZZWORD":       "⚠️ KI-Buzzword",
    "KEIN_KI":        "❌ Kein KI",
}
KAT_ICONS = {
    "ECHTER_EINSATZ": "✅",
    "INTEGRATION":    "🔗",
    "BUZZWORD":       "⚠️",
    "KEIN_KI":        "❌",
}

# ══════════════════════════════════════════════════════════════
# DATENBANK
# ══════════════════════════════════════════════════════════════

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS companies (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        name          TEXT NOT NULL,
        website       TEXT DEFAULT '',
        address       TEXT DEFAULT '',
        city          TEXT DEFAULT '',
        postal_code   TEXT DEFAULT '',
        industry      TEXT DEFAULT '',
        employee_count TEXT DEFAULT '',
        created_at    TEXT DEFAULT (datetime('now')),
        analyzed_at   TEXT
    );
    CREATE TABLE IF NOT EXISTS analyses (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id  INTEGER NOT NULL,
        kategorie   TEXT,
        vertrauen   INTEGER DEFAULT 0,
        begruendung TEXT DEFAULT '',
        ki_anwendungen TEXT DEFAULT '[]',
        biografie   TEXT DEFAULT '',
        analyzed_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (company_id) REFERENCES companies(id)
    );
    CREATE TABLE IF NOT EXISTS events (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id  INTEGER,
        event_type  TEXT,
        message     TEXT,
        created_at  TEXT DEFAULT (datetime('now'))
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_company_name ON companies(name);
    """)
    conn.commit()
    conn.close()

def upsert_company(name, website="", address="", city="", postal_code="", industry="", employee_count=""):
    conn = get_db()
    conn.execute("""
        INSERT INTO companies (name, website, address, city, postal_code, industry, employee_count)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            website=excluded.website,
            address=excluded.address,
            city=excluded.city,
            postal_code=excluded.postal_code,
            industry=CASE WHEN excluded.industry != '' THEN excluded.industry ELSE industry END,
            employee_count=CASE WHEN excluded.employee_count != '' THEN excluded.employee_count ELSE employee_count END
    """, (name, website, address, city, postal_code, industry, employee_count))
    conn.commit()
    row = conn.execute("SELECT id FROM companies WHERE name=?", (name,)).fetchone()
    conn.close()
    return row["id"]

def save_analysis(company_id, kategorie, vertrauen, begruendung, ki_anwendungen, biografie=""):
    conn = get_db()
    ki_json = json.dumps(ki_anwendungen, ensure_ascii=False)
    ts = datetime.now().isoformat()
    conn.execute("DELETE FROM analyses WHERE company_id=?", (company_id,))
    conn.execute("""
        INSERT INTO analyses (company_id, kategorie, vertrauen, begruendung, ki_anwendungen, biografie, analyzed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (company_id, kategorie, vertrauen, begruendung, ki_json, biografie, ts))
    conn.execute("UPDATE companies SET analyzed_at=? WHERE id=?", (ts, company_id))
    conn.commit()
    conn.close()

def get_all_companies():
    conn = get_db()
    rows = conn.execute("""
        SELECT c.*, a.kategorie, a.vertrauen, a.begruendung,
               a.ki_anwendungen, a.biografie, a.analyzed_at as last_analyzed
        FROM companies c
        LEFT JOIN analyses a ON a.company_id = c.id
        ORDER BY c.name
    """).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("ki_anwendungen"):
            try:
                d["ki_anwendungen"] = json.loads(d["ki_anwendungen"])
            except Exception:
                d["ki_anwendungen"] = []
        else:
            d["ki_anwendungen"] = []
        result.append(d)
    return result

def log_event(company_id, event_type, message):
    conn = get_db()
    conn.execute("INSERT INTO events (company_id, event_type, message) VALUES (?, ?, ?)",
                 (company_id, event_type, message))
    conn.commit()
    conn.close()

def get_recent_events(limit=50):
    conn = get_db()
    rows = conn.execute("""
        SELECT e.*, c.name as company_name
        FROM events e LEFT JOIN companies c ON c.id = e.company_id
        ORDER BY e.created_at DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ══════════════════════════════════════════════════════════════
# SCRAPER
# ══════════════════════════════════════════════════════════════

SCRAPER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; StormarnKI-Radar/1.0)",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}

KI_SUBPAGES = [
    "ki", "ai", "innovation", "digital", "technologie", "technology",
    "forschung", "research", "automatisierung", "smart", "produkte",
    "loesungen", "solutions", "ueber-uns", "about", "news",
]

def clean_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script","style","nav","footer","header","aside","form","iframe"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()

def get_ki_links(base_url, soup, limit=5):
    base_domain = urlparse(base_url).netloc
    scored = {}
    for a in soup.find_all("a", href=True):
        full = urljoin(base_url, a["href"])
        if urlparse(full).netloc != base_domain or full == base_url:
            continue
        if any(full.endswith(e) for e in [".pdf",".jpg",".png",".zip"]):
            continue
        link_text = (a.get_text(strip=True) + " " + a["href"]).lower()
        for i, kw in enumerate(KI_SUBPAGES):
            if kw in link_text:
                scored[full] = max(scored.get(full, 0), len(KI_SUBPAGES) - i)
    return [u for u, _ in sorted(scored.items(), key=lambda x: x[1], reverse=True)][:limit]

def scrape_website(url):
    if not url.startswith("http"):
        url = "https://" + url
    result = {"url": url, "title": "", "text": "", "pages": 0, "error": None}
    try:
        resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        title = soup.find("title")
        result["title"] = title.get_text(strip=True) if title else ""
        texts = ["[Hauptseite]\n" + clean_text(resp.text)]
        result["pages"] = 1
        for link in get_ki_links(url, soup, limit=4):
            try:
                time.sleep(1)
                sub = requests.get(link, headers=SCRAPER_HEADERS, timeout=10)
                sub.raise_for_status()
                sub_text = clean_text(sub.text)
                if len(sub_text) > 100:
                    page_name = link.replace(url, "").strip("/") or "Unterseite"
                    texts.append(f"[{page_name}]\n{sub_text[:2000]}")
                    result["pages"] += 1
            except Exception:
                continue
        result["text"] = "\n\n".join(texts)[:12000]
    except requests.exceptions.ConnectionError:
        result["error"] = "Website nicht erreichbar"
    except requests.exceptions.Timeout:
        result["error"] = "Timeout"
    except Exception as e:
        result["error"] = str(e)[:100]
    return result

# ══════════════════════════════════════════════════════════════
# ANALYZER (OpenAI)
# ══════════════════════════════════════════════════════════════

def get_openai_client():
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY fehlt in den Streamlit Secrets!")
    return OpenAI(api_key=api_key)

def classify_company(name, text):
    try:
        client = get_openai_client()
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": CLASSIFICATION_PROMPT},
                {"role": "user", "content": f"Unternehmen: {name}\n\nWebsite-Text:\n{text[:4000]}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=600
        )
        result = json.loads(resp.choices[0].message.content)
        result.setdefault("kategorie", "UNBEKANNT")
        result.setdefault("begruendung", "")
        result.setdefault("ki_anwendungen", [])
        result.setdefault("vertrauen", 50)
        if isinstance(result["ki_anwendungen"], str):
            result["ki_anwendungen"] = [result["ki_anwendungen"]]
        return result
    except Exception as e:
        return {"kategorie": "UNBEKANNT", "begruendung": str(e), "ki_anwendungen": [], "vertrauen": 0}

def generate_biography(name, text, classification):
    try:
        client = get_openai_client()
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": BIOGRAPHY_PROMPT},
                {"role": "user", "content": f"Firma: {name}\nKI-Kategorie: {classification.get('kategorie')}\nKI-Anwendungen: {', '.join(classification.get('ki_anwendungen', []))}\n\nWebsite-Auszug:\n{text[:2500]}"}
            ],
            temperature=0.4,
            max_tokens=250
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return ""

def analyze_company_full(name, website, do_bio=True):
    scrape = scrape_website(website)
    if scrape["error"]:
        return None, scrape["error"]
    classification = classify_company(name, scrape["text"])
    if do_bio:
        classification["biografie"] = generate_biography(name, scrape["text"], classification)
    else:
        classification["biografie"] = ""
    classification["pages_scraped"] = scrape["pages"]
    return classification, None

# ══════════════════════════════════════════════════════════════
# GEOCODER
# ══════════════════════════════════════════════════════════════

def geocode_address(address, city, postal_code):
    query = f"{address}, {postal_code} {city}, Deutschland"
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": "StormarnKI-Radar/1.0"},
            timeout=8
        )
        data = resp.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None, None

# ══════════════════════════════════════════════════════════════
# PDF EXPORT
# ══════════════════════════════════════════════════════════════

def wrap_text(text, max_chars):
    words = text.split()
    lines, current = [], ""
    for word in words:
        if len(current) + len(word) + 1 <= max_chars:
            current = (current + " " + word).strip()
        else:
            if current: lines.append(current)
            current = word
    if current: lines.append(current)
    return lines

def draw_page_frame(c, date_str):
    w, h = A4
    c.setFillColor(C_BLUE)
    c.rect(0, h-2.0*cm, w, 2.0*cm, fill=1, stroke=0)
    c.setFillColor(C_ORANGE)
    c.rect(0, h-2.1*cm, w, 0.1*cm, fill=1, stroke=0)
    c.setFillColor(C_WHITE)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(2.5*cm, h-1.35*cm, RADAR_NAME)
    c.setFont("Helvetica", 8.5)
    c.drawRightString(w-2.5*cm, h-1.35*cm, date_str)
    c.setFillColor(C_BLUE)
    c.rect(0, 0, w, 1.2*cm, fill=1, stroke=0)
    c.setFillColor(C_WHITE)
    c.setFont("Helvetica", 7)
    c.drawString(2.5*cm, 0.45*cm, "Kreis Stormarn – Wirtschaftsförderung & Innovation | KI-Radar")
    c.drawRightString(w-2.5*cm, 0.45*cm, f"Erstellt: {datetime.now().strftime('%d.%m.%Y %H:%M')} Uhr")

def generate_profile_pdf(company):
    buf = io.BytesIO()
    w, h = A4
    c = rl_canvas.Canvas(buf, pagesize=A4)
    date_str = datetime.now().strftime("%d.%m.%Y")
    draw_page_frame(c, date_str)

    y = h - 2.7*cm
    c.setFillColor(C_BLUE)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(2.5*cm, y, str(company.get("name",""))[:45])

    industry = company.get("industry","")
    if industry:
        c.setFont("Helvetica", 9)
        c.setFillColor(C_GMID)
        c.drawString(2.5*cm, y-0.55*cm, str(industry)[:70])

    kat = company.get("kategorie","KEIN_KI") or "KEIN_KI"
    badge_col = KAT_COLORS.get(kat, C_GMID)
    badge_lbl = KAT_LABELS.get(kat, kat).replace("✅ ","").replace("🔗 ","").replace("⚠️ ","").replace("❌ ","")
    bx = w - 6*cm
    c.setFillColor(badge_col)
    c.roundRect(bx, y-0.3*cm, 3.3*cm, 0.85*cm, 4*mm, fill=1, stroke=0)
    c.setFillColor(C_WHITE)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(bx+1.65*cm, y-0.05*cm, badge_lbl)

    y -= 1.3*cm
    c.setStrokeColor(C_BLIGHT)
    c.setLineWidth(1.5)
    c.line(2.5*cm, y, w-2.5*cm, y)

    # Stammdaten
    y -= 0.55*cm
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(C_GMID)
    c.drawString(2.5*cm, y, "UNTERNEHMENSDATEN")
    y -= 0.45*cm

    addr = f"{company.get('address','')} {company.get('postal_code','')} {company.get('city','')}".strip()
    items = [
        ("Website", company.get("website","–")),
        ("Adresse", addr or "–"),
        ("Mitarbeiter", company.get("employee_count","–") or "–"),
    ]
    col2 = w/2 + 0.5*cm
    for i,(lbl,val) in enumerate(items):
        cx = 2.5*cm if i%2==0 else col2
        ry = y - (i//2)*0.52*cm
        c.setFont("Helvetica-Bold", 8); c.setFillColor(C_BMID)
        c.drawString(cx, ry, lbl+":")
        c.setFont("Helvetica", 8); c.setFillColor(C_GDARK)
        c.drawString(cx+2.3*cm, ry, str(val)[:50] if val else "–")
    y -= (len(items)//2+1)*0.52*cm + 0.3*cm

    # Score
    c.setStrokeColor(C_BLIGHT); c.setLineWidth(1)
    c.line(2.5*cm, y, w-2.5*cm, y)
    y -= 0.55*cm
    c.setFont("Helvetica-Bold", 8); c.setFillColor(C_GMID)
    c.drawString(2.5*cm, y, "KI-BEWERTUNG")
    y -= 0.5*cm

    vertrauen = int(company.get("vertrauen") or 0)
    c.setFont("Helvetica", 8.5); c.setFillColor(C_GDARK)
    c.drawString(2.5*cm, y, "Analyse-Sicherheit:")
    # Balken
    bar_w = 7*cm
    c.setFillColor(C_GLIGHT)
    c.roundRect(5.8*cm, y-0.05*cm, bar_w, 0.4*cm, 2*mm, fill=1, stroke=0)
    ratio = vertrauen/100
    fill_col = C_GREEN if ratio>=0.7 else (C_ORANGE if ratio>=0.4 else C_RED)
    if ratio > 0:
        c.setFillColor(fill_col)
        c.roundRect(5.8*cm, y-0.05*cm, bar_w*ratio, 0.4*cm, 2*mm, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 8); c.setFillColor(C_GDARK)
    c.drawString(5.8*cm+bar_w+0.3*cm, y, f"{vertrauen}/100")
    y -= 0.65*cm

    # KI-Dots
    c.setFont("Helvetica", 8.5); c.setFillColor(C_GDARK)
    c.drawString(2.5*cm, y, "KI-Reifegrad:")
    ki_score = min(10, vertrauen//10)
    for i in range(10):
        c.setFillColor(C_BMID if i < ki_score else C_GLIGHT)
        c.circle(5.8*cm+i*0.55*cm, y+0.15*cm, 0.18*cm, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 8.5); c.setFillColor(C_BLUE)
    c.drawString(5.8*cm+10*0.55*cm+0.2*cm, y, f"{ki_score}/10")
    y -= 0.9*cm

    # KI-Anwendungen
    ki_apps = company.get("ki_anwendungen") or []
    if isinstance(ki_apps, str):
        try: ki_apps = json.loads(ki_apps)
        except: ki_apps = []
    if ki_apps:
        c.setStrokeColor(C_BLIGHT); c.line(2.5*cm, y, w-2.5*cm, y)
        y -= 0.55*cm
        c.setFont("Helvetica-Bold", 8); c.setFillColor(C_GMID)
        c.drawString(2.5*cm, y, "IDENTIFIZIERTE KI-ANWENDUNGEN")
        y -= 0.45*cm
        for app in ki_apps[:5]:
            c.setFillColor(C_BMID); c.circle(2.8*cm, y+0.1*cm, 0.12*cm, fill=1, stroke=0)
            c.setFont("Helvetica", 8.5); c.setFillColor(C_GDARK)
            c.drawString(3.1*cm, y, str(app)[:80])
            y -= 0.45*cm
        y -= 0.2*cm

    # Analyse
    begruendung = company.get("begruendung","")
    if begruendung:
        c.setStrokeColor(C_BLIGHT); c.line(2.5*cm, y, w-2.5*cm, y)
        y -= 0.55*cm
        c.setFont("Helvetica-Bold", 8); c.setFillColor(C_GMID)
        c.drawString(2.5*cm, y, "KI-ANALYSE")
        y -= 0.45*cm
        lines = wrap_text(begruendung, 88)
        box_h = len(lines)*0.4*cm + 0.35*cm
        c.setFillColor(C_BLIGHT)
        c.roundRect(2.5*cm, y-box_h, w-5*cm, box_h, 3*mm, fill=1, stroke=0)
        c.setFont("Helvetica", 8.5); c.setFillColor(C_GDARK)
        for line in lines:
            c.drawString(2.9*cm, y-0.12*cm, line)
            y -= 0.4*cm
        y -= 0.5*cm

    # Biografie
    bio = company.get("biografie","")
    if bio and y > 4*cm:
        c.setStrokeColor(C_BLIGHT); c.line(2.5*cm, y, w-2.5*cm, y)
        y -= 0.55*cm
        c.setFont("Helvetica-Bold", 8); c.setFillColor(C_GMID)
        c.drawString(2.5*cm, y, "UNTERNEHMENSBIOGRAFIE")
        y -= 0.45*cm
        c.setFont("Helvetica", 8.5); c.setFillColor(C_GDARK)
        for line in wrap_text(bio, 90):
            if y < 2.5*cm: break
            c.drawString(2.5*cm, y, line)
            y -= 0.4*cm

    c.save()
    return buf.getvalue()

# ══════════════════════════════════════════════════════════════
# WIRTSCHAFTSDATEN IMPORT
# ══════════════════════════════════════════════════════════════

def load_wirtschaftsdaten(file_bytes):
    try:
        df = pd.read_excel(io.BytesIO(file_bytes))
        if "Name des Unternehmens" not in df.columns:
            return None, "Falsche Datei – Spalte 'Name des Unternehmens' fehlt"

        unique = df.drop_duplicates(subset=["Name des Unternehmens"]).copy()
        result = pd.DataFrame()
        result["name"] = unique["Name des Unternehmens"].fillna("").astype(str).str.strip()

        strasse = unique["Straße (*)"].fillna("").astype(str)
        hausnr  = unique["Hausnummer (*)"].fillna("").astype(str)
        strasse = strasse.apply(lambda x: "" if x in ["nan","NaN"] else x)
        hausnr  = hausnr.apply(lambda x: "" if x in ["nan","NaN"] else x)
        result["adresse"] = (strasse + " " + hausnr).str.strip()

        result["plz"] = unique["Postleitzahl"].fillna("").astype(str)\
            .str.replace(".0","",regex=False).str.strip()
        result["plz"] = result["plz"].apply(lambda x: "" if x in ["nan","NaN"] else x)

        result["ort"] = unique["Ort"].fillna("").astype(str).str.strip()
        result["ort"] = result["ort"].apply(lambda x: "" if x in ["nan","NaN"] else x)

        result["website"] = unique["Web Adresse (*)"].fillna("").astype(str).str.strip()
        result["website"] = result["website"].apply(lambda x:
            "" if x in ["nan","NaN","n.v.",""] else
            ("https://"+x if not x.startswith("http") else x))

        branche_col = "WZ 2008 - Haupttätigkeit - Beschreibung (*)"
        if branche_col in unique.columns:
            result["branche"] = unique[branche_col].fillna("").astype(str)
            result["branche"] = result["branche"].apply(
                lambda x: "" if x in ["nan","NaN"] else x[:80])
        else:
            result["branche"] = ""

        ma_col = "Anzahl der Mitarbeiter (Zuletzt angegebener Wert) (*)"
        if ma_col in unique.columns:
            result["mitarbeiter"] = unique[ma_col].fillna("").astype(str)\
                .str.replace(".0","",regex=False)
            result["mitarbeiter"] = result["mitarbeiter"].apply(
                lambda x: "" if x in ["nan","NaN","n.v."] else x)
        else:
            result["mitarbeiter"] = ""

        result = result[result["name"].str.len() > 2].reset_index(drop=True)
        return result, None
    except Exception as e:
        return None, str(e)

# ══════════════════════════════════════════════════════════════
# WOCHENBERICHT HTML
# ══════════════════════════════════════════════════════════════

def build_weekly_html(companies):
    analyzed = [c for c in companies if c.get("kategorie")]
    echter   = [c for c in analyzed if c.get("kategorie") == "ECHTER_EINSATZ"]
    integ    = [c for c in analyzed if c.get("kategorie") == "INTEGRATION"]
    total    = len(companies)
    ki_quote = round((len(echter)+len(integ))/total*100, 1) if total > 0 else 0

    week_ago = datetime.now() - timedelta(days=7)
    new_this_week = []
    for c in analyzed:
        try:
            ts = datetime.fromisoformat(str(c.get("created_at","")).split("+")[0])
            if ts > week_ago:
                new_this_week.append(c)
        except: pass

    top5 = sorted(echter, key=lambda x: x.get("vertrauen",0), reverse=True)[:5]

    rows_new = ""
    for c in new_this_week[:10]:
        lbl = KAT_LABELS.get(c.get("kategorie",""), "")
        rows_new += f"<tr><td>{c['name']}</td><td>{c.get('city','')}</td><td>{lbl}</td><td>{c.get('vertrauen',0)}%</td></tr>"

    rows_top = ""
    for i,c in enumerate(top5, 1):
        rows_top += f"<tr><td>#{i}</td><td><b>{c['name']}</b></td><td>{c.get('city','')}</td><td>{c.get('vertrauen',0)}%</td></tr>"

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>body{{font-family:Arial,sans-serif;max-width:600px;margin:0 auto}}
.hdr{{background:#1a5276;color:white;padding:20px}}
.stat{{display:inline-block;background:#f0f4f8;border-radius:8px;padding:12px 20px;margin:6px;text-align:center}}
.num{{font-size:28px;font-weight:bold;color:#1a5276}}
table{{width:100%;border-collapse:collapse;margin:10px 0}}
th{{background:#1a5276;color:white;padding:8px;text-align:left}}
td{{padding:7px;border-bottom:1px solid #eee}}
.ftr{{background:#f8f9fa;padding:12px;text-align:center;font-size:11px;color:#999}}</style>
</head><body>
<div class="hdr"><h2 style="margin:0">📊 {RADAR_NAME}</h2>
<p style="margin:4px 0 0;opacity:.85">Wochenbericht · {datetime.now().strftime('%d. %B %Y')}</p></div>
<div style="padding:16px">
<div class="stat"><div class="num">{total}</div><div>Gesamt</div></div>
<div class="stat"><div class="num">{len(analyzed)}</div><div>Analysiert</div></div>
<div class="stat"><div class="num" style="color:#1e8449">{len(echter)}</div><div>Echter Einsatz</div></div>
<div class="stat"><div class="num">{ki_quote}%</div><div>KI-Quote</div></div>
</div>
{"<div style='padding:0 16px'><h3>🆕 Neue Firmen diese Woche</h3><table><tr><th>Firma</th><th>Stadt</th><th>Status</th><th>Score</th></tr>"+rows_new+"</table></div>" if new_this_week else ""}
{"<div style='padding:0 16px'><h3>🏆 Top KI-Vorreiter</h3><table><tr><th>#</th><th>Firma</th><th>Stadt</th><th>Score</th></tr>"+rows_top+"</table></div>" if top5 else ""}
<div class="ftr">{RADAR_NAME} · Automatischer Wochenbericht · {datetime.now().strftime('%d.%m.%Y %H:%M')}</div>
</body></html>"""

# ══════════════════════════════════════════════════════════════
# STREAMLIT APP
# ══════════════════════════════════════════════════════════════

st.set_page_config(page_title=RADAR_NAME, page_icon="📡", layout="wide")
init_db()

# Sidebar
with st.sidebar:
    st.markdown(f"## 📡 {RADAR_NAME}")
    st.markdown(f"*{RADAR_REGION}*")
    st.markdown("---")
    page = st.radio("Navigation", [
        "📊 Dashboard",
        "🏢 Unternehmen",
        "🗺️ Karte",
        "➕ Neu analysieren",
        "📊 Wirtschaftsdaten",
        "📈 Trends & Statistik",
        "🏅 KI-Ranking",
        "🌍 Regionalvergleich",
        "📄 PDF-Export",
        "📧 Wochenbericht",
        "📋 Aktivitätslog",
        "⚙️ Einstellungen",
    ], label_visibility="collapsed")
    st.markdown("---")
    companies_all = get_all_companies()
    analyzed_all = [c for c in companies_all if c.get("kategorie")]
    st.metric("🏢 Firmen", len(companies_all))
    st.metric("🔍 Analysiert", len(analyzed_all))
    if analyzed_all:
        echter_ct = len([c for c in analyzed_all if c.get("kategorie")=="ECHTER_EINSATZ"])
        st.metric("✅ Echter KI-Einsatz", echter_ct)

# ── DASHBOARD ──────────────────────────────────────────────
if page == "📊 Dashboard":
    st.title(f"📡 {RADAR_NAME}")
    st.markdown(f"*KI-Aktivitäten im {RADAR_REGION} – Live-Übersicht*")

    companies = get_all_companies()
    analyzed  = [c for c in companies if c.get("kategorie")]
    echter    = [c for c in analyzed if c.get("kategorie")=="ECHTER_EINSATZ"]
    integ     = [c for c in analyzed if c.get("kategorie")=="INTEGRATION"]
    buzzword  = [c for c in analyzed if c.get("kategorie")=="BUZZWORD"]
    kein_ki   = [c for c in analyzed if c.get("kategorie")=="KEIN_KI"]
    ki_quote  = round((len(echter)+len(integ))/len(analyzed)*100,1) if analyzed else 0

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("🏢 Gesamt", len(companies))
    c2.metric("🔍 Analysiert", len(analyzed))
    c3.metric("✅ Echter Einsatz", len(echter))
    c4.metric("🔗 Integration", len(integ))
    c5.metric("📊 KI-Quote", f"{ki_quote}%")

    if analyzed:
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📊 KI-Kategorien")
            cat_data = pd.DataFrame({
                "Kategorie": ["Echter Einsatz","Integration","Buzzword","Kein KI"],
                "Anzahl":    [len(echter), len(integ), len(buzzword), len(kein_ki)]
            })
            st.bar_chart(cat_data.set_index("Kategorie"))

        with col2:
            st.subheader("🏆 Top KI-Vorreiter")
            for c in sorted(echter, key=lambda x: x.get("vertrauen",0), reverse=True)[:8]:
                v = c.get("vertrauen",0)
                st.markdown(f"**{c['name']}** – {c.get('city','')} · Score: {v}%")
                st.progress(v/100)

        st.markdown("---")
        st.subheader("📋 Letzte Aktivitäten")
        events = get_recent_events(10)
        for e in events:
            st.caption(f"🕐 {e.get('created_at','')} · **{e.get('company_name','')}** · {e.get('message','')}")

# ── UNTERNEHMEN ────────────────────────────────────────────
elif page == "🏢 Unternehmen":
    st.header("🏢 Unternehmen")
    companies = get_all_companies()

    col1,col2,col3 = st.columns(3)
    with col1:
        search = st.text_input("🔍 Suche", placeholder="Firmenname...")
    with col2:
        kat_filter = st.selectbox("Kategorie", ["Alle","ECHTER_EINSATZ","INTEGRATION","BUZZWORD","KEIN_KI"])
    with col3:
        city_filter = st.selectbox("Stadt", ["Alle"] + sorted(set(c.get("city","") for c in companies if c.get("city"))))

    filtered = companies
    if search:
        filtered = [c for c in filtered if search.lower() in c.get("name","").lower()]
    if kat_filter != "Alle":
        filtered = [c for c in filtered if c.get("kategorie") == kat_filter]
    if city_filter != "Alle":
        filtered = [c for c in filtered if c.get("city") == city_filter]

    st.info(f"**{len(filtered)}** Unternehmen")

    for c in filtered[:100]:
        icon = KAT_ICONS.get(c.get("kategorie",""), "❓")
        label = KAT_LABELS.get(c.get("kategorie",""), "Nicht analysiert")
        with st.expander(f"{icon} {c['name']} – {c.get('city','')}"):
            col1,col2,col3 = st.columns(3)
            col1.metric("Kategorie", label)
            col2.metric("Vertrauen", f"{c.get('vertrauen',0)}%")
            col3.metric("Branche", c.get("industry","–") or "–")
            if c.get("website"):
                st.markdown(f"🌐 [{c['website']}]({c['website']})")
            if c.get("begruendung"):
                st.markdown(f"**Analyse:** {c['begruendung']}")
            if c.get("ki_anwendungen"):
                st.markdown("**KI-Anwendungen:** " + " · ".join(c["ki_anwendungen"]))
            if c.get("biografie"):
                st.markdown(f"*{c['biografie']}*")

# ── KARTE ──────────────────────────────────────────────────
elif page == "🗺️ Karte":
    st.header("🗺️ KI-Karte Stormarn")
    companies = get_all_companies()
    analyzed  = [c for c in companies if c.get("kategorie") and c.get("lat") and c.get("lon")]

    m = folium.Map(location=[53.7, 10.25], zoom_start=10)
    colors_map = {"ECHTER_EINSATZ":"green","INTEGRATION":"blue","BUZZWORD":"orange","KEIN_KI":"gray"}

    for c in analyzed:
        try:
            folium.CircleMarker(
                location=[float(c["lat"]), float(c["lon"])],
                radius=8,
                color=colors_map.get(c.get("kategorie",""), "gray"),
                fill=True, fill_opacity=0.8,
                popup=folium.Popup(f"<b>{c['name']}</b><br>{KAT_LABELS.get(c.get('kategorie',''),'')}<br>Score: {c.get('vertrauen',0)}%", max_width=200)
            ).add_to(m)
        except Exception:
            continue

    st_folium(m, width=None, height=500)
    st.info(f"**{len(analyzed)}** Firmen auf der Karte · Grün=Echter Einsatz · Blau=Integration · Orange=Buzzword")

# ── NEU ANALYSIEREN ────────────────────────────────────────
elif page == "➕ Neu analysieren":
    st.header("➕ Neues Unternehmen analysieren")

    if not os.getenv("OPENAI_API_KEY"):
        st.error("⚠️ OpenAI API Key fehlt! Bitte in den Streamlit Secrets eintragen: OPENAI_API_KEY = 'sk-...'")
    else:
        with st.form("analyze_form"):
            name    = st.text_input("Firmenname *", placeholder="z.B. Minimax GmbH")
            website = st.text_input("Website *", placeholder="z.B. www.minimax.com")
            col1,col2,col3 = st.columns(3)
            city    = col1.text_input("Stadt", placeholder="Bad Oldesloe")
            plz     = col2.text_input("PLZ", placeholder="23843")
            branch  = col3.text_input("Branche", placeholder="Brandschutz")
            do_bio  = st.checkbox("Biografie erstellen", value=True)
            submit  = st.form_submit_button("🔍 Analysieren", type="primary")

        if submit and name and website:
            with st.spinner(f"Analysiere {name}..."):
                company_id = upsert_company(name, website, city=city, postal_code=plz, industry=branch)
                classification, error = analyze_company_full(name, website, do_bio)

            if error:
                st.error(f"Fehler: {error}")
            else:
                save_analysis(company_id, classification["kategorie"],
                              classification["vertrauen"], classification["begruendung"],
                              classification.get("ki_anwendungen",[]),
                              classification.get("biografie",""))
                log_event(company_id, "ANALYSE", f"Neu analysiert: {classification['kategorie']}")

                st.success("✅ Analyse abgeschlossen!")
                kat = classification["kategorie"]
                col1,col2,col3 = st.columns(3)
                col1.metric("Kategorie", KAT_LABELS.get(kat, kat))
                col2.metric("Vertrauen", f"{classification['vertrauen']}%")
                col3.metric("Seiten gescannt", classification.get("pages_scraped",1))

                if classification.get("ki_anwendungen"):
                    st.markdown("**KI-Anwendungen:**")
                    for app in classification["ki_anwendungen"]:
                        st.markdown(f"• {app}")

                if classification.get("begruendung"):
                    st.info(classification["begruendung"])

                if classification.get("biografie"):
                    st.markdown("---")
                    st.markdown(f"*{classification['biografie']}*")

# ── WIRTSCHAFTSDATEN ───────────────────────────────────────
elif page == "📊 Wirtschaftsdaten":
    st.header("📊 Wirtschaftsdaten Stormarn – 8.838 Unternehmen")
    st.markdown("Lade die Wirtschaftsdaten-Excel hoch und importiere alle Stormarn-Firmen.")

    uploaded = st.file_uploader("Wirtschaftsdaten_Stormarn.xlsx", type=["xlsx"])

    if uploaded:
        with st.spinner("Datei wird gelesen..."):
            df, error = load_wirtschaftsdaten(uploaded.read())

        if error:
            st.error(f"Fehler: {error}")
        else:
            total = len(df)
            with_web = int((df["website"] != "").sum())

            c1,c2,c3 = st.columns(3)
            c1.metric("🏢 Gesamt", f"{total:,}")
            c2.metric("🌐 Mit Website", f"{with_web:,}")
            c3.metric("📍 Ohne Website", f"{total-with_web:,}")

            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                only_web = st.checkbox("Nur Firmen mit Website", value=True)
            with col2:
                cities = sorted(df["ort"].unique().tolist())
                sel_cities = st.multiselect("Städte filtern", cities, default=[])

            filtered = df.copy()
            if only_web:
                filtered = filtered[filtered["website"] != ""]
            if sel_cities:
                filtered = filtered[filtered["ort"].isin(sel_cities)]

            st.info(f"**{len(filtered):,}** Unternehmen nach Filter")
            st.dataframe(filtered[["name","ort","website","branche","mitarbeiter"]].head(100),
                        use_container_width=True, hide_index=True)

            st.markdown("---")
            if st.button("💾 Alle in Datenbank speichern", type="primary"):
                progress = st.progress(0)
                saved = 0
                for i, row in filtered.iterrows():
                    try:
                        upsert_company(row["name"], row.get("website",""),
                                      row.get("adresse",""), row.get("ort",""),
                                      row.get("plz",""), row.get("branche",""),
                                      str(row.get("mitarbeiter","")))
                        saved += 1
                        if saved % 200 == 0:
                            progress.progress(saved/len(filtered))
                    except Exception:
                        continue
                progress.progress(1.0)
                st.success(f"✅ {saved:,} Unternehmen gespeichert!")
                log_event(None, "WIRTSCHAFTSDATEN_IMPORT", f"{saved} Firmen importiert")

# ── TRENDS ─────────────────────────────────────────────────
elif page == "📈 Trends & Statistik":
    st.header("📈 Trends & Statistik")
    companies = get_all_companies()
    analyzed  = [c for c in companies if c.get("kategorie")]

    if not analyzed:
        st.info("Noch keine Firmen analysiert.")
    else:
        # Branchen-Analyse
        st.subheader("🏭 KI nach Branchen")
        branchen = {}
        for c in analyzed:
            if c.get("kategorie") in ("ECHTER_EINSATZ","INTEGRATION"):
                b = (c.get("industry") or "Unbekannt")[:50]
                branchen[b] = branchen.get(b,0) + 1

        if branchen:
            top_b = sorted(branchen.items(), key=lambda x: x[1], reverse=True)[:10]
            b_df = pd.DataFrame(top_b, columns=["Branche","KI-Firmen"])
            st.bar_chart(b_df.set_index("Branche"))

        # Städte-Analyse
        st.subheader("📍 KI nach Städten")
        staedte = {}
        for c in analyzed:
            if c.get("kategorie") in ("ECHTER_EINSATZ","INTEGRATION"):
                s = c.get("city","Unbekannt") or "Unbekannt"
                staedte[s] = staedte.get(s,0) + 1

        if staedte:
            top_s = sorted(staedte.items(), key=lambda x: x[1], reverse=True)[:10]
            s_df = pd.DataFrame(top_s, columns=["Stadt","KI-Firmen"])
            st.bar_chart(s_df.set_index("Stadt"))

        # Kategorie-Übersicht
        st.subheader("📊 Kategorie-Verteilung")
        kat_count = {}
        for c in analyzed:
            k = c.get("kategorie","UNBEKANNT")
            kat_count[k] = kat_count.get(k,0) + 1
        for kat, cnt in sorted(kat_count.items(), key=lambda x: x[1], reverse=True):
            pct = round(cnt/len(analyzed)*100,1)
            st.markdown(f"{KAT_ICONS.get(kat,'?')} **{KAT_LABELS.get(kat,kat)}**: {cnt} Firmen ({pct}%)")
            st.progress(cnt/len(analyzed))

# ── KI-RANKING ──────────────────────────────────────────────
elif page == "🏅 KI-Ranking":
    st.header("🏅 KI-Ranking Stormarn")
    companies = get_all_companies()
    analyzed  = [c for c in companies if c.get("kategorie")]

    if not analyzed:
        st.info("Noch keine Firmen analysiert.")
    else:
        scored = sorted(analyzed, key=lambda x: (
            {"ECHTER_EINSATZ":3,"INTEGRATION":2,"BUZZWORD":1,"KEIN_KI":0}.get(x.get("kategorie",""),0),
            x.get("vertrauen",0)
        ), reverse=True)

        st.subheader("🏆 Top 3")
        medals = ["🥇","🥈","🥉"]
        cols = st.columns(3)
        for i,(col,firm) in enumerate(zip(cols, scored[:3])):
            with col:
                st.metric(f"{medals[i]} {firm['name'][:20]}",
                         f"{firm.get('vertrauen',0)}% Score",
                         KAT_LABELS.get(firm.get("kategorie",""),""))

        st.markdown("---")
        min_score = st.slider("Mindest-Score", 0, 100, 0)
        filtered = [c for c in scored if (c.get("vertrauen") or 0) >= min_score]

        for i,firm in enumerate(filtered, 1):
            icon = KAT_ICONS.get(firm.get("kategorie",""),"❓")
            v    = firm.get("vertrauen",0)
            with st.expander(f"#{i} {icon} {firm['name']} – {v}%"):
                col1,col2 = st.columns(2)
                col1.metric("Vertrauen", f"{v}%")
                col2.metric("Stadt", firm.get("city","–"))
                st.progress(v/100)
                if firm.get("ki_anwendungen"):
                    st.markdown("**KI:** " + " · ".join(firm["ki_anwendungen"][:3]))

# ── REGIONALVERGLEICH ───────────────────────────────────────
elif page == "🌍 Regionalvergleich":
    st.header("🌍 Regionalvergleich – Stormarn vs. Schleswig-Holstein")

    companies = get_all_companies()
    analyzed  = [c for c in companies if c.get("kategorie")]
    echter    = len([c for c in analyzed if c.get("kategorie")=="ECHTER_EINSATZ"])
    integ     = len([c for c in analyzed if c.get("kategorie")=="INTEGRATION"])
    ki_quote  = round((echter+integ)/len(analyzed)*100,1) if analyzed else 0

    benchmarks = {
        "Kreis Stormarn (Radar)": ki_quote if analyzed else 8,
        "Kreis Pinneberg":         7,
        "Kreis Segeberg":          6,
        "Stadt Lübeck":           10,
        "Kreis Herzogtum Lauenburg":5,
        "Hamburg (Metropole)":    18,
    }

    if analyzed:
        st.success(f"🎯 Echte KI-Quote aus {len(analyzed)} analysierten Firmen: **{ki_quote}%**")

    st.subheader("📊 KI-Quote Vergleich")
    b_df = pd.DataFrame(list(benchmarks.items()), columns=["Region","KI-Quote (%)"])
    b_df = b_df.sort_values("KI-Quote (%)", ascending=True)
    st.bar_chart(b_df.set_index("Region"))

    ranking = sorted(benchmarks.items(), key=lambda x: x[1], reverse=True)
    st.subheader("🏆 Ranking")
    for i,(region, quote) in enumerate(ranking, 1):
        prefix = "👉 **" if "Stormarn" in region else ""
        suffix = "**" if "Stormarn" in region else ""
        st.markdown(f"{i}. {prefix}{region}{suffix}: **{quote}%**")

# ── PDF-EXPORT ─────────────────────────────────────────────
elif page == "📄 PDF-Export":
    st.header("📄 PDF-Export")
    companies = get_all_companies()
    analyzed  = [c for c in companies if c.get("kategorie")]

    if not analyzed:
        st.info("Erst Firmen analysieren.")
    else:
        selected = st.selectbox("Firma auswählen", [c["name"] for c in analyzed])
        firm = next((c for c in analyzed if c["name"] == selected), {})

        if firm:
            col1,col2,col3 = st.columns(3)
            col1.metric("Kategorie", KAT_LABELS.get(firm.get("kategorie",""),"–"))
            col2.metric("Vertrauen", f"{firm.get('vertrauen',0)}%")
            col3.metric("Stadt", firm.get("city","–"))

            if st.button("📄 PDF erstellen", type="primary"):
                with st.spinner("PDF wird erstellt..."):
                    pdf_bytes = generate_profile_pdf(firm)
                st.download_button(
                    "⬇️ PDF herunterladen",
                    data=pdf_bytes,
                    file_name=f"Steckbrief_{selected.replace(' ','_')}.pdf",
                    mime="application/pdf"
                )
                st.success("✅ Fertig!")

# ── WOCHENBERICHT ──────────────────────────────────────────
elif page == "📧 Wochenbericht":
    st.header("📧 Wochenbericht")
    companies = get_all_companies()

    tab1, tab2 = st.tabs(["👁️ Vorschau", "📤 Per E-Mail senden"])

    with tab1:
        if st.button("🔄 Vorschau generieren"):
            html = build_weekly_html(companies)
            st.components.v1.html(html, height=700, scrolling=True)

    with tab2:
        st.markdown("E-Mail via Streamlit Secrets konfigurieren:")
        st.code("SMTP_USER = 'deine@gmail.com'\nSMTP_PASSWORD = 'app-passwort'\nREPORT_EMAIL = 'empfaenger@example.com'")

        recipient = st.text_input("Empfänger", value=os.getenv("REPORT_EMAIL",""))
        if st.button("📤 Jetzt senden", type="primary"):
            smtp_user = os.getenv("SMTP_USER","")
            smtp_pass = os.getenv("SMTP_PASSWORD","")
            if not smtp_user or not smtp_pass:
                st.error("SMTP nicht konfiguriert!")
            else:
                try:
                    html = build_weekly_html(companies)
                    msg = MIMEMultipart("alternative")
                    msg["Subject"] = f"📊 {RADAR_NAME} Wochenbericht – {datetime.now().strftime('%d.%m.%Y')}"
                    msg["From"] = smtp_user
                    msg["To"] = recipient
                    msg.attach(MIMEText(html, "html", "utf-8"))
                    with smtplib.SMTP("smtp.gmail.com", 587) as server:
                        server.starttls()
                        server.login(smtp_user, smtp_pass)
                        server.send_message(msg)
                    st.success(f"✅ Bericht gesendet an {recipient}!")
                except Exception as e:
                    st.error(f"Fehler: {e}")

# ── AKTIVITÄTSLOG ──────────────────────────────────────────
elif page == "📋 Aktivitätslog":
    st.header("📋 Aktivitätslog")
    events = get_recent_events(100)
    if events:
        for e in events:
            st.markdown(f"🕐 `{e.get('created_at','')}` · **{e.get('company_name','System')}** · {e.get('event_type','')} · {e.get('message','')}")
    else:
        st.info("Noch keine Aktivitäten.")

# ── EINSTELLUNGEN ──────────────────────────────────────────
elif page == "⚙️ Einstellungen":
    st.header("⚙️ Einstellungen")

    st.subheader("🔑 API Key Status")
    if os.getenv("OPENAI_API_KEY"):
        st.success("✅ OpenAI API Key gesetzt")
    else:
        st.error("❌ OpenAI API Key fehlt!")
        st.markdown("In Streamlit Secrets eintragen:")
        st.code("OPENAI_API_KEY = 'sk-...'")

    st.markdown("---")
    st.subheader("🗄️ Datenbank")
    companies = get_all_companies()
    analyzed  = [c for c in companies if c.get("kategorie")]
    col1,col2,col3 = st.columns(3)
    col1.metric("Firmen gesamt", len(companies))
    col2.metric("Analysiert", len(analyzed))
    col3.metric("Nicht analysiert", len(companies)-len(analyzed))

    if st.button("🗑️ Datenbank leeren", type="secondary"):
        if st.session_state.get("confirm_delete"):
            conn = get_db()
            conn.executescript("DELETE FROM analyses; DELETE FROM companies; DELETE FROM events;")
            conn.commit(); conn.close()
            st.success("Datenbank geleert!")
            st.session_state["confirm_delete"] = False
        else:
            st.session_state["confirm_delete"] = True
            st.warning("Nochmal klicken zum Bestätigen!")

    st.markdown("---")
    st.subheader("ℹ️ System-Info")
    st.markdown(f"- **Radar:** {RADAR_NAME}")
    st.markdown(f"- **Region:** {RADAR_REGION}")
    st.markdown(f"- **KI-Modell:** {LLM_MODEL}")
    st.markdown(f"- **Version:** v7 Single-File")
