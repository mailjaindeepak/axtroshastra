"""ops.alerts — the notification layer must NEVER raise, must gate cleanly when
unconfigured, and must fan out to email + WhatsApp when configured.

(Flat filename on purpose: a tests/ops/ subdir would shadow the `ops` source
package on pytest's import path.)"""
import ops.config as config
import ops.alerts as alerts


def test_send_alert_noop_when_unconfigured(monkeypatch):
    for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "TWILIO_SID",
              "TWILIO_TOKEN", "TWILIO_WHATSAPP_FROM"):
        monkeypatch.setattr(config, k, "")
    monkeypatch.setattr(config, "ALERT_EMAILS", [])
    monkeypatch.setattr(config, "ALERT_WHATSAPP", [])
    res = alerts.send_alert("Site down", "healthz returned 503", "critical")
    assert res == {"email": False, "whatsapp": False}


def test_email_alert_sends_when_configured(monkeypatch):
    monkeypatch.setattr(config, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(config, "SMTP_USER", "bot@example.com")
    monkeypatch.setattr(config, "SMTP_PASSWORD", "secret")
    monkeypatch.setattr(config, "SMTP_FROM", "bot@example.com")
    monkeypatch.setattr(config, "SMTP_STARTTLS", True)
    monkeypatch.setattr(config, "ALERT_EMAILS", ["dev1@example.com", "dev2@example.com"])

    sent = {}

    class _SMTP:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self, *a, **k): sent["tls"] = True
        def login(self, u, p): sent["login"] = (u, p)
        def send_message(self, msg):
            sent["to"] = msg["To"]; sent["subject"] = msg["Subject"]

    monkeypatch.setattr(alerts.smtplib, "SMTP", _SMTP)
    res = alerts.send_alert("DB write failed", "sentinel missing on re-read", "critical")
    assert res["email"] is True
    assert sent["login"] == ("bot@example.com", "secret")
    assert "dev1@example.com" in sent["to"] and "dev2@example.com" in sent["to"]
    assert "Axtroshastra ops" in sent["subject"]


def test_whatsapp_alert_best_effort(monkeypatch):
    monkeypatch.setattr(config, "TWILIO_SID", "AC_test")
    monkeypatch.setattr(config, "TWILIO_TOKEN", "tok")
    monkeypatch.setattr(config, "TWILIO_WHATSAPP_FROM", "whatsapp:+15550000000")
    monkeypatch.setattr(config, "ALERT_WHATSAPP", ["+919999999999"])
    monkeypatch.setattr(config, "SMTP_HOST", "")  # email off; prove whatsapp independent

    calls = []
    import twilio.rest

    class _Msgs:
        def create(self, **kw): calls.append(kw)

    class _Client:
        def __init__(self, *a, **k): self.messages = _Msgs()

    monkeypatch.setattr(twilio.rest, "Client", _Client)
    res = alerts.send_alert("Robot customer failed", "unlock step 404", "warning")
    assert res == {"email": False, "whatsapp": True}
    assert calls and calls[0]["to"] == "whatsapp:+919999999999"


def test_send_alert_never_raises_on_broken_smtp(monkeypatch):
    monkeypatch.setattr(config, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(config, "SMTP_USER", "bot@example.com")
    monkeypatch.setattr(config, "SMTP_PASSWORD", "secret")
    monkeypatch.setattr(config, "ALERT_EMAILS", ["dev@example.com"])

    def _boom(*a, **k):
        raise OSError("connection refused")

    monkeypatch.setattr(alerts.smtplib, "SMTP", _boom)
    assert alerts.send_alert("x", "y")["email"] is False
