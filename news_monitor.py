"""
news_monitor.py – News-Monitoring für Stormarn-Unternehmen
Sucht automatisch nach Pressemitteilungen und KI-News
"""
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import feedparser

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; StormarnRadar/1.0)",
    "Accept-Language": "de-DE,de;q=0.9"
}

KI_NEWS_KEYWORDS = [
    "künstliche intelligenz", "ki ", "machine learning", "automatisierung",
    "digitalisierung", "robotik", "chatbot", "algorithmus", "deep learning"
]


def search_company_news(company_name: str, max_results: int = 5) -> list:
    """
    Sucht News zu einem Unternehmen via Google News RSS.
    Returns: Liste von News-Dicts
    """
    news = []
    
    try:
        query = f"{company_name} KI Digitalisierung"
        rss_url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=de&gl=DE&ceid=DE:de"
        
        feed = feedparser.parse(rss_url)
        
        for entry in feed.entries[:max_results]:
            news.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "source": entry.get("source", {}).get("title", "Google News"),
                "company": company_name,
                "ki_relevant": _is_ki_relevant(entry.get("title", "") + " " + entry.get("summary", ""))
            })
        
        time.sleep(1)
        
    except Exception as e:
        print(f"News-Fehler ({company_name}): {e}")
    
    return news


def search_stormarn_ki_news() -> list:
    """
    Sucht allgemeine KI-News aus Stormarn / Schleswig-Holstein.
    """
    news = []
    queries = [
        "Stormarn Künstliche Intelligenz",
        "Stormarn Digitalisierung Unternehmen",
        "Ahrensburg KI Technologie",
        "Reinbek Digitalisierung",
        "Bad Oldesloe KI"
    ]
    
    for query in queries:
        try:
            rss_url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=de&gl=DE&ceid=DE:de"
            feed = feedparser.parse(rss_url)
            
            for entry in feed.entries[:3]:
                news.append({
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "source": entry.get("source", {}).get("title", ""),
                    "query": query,
                    "ki_relevant": True
                })
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Stormarn News Fehler: {e}")
    
    # Deduplizieren
    seen = set()
    unique = []
    for n in news:
        if n["title"] not in seen:
            seen.add(n["title"])
            unique.append(n)
    
    return unique


def search_job_postings_ki(company_name: str) -> list:
    """
    Sucht KI-Stellenanzeigen eines Unternehmens.
    Returns: Liste von Job-Dicts
    """
    jobs = []
    
    try:
        query = f"{company_name} Machine Learning Data Scientist KI"
        rss_url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=de&gl=DE&ceid=DE:de"
        feed = feedparser.parse(rss_url)
        
        for entry in feed.entries[:3]:
            title = entry.get("title", "")
            if any(kw in title.lower() for kw in ["job", "stelle", "karriere", "gesucht", "data", "ml", "ki"]):
                jobs.append({
                    "title": title,
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "company": company_name
                })
        
        time.sleep(1)
        
    except Exception as e:
        print(f"Job-Suche Fehler ({company_name}): {e}")
    
    return jobs


def _is_ki_relevant(text: str) -> bool:
    """Prüft ob ein Text KI-relevant ist."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in KI_NEWS_KEYWORDS)
