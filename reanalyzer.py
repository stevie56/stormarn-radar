"""
reanalyzer.py – Zweiter Analyse-Durchlauf & Daten-Aktualität
1. Unsichere Fälle (Vertrauen < 50%) nochmal tief analysieren
2. Firmen älter als 30 Tage automatisch neu analysieren
"""
from datetime import datetime, timedelta
import time

import database as db
import scraper
import analyzer

LOW_CONFIDENCE_THRESHOLD = 50
STALE_DAYS = 30


def get_uncertain_companies(companies: list = None) -> list:
    """Firmen mit Vertrauen < 50% oder unbekannter Kategorie."""
    if companies is None:
        companies = db.get_all_companies()
    return [c for c in companies if (
        c.get("kategorie") in ("UNBEKANNT", None, "") or
        int(c.get("vertrauen") or 0) < LOW_CONFIDENCE_THRESHOLD
    ) and c.get("website")]


def reanalyze_company(company: dict, progress_callback=None) -> dict:
    """
    Tiefer zweiter Analyse-Durchlauf – mehr Unterseiten, mehr Kontext.
    """
    name = company.get("name", "")
    website = company.get("website", "")

    if progress_callback:
        progress_callback(f"🔬 Tiefenanalyse: {name}")

    # Deep-Scraping
    scrape_result = scraper.scrape_website(website, deep=True)

    if scrape_result.get("error"):
        return {"success": False, "error": scrape_result["error"], "company": name}

    classification = analyzer.classify_company(name, scrape_result["text"])
    biografie = analyzer.generate_biography(name, scrape_result["text"], classification)
    classification["biografie"] = biografie
    classification["pages_scraped"] = scrape_result.get("pages_scraped", 0)
    classification["reanalyzed_at"] = datetime.now().isoformat()

    try:
        db.update_analysis(
            company_id=company.get("id"),
            kategorie=classification["kategorie"],
            vertrauen=classification["vertrauen"],
            begruendung=classification["begruendung"],
            ki_anwendungen=classification.get("ki_anwendungen", []),
            biografie=biografie
        )
    except Exception as e:
        print(f"DB-Fehler ({name}): {e}")

    return {
        "success":        True,
        "company":        name,
        "old_vertrauen":  int(company.get("vertrauen") or 0),
        "new_vertrauen":  classification["vertrauen"],
        "old_kategorie":  company.get("kategorie", ""),
        "new_kategorie":  classification["kategorie"],
        "pages_scanned":  scrape_result.get("pages_scraped", 0),
        "subpages":       scrape_result.get("subpages", []),
    }


def run_second_pass(progress_callback=None) -> list:
    """Zweiter Durchlauf für alle unsicheren Firmen."""
    uncertain = get_uncertain_companies()
    results = []
    for i, company in enumerate(uncertain):
        if progress_callback:
            progress_callback(i + 1, len(uncertain),
                              f"Tiefenanalyse {i+1}/{len(uncertain)}: {company['name']}")
        results.append(reanalyze_company(company))
        time.sleep(2)
    return results


def get_stale_companies(companies: list = None, days: int = STALE_DAYS) -> list:
    """Firmen die seit mehr als X Tagen nicht analysiert wurden."""
    if companies is None:
        companies = db.get_all_companies()
    cutoff = datetime.now() - timedelta(days=days)
    stale = []
    for c in companies:
        if not c.get("website"):
            continue
        last = c.get("last_analyzed") or c.get("created_at")
        if not last:
            stale.append(c)
            continue
        try:
            last_dt = datetime.fromisoformat(str(last).split("+")[0].replace("Z", ""))
            if last_dt < cutoff:
                stale.append(c)
        except Exception:
            stale.append(c)
    return stale


def get_freshness_stats(companies: list = None) -> dict:
    """Statistiken über Daten-Aktualität."""
    if companies is None:
        companies = db.get_all_companies()
    total = len(companies)
    stale_30 = len(get_stale_companies(companies, days=30))
    stale_7  = len(get_stale_companies(companies, days=7))
    uncertain = len(get_uncertain_companies(companies))
    analyzed  = len([c for c in companies if c.get("kategorie")])
    return {
        "total":         total,
        "analyzed":      analyzed,
        "fresh":         total - stale_30,
        "stale_30":      stale_30,
        "stale_7":       stale_7,
        "uncertain":     uncertain,
        "fresh_percent": round((total - stale_30) / total * 100, 1) if total > 0 else 0,
    }


def refresh_stale_companies(days: int = STALE_DAYS, progress_callback=None) -> list:
    """Analysiert alle veralteten Firmen neu."""
    stale = get_stale_companies(days=days)
    results = []
    for i, company in enumerate(stale):
        if progress_callback:
            progress_callback(i + 1, len(stale),
                              f"Aktualisiere {i+1}/{len(stale)}: {company['name']}")
        results.append(reanalyze_company(company))
        time.sleep(2)
    return results


def get_changes_summary(results: list) -> dict:
    """Zusammenfassung der Änderungen nach Re-Analyse."""
    successful = [r for r in results if r.get("success")]
    category_changed = [r for r in successful
                        if r.get("new_kategorie") != r.get("old_kategorie")]
    improved = [r for r in successful
                if r.get("new_vertrauen", 0) > r.get("old_vertrauen", 0)]
    return {
        "total":            len(results),
        "successful":       len(successful),
        "failed":           len([r for r in results if not r.get("success")]),
        "improved":         len(improved),
        "category_changed": len(category_changed),
        "changes":          category_changed,
    }
