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
import os
from datetime import datetime


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


def reconcile(db, limit: int = 200) -> dict:
    """Check unpaid reports that have an order against Razorpay; mark any that were
    actually paid. Returns a summary. Safe no-op if Razorpay is not configured."""
    client = _rzp()
    if client is None:
        return {"checked": 0, "recovered": 0, "note": "razorpay not configured"}
    with db() as c:
        rows = c.execute("SELECT id,order_id FROM reports "
                         "WHERE paid=0 AND order_id IS NOT NULL LIMIT ?",
                         (limit,)).fetchall()
    recovered = 0
    for rid, order_id in rows:
        try:
            payments = client.order.payments(order_id)
            captured = [p for p in payments.get("items", []) if p.get("status") == "captured"]
            if captured:
                pay = captured[0]
                with db() as c:
                    c.execute("UPDATE reports SET paid=1,payment_id=?,phone=? WHERE id=?",
                              (pay.get("id"), pay.get("contact") or "", rid))
                recovered += 1
        except Exception:
            continue
    return {"checked": len(rows), "recovered": recovered}


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
