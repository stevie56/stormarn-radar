"""
scraper.py – Verbesserter Website-Scraper mit Unterseiten-Fokus
Scannt Haupt- UND KI-relevante Unterseiten für bessere Analyse-Qualität
"""
import time
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

import config_loader as cfg

# Unterseiten die KI-Infos enthalten – nach Priorität
KI_SUBPAGE_KEYWORDS = [
    # Höchste Priorität
    "ki", "ai", "artificial-intelligence", "kuenstliche-intelligenz",
    "machine-learning", "deep-learning", "innovation", "digital",
    # Mittlere Priorität
    "technologie", "technology", "forschung", "research",
    "automatisierung", "robotik", "smart", "zukunft", "future",
    "produkte", "loesungen", "solutions", "services",
    # Niedrige Priorität
    "ueber-uns", "about", "unternehmen", "company", "news", "blog",
    "karriere", "jobs",
]


def _get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (compatible; StormarnKI-Radar/1.0)",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    }


def _clean_text(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "form", "iframe", "noscript", "cookie"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _get_ki_relevant_links(base_url: str, soup: BeautifulSoup, limit: int = 6) -> list:
    """
    Findet KI-relevante Unterseiten – priorisiert nach KI-Relevanz.
    """
    base_domain = urlparse(base_url).netloc
    priority = {}   # url -> score

    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(base_url, href)
        link_text = (a.get_text(strip=True) + " " + href).lower()

        # Nur interne Links
        if urlparse(full_url).netloc != base_domain:
            continue
        if full_url == base_url:
            continue
        if any(full_url.endswith(ext) for ext in [".pdf", ".jpg", ".png", ".zip", ".mp4"]):
            continue
        if "#" in full_url.split("?")[0].split(base_url)[1:]:
            continue

        # Score basierend auf Keyword-Position in Liste
        for i, kw in enumerate(KI_SUBPAGE_KEYWORDS):
            if kw in link_text:
                score = len(KI_SUBPAGE_KEYWORDS) - i  # Frühere Keywords = höherer Score
                if full_url not in priority or priority[full_url] < score:
                    priority[full_url] = score

    # Sortiert nach Score
    sorted_links = sorted(priority.items(), key=lambda x: x[1], reverse=True)
    return [url for url, _ in sorted_links[:limit]]


def scrape_website(url: str, deep: bool = False) -> dict:
    """
    Scrapt eine Website inkl. KI-relevanter Unterseiten.

    Args:
        url: Website-URL
        deep: True = mehr Unterseiten für zweiten Analyse-Durchlauf

    Returns:
        dict mit url, title, text, pages_scraped, subpages, error
    """
    timeout = cfg.get("radar.scraper.timeout_seconds", 15)
    max_pages = cfg.get("radar.scraper.max_pages_per_site", 5)
    if deep:
        max_pages = 10  # Zweiter Durchlauf: mehr Seiten
    delay = cfg.get("radar.scraper.delay_between_requests", 1)
    keywords = cfg.get("radar.keywords", [])

    if not url.startswith("http"):
        url = "https://" + url

    result = {
        "url": url,
        "title": "",
        "text": "",
        "pages_scraped": 0,
        "subpages": [],
        "keyword_hits": [],
        "error": None
    }

    try:
        session = requests.Session()
        headers = _get_headers()

        # ── Hauptseite ──
        resp = session.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")

        title_tag = soup.find("title")
        result["title"] = title_tag.get_text(strip=True) if title_tag else ""

        main_text = _clean_text(resp.text)
        texts = [f"[Hauptseite]\n{main_text}"]
        result["pages_scraped"] = 1

        # ── KI-relevante Unterseiten ──
        extra_links = _get_ki_relevant_links(url, soup, limit=max_pages - 1)

        for link in extra_links:
            try:
                time.sleep(delay)
                sub_resp = session.get(link, headers=headers, timeout=timeout)
                sub_resp.raise_for_status()

                sub_text = _clean_text(sub_resp.text)
                if len(sub_text) > 100:  # Nur sinnvolle Seiten
                    page_name = link.replace(url, "").strip("/") or "Unterseite"
                    texts.append(f"[{page_name}]\n{sub_text[:2000]}")
                    result["subpages"].append(link)
                    result["pages_scraped"] += 1

            except Exception:
                continue

        full_text = "\n\n".join(texts)
        # Deep-Scan bekommt mehr Text
        char_limit = 20000 if deep else 12000
        result["text"] = full_text[:char_limit]

        # Keyword-Treffer
        text_lower = full_text.lower()
        result["keyword_hits"] = [kw for kw in keywords if kw.lower() in text_lower]

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
    return len(scrape_result.get("keyword_hits", [])) >= min_keyword_hits
