"""
Payment robustness helpers (v2).

- `event_id_of`: the stable per-payment id used for webhook idempotency (the dedupe
  itself lives in `payments_v2.claim_event` / the `webhook_events` table).
- `_rzp` / `configured`: the Razorpay client + a "creds present?" check, used by the
  recovery backstop (`api._reconcile_and_deliver` + `api._find_recoverable_v2`).
- `refund`: issue a Razorpay refund and record it in the v2 `refunds` table.

The v1 primitives (already_processed / mark_processed / find_recoverable / claim_paid /
reconcile / ensure_tables) were retired with the v2 cutover — the v2 layer (payments_v2 +
db_v2 + api._reconcile_and_deliver) replaced them.

Env: RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET.
"""
import logging
import os

logger = logging.getLogger("axtroshastra.payments")


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


def refund(payment_id: str, amount_paise: int | None = None) -> dict:
    """Issue a Razorpay refund for a captured payment and record it in the v2
    `refunds` table. `payment_id` is the razorpay_payment_id; we resolve it to our
    `payments.id` for the FK. Full refund when `amount_paise` is None. If the payment
    isn't in our DB, the refund is still issued but logged as unrecorded (the refunds
    FK requires a known payment row)."""
    import db_v2
    client = _rzp()
    if client is None:
        return {"error": "razorpay not configured"}
    data = {} if amount_paise is None else {"amount": amount_paise}
    r = client.payment.refund(payment_id, data)
    status = (r.get("status") or "pending")
    if status not in ("pending", "processed", "failed"):
        status = "pending"
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM payments WHERE razorpay_payment_id=%s", (payment_id,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    "INSERT INTO refunds(id, payment_id, amount_paise, status, reason) "
                    "VALUES(%s,%s,%s,%s,%s)",
                    (db_v2._new_id("rf_"), row[0],
                     int(r.get("amount") or amount_paise or 0), status, None))
                conn.commit()
            else:
                logger.error("[refund] razorpay payment %s not in our payments table; "
                             "refund issued but NOT recorded locally", payment_id)
    finally:
        conn.close()
    return r
