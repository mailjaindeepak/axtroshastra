"""Fulfilment of a PAID Mulank report: render the report, cache the PDF, and record where it stands.

Entitlement is the report's paid status (set only by the verified payment flow). Everything here is
idempotent and safe to repeat: the PDF cache is keyed by the report id, a retry never charges anyone,
and the customer's WhatsApp number gets one message with the report link the first time the report is ready (only when Twilio and the approved text template are configured). State lives in report_data.meta.fulfilment and holds no personal data.
"""
import json
import logging
from datetime import date, datetime, timezone

import db_v2
import mulank_content
import mulank_payment as mp
import mulank_preorder
import mulank_tracking
import numerology_report
import reports_v2

logger = logging.getLogger("axtroshastra")
READY, PENDING, FAILED = "ready", "pending", "failed"
AWAITING = "awaiting_content"          # a pre-order whose report cannot be produced yet (content not approved and complete)


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_state(payload: dict) -> dict:
    return dict(((payload or {}).get("meta") or {}).get("fulfilment") or {"status": PENDING, "attempts": 0})


def _record(conn, rid: str, status: str, error: str = "", **extra) -> dict:
    rec = db_v2.get_report(conn, rid)
    data = (rec or {}).get("report_data") or {}
    state = dict((data.get("meta") or {}).get("fulfilment") or {"attempts": 0})
    attempts = int(state.get("attempts") or 0)
    if not (status == READY and state.get("status") == READY):
        attempts += 1
    state.update(status=status, last_error=error, updated=_now(), attempts=attempts, **extra)
    data.setdefault("meta", {})["fulfilment"] = state
    with conn.cursor() as cur:
        cur.execute("UPDATE reports SET report_data=%s WHERE id=%s", (json.dumps(data), rid))
    conn.commit()
    return state


def prepared_on(payload: dict):
    """The date the report was first fulfilled. Once set, every render (web page and PDF) uses it, so a delivered
    report never changes later (personal years and the "prepared" date stay as delivered)."""
    raw = get_state(payload).get("prepared_on")
    try:
        return date.fromisoformat(raw) if raw else None
    except (TypeError, ValueError):
        return None


def render(rec: dict, today=None):
    """Production render for a stored Mulank report (raises ReportNotAvailable / ContentMissing)."""
    p = rec["payload"]
    y, m, d = (int(x) for x in p["dob"].split("-"))
    return numerology_report.build_report(d, m, y, p.get("name") or "", today=today or prepared_on(p))


def _send_wa(phone: str, name: str, link: str) -> None:
    """One WhatsApp message through the approved TEXT template ({{1}} name, {{2}} report link). The shared media template points at another
    product's PDF path, so it is deliberately not used here: the PDF is one tap away on the report page."""
    import api
    from twilio.rest import Client
    to = phone if phone.startswith("+") else "+91" + phone[-10:]
    Client(api.TWILIO_SID, api.TWILIO_TOKEN).messages.create(
        from_=api.TWILIO_FROM, to=f"whatsapp:{to}", content_sid=api.TWILIO_CONTENT_SID_TEXT,
        content_variables=json.dumps({"1": name, "2": link}))


def _ready(conn, rid: str, rec: dict, prepared: str) -> dict:
    """Record READY, then (once, and only when delivery is configured) tell the customer on WhatsApp. A failed send never affects the report."""
    state = _record(conn, rid, READY, prepared_on=prepared)
    if state.get("wa") or mp.is_demo_unlock(rec.get("payload")):      # a demo unlock never messages the number on the report
        return state
    import api
    if not (api.TWILIO_SID and api.TWILIO_TOKEN and api.TWILIO_FROM and api.TWILIO_CONTENT_SID_TEXT and api.PUBLIC_BASE_URL and rec.get("user_phone")):
        return state
    try:
        _send_wa(rec["user_phone"], (rec["payload"].get("name") or "").strip() or "there", f"{api.PUBLIC_BASE_URL}/en/numerology/report/{rid}")
    except Exception as e:
        logger.error("[mulank] whatsapp delivery failed: %s", e.__class__.__name__)
        return state
    return _record(conn, rid, READY, wa=_now())


def run_fulfilment(rid: str) -> dict:
    """Generate (or confirm) the PDF for a paid report and record the outcome. Never raises, never charges,
    safe to call any number of times. Returns the recorded state."""
    import pdfgen
    conn = db_v2.get_conn()
    try:
        rec = reports_v2.read_report(conn, rid)
        if not rec or rec.get("product") != mp.PRODUCT or not rec["paid"]:
            return {"status": "not_paid"}
        if pdfgen.get_cached(rid):
            return _ready(conn, rid, rec, (prepared_on(rec["payload"]) or mulank_content._today()).isoformat())
        freeze = prepared_on(rec["payload"]) or mulank_content._today()
        try:
            html = render(rec, freeze)["html"]
        except (numerology_report.ReportNotAvailable, numerology_report.ContentMissing) as e:
            if mulank_preorder.get(rec["payload"]):
                return _record(conn, rid, AWAITING, "content_not_ready")      # expected for a pre-order; not an error
            logger.error("[mulank] paid report cannot be rendered (content): %s", e.__class__.__name__)
            return _record(conn, rid, FAILED, "content_unavailable")
        except Exception as e:
            logger.error("[mulank] paid report render failed: %s", e.__class__.__name__)
            return _record(conn, rid, FAILED, "render_failed")
        data = None
        try:
            data = pdfgen.get_or_generate(rid, html)
        except Exception as e:
            logger.error("[mulank] pdf generation failed: %s", e.__class__.__name__)
        if not data:
            return _record(conn, rid, FAILED, "pdf_unavailable")
        return _ready(conn, rid, rec, freeze.isoformat())
    finally:
        conn.close()


def schedule(rid: str, background) -> None:
    """Called once per paid report by the payment flow. Runs after the response; failures are recorded, not raised."""
    logger.info("[mulank] paid, starting fulfilment")
    if background is not None:
        background.add_task(run_fulfilment, rid)
        background.add_task(mulank_tracking.run, rid)      # server Purchase; once per paid report, same path as fulfilment
    else:
        run_fulfilment(rid)
        mulank_tracking.run(rid)
