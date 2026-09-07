"""End-to-end v2 ROUTE tests (Phase 4) — the real gate for the cutover wiring.

Unlike the other db/ tests, these import `api` and drive the actual FastAPI routes
(create report -> order -> webhook/verify/free-pass) against a throwaway v2 MySQL DB,
so the route WIRING is covered, not just the modules. Env points at a throwaway DB
BEFORE `import api`, so load_dotenv can't pull prod and db_v2/dbcompat hit the test DB.

Needs a MySQL server (same as the rest of db/); safe-by-default via ALLOW_NO_DB.
Run: DB_HOST=.. DB_PORT=.. DB_USER=.. DB_PASSWORD=.. pytest db/test_routes_v2.py -v
"""
import hashlib
import hmac
import json
import os
import re
from pathlib import Path

import pymysql
import pytest

ROUTE_DB = os.getenv("DBV2_ROUTE_DB", "axtroshastra_v2_route_test")
os.environ["DB_NAME"] = ROUTE_DB            # BEFORE any `import api` below (in the fixture)
SCHEMA_FILE = Path(__file__).with_name("schema_v2.sql")
WH_SECRET = "wh_secret_routes_v2"
KEY_SECRET = "key_secret_routes_v2"

KUNDLI = {"name": "Route Test", "dob": "1992-03-03", "tob": "07:07",
          "time_quality": "T0", "place": "Delhi", "lat": 28.6, "lon": 77.2,
          "tz": "Asia/Kolkata", "gender": "female"}


def _server_conn(database=None):
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"), port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"), password=os.getenv("DB_PASSWORD", ""),
        database=database, charset="utf8mb4", autocommit=True)


def _statements(ddl):
    for chunk in re.sub(r"--[^\n]*", "", ddl).split(";"):
        if chunk.strip():
            yield chunk


class _StubRzp:
    """Fake Razorpay: order.create (for /api/order) + payment.fetch (for /api/verify)."""
    class order:
        @staticmethod
        def create(d):
            return {"id": "order_" + d["receipt"], "amount": d["amount"], "currency": "INR"}
    class payment:
        @staticmethod
        def fetch(pid):
            return {"contact": "+911119999999", "email": "", "amount": 49900, "method": "upi"}


