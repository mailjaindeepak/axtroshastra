"""
payments_v2.py — payment flows on the MySQL-native db_v2 layer (Piece 3).

Covers: create a payment at order time, capture it at webhook/verify, and redeem
a free pass. All functions take an open connection and DO NOT commit (the caller
owns the transaction). MySQL-native; ON DUPLICATE KEY UPDATE, never REPLACE.

Two idempotency guards, matching the v1 design (so money/delivery happen once):
  * webhook_events (event_id PK) — a repeated Razorpay webhook for the SAME event
    is ignored (`claim_event` returns False the second time).
  * an atomic report claim (UPDATE ... WHERE status <> 'paid') — when the webhook
    and the /api/verify fallback race to capture the same payment, exactly ONE
    wins the right to run delivery (`capture_payment` returns True only for it).
"""
import logging
from datetime import datetime, timezone

import db_v2


def _now():
    # timezone-aware UTC (datetime.utcnow() is deprecated in Python 3.12+).
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def claim_event(conn, event_id, *, event_type=None, razorpay_payment_id=None,
                report_id=None) -> bool:
    """Record a Razorpay event once. True = first time we've seen it (process it);
    False = a duplicate we've already recorded (skip)."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT IGNORE INTO webhook_events(event_id, event_type, "
            "razorpay_payment_id, report_id) VALUES(%s,%s,%s,%s)",
            (event_id, event_type, razorpay_payment_id, report_id))
        return cur.rowcount == 1


def record_order(conn, report_id, user_id, amount_paise, razorpay_order_id) -> str:
    """Create the payment row when the Razorpay order is created (status='created')."""
    return db_v2.record_payment(conn, report_id, user_id, amount_paise,
                                razorpay_order_id=razorpay_order_id, status="created")


def capture_payment(conn, *, report_id, amount_paise, razorpay_order_id=None,
                    razorpay_payment_id=None, event_id=None,
                    event_type="payment.captured", method=None, upi_vpa=None,
                    payment_email=None, payment_contact=None, paid_at=None) -> bool:
    """Mark a payment captured and the report paid. Returns True for the ONE caller
    that should run delivery (WhatsApp/PDF/email); False for a duplicate webhook
    event or a later racing caller. Safe to call more than once."""
    # Guard 1: a repeated webhook for the same event_id is a no-op.
    if event_id is not None and not claim_event(
            conn, event_id, event_type=event_type,
            razorpay_payment_id=razorpay_payment_id, report_id=report_id):
        return False

    # Guard 2: only the first caller to flip the report preview->paid delivers.
    with conn.cursor() as cur:
        cur.execute("UPDATE reports SET status='paid' WHERE id=%s AND status<>'paid'",
                    (report_id,))
        should_deliver = cur.rowcount == 1

    # Settlement detail on the payment row (idempotent).
    paid_at = paid_at or _now()
    pid = None
    if razorpay_order_id is not None:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM payments WHERE razorpay_order_id=%s",
                        (razorpay_order_id,))
            row = cur.fetchone()
            pid = row[0] if row else None
    if pid:
        db_v2.mark_payment_captured(
            conn, pid, razorpay_payment_id=razorpay_payment_id, method=method,
            upi_vpa=upi_vpa, payment_email=payment_email,
            payment_contact=payment_contact, paid_at=paid_at,
            amount_paise=(amount_paise or None))   # §13/P5-6: persist the ACTUAL charged amount
    else:
        # No order row on file (recovery path): create a captured payment, taking
        # the owner from the report.
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM reports WHERE id=%s", (report_id,))
            r = cur.fetchone()
        user_id = r[0] if r else None
        if user_id:
            db_v2.record_payment(
                conn, report_id, user_id, amount_paise, razorpay_order_id=razorpay_order_id,
                razorpay_payment_id=razorpay_payment_id, status="captured", method=method,
                upi_vpa=upi_vpa, payment_email=payment_email,
                payment_contact=payment_contact, paid_at=paid_at)
        else:
            # P5-3: an orphan captured with NO user at all (payments.user_id is NOT
            # NULL, so we can't write a payment row). A real Razorpay capture always
            # carries a contact, so callers normally attach a user first; this is the
            # last-resort guard. The report is ALREADY flipped to paid by the atomic
            # claim above — so the customer isn't harmed — we just can't record the
            # payment row. Log loudly for manual Razorpay reconciliation; never crash.
            logging.getLogger("axtroshastra").error(
                "[payments_v2] captured report %s has no user and no contact — marked "
                "paid but payment row NOT recorded (reconcile from Razorpay).", report_id)
    return should_deliver


def redeem_free_pass(conn, *, token, report_id, user_id) -> bool:
    """Atomically redeem a free pass: mark it used, create a ₹0 free_pass payment,
    mark the report paid. Returns True if THIS call redeemed it; False if the pass
    was already used or doesn't exist (the atomic UPDATE is the one-winner gate)."""
    with conn.cursor() as cur:
        cur.execute("UPDATE passes SET used=1, used_at=%s WHERE token=%s AND used=0",
                    (_now(), token))
        if cur.rowcount != 1:
            return False   # invalid or already-used pass
    pid = db_v2.record_payment(conn, report_id, user_id, 0, status="captured",
                               method="free_pass", paid_at=_now())
    with conn.cursor() as cur:
        cur.execute("UPDATE passes SET used_by_payment_id=%s WHERE token=%s", (pid, token))
    db_v2.set_report_paid(conn, report_id)
    return True
