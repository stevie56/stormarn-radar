"""
bulk_analyzer.py – Massenanalyse von Unternehmen aus Excel-Listen
"""
import time
import pandas as pd
import io

import database as db
import scraper
import analyzer
import geo_mapper
import config_loader as cfg


REQUIRED_COLUMNS = ["Firmenname*", "Website*"]
OPTIONAL_COLUMNS = ["Straße", "PLZ", "Stadt", "Branche", "Mitarbeiter", "Notizen"]


def read_excel(file_bytes: bytes) -> tuple:
    """
    Liest eine Excel-Datei und gibt DataFrame + Fehler zurück.
    Returns: (DataFrame or None, error_message or None)
    """
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name="Unternehmen")
        
        # Pflichtfelder prüfen
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                return None, f"Spalte '{col}' fehlt in der Excel-Datei."
        
        # Leere Zeilen entfernen
        df = df.dropna(subset=REQUIRED_COLUMNS)
        df = df.reset_index(drop=True)
        
        return df, None
    except Exception as e:
        return None, str(e)


def analyze_batch(df: pd.DataFrame, progress_callback=None, 
                  do_geo: bool = True, do_bio: bool = True) -> list:
    """
    Analysiert alle Unternehmen aus einem DataFrame.
    
    Args:
        df: DataFrame mit Unternehmensdaten
        progress_callback: Funktion(current, total, message) für Fortschrittsanzeige
        do_geo: Geocodierung durchführen
        do_bio: Biografie generieren
    
    Returns:
        Liste von Ergebnis-Dicts
    """
    results = []
    total = len(df)

    for idx, row in df.iterrows():
        current = idx + 1
        name = str(row.get("Firmenname*", "")).strip()
        website = str(row.get("Website*", "")).strip()
        
        if not name or not website:
            continue

        address = str(row.get("Straße", "") or "")
        postal_code = str(row.get("PLZ", "") or "")
        city = str(row.get("Stadt", "") or "")
        industry = str(row.get("Branche", "") or "")
        employee_count = str(row.get("Mitarbeiter", "") or "")

        result = {
            "name": name,
            "website": website,
            "status": "pending",
            "kategorie": None,
            "vertrauen": None,
            "error": None
        }

        try:
            if progress_callback:
                progress_callback(current, total, f"🌐 {name} – Website wird gelesen...")

            # Scraping
            scrape_result = scraper.scrape_website(website)
            website_text = scrape_result.get("text", "") or f"Firma: {name}"

            if progress_callback:
                progress_callback(current, total, f"📍 {name} – Geocodierung...")

            # Geocodierung
            lat, lng = None, None
            if do_geo and (address or city):
                lat, lng = geo_mapper.geocode_address(address, city, postal_code)

            # Company speichern
            company_id = db.upsert_company(
                name=name, website=website, address=address,
                city=city, postal_code=postal_code,
                lat=lat, lng=lng, industry=industry,
                employee_count=employee_count
            )

            if progress_callback:
                progress_callback(current, total, f"🤖 {name} – KI-Analyse...")

            # LLM-Analyse
            classification = analyzer.classify_company(name, website_text)

            biografie = ""
            if do_bio:
                if progress_callback:
                    progress_callback(current, total, f"✍️ {name} – Biografie...")
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

            db.log_event(company_id, "BULK_IMPORT",
                        f"Batch-Analyse: {classification['kategorie']} (Score: {classification['vertrauen']})")

            result["status"] = "success"
            result["kategorie"] = classification["kategorie"]
            result["vertrauen"] = classification["vertrauen"]

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        results.append(result)
        
        # Kurze Pause zwischen Anfragen
        time.sleep(1)

    return results
