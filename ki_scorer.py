"""
ki_scorer.py – KI-Reifegrad Scoring System (1-10)
Bewertet Unternehmen nach ihrem KI-Einsatz
"""

# Scoring-Gewichte
KATEGORIE_SCORE = {
    "ECHTER_EINSATZ": 8,
    "INTEGRATION": 5,
    "BUZZWORD": 2,
    "KEIN_KI": 0
}

VERTRAUEN_BONUS = {
    range(90, 101): 2,
    range(70, 90): 1,
    range(50, 70): 0,
    range(0, 50): -1
}

KI_KEYWORDS_ADVANCED = [
    ("machine learning", 3), ("deep learning", 3), ("neural network", 3),
    ("computer vision", 3), ("nlp", 2), ("llm", 3), ("gpt", 2),
    ("automatisierung", 1), ("robotik", 2), ("prädiktiv", 2),
    ("ki-gestützt", 2), ("künstliche intelligenz", 1), ("algorithmus", 1),
    ("datenanalyse", 1), ("predictive", 2), ("chatbot", 1)
]


def calculate_ki_score(kategorie: str, vertrauen: int, 
                        ki_anwendungen: list = None,
                        raw_text: str = "") -> dict:
    """
    Berechnet den KI-Reifegrad (1-10) eines Unternehmens.
    
    Returns:
        dict mit score, level, badge, erklaerung
    """
    score = KATEGORIE_SCORE.get(kategorie, 0)
    
    # Vertrauen-Bonus
    v_bonus = 0
    for score_range, bonus in VERTRAUEN_BONUS.items():
        if vertrauen in score_range:
            v_bonus = bonus
            break
    score += v_bonus
    
    # Keyword-Bonus aus Raw Text
    keyword_bonus = 0
    if raw_text:
        text_lower = raw_text.lower()
        for keyword, points in KI_KEYWORDS_ADVANCED:
            if keyword in text_lower:
                keyword_bonus = min(keyword_bonus + points, 3)
    score += keyword_bonus
    
    # KI-Anwendungen Bonus
    if ki_anwendungen:
        app_count = len([a for a in ki_anwendungen if a and a.strip()])
        score += min(app_count, 2)
    
    # Auf 1-10 normalisieren
    score = max(1, min(10, score + 1))
    
    # Level bestimmen
    if score >= 8:
        level = "KI-Vorreiter"
        badge = "🏆"
        color = "#27AE60"
    elif score >= 6:
        level = "KI-Aktiv"
        badge = "⭐"
        color = "#2ECC71"
    elif score >= 4:
        level = "KI-Einsteiger"
        badge = "🔵"
        color = "#3498DB"
    elif score >= 2:
        level = "KI-Beobachter"
        badge = "🟡"
        color = "#F1C40F"
    else:
        level = "Kein KI"
        badge = "⚪"
        color = "#BDC3C7"
    
    erklaerung = _build_erklaerung(kategorie, vertrauen, keyword_bonus, ki_anwendungen)
    
    return {
        "score": score,
        "level": level,
        "badge": badge,
        "color": color,
        "erklaerung": erklaerung
    }


def _build_erklaerung(kategorie, vertrauen, keyword_bonus, ki_anwendungen):
    parts = []
    if kategorie == "ECHTER_EINSATZ":
        parts.append("Echter KI-Einsatz nachgewiesen")
    elif kategorie == "INTEGRATION":
        parts.append("KI in Integration")
    elif kategorie == "BUZZWORD":
        parts.append("KI nur als Marketing")
    else:
        parts.append("Kein KI erkennbar")
    
    if vertrauen >= 80:
        parts.append(f"Hohe Analyse-Sicherheit ({vertrauen}%)")
    
    if keyword_bonus > 0:
        parts.append("Fortgeschrittene KI-Begriffe gefunden")
    
    if ki_anwendungen:
        count = len([a for a in ki_anwendungen if a])
        if count > 0:
            parts.append(f"{count} KI-Anwendungen identifiziert")
    
    return " · ".join(parts)
