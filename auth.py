"""
auth.py — OTP login + session layer.

The *account* half already exists in users.py (a `users` row per mobile, created
at payment time, with reports linked via reports.user_id). This module adds the
*auth* half so a user can prove they own a mobile and then see everything on that
account:

  request-otp  ->  send a 6-digit code to the mobile
  verify-otp   ->  check the code, upsert the user, mint a session
  session      ->  opaque token in an httpOnly cookie, backed by a `sessions` row

OTP delivery uses **Twilio Verify** (channel configurable, default WhatsApp) so we
reuse the Twilio credentials already wired for report delivery and let Twilio own
the message templates — the only same-day-launchable path for India, since our own
SMS/WhatsApp templates would need DLT / template approval first.

When Twilio Verify is NOT configured (local dev), we fall back to a self-managed
code stored in `login_otps` and logged to the console, so the whole flow is
testable without Twilio. That path is dev-only and never used once
TWILIO_VERIFY_SERVICE_SID is set.

All SQL is SQLite dialect, auto-translated to MySQL by dbcompat (same constraints
as users.py: opaque token PKs, no AUTOINCREMENT, status set on INSERT). Storage
goes through the app's `db()` connection factory, passed in from api.py.
"""
import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta

import dbcompat
import users

logger = logging.getLogger("axtroshastra.auth")

# --------------------------------------------------------------------------- #
# config (all read at call time so tests / dashboards can set env late)
# --------------------------------------------------------------------------- #
SESSION_COOKIE = "axs_session"
SESSION_TTL_DAYS = 30
OTP_TTL_MINUTES = 10
OTP_MAX_ATTEMPTS = 5


def _twilio_verify_sid() -> str:
    return os.getenv("TWILIO_VERIFY_SERVICE_SID", "")


def _verify_channel() -> str:
    # 'whatsapp' (default, launch-today) | 'sms' (needs DLT) | 'call' | 'email'
    return os.getenv("TWILIO_VERIFY_CHANNEL", "whatsapp").strip().lower() or "whatsapp"


def _demo_mode() -> bool:
    return os.getenv("DEMO_MODE") == "1"


def cookie_secure() -> bool:
    """Only mark the session cookie Secure when we're actually served over https,
    otherwise the cookie would be dropped on a plain-http local dev server."""
    return os.getenv("PUBLIC_BASE_URL", "").startswith("https")


