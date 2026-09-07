"""Payment recovery backstop — "no paid customer is ever left without their
report". If a browser closes mid-payment AND the Razorpay webhook is missed, the
report is orphaned (paid on Razorpay, unpaid in our DB, never delivered).

`api._reconcile_and_deliver` is the webhook-independent net: it asks Razorpay
which unpaid-in-our-DB reports (that carry a Razorpay order) were actually
captured, and runs the SAME shared delivery the webhook does — but ONLY for the
caller that atomically flips the report to paid inside payments_v2.capture_payment,
so nothing is ever double-delivered. Delivery goes to the POPUP number only (§1).

v2: the recovery scan (_find_recoverable_v2) joins reports+payments on
razorpay_order_id, so a recoverable candidate always has a user (a payment row
needs one). The orphan/order rows are set up through the real /api/order route.
Razorpay is stubbed via payments.configured() + payments._rzp().
"""
import api
import db_v2
import payments
import payments_v2

KUNDLI = {"name": "Recovery Buyer", "dob": "1991-07-22", "tob": "08:15",
          "time_quality": "T0", "place": "Delhi", "gender": "female"}


# --------------------------------------------------------------------- stubs
class _ApiOrder:
    def __init__(self, oid):
        self._oid = oid

    def create(self, d):
        return {"id": self._oid, "amount": d["amount"]}


class _ApiRzp:
    """Stub for api.rzp_client() (order creation at /api/order)."""
    def __init__(self, oid):
        self.order = _ApiOrder(oid)


class _RecOrder:
    def __init__(self, mapping):
        self._m = mapping                      # order_id -> [payment dicts]

    def payments(self, order_id):
        return {"items": self._m.get(order_id, [])}


class _RecRzp:
    def __init__(self, mapping):
        self.order = _RecOrder(mapping)


def _stub_reconcile_rzp(monkeypatch, mapping):
    """Make Razorpay 'configured' and answer order.payments() from `mapping` for
    the reconcile path (payments._rzp / payments.configured)."""
    monkeypatch.setattr(payments, "configured", lambda: True)
    monkeypatch.setattr(payments, "_rzp", lambda: _RecRzp(mapping))


def _captured(pid, contact="", email=""):
    return {"id": pid, "status": "captured", "contact": contact, "email": email,
            "amount": 49900}


def _record_delivery(monkeypatch):
    """Record the delivery tasks so we can assert what the recovery path ran.
    _reconcile_and_deliver calls these SYNCHRONOUSLY (background=None)."""
    calls = {"wa": [], "pdf": [], "narr": [], "email": []}
    monkeypatch.setattr(api, "send_whatsapp_report",
                        lambda *a, **k: calls["wa"].append((a, k)))
    monkeypatch.setattr(api, "_pregenerate_pdf_task",
                        lambda rid: calls["pdf"].append(rid))
    monkeypatch.setattr(api, "_generate_narrative_task",
                        lambda rid: calls["narr"].append(rid))
    monkeypatch.setattr(api, "email_report",
                        lambda *a, **k: calls["email"].append((a, k)))
    return calls


def _orphan_with_order(client, monkeypatch, oid, popup_phone):
    """A report that is unpaid in our DB but carries a Razorpay order (+ popup
    user), i.e. exactly what the recovery scan looks for."""
    rid = client.post("/api/kundli", json=KUNDLI).json()["report_id"]
    monkeypatch.setattr(api, "rzp_client", lambda: _ApiRzp(oid))
    r = client.post("/api/order", json={"report_id": rid, "phone": popup_phone})
    assert r.status_code == 200, r.text
    return rid


# ------------------------------------------------- reconcile delivers (part 1)
def test_reconcile_delivers_to_popup_number(client, monkeypatch):
    calls = _record_delivery(monkeypatch)
    oid, pid = "order_rec_1", "pay_rec_1"
    rid = _orphan_with_order(client, monkeypatch, oid, "9876540001")
    _stub_reconcile_rzp(monkeypatch, {oid: [_captured(pid, contact="+911112223001")]})

    res = api._reconcile_and_deliver()

    assert res["recovered"] == 1
    assert client.get(f"/api/report/{rid}").json()["paid"] is True   # marked paid
    # PDF + narrative scheduled, exactly one WhatsApp to the POPUP number.
    assert calls["pdf"] == [rid]
    assert calls["narr"] == [rid]
    assert len(calls["wa"]) == 1
    args, _ = calls["wa"][0]
    assert args[0] == "+919876540001"              # popup number, NOT +911112223001
    assert args[1] == rid
    assert args[2] == "Recovery Buyer"             # _display_name(payload)
    assert args[3] == "marriage"


