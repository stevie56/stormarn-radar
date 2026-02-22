"""
pdf_export.py – PDF-Steckbriefe für Unternehmen
Verwendet ReportLab (pip install reportlab)
"""
import json
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, HRFlowable)

import config_loader as cfg

EXPORTS_DIR = Path(__file__).parent / "exports"
EXPORTS_DIR.mkdir(exist_ok=True)

# Kategorie → Farbe
CATEGORY_COLORS = {
    "ECHTER_EINSATZ": colors.HexColor("#1e8449"),
    "INTEGRATION":    colors.HexColor("#d4ac0d"),
    "BUZZWORD":       colors.HexColor("#e67e22"),
    "KEIN_KI":        colors.HexColor("#95a5a6"),
    "UNBEKANNT":      colors.HexColor("#bdc3c7"),
}

CATEGORY_LABELS = {
    "ECHTER_EINSATZ": "✅ Echter KI-Einsatz",
    "INTEGRATION":    "🔗 KI-Integration",
    "BUZZWORD":       "⚠️ KI-Buzzword",
    "KEIN_KI":        "❌ Kein KI-Bezug",
    "UNBEKANNT":      "❓ Unbekannt",
}


def _hex_color(hex_str: str):
    return colors.HexColor(hex_str)


def generate_company_profile(company: dict, analysis: dict) -> str:
    """
    Generiert einen PDF-Steckbrief für ein Unternehmen.

    Returns:
        Pfad zur erstellten PDF-Datei
    """
    primary = cfg.get("radar.pdf.primary_color", "#1a5276")
    accent = cfg.get("radar.pdf.accent_color", "#2e86c1")
    radar_name = cfg.get("radar.name", "Regional Radar")
    footer_text = cfg.get("radar.pdf.footer", "")

    safe_name = "".join(c for c in company["name"] if c.isalnum() or c in " -_")
    filename = EXPORTS_DIR / f"Steckbrief_{safe_name.replace(' ', '_')}.pdf"

    doc = SimpleDocTemplate(
        str(filename),
        pagesize=A4,
        topMargin=2*cm, bottomMargin=2*cm,
        leftMargin=2*cm, rightMargin=2*cm
    )

    styles = getSampleStyleSheet()
    story = []

    # ── Header ──
    header_data = [[
        Paragraph(f"<font color='white' size='16'><b>{radar_name}</b></font>",
                  styles["Normal"]),
        Paragraph(f"<font color='white' size='10'>{datetime.now().strftime('%d.%m.%Y')}</font>",
                  styles["Normal"])
    ]]
    header_table = Table(header_data, colWidths=["70%", "30%"])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _hex_color(primary)),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Unternehmensname ──
    story.append(Paragraph(
        f"<font size='20' color='{primary}'><b>{company['name']}</b></font>",
        styles["Normal"]
    ))
    story.append(Spacer(1, 0.3*cm))

    # ── KI-Kategorie Badge ──
    kategorie = analysis.get("kategorie", "UNBEKANNT")
    badge_color = CATEGORY_COLORS.get(kategorie, colors.grey)
    badge_label = CATEGORY_LABELS.get(kategorie, kategorie)

    badge_data = [[Paragraph(
        f"<font color='white' size='11'><b>{badge_label}</b></font>",
        styles["Normal"]
    )]]
    badge_table = Table(badge_data, colWidths=["50%"])
    badge_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), badge_color),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("ROUNDEDCORNERS", (0, 0), (-1, -1), 5),
    ]))
    story.append(badge_table)
    story.append(Spacer(1, 0.5*cm))

    story.append(HRFlowable(color=_hex_color(accent), thickness=1, width="100%"))
    story.append(Spacer(1, 0.3*cm))

    # ── Stammdaten ──
    story.append(Paragraph(
        f"<font size='13' color='{primary}'><b>Unternehmensdaten</b></font>",
        styles["Normal"]
    ))
    story.append(Spacer(1, 0.2*cm))

    info_rows = [
        ["Website:", company.get("website", "–")],
        ["Adresse:", f"{company.get('address', '')}, {company.get('postal_code', '')} {company.get('city', '')}".strip(", ")],
        ["Branche:", company.get("industry", "–")],
        ["Mitarbeiter:", company.get("employee_count", "–")],
        ["Vertrauens-Score:", f"{analysis.get('vertrauen', 0)}/100"],
    ]

    info_table = Table(info_rows, colWidths=["30%", "70%"])
    info_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5*cm))

    # ── KI-Anwendungen ──
    ki_anwendungen = analysis.get("ki_anwendungen", [])
    if isinstance(ki_anwendungen, str):
        try:
            ki_anwendungen = json.loads(ki_anwendungen)
        except Exception:
            ki_anwendungen = []

    if ki_anwendungen:
        story.append(Paragraph(
            f"<font size='13' color='{primary}'><b>Identifizierte KI-Anwendungen</b></font>",
            styles["Normal"]
        ))
        story.append(Spacer(1, 0.2*cm))
        for app in ki_anwendungen:
            story.append(Paragraph(f"• {app}", styles["Normal"]))
            story.append(Spacer(1, 0.1*cm))
        story.append(Spacer(1, 0.3*cm))

    # ── Analyse-Begründung ──
    begruendung = analysis.get("begruendung", "")
    if begruendung:
        story.append(Paragraph(
            f"<font size='13' color='{primary}'><b>Analyse</b></font>",
            styles["Normal"]
        ))
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph(begruendung, styles["Normal"]))
        story.append(Spacer(1, 0.4*cm))

    # ── Biografie ──
    biografie = analysis.get("biografie", "")
    if biografie:
        story.append(HRFlowable(color=_hex_color(accent), thickness=0.5, width="100%"))
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(
            f"<font size='13' color='{primary}'><b>Unternehmensbiografie</b></font>",
            styles["Normal"]
        ))
        story.append(Spacer(1, 0.2*cm))

        bio_style = ParagraphStyle(
            "Bio",
            parent=styles["Normal"],
            leading=16,
            textColor=colors.HexColor("#444444")
        )
        story.append(Paragraph(biografie, bio_style))

    # ── Footer ──
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(color=colors.grey, thickness=0.5, width="100%"))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"<font size='8' color='grey'>{footer_text} | Erstellt: {datetime.now().strftime('%d.%m.%Y %H:%M')}</font>",
        styles["Normal"]
    ))

    doc.build(story)
    return str(filename)


