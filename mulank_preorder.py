"""Pre-order mode for Mulank reports whose content is not complete yet. OFF unless the owner supplies ALL of:

  MULANK_PREORDER=1            the switch
  MULANK_DELIVERY_PROMISE      the exact delivery wording, a phrase that finishes "we will deliver it ...",
                               e.g. "within 7 days of your order". Never invented here.
  MULANK_REFUND_URL            the owner-approved refund and cancellation page (site path or https URL)

A pre-order is a normal verified Rs 299 payment (same amount, currency, order, captured checks) recorded against the
report, but it never unlocks anything: the paid report page renders only when the report is approved AND complete,
exactly as for any other order. The promise and refund link shown at purchase are snapshotted on the report.
"""
import hashlib
import json
import os
import re
from datetime import datetime, timezone

import db_v2


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def config() -> dict:
    """Read at call time. `enabled` is true only when every required value is present and safe."""
    on = os.getenv("MULANK_PREORDER", "") == "1"
    promise = re.sub(r"\s+", " ", os.getenv("MULANK_DELIVERY_PROMISE", "") or "").strip()
    refund = (os.getenv("MULANK_REFUND_URL", "") or "").strip()
    safe_refund = refund.startswith("https://") or (refund.startswith("/") and not refund.startswith("//"))
    ok = bool(on and 8 <= len(promise) <= 160 and not re.search(r"[<>]|instant", promise, re.I) and safe_refund)
    return {"enabled": ok, "promise": promise if ok else "", "refund_url": refund if ok else "",
            "version": hashlib.sha1((promise + "|" + refund).encode()).hexdigest()[:8] if ok else ""}


def get(payload: dict):
    """The pre-order snapshot stored on a report, or None."""
    return ((payload or {}).get("meta") or {}).get("preorder")


def record(conn, rid: str, cfg: dict) -> None:
    """Snapshot what the customer was promised at purchase time. Set once; caller commits."""
    rec = db_v2.get_report(conn, rid)
    data = (rec or {}).get("report_data") or {}
    meta = data.setdefault("meta", {})
    if meta.get("preorder"):
        return
    meta["preorder"] = {"at": _now(), "promise": cfg["promise"], "refund_url": cfg["refund_url"], "version": cfg["version"]}
    with conn.cursor() as cur:
        cur.execute("UPDATE reports SET report_data=%s WHERE id=%s", (json.dumps(data), rid))
