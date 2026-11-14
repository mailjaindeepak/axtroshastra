"""Mulank-only Razorpay payment logic (price, order, verification, capture).

Self-contained on purpose: it reuses the shared `payments_v2` / `reports_v2`
helpers but changes none of them, and it never reads DEMO_MODE. Every check below
runs on the server; the browser callback alone never unlocks anything.

Contract with the report record (written by POST /api/mulank, piece 4):
  rec["product"] == PRODUCT and rec["payload"]["dob"] == "YYYY-MM-DD".
"""
import hashlib
import hmac
import logging
from datetime import date

import db_v2
import mulank_content
import mulank_preorder
import numerology
import payments_v2
import reports_v2

logger = logging.getLogger("axtroshastra")

PRODUCT = "numerology_mulank"
from mulank_pricing import MULANK_PRICE_PAISE, MULANK_LIST_PRICE_PAISE, MULANK_CURRENCY  # noqa: E402,F401


DEMO_UNLOCK_KEY = "demo_unlock"           # report meta set by mulank_demo.py (development only). Such a report is never a sale.


def is_demo_unlock(payload) -> bool:
    """True when the report was unlocked by demo pay: no server Purchase and no WhatsApp message must ever be sent for it."""
    return bool(((payload or {}).get("meta") or {}).get(DEMO_UNLOCK_KEY))


def numerology_event_id(rid: str) -> str:
    """The id every ad and analytics platform sees for this report: "mk_" + the first 16 hex characters of SHA-256 of the report id.
    The report id is the private link token, so it never leaves the server or the page; the page computes the identical value in
    pages/numerology.html (evId) so the browser and server copies of one event deduplicate. One-way: the id cannot be turned back
    into the report id."""
    return "mk_" + hashlib.sha256(str(rid).encode("utf-8")).hexdigest()[:16]


class MulankPaymentError(Exception):
    def __init__(self, code: str, http: int = 400):
        super().__init__(code)
        self.code, self.http = code, http


def _hmac_hex(secret: str, msg) -> str:
    if isinstance(msg, str):
        msg = msg.encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def signature_ok(key_secret: str, order_id: str, payment_id: str, sig: str) -> bool:
    if not (key_secret and order_id and payment_id and sig):
        return False
    return hmac.compare_digest(_hmac_hex(key_secret, f"{order_id}|{payment_id}"), sig)


def webhook_signature_ok(webhook_secret: str, raw_body: bytes, sig: str) -> bool:
    if not (webhook_secret and sig):
        return False
    return hmac.compare_digest(_hmac_hex(webhook_secret, raw_body), sig)


def check_entity(ent: dict, *, payment_id: str, order_id: str):
    """Judge a Razorpay payment entity. Returns (verdict, reason):
    ("ok", "")  every check passed, safe to unlock
    ("pending", reason)  not captured yet (authorized/created); do not unlock, retry later
    ("reject", reason)  mismatch, failure or refund; never unlock."""
    if (ent.get("id") or "") != payment_id:
        return "reject", "payment_id_mismatch"
    if (ent.get("order_id") or "") != order_id:
        return "reject", "order_mismatch"
    try:
        amount = int(ent.get("amount"))
    except (TypeError, ValueError):
        return "reject", "amount_mismatch"
    if amount != MULANK_PRICE_PAISE:
        return "reject", "amount_mismatch"
    if (ent.get("currency") or "") != MULANK_CURRENCY:
        return "reject", "currency_mismatch"
    status = ent.get("status") or ""
    if status in ("authorized", "created"):
        return "pending", "not_captured"
    if status != "captured":
        return "reject", "status_" + (status or "unknown")
    if int(ent.get("amount_refunded") or 0) > 0:
        return "reject", "refunded"
    return "ok", ""


def dob_of(rec: dict):
    """(day, month, year) from the stored report, or None if it is not a valid ISO date."""
    raw = ((rec.get("payload") or {}).get("dob") or "")
    try:
        d = date.fromisoformat(raw)
    except (TypeError, ValueError):
        return None
    return d.day, d.month, d.year


def readiness_for(rec: dict, today=None) -> dict:
    dob = dob_of(rec)
    if not dob:
        return {"eligible": False, "reason_code": "no_dob", "missing": ["dob"], "pair_key": "?",
                "content_version": mulank_content.CONTENT_VERSION}
    try:
        return mulank_content.pair_readiness(*dob, today=today)
    except numerology.NumerologyInputError:
        return {"eligible": False, "reason_code": "bad_dob", "missing": ["dob"], "pair_key": "?",
                "content_version": mulank_content.CONTENT_VERSION}


def _mulank_report(conn, rid: str):
    rec = reports_v2.read_report(conn, rid)
    if not rec or rec.get("product") != PRODUCT:
        return None
    return rec


