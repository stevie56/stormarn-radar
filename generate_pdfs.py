"""
Generiert PDF-Steckbriefe für Basler AG und Buhck Gruppe
basierend auf bekannten Unternehmensinformationen.
"""
import database
import pdf_export

database.init_db()

# ── Basler AG ──
basler_company = {
    "name": "Basler AG",
    "website": "https://www.baslerweb.com",
    "address": "An der Strusbek 60-62",
    "city": "Ahrensburg",
    "postal_code": "22926",
    "industry": "Industrielle Bildverarbeitung / Machine Vision",
    "employee_count": "ca. 1.000",
    "linkedin": "https://www.linkedin.com/company/basler-ag",
}

basler_analysis = {
    "kategorie": "ECHTER_EINSATZ",
    "begruendung": (
        "Basler AG ist ein weltweit führender Hersteller von industriellen Kameras und "
        "Bildverarbeitungslösungen. Das Unternehmen entwickelt und vertreibt KI-gestützte "
        "Bildverarbeitungssoftware (Basler AI Solution) sowie KI-fähige Industriekameras mit "
        "integrierter Edge-AI-Verarbeitung. Machine Vision und Computer Vision sind "
        "Kerngeschäftsfelder des Unternehmens."
    ),
    "ki_anwendungen": [
        "Industrielle KI-Bildverarbeitung",
        "Edge AI in Industriekameras",
        "Basler AI Solution Software",
        "Computer Vision für Qualitätskontrolle",
        "Deep Learning-basierte Bildanalyse",
    ],
    "vertrauen": 95,
    "biografie": (
        "Die Basler AG mit Sitz in Ahrensburg im Kreis Stormarn ist eines der führenden "
        "Unternehmen im Bereich industrieller Bildverarbeitung und Machine Vision weltweit. "
        "Gegründet 1988, entwickelt und produziert Basler hochwertige Digitalkameras und "
        "Bildverarbeitungslösungen für Industrie, Medizin und Verkehr. Mit über 1.000 "
        "Mitarbeitenden und Standorten auf drei Kontinenten setzt das Unternehmen konsequent "
        "auf Künstliche Intelligenz: Die Produktlinie Basler AI Solution ermöglicht "
        "Deep-Learning-basierte Qualitätsprüfungen ohne Programmierkenntnisse. Darüber hinaus "
        "bietet Basler KI-fähige Kameras mit integrierter Edge-AI-Verarbeitung an, die direkt "
        "am Gerät Bildanalysen durchführen. Basler zählt damit zu den Vorreitern der "
        "KI-Integration in der industriellen Automatisierung im Kreis Stormarn."
    ),
}

# ── Buhck Gruppe ──
buhck_company = {
    "name": "Buhck Gruppe",
    "website": "https://www.buhck.de",
    "address": "Lohkampstrasse 4",
    "city": "Stapelfeld",
    "postal_code": "22145",
    "industry": "Entsorgung / Umweltdienstleistungen",
    "employee_count": "ca. 1.800",
    "linkedin": "",
}

buhck_analysis = {
    "kategorie": "INTEGRATION",
    "begruendung": (
        "Die Buhck Gruppe setzt im Bereich Logistik und Tourenplanung auf KI-gestützte "
        "Optimierungssoftware. Digitale Wiegesysteme, automatisierte Sortieranlagen und "
        "softwaregestützte Abfallstromanalysen sind dokumentierte Anwendungsfälle. Eine "
        "eigenständige KI-Entwicklung ist nicht belegt, jedoch werden Drittanbieter-KI-Tools "
        "für die Betriebsoptimierung eingesetzt."
    ),
    "ki_anwendungen": [
        "KI-gestützte Tourenoptimierung",
        "Automatisierte Sortieranalysen",
        "Digitale Abfallstromverfolgung",
        "Softwaregestützte Logistikplanung",
    ],
    "vertrauen": 65,
    "biografie": (
        "Die Buhck Gruppe ist eines der größten familiengeführten Entsorgungsunternehmen "
        "Norddeutschlands mit Hauptsitz in Stapelfeld im Kreis Stormarn. Gegründet 1943, "
        "beschäftigt die Unternehmensgruppe heute rund 1.800 Mitarbeitende an über 30 Standorten "
        "und bietet ein umfassendes Leistungsspektrum in den Bereichen Entsorgung, Recycling, "
        "Logistik und Deponiemanagement. Im Bereich Digitalisierung setzt Buhck auf moderne "
        "Softwarelösungen zur Tourenoptimierung und Abfallstromverfolgung, die KI-basierte "
        "Algorithmen nutzen. Automatisierte Sortieranlagen und digitale Wiegesysteme "
        "unterstützen die Effizienz der Entsorgungsprozesse. Die Buhck Gruppe positioniert sich "
        "damit als innovativer Akteur in der Kreislaufwirtschaft, der digitale Technologien "
        "gezielt zur Steigerung von Nachhaltigkeit und Betriebseffizienz einsetzt."
    ),
}

print("Generiere Basler AG PDF...")
pdf1 = pdf_export.generate_company_profile(basler_company, basler_analysis)
print(f"OK: {pdf1}")

print("Generiere Buhck Gruppe PDF...")
pdf2 = pdf_export.generate_company_profile(buhck_company, buhck_analysis)
print(f"OK: {pdf2}")

print("Generiere Uebersichts-PDF...")
overview_data = [
    {**basler_company, "kategorie": basler_analysis["kategorie"], "vertrauen": basler_analysis["vertrauen"]},
    {**buhck_company, "kategorie": buhck_analysis["kategorie"], "vertrauen": buhck_analysis["vertrauen"]},
]
pdf3 = pdf_export.generate_overview_pdf(overview_data)
print(f"OK: {pdf3}")

print("\nAlle PDFs fertig!")
