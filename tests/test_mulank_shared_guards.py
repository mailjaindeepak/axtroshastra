"""The shared payment paths must never mark a Mulank report paid (only /api/mulank/* may), and must
behave exactly as before for every other product. Covers /api/webhook (notes.report_id), /api/_demo_pay
(even with DEMO_MODE=1), and the other shared unlock paths: /api/order (incl. free pass), /api/verify
and the reconcile sweep."""
import hashlib
import hmac
import itertools
import json

import pytest

import api
import db_v2
import mulank_content as mc
import mulank_payment as mp
import numerology
import payments
import reports_v2

KEY_SECRET = "rzp_key_secret_guard_test"
KUNDLI = {"name": "Guard Buyer", "dob": "1990-05-10", "tob": "09:20",
          "time_quality": "T0", "place": "Delhi", "gender": "male"}
_seq = itertools.count(1)


def _wh(body: dict):
    raw = json.dumps(body).encode()
    sig = hmac.new(api.RZP_WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return {"content": raw, "headers": {"X-Razorpay-Signature": sig}}


def _paid(rid):
    conn = db_v2.get_conn()
    try:
        return reports_v2.read_report(conn, rid)["paid"]
    finally:
        conn.close()


def _payments_for(rid):
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT status, amount_paise FROM payments WHERE report_id=%s", (rid,))
            return cur.fetchall()
    finally:
        conn.close()


class Rzp:
    def __init__(self):
        self.orders = []
        outer = self

        class order:
            @staticmethod
            def create(d):
                outer.orders.append(d)
                return {"id": "order_" + d["receipt"][-30:], "amount": d["amount"], "currency": d["currency"]}

        class payment:
            @staticmethod
            def fetch(pid):
                return outer.entity
        self.order, self.payment, self.entity = order, payment, {}


@pytest.fixture
def rz(monkeypatch):
    s = Rzp()
    monkeypatch.setattr(api, "RZP_SECRET", KEY_SECRET)
    monkeypatch.setattr(api, "rzp_client", lambda: s)
    for name in ("_pregenerate_pdf_task", "_generate_narrative_task"):
        monkeypatch.setattr(api, name, lambda *a, **k: None)
    monkeypatch.setattr(api, "send_whatsapp_report", lambda *a, **k: None)
    return s


@pytest.fixture
def eligible(monkeypatch):
    res = numerology.compute_mulank(29, 7, 1990, today=mc._today())
    monkeypatch.setattr(mc, "REGISTRY", {k: mc.Entry(mc.VERIFIED, "Test Reviewer", "2026-11-03")
                                         for k in mc.required_keys(res)})


def _mulank(client):
    """A Mulank report WITH a real order created through the dedicated route."""
    r = client.post("/api/mulank", json={"name": "Priya Sharma", "dob": "29/07/1990", "gender": "female", "country_code": "+91",
                                         "phone": "97%08d" % (60000000 + next(_seq)), "consent_terms": True})
    assert r.status_code == 200, r.text
    rid = r.json()["report_id"]
    o = client.post("/api/mulank/order", json={"report_id": rid})
    assert o.status_code == 200, o.text
    return rid, o.json()["razorpay_order_id"]


def _kundli(client, phone):
    rid = client.post("/api/kundli", json=KUNDLI).json()["report_id"]
    r = client.post("/api/order", json={"report_id": rid, "phone": phone})
    assert r.status_code == 200, r.text
    return rid, r.json()["razorpay_order_id"]


def _captured_event(rid, oid, pid, amount=29900, eid="evt"):
    return {"event": "payment.captured", "payload": {"payment": {"entity": {
        "id": pid, "order_id": oid, "amount": amount, "currency": "INR", "status": "captured", "method": "upi",
        "contact": "+919800000000", "email": "x@example.com", "notes": {"report_id": rid}}}}}


# ------------------------------------------------------------------ 1. /api/webhook + notes.report_id
@pytest.mark.parametrize("amount", [100, 29900, 49900])
def test_shared_webhook_never_unlocks_a_mulank_report(client, rz, eligible, amount):
    rid, oid = _mulank(client)
    r = client.post("/api/webhook", **_wh(_captured_event(rid, oid, "pay_g_" + str(amount), amount)))
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert not _paid(rid)
    assert all(s != "captured" for s, _ in _payments_for(rid))


def test_shared_webhook_notes_pointing_at_a_mulank_report_is_ignored_even_with_a_foreign_order(client, rz, eligible):
    rid, _ = _mulank(client)
    r = client.post("/api/webhook", **_wh(_captured_event(rid, "order_somebody_elses", "pay_g_foreign")))
    assert r.status_code == 200 and not _paid(rid)


def test_dedicated_flow_still_unlocks_the_same_report(client, rz, eligible, monkeypatch):
    import mulank_routes
    done = []
    monkeypatch.setattr(mulank_routes, "FULFIL", lambda rid, bg: done.append(rid))
    rid, oid = _mulank(client)
    pid = "pay_ded_" + oid[-20:]
    rz.entity = {"id": pid, "order_id": oid, "amount": 29900, "currency": "INR", "status": "captured", "method": "upi"}
    sig = hmac.new(KEY_SECRET.encode(), f"{oid}|{pid}".encode(), hashlib.sha256).hexdigest()
    r = client.post("/api/mulank/verify", json={"razorpay_order_id": oid, "razorpay_payment_id": pid, "razorpay_signature": sig})
    assert r.status_code == 200 and _paid(rid) and done == [rid]


# ------------------------------------------------------------------ 2. /api/_demo_pay
def test_demo_pay_route_exists_in_this_run(client):
    assert api.DEMO_MODE is True                 # conftest sets DEMO_MODE=1, so the bypass route is live here
    assert client.post("/api/_demo_pay/nonexistent").status_code == 404


def test_demo_pay_for_a_mulank_report_follows_numerology_rules_not_the_shared_shortcut(client, rz, eligible, monkeypatch):
    """Owner decision (14 Nov 2026): Numerology unlocks through /api/_demo_pay like every other product, in DEMO_MODE only. It is NOT the shared
    shortcut: an incomplete pair is refused (409) and stays unpaid, an unknown id is a 404. The full behaviour is in test_mulank_demo_pay.py."""
    import mulank_content
    rid, _ = _mulank(client)
    r = client.post(f"/api/_demo_pay/{rid}")
    assert r.status_code == 200 and _paid(rid)
    # an ineligible pair (nothing approved for its numbers) cannot be unlocked
    monkeypatch.setattr(mulank_content, "REGISTRY", {})
    r2 = client.post("/api/mulank", json={"name": "No Order", "dob": "15/03/1985", "country_code": "+91",
                                          "phone": "97%08d" % (60000000 + next(_seq)), "consent_terms": True})
    rid2 = r2.json()["report_id"]
    assert client.post(f"/api/_demo_pay/{rid2}").status_code == 409 and not _paid(rid2)
    assert client.post("/api/_demo_pay/no-such-report").status_code == 404


def test_demo_pay_still_works_for_other_products(client):
    rid = client.post("/api/kundli", json=KUNDLI).json()["report_id"]
    r = client.post(f"/api/_demo_pay/{rid}")
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert _paid(rid)


# ------------------------------------------------------------------ the other shared unlock paths
def test_shared_order_refuses_mulank_reports_so_no_499_charge_or_free_pass(client, rz, eligible):
    rid, _ = _mulank(client)
    n = len(rz.orders)
    assert client.post("/api/order", json={"report_id": rid, "phone": "9876500001"}).status_code == 404
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO passes(token) VALUES (%s)", ("GUARDPASS1",))
        conn.commit()
    finally:
        conn.close()
    assert client.post("/api/order", json={"report_id": rid, "pass": "GUARDPASS1"}).status_code == 404
    assert len(rz.orders) == n and not _paid(rid)
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT used FROM passes WHERE token=%s", ("GUARDPASS1",))
            assert cur.fetchone()[0] == 0
    finally:
        conn.close()


def test_shared_order_never_charges_mulank_default_price(client, rz, eligible):
    rid, _ = _mulank(client)
    client.post("/api/order", json={"report_id": rid, "phone": "9876500002"})
    assert all(o["amount"] == mp.MULANK_PRICE_PAISE for o in rz.orders)       # only the dedicated 29900 order exists


def test_shared_verify_refuses_a_mulank_order(client, rz, eligible):
    rid, oid = _mulank(client)
    pid = "pay_sv_" + oid[-20:]
    rz.entity = {"contact": "+919800000000", "email": "x@example.com", "amount": 29900}
    sig = hmac.new(KEY_SECRET.encode(), f"{oid}|{pid}".encode(), hashlib.sha256).hexdigest()
    r = client.post("/api/verify", json={"razorpay_order_id": oid, "razorpay_payment_id": pid, "razorpay_signature": sig})
    assert r.status_code == 404 and not _paid(rid)


class _RecRzp:
    def __init__(self, mapping):
        outer = self

        class order:
            @staticmethod
            def payments(order_id):
                return {"items": mapping.get(order_id, [])}
        self.order = order


def test_reconcile_sweep_skips_mulank_but_still_recovers_other_products(client, rz, eligible, monkeypatch):
    m_rid, m_oid = _mulank(client)
    k_rid, k_oid = _kundli(client, "9876500003")
    mapping = {m_oid: [{"id": "pay_rec_m", "status": "captured", "contact": "", "email": "", "amount": 29900}],
               k_oid: [{"id": "pay_rec_k", "status": "captured", "contact": "", "email": "", "amount": 49900}]}
    monkeypatch.setattr(payments, "configured", lambda: True)
    monkeypatch.setattr(payments, "_rzp", lambda: _RecRzp(mapping))
    res = api._reconcile_and_deliver()
    assert res["recovered"] >= 1
    assert _paid(k_rid) is True and not _paid(m_rid)


# ------------------------------------------------------------------ existing flows unchanged
def test_existing_order_verify_and_webhook_flow_is_unchanged(client, rz):
    rid, oid = _kundli(client, "9876500004")
    pid = "pay_ex_" + oid[-20:]
    rz.entity = {"contact": "+919800000000", "email": "x@example.com", "amount": 49900, "method": "upi"}
    sig = hmac.new(KEY_SECRET.encode(), f"{oid}|{pid}".encode(), hashlib.sha256).hexdigest()
    r = client.post("/api/verify", json={"razorpay_order_id": oid, "razorpay_payment_id": pid, "razorpay_signature": sig})
    assert r.status_code == 200 and r.json()["report_id"] == rid and _paid(rid)

    rid2, oid2 = _kundli(client, "9876500005")
    ev = _captured_event(rid2, oid2, "pay_ex_wh_" + oid2[-15:], amount=49900)
    assert client.post("/api/webhook", **_wh(ev)).status_code == 200
    assert _paid(rid2)
    assert client.post("/api/webhook", **_wh(ev)).status_code == 200       # duplicate event is still a quiet no-op


def test_existing_order_endpoint_still_prices_and_creates_orders(client, rz):
    _kundli(client, "9876500006")
    assert rz.orders and rz.orders[-1]["amount"] == api.PRICE_PAISE


def test_guard_helper_is_exact():
    assert api._is_mulank_report({"product": "numerology_mulank"}) is True
    for p in ("marriage", "milan", "iq_test", "career_intelligence", "diwali", "vyapar", "", None):
        assert api._is_mulank_report({"product": p}) is False
    assert api._is_mulank_report(None) is False and api._is_mulank_report({}) is False


@pytest.fixture(autouse=True)
def _pin_today(monkeypatch):
    """Personal years depend on the calendar; pin it so these tests do not age."""
    from datetime import date
    monkeypatch.setattr(mc, "_today", lambda: date(2026, 11, 3))