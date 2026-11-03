"""Routes for the Mulank payment flow. Mounted by api.py with one include_router line.

`api` is imported inside handlers (not at module top) because api.py includes this
router; it also keeps api.RZP_SECRET / api.rzp_client() monkeypatchable in tests.
DEMO_MODE is deliberately never read here.
"""
import json
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel

import db_v2
import mulank_payment as mp
import payments

logger = logging.getLogger("axtroshastra")
router = APIRouter()


def _fulfil(rid: str, background: BackgroundTasks) -> None:
    """Seam for fulfilment (PDF + website access + optional WhatsApp). The paid-report
    renderer is a later piece, so for now we only log; entitlement is already recorded."""
    logger.info("[mulank] paid, fulfilment pending renderer rid=%s", rid)


FULFIL = _fulfil


class MulankOrderIn(BaseModel):
    report_id: str | None = None        # nothing else is read: price comes from the server


def _http(e: mp.MulankPaymentError):
    return HTTPException(e.http, e.code)


@router.post("/api/mulank/order")
def mulank_order(body: MulankOrderIn):
    import api
    conn = db_v2.get_conn()
    try:
        try:
            return mp.create_order(conn, api.rzp_client(), body.report_id or "")
        except mp.MulankPaymentError as e:
            conn.rollback()
            raise _http(e)
    finally:
        conn.close()


@router.post("/api/mulank/verify")
def mulank_verify(body: dict, background_tasks: BackgroundTasks):
    import api
    pid = (body.get("razorpay_payment_id") or "").strip()
    oid = (body.get("razorpay_order_id") or "").strip()
    sig = (body.get("razorpay_signature") or "").strip()
    if not (pid and oid and sig):
        raise HTTPException(400, "missing_payment_fields")
    if not api.RZP_SECRET:
        raise HTTPException(503, "payment_not_configured")
    if not mp.signature_ok(api.RZP_SECRET, oid, pid, sig):
        raise HTTPException(400, "invalid_signature")
    try:
        ent = api.rzp_client().payment.fetch(pid)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[mulank] payment fetch failed: %s", e.__class__.__name__)
        raise HTTPException(502, "verification_unavailable")   # safe to retry; nothing unlocked
    conn = db_v2.get_conn()
    try:
        try:
            out = mp.settle(conn, ent, order_id=oid, payment_id=pid)
        except mp.MulankPaymentError as e:
            conn.rollback()
            raise _http(e)
    finally:
        conn.close()
    if out["deliver"]:
        FULFIL(out["report_id"], background_tasks)
    return {"ok": out["status"] == "paid", "status": out["status"], "report_id": out["report_id"]}


@router.post("/api/mulank/webhook")
async def mulank_webhook(request: Request, background_tasks: BackgroundTasks):
    import api
    raw = await request.body()
    if not api.RZP_WEBHOOK_SECRET:
        raise HTTPException(503, "webhook_not_configured")
    if not mp.webhook_signature_ok(api.RZP_WEBHOOK_SECRET, raw,
                                   request.headers.get("X-Razorpay-Signature", "")):
        raise HTTPException(400, "bad_signature")
    try:
        event = json.loads(raw)
    except ValueError:
        raise HTTPException(400, "bad_payload")
    if event.get("event") != "payment.captured":
        return {"ok": True}
    ent = (((event.get("payload") or {}).get("payment") or {}).get("entity")) or {}
    oid, pid = ent.get("order_id") or "", ent.get("id") or ""
    if not (oid and pid):
        return {"ok": True}
    conn = db_v2.get_conn()
    try:
        try:
            out = mp.settle(conn, ent, order_id=oid, payment_id=pid,
                            event_id=payments.event_id_of(event), event_type="payment.captured")
        except mp.MulankPaymentError as e:
            conn.rollback()
            if e.code == "order_not_found":     # not a Mulank order: the shared webhook's job
                return {"ok": True}
            logger.error("[mulank] webhook rejected code=%s", e.code)
            return {"ok": False, "error": e.code}   # 200 so Razorpay does not retry a bad payment forever
    finally:
        conn.close()
    if out["deliver"]:
        FULFIL(out["report_id"], background_tasks)
    return {"ok": True}
