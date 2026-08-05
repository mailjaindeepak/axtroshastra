"""Webhook-vs-verify idempotency — the hardening for the payment-recovery net.

A single successful checkout can trigger BOTH delivery paths at once: Razorpay's
server calls our `/api/webhook` while the buyer's browser also posts to
`/api/verify` (the fallback). Before the hardening each path used its own
read-then-write guard, so if they landed together the report could be delivered
TWICE (two WhatsApp template sends to the customer).

Both paths now go through the SAME atomic gate the poll path uses
(`payments.claim_paid` = `UPDATE ... WHERE id=? AND paid=0`): only the caller
that flips paid 0->1 delivers. These tests fire both endpoints for one payment,
in both orders, and assert EXACTLY ONE delivery — to the popup number.

Shared sqlite DB across the suite, so each test uses a UNIQUE popup number
(users de-dupe by mobile).
"""
import hashlib
import hmac
import json

import api

WH_SECRET = "wh_secret_double_fire"
KEY_SECRET = "key_secret_double_fire"

KUNDLI = {"name": "Double Fire", "dob": "1992-03-03", "tob": "07:07",
          "time_quality": "T0", "place": "Delhi", "gender": "female"}


class _StubPay:
    def fetch(self, pid):
        return {"contact": "+911110000009", "email": ""}


class _StubRzp:
    payment = _StubPay()


def _wire(monkeypatch):
    """Both secrets present, Razorpay payment.fetch stubbed, delivery recorded."""
    monkeypatch.setattr(api, "RZP_WEBHOOK_SECRET", WH_SECRET)
    monkeypatch.setattr(api, "RZP_SECRET", KEY_SECRET)
    monkeypatch.setattr(api, "rzp_client", lambda: _StubRzp())
    calls = {"wa": [], "pdf": [], "narr": [], "email": []}
    monkeypatch.setattr(api, "send_whatsapp_report",
                        lambda *a, **k: calls["wa"].append(a))
    monkeypatch.setattr(api, "_pregenerate_pdf_task",
                        lambda rid: calls["pdf"].append(rid))
    monkeypatch.setattr(api, "_generate_narrative_task",
                        lambda rid: calls["narr"].append(rid))
    monkeypatch.setattr(api, "email_report",
                        lambda *a, **k: calls["email"].append(a))
    return calls


def _orphan(client, oid, popup):
    rid = client.post("/api/kundli", json=KUNDLI).json()["report_id"]
    api.set_order(rid, oid)
    api.store_user_contact(rid, popup)
    return rid


def _webhook_body(rid, pid, contact):
    return json.dumps({
        "event": "payment.captured",
        "payload": {"payment": {"entity": {
            "id": pid, "contact": contact, "email": "",
            "notes": {"report_id": rid}}}}}).encode()


def _fire_webhook(client, rid, pid, contact):
    body = _webhook_body(rid, pid, contact)
    sig = hmac.new(WH_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return client.post("/api/webhook", content=body,
                       headers={"X-Razorpay-Signature": sig})


def _fire_verify(client, oid, pid):
    sig = hmac.new(KEY_SECRET.encode(), f"{oid}|{pid}".encode(),
                   hashlib.sha256).hexdigest()
    return client.post("/api/verify", json={
        "razorpay_order_id": oid, "razorpay_payment_id": pid,
        "razorpay_signature": sig})


def test_webhook_then_verify_delivers_once(client, monkeypatch):
    """Webhook wins the claim; the browser's verify fallback then no-ops."""
    calls = _wire(monkeypatch)
    oid, pid = "order_df_1", "pay_df_1"
    rid = _orphan(client, oid, "9876550001")

    assert _fire_webhook(client, rid, pid, "+911112220001").status_code == 200
    assert _fire_verify(client, oid, pid).status_code == 200   # loses the claim

    assert client.get(f"/api/report/{rid}").json()["paid"] is True
    assert len(calls["wa"]) == 1                # exactly ONE WhatsApp, not two
    assert calls["pdf"] == [rid]               # generated once
    assert calls["wa"][0][0] == "+919876550001"  # popup number, not Razorpay's


def test_verify_then_webhook_delivers_once(client, monkeypatch):
    """Reverse order: verify wins, the webhook then no-ops (claim already lost)."""
    calls = _wire(monkeypatch)
    oid, pid = "order_df_2", "pay_df_2"
    rid = _orphan(client, oid, "9876550002")

    assert _fire_verify(client, oid, pid).status_code == 200        # wins
    assert _fire_webhook(client, rid, pid, "+911112220002").status_code == 200

    assert client.get(f"/api/report/{rid}").json()["paid"] is True
    assert len(calls["wa"]) == 1                # exactly ONE WhatsApp, not two
    assert calls["pdf"] == [rid]
    assert calls["wa"][0][0] == "+919876550002"  # popup number


def test_verify_twice_delivers_once(client, monkeypatch):
    """Two verify posts (double-click / retry) also collapse to one delivery."""
    calls = _wire(monkeypatch)
    oid, pid = "order_df_3", "pay_df_3"
    rid = _orphan(client, oid, "9876550003")

    assert _fire_verify(client, oid, pid).status_code == 200        # wins
    assert _fire_verify(client, oid, pid).status_code == 200        # loses claim

    assert len(calls["wa"]) == 1
    assert calls["wa"][0][0] == "+919876550003"