def create_order(conn, rzp_factory, rid: str, preorder=None) -> dict:
    """Server-side order for a Mulank report. Price is the constant above; the client
    supplies nothing but the report id. Refuses ineligible pairs BEFORE any Razorpay call.
    With `preorder` (an enabled mulank_preorder.config()) the rule flips: only a pair that is NOT yet sellable may
    pre-order; a sellable pair must use the normal order. A pre-order never unlocks anything by itself."""
    rec = _mulank_report(conn, rid or "")
    if not rec:
        raise MulankPaymentError("report_not_found", 404)
    if rec["paid"]:
        return {"already_paid": True}
    ready = readiness_for(rec)
    if preorder is None:
        if not ready["eligible"]:
            logger.info(mulank_content.gap_log_line(ready))
            raise MulankPaymentError("not_available", 409)
    else:
        if not preorder.get("enabled"):
            raise MulankPaymentError("preorder_closed", 409)
        if ready["eligible"]:
            raise MulankPaymentError("use_order", 409)
        if ready["reason_code"] in ("no_dob", "bad_dob"):
            raise MulankPaymentError("not_available", 409)
    urec = db_v2.get_report(conn, rid)
    uid = urec.get("user_id") if urec else None
    if not uid:
        raise MulankPaymentError("contact_required", 400)
    order = rzp_factory().order.create({
        "amount": MULANK_PRICE_PAISE, "currency": MULANK_CURRENCY, "receipt": rid,
        "notes": {"report_id": rid, "product": PRODUCT, "preorder": "1" if preorder else "0",
                  "content_version": ready["content_version"]}})
    if int(order.get("amount") or 0) != MULANK_PRICE_PAISE or order.get("currency") != MULANK_CURRENCY:
        logger.error("[mulank] razorpay order amount/currency differs from request rid=%s", rid)
        raise MulankPaymentError("order_mismatch", 502)
    payments_v2.record_order(conn, rid, uid, MULANK_PRICE_PAISE, order["id"])
    if preorder:
        mulank_preorder.record(conn, rid, preorder)
    conn.commit()
    return {"razorpay_order_id": order["id"], "amount": MULANK_PRICE_PAISE,
            "currency": MULANK_CURRENCY}


def _order_row(conn, order_id: str):
    with conn.cursor() as cur:
        cur.execute("SELECT report_id, amount_paise, status FROM payments "
                    "WHERE razorpay_order_id=%s ORDER BY created_at DESC LIMIT 1", (order_id,))
        return cur.fetchone()


def settle(conn, ent: dict, *, order_id: str, payment_id: str, event_id=None,
           event_type: str = "verify") -> dict:
    """Validate the payment entity and, only if every check passes, record the capture.
    Returns {"status": "paid"|"pending", "report_id", "deliver": bool}. `deliver` is True
    for exactly one caller per report (the atomic claim in payments_v2.capture_payment),
    so a duplicate verify/webhook never triggers fulfilment twice.
    Raises MulankPaymentError for anything that must not unlock."""
    row = _order_row(conn, order_id)
    if not row:
        raise MulankPaymentError("order_not_found", 404)
    rid, stored_amount, _pay_status = row
    if not _mulank_report(conn, rid):
        raise MulankPaymentError("order_not_found", 404)      # another product's order
    if int(stored_amount or 0) != MULANK_PRICE_PAISE:
        logger.error("[mulank] stored order amount differs from price rid=%s", rid)
        raise MulankPaymentError("amount_mismatch", 409)
    verdict, reason = check_entity(ent, payment_id=payment_id, order_id=order_id)
    if verdict == "pending":
        return {"status": "pending", "report_id": rid, "deliver": False}
    if verdict == "reject":
        logger.error("[mulank] payment rejected rid=%s reason=%s", rid, reason)
        raise MulankPaymentError(reason, 409)
    already_paid = bool(_mulank_report(conn, rid)["paid"])
    deliver = payments_v2.capture_payment(
        conn, report_id=rid, amount_paise=MULANK_PRICE_PAISE, razorpay_order_id=order_id,
        razorpay_payment_id=payment_id, event_id=event_id, event_type=event_type,
        method=ent.get("method") if ent.get("method") in ("upi", "card", "netbanking", "wallet") else None,
        payment_email=ent.get("email") or None, payment_contact=ent.get("contact") or None)
    if already_paid and not deliver:
        # a second, different order captured for a report that was already paid
        logger.warning("[mulank] extra captured payment on paid report rid=%s "
                       "(duplicate charge, review for refund)", rid)
    conn.commit()
    rec_now = _mulank_report(conn, rid)
    if deliver and not readiness_for(rec_now)["eligible"]:
        # capture is never blocked after money moved; a pre-order is expected here, anything else needs a person
        if mulank_preorder.get(rec_now["payload"]):
            logger.info("[mulank] pre-order paid; report will be fulfilled when its content is approved")
        else:
            logger.error("[mulank] paid while content not approved rid=%s (manual review)", rid)
    return {"status": "paid", "report_id": rid, "deliver": bool(deliver)}
