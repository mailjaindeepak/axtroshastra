"""reports_v2.py — bridge the app's legacy "report dict" shape to the v2 tables.

Kept as its own module (not inside api.py) so it imports with NO side effects
(no .env/RDS load, no DB connect the way importing api.py does) and can be
unit-tested in isolation. api.py's get_report() + the report-creating routes call
these. Write functions take an OPEN connection and DO NOT commit — the caller owns
the transaction (matches db_v2 / flows_v2).
"""
import json

import db_v2
from flows_v2 import split_phone, clean_email


def _b2n(v):
    """Blank -> None, so empty form fields don't hit NOT-NULL/ENUM columns as ''."""
    if v is None:
        return None
    if isinstance(v, str) and not v.strip():
        return None
    return v


def norm_lang(report: dict) -> str:
    """v1 stored meta.lang as 'english'/'hi' (create_kundli) — milan already uses
    'en'/'hi'. v2's lang column is ENUM('en','hi'): map anything not 'hi' to 'en'."""
    lang = ((report or {}).get("meta") or {}).get("lang")
    return "hi" if lang == "hi" else "en"


def save_report(conn, rid: str, report: dict, subjects: list[dict], *,
                product: str, phone: str | None = None) -> str | None:
    """Write a legacy `report` dict into the v2 tables under id `rid`.

    Creates the user (the LEAD) when a phone is supplied, else user_id stays NULL
    (attached later at payment). The WHOLE report dict is stored as report_data so
    nothing (attribution cookies, _email, teaser, chart) is lost — v2 only ADDS
    structured columns on top. `subjects` is a list of dicts (role in
    {'self','partner'}). Caller commits. Returns the user_id, or None.
    """
    user_id = None
    if phone:
        cc, mobile = split_phone(phone)
        if mobile:
            email = clean_email(((report.get("meta") or {}).get("_email")))
            user_id = db_v2.create_or_get_user(conn, cc, mobile, email=email)

    variant = _b2n(((report.get("meta") or {}).get("variant")))
    db_v2.create_report(conn, user_id, product, report,
                        lang=norm_lang(report), variant=variant,
                        status="preview", report_id=rid)
    for s in subjects:
        db_v2.add_subject(
            conn, rid, s.get("role", "self"),
            name=_b2n(s.get("name")), gender=_b2n(s.get("gender")),
            dob=_b2n(s.get("dob")), tob=_b2n(s.get("tob")),
            time_quality=_b2n(s.get("time_quality")),
            birth_place=_b2n(s.get("birth_place")),
            birth_lat=s.get("birth_lat"), birth_lon=s.get("birth_lon"),
            birth_tz=s.get("birth_tz"))
    return user_id


def attach_user(conn, rid: str, phone: str | None, email: str | None = None) -> str:
    """Attach the popup contact to a report: create/find the user by phone and set
    reports.user_id (the anonymous lead becomes an identified account here). Returns
    the reassembled full number ('+CC' + mobile), or '' if no valid phone. Caller
    commits. Repeat calls are safe — the user is deduped by (country_code, mobile)."""
    cc, mobile = split_phone(phone or "")
    if not mobile:
        return ""
    user_id = db_v2.create_or_get_user(conn, cc, mobile, email=clean_email(email))
    with conn.cursor() as cur:
        cur.execute("UPDATE reports SET user_id=%s WHERE id=%s", (user_id, rid))
    return f"{cc}{mobile}"


def store_attribution(conn, rid: str, *, fbc=None, fbp=None, ua=None, ip=None,
                      li_fat_id=None) -> None:
    """Persist ad-click attribution + request context INTO the report body (report_data
    .meta), so the server-side CAPI purchase can forward them. v2 has no dedicated
    columns for these — they live in the JSON body exactly as v1's meta._fbc/_fbp/
    _ua/_ip/_li_fat_id did. Read-modify-write; only non-empty values are set. Caller
    commits."""
    vals = {"_fbc": (fbc or "").strip(), "_fbp": (fbp or "").strip(),
            "_ua": (ua or "").strip(), "_ip": (ip or "").strip(),
            "_li_fat_id": (li_fat_id or "").strip()}
    vals = {k: v for k, v in vals.items() if v}
    if not vals:
        return
    rec = db_v2.get_report(conn, rid)
    if not rec:
        return
    data = rec.get("report_data") or {}
    data.setdefault("meta", {}).update(vals)
    with conn.cursor() as cur:
        cur.execute("UPDATE reports SET report_data=%s WHERE id=%s",
                    (json.dumps(data), rid))


def read_report(conn, rid: str):
    """v2 read reshaped into the exact bundle the legacy api.get_report() returned:
    {payload, paid, order_id, phone, user_phone} — so its ~12 callers are unchanged.

    order_id + phone come from the latest payment (Razorpay's order id + the phone
    used AT payment); user_phone is the report owner's own mobile (the account /
    delivery number). All default to "" when there's no payment / no user yet.
    Returns None if the report doesn't exist.
    """
    rec = db_v2.get_report(conn, rid)
    if not rec:
        return None
    order_id = phone = user_phone = ""
    with conn.cursor() as cur:
        cur.execute("SELECT razorpay_order_id, payment_contact FROM payments "
                    "WHERE report_id=%s ORDER BY created_at DESC LIMIT 1", (rid,))
        prow = cur.fetchone()
        if prow:
            order_id = prow[0] or ""
            phone = prow[1] or ""
        if rec.get("user_id"):
            cur.execute("SELECT country_code, mobile FROM users WHERE id=%s",
                        (rec["user_id"],))
            urow = cur.fetchone()
            if urow:
                user_phone = f"{urow[0] or ''}{urow[1] or ''}"
    return {"payload": rec.get("report_data") or {},
            "paid": rec.get("status") == "paid",
            "order_id": order_id, "phone": phone, "user_phone": user_phone}
