"""Server-side Purchase for a paid Mulank report (the backstop for the browser Purchase, which fires only if the buyer stays on the page).

Called once per paid report from mulank_fulfilment.schedule, which verify, webhook and both recovery paths all reach exactly once
(payments_v2.capture_payment's atomic claim). Never raises, never blocks the report.

Privacy (FUNNEL-EVENTS-CONTRACT.md, decision C3): the report id is the private link token, so every platform receives
mulank_payment.numerology_event_id(rid) instead, and the source URL is the public landing page, not a private report path.
What is sent is what Career Intelligence sends and nothing more: hashed phone, IP address, user agent, ad-click ids, value and currency.
Never the name, date of birth, report text, a raw phone number or the raw report id. A free-pass unlock is not a sale and sends nothing.
"""
import logging

import db_v2
import mulank_payment as mp
import reports_v2
import tracking

logger = logging.getLogger("axtroshastra")
SOURCE_PATH = "/en/numerology"


def source_url() -> str:
    return f"{tracking.PUBLIC_BASE_URL}{SOURCE_PATH}"


def _is_free_pass(conn, rid: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT method FROM payments WHERE report_id=%s AND status='captured' ORDER BY created_at DESC LIMIT 1", (rid,))
        row = cur.fetchone()
    return bool(row and row[0] == "free_pass")


def run(rid: str) -> bool:
    """Fire the server Purchase for this paid Mulank report. Returns True when it was handed to tracking.track_purchase."""
    try:
        conn = db_v2.get_conn()
        try:
            rec = reports_v2.read_report(conn, rid)
            if not rec or rec.get("product") != mp.PRODUCT or not rec.get("paid"):
                return False
            if _is_free_pass(conn, rid) or mp.is_demo_unlock(rec.get("payload")):
                return False                            # a pass or a demo unlock is not a sale
        finally:
            conn.close()
        meta = (rec.get("payload") or {}).get("meta") or {}
        tracking.track_purchase(
            mp.numerology_event_id(rid), mp.MULANK_PRICE_PAISE / 100, mp.MULANK_CURRENCY,
            phone=rec.get("user_phone") or None, email=None,
            fbc=meta.get("_fbc"), fbp=meta.get("_fbp"),
            client_user_agent=meta.get("_ua"), client_ip_address=meta.get("_ip"),
            li_fat_id=meta.get("_li_fat_id"), twclid=meta.get("_twclid"),
            source_url=source_url())
        return True
    except Exception as e:                      # a tracking problem must never touch the customer's report
        logger.error("[mulank] server purchase not sent: %s", e.__class__.__name__)
        return False