# ----------------------------------------- idempotency vs the webhook (part 2)
def test_already_paid_report_not_redelivered(client, monkeypatch):
    """A report the webhook already delivered (paid) is never re-delivered by the
    poll — the recovery scan only looks at unpaid rows, and the claim would fail
    anyway."""
    calls = _record_delivery(monkeypatch)
    oid, pid = "order_rec_2", "pay_rec_2"
    rid = _orphan_with_order(client, monkeypatch, oid, "9876540002")
    # Webhook already handled it: mark paid directly.
    conn = db_v2.get_conn()
    try:
        db_v2.set_report_paid(conn, rid)
        conn.commit()
    finally:
        conn.close()
    _stub_reconcile_rzp(monkeypatch, {oid: [_captured(pid, contact="+911112223002")]})

    res = api._reconcile_and_deliver()

    assert res["recovered"] == 0
    assert calls["wa"] == [] and calls["pdf"] == [] and calls["narr"] == []


# ------------------------------------ idempotency: only the claimant delivers
def test_claim_gate_delivers_exactly_once(client, monkeypatch):
    """Two overlapping cycles that BOTH see the same candidate must produce ONE
    delivery — only the cycle that flips the report to paid delivers. We bypass
    the SQL scan (monkeypatch _find_recoverable_v2) to hit the claim directly."""
    calls = _record_delivery(monkeypatch)
    oid, pid = "order_rec_3", "pay_rec_3"
    rid = _orphan_with_order(client, monkeypatch, oid, "9876540003")
    cand = {"rid": rid, "order_id": oid, "payment_id": pid,
            "contact": "+911112223003", "email": "", "amount": 49900}
    monkeypatch.setattr(payments, "configured", lambda: True)
    monkeypatch.setattr(api, "_find_recoverable_v2", lambda conn, limit=200: [cand])

    r1 = api._reconcile_and_deliver()      # wins the claim -> delivers
    r2 = api._reconcile_and_deliver()      # loses the claim -> skips

    assert r1["recovered"] == 1
    assert r2["recovered"] == 0
    assert len(calls["wa"]) == 1           # exactly one delivery across both runs
    assert calls["pdf"] == [rid]


def test_capture_payment_claim_is_atomic(client, monkeypatch):
    """The primitive: capture_payment's atomic report claim returns True once
    (the deliverer), then False forever."""
    oid = "order_rec_claim"
    rid = _orphan_with_order(client, monkeypatch, oid, "9876540011")
    conn = db_v2.get_conn()
    try:
        assert payments_v2.capture_payment(
            conn, report_id=rid, amount_paise=49900, razorpay_order_id=oid,
            razorpay_payment_id="pay_claim", event_id=None) is True
        conn.commit()
        assert payments_v2.capture_payment(
            conn, report_id=rid, amount_paise=49900, razorpay_order_id=oid,
            razorpay_payment_id="pay_claim", event_id=None) is False
        conn.commit()
    finally:
        conn.close()
    assert client.get(f"/api/report/{rid}").json()["paid"] is True


# ------------------------------------------------- no-contact edge (P5-3 guard)
def test_recovered_orphan_without_contact_skips_whatsapp(client, monkeypatch):
    """A recovery candidate whose report has NO user and NO Razorpay contact:
    still marked paid + report generated (viewable / in the account), WhatsApp
    skipped and NO crash (payments.user_id is NOT NULL — the P5-3 guard). We
    insert a bare userless report directly, since v2's normal scan can't produce
    a userless candidate."""
    calls = _record_delivery(monkeypatch)
    conn = db_v2.get_conn()
    try:
        rid = db_v2.create_report(conn, None, "marriage",
                                  {"product": "marriage", "teaser": {"verdict": "ok"},
                                   "meta": {"name": "No Contact"}}, status="preview")
        conn.commit()
    finally:
        conn.close()
    cand = {"rid": rid, "order_id": "order_rec_4", "payment_id": "pay_rec_4",
            "contact": "", "email": "", "amount": 49900}
    monkeypatch.setattr(payments, "configured", lambda: True)
    monkeypatch.setattr(api, "_find_recoverable_v2", lambda conn, limit=200: [cand])

    res = api._reconcile_and_deliver()

    assert res["recovered"] == 1
    assert client.get(f"/api/report/{rid}").json()["paid"] is True   # paid + viewable
    assert calls["pdf"] == [rid]                    # report still generated
    assert calls["wa"] == []                        # no number -> no send, no crash


# --------------------------------------------------- no-razorpay safe no-op
def test_reconcile_noop_without_razorpay(client, monkeypatch):
    calls = _record_delivery(monkeypatch)
    monkeypatch.setattr(payments, "configured", lambda: False)

    res = api._reconcile_and_deliver()

    assert res["recovered"] == 0
    assert res.get("note") == "razorpay not configured"
    assert calls["wa"] == [] and calls["pdf"] == []