@pytest.fixture
def client(monkeypatch):
    try:
        admin = _server_conn()
    except Exception as e:
        if (os.getenv("ALLOW_NO_DB") or "").strip() == "1":
            pytest.skip(f"ALLOW_NO_DB=1 and no MySQL ({e.__class__.__name__})")
        raise
    with admin.cursor() as c:
        c.execute(f"DROP DATABASE IF EXISTS {ROUTE_DB}")
        c.execute(f"CREATE DATABASE {ROUTE_DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
    admin.close()
    loader = _server_conn(database=ROUTE_DB)
    with loader.cursor() as c:
        for stmt in _statements(SCHEMA_FILE.read_text()):
            c.execute(stmt)
    loader.close()

    monkeypatch.setenv("DB_NAME", ROUTE_DB)
    import api
    from fastapi.testclient import TestClient
    monkeypatch.setattr(api, "RZP_WEBHOOK_SECRET", WH_SECRET)
    monkeypatch.setattr(api, "RZP_SECRET", KEY_SECRET)
    monkeypatch.setattr(api, "rzp_client", lambda: _StubRzp())
    calls = {"wa": [], "pdf": [], "narr": [], "email": []}
    monkeypatch.setattr(api, "send_whatsapp_report", lambda *a, **k: calls["wa"].append(a))
    monkeypatch.setattr(api, "_pregenerate_pdf_task", lambda rid: calls["pdf"].append(rid))
    monkeypatch.setattr(api, "_generate_narrative_task", lambda rid: calls["narr"].append(rid))
    monkeypatch.setattr(api, "email_report", lambda *a, **k: calls["email"].append(a))
    monkeypatch.setattr(api.tracking, "track_purchase", lambda *a, **k: None)
    with TestClient(api.app) as c:
        c.calls = calls
        yield c
    admin = _server_conn()
    with admin.cursor() as cur:
        cur.execute(f"DROP DATABASE IF EXISTS {ROUTE_DB}")
    admin.close()


def _make_report(client):
    r = client.post("/api/kundli", json=KUNDLI)
    assert r.status_code == 200, r.text
    return r.json()["report_id"]


def _webhook(client, rid, pid, contact, order_id="order_x"):
    body = json.dumps({"event": "payment.captured", "payload": {"payment": {"entity": {
        "id": pid, "contact": contact, "email": "", "amount": 49900, "method": "upi",
        "order_id": order_id, "notes": {"report_id": rid}}}}}).encode()
    sig = hmac.new(WH_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return client.post("/api/webhook", content=body, headers={"X-Razorpay-Signature": sig})


def test_orphan_webhook_with_contact_does_not_whatsapp_razorpay_number(client):
    """P5-1 + P5-3: a paid report with NO popup user must NOT be WhatsApp'd to
    Razorpay's contact — it's skipped — and it must not crash."""
    rid = _make_report(client)                       # orphan: no popup user
    assert _webhook(client, rid, "pay_o1", "+911110000001").status_code == 200
    assert client.get(f"/api/report/{rid}").json()["paid"] is True   # paid, no crash
    assert client.calls["wa"] == []                  # WhatsApp SKIPPED (never Razorpay's number)


def test_popup_webhook_delivers_to_popup_number_only(client):
    """P5-1: with a popup number captured at order, delivery goes to THAT number,
    never the (different) Razorpay contact."""
    rid = _make_report(client)
    o = client.post("/api/order", json={"report_id": rid, "phone": "9876500001"})
    assert o.status_code == 200, o.text
    oid = o.json()["razorpay_order_id"]
    assert _webhook(client, rid, "pay_p1", "+911110000002", order_id=oid).status_code == 200
    assert client.get(f"/api/report/{rid}").json()["paid"] is True
    assert len(client.calls["wa"]) == 1
    assert client.calls["wa"][0][0] == "+919876500001"   # popup number, NOT +911110000002


def test_duplicate_webhook_delivers_once(client):
    """Idempotency: the same captured event twice = one delivery."""
    rid = _make_report(client)
    o = client.post("/api/order", json={"report_id": rid, "phone": "9876500002"})
    oid = o.json()["razorpay_order_id"]
    assert _webhook(client, rid, "pay_d1", "+911110000003", order_id=oid).status_code == 200
    assert _webhook(client, rid, "pay_d1", "+911110000003", order_id=oid).status_code == 200
    assert len(client.calls["wa"]) == 1                  # exactly one, not two


def test_orphan_webhook_no_contact_delivers_or_skips_without_crashing(client):
    """P5-3 reproduction: a captured orphan with NO contact at all must still not
    crash (today the recovery path can hit user_id=None -> NOT NULL). Expected to
    FAIL until P5-3 is fixed."""
    rid = _make_report(client)
    assert _webhook(client, rid, "pay_o2", "").status_code == 200   # no contact
    assert client.get(f"/api/report/{rid}").json()["paid"] is True


def test_kundli_identifies_the_beacon_visitor(client):
    """events_v2.identify() wiring: a main-form kundli (with a phone) creates the
    user AND stitches the anonymous beacon visitor (ax_vid cookie) to it — so the
    visitor's prior anonymous browsing back-attributes to the account."""
    conn = _server_conn(database=ROUTE_DB)
    with conn.cursor() as cur:
        cur.execute("INSERT INTO visitors(visitor_id) VALUES('vis_idfy')")  # as the beacon would
    conn.close()
    r = client.post("/api/kundli", json={**KUNDLI, "phone": "9800012345"},
                    headers={"Cookie": "ax_vid=vis_idfy"})
    assert r.status_code == 200, r.text
    conn = _server_conn(database=ROUTE_DB)
    with conn.cursor() as cur:
        cur.execute("SELECT user_id FROM visitors WHERE visitor_id='vis_idfy'")
        uid = cur.fetchone()[0]
    conn.close()
    assert uid, "the beacon visitor should be stitched to the new user"


def test_refund_records_into_v2_refunds(client, monkeypatch):
    """payments.refund (admin /api/refund) issues a Razorpay refund and records it in
    the v2 `refunds` table, resolved to our payments.id via the FK."""
    import payments
    rid = _make_report(client)
    o = client.post("/api/order", json={"report_id": rid, "phone": "9876500099"})
    oid = o.json()["razorpay_order_id"]
    assert _webhook(client, rid, "pay_refund_1", "+911110000099", order_id=oid).status_code == 200

    class _RzpRefund:
        class payment:
            @staticmethod
            def refund(pid, data):
                return {"id": "rfnd_1", "amount": 49900, "status": "processed"}
    monkeypatch.setattr(payments, "_rzp", lambda: _RzpRefund())

    r = payments.refund("pay_refund_1")
    assert r["status"] == "processed"
    conn = _server_conn(database=ROUTE_DB)
    with conn.cursor() as cur:
        cur.execute("SELECT rf.amount_paise, rf.status FROM refunds rf "
                    "JOIN payments p ON p.id = rf.payment_id "
                    "WHERE p.razorpay_payment_id=%s", ("pay_refund_1",))
        row = cur.fetchone()
    conn.close()
    assert row == (49900, "processed")
