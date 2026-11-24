"""Vastu Career Report: the Rs 99 payment path, with a SIMULATED Razorpay (no network, no keys).

Reference: the owner's "How Razorpay works in Career Intelligence" document. The shared /api/verify and /api/webhook routes do not check
the payment status, amount or currency, and /api/verify marks a report paid even when it cannot fetch the payment. Numerology closes
those gaps on its own routes; this product, which uses the shared routes, closes them for itself: a payment unlocks a Vastu report only
if it is captured, exactly 9900 paise in INR, and belongs to an order WE created for that report.

This proves the SERVER side only. It does NOT prove Razorpay itself is configured: the live keys, webhook registration and auto-capture
still need one real test-mode payment.
"""
import hashlib
import hmac
import itertools
import json
import os
import re

import pytest

import api
import db_v2

PHONES = iter(f"98765930{n:02d}" for n in range(1, 99))
SECRET = "test-key-secret"


_ORDER_SEQ = itertools.count(1)               # Razorpay order ids are unique; so are the stub's, across the whole test session


class _Orders:
    def __init__(self):
        self.calls = []

    def create(self, payload):
        self.calls.append(payload)
        return {"id": f"order_stub_{next(_ORDER_SEQ):06d}", "amount": payload["amount"]}


class _Payments:
    def __init__(self):
        self.entity = None            # what payment.fetch returns; an Exception instance is raised

    def fetch(self, pid):
        if isinstance(self.entity, Exception):
            raise self.entity
        return dict(self.entity)


class _Rzp:
    def __init__(self):
        self.order = _Orders()
        self.payment = _Payments()


@pytest.fixture
def rzp(monkeypatch):
    stub = _Rzp()
    monkeypatch.setattr(api, "rzp_client", lambda: stub)
    monkeypatch.setattr(api, "RZP_SECRET", SECRET)
    return stub


def _create(client, **kw):
    body = {"name": "Pay Tester", "dob": "2003-03-14", "segment": "student", "desk_direction": "W", "desk_flexibility": "a_little",
            "door_direction": "N", "phone": next(PHONES)}
    body.update(kw)
    r = client.post("/api/vastu-career", json=body)
    assert r.status_code == 200, r.text
    return r.json()["report_id"], "+91" + body["phone"]


def _order(client, rid, phone):
    r = client.post("/api/order", json={"report_id": rid, "phone": phone})
    assert r.status_code == 200, r.text
    return r.json()["razorpay_order_id"]


def _payments(rid):
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT amount_paise, currency, status, razorpay_order_id, razorpay_payment_id, method FROM payments WHERE report_id=%s", (rid,))
            return cur.fetchall()
    finally:
        conn.close()


def _hook(client, rid, payment_id, order_id, *, amount=9900, currency="INR", status="captured", secret=None, event="payment.captured",
          signed=True):
    ent = {"id": payment_id, "order_id": order_id, "amount": amount, "currency": currency, "status": status, "method": "upi",
           "contact": "+919000000000", "email": "buyer@example.com", "notes": {"report_id": rid}}
    body = json.dumps({"event": event, "payload": {"payment": {"entity": ent}}}).encode()
    headers = {}
    if signed:
        key = (secret or os.environ["RAZORPAY_WEBHOOK_SECRET"]).encode()
        headers["X-Razorpay-Signature"] = hmac.new(key, body, hashlib.sha256).hexdigest()
    return client.post("/api/webhook", content=body, headers=headers)


