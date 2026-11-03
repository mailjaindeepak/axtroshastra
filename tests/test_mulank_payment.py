"""Mulank-only payment flow: server-side order, signature + amount + currency + order +
captured-status verification, single fulfilment, and no bypass via DEMO_MODE or sample
content. Razorpay is stubbed; the DB is the real throwaway MySQL from conftest."""
import hashlib
import hmac
import itertools
import json

import pytest

import api
import db_v2
import mulank_content as mc
import mulank_payment as mp
import mulank_routes
import reports_v2

SECRET = "rzp_key_secret_mulank_test"
WH_SECRET = "mulank-webhook-secret"
DOB = "1990-07-29"
_seq = itertools.count(1)


def _sign(oid, pid):
    return hmac.new(SECRET.encode(), f"{oid}|{pid}".encode(), hashlib.sha256).hexdigest()


def _wh_sig(raw: bytes):
    return hmac.new(WH_SECRET.encode(), raw, hashlib.sha256).hexdigest()


class Stub:
    """Razorpay client double. `entity` is what payment.fetch returns for any id."""
    def __init__(self):
        self.orders, self.entity, self.fetch_error = [], None, None
        stub = self

        class order:
            @staticmethod
            def create(d):
                stub.orders.append(d)
                return {"id": "order_" + d["receipt"], "amount": d["amount"],
                        "currency": d["currency"]}

        class payment:
            @staticmethod
            def fetch(pid):
                if stub.fetch_error:
                    raise stub.fetch_error
                return dict(stub.entity)
        self.order, self.payment = order, payment


@pytest.fixture
def rz(monkeypatch):
    s = Stub()
    monkeypatch.setattr(api, "RZP_SECRET", SECRET)
    monkeypatch.setattr(api, "RZP_WEBHOOK_SECRET", WH_SECRET)
    monkeypatch.setattr(api, "rzp_client", lambda: s)
    monkeypatch.setattr(api, "DEMO_MODE", True)       # must change nothing
    return s


@pytest.fixture
def fulfilled(monkeypatch):
    calls = []
    monkeypatch.setattr(mulank_routes, "FULFIL", lambda rid, bg: calls.append(rid))
    return calls


@pytest.fixture
def eligible(monkeypatch):
    """Test-only registry where every key for DOB is verified by a named reviewer."""
    from datetime import date
    import numerology
    d = date.fromisoformat(DOB)
    res = numerology.compute_mulank(d.day, d.month, d.year)
    reg = {k: mc.Entry(mc.VERIFIED, "Test Reviewer", "2026-11-03") for k in mc.required_keys(res)}
    monkeypatch.setattr(mc, "REGISTRY", reg)


def _report(product=mp.PRODUCT, dob=DOB, phone=True):
    rid = "mk%030d" % next(_seq)
    conn = db_v2.get_conn()
    try:
        reports_v2.save_report(
            conn, rid, {"product": product, "dob": dob, "meta": {}}, [],
            product=product, phone=("98%08d" % (30000000 + next(_seq))) if phone else None)
        conn.commit()
    finally:
        conn.close()
    return rid


def _paid(rid):
    conn = db_v2.get_conn()
    try:
        return reports_v2.read_report(conn, rid)["paid"]
    finally:
        conn.close()


def _pid(oid):
    return "pay_" + oid[-30:]


def _ent(oid, pid=None, **kw):
    e = {"id": pid or _pid(oid), "order_id": oid, "amount": 29900, "currency": "INR",
         "status": "captured", "method": "upi", "contact": "+919800000000",
         "email": "b@example.com"}
    e.update(kw)
    return e


def _verify(client, oid, pid=None, sig=None):
    pid = pid or _pid(oid)
    return client.post("/api/mulank/verify", json={
        "razorpay_order_id": oid, "razorpay_payment_id": pid,
        "razorpay_signature": _sign(oid, pid) if sig is None else sig})


def _order(client, rid, **extra):
    return client.post("/api/mulank/order", json={"report_id": rid, **extra})


# ------------------------------------------------------------------ price + order
def test_price_is_299_rupees_in_inr():
    assert mp.MULANK_PRICE_PAISE == 29900 and mp.MULANK_CURRENCY == "INR"


def test_order_refused_for_every_pair_today_even_in_demo_mode(client, rz):
    rid = _report()
    r = _order(client, rid)
    assert r.status_code == 409 and r.json()["detail"] == "not_available"
    assert rz.orders == []                      # no Razorpay order was ever created


