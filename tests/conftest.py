"""Shared pytest fixtures. Env is set BEFORE importing the app, because api.py
reads configuration at import time."""
import hashlib
import hmac
import json
import os
import tempfile

os.environ.setdefault("DEMO_MODE", "1")  # enables /api/_demo_pay for the escape test
# The whole suite shares one TestClient (=> one client IP), so the per-IP token
# bucket would throttle /api/kundli across unrelated tests. Disable the MIDDLEWARE
# here; the limiter algorithm itself is still unit-tested directly in test_features.
os.environ.setdefault("RATE_LIMIT_ENABLED", "0")
os.environ.setdefault("DB_PATH", os.path.join(tempfile.mkdtemp(), "reports.db"))
os.environ.setdefault("RAZORPAY_WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("STATS_KEY", "test-stats-key")
os.environ["ADMIN_KEY"] = ""
os.environ["DB_HOST"] = ""
os.environ.setdefault("NARRATIVE_ENABLED", "0")

import pytest
from fastapi.testclient import TestClient

import api


@pytest.fixture(scope="session")
def client():
    return TestClient(api.app)


@pytest.fixture
def pay_webhook():
    """Shared helper (was copy-pasted into test_users / test_contact_capture /
    test_tracking): build a real HMAC-SHA256-signed Razorpay `payment.captured`
    webhook for `rid` and POST it to /api/webhook. The signing key is the same
    RAZORPAY_WEBHOOK_SECRET the app was imported with (set at the top of this
    file). Returns the helper so tests call:

        pay_webhook(client, rid, payment_id, contact, email=None)
    """
    secret = os.environ["RAZORPAY_WEBHOOK_SECRET"].encode()

    def _pay(client, rid, payment_id, contact, email=None):
        ent = {"id": payment_id, "contact": contact, "notes": {"report_id": rid}}
        if email is not None:
            ent["email"] = email
        event = {"event": "payment.captured",
                 "payload": {"payment": {"entity": ent}}}
        body = json.dumps(event).encode()
        sig = hmac.new(secret, body, hashlib.sha256).hexdigest()
        r = client.post("/api/webhook", content=body,
                        headers={"X-Razorpay-Signature": sig})
        assert r.status_code == 200, r.text
        return r.json()

    return _pay
