"""POST /api/verify — the client-side payment fallback (used when the Razorpay
webhook is delayed or misconfigured). It verifies the checkout signature
(HMAC-SHA256 of "{order_id}|{payment_id}" with the Razorpay KEY secret), looks
the report up by order_id (v2: the order id lives on the payment row), marks it
paid and mirrors the webhook's delivery.

v2 MySQL: the order row is created through the real /api/order route (which needs
a popup phone — payments.user_id is NOT NULL), not the retired api.set_order.
RZP_SECRET (env RAZORPAY_KEY_SECRET) is unset in tests, so we monkeypatch it and
stub the Razorpay order.create / payment.fetch calls.
"""
import hashlib
import hmac

import api

SECRET = "rzp_key_secret_test"

KUNDLI = {"name": "Verify Buyer", "dob": "1990-05-10", "tob": "09:20",
          "time_quality": "T0", "place": "Delhi", "gender": "male"}


def _sign(oid, pid):
    return hmac.new(SECRET.encode(), f"{oid}|{pid}".encode(),
                    hashlib.sha256).hexdigest()


class _StubRzp:
    """order.create echoes an id off the receipt (=rid); payment.fetch returns a
    contact for the /api/verify entity read."""
    class order:
        @staticmethod
        def create(d):
            return {"id": "order_" + d["receipt"], "amount": d["amount"], "currency": "INR"}

    class payment:
        @staticmethod
        def fetch(pid):
            return {"contact": "+919855511111", "email": "verified@example.com",
                    "amount": 49900, "method": "upi"}


def _wire(monkeypatch):
    """Configure the KEY secret, stub the Razorpay client, and neutralise the
    post-payment background tasks so the endpoint's core logic is isolated."""
    monkeypatch.setattr(api, "RZP_SECRET", SECRET)
    monkeypatch.setattr(api, "rzp_client", lambda: _StubRzp())
    monkeypatch.setattr(api, "_pregenerate_pdf_task", lambda rid: None)
    monkeypatch.setattr(api, "_generate_narrative_task", lambda rid: None)
    monkeypatch.setattr(api, "send_whatsapp_report", lambda *a, **k: None)


def _new_order(client, phone):
    """Create a report and a real v2 order row; return (rid, order_id). The order
    id comes back from /api/order (record_order persisted it on the payment)."""
    rid = client.post("/api/kundli", json=KUNDLI).json()["report_id"]
    r = client.post("/api/order", json={"report_id": rid, "phone": phone})
    assert r.status_code == 200, r.text
    return rid, r.json()["razorpay_order_id"]


def test_verify_valid_signature_marks_paid(client, monkeypatch):
    _wire(monkeypatch)
    rid, oid = _new_order(client, "9800010001")
    pid = "pay_verify_1"

    r = client.post("/api/verify", json={
        "razorpay_order_id": oid,
        "razorpay_payment_id": pid,
        "razorpay_signature": _sign(oid, pid),
    })
    assert r.status_code == 200, r.text
    assert r.json()["report_id"] == rid
    assert client.get(f"/api/report/{rid}").json()["paid"] is True


def test_verify_bad_signature_400(client, monkeypatch):
    _wire(monkeypatch)
    _, oid = _new_order(client, "9800010002")

    r = client.post("/api/verify", json={
        "razorpay_order_id": oid,
        "razorpay_payment_id": "pay_verify_2",
        "razorpay_signature": "deadbeef_not_a_valid_sig",
    })
    assert r.status_code == 400, r.text


def test_verify_unknown_order_404(client, monkeypatch):
    _wire(monkeypatch)
    # Correctly signed, but no report carries this order_id.
    oid, pid = "order_does_not_exist", "pay_verify_3"
    r = client.post("/api/verify", json={
        "razorpay_order_id": oid,
        "razorpay_payment_id": pid,
        "razorpay_signature": _sign(oid, pid),
    })
    assert r.status_code == 404, r.text


def test_verify_missing_fields_400(client, monkeypatch):
    _wire(monkeypatch)
    assert client.post("/api/verify", json={}).status_code == 400
    # partial body is still incomplete
    assert client.post("/api/verify", json={
        "razorpay_order_id": "o", "razorpay_payment_id": "p"}).status_code == 400
