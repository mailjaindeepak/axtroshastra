"""Unit tests for the server-side purchase-tracking module (Meta CAPI + GA4 MP).

The feature is dormant until its secrets are set, so the load-bearing guarantee
is: with no keys configured, track_purchase does absolutely nothing and never
raises (it runs inside a payment background task and must never break checkout).
"""
import hashlib
import hmac
import json

import api
import tracking

WEBHOOK_SECRET = b"test-webhook-secret"   # matches conftest's RAZORPAY_WEBHOOK_SECRET
KUNDLI = {"name": "Track Buyer", "dob": "1991-06-10", "tob": "09:20",
          "time_quality": "T0", "place": "Delhi", "gender": "female"}


def test_webhook_fires_server_side_purchase(client, monkeypatch):
    """A captured payment must hand the Purchase to tracking.track_purchase with
    the report id (dedup key), value, currency and the buyer contact."""
    calls = []
    monkeypatch.setattr(tracking, "track_purchase",
                        lambda *a, **k: calls.append((a, k)))
    rid = client.post("/api/kundli", json=KUNDLI).json()["report_id"]
    ent = {"id": "pay_trk_1", "contact": "+919812345678",
           "email": "buyer@example.com", "notes": {"report_id": rid}}
    body = json.dumps({"event": "payment.captured",
                       "payload": {"payment": {"entity": ent}}}).encode()
    sig = hmac.new(WEBHOOK_SECRET, body, hashlib.sha256).hexdigest()
    r = client.post("/api/webhook", content=body,
                    headers={"X-Razorpay-Signature": sig})
    assert r.status_code == 200, r.text
    assert len(calls) == 1, "track_purchase should fire exactly once per capture"
    args, _ = calls[0]
    assert args[0] == rid                 # event_id / transaction_id dedup key
    assert args[1] == 499.0               # value in rupees
    assert args[2] == "INR"


def test_dormant_without_keys(monkeypatch):
    # No secrets -> feature is off and track_purchase is a safe no-op.
    monkeypatch.setattr(tracking, "META_CAPI_TOKEN", "")
    monkeypatch.setattr(tracking, "GA4_API_SECRET", "")
    assert tracking.enabled() is False
    # Must not raise and must not attempt any network call.
    assert tracking.track_purchase("rid123", 499, "INR", "9876543210", "a@b.com") is None


def test_enabled_flips_with_either_key(monkeypatch):
    monkeypatch.setattr(tracking, "GA4_API_SECRET", "")
    monkeypatch.setattr(tracking, "META_CAPI_TOKEN", "tok")
    assert tracking.enabled() is True
    monkeypatch.setattr(tracking, "META_CAPI_TOKEN", "")
    monkeypatch.setattr(tracking, "GA4_API_SECRET", "sec")
    assert tracking.enabled() is True


def test_phone_normalisation():
    assert tracking._norm_phone("9876543210") == "919876543210"      # assume India
    assert tracking._norm_phone("+91 98765 43210") == "919876543210"  # strip +/spaces
    assert tracking._norm_phone("") is None


def test_sha256_lowercases_and_trims():
    assert tracking._sha256("  A@B.com ") == hashlib.sha256("a@b.com".encode()).hexdigest()
    assert tracking._sha256("") is None


def test_ga_client_id_prefers_browser_then_stable_fallback():
    assert tracking._ga4_client_id("rid", "111.222") == "111.222"
    # Fallback is deterministic across calls (dedup relies on transaction_id,
    # but a stable cid keeps a single synthetic "user" rather than many).
    assert tracking._ga4_client_id("rid", None) == tracking._ga4_client_id("rid", None)
    assert tracking._ga4_client_id("rid", None).startswith("555.")


def test_track_purchase_never_raises_even_if_a_sender_errors(monkeypatch):
    # Even with a key set, a sender blowing up must be swallowed (background task).
    monkeypatch.setattr(tracking, "META_CAPI_TOKEN", "tok")
    monkeypatch.setattr(tracking, "GA4_API_SECRET", "")

    def _boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(tracking, "_meta_purchase", _boom)
    assert tracking.track_purchase("rid123", 499, "INR", "9876543210", None) is None
