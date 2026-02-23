"""
company_finder.py – Automatischer Firmen-Finder für den Stormarn KI-Radar
Quellen: Gelbe Seiten, Handelsregister, IHK Schleswig-Holstein
"""
import time
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode, quote_plus

import config_loader as cfg

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; StormarnRadar/1.0)",
    "Accept-Language": "de-DE,de;q=0.9",
    "Accept": "text/html,application/xhtml+xml"
}

# Stormarn PLZ-Bereiche
STORMARN_CITIES = [
    "Bad Oldesloe", "Reinbek", "Bargteheide", "Ahrensburg", "Glinde",
    "Großhansdorf", "Trittau", "Barsbüttel", "Stapelfeld", "Oststeinbek",
    "Hammoor", "Wentorf", "Brunsbek", "Steinburg", "Siek", "Ammersbek"
]

STORMARN_PLZ = [
    "23843", "23858", "23863", "23866", "23869", "23879", "23881", "23883",
    "21465", "21493", "22941", "22929", "22949", "22952", "22955", "22956",
    "22958", "22959", "22962", "22963", "22965", "22967", "22969"
]


# ──────────────────────────────────────────────────────────
# QUELLE 1: Gelbe Seiten
# ──────────────────────────────────────────────────────────

def scrape_gelbe_seiten(city: str, category: str = "Unternehmen",
                         max_pages: int = 3) -> list:
    """
    Sucht Firmen auf Gelbe Seiten für eine Stadt.
    Returns: Liste von dicts mit name, address, website, phone
    """
    companies = []
    base_url = "https://www.gelbeseiten.de/suche"

    for page in range(1, max_pages + 1):
        params = {
            "cyellow": category,
            "clocation": f"{city}, Schleswig-Holstein",
            "page": page
        }
        url = f"{base_url}/{quote_plus(category)}/{quote_plus(city)}"
        if page > 1:
            url += f"?page={page}"

        try:
            time.sleep(2)
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                break

            soup = BeautifulSoup(resp.content, "html.parser")
            entries = soup.find_all("article", class_=re.compile(r"mod-Treffer"))

            if not entries:
                break

            for entry in entries:
                company = _parse_gelbe_seiten_entry(entry, city)
                if company:
                    companies.append(company)

        except Exception as e:
            print(f"Gelbe Seiten Fehler ({city}): {e}")
            break

    return companies


def _parse_gelbe_seiten_entry(entry, city: str) -> dict:
    """Parst einen einzelnen Gelbe-Seiten-Eintrag."""
    try:
        # Name
        name_tag = entry.find(["h2", "h3"], class_=re.compile(r"[Nn]ame|[Tt]itle"))
        if not name_tag:
            name_tag = entry.find("a", class_=re.compile(r"[Nn]ame"))
        name = name_tag.get_text(strip=True) if name_tag else ""

        if not name:
            return None

        # Adresse
        addr_tag = entry.find(class_=re.compile(r"[Aa]dresse|[Aa]ddress|[Ss]treet"))
        address = addr_tag.get_text(strip=True) if addr_tag else ""

        # PLZ extrahieren
        postal_code = ""
        plz_match = re.search(r'\b(\d{5})\b', address)
        if plz_match:
            postal_code = plz_match.group(1)

        # Website
        website = ""
        website_tag = entry.find("a", href=re.compile(r"https?://"), 
                                  class_=re.compile(r"[Ww]eb|[Hh]ome|[Ll]ink"))
        if not website_tag:
            for a in entry.find_all("a", href=True):
                href = a["href"]
                if href.startswith("http") and "gelbeseiten" not in href:
                    website = href
                    break
        else:
            website = website_tag.get("href", "")

        # Telefon
        phone_tag = entry.find(class_=re.compile(r"[Tt]el|[Pp]hone"))
        phone = phone_tag.get_text(strip=True) if phone_tag else ""

        return {
            "name": name,
            "address": address,
            "city": city,
            "postal_code": postal_code,
            "website": website,
            "phone": phone,
            "source": "Gelbe Seiten"
        }

    except Exception:
        return None


# ──────────────────────────────────────────────────────────
# QUELLE 2: Handelsregister (unternehmensregister.de)
# ──────────────────────────────────────────────────────────

