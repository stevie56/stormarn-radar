"""
wirtschaftsdaten_importer.py
Importiert Unternehmen direkt aus der Wirtschaftsdaten-Excel-Datei (Stormarn)
"""
import pandas as pd
import io


def load_wirtschaftsdaten(file_bytes: bytes) -> tuple:
    """
    Liest die Wirtschaftsdaten-Excel und gibt einen sauberen DataFrame zurück.
    Returns: (DataFrame, error_message)
    """
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name="Tabelle1")

        if "Name des Unternehmens" not in df.columns:
            return None, "Datei hat nicht das erwartete Format (Spalte 'Name des Unternehmens' fehlt)"

        # Eindeutige Firmen
        unique = df.drop_duplicates(subset=["Name des Unternehmens"]).copy()

        # Relevante Spalten extrahieren
        result = pd.DataFrame()
        result["name"] = unique["Name des Unternehmens"].fillna("").astype(str).str.strip()

        # Adresse
        strasse = unique["Straße (*)"].fillna("").astype(str)
        hausnr = unique["Hausnummer (*)"].fillna("").astype(str)
        hausnr = hausnr.apply(lambda x: "" if x in ["nan", "NaN"] else x)
        strasse = strasse.apply(lambda x: "" if x in ["nan", "NaN"] else x)
        result["adresse"] = (strasse + " " + hausnr).str.strip()

        result["plz"] = unique["Postleitzahl"].fillna("").astype(str)\
            .str.replace(".0", "", regex=False).str.strip()
        result["plz"] = result["plz"].apply(lambda x: "" if x in ["nan", "NaN"] else x)

        result["ort"] = unique["Ort"].fillna("").astype(str).str.strip()
        result["ort"] = result["ort"].apply(lambda x: "" if x in ["nan", "NaN"] else x)

        # Website normalisieren
        result["website"] = unique["Web Adresse (*)"].fillna("").astype(str).str.strip()
        result["website"] = result["website"].apply(_normalize_url)

        # Branche (WZ Code Beschreibung kürzen)
        branche_col = "WZ 2008 - Haupttätigkeit - Beschreibung (*)"
        if branche_col in unique.columns:
            result["branche"] = unique[branche_col].fillna("").astype(str)
            result["branche"] = result["branche"].apply(
                lambda x: "" if x in ["nan", "NaN"] else x[:80]
            )
        else:
            result["branche"] = ""

        # Mitarbeiter
        ma_col = "Anzahl der Mitarbeiter (Zuletzt angegebener Wert) (*)"
        if ma_col in unique.columns:
            result["mitarbeiter"] = unique[ma_col].fillna("").astype(str)\
                .str.replace(".0", "", regex=False)
            result["mitarbeiter"] = result["mitarbeiter"].apply(
                lambda x: "" if x in ["nan", "NaN", "n.v."] else x
            )
        else:
            result["mitarbeiter"] = ""

        # Umsatz
        umsatz_col = "Umsatz tsd  (zuletzt angegebener Wert)\ntsd EUR (*)"
        if umsatz_col in unique.columns:
            result["umsatz"] = unique[umsatz_col].fillna("").astype(str)
            result["umsatz"] = result["umsatz"].apply(
                lambda x: "" if x in ["nan", "NaN", "n.v."] else x
            )
        else:
            result["umsatz"] = ""

        # Nur gültige Firmen
        result = result[result["name"].str.len() > 2].reset_index(drop=True)

        return result, None

    except Exception as e:
        return None, str(e)


def _normalize_url(url: str) -> str:
    """Normalisiert eine URL."""
    if not url or url in ["nan", "NaN", "n.v.", ""]:
        return ""
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    return url


def get_stats(df: pd.DataFrame) -> dict:
    """Gibt Statistiken über den DataFrame zurück."""
    return {
        "total": len(df),
        "with_website": int((df["website"] != "").sum()),
        "without_website": int((df["website"] == "").sum()),
        "cities": df["ort"].value_counts().head(10).to_dict(),
        "top_branches": df["branche"].value_counts().head(5).to_dict()
    }


def filter_companies(df: pd.DataFrame, only_with_website: bool = True,
                     cities: list = None, min_employees: int = None) -> pd.DataFrame:
    """Filtert Unternehmen nach Kriterien."""
    filtered = df.copy()

    if only_with_website:
        filtered = filtered[filtered["website"] != ""]

    if cities:
        cities_lower = [c.lower() for c in cities]
        filtered = filtered[filtered["ort"].str.lower().isin(cities_lower)]

    if min_employees:
        filtered = filtered[
            pd.to_numeric(filtered["mitarbeiter"], errors="coerce") >= min_employees
        ]

    return filtered.reset_index(drop=True)
