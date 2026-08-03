"""POST /api/verify — the client-side payment fallback (used when the Razorpay
webhook is delayed or misconfigured). It verifies the checkout signature
(HMAC-SHA256 of "{order_id}|{payment_id}" with the Razorpay KEY secret), looks
the report up by order_id, marks it paid and mirrors the webhook's delivery.

Had ZERO coverage before this file. RZP_SECRET (env RAZORPAY_KEY_SECRET) is
unset in tests, so we monkeypatch it and stub the Razorpay payment.fetch call.
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


class _StubPayment:
    def fetch(self, pid):
        # NB: the suite shares ONE database, and users de-dupe by mobile with
        # first-writer-wins email. This number must stay UNIQUE to test_verify:
        # reusing +919812345678 (test_users / test_delivery / test_tracking)
        # made test_users' account-email assertion order-dependent.
        return {"contact": "+919855511111", "email": "verified@example.com"}


class _StubRzp:
    payment = _StubPayment()


def _wire(monkeypatch):
    """Configure the KEY secret, stub the Razorpay client, and neutralise the
    post-payment background tasks so the endpoint's core logic is isolated."""
    monkeypatch.setattr(api, "RZP_SECRET", SECRET)
    monkeypatch.setattr(api, "rzp_client", lambda: _StubRzp())
    monkeypatch.setattr(api, "_pregenerate_pdf_task", lambda rid: None)
    monkeypatch.setattr(api, "_generate_narrative_task", lambda rid: None)
    monkeypatch.setattr(api, "send_whatsapp_report", lambda *a, **k: None)


def _new_order(client, oid):
    rid = client.post("/api/kundli", json=KUNDLI).json()["report_id"]
    api.set_order(rid, oid)
    return rid


def test_verify_valid_signature_marks_paid(client, monkeypatch):
    _wire(monkeypatch)
    oid, pid = "order_verify_1", "pay_verify_1"
    rid = _new_order(client, oid)

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
    oid, pid = "order_verify_2", "pay_verify_2"
    _new_order(client, oid)

    r = client.post("/api/verify", json={
        "razorpay_order_id": oid,
        "razorpay_payment_id": pid,
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
