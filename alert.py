"""
alert.py – E-Mail-Alert-System für neue Aktivitäten
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

import config_loader as cfg
import database as db


def _build_html_email(events: list) -> str:
    radar_name = cfg.get("radar.name", "Regional Radar")
    region = cfg.get("radar.region", "")
    primary_color = cfg.get("radar.pdf.primary_color", "#1a5276")

    rows = ""
    for e in events:
        rows += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #eee;">{e.get('created_at','')}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;"><strong>{e.get('company_name','')}</strong></td>
            <td style="padding:8px;border-bottom:1px solid #eee;">{e.get('event_type','')}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;">{e.get('message','')}</td>
        </tr>
        """

    return f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;">
        <div style="background:{primary_color};padding:20px;color:white;">
            <h2 style="margin:0;">🎯 {radar_name} – Aktivitäts-Alert</h2>
            <p style="margin:5px 0 0 0;">{region} | {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
        </div>
        <div style="padding:20px;">
            <p>Es gibt <strong>{len(events)} neue Ereignisse</strong>:</p>
            <table style="width:100%;border-collapse:collapse;font-size:14px;">
                <thead>
                    <tr style="background:#f5f5f5;">
                        <th style="padding:8px;text-align:left;">Zeit</th>
                        <th style="padding:8px;text-align:left;">Unternehmen</th>
                        <th style="padding:8px;text-align:left;">Typ</th>
                        <th style="padding:8px;text-align:left;">Details</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
        <div style="background:#f5f5f5;padding:15px;font-size:12px;color:#666;">
            {cfg.get("radar.pdf.footer", "")}
        </div>
    </body></html>
    """


def send_alert(events: list, password: str) -> bool:
    """
    Sendet einen E-Mail-Alert mit neuen Ereignissen.

    Args:
        events: Liste von Ereignis-Dicts aus der Datenbank
        password: SMTP-Passwort (App-Passwort bei Gmail)

    Returns:
        True wenn erfolgreich
    """
    from_email = cfg.get("radar.alerts.from_email", "")
    to_email = cfg.get("radar.alerts.to_email", "")
    smtp_host = cfg.get("radar.alerts.smtp_host", "smtp.gmail.com")
    smtp_port = cfg.get("radar.alerts.smtp_port", 587)
    radar_name = cfg.get("radar.name", "Regional Radar")

    if not from_email or not to_email:
        print("E-Mail nicht konfiguriert (from_email / to_email in config.yaml)")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[{radar_name}] {len(events)} neue Aktivitäten"
    msg["From"] = from_email
    msg["To"] = to_email

    html_body = _build_html_email(events)
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(from_email, password)
            server.sendmail(from_email, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"E-Mail-Fehler: {e}")
        return False


def check_and_alert(password: str = "") -> dict:
    """
    Prüft auf neue Ereignisse und sendet ggf. einen Alert.

    Returns:
        dict mit status und Anzahl der gesendeten Events
    """
    if not cfg.get("radar.alerts.enabled", False):
        return {"status": "disabled", "count": 0}

    events = db.get_unalerted_events()
    if not events:
        return {"status": "no_new_events", "count": 0}

    # Nur wenn relevante Keywords enthalten
    trigger_keywords = cfg.get("radar.alerts.trigger_keywords", [])
    relevant = [
        e for e in events
        if any(kw.lower() in (e.get("message", "") + e.get("event_type", "")).lower()
               for kw in trigger_keywords)
    ] if trigger_keywords else events

    if not relevant:
        return {"status": "no_relevant_events", "count": 0}

    success = send_alert(relevant, password)
    if success:
        db.mark_events_alerted([e["id"] for e in relevant])
        return {"status": "sent", "count": len(relevant)}

    return {"status": "error", "count": 0}
