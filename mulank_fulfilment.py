"""Fulfilment of a PAID Mulank report: render the report, cache the PDF, and record where it stands.

Entitlement is the report's paid status (set only by the verified payment flow). Everything here is
idempotent and safe to repeat: the PDF cache is keyed by the report id, a retry never charges anyone,
and no step sends a WhatsApp message. State lives in report_data.meta.fulfilment and holds no personal data.
"""
import json
import logging
from datetime import datetime, timezone

import db_v2
import mulank_payment as mp
import numerology_report
import reports_v2

logger = logging.getLogger("axtroshastra")
READY, PENDING, FAILED = "ready", "pending", "failed"


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_state(payload: dict) -> dict:
    return dict(((payload or {}).get("meta") or {}).get("fulfilment") or {"status": PENDING, "attempts": 0})


def _record(conn, rid: str, status: str, error: str = "") -> dict:
    rec = db_v2.get_report(conn, rid)
    data = (rec or {}).get("report_data") or {}
    state = dict((data.get("meta") or {}).get("fulfilment") or {"attempts": 0})
    attempts = int(state.get("attempts") or 0)
    if not (status == READY and state.get("status") == READY):
        attempts += 1
    state.update(status=status, last_error=error, updated=_now(), attempts=attempts)
    data.setdefault("meta", {})["fulfilment"] = state
    with conn.cursor() as cur:
        cur.execute("UPDATE reports SET report_data=%s WHERE id=%s", (json.dumps(data), rid))
    conn.commit()
    return state


def render(rec: dict):
    """Production render for a stored Mulank report (raises ReportNotAvailable / ContentMissing)."""
    p = rec["payload"]
    y, m, d = (int(x) for x in p["dob"].split("-"))
    return numerology_report.build_report(d, m, y, p.get("name") or "")


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
            return _record(conn, rid, READY)
        try:
            html = render(rec)["html"]
        except (numerology_report.ReportNotAvailable, numerology_report.ContentMissing) as e:
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
        return _record(conn, rid, READY)
    finally:
        conn.close()


def schedule(rid: str, background) -> None:
    """Called once per paid report by the payment flow. Runs after the response; failures are recorded, not raised."""
    logger.info("[mulank] paid, starting fulfilment")
    if background is not None:
        background.add_task(run_fulfilment, rid)
    else:
        run_fulfilment(rid)
