"""
job_radar.py – KI-Stellenanzeigen-Erkennung auf Unternehmenswebsites
Nur öffentliche Karriereseiten der Unternehmen selbst – 100% legal
"""
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; StormarnKI-Radar/1.0; +https://stormarn.de)",
    "Accept-Language": "de-DE,de;q=0.9",
}

# KI-relevante Job-Keywords mit Scoring
KI_JOB_KEYWORDS = {
    "machine learning":       10,
    "deep learning":          10,
    "data scientist":         10,
    "ml engineer":            10,
    "ai engineer":            10,
    "nlp engineer":           10,
    "computer vision":         9,
    "llm":                     9,
    "ki-entwickler":           9,
    "ki entwickler":           9,
    "prompt engineer":         8,
    "data engineer":           7,
    "robotics":                7,
    "automatisierung":         5,
    "künstliche intelligenz":  5,
    "algorithmus entwickler":  6,
    "python entwickler":       4,
    "data analyst":            5,
    "business intelligence":   4,
    "predictive":              6,
}

# Typische Karriereseiten-Pfade
CAREER_PATHS = [
    "/karriere",
    "/karriere/jobs",
    "/karriere/stellenangebote",
    "/jobs",
    "/stellenangebote",
    "/stellen",
    "/career",
    "/careers",
    "/jobs-karriere",
    "/offene-stellen",
    "/arbeiten-bei-uns",
    "/team/jobs",
]


def find_career_page(website: str) -> str:
    """
    Findet die Karriereseite eines Unternehmens.
    Returns: URL der Karriereseite oder ""
    """
    if not website:
        return ""

    base = website.rstrip("/")
    if not base.startswith("http"):
        base = "https://" + base

    for path in CAREER_PATHS:
        try:
            url = base + path
            resp = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
            if resp.status_code == 200 and len(resp.content) > 500:
                return url
            time.sleep(0.3)
        except Exception:
            continue

    # Fallback: Hauptseite nach Karriere-Links durchsuchen
    try:
        resp = requests.get(base, headers=HEADERS, timeout=8)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"].lower()
                text = a.get_text(strip=True).lower()
                if any(kw in href or kw in text
                       for kw in ["karriere", "jobs", "stellen", "career"]):
                    full_url = a["href"]
                    if not full_url.startswith("http"):
                        full_url = base + full_url
                    return full_url
    except Exception:
        pass

    return ""


def scan_career_page(career_url: str, company_name: str) -> list:
    """
    Scannt eine Karriereseite nach KI-relevanten Stellenanzeigen.
    Returns: Liste von Job-Dicts
    """
    jobs = []
    if not career_url:
        return jobs

    try:
        resp = requests.get(career_url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            return jobs

        soup = BeautifulSoup(resp.content, "html.parser")
        text_lower = soup.get_text(" ", strip=True).lower()

        # Gefundene Keywords sammeln
        found_keywords = []
        max_score = 0
        for keyword, score in KI_JOB_KEYWORDS.items():
            if keyword in text_lower:
                found_keywords.append((keyword, score))
                max_score = max(max_score, score)

        if found_keywords:
            # Job-Titel aus Überschriften extrahieren
            job_titles = []
            for tag in soup.find_all(["h2", "h3", "h4", "li", "a"]):
                title = tag.get_text(strip=True)
                if 5 < len(title) < 80:
                    title_lower = title.lower()
                    for keyword, score in KI_JOB_KEYWORDS.items():
                        if keyword in title_lower:
                            job_titles.append({
                                "title": title,
                                "ki_score": score,
                                "ki_signal": keyword
                            })
                            break

            # Deduplizieren
            seen = set()
            for job in job_titles:
                key = job["title"].lower()[:40]
                if key not in seen:
                    seen.add(key)
                    jobs.append({
                        "title": job["title"],
                        "company": company_name,
                        "career_url": career_url,
                        "source": "Unternehmenswebsite",
                        "ki_score": job["ki_score"],
                        "ki_signal": job["ki_signal"]
                    })

            # Falls keine konkreten Titel: allgemeinen Eintrag erstellen
            if not jobs and found_keywords:
                top_kw = sorted(found_keywords, key=lambda x: x[1], reverse=True)[0]
                jobs.append({
                    "title": f"KI-relevante Inhalte gefunden: '{top_kw[0]}'",
                    "company": company_name,
                    "career_url": career_url,
                    "source": "Unternehmenswebsite",
                    "ki_score": top_kw[1],
                    "ki_signal": top_kw[0]
                })

    except Exception as e:
        print(f"Karriereseite Fehler ({company_name}): {e}")

    return jobs


def analyze_company_jobs(company_name: str, website: str = "") -> dict:
    """
    Vollständige Job-Analyse eines Unternehmens.
    Sucht nur auf der Unternehmenswebsite – 100% legal.

    Returns: Dict mit jobs, ki_job_score, has_ki_jobs, signal_strength
    """
    # Karriereseite finden
    career_url = find_career_page(website)

    jobs = []
    if career_url:
        jobs = scan_career_page(career_url, company_name)

    max_score = max((j["ki_score"] for j in jobs), default=0)
    has_ki_jobs = len(jobs) > 0

    return {
        "jobs":           jobs,
        "ki_job_count":   len(jobs),
        "ki_job_score":   max_score,
        "has_ki_jobs":    has_ki_jobs,
        "career_url":     career_url,
        "signal_strength": _signal_strength(max_score, len(jobs))
    }


def _signal_strength(max_score: int, count: int) -> str:
    if max_score >= 9 and count >= 2:
        return "🔴 Sehr stark – Firma investiert intensiv in KI"
    elif max_score >= 7:
        return "🟠 Stark – KI-Entwicklung aktiv"
    elif max_score >= 5:
        return "🟡 Mittel – KI wird eingesetzt"
    elif max_score > 0:
        return "🟢 Schwach – KI-Interesse vorhanden"
    else:
        return "⚪ Kein KI-Signal auf Karriereseite"
