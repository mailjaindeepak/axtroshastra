"""Local-only unlock of a Numerology report through /api/_demo_pay/{report_id}, the same way every other product is unlocked in development and in tests.

Reachable ONLY when DEMO_MODE is on: api.py registers /api/_demo_pay only then, demo_guard.py forces DEMO_MODE off on anything that looks like production,
and this module is imported only by that route. mulank_payment.py and mulank_routes.py still never read DEMO_MODE.

What it does and does not do:
  * the same eligibility rule as a real purchase: an incomplete pair cannot be unlocked (409), an unknown or non-Numerology id is a 404;
  * no payment row, like the other products' demo pay, so dashboards never count it (they only count a genuine pay_... id);
  * the report is marked with meta.demo_unlock so that no server Purchase is sent to any ad platform and no WhatsApp message goes to the number on it.
"""
import json
from datetime import datetime, timezone

from fastapi import HTTPException

import db_v2
import mulank_payment as mp

def unlock(conn, rid: str) -> dict:
    rec = mp._mulank_report(conn, rid or "")
    if not rec:
        raise HTTPException(404, "report not found")
    if rec["paid"]:
        return {"ok": True, "already_paid": True}
    ready = mp.readiness_for(rec)
    if not ready["eligible"]:
        raise HTTPException(409, "not_available")
    data = (db_v2.get_report(conn, rid) or {}).get("report_data") or {}
    data.setdefault("meta", {})[mp.DEMO_UNLOCK_KEY] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with conn.cursor() as cur:
        cur.execute("UPDATE reports SET report_data=%s WHERE id=%s", (json.dumps(data), rid))
    db_v2.set_report_paid(conn, rid)
    conn.commit()
    return {"ok": True}
