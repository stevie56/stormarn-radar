"""
regional_compare.py – Vergleich Stormarn mit anderen SH-Kreisen
"""

# Benchmark-Daten (öffentlich verfügbare Statistiken, Stand 2023)
KREISE_BENCHMARKS = {
    "Kreis Stormarn": {
        "einwohner": 244000,
        "unternehmen": 15000,
        "digitalquote": 42,  # % Firmen mit Digitalisierungsstrategie
        "ki_quote_est": 8,   # % Firmen mit KI (Schätzung)
        "breitband": 89,     # % Breitbandversorgung
        "startup_index": 65, # Index 0-100
        "farbe": "#1A5276"
    },
    "Kreis Pinneberg": {
        "einwohner": 319000,
        "unternehmen": 19000,
        "digitalquote": 38,
        "ki_quote_est": 7,
        "breitband": 85,
        "startup_index": 58,
        "farbe": "#21618C"
    },
    "Kreis Segeberg": {
        "einwohner": 280000,
        "unternehmen": 16000,
        "digitalquote": 35,
        "ki_quote_est": 6,
        "breitband": 82,
        "startup_index": 52,
        "farbe": "#2874A6"
    },
    "Stadt Lübeck": {
        "einwohner": 217000,
        "unternehmen": 14000,
        "digitalquote": 44,
        "ki_quote_est": 10,
        "breitband": 91,
        "startup_index": 72,
        "farbe": "#2E86C1"
    },
    "Kreis Herzogtum Lauenburg": {
        "einwohner": 200000,
        "unternehmen": 11000,
        "digitalquote": 30,
        "ki_quote_est": 5,
        "breitband": 78,
        "startup_index": 44,
        "farbe": "#3498DB"
    },
    "Hamburg (Metropole)": {
        "einwohner": 1900000,
        "unternehmen": 130000,
        "digitalquote": 61,
        "ki_quote_est": 18,
        "breitband": 96,
        "startup_index": 92,
        "farbe": "#85C1E9"
    }
}


def get_stormarn_ki_quote(analyzed_companies: list) -> float:
    """
    Berechnet die echte KI-Quote aus den analysierten Firmen.
    """
    if not analyzed_companies:
        return 0.0
    
    ki_firms = [c for c in analyzed_companies 
                if c.get("kategorie") in ("ECHTER_EINSATZ", "INTEGRATION")]
    
    total = len(analyzed_companies)
    return round(len(ki_firms) / total * 100, 1) if total > 0 else 0.0


def get_comparison_data(actual_ki_quote: float = None) -> dict:
    """
    Gibt Vergleichsdaten zurück, optional mit echter KI-Quote.
    """
    data = KREISE_BENCHMARKS.copy()
    
    if actual_ki_quote is not None:
        data["Kreis Stormarn"]["ki_quote_est"] = actual_ki_quote
        data["Kreis Stormarn"]["ki_quote_real"] = True
    
    return data


def get_ranking(metric: str, data: dict = None) -> list:
    """
    Erstellt ein Ranking aller Kreise nach einer Metrik.
    Returns: Sortierte Liste von (kreis, wert) Tupeln
    """
    if data is None:
        data = KREISE_BENCHMARKS
    
    ranking = [(kreis, info.get(metric, 0)) for kreis, info in data.items()]
    return sorted(ranking, key=lambda x: x[1], reverse=True)


def get_stormarn_position(metric: str, data: dict = None) -> dict:
    """
    Gibt Position von Stormarn im Ranking zurück.
    """
    ranking = get_ranking(metric, data)
    for i, (kreis, wert) in enumerate(ranking, 1):
        if kreis == "Kreis Stormarn":
            return {
                "position": i,
                "total": len(ranking),
                "wert": wert,
                "besser_als": len(ranking) - i,
                "ranking": ranking
            }
    return {"position": 0, "total": len(ranking), "wert": 0}
