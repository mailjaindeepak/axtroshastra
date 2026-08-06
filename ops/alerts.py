"""Alerting for the ops framework.

Two channels:
  * EMAIL (SMTP) — the RELIABLE channel. A monitoring system must not depend on
    the thing it monitors, and it must not depend on WhatsApp (the very channel
    that has broken before). So email is primary.
  * WHATSAPP (Twilio) — BEST-EFFORT. Free-form WhatsApp only delivers inside a
    24h session window (or via an approved template), and our WhatsApp sender
    has had outages, so treat WhatsApp alerts as a bonus, never the guarantee.

Runs OUTSIDE the app (GitHub Actions), sends directly, and NEVER raises — it
returns a per-channel result dict so the caller can log what got through.
"""
import logging
import smtplib
import ssl
from email.message import EmailMessage

from ops import config

log = logging.getLogger("ops.alerts")

_ICON = {"info": "ℹ️", "warning": "⚠️", "critical": "\U0001f6a8"}


def _email(subject, body):
    if not (config.SMTP_HOST and config.SMTP_USER and config.SMTP_PASSWORD and config.ALERT_EMAILS):
        return False
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = config.SMTP_FROM
        msg["To"] = ", ".join(config.ALERT_EMAILS)
        msg.set_content(body)
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as s:
            if config.SMTP_STARTTLS:
                s.starttls(context=ssl.create_default_context())
            s.login(config.SMTP_USER, config.SMTP_PASSWORD)
            s.send_message(msg)
        return True
    except Exception as e:
        log.error("email alert failed: %s", e)
        return False


def _whatsapp(text):
    if not (config.TWILIO_SID and config.TWILIO_TOKEN and config.TWILIO_WHATSAPP_FROM and config.ALERT_WHATSAPP):
        return False
    sent = False
    try:
        from twilio.rest import Client
        client = Client(config.TWILIO_SID, config.TWILIO_TOKEN)
        for to in config.ALERT_WHATSAPP:
            num = to if to.startswith("+") else "+" + to
            try:
                client.messages.create(from_=config.TWILIO_WHATSAPP_FROM,
                                        to=f"whatsapp:{num}", body=text)
                sent = True
            except Exception as e:
                log.error("whatsapp alert to %s failed: %s", num, e)
    except Exception as e:
        log.error("whatsapp alert init failed: %s", e)
    return sent


def send_alert(subject: str, body: str, severity: str = "warning") -> dict:
    """Fan an alert out to every configured channel. severity in
    {info, warning, critical}. Returns {'email': bool, 'whatsapp': bool}."""
    subj = f"{_ICON.get(severity, _ICON['warning'])} [Axtroshastra ops] {subject}"
    result = {"email": _email(subj, body), "whatsapp": _whatsapp(f"{subj}\n\n{body}")}
    log.info("alert '%s' -> %s", subject, result)
    return result
