"""Mulank-specific payment recovery (the shared reconcile sweep skips Mulank on purpose).

For unpaid Mulank reports that have a Razorpay order, ask Razorpay for that order's payments and settle each
CAPTURED one through mulank_payment.settle: the same signature-free server verification as the dedicated routes
(payment id, matching order id, amount 29900, currency INR, captured, not refunded). Anything that does not
pass is logged and ignored, so a wrong-amount or foreign payment can never grant access.
"""
import logging
import os
import threading
import time

import db_v2
import mulank_payment as mp

logger = logging.getLogger("axtroshastra")
_lock = threading.Lock()
_started = False


def _candidates(conn, limit: int, rid=None):
    sql = ("SELECT r.id, p.razorpay_order_id FROM reports r JOIN payments p ON p.report_id = r.id "
           "WHERE r.product=%s AND r.status <> 'paid' AND p.razorpay_order_id IS NOT NULL ")
    args = [mp.PRODUCT]
    if rid:
        sql += "AND r.id=%s "
        args.append(rid)
    sql += "ORDER BY r.created_at DESC LIMIT %s"
    args.append(limit)
    with conn.cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchall()


def recover(client, *, limit: int = 100, rid=None) -> dict:
    """Settle captured payments for unpaid Mulank reports. Returns {"checked", "recovered", "paid": [rids to fulfil]}.
    `paid` lists reports THIS call flipped to paid (exactly one caller per report), ready for fulfilment."""
    out = {"checked": 0, "recovered": 0, "paid": []}
    if client is None or not _lock.acquire(blocking=False):
        return out
    conn = db_v2.get_conn()
    try:
        for r_id, order_id in _candidates(conn, limit, rid):
            out["checked"] += 1
            try:
                items = (client.order.payments(order_id) or {}).get("items", [])
            except Exception as e:
                logger.error("[mulank] recovery fetch failed: %s", e.__class__.__name__)
                continue
            for ent in items:
                if ent.get("status") != "captured" or not ent.get("id"):
                    continue
                try:
                    res = mp.settle(conn, ent, order_id=order_id, payment_id=ent["id"], event_type="reconcile")
                except mp.MulankPaymentError as e:
                    conn.rollback()
                    logger.error("[mulank] recovery rejected a payment code=%s", e.code)
                    continue
                if res["status"] == "paid":
                    out["recovered"] += 1
                    if res["deliver"]:
                        out["paid"].append(res["report_id"])
                    break
        return out
    finally:
        conn.close()
        _lock.release()


def start_loop(get_client, fulfil) -> None:
    """Background sweep; a no-op unless Razorpay is configured. Started once from the app's startup."""
    global _started
    if _started or os.getenv("MULANK_RECOVERY", "1") != "1":
        return
    _started = True
    interval = max(int(os.getenv("MULANK_RECOVERY_INTERVAL_SEC", "300") or 300), 30)

    def loop():
        while True:
            try:
                client = get_client()
                res = recover(client) if client is not None else None
                for rid in (res or {}).get("paid", []):
                    fulfil(rid, None)
            except Exception as e:
                logger.error("[mulank] recovery cycle error: %s", e.__class__.__name__)
            time.sleep(interval)
    threading.Thread(target=loop, name="mulank-recovery", daemon=True).start()
