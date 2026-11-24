"""Vastu Career Report: the Rs 99 payment path, with a SIMULATED Razorpay (no network, no keys).

This proves the SERVER side only: the amount the server asks Razorpay for, that the browser cannot change it, that a signed
`payment.captured` webhook unlocks the report, that a forged or repeated webhook does not, and that an unapproved segment is
never ordered. It does NOT prove Razorpay itself is configured: the live keys, webhook registration and auto-capture still need
one real test-mode payment (see docs/vastu-career-report-spec.md section 8).
"""
import hashlib
import hmac
import json
import os
import re

import pytest

import api
import db_v2

PHONES = iter(f"98765930{n:02d}" for n in range(1, 60))


class _Orders:
    def __init__(self):
        self.calls = []

    def create(self, payload):
        self.calls.append(payload)
        return {"id": f"order_stub_{len(self.calls):04d}", "amount": payload["amount"]}


class _Rzp:
    def __init__(self):
        self.order = _Orders()


@pytest.fixture
def rzp(monkeypatch):
    stub = _Rzp()
    monkeypatch.setattr(api, "rzp_client", lambda: stub)
    return stub


def _create(client, **kw):
    body = {"name": "Pay Tester", "dob": "2003-03-14", "segment": "student", "desk_direction": "W", "desk_flexibility": "a_little",
            "door_direction": "N", "phone": next(PHONES)}
    body.update(kw)
    r = client.post("/api/vastu-career", json=body)
    assert r.status_code == 200, r.text
    return r.json()["report_id"], "+91" + body["phone"]


def _payments(rid):
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT amount_paise, currency, status, razorpay_order_id, razorpay_payment_id, method FROM payments WHERE report_id=%s", (rid,))
            return cur.fetchall()
    finally:
        conn.close()


@pytest.mark.parametrize("segment", ["student", "exam_aspirant"])
def test_the_server_asks_razorpay_for_exactly_99_rupees(client, rzp, segment):
    rid, phone = _create(client, segment=segment, desk_direction="S")
    r = client.post("/api/order", json={"report_id": rid, "phone": phone})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["amount"] == 9900 and d["currency"] == "INR" and d["razorpay_order_id"].startswith("order_stub_")
    (call,) = rzp.order.calls
    assert call["amount"] == 9900 and call["currency"] == "INR" and call["receipt"] == rid and call["notes"] == {"report_id": rid}
    rows = _payments(rid)
    assert len(rows) == 1 and rows[0][0] == 9900 and rows[0][2] == "created"            # the actual amount is stored when the order is made


def test_the_browser_cannot_change_the_price(client, rzp):
    rid, phone = _create(client)
    r = client.post("/api/order", json={"report_id": rid, "phone": phone, "amount": 1, "amount_paise": 1, "price": 1, "currency": "USD"})
    assert r.status_code == 200 and r.json()["amount"] == 9900
    assert rzp.order.calls[0]["amount"] == 9900 and rzp.order.calls[0]["currency"] == "INR"


def test_an_unapproved_segment_never_reaches_razorpay(client, rzp):
    rid, phone = _create(client, segment="owner", desk_direction="NE")
    r = client.post("/api/order", json={"report_id": rid, "phone": phone})
    assert r.status_code == 409 and r.json()["detail"] == "not_available"
    assert rzp.order.calls == [] and not _payments(rid)


def test_a_signed_captured_webhook_unlocks_the_report_and_records_99(client, rzp, pay_webhook):
    rid, phone = _create(client)
    order = client.post("/api/order", json={"report_id": rid, "phone": phone}).json()
    assert client.get(f"/report/{rid}").status_code == 404                              # nothing is served before payment
    pay_webhook(client, rid, "pay_vastu_ok_0001", phone, email="buyer@example.com", order_id=order["razorpay_order_id"], amount=9900)
    page = client.get(f"/report/{rid}")
    assert page.status_code == 200 and len(re.findall(r'<section class="page', page.text)) == 16
    assert "Share on WhatsApp" not in page.text and "Disclaimer" not in page.text and "axPdfDl" in page.text
    rows = _payments(rid)
    assert len(rows) == 1 and rows[0][0] == 9900 and rows[0][2] == "captured" and rows[0][4] == "pay_vastu_ok_0001"


def test_a_repeated_webhook_does_not_create_a_second_payment(client, rzp, pay_webhook):
    rid, phone = _create(client)
    order = client.post("/api/order", json={"report_id": rid, "phone": phone}).json()
    for _ in range(3):
        pay_webhook(client, rid, "pay_vastu_dup_0001", phone, order_id=order["razorpay_order_id"], amount=9900)
    assert len(_payments(rid)) == 1 and client.get(f"/report/{rid}").status_code == 200


def test_a_forged_webhook_is_refused_and_unlocks_nothing(client, rzp):
    rid, phone = _create(client)
    client.post("/api/order", json={"report_id": rid, "phone": phone})
    body = json.dumps({"event": "payment.captured", "payload": {"payment": {"entity": {"id": "pay_fake", "notes": {"report_id": rid}}}}}).encode()
    bad = hmac.new(b"not-the-secret", body, hashlib.sha256).hexdigest()
    assert client.post("/api/webhook", content=body, headers={"X-Razorpay-Signature": bad}).status_code == 400
    assert client.post("/api/webhook", content=body).status_code == 400                # no signature at all
    assert client.get(f"/report/{rid}").status_code == 404


def test_other_webhook_events_do_not_unlock(client, rzp):
    rid, phone = _create(client)
    client.post("/api/order", json={"report_id": rid, "phone": phone})
    body = json.dumps({"event": "payment.failed", "payload": {"payment": {"entity": {"id": "pay_failed_1", "notes": {"report_id": rid}}}}}).encode()
    sig = hmac.new(os.environ["RAZORPAY_WEBHOOK_SECRET"].encode(), body, hashlib.sha256).hexdigest()
    assert client.post("/api/webhook", content=body, headers={"X-Razorpay-Signature": sig}).status_code == 200
    assert client.get(f"/report/{rid}").status_code == 404


def test_an_already_paid_report_is_not_charged_again(client, rzp, pay_webhook):
    rid, phone = _create(client)
    order = client.post("/api/order", json={"report_id": rid, "phone": phone}).json()
    pay_webhook(client, rid, "pay_vastu_paid_0001", phone, order_id=order["razorpay_order_id"], amount=9900)
    again = client.post("/api/order", json={"report_id": rid, "phone": phone})
    assert again.json() == {"already_paid": True} and len(rzp.order.calls) == 1


def test_an_order_for_a_report_that_does_not_exist_is_refused(client, rzp):
    r = client.post("/api/order", json={"report_id": "doesnotexist1234", "phone": "+919876593099"})
    assert r.status_code == 404 and rzp.order.calls == []
