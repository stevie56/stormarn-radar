"""
utils/scoring.py — RNVP Score-Berechnung
"""

SCORE_LABELS = {
    (17, 99): ("A",  "grün"),
    (15, 16): ("B+", "grün"),
    (13, 14): ("B",  "grün"),
    (11, 12): ("C+", "gelb"),
    ( 9, 10): ("C",  "gelb"),
    ( 7,  8): ("C−", "gelb"),
    ( 5,  6): ("D+", "rot"),
    ( 3,  4): ("D",  "rot"),
    ( 0,  2): ("D−", "rot"),
}

STATUS_COLOR = {"grün": "#16a34a", "gelb": "#d97706", "rot": "#dc2626"}
STATUS_EMOJI = {"grün": "🟢", "gelb": "🟡", "rot": "🔴"}

def calc_score(s: dict) -> tuple[str, str, int]:
    """Berechnet Score-Label, Status und Punkte aus einem Standort-dict."""
    pts = 0

    # Fahrten/Tag (max 5)
    f = s.get("fahrten_tag") or 0
    pts += 5 if f >= 30 else 4 if f >= 20 else 3 if f >= 12 else 2 if f >= 6 else 1 if f >= 1 else 0

    # HVZ-Takt (max 4)
    t = s.get("takt_hvz") or 999
    pts += 4 if t <= 15 else 3 if t <= 20 else 2 if t <= 30 else 1 if t <= 60 else 0

    # Abendverkehr (max 2)
    if s.get("abend"):     pts += 2
    # Wochenende (max 2)
    if s.get("wochenende"): pts += 2

    # Erste Abfahrt (max 1)
    ea = s.get("erste_abfahrt") or "99:00"
    try:
        h = int(ea.split(":")[0])
        pts += 1 if h <= 6 else 0
    except: pass

    # Letzte Abfahrt (max 1)
    la = s.get("letzte_abfahrt") or "00:00"
    try:
        h = int(la.split(":")[0])
        pts += 1 if h >= 21 else 0
    except: pass

    # Haltestellennähe über ge_stops (vereinfacht: wenn fahrten > 0 = nah)
    pts += 3 if f >= 6 else 2 if f >= 1 else 0

    # Score-Label
    label, status = "D−", "rot"
    for (lo, hi), (lbl, st) in SCORE_LABELS.items():
        if lo <= pts <= hi:
            label, status = lbl, st
            break

    return label, status, pts


def schwachstellen(s: dict) -> list[str]:
    """Gibt die Top-3 Schwachpunkte eines Standorts zurück."""
    issues = []
    f = s.get("fahrten_tag") or 0
    t = s.get("takt_hvz") or 999

    if f == 0:           issues.append("🚫 Kein Bus")
    elif f < 6:          issues.append(f"⚠ Nur {f} Fahrten/Tag")
    if t > 30:           issues.append(f"⏱ Takt {t} Min.")
    if not s.get("abend"):     issues.append("🌙 Kein Abendverkehr")
    if not s.get("wochenende"): issues.append("📅 Kein Wochenende")

    ea = s.get("erste_abfahrt") or "99:00"
    try:
        if int(ea.split(":")[0]) > 6: issues.append(f"🌅 Erste Abfahrt {ea}")
    except: pass

    return issues[:3]
