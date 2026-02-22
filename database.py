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
            linkedin TEXT,
            xing TEXT,
            twitter TEXT,
            instagram TEXT,
            tags TEXT DEFAULT '[]',
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
            ki_aktiv INTEGER DEFAULT 0,
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
    # Migrationen für bestehende Datenbanken
    _migrate_columns(conn)

    conn.commit()
    conn.close()


def _migrate_columns(conn):
    """Fügt fehlende Spalten zur bestehenden Datenbank hinzu (idempotent)."""
    company_cols = {row[1] for row in conn.execute("PRAGMA table_info(companies)")}
    for col in ("linkedin", "xing", "twitter", "instagram"):
        if col not in company_cols:
            conn.execute(f"ALTER TABLE companies ADD COLUMN {col} TEXT")
    if "tags" not in company_cols:
        conn.execute("ALTER TABLE companies ADD COLUMN tags TEXT DEFAULT '[]'")

    analysis_cols = {row[1] for row in conn.execute("PRAGMA table_info(analyses)")}
    if "ki_aktiv" not in analysis_cols:
        conn.execute("ALTER TABLE analyses ADD COLUMN ki_aktiv INTEGER DEFAULT 0")


# ──────────────────────────────────────────────────────────
# Companies
# ──────────────────────────────────────────────────────────

def upsert_company(name, website, address="", city="", postal_code="",
                   lat=None, lng=None, industry="", employee_count="",
                   linkedin="", xing="", twitter="", instagram="",
                   tags=None):
    tags_json = json.dumps(tags or [], ensure_ascii=False)
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO companies (name, website, address, city, postal_code, lat, lng,
                               industry, employee_count, linkedin, xing, twitter, instagram, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(website) DO UPDATE SET
            name=excluded.name, address=excluded.address,
            city=excluded.city, lat=excluded.lat, lng=excluded.lng,
            industry=excluded.industry,
            linkedin=excluded.linkedin, xing=excluded.xing,
            twitter=excluded.twitter, instagram=excluded.instagram,
            tags=excluded.tags,
            updated_at=datetime('now')
        RETURNING id
    """, (name, website, address, city, postal_code, lat, lng,
          industry, employee_count, linkedin, xing, twitter, instagram, tags_json))
    row = c.fetchone()
    conn.commit()
    conn.close()
    return row[0] if row else None


def update_company_tags(company_id: int, tags: list):
    """Aktualisiert die Tags eines Unternehmens."""
    conn = get_connection()
    conn.execute(
        "UPDATE companies SET tags=?, updated_at=datetime('now') WHERE id=?",
        (json.dumps(tags, ensure_ascii=False), company_id)
    )
    conn.commit()
    conn.close()


def get_all_companies():
    conn = get_connection()
    rows = conn.execute("""
        SELECT c.*, a.kategorie, a.vertrauen, a.biografie, a.ki_anwendungen,
               a.ki_aktiv, a.analyzed_at
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
    ki_aktiv = 1 if kategorie in ("ECHTER_EINSATZ", "INTEGRATION") else 0
    conn = get_connection()
    conn.execute("""
        INSERT INTO analyses (company_id, kategorie, begruendung, ki_anwendungen,
                              vertrauen, biografie, raw_text, ki_aktiv)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (company_id, kategorie, begruendung,
          json.dumps(ki_anwendungen, ensure_ascii=False),
          vertrauen, biografie, raw_text, ki_aktiv))
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
# Tags
# ──────────────────────────────────────────────────────────

def get_all_tags() -> list:
    """Gibt alle einzigartigen Tags aus allen Unternehmen zurück (alphabetisch)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT tags FROM companies WHERE tags IS NOT NULL AND tags != '[]'"
    ).fetchall()
    conn.close()
    tags: set = set()
    for row in rows:
        try:
            tags.update(json.loads(row[0]))
        except Exception:
            pass
    return sorted(t for t in tags if t)


def get_tag_stats() -> dict:
    """Gibt je Tag die Anzahl der Unternehmen zurück, die diesen Tag haben."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT tags FROM companies WHERE tags IS NOT NULL AND tags != '[]'"
    ).fetchall()
    conn.close()
    counts: dict = {}
    for row in rows:
        try:
            for tag in json.loads(row[0]):
                if tag:
                    counts[tag] = counts.get(tag, 0) + 1
        except Exception:
            pass
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))


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