def test_sample_ok_content_cannot_open_checkout(client, rz, monkeypatch):
    import numerology
    res = numerology.compute_mulank(29, 7, 1990)
    monkeypatch.setattr(mc, "REGISTRY", {k: mc.Entry(mc.SAMPLE_OK, "X", "2026-11-03")
                                         for k in mc.required_keys(res)})
    assert _order(client, _report()).status_code == 409 and rz.orders == []


def test_order_created_server_side_with_fixed_price_ignoring_client(client, rz, eligible):
    rid = _report()
    r = _order(client, rid, amount=100, currency="USD", price=1)
    assert r.status_code == 200, r.text
    assert r.json() == {"razorpay_order_id": "order_" + rid, "amount": 29900, "currency": "INR", "key_id": api.RZP_KEY}
    assert rz.orders[0]["amount"] == 29900 and rz.orders[0]["currency"] == "INR"
    assert "secret" not in json.dumps(r.json()).lower()


def test_order_refused_for_other_product_unknown_and_missing(client, rz, eligible):
    assert _order(client, _report(product="iq_test")).status_code == 404
    assert _order(client, "nope").status_code == 404
    assert _order(client, None).status_code == 404
    assert rz.orders == []


def test_order_needs_contact(client, rz, eligible):
    assert _order(client, _report(phone=False)).status_code == 400


def test_bad_or_missing_dob_is_not_eligible(client, rz, eligible):
    assert _order(client, _report(dob="not-a-date")).status_code == 409
    assert _order(client, _report(dob="2999-01-01")).status_code == 409


# ------------------------------------------------------------------ verify
def _ready(client, rz, eligible_fixture=None):
    rid = _report()
    oid = _order(client, rid).json()["razorpay_order_id"]
    return rid, oid


def test_verified_captured_payment_unlocks_once(client, rz, eligible, fulfilled):
    rid, oid = _ready(client, rz)
    rz.entity = _ent(oid)
    assert not _paid(rid)
    r = _verify(client, oid)
    assert r.status_code == 200 and r.json() == {"ok": True, "status": "paid", "report_id": rid}
    assert _paid(rid) and fulfilled == [rid]
    assert _verify(client, oid).status_code == 200          # replay
    assert fulfilled == [rid]                                # still exactly one fulfilment


def test_bad_signature_never_unlocks_even_in_demo_mode(client, rz, eligible, fulfilled):
    rid, oid = _ready(client, rz)
    rz.entity = _ent(oid)
    assert _verify(client, oid, sig="deadbeef").status_code == 400
    assert not _paid(rid) and fulfilled == []


def test_missing_fields_and_unconfigured(client, rz, monkeypatch):
    assert client.post("/api/mulank/verify", json={}).status_code == 400
    monkeypatch.setattr(api, "RZP_SECRET", "")
    assert _verify(client, "o", "p").status_code == 503


@pytest.mark.parametrize("patch,code", [
    ({"amount": 100}, "amount_mismatch"),
    ({"amount": 49900}, "amount_mismatch"),
    ({"amount": "abc"}, "amount_mismatch"),
    ({"currency": "USD"}, "currency_mismatch"),
    ({"order_id": "order_other"}, "order_mismatch"),
    ({"id": "pay_other"}, "payment_id_mismatch"),
    ({"status": "failed"}, "status_failed"),
    ({"status": "refunded"}, "status_refunded"),
    ({"amount_refunded": 5000}, "refunded"),
])
def test_entity_mismatch_never_unlocks(client, rz, eligible, fulfilled, patch, code):
    rid, oid = _ready(client, rz)
    rz.entity = _ent(oid, **patch)
    r = _verify(client, oid)
    assert r.status_code == 409 and r.json()["detail"] == code
    assert not _paid(rid) and fulfilled == []


@pytest.mark.parametrize("status", ["authorized", "created"])
def test_not_captured_yet_is_pending_and_does_not_unlock(client, rz, eligible, fulfilled, status):
    rid, oid = _ready(client, rz)
    rz.entity = _ent(oid, status=status)
    r = _verify(client, oid)
    assert r.status_code == 200 and r.json()["status"] == "pending" and r.json()["ok"] is False
    assert not _paid(rid) and fulfilled == []
    rz.entity = _ent(oid)                                    # later captured: same order, no recharge
    assert _verify(client, oid).json()["ok"] is True and _paid(rid)


