"""
users.py — account layer.

One `users` row per person, keyed on mobile. The account is created AUTOMATICALLY
at payment time from the Razorpay payment entity (contact + email); there is no
separate signup. Reports link back to a user via `reports.user_id`, so a
logged-in user can later see everything they've bought.

The OTP login flow (login_otps / sessions tables + /api/auth routes) is
intentionally NOT here yet — it lands in a separate change. This module owns only:
the users table, the mobile-uniqueness map, the reports.user_id link, the
upsert-at-payment, and the lookups used to show a user their saved details.

Storage goes through the app's `db` connection factory (dbcompat), so all SQL is
written in SQLite dialect and auto-translated to MySQL on RDS. Constraints imposed
by that shim (why the schema looks the way it does):
  * no AUTOINCREMENT  -> we use opaque token primary keys, like `reports`/`passes`.
  * a plain TEXT column becomes LONGTEXT on MySQL, which cannot carry a UNIQUE
    index or a string DEFAULT -> mobile uniqueness is enforced by a mapping table
    whose PRIMARY KEY *is* the mobile (VARCHAR via the `TEXT PRIMARY KEY` rule),
    and `status` is set on INSERT rather than via a column DEFAULT.
"""
import json
import secrets
from datetime import datetime

import dbcompat


def _norm_mobile(mobile: str) -> str:
    """Normalise to a stable key. Razorpay `contact` for Indian numbers usually
    arrives as '+919812345678' but can be bare 10 digits or contain spaces/dashes.
    Keep an already-international '+' number as-is; otherwise take the last 10
    digits and prefix +91 (mirrors send_whatsapp_report in api.py)."""
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
# schema
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
    """Add reports.user_id / reports.user_phone once, idempotently, on either
    backend. A plain `TEXT` in an ALTER is left untranslated by dbcompat and is
    a valid column type on both SQLite and MySQL, so no CREATE-TABLE type
    mapping is needed here.

    user_phone is the number the buyer TYPED into the pre-payment contact popup
    (their WhatsApp/account number). It is distinct from reports.phone, which
    stays the contact Razorpay reported for the payment itself."""
    for col in ("user_id", "user_phone"):
        if not _column_exists(c, "reports", col):
            c.execute("ALTER TABLE reports ADD COLUMN %s TEXT" % col)
    if not _column_exists(c, "reports", "amount_paise"):
        c.execute("ALTER TABLE reports ADD COLUMN amount_paise INTEGER")


def ensure_tables(db):
    """Create the account tables and the reports.user_id link. Safe to call on
    every boot. `reports` is created by the app's db() factory before this runs,
    so the ALTER always has a table to target."""
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


# --------------------------------------------------------------------------- #
# write path (payment time)
# --------------------------------------------------------------------------- #
def upsert_user_from_payment(db, mobile: str, email: str = "", name: str = ""):
    """Create-or-fetch the user for this mobile and return their opaque id.

    Idempotent and worker-safe: the first writer to claim a mobile wins the
    `user_mobiles` PRIMARY KEY via INSERT-OR-IGNORE, so concurrent captures for
    the same number converge on one user row without relying on the app lock.
    Email/name are backfilled only when currently empty (never overwritten)."""
    mobile = _norm_mobile(mobile)
    if not mobile:
        return None
    email = (email or "").strip()
    name = (name or "").strip()
    now = datetime.utcnow().isoformat()
    candidate = "u_" + secrets.token_urlsafe(12)
    with db() as c:
        # Atomic claim: the mapping row's PK guarantees one user per mobile.
        c.execute("INSERT OR IGNORE INTO user_mobiles(mobile,user_id,created_at) "
                  "VALUES(?,?,?)", (mobile, candidate, now))
        row = c.execute("SELECT user_id FROM user_mobiles WHERE mobile=?",
                        (mobile,)).fetchone()
        uid = row[0] if row else candidate     # never subscript a None result
        # Create the user row on first sight (no-op if it already exists).
        c.execute("INSERT OR IGNORE INTO users"
                  "(id,mobile,email,name,status,created_at,updated_at) "
                  "VALUES(?,?,?,?,?,?,?)",
                  (uid, mobile, email, name, "active", now, now))
        # Fill in email/name if they were blank and we now have them.
        c.execute("UPDATE users SET "
                  "email=CASE WHEN (email IS NULL OR email='') THEN ? ELSE email END, "
                  "name=CASE WHEN (name IS NULL OR name='') THEN ? ELSE name END, "
                  "updated_at=? WHERE id=?",
                  (email, name, now, uid))
    return uid


