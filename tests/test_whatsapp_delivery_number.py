"""Proves the WhatsApp REPORT is delivered to the number the customer typed in
the contact popup — NOT the (possibly different) number Razorpay reports for the
payment. Runs the real webhook + verify paths with the two numbers deliberately
different, and records the exact phone handed to send_whatsapp_report.

Run just this file to see it:
    .venv/bin/pytest tests/test_whatsapp_delivery_number.py -v
"""
import api
from tests.test_contact_capture import _new_report, _stub_rzp

POPUP = "9876500002"          # what the user typed in the popup
RZP   = "+911112223334"       # a DIFFERENT number Razorpay reports for the card


def _record_sends(monkeypatch):
    sent = []
    monkeypatch.setattr(api, "send_whatsapp_report",
                        lambda phone, rid, name, product="marriage": sent.append(phone))
    monkeypatch.setattr(api, "_pregenerate_pdf_task", lambda rid: None)
    return sent


def test_webhook_delivers_to_popup_number_not_razorpay(client, monkeypatch, pay_webhook):
    sent = _record_sends(monkeypatch)
    rid = _new_report(client)
    _stub_rzp(monkeypatch)
    client.post("/api/order", json={"report_id": rid, "phone": POPUP})
    pay_webhook(client, rid, "pay_wa_1", RZP)          # pay from a different number

    assert sent == ["+919876500002"], f"WhatsApp went to {sent}, expected the popup number"


def test_never_sends_to_razorpay_number_even_without_popup_number(client, monkeypatch, pay_webhook):
    # Popup number is a mandatory field, so this path is only reachable by
    # direct API abuse. Policy: we NEVER deliver to the Razorpay number — so
    # with no popup number, nothing is sent at all.
    sent = _record_sends(monkeypatch)
    rid = _new_report(client)
    _stub_rzp(monkeypatch)
    client.post("/api/order", json={"report_id": rid})   # no popup phone given
    pay_webhook(client, rid, "pay_fb_1", RZP)
    assert sent == [], f"report must NEVER go to the Razorpay number, but sent to {sent}"
