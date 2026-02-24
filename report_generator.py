"""
report_generator.py – Automatische Berichte für IHK und Kreisverwaltung
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import io
from datetime import datetime


STORMARN_BLUE = colors.Color(0.102, 0.322, 0.463)
STORMARN_LIGHT = colors.Color(0.53, 0.808, 0.922)
WHITE = colors.white
GRAY = colors.Color(0.95, 0.95, 0.95)
DARK_GRAY = colors.Color(0.3, 0.3, 0.3)


def generate_ihk_report(companies: list, stats: dict, title: str = None) -> bytes:
    """
    Erstellt einen professionellen IHK-Bericht als PDF.
    
    Args:
        companies: Liste analysierter Unternehmen
        stats: Statistik-Dict
        title: Berichtstitel
    
    Returns:
        PDF als bytes
    """
    buf = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2.5*cm,
        rightMargin=2.5*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        "Title", parent=styles["Normal"],
        fontSize=22, textColor=STORMARN_BLUE,
        spaceAfter=6, fontName="Helvetica-Bold",
        alignment=TA_CENTER
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontSize=12, textColor=DARK_GRAY,
        spaceAfter=20, alignment=TA_CENTER
    )
    h1_style = ParagraphStyle(
        "H1", parent=styles["Normal"],
        fontSize=14, textColor=STORMARN_BLUE,
        spaceBefore=16, spaceAfter=8,
        fontName="Helvetica-Bold"
    )
    h2_style = ParagraphStyle(
        "H2", parent=styles["Normal"],
        fontSize=11, textColor=DARK_GRAY,
        spaceBefore=10, spaceAfter=6,
        fontName="Helvetica-Bold"
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=9, textColor=colors.black,
        spaceAfter=6, leading=14
    )
    
    story = []
    
    # ── DECKBLATT ──
    story.append(Spacer(1, 3*cm))
    
    report_title = title or "KI-Radar Kreis Stormarn"
    story.append(Paragraph(report_title, title_style))
    story.append(Paragraph(
        f"Analysebericht · Stand: {datetime.now().strftime('%d. %B %Y')}",
        subtitle_style
    ))
    
    story.append(HRFlowable(width="100%", thickness=2, color=STORMARN_BLUE))
    story.append(Spacer(1, 1*cm))
    
    # Kennzahlen-Box
    total = stats.get("total", len(companies))
    analyzed = stats.get("analyzed", len([c for c in companies if c.get("kategorie")]))
    echter = stats.get("echter_einsatz", len([c for c in companies if c.get("kategorie") == "ECHTER_EINSATZ"]))
    integration = stats.get("integration", len([c for c in companies if c.get("kategorie") == "INTEGRATION"]))
    ki_quote = round((echter + integration) / total * 100, 1) if total > 0 else 0
    
    summary_data = [
        ["Kennzahl", "Wert", "Anteil"],
        ["Unternehmen gesamt", str(total), "100%"],
        ["Davon analysiert", str(analyzed), f"{round(analyzed/total*100,1) if total > 0 else 0}%"],
        ["KI – Echter Einsatz ✅", str(echter), f"{round(echter/total*100,1) if total > 0 else 0}%"],
        ["KI – Integration 🔗", str(integration), f"{round(integration/total*100,1) if total > 0 else 0}%"],
        ["KI-Quote gesamt", "", f"{ki_quote}%"],
        ["Kein KI erkennbar ❌", str(stats.get("kein_ki", 0)), ""],
    ]
    
    summary_table = Table(summary_data, colWidths=[8*cm, 4*cm, 4*cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), STORMARN_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [GRAY, WHITE]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("FONTNAME", (0, 4), (-1, 4), "Helvetica-Bold"),
        ("TEXTCOLOR", (2, 4), (2, 4), colors.Color(0.1, 0.6, 0.1)),
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 1*cm))
    
    # ── SEITE 2: DETAILS ──
    story.append(PageBreak())
    story.append(Paragraph("1. KI-Vorreiter in Stormarn", h1_style))
    story.append(Paragraph(
        "Die folgenden Unternehmen setzen Künstliche Intelligenz bereits produktiv ein:",
        body_style
    ))
    
    # Top KI-Firmen
    top_firms = [c for c in companies if c.get("kategorie") == "ECHTER_EINSATZ"][:20]
    
    if top_firms:
        firm_data = [["Unternehmen", "Ort", "Branche", "KI-Score"]]
        for c in top_firms:
            firm_data.append([
                str(c.get("name", ""))[:35],
                str(c.get("city", ""))[:15],
                str(c.get("industry", ""))[:25],
                str(c.get("ki_score", ""))
            ])
        
        firm_table = Table(firm_data, colWidths=[6*cm, 3*cm, 5*cm, 2*cm])
        firm_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), STORMARN_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [GRAY, WHITE]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(firm_table)
    else:
        story.append(Paragraph("Noch keine Firmen analysiert.", body_style))
    
    story.append(Spacer(1, 0.5*cm))
    
    # ── BRANCHEN-ANALYSE ──
    story.append(Paragraph("2. Branchen-Analyse", h1_style))
    
    branchen = {}
    for c in companies:
        if c.get("kategorie") in ("ECHTER_EINSATZ", "INTEGRATION"):
            branche = c.get("industry", "Unbekannt") or "Unbekannt"
            branche = branche[:40]
            branchen[branche] = branchen.get(branche, 0) + 1
    
    if branchen:
        top_branchen = sorted(branchen.items(), key=lambda x: x[1], reverse=True)[:10]
        branch_data = [["Branche", "KI-Firmen"]]
        for b, count in top_branchen:
            branch_data.append([b, str(count)])
        
        branch_table = Table(branch_data, colWidths=[13*cm, 3*cm])
        branch_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), STORMARN_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [GRAY, WHITE]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(branch_table)
    
    # ── EMPFEHLUNGEN ──
    story.append(PageBreak())
    story.append(Paragraph("3. Handlungsempfehlungen", h1_style))
    
    empfehlungen = [
        ("Förderung der KI-Vorreiter", 
         f"Die {echter} identifizierten KI-Vorreiter sollten als Best-Practice-Beispiele "
         "für andere Stormarn-Unternehmen präsentiert werden."),
        ("Digitalisierungsberatung",
         f"Für die {stats.get('kein_ki', 0)} Unternehmen ohne KI-Einsatz empfehlen wir "
         "gezielte Beratungsangebote durch IHK und Wirtschaftsförderung."),
        ("Branchenspezifische Initiativen",
         "Branchen mit niedrigem KI-Anteil sollten durch spezifische "
         "Förderprogramme angesprochen werden."),
        ("Regelmäßiges Monitoring",
         "Der KI-Radar sollte quartalsweise aktualisiert werden um Trends "
         "frühzeitig zu erkennen.")
    ]
    
    for titel, text in empfehlungen:
        story.append(Paragraph(f"• {titel}", h2_style))
        story.append(Paragraph(text, body_style))
    
    # ── FOOTER ──
    story.append(Spacer(1, 2*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=STORMARN_BLUE))
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontSize=7, textColor=DARK_GRAY,
        alignment=TA_CENTER
    )
    story.append(Paragraph(
        f"Stormarn KI-Radar · Erstellt am {datetime.now().strftime('%d.%m.%Y um %H:%M Uhr')} · "
        "Automatisierter Bericht · Daten basieren auf öffentlich zugänglichen Websites",
        footer_style
    ))
    
    doc.build(story)
    return buf.getvalue()