def set_user_name(db, user_id: str, name: str) -> bool:
    """User-editable account name (there is no auto-set name at payment time —
    a milan report's name is a couple, wrong for a person's account). Trims and
    caps length; an empty name clears it back to blank. Returns True on write."""
    if not user_id:
        return False
    name = (name or "").strip()[:80]
    now = datetime.utcnow().isoformat()
    with db() as c:
        c.execute("UPDATE users SET name=?, updated_at=? WHERE id=?",
                  (name, now, user_id))
    return True


def link_report(db, rid: str, user_id: str):
    """Point a paid report at its owner. No-op if either id is missing."""
    if not (rid and user_id):
        return
    with db() as c:
        c.execute("UPDATE reports SET user_id=? WHERE id=?", (user_id, rid))


# --------------------------------------------------------------------------- #
# read path (show the user their saved details)
# --------------------------------------------------------------------------- #
def get_user(db, user_id: str):
    if not user_id:
        return None
    with db() as c:
        row = c.execute("SELECT id,mobile,email,name,city,created_at "
                        "FROM users WHERE id=?", (user_id,)).fetchone()
    if not row:
        return None
    return {"id": row[0], "mobile": row[1], "email": row[2],
            "name": row[3], "city": row[4], "created_at": row[5]}


def get_user_reports(db, user_id: str, limit: int = 100):
    """Every paid report owned by this user, newest first, as light dicts for the
    account dashboard. Product + a display name are pulled out of the stored
    payload so the page needs no second lookup."""
    if not user_id:
        return []
    with db() as c:
        rows = c.execute(
            "SELECT id, payload, created_at FROM reports "
            "WHERE user_id=? AND paid=1 ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)).fetchall()
    out = []
    for rid, payload, created_at in rows:
        product, subject = "marriage", ""
        try:
            data = json.loads(payload) if payload else {}
            meta = data.get("meta") or {}
            product = data.get("product") or meta.get("product") or "marriage"
            subject = meta.get("name") or meta.get("p1") or ""
        except Exception:
            pass
        out.append({"id": rid, "product": product, "subject": subject,
                    "created_at": created_at})
    return out


def get_user_for_report(db, rid: str):
    """The account linked to a report, or None. Used by the report page + API to
    show 'aapka account save ho gaya' with the saved mobile/email."""
    if not rid:
        return None
    with db() as c:
        row = c.execute("SELECT user_id FROM reports WHERE id=?", (rid,)).fetchone()
    if not row or not row[0]:
        return None
    return get_user(db, row[0])


# --------------------------------------------------------------------------- #
# one-time backfill
# --------------------------------------------------------------------------- #
def backfill(db, limit: int = 5000) -> dict:
    """Create + link accounts for reports that were already paid before the
    accounts code existed (or were rescued by reconcile with the old code):
    paid=1, a phone on file, but no linked user. Idempotent — the mobile map
    de-dupes, so re-running only picks up rows still missing a user. Mobile is
    the anchor; email/name are pulled from the report payload when present."""
    with db() as c:
        rows = c.execute(
            "SELECT id, phone, payload FROM reports "
            "WHERE paid=1 AND (user_id IS NULL OR user_id='') "
            "AND phone IS NOT NULL AND phone<>'' LIMIT ?", (limit,)).fetchall()
    linked = 0
    for rid, phone, payload in rows:
        email, name = "", ""
        try:
            meta = (json.loads(payload) if payload else {}).get("meta") or {}
            email = meta.get("_email") or ""
            name = meta.get("name") or ""
        except Exception:
            pass
        uid = upsert_user_from_payment(db, mobile=phone, email=email, name=name)
        if uid:
            link_report(db, rid, uid)
            linked += 1
    return {"scanned": len(rows), "linked": linked}
