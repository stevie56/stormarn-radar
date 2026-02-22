"""
geo_mapper.py – Geocodierung von Adressen via Nominatim (OpenStreetMap, kostenlos)
"""
import time
import requests
import config_loader as cfg


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_CACHE = {}  # Einfacher In-Memory-Cache


def geocode_address(address: str, city: str = "", postal_code: str = "") -> tuple:
    """
    Gibt (lat, lng) zurück oder (None, None) wenn nicht gefunden.
    Verwendet Nominatim (kein API-Key nötig!).
    """
    region = cfg.get("radar.region", "")

    # Vollständige Adresse zusammenbauen
    parts = [p for p in [address, postal_code, city, "Deutschland"] if p]
    query = ", ".join(parts)

    if query in _CACHE:
        return _CACHE[query]

    try:
        time.sleep(1)  # Nominatim-Höflichkeits-Pause
        resp = requests.get(
            NOMINATIM_URL,
            params={
                "q": query,
                "format": "json",
                "limit": 1,
                "countrycodes": "de"
            },
            headers={"User-Agent": cfg.get("radar.scraper.user_agent", "RadarBot/1.0")},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()

        if data:
            lat = float(data[0]["lat"])
            lng = float(data[0]["lon"])

            # Prüfe ob in Stormarn-Bounds
            bounds = cfg.get("radar.region_bounds", {})
            if bounds:
                if not (bounds["south"] <= lat <= bounds["north"] and
                        bounds["west"] <= lng <= bounds["east"]):
                    # Koordinaten außerhalb der Region – trotzdem zurückgeben
                    pass

            _CACHE[query] = (lat, lng)
            return lat, lng

    except Exception as e:
        print(f"Geocoding-Fehler für '{query}': {e}")

    _CACHE[query] = (None, None)
    return None, None


def geocode_company(company: dict) -> tuple:
    """Geocodiert ein Company-Dict direkt."""
    return geocode_address(
        address=company.get("address", ""),
        city=company.get("city", ""),
        postal_code=company.get("postal_code", "")
    )
