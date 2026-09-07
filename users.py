"""
users.py — account layer (MIGRATED to the v2 MySQL-native schema, Piece 5 / 5c).

One `users` row per (country_code, mobile). The account is created at form-fill /
order (the lead) and at OTP login; reports link back via reports.user_id, so a
logged-in user sees everything they've bought.

The public functions KEEP their signatures — including the leading `db` argument —
so the ~15 call sites in api.py / auth.py are unchanged across the cutover. That
`db` argument is now VESTIGIAL and ignored: each function opens its own v2
connection via db_v2 (which reads DB_HOST/.../DB_NAME). The vestigial param is
removed in 5d along with the other dead v1 code.

`_column_exists` / `_ensure_report_columns` / `ensure_tables` below are the LAST v1
(dbcompat) remnants, kept only until 5c-2 removes the module-load ensure_tables
calls in api.py. They never run against v2 (its schema is provisioned by
schema_v2.sql); do not add new callers.
"""
import json
import os
import sys

import dbcompat   # only for the soon-to-be-removed v1 ensure_tables / _column_exists
# db/ holds the v2 modules; make this import-order-independent (api imports `users`
# before it adds db/ to sys.path). Idempotent — the same dir may already be present.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "db"))
import db_v2      # noqa: E402
import flows_v2   # noqa: E402


def _norm_mobile(mobile: str) -> str:
    """Normalise to a stable key / msisdn. Razorpay `contact` for Indian numbers
    usually arrives as '+919812345678' but can be bare 10 digits or contain
    spaces/dashes. Keep an already-international '+' number as-is; otherwise take
    the last 10 digits and prefix +91 (mirrors send_whatsapp_report in api.py)."""
    if not mobile:
        return ""
    m = mobile.strip().replace(" ", "").replace("-", "")
    if m.startswith("+"):
        return m
    digits = "".join(ch for ch in m if ch.isdigit())
    if len(digits) >= 10:
        return "+91" + digits[-10:]
    return m


# --------------------------------------------------------------------------- #
# write path
# --------------------------------------------------------------------------- #
def upsert_user_from_payment(db, mobile: str, email: str = "", name: str = ""):
    """Create-or-fetch the user for this mobile and return their opaque id (or None).
    v2: deduped by UNIQUE(country_code, mobile) via create_or_get_user. `name` is
    intentionally NOT auto-set (a milan report's name is a couple, wrong for a
    person's account) — the user edits it on /account. `db` is vestigial."""
    cc, national = flows_v2.split_phone(_norm_mobile(mobile))
    if not national:
        return None
    conn = db_v2.get_conn()
    try:
        uid = db_v2.create_or_get_user(conn, cc, national,
                                       email=flows_v2.clean_email(email))
        conn.commit()
        return uid
    finally:
        conn.close()


def set_user_name(db, user_id: str, name: str) -> bool:
    """User-editable account name. Trims + caps length; an empty name clears it."""
    if not user_id:
        return False
    name = (name or "").strip()[:80]
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET name=%s WHERE id=%s", (name or None, user_id))
        conn.commit()
    finally:
        conn.close()
    return True


def link_report(db, rid: str, user_id: str):
    """Point a report at its owner. No-op if either id is missing."""
    if not (rid and user_id):
        return
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE reports SET user_id=%s WHERE id=%s", (user_id, rid))
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# read path
# --------------------------------------------------------------------------- #
def get_user(db, user_id: str):
    if not user_id:
        return None
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, country_code, mobile, email, name, created_at "
                        "FROM users WHERE id=%s", (user_id,))
            row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        return None
    # `mobile` is reassembled to the full +CC number (the shape v1 returned); v2
    # has no `city` column, so it's always None now. `created_at` is stringified
    # because MySQL hands back a datetime and this dict is JSON-dumped raw by the
    # cookie-setting auth routes (raw JSONResponse, no jsonable_encoder).
    created = row[5]
    return {"id": row[0], "mobile": f"{row[1] or ''}{row[2] or ''}", "email": row[3],
            "name": row[4], "city": None,
            "created_at": created.isoformat() if hasattr(created, "isoformat") else created}


def get_user_reports(db, user_id: str, limit: int = 100):
    """Every PAID report owned by this user, newest first, as light dicts for the
    account dashboard. Product + a display name are pulled out of report_data so
    the page needs no second lookup."""
    if not user_id:
        return []
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, report_data, created_at FROM reports "
                        "WHERE user_id=%s AND status='paid' "
                        "ORDER BY created_at DESC LIMIT %s", (user_id, limit))
            rows = cur.fetchall()
    finally:
        conn.close()
    out = []
    for rid, report_data, created_at in rows:
        product, subject = "marriage", ""
        try:
            data = json.loads(report_data) if report_data else {}
            meta = data.get("meta") or {}
            product = data.get("product") or meta.get("product") or "marriage"
            subject = meta.get("name") or meta.get("p1") or ""
        except Exception:
            pass
        out.append({"id": rid, "product": product, "subject": subject,
                    "created_at": (created_at.isoformat()
                                   if hasattr(created_at, "isoformat") else created_at)})
    return out


def get_user_for_report(db, rid: str):
    """The account linked to a report, or None. Used by the report page + API to
    show 'account saved' with the saved mobile/email."""
    if not rid:
        return None
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM reports WHERE id=%s", (rid,))
            row = cur.fetchone()
    finally:
        conn.close()
    if not row or not row[0]:
        return None
    return get_user(db, row[0])


def backfill(db, limit: int = 5000) -> dict:
    """Obsolete under v2: users are attached at form-fill / order (the lead) and at
    OTP login, so there are no paid-but-unlinked reports to sweep. Kept as a no-op
    so the admin route still responds."""
    return {"scanned": 0, "linked": 0, "note": "obsolete in v2 (users attach at order)"}


# --------------------------------------------------------------------------- #
# v1 remnants — REMOVED in 5c-2/5d with the module-load ensure_tables calls.
# Kept only so `import api` still boots between 5c-1 and 5c-2. Never run on v2.
# --------------------------------------------------------------------------- #
def _column_exists(c, table: str, column: str) -> bool:
    if dbcompat.using_mysql():
        row = c.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema=DATABASE() AND table_name=? AND column_name=?",
            (table, column)).fetchone()
        return row is not None
    rows = c.execute("PRAGMA table_info(%s)" % table).fetchall()
    return any(r[1] == column for r in rows)


def _ensure_report_columns(c):
    for col in ("user_id", "user_phone"):
        if not _column_exists(c, "reports", col):
            c.execute("ALTER TABLE reports ADD COLUMN %s TEXT" % col)
    if not _column_exists(c, "reports", "amount_paise"):
        c.execute("ALTER TABLE reports ADD COLUMN amount_paise INTEGER")


def ensure_tables(db):
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            id TEXT PRIMARY KEY,
            mobile TEXT, email TEXT, name TEXT, city TEXT,
            mobile_verified INTEGER DEFAULT 0,
            email_verified INTEGER DEFAULT 0,
            status TEXT, created_at TEXT, updated_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS user_mobiles(
            mobile TEXT PRIMARY KEY, user_id TEXT, created_at TEXT)""")
        _ensure_report_columns(c)
