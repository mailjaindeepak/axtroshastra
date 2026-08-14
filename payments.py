"""
Payment robustness helpers. (#6)

- Webhook idempotency: a `webhook_events` table records every processed event id
  so duplicate Razorpay deliveries (which happen on retries) are ignored and side
  effects like WhatsApp delivery fire exactly once.
- Reconciliation: `reconcile()` cross-checks reports marked unpaid against
  Razorpay's order/payment status, catching payments whose webhook was missed.
- Refunds: `refund()` issues a Razorpay refund and records it.

All functions take the app's `db` connection factory so there is a single source
of truth for storage and no circular import with api.py.

Env: RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET (reused from the app).
"""
import logging
import os
from datetime import datetime

import users

logger = logging.getLogger("axtroshastra.payments")


def ensure_tables(db):
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS webhook_events(
            event_id TEXT PRIMARY KEY, event_type TEXT, report_id TEXT,
            processed_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS refunds(
            refund_id TEXT PRIMARY KEY, payment_id TEXT, report_id TEXT,
            amount INTEGER, status TEXT, created_at TEXT)""")


def already_processed(db, event_id: str) -> bool:
    """True if this webhook event id was handled before (idempotency guard)."""
    if not event_id:
        return False
    with db() as c:
        row = c.execute("SELECT 1 FROM webhook_events WHERE event_id=?",
                        (event_id,)).fetchone()
    return row is not None


def mark_processed(db, event_id: str, event_type: str, report_id: str):
    if not event_id:
        return
    with db() as c:
        c.execute("INSERT OR IGNORE INTO webhook_events"
                  "(event_id,event_type,report_id,processed_at) VALUES(?,?,?,?)",
                  (event_id, event_type, report_id, datetime.utcnow().isoformat()))


def event_id_of(event: dict) -> str:
    """Razorpay sends a stable id per payment entity; use it for dedupe."""
    try:
        return event["payload"]["payment"]["entity"]["id"]
    except (KeyError, TypeError):
        return event.get("id", "")


def _rzp():
    key, secret = os.getenv("RAZORPAY_KEY_ID", ""), os.getenv("RAZORPAY_KEY_SECRET", "")
    if not (key and secret):
        return None
    import razorpay
    return razorpay.Client(auth=(key, secret))


def configured() -> bool:
    """True when Razorpay credentials are present, so the recovery backstop (poll
    thread / admin sweep) can run. False -> every recovery path is a safe no-op."""
    return _rzp() is not None


def find_recoverable(db, limit: int = 200) -> list:
    """Cross-check unpaid reports that carry an order against Razorpay and return
    the ones Razorpay reports as *captured* — i.e. paid there but still paid=0 in
    our DB (a missed webhook / tab closed mid-payment). Returns a list of dicts
    ``{rid, order_id, payment_id, contact, email}``. It does NOT mark or deliver:
    the caller flips paid via ``claim_paid`` (the atomic idempotency gate) so the
    recovery path can run the SAME delivery the webhook does. Empty list when
    Razorpay is not configured."""
    client = _rzp()
    if client is None:
        return []
    with db() as c:
        rows = c.execute("SELECT id,order_id FROM reports "
                         "WHERE paid=0 AND order_id IS NOT NULL LIMIT ?",
                         (limit,)).fetchall()
    out = []
    for rid, order_id in rows:
        try:
            pays = client.order.payments(order_id)
            captured = [p for p in pays.get("items", []) if p.get("status") == "captured"]
            if captured:
                pay = captured[0]
                out.append({"rid": rid, "order_id": order_id,
                            "payment_id": pay.get("id"),
                            "contact": pay.get("contact") or "",
                            "email": pay.get("email") or "",
                            "amount": pay.get("amount")})
        except Exception:
            continue
    return out


def claim_paid(db, rid: str, payment_id: str, phone: str) -> bool:
    """Atomically flip ONE report unpaid->paid and report whether THIS caller won
    the flip. The whole idempotency story rests here:

        UPDATE reports SET paid=1,... WHERE id=? AND paid=0

    Because the ``AND paid=0`` predicate is evaluated inside the single UPDATE,
    exactly one caller can change the row from 0 to 1; every later attempt (the
    webhook that already delivered, or an overlapping poll cycle) matches zero
    rows. Returns True only when ``rowcount == 1`` — the caller that must deliver.
    A False result means someone else already handled the report; do NOT deliver."""
    with db() as c:
        cur = c.execute(
            "UPDATE reports SET paid=1,payment_id=?,phone=? WHERE id=? AND paid=0",
            (payment_id, phone or "", rid))
        return cur.rowcount == 1


def reconcile(db, limit: int = 200) -> dict:
    """Non-delivering reconcile (account-link only), kept for callers that just
    want unpaid-but-captured reports flipped + linked to an account. The
    deliver-capable backstop is ``api._reconcile_and_deliver``. Now claims each
    report atomically (``claim_paid``) so it can never double-fire. Safe no-op if
    Razorpay is not configured."""
    if not configured():
        return {"checked": 0, "recovered": 0, "note": "razorpay not configured"}
    candidates = find_recoverable(db, limit)
    recovered = 0
    for cand in candidates:
        rid = cand["rid"]
        if not claim_paid(db, rid, cand["payment_id"], cand["contact"]):
            continue                     # someone else already handled it
        try:                             # account: same mobile+email capture as the webhook
            uid = users.upsert_user_from_payment(
                db, mobile=cand["contact"], email=cand["email"])
            if uid:
                users.link_report(db, rid, uid)
        except Exception as e:           # never fatal, but MUST be visible (was silent)
            logger.error("[users] reconcile account link failed for %s: %s", rid, e)
        recovered += 1
    return {"checked": len(candidates), "recovered": recovered}


def refund(db, payment_id: str, amount_paise: int | None = None) -> dict:
    """Issue a refund for a captured payment and record it."""
    client = _rzp()
    if client is None:
        return {"error": "razorpay not configured"}
    data = {} if amount_paise is None else {"amount": amount_paise}
    r = client.payment.refund(payment_id, data)
    with db() as c:
        report_id = (c.execute("SELECT id FROM reports WHERE payment_id=?",
                               (payment_id,)).fetchone() or [None])[0]
        c.execute("INSERT OR REPLACE INTO refunds"
                  "(refund_id,payment_id,report_id,amount,status,created_at)"
                  " VALUES(?,?,?,?,?,?)",
                  (r.get("id"), payment_id, report_id, r.get("amount"),
                   r.get("status"), datetime.utcnow().isoformat()))
    return r
