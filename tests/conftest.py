"""Shared pytest fixtures. Env is set BEFORE importing the app, because api.py
reads configuration at import time.

The app is MySQL-native now (db_v2), so the suite runs against a throwaway MySQL
database built from db/schema_v2.sql and dropped at the end — one DB for the
whole session, mirroring the old shared-sqlite behaviour (tests keep phone
numbers unique per the shared-DB contract). `db_v2.get_conn()` defaults to
127.0.0.1:3306 (the real-local / RDS trap), so we set every DB_* explicitly:
CI overrides host/port/user/password via its MySQL service; locally they default
to the docker mysql on 3307. Missing DB = hard FAIL, not skip (deliberate
ALLOW_NO_DB=1 is the only escape) — matches db/conftest.py.
"""
import hashlib
import hmac
import json
import os
import re
from pathlib import Path

os.environ.setdefault("DEMO_MODE", "1")  # enables /api/_demo_pay for the escape test
# The whole suite shares one TestClient (=> one client IP), so the per-IP token
# bucket would throttle /api/kundli across unrelated tests. Disable the MIDDLEWARE
# here; the limiter algorithm itself is still unit-tested directly in test_features.
os.environ.setdefault("RATE_LIMIT_ENABLED", "0")
os.environ.setdefault("RAZORPAY_WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("STATS_KEY", "test-stats-key")
os.environ["ADMIN_KEY"] = ""
os.environ.setdefault("NARRATIVE_ENABLED", "0")

os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "3307")
os.environ.setdefault("DB_USER", "root")
os.environ.setdefault("DB_PASSWORD", "root")
os.environ["DB_NAME"] = "axtroshastra_v2_tests_suite"

_SCHEMA_FILE = Path(__file__).parent.parent / "db" / "schema_v2.sql"

import pytest
from fastapi.testclient import TestClient

import api


def _server_conn(database=None):
    import pymysql
    return pymysql.connect(
        host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=database, charset="utf8mb4", autocommit=True)


@pytest.fixture(scope="session", autouse=True)
def _v2_db():
    """Build a fresh throwaway v2 DB from the schema for the whole session; drop
    it after. Require a DB by default; only ALLOW_NO_DB=1 downgrades to skip."""
    name = os.environ["DB_NAME"]
    try:
        admin = _server_conn()
    except Exception as e:
        if (os.getenv("ALLOW_NO_DB") or "").strip() == "1":
            pytest.skip(f"ALLOW_NO_DB=1 and no MySQL ({e.__class__.__name__})")
        raise RuntimeError(
            "tests/ REQUIRE a MySQL database (the app is v2/MySQL-native) — this is "
            "a hard failure, not a skip. Start one (docker mysql on DB_PORT) or set "
            "ALLOW_NO_DB=1 to deliberately skip.") from e
    with admin.cursor() as c:
        c.execute(f"DROP DATABASE IF EXISTS {name}")
        c.execute(f"CREATE DATABASE {name} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
    admin.close()
    loader = _server_conn(database=name)
    with loader.cursor() as c:
        for stmt in re.sub(r"--[^\n]*", "", _SCHEMA_FILE.read_text()).split(";"):
            if stmt.strip():
                c.execute(stmt)
    loader.close()
    yield
    admin = _server_conn()
    with admin.cursor() as c:
        c.execute(f"DROP DATABASE IF EXISTS {name}")
    admin.close()


@pytest.fixture(scope="session")
def client(_v2_db):
    return TestClient(api.app)


@pytest.fixture
def pay_webhook():
    """Shared helper (was copy-pasted into test_users / test_contact_capture /
    test_tracking): build a real HMAC-SHA256-signed Razorpay `payment.captured`
    webhook for `rid` and POST it to /api/webhook. The signing key is the same
    RAZORPAY_WEBHOOK_SECRET the app was imported with (set at the top of this
    file). Returns the helper so tests call:

        pay_webhook(client, rid, payment_id, contact, email=None, order_id=None)

    Pass `order_id` (the razorpay_order_id from /api/order) for a realistic capture:
    it lets the app UPDATE the existing payment row instead of creating a second one
    (a real Razorpay webhook always carries order_id). Omit it only for orphan
    (no-order) captures.
    """
    secret = os.environ["RAZORPAY_WEBHOOK_SECRET"].encode()

    def _pay(client, rid, payment_id, contact, email=None, order_id=None, amount=None):
        ent = {"id": payment_id, "contact": contact, "notes": {"report_id": rid}}
        if email is not None:
            ent["email"] = email
        if order_id is not None:
            ent["order_id"] = order_id
        if amount is not None:
            ent["amount"] = amount
        event = {"event": "payment.captured",
                 "payload": {"payment": {"entity": ent}}}
        body = json.dumps(event).encode()
        sig = hmac.new(secret, body, hashlib.sha256).hexdigest()
        r = client.post("/api/webhook", content=body,
                        headers={"X-Razorpay-Signature": sig})
        assert r.status_code == 200, r.text
        return r.json()

    return _pay