def generate_overview_pdf(companies: list) -> str:
    """Generiert ein Übersichts-PDF für alle Unternehmen."""
    primary = cfg.get("radar.pdf.primary_color", "#1a5276")
    radar_name = cfg.get("radar.name", "Regional Radar")
    region = cfg.get("radar.region", "")
    footer_text = cfg.get("radar.pdf.footer", "")

    filename = EXPORTS_DIR / f"Uebersicht_{datetime.now().strftime('%Y%m%d')}.pdf"
    doc = SimpleDocTemplate(str(filename), pagesize=A4,
                            topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2*cm, rightMargin=2*cm)

    styles = getSampleStyleSheet()
    story = []

    # Titel
    story.append(Paragraph(
        f"<font size='22' color='{primary}'><b>{radar_name}</b></font>",
        styles["Normal"]
    ))
    story.append(Paragraph(
        f"<font size='14' color='grey'>Übersicht – {region} | {datetime.now().strftime('%d.%m.%Y')}</font>",
        styles["Normal"]
    ))
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(color=_hex_color(primary), thickness=2, width="100%"))
    story.append(Spacer(1, 0.5*cm))

    # Tabelle
    table_data = [["Unternehmen", "Stadt", "Branche", "KI-Kategorie", "Score"]]
    for c in companies:
        table_data.append([
            c.get("name", ""),
            c.get("city", ""),
            c.get("industry", ""),
            CATEGORY_LABELS.get(c.get("kategorie", ""), c.get("kategorie", "")),
            str(c.get("vertrauen", "–")),
        ])

    table = Table(table_data, colWidths=["30%", "15%", "20%", "25%", "10%"])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _hex_color(primary)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f8")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")),
    ]))
    story.append(table)

    # Footer
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(
        f"<font size='8' color='grey'>{footer_text} | {len(companies)} Unternehmen analysiert</font>",
        styles["Normal"]
    ))

    doc.build(story)
    return str(filename)