def _verify(client, order_id, payment_id, *, secret=SECRET):
    sig = hmac.new(secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
    return client.post("/api/verify", json={"razorpay_order_id": order_id, "razorpay_payment_id": payment_id, "razorpay_signature": sig})


def _paid(client, rid):
    return client.get(f"/report/{rid}").status_code == 200


# ---------------------------------------------------------------- the order
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


def test_an_order_for_a_report_that_does_not_exist_is_refused(client, rzp):
    r = client.post("/api/order", json={"report_id": "doesnotexist1234", "phone": "+919876593099"})
    assert r.status_code == 404 and rzp.order.calls == []


# ---------------------------------------------------------------- webhook (the main path)
def test_a_correct_signed_captured_webhook_unlocks_the_report_and_records_99(client, rzp):
    rid, phone = _create(client)
    oid = _order(client, rid, phone)
    assert not _paid(client, rid)                                                        # nothing is served before payment
    assert _hook(client, rid, "pay_vastu_ok_0001", oid).status_code == 200
    page = client.get(f"/report/{rid}")
    assert page.status_code == 200 and len(re.findall(r'<section class="page', page.text)) == 16
    assert "Share on WhatsApp" not in page.text and "Disclaimer" not in page.text and "axPdfDl" in page.text
    rows = _payments(rid)
    assert len(rows) == 1 and rows[0][0] == 9900 and rows[0][2] == "captured" and rows[0][4] == "pay_vastu_ok_0001"


@pytest.mark.parametrize("what,kw", [
    ("wrong amount", dict(amount=100)), ("amount of zero", dict(amount=0)), ("higher amount", dict(amount=49900)),
    ("wrong currency", dict(currency="USD")), ("not captured", dict(status="authorized")), ("refunded", dict(status="refunded")),
    ("failed", dict(status="failed")), ("no status", dict(status=None)),
])
def test_a_webhook_that_does_not_match_unlocks_nothing(client, rzp, what, kw):
    rid, phone = _create(client)
    oid = _order(client, rid, phone)
    assert _hook(client, rid, "pay_vastu_bad_0001", oid, **kw).status_code == 200       # 200 so Razorpay does not retry forever
    assert not _paid(client, rid), what
    assert [r[2] for r in _payments(rid)] == ["created"]


def test_a_payment_on_someone_elses_order_cannot_unlock_this_report(client, rzp):
    rid, phone = _create(client)
    _order(client, rid, phone)
    other_rid, other_phone = _create(client)
    other_oid = _order(client, other_rid, other_phone)
    assert _hook(client, rid, "pay_vastu_cross_0001", other_oid).status_code == 200      # right amount, but an order that is not this report's
    assert not _paid(client, rid)
    assert _hook(client, rid, "pay_vastu_cross_0002", "order_not_in_our_database").status_code == 200
    assert not _paid(client, rid)


def test_a_webhook_with_no_order_id_unlocks_nothing(client, rzp):
    rid, phone = _create(client)
    _order(client, rid, phone)
    assert _hook(client, rid, "pay_vastu_noorder_1", None).status_code == 200 and not _paid(client, rid)


def test_a_repeated_webhook_does_not_create_a_second_payment(client, rzp):
    rid, phone = _create(client)
    oid = _order(client, rid, phone)
    for _ in range(3):
        assert _hook(client, rid, "pay_vastu_dup_0001", oid).status_code == 200
    assert len(_payments(rid)) == 1 and _paid(client, rid)


def test_a_forged_webhook_is_refused_and_unlocks_nothing(client, rzp):
    rid, phone = _create(client)
    oid = _order(client, rid, phone)
    assert _hook(client, rid, "pay_forged_0001", oid, secret="not-the-secret").status_code == 400
    assert _hook(client, rid, "pay_forged_0002", oid, signed=False).status_code == 400
    assert not _paid(client, rid)


def test_other_webhook_events_do_not_unlock(client, rzp):
    rid, phone = _create(client)
    oid = _order(client, rid, phone)
    assert _hook(client, rid, "pay_failed_0001", oid, event="payment.failed").status_code == 200
    assert not _paid(client, rid)


def test_an_already_paid_report_is_not_charged_again(client, rzp):
    rid, phone = _create(client)
    oid = _order(client, rid, phone)
    _hook(client, rid, "pay_vastu_paid_0001", oid)
    again = client.post("/api/order", json={"report_id": rid, "phone": phone})
    assert again.json() == {"already_paid": True} and len(rzp.order.calls) == 1


# ---------------------------------------------------------------- /api/verify (the browser fallback)
def _ok_entity(**kw):
    e = {"status": "captured", "amount": 9900, "currency": "INR", "contact": "+919000000001", "email": "buyer@example.com", "method": "card"}
    e.update(kw)
    return e


def test_verify_unlocks_a_correct_captured_payment(client, rzp):
    rid, phone = _create(client)
    oid = _order(client, rid, phone)
    rzp.payment.entity = _ok_entity()
    r = _verify(client, oid, "pay_verify_ok_0001")
    assert r.status_code == 200 and r.json() == {"ok": True, "report_id": rid}
    assert _paid(client, rid) and _payments(rid)[0][0] == 9900


def test_verify_never_guesses_when_razorpay_cannot_be_reached(client, rzp):
    # the shared route used to mark the report paid with an amount of 0 here; for this product it must not
    rid, phone = _create(client)
    oid = _order(client, rid, phone)
    rzp.payment.entity = RuntimeError("razorpay unreachable")
    assert _verify(client, oid, "pay_verify_net_0001").status_code == 502
    assert not _paid(client, rid) and [r[2] for r in _payments(rid)] == ["created"]


@pytest.mark.parametrize("what,kw,code", [
    ("authorized only", dict(status="authorized"), 200), ("refunded", dict(status="refunded"), 409), ("failed", dict(status="failed"), 409),
    ("wrong amount", dict(amount=100), 409), ("wrong currency", dict(currency="USD"), 409),
])
def test_verify_refuses_a_payment_that_does_not_match(client, rzp, what, kw, code):
    rid, phone = _create(client)
    oid = _order(client, rid, phone)
    rzp.payment.entity = _ok_entity(**kw)
    r = _verify(client, oid, "pay_verify_bad_0001")
    assert r.status_code == code, (what, r.status_code)
    if code == 200:
        assert r.json() == {"ok": False, "status": "pending"}                              # not captured yet: the webhook or a retry settles it
    assert not _paid(client, rid)


def test_verify_refuses_a_bad_signature_and_an_unknown_order(client, rzp):
    rid, phone = _create(client)
    oid = _order(client, rid, phone)
    rzp.payment.entity = _ok_entity()
    assert _verify(client, oid, "pay_verify_sig_0001", secret="wrong-secret").status_code == 400
    assert _verify(client, "order_nobody_knows", "pay_verify_sig_0002").status_code == 404
    assert not _paid(client, rid)


def test_the_webhook_then_verify_race_delivers_once(client, rzp):
    rid, phone = _create(client)
    oid = _order(client, rid, phone)
    rzp.payment.entity = _ok_entity()
    _hook(client, rid, "pay_vastu_race_0001", oid)
    assert _verify(client, oid, "pay_vastu_race_0001").status_code == 200
    assert len(_payments(rid)) == 1 and _paid(client, rid)


def test_other_products_keep_the_shared_behaviour(client, rzp):
    """The stricter rules are Vastu only: the IQ test still settles through the shared verify path even when the payment fetch fails."""
    from tests.test_iq_test_api import _base_body
    rid = client.post("/api/iq-test", json=_base_body(phone="9876593500")).json()["report_id"]
    oid = client.post("/api/order", json={"report_id": rid, "phone": "9876593500"}).json()["razorpay_order_id"]
    rzp.payment.entity = RuntimeError("razorpay unreachable")
    assert _verify(client, oid, "pay_iq_shared_0001").status_code == 200
    assert client.get(f"/report/{rid}").status_code == 200
