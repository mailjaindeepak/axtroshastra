"""WhatsApp delivery (api.send_whatsapp_report) + admin re-send.

The single highest-value guarantee here is the Twilio *template-variable
mapping*: a regression in which the report id was passed as a path instead of
the bare `{{3}}` variable silently took WhatsApp delivery down. These tests pin
the exact content_sid + content_variables for both the media and the text
templates, and the env-gating that keeps the whole thing dormant in dev/CI.
"""
import json

import twilio.rest

import api

# Fully-populated Twilio config; individual tests override pieces via monkeypatch.
TW_ENV = {
    "TWILIO_SID": "AC_test_sid",
    "TWILIO_TOKEN": "test_token",
    "TWILIO_FROM": "whatsapp:+14155238886",
    "PUBLIC_BASE_URL": "https://axtroshastra.example",
    "TWILIO_CONTENT_SID": "HXmedia0000000000000000000000000",
    "TWILIO_CONTENT_SID_TEXT": "HXtext00000000000000000000000000",
}


def _set_twilio_env(monkeypatch, **overrides):
    for key, val in {**TW_ENV, **overrides}.items():
        monkeypatch.setattr(api, key, val)


def _fake_client(monkeypatch, calls):
    """Install a fake `twilio.rest.Client` whose messages.create records kwargs.
    send_whatsapp_report does `from twilio.rest import Client` inside the fn, so
    patching the attribute on the module is what it will pick up."""
    class _Msgs:
        def create(self, **kwargs):
            calls.append(kwargs)
            return type("Msg", (), {"sid": "SM_fake"})()

    class _Client:
        def __init__(self, *a, **k):
            self.messages = _Msgs()

    monkeypatch.setattr(twilio.rest, "Client", _Client)


# ---------------------------------------------------- B1: template-var mapping
def test_media_template_passes_rid_as_bare_variable_3(client, monkeypatch):
    """Media/CONTENT_SID path: the approved template's {{3}} must be the rid
    ALONE (never a path) — this is the exact thing that regressed."""
    _set_twilio_env(monkeypatch)
    calls = []
    _fake_client(monkeypatch, calls)
    # A cached PDF that is ALSO publicly downloadable selects the media template.
    monkeypatch.setattr(api.pdfgen, "get_cached", lambda rid: b"%PDF-1.4 fake")
    monkeypatch.setattr(api, "_pdf_is_fetchable", lambda rid: True)

    api.send_whatsapp_report("+919812345678", "rid_media_1", "Asha", "marriage")

    assert len(calls) == 1, "exactly one WhatsApp message must be sent"
    kw = calls[0]
    assert kw["content_sid"] == TW_ENV["TWILIO_CONTENT_SID"]
    assert json.loads(kw["content_variables"]) == {
        "1": "Asha",
        "2": f"{TW_ENV['PUBLIC_BASE_URL']}/login",
        "3": "rid_media_1",          # bare rid, NOT a path/URL
    }


def test_media_skipped_when_pdf_not_publicly_fetchable(client, monkeypatch):
    """The 63019 fix: a PDF cached on THIS instance but not downloadable from the
    public url must NOT be attached (that fails async and the customer gets
    nothing). We fall back to the TEXT template with the report link instead."""
    _set_twilio_env(monkeypatch)
    calls = []
    _fake_client(monkeypatch, calls)
    monkeypatch.setattr(api.pdfgen, "get_cached", lambda rid: b"%PDF-1.4 fake")  # cached...
    monkeypatch.setattr(api, "_pdf_is_fetchable", lambda rid: False)             # ...but not fetchable

    api.send_whatsapp_report("+919812345678", "rid_media_2", "Asha", "marriage")

    assert len(calls) == 1, "still exactly one WhatsApp — never zero"
    kw = calls[0]
    assert kw["content_sid"] == TW_ENV["TWILIO_CONTENT_SID_TEXT"], "must use the TEXT template"
    assert json.loads(kw["content_variables"]) == {
        "1": "Asha",
        "2": f"{TW_ENV['PUBLIC_BASE_URL']}/report/rid_media_2",   # link, no media attached
    }