def scrape_handelsregister(city: str, max_results: int = 50) -> list:
    """
    Sucht Firmen im Unternehmensregister.
    Returns: Liste von dicts
    """
    companies = []

    try:
        time.sleep(2)
        url = "https://www.unternehmensregister.de/ureg/search.html"
        params = {
            "query": city,
            "state": "SH",  # Schleswig-Holstein
            "searchType": "0"
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return companies

        soup = BeautifulSoup(resp.content, "html.parser")
        rows = soup.find_all("tr", class_=re.compile(r"result|entry"))

        for row in rows[:max_results]:
            cols = row.find_all("td")
            if len(cols) >= 2:
                name = cols[0].get_text(strip=True)
                location = cols[1].get_text(strip=True) if len(cols) > 1 else city

                if name and city.lower() in location.lower():
                    companies.append({
                        "name": name,
                        "address": location,
                        "city": city,
                        "postal_code": "",
                        "website": "",
                        "source": "Handelsregister"
                    })

    except Exception as e:
        print(f"Handelsregister Fehler ({city}): {e}")

    return companies


# ──────────────────────────────────────────────────────────
# QUELLE 3: Wer-zu-Wem (deutsches Firmenverzeichnis, kostenlos)
# ──────────────────────────────────────────────────────────

def scrape_wer_zu_wem(city: str, max_pages: int = 2) -> list:
    """
    Sucht Firmen auf wer-zu-wem.de – gutes deutsches Firmenverzeichnis.
    Returns: Liste von dicts
    """
    companies = []

    for page in range(1, max_pages + 1):
        try:
            time.sleep(2)
            url = f"https://www.wer-zu-wem.de/firma/{quote_plus(city.lower())}/"
            if page > 1:
                url += f"?page={page}"

            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                break

            soup = BeautifulSoup(resp.content, "html.parser")
            entries = soup.find_all("div", class_=re.compile(r"company|firma|result"))

            if not entries:
                # Fallback: alle Links die wie Firmennamen aussehen
                entries = soup.find_all("h3")

            for entry in entries:
                name_tag = entry.find("a") or entry
                name = name_tag.get_text(strip=True)

                if not name or len(name) < 3:
                    continue

                website_tag = entry.find("a", href=re.compile(r"https?://"))
                website = website_tag.get("href", "") if website_tag else ""

                addr_tag = entry.find(class_=re.compile(r"addr|adress|street"))
                address = addr_tag.get_text(strip=True) if addr_tag else ""

                companies.append({
                    "name": name,
                    "address": address,
                    "city": city,
                    "postal_code": "",
                    "website": website,
                    "source": "Wer-zu-Wem"
                })

        except Exception as e:
            print(f"Wer-zu-Wem Fehler ({city}): {e}")
            break

    return companies


# ──────────────────────────────────────────────────────────
# HAUPT-FUNKTION: Alle Quellen kombinieren
# ──────────────────────────────────────────────────────────

def find_companies_in_stormarn(cities: list = None, sources: list = None,
                                progress_callback=None) -> list:
    """
    Sucht Firmen in Stormarn aus allen verfügbaren Quellen.

    Args:
        cities: Liste von Städten (Standard: alle Stormarn-Städte)
        sources: ["gelbe_seiten", "handelsregister", "wer_zu_wem"]
        progress_callback: Funktion(message) für Fortschrittsanzeige

    Returns:
        Deduplizierte Liste von Firmen-Dicts
    """
    if cities is None:
        cities = STORMARN_CITIES[:8]  # Erstmal die größten
    if sources is None:
        sources = ["gelbe_seiten", "wer_zu_wem"]

    all_companies = []
    seen_names = set()

    total = len(cities) * len(sources)
    current = 0

    for city in cities:
        for source in sources:
            current += 1
            if progress_callback:
                progress_callback(f"🔍 {source} – {city} ({current}/{total})")

            companies = []

            if source == "gelbe_seiten":
                companies = scrape_gelbe_seiten(city, max_pages=2)
            elif source == "handelsregister":
                companies = scrape_handelsregister(city)
            elif source == "wer_zu_wem":
                companies = scrape_wer_zu_wem(city)

            # Deduplizierung
            for c in companies:
                name_key = c["name"].lower().strip()
                if name_key and name_key not in seen_names:
                    seen_names.add(name_key)
                    all_companies.append(c)

    return all_companies


def deduplicate(companies: list) -> list:
    """Entfernt Duplikate anhand des Firmennamens."""
    seen = set()
    result = []
    for c in companies:
        key = c["name"].lower().strip()
        if key not in seen:
            seen.add(key)
            result.append(c)
    return result
