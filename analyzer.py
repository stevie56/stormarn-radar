"""
analyzer.py – LLM-gestützte Analyse via OpenAI
Klassifiziert KI-Reife, schreibt Biografien und erstellt Trend-Reports.
"""
import json
import os
from openai import OpenAI

import config_loader as cfg


def _get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY nicht gesetzt. "
            "Bitte als Umgebungsvariable exportieren: export OPENAI_API_KEY='sk-...'"
        )
    return OpenAI(api_key=api_key)


def _chat(system_prompt: str, user_content: str, json_mode: bool = False) -> str:
    """Einfacher Wrapper um OpenAI Chat Completions."""
    client = _get_client()
    model = cfg.get("radar.llm.model", "gpt-4o-mini")

    kwargs = dict(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        temperature=0.3,
        max_tokens=1000,
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content.strip()


# ──────────────────────────────────────────────────────────
# Klassifikation
# ──────────────────────────────────────────────────────────

def classify_company(company_name: str, website_text: str) -> dict:
    """
    Klassifiziert ein Unternehmen nach KI-Einsatz.

    Returns:
        dict mit: kategorie, begruendung, ki_anwendungen, vertrauen
    """
    system_prompt = cfg.get("radar.llm.classification_prompt", "")
    region = cfg.get("radar.region", "")
    topic = cfg.get("radar.topic", "")

    user_content = f"""
Unternehmensname: {company_name}
Region: {region}
Analysiertes Thema: {topic}

Website-Inhalt (Auszug):
{website_text[:4000]}

Bitte klassifiziere und antworte als JSON.
"""

    raw = _chat(system_prompt, user_content, json_mode=True)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {
            "kategorie": "UNBEKANNT",
            "begruendung": "Analyse fehlgeschlagen",
            "ki_anwendungen": [],
            "vertrauen": 0
        }

    # Felder normalisieren
    result.setdefault("kategorie", "UNBEKANNT")
    result.setdefault("begruendung", "")
    result.setdefault("ki_anwendungen", [])
    result.setdefault("vertrauen", 50)

    # ki_anwendungen sicherstellen als Liste
    if isinstance(result["ki_anwendungen"], str):
        result["ki_anwendungen"] = [result["ki_anwendungen"]]

    return result


# ──────────────────────────────────────────────────────────
# Biografie
# ──────────────────────────────────────────────────────────

def generate_biography(company_name: str, website_text: str,
                       classification: dict) -> str:
    """Schreibt eine professionelle Kurzbiografie des Unternehmens."""
    system_prompt = cfg.get("radar.llm.biography_prompt", "")
    region = cfg.get("radar.region", "")

    user_content = f"""
Unternehmen: {company_name}
Region: {region}
KI-Kategorie: {classification.get('kategorie')}
KI-Anwendungen: {', '.join(classification.get('ki_anwendungen', []))}

Website-Auszug:
{website_text[:3000]}

Schreibe jetzt die Biografie (max. 150 Wörter, auf Deutsch).
"""

    return _chat(system_prompt, user_content)


# ──────────────────────────────────────────────────────────
# Trend-Report
# ──────────────────────────────────────────────────────────

def generate_trend_report(companies_data: list) -> str:
    """
    Erstellt einen Trend-Report für alle analysierten Unternehmen.

    companies_data: Liste von dicts mit name, kategorie, ki_anwendungen, industry
    """
    system_prompt = cfg.get("radar.llm.trend_prompt", "")
    region = cfg.get("radar.region", "")
    topic = cfg.get("radar.topic", "")

    summary_lines = []
    for c in companies_data:
        anwendungen = c.get("ki_anwendungen", [])
        if isinstance(anwendungen, str):
            try:
                anwendungen = json.loads(anwendungen)
            except Exception:
                anwendungen = []
        line = (f"- {c['name']} ({c.get('industry', 'unbekannte Branche')}): "
                f"Kategorie={c.get('kategorie', '?')}, "
                f"Anwendungen={', '.join(anwendungen) if anwendungen else 'keine'}")
        summary_lines.append(line)

    user_content = f"""
Region: {region}
Thema: {topic}
Anzahl Unternehmen: {len(companies_data)}

Unternehmensdaten:
{chr(10).join(summary_lines)}

Erstelle einen strukturierten Trend-Report auf Deutsch.
"""

    return _chat(system_prompt, user_content)