def test_gateway_outage_fails_closed_then_retry_works(client, rz, eligible, fulfilled):
    rid, oid = _ready(client, rz)
    rz.fetch_error = RuntimeError("razorpay down")
    r = _verify(client, oid)
    assert r.status_code == 502 and not _paid(rid) and fulfilled == []
    rz.fetch_error, rz.entity = None, _ent(oid)
    assert _verify(client, oid).status_code == 200 and _paid(rid) and fulfilled == [rid]


def test_other_products_order_cannot_be_settled_here(client, rz, fulfilled):
    rid = _report(product="iq_test")
    conn = db_v2.get_conn()
    try:
        import payments_v2
        uid = db_v2.get_report(conn, rid)["user_id"]
        payments_v2.record_order(conn, rid, uid, 4900, "order_iq_" + rid[-20:])
        conn.commit()
    finally:
        conn.close()
    rz.entity = _ent("order_iq_" + rid[-20:])
    assert _verify(client, "order_iq_" + rid[-20:]).status_code == 404
    assert not _paid(rid) and fulfilled == []


def test_unknown_order_404(client, rz):
    rz.entity = _ent("order_ghost")
    assert _verify(client, "order_ghost").status_code == 404


# ------------------------------------------------------------------ webhook
def _hook(client, oid, pid=None, event="payment.captured", eid=None, sig=True, **ent_kw):
    eid = eid or "evt_" + oid[-30:]
    body = {"event": event, "payload": {"payment": {"entity": _ent(oid, pid, **ent_kw)}}}
    raw = json.dumps(body).encode()
    return client.post("/api/mulank/webhook", content=raw, headers={
        "X-Razorpay-Signature": _wh_sig(raw) if sig else "bad", "X-Razorpay-Event-Id": eid})


def test_webhook_unlocks_and_duplicates_fulfil_once(client, rz, eligible, fulfilled):
    rid, oid = _ready(client, rz)
    assert _hook(client, oid).status_code == 200
    assert _paid(rid) and fulfilled == [rid]
    assert _hook(client, oid).status_code == 200            # same event again
    assert _hook(client, oid, eid="evt_2_" + oid[-20:]).status_code == 200   # new event id, same payment
    assert fulfilled == [rid]


def test_webhook_and_verify_race_fulfil_once(client, rz, eligible, fulfilled):
    rid, oid = _ready(client, rz)
    rz.entity = _ent(oid)
    _hook(client, oid)
    _verify(client, oid)
    assert fulfilled == [rid]


def test_webhook_bad_signature_400(client, rz, eligible, fulfilled):
    rid, oid = _ready(client, rz)
    assert _hook(client, oid, sig=False).status_code == 400
    assert not _paid(rid) and fulfilled == []


def test_webhook_wrong_amount_or_currency_rejected(client, rz, eligible, fulfilled):
    rid, oid = _ready(client, rz)
    for kw in ({"amount": 100}, {"currency": "USD"}, {"status": "authorized"}):
        r = _hook(client, oid, eid="evt_" + oid[-20:] + str(sorted(kw)), **kw)
        assert r.status_code == 200
    assert not _paid(rid) and fulfilled == []


def test_webhook_ignores_notes_report_id_and_binds_by_order(client, rz, eligible, fulfilled):
    victim, v_oid = _ready(client, rz)
    other = _report()
    r = _hook(client, "order_unrelated", notes={"report_id": other})
    assert r.status_code == 200 and not _paid(other) and not _paid(victim)
    assert fulfilled == []


def test_webhook_other_events_and_other_products_are_noops(client, rz, eligible, fulfilled):
    rid, oid = _ready(client, rz)
    assert _hook(client, oid, event="payment.failed").status_code == 200
    assert _hook(client, oid, event="order.paid", eid="e9_" + oid[-20:]).status_code == 200
    assert not _paid(rid) and fulfilled == []


# ------------------------------------------------------------------ pure helpers
def test_check_entity_ok_and_signature_helpers():
    assert mp.check_entity(_ent("o", "p"), payment_id="p", order_id="o") == ("ok", "")
    assert mp.signature_ok("s", "o", "p", hmac.new(b"s", b"o|p", hashlib.sha256).hexdigest())
    assert not mp.signature_ok("", "o", "p", "x") and not mp.signature_ok("s", "o", "p", "")
    assert not mp.webhook_signature_ok("", b"x", "y")