def test_pdf_is_fetchable_returns_false_when_probe_fails(monkeypatch):
    """The probe never raises and returns False on any error, so a broken public
    PDF url can never crash delivery — it just downgrades to the link template."""
    monkeypatch.setattr(api, "PUBLIC_BASE_URL", "https://axtroshastra.example")
    import urllib.request

    def _boom(*a, **k):
        raise OSError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    assert api._pdf_is_fetchable("rid_probe") is False


def test_text_template_used_when_pdf_not_ready(client, monkeypatch):
    """Text-fallback path: no cached PDF + a TEXT sid set -> the TEXT template
    with {{1}}=name and {{2}}=the report link."""
    _set_twilio_env(monkeypatch)
    calls = []
    _fake_client(monkeypatch, calls)
    monkeypatch.setattr(api.pdfgen, "get_cached", lambda rid: None)  # PDF not ready

    api.send_whatsapp_report("+919812345678", "rid_text_1", "Vikram", "marriage")

    assert len(calls) == 1
    kw = calls[0]
    assert kw["content_sid"] == TW_ENV["TWILIO_CONTENT_SID_TEXT"]
    assert json.loads(kw["content_variables"]) == {
        "1": "Vikram",
        "2": f"{TW_ENV['PUBLIC_BASE_URL']}/report/rid_text_1",
    }


# ---------------------------------------------------- B2: env-gating (dormant)
def test_no_send_when_twilio_env_unset(client, monkeypatch):
    """With the Twilio globals blank, the function returns before ever building
    a Client or calling create()."""
    _set_twilio_env(monkeypatch, TWILIO_SID="", TWILIO_TOKEN="", TWILIO_FROM="")

    def _boom(*a, **k):
        raise AssertionError("Twilio Client must NOT be constructed when unconfigured")

    monkeypatch.setattr(twilio.rest, "Client", _boom)
    monkeypatch.setattr(api.pdfgen, "get_cached", lambda rid: b"pdf")

    # Must simply return None without raising.
    assert api.send_whatsapp_report("+919812345678", "rid_x", "Nobody") is None


# ---------------------------------------------------- B3: admin re-send happy path
KUNDLI = {"name": "Resend Buyer", "dob": "1990-05-10", "tob": "09:20",
          "time_quality": "T0", "place": "Delhi", "gender": "male"}


def test_resend_wa_calls_send_for_paid_report_with_phone(client, monkeypatch, pay_webhook):
    rid = client.post("/api/kundli", json=KUNDLI).json()["report_id"]
    # Keep the webhook's own background delivery a no-op & fast.
    monkeypatch.setattr(api, "_pregenerate_pdf_task", lambda rid: None)
    # Popup number (mandatory in production) — this is where the report must go.
    client.post("/api/order", json={"report_id": rid, "phone": "9876500055"})
    # The customer pays from a DIFFERENT number — must be ignored for delivery.
    pay_webhook(client, rid, "pay_resend_1", "+919812345678", "buyer@example.com")

    # Now record what resend_wa hands to the sender.
    calls = []
    monkeypatch.setattr(api, "send_whatsapp_report",
                        lambda *a, **k: calls.append((a, k)))

    r = client.post(f"/api/resend_wa/{rid}?key=test-stats-key")
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    assert len(calls) == 1, "send_whatsapp_report must fire exactly once"
    args, _ = calls[0]
    assert args[0] == "+919876500055"     # the POPUP number, NEVER the payment number
    assert args[1] == rid


def test_resend_wa_paid_report_without_phone(client, monkeypatch):
    """A paid report that has no phone at all -> explicit no_phone_on_report."""
    monkeypatch.setattr(api, "_pregenerate_pdf_task", lambda rid: None)

    def _boom(*a, **k):
        raise AssertionError("must not attempt to send with no phone")

    monkeypatch.setattr(api, "send_whatsapp_report", _boom)

    rid = client.post("/api/kundli", json=KUNDLI).json()["report_id"]
    # demo-pay marks paid but records NO phone.
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200

    r = client.post(f"/api/resend_wa/{rid}?key=test-stats-key")
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": False, "error": "no_phone_on_report"}
