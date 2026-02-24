"""
database.py – SQLite-Datenbankschicht für den Regional Radar
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path


DB_PATH = Path(__file__).parent / "data" / "radar.db"


def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Erstellt alle Tabellen, falls sie nicht existieren."""
    conn = get_connection()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            website TEXT UNIQUE,
            address TEXT,
            city TEXT,
            postal_code TEXT,
            lat REAL,
            lng REAL,
            industry TEXT,
            employee_count TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            kategorie TEXT,
            begruendung TEXT,
            ki_anwendungen TEXT,
            vertrauen INTEGER,
            biografie TEXT,
            raw_text TEXT,
            analyzed_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (company_id) REFERENCES companies(id)
        );

        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            event_type TEXT,
            message TEXT,
            alerted INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (company_id) REFERENCES companies(id)
        );

        CREATE TABLE IF NOT EXISTS trend_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_text TEXT,
            companies_count INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────────────────
# Companies
# ──────────────────────────────────────────────────────────

def upsert_company(name, website, address="", city="", postal_code="",
                   lat=None, lng=None, industry="", employee_count=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO companies (name, website, address, city, postal_code, lat, lng, industry, employee_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(website) DO UPDATE SET
            name=excluded.name, address=excluded.address,
            city=excluded.city, lat=excluded.lat, lng=excluded.lng,
            industry=excluded.industry, updated_at=datetime('now')
        RETURNING id
    """, (name, website, address, city, postal_code, lat, lng, industry, employee_count))
    row = c.fetchone()
    conn.commit()
    conn.close()
    return row[0] if row else None


def get_all_companies():
    conn = get_connection()
    rows = conn.execute("""
        SELECT c.*, a.kategorie, a.vertrauen, a.biografie, a.ki_anwendungen, a.analyzed_at
        FROM companies c
        LEFT JOIN analyses a ON a.id = (
            SELECT id FROM analyses WHERE company_id = c.id ORDER BY analyzed_at DESC LIMIT 1
        )
        ORDER BY c.name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_company_by_id(company_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM companies WHERE id=?", (company_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ──────────────────────────────────────────────────────────
# Analyses
# ──────────────────────────────────────────────────────────

def save_analysis(company_id, kategorie, begruendung, ki_anwendungen,
                  vertrauen, biografie, raw_text=""):
    conn = get_connection()
    conn.execute("""
        INSERT INTO analyses (company_id, kategorie, begruendung, ki_anwendungen,
                              vertrauen, biografie, raw_text)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (company_id, kategorie, begruendung,
          json.dumps(ki_anwendungen, ensure_ascii=False),
          vertrauen, biografie, raw_text))
    conn.commit()
    conn.close()


def get_analyses_for_company(company_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM analyses WHERE company_id=? ORDER BY analyzed_at DESC
    """, (company_id,)).fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        try:
            d["ki_anwendungen"] = json.loads(d["ki_anwendungen"] or "[]")
        except Exception:
            d["ki_anwendungen"] = []
        results.append(d)
    return results


# ──────────────────────────────────────────────────────────
# Activity Log
# ──────────────────────────────────────────────────────────

def log_event(company_id, event_type, message):
    conn = get_connection()
    conn.execute("""
        INSERT INTO activity_log (company_id, event_type, message)
        VALUES (?, ?, ?)
    """, (company_id, event_type, message))
    conn.commit()
    conn.close()


def get_recent_events(limit=50):
    conn = get_connection()
    rows = conn.execute("""
        SELECT l.*, c.name as company_name
        FROM activity_log l
        LEFT JOIN companies c ON c.id = l.company_id
        ORDER BY l.created_at DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_unalerted_events():
    conn = get_connection()
    rows = conn.execute("""
        SELECT l.*, c.name as company_name, c.website
        FROM activity_log l
        LEFT JOIN companies c ON c.id = l.company_id
        WHERE l.alerted = 0
        ORDER BY l.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_events_alerted(event_ids):
    conn = get_connection()
    conn.execute(f"""
        UPDATE activity_log SET alerted=1
        WHERE id IN ({','.join('?' * len(event_ids))})
    """, event_ids)
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────────────────
# Trend Reports
# ──────────────────────────────────────────────────────────

def save_trend_report(report_text, companies_count):
    conn = get_connection()
    conn.execute("""
        INSERT INTO trend_reports (report_text, companies_count)
        VALUES (?, ?)
    """, (report_text, companies_count))
    conn.commit()
    conn.close()


def get_latest_trend_report():
    conn = get_connection()
    row = conn.execute("""
        SELECT * FROM trend_reports ORDER BY created_at DESC LIMIT 1
    """).fetchone()
    conn.close()
    return dict(row) if row else None


# ──────────────────────────────────────────────────────────
# Stats
# ──────────────────────────────────────────────────────────

def get_stats():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    by_category = conn.execute("""
        SELECT a.kategorie, COUNT(*) as cnt
        FROM analyses a
        INNER JOIN (
            SELECT company_id, MAX(analyzed_at) as max_date
            FROM analyses GROUP BY company_id
        ) latest ON a.company_id = latest.company_id AND a.analyzed_at = latest.max_date
        GROUP BY a.kategorie
    """).fetchall()
    conn.close()
    return {
        "total_companies": total,
        "by_category": {r["kategorie"]: r["cnt"] for r in by_category}
    }


def update_company_analysis(company_id, kategorie, vertrauen, begruendung="",
                             ki_anwendungen=None, biografie="", analyzed_at=None):
    """Aktualisiert die Analyse einer Firma (für Re-Analyse)."""
    import json
    from datetime import datetime
    conn = get_connection()
    ts = analyzed_at or datetime.now().isoformat()
    ki_json = json.dumps(ki_anwendungen or [], ensure_ascii=False)
    conn.execute("""
        INSERT INTO analyses
            (company_id, kategorie, vertrauen, begruendung, ki_anwendungen, biografie, analyzed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (company_id, kategorie, vertrauen, begruendung, ki_json, biografie, ts))
    # analyzed_at in companies-Tabelle aktualisieren
    conn.execute("""
        UPDATE companies SET analyzed_at = ? WHERE id = ?
    """, (ts, company_id))
    conn.commit()
    conn.close()


def get_companies_needing_refresh(days: int = 30, max_confidence: int = 55) -> list:
    """Gibt Firmen zurück die Re-Analyse benötigen."""
    from datetime import datetime, timedelta
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    rows = conn.execute("""
        SELECT c.*, a.kategorie, a.vertrauen, a.analyzed_at as last_analyzed
        FROM companies c
        LEFT JOIN analyses a ON a.company_id = c.id
        WHERE c.website != ''
        AND (
            a.analyzed_at IS NULL
            OR a.analyzed_at < ?
            OR (a.kategorie IS NOT NULL AND a.vertrauen < ?)
        )
        ORDER BY a.vertrauen ASC
    """, (cutoff, max_confidence)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
