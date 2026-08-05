"""Payment recovery backstop — "no paid customer is ever left without their
report". If a browser closes mid-payment AND the Razorpay webhook is missed, the
report is orphaned (paid on Razorpay, paid=0 in our DB, never delivered).

`api._reconcile_and_deliver` is the webhook-independent net: it asks Razorpay
which unpaid-in-our-DB reports were actually captured and runs the SAME delivery
the webhook does — but ONLY for the caller that atomically flips paid 0->1
(`payments.claim_paid`), so nothing is ever double-delivered.

Razorpay creds are absent in tests, so `payments._rzp` is stubbed. Delivery tasks
are recorded via monkeypatch (like tests/test_contact_capture.py). The suite
shares one sqlite DB, so every test uses a UNIQUE popup number (users de-dupe by
mobile, first email wins).
"""
import api
import payments

KUNDLI = {"name": "Recovery Buyer", "dob": "1991-07-22", "tob": "08:15",
          "time_quality": "T0", "place": "Delhi", "gender": "female"}


# --------------------------------------------------------------------- stubs
class _StubOrder:
    def __init__(self, mapping):
        self._m = mapping                      # order_id -> [payment dicts]

    def payments(self, order_id):
        return {"items": self._m.get(order_id, [])}


class _StubRzp:
    def __init__(self, mapping):
        self.order = _StubOrder(mapping)


def _stub_razorpay(monkeypatch, mapping):
    """Make Razorpay 'configured' and answer order.payments() from `mapping`."""
    monkeypatch.setattr(payments, "_rzp", lambda: _StubRzp(mapping))


def _captured(pid, contact="", email=""):
    return {"id": pid, "status": "captured", "contact": contact, "email": email}


def _record_delivery(monkeypatch):
    """Record the delivery tasks so we can assert what the recovery path ran.
    _reconcile_and_deliver calls these SYNCHRONOUSLY (no BackgroundTasks)."""
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


def _orphan(client, order_id, popup_phone=None):
    """A report that is paid=0 in our DB but will be 'captured' on Razorpay."""
    rid = client.post("/api/kundli", json=KUNDLI).json()["report_id"]
    api.set_order(rid, order_id)
    if popup_phone:
        api.store_user_contact(rid, popup_phone)
    return rid


# ------------------------------------------------- reconcile delivers (part 1)
def test_reconcile_delivers_to_popup_number(client, monkeypatch):
    calls = _record_delivery(monkeypatch)
    oid, pid = "order_rec_1", "pay_rec_1"
    rid = _orphan(client, oid, popup_phone="9876540001")
    _stub_razorpay(monkeypatch, {oid: [_captured(pid, contact="+911112223001")]})

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

    with api.db() as c:
        pay_phone = c.execute("SELECT phone FROM reports WHERE id=?",
                              (rid,)).fetchone()[0]
    assert pay_phone == "+911112223001"            # payment number kept verbatim


# ----------------------------------------- idempotency vs the webhook (part 2)
def test_already_paid_report_not_redelivered(client, monkeypatch):
    """A report the webhook already delivered (paid=1) is never re-delivered by
    the poll — find_recoverable only looks at paid=0 rows, and the claim would
    fail anyway."""
    calls = _record_delivery(monkeypatch)
    oid, pid = "order_rec_2", "pay_rec_2"
    rid = _orphan(client, oid, popup_phone="9876540002")
    # Webhook already handled it: paid=1.
    api.mark_paid(rid, payment_id=pid, phone="+911112223002")
    # Razorpay still says captured, but our DB already shows paid.
    _stub_razorpay(monkeypatch, {oid: [_captured(pid, contact="+911112223002")]})

    res = api._reconcile_and_deliver()

    assert res["recovered"] == 0
    assert calls["wa"] == [] and calls["pdf"] == [] and calls["narr"] == []


# ------------------------------------ idempotency: only the claimant delivers
def test_claim_gate_delivers_exactly_once(client, monkeypatch):
    """Two overlapping cycles that BOTH see the same candidate must produce ONE
    delivery — only the caller that flips paid 0->1 delivers. We bypass the
    paid=0 SQL filter (monkeypatch find_recoverable) to hit the claim directly."""
    calls = _record_delivery(monkeypatch)
    oid, pid = "order_rec_3", "pay_rec_3"
    rid = _orphan(client, oid, popup_phone="9876540003")
    cand = {"rid": rid, "order_id": oid, "payment_id": pid,
            "contact": "+911112223003", "email": ""}
    monkeypatch.setattr(payments, "configured", lambda: True)
    monkeypatch.setattr(payments, "find_recoverable", lambda db, limit=200: [cand])

    r1 = api._reconcile_and_deliver()      # wins the claim -> delivers
    r2 = api._reconcile_and_deliver()      # loses the claim -> skips

    assert r1["recovered"] == 1
    assert r2["recovered"] == 0
    assert len(calls["wa"]) == 1           # exactly one delivery across both runs
    assert calls["pdf"] == [rid]


def test_claim_paid_is_atomic(client):
    """The primitive: claim_paid returns True once, then False forever."""
    oid = "order_rec_claim"
    rid = _orphan(client, oid)
    assert payments.claim_paid(api.db, rid, "pay_claim", "+911119990001") is True
    assert payments.claim_paid(api.db, rid, "pay_claim", "+911119990001") is False
    assert client.get(f"/api/report/{rid}").json()["paid"] is True


# ------------------------------------------------- no-phone edge (part 1 edge)
def test_recovered_without_popup_number_skips_whatsapp(client, monkeypatch):
    """An old orphan with no captured popup number: still marked paid + report
    generated (viewable / in the account), WhatsApp skipped gracefully."""
    calls = _record_delivery(monkeypatch)
    oid, pid = "order_rec_4", "pay_rec_4"
    rid = _orphan(client, oid, popup_phone=None)   # no user_phone
    _stub_razorpay(monkeypatch, {oid: [_captured(pid, contact="+911112223004")]})

    res = api._reconcile_and_deliver()

    assert res["recovered"] == 1
    assert client.get(f"/api/report/{rid}").json()["paid"] is True   # paid + viewable
    assert calls["pdf"] == [rid]                    # report still generated
    assert calls["wa"] == []                        # no number -> no send, no crash


# --------------------------------------------------- no-razorpay safe no-op
def test_reconcile_noop_without_razorpay(client, monkeypatch):
    calls = _record_delivery(monkeypatch)
    # No _rzp stub: credentials absent -> configured() is False.
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("RAZORPAY_KEY_SECRET", raising=False)

    res = api._reconcile_and_deliver()

    assert res["recovered"] == 0
    assert res.get("note") == "razorpay not configured"
    assert calls["wa"] == [] and calls["pdf"] == []