# --------------------------------------------------------------------------- #
# schema
# --------------------------------------------------------------------------- #
def ensure_tables(db):
    """Create the auth tables. Safe to call on every boot. `users.ensure_tables`
    should have run first (this module upserts into it)."""
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS sessions(
            token TEXT PRIMARY KEY, user_id TEXT, mobile TEXT,
            created_at TEXT, expires_at TEXT)""")
        # dev-fallback OTP store (unused when Twilio Verify is configured).
        # PK is the mobile so a fresh request overwrites any pending code.
        c.execute("""CREATE TABLE IF NOT EXISTS login_otps(
            mobile TEXT PRIMARY KEY, code_hash TEXT,
            expires_at TEXT, attempts INTEGER)""")


# --------------------------------------------------------------------------- #
# OTP send / check
# --------------------------------------------------------------------------- #
def _norm(mobile: str) -> str:
    return users._norm_mobile(mobile)


def _hash_code(mobile: str, code: str) -> str:
    return hashlib.sha256(f"{mobile}:{code}".encode()).hexdigest()


def _twilio_client():
    sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    tok = os.getenv("TWILIO_AUTH_TOKEN", "")
    if not (sid and tok):
        return None
    from twilio.rest import Client
    return Client(sid, tok)


def send_otp(db, mobile: str) -> dict:
    """Send an OTP to `mobile`. Returns {'ok': bool, 'channel': str, 'dev_code': str?}.
    Never raises to the caller for a delivery failure — returns ok=False instead."""
    mobile = _norm(mobile)
    if not mobile or len(mobile) < 8:
        return {"ok": False, "error": "invalid_mobile"}

    sid = _twilio_verify_sid()
    if sid:
        # --- production: Twilio Verify owns code generation, storage, expiry ---
        try:
            client = _twilio_client()
            if client is None:
                return {"ok": False, "error": "twilio_not_configured"}
            client.verify.v2.services(sid).verifications.create(
                to=mobile, channel=_verify_channel())
            return {"ok": True, "channel": _verify_channel()}
        except Exception as e:
            logger.error("[auth] Twilio Verify send failed for %s: %s", mobile, e)
            return {"ok": False, "error": "send_failed"}

    # --- dev fallback: self-managed code, logged (and echoed only in DEMO_MODE) ---
    code = f"{secrets.randbelow(1000000):06d}"
    expires = (datetime.utcnow() + timedelta(minutes=OTP_TTL_MINUTES)).isoformat()
    with db() as c:
        c.execute("DELETE FROM login_otps WHERE mobile=?", (mobile,))
        c.execute("INSERT INTO login_otps(mobile,code_hash,expires_at,attempts) "
                  "VALUES(?,?,?,0)", (mobile, _hash_code(mobile, code), expires))
    logger.warning("[auth][DEV] OTP for %s is %s (Twilio Verify not configured)",
                   mobile, code)
    out = {"ok": True, "channel": "dev"}
    if _demo_mode():
        out["dev_code"] = code          # surfaced to the UI only in DEMO_MODE
    return out


def check_otp(db, mobile: str, code: str) -> bool:
    """Verify `code` for `mobile`. True on success. Consumes the code either way
    (single-use) in the dev path; Twilio Verify enforces single-use itself."""
    mobile = _norm(mobile)
    code = (code or "").strip()
    if not (mobile and code.isdigit()):
        return False

    sid = _twilio_verify_sid()
    if sid:
        try:
            client = _twilio_client()
            if client is None:
                return False
            res = client.verify.v2.services(sid).verification_checks.create(
                to=mobile, code=code)
            return getattr(res, "status", "") == "approved"
        except Exception as e:
            logger.error("[auth] Twilio Verify check failed for %s: %s", mobile, e)
            return False

    # --- dev fallback ---
    with db() as c:
        row = c.execute("SELECT code_hash,expires_at,attempts FROM login_otps "
                        "WHERE mobile=?", (mobile,)).fetchone()
        if not row:
            return False
        code_hash, expires_at, attempts = row[0], row[1], (row[2] or 0)
        if attempts >= OTP_MAX_ATTEMPTS or expires_at < datetime.utcnow().isoformat():
            c.execute("DELETE FROM login_otps WHERE mobile=?", (mobile,))
            return False
        ok = hmac.compare_digest(code_hash, _hash_code(mobile, code))
        if ok:
            c.execute("DELETE FROM login_otps WHERE mobile=?", (mobile,))
        else:
            c.execute("UPDATE login_otps SET attempts=? WHERE mobile=?",
                      (attempts + 1, mobile))
        return ok


# --------------------------------------------------------------------------- #
# sessions
# --------------------------------------------------------------------------- #
def create_session(db, user_id: str, mobile: str) -> str:
    token = "s_" + secrets.token_urlsafe(24)
    now = datetime.utcnow()
    with db() as c:
        c.execute("INSERT INTO sessions(token,user_id,mobile,created_at,expires_at) "
                  "VALUES(?,?,?,?,?)",
                  (token, user_id, mobile, now.isoformat(),
                   (now + timedelta(days=SESSION_TTL_DAYS)).isoformat()))
    return token


def user_for_session(db, token: str):
    """Return the user dict for a valid, unexpired session token, else None."""
    if not token:
        return None
    with db() as c:
        row = c.execute("SELECT user_id,expires_at FROM sessions WHERE token=?",
                        (token,)).fetchone()
    if not row:
        return None
    user_id, expires_at = row[0], row[1]
    if expires_at and expires_at < datetime.utcnow().isoformat():
        destroy_session(db, token)
        return None
    return users.get_user(db, user_id)


def destroy_session(db, token: str):
    if not token:
        return
    with db() as c:
        c.execute("DELETE FROM sessions WHERE token=?", (token,))


# --------------------------------------------------------------------------- #
# login = verify + upsert account + session
# --------------------------------------------------------------------------- #
def login(db, mobile: str, code: str):
    """Full verify->account->session step. Returns (token, user) on success, or
    (None, None) on a bad/expired code. Logging in also creates the account row
    (idempotent) so a first-time visitor who never purchased still gets a home."""
    if not check_otp(db, mobile, code):
        return None, None
    uid = users.upsert_user_from_payment(db, mobile=_norm(mobile))
    if not uid:
        return None, None
    token = create_session(db, uid, _norm(mobile))
    return token, users.get_user(db, uid)
