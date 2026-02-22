"""
scraper.py – Generischer Website-Scraper
Liest Firmenwebseiten und extrahiert relevanten Text.
"""
import time
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

import config_loader as cfg

# ──────────────────────────────────────────────────────────
# Social-Media-Erkennung
# ──────────────────────────────────────────────────────────

_LINKEDIN_PATTERN = re.compile(
    r"https?://(?:www\.)?linkedin\.com/company/([^/\s\"'?#><]+)", re.I)


def extract_social_media(html_content: str) -> dict:
    """
    Extrahiert den LinkedIn-Unternehmensseiten-Link aus einem HTML-Dokument.
    Nur /company/-URLs werden erkannt – keine Personenprofile (/in/).

    Returns:
        dict mit key: linkedin (leer wenn nicht gefunden)
    """
    result = {"linkedin": ""}
    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Versuch: in allen <a href>-Tags suchen
    for tag in soup.find_all("a", href=True):
        m = _LINKEDIN_PATTERN.search(tag["href"])
        if m:
            result["linkedin"] = m.group(0).split("?")[0].split("#")[0].rstrip("/")
            return result

    # 2. Fallback: rohen HTML-Text durchsuchen (z.B. JS-Variablen, Meta-Tags)
    m = _LINKEDIN_PATTERN.search(html_content)
    if m:
        result["linkedin"] = m.group(0).split("?")[0].split("#")[0].rstrip("/")

    return result


def _get_headers():
    return {
        "User-Agent": cfg.get("radar.scraper.user_agent", "RadarBot/1.0"),
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    }


def _clean_text(html_content: str) -> str:
    """Bereinigt HTML zu lesbarem Text."""
    soup = BeautifulSoup(html_content, "html.parser")

    # Entferne unwichtige Tags
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "form", "iframe", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    # Whitespace normalisieren
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _get_internal_links(base_url: str, soup: BeautifulSoup, limit: int = 5) -> list:
    """Sammelt interne Links einer Seite."""
    base_domain = urlparse(base_url).netloc
    links = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(base_url, href)
        if urlparse(full_url).netloc == base_domain:
            # Bevorzuge inhaltlich relevante Seiten
            if any(kw in full_url.lower() for kw in
                   ["ki", "ai", "digital", "innovation", "produkt", "leistung",
                    "technologie", "loesung", "ueber", "about"]):
                links.add(full_url)

    return list(links)[:limit]


def scrape_website(url: str) -> dict:
    """
    Scrapt eine Website und gibt strukturierten Text zurück.

    Returns:
        dict mit keys: url, title, text, pages_scraped, error
    """
    timeout = cfg.get("radar.scraper.timeout_seconds", 15)
    max_pages = cfg.get("radar.scraper.max_pages_per_site", 3)
    delay = cfg.get("radar.scraper.delay_between_requests", 2)
    keywords = cfg.get("radar.keywords", [])

    if not url.startswith("http"):
        url = "https://" + url

    result = {
        "url": url,
        "title": "",
        "text": "",
        "pages_scraped": 0,
        "keyword_hits": [],
        "social_media": {"linkedin": ""},
        "error": None
    }

    try:
        session = requests.Session()
        headers = _get_headers()

        # Hauptseite laden
        resp = session.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")

        title_tag = soup.find("title")
        result["title"] = title_tag.get_text(strip=True) if title_tag else ""

        # Social-Media-Links von der Hauptseite extrahieren
        result["social_media"] = extract_social_media(resp.text)

        texts = [_clean_text(resp.text)]
        result["pages_scraped"] = 1

        # Unterseiten laden
        extra_links = _get_internal_links(url, soup, limit=max_pages - 1)
        for link in extra_links:
            try:
                time.sleep(delay)
                sub_resp = session.get(link, headers=headers, timeout=timeout)
                sub_resp.raise_for_status()
                texts.append(_clean_text(sub_resp.text))
                result["pages_scraped"] += 1
            except Exception:
                continue

        full_text = " ".join(texts)

        # Auf 8000 Zeichen kürzen (reicht für LLM-Analyse)
        result["text"] = full_text[:8000]

        # Keyword-Treffer zählen
        text_lower = full_text.lower()
        result["keyword_hits"] = [
            kw for kw in keywords if kw.lower() in text_lower
        ]

    except requests.exceptions.ConnectionError:
        result["error"] = "Website nicht erreichbar"
    except requests.exceptions.Timeout:
        result["error"] = "Timeout"
    except requests.exceptions.HTTPError as e:
        result["error"] = f"HTTP-Fehler: {e.response.status_code}"
    except Exception as e:
        result["error"] = str(e)

    return result


def has_topic_relevance(scrape_result: dict, min_keyword_hits: int = 1) -> bool:
    """Schnell-Check: Hat die Seite überhaupt Relevanz für das Thema?"""
    return len(scrape_result.get("keyword_hits", [])) >= min_keyword_hits
