"""
auth.py — OTP login + session layer.

The *account* half already exists in users.py (a `users` row per mobile, created
at payment time, with reports linked via reports.user_id). This module adds the
*auth* half so a user can prove they own a mobile and then see everything on that
account:

  request-otp  ->  send a 6-digit code to the mobile
  verify-otp   ->  check the code, upsert the user, mint a session
  session      ->  opaque token in an httpOnly cookie, backed by a `sessions` row

OTP delivery is provider-pluggable via `OTP_PROVIDER` (auto-detected when unset):

  * ``messagecentral`` — Message Central Verify Now (SMS). Selected automatically
    when MESSAGECENTRAL_CUSTOMER_ID is set. Message Central owns code generation,
    delivery and expiry; unlike Twilio it keys a verification by a `verificationId`
    returned from *send* that must be replayed to *validate*, so we stash that id in
    `login_otps` (column ``mc_verification_id``) between the two requests.
  * ``twilio`` — Twilio Verify (channel configurable, default WhatsApp), reusing the
    Twilio credentials already wired for report delivery.
  * ``dev`` — self-managed 6-digit code stored in `login_otps` and logged to the
    console, so the whole flow is testable locally without any provider. Used when
    neither provider is configured; never used once a provider is set.

All provider HTTP is stdlib ``urllib`` (no SDK), so nothing needs adding to the
offline wheelhouse in ``packages/``.

Storage is MySQL-native via db_v2 (Piece 5 / 5c): OTP codes live in `login_otps`
(keyed by `msisdn`) and sessions in `login_sessions`. The `db` argument on the
public functions is VESTIGIAL — kept for call-site compatibility, ignored inside
(each opens its own v2 connection); it's removed in 5d.
"""
import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

import sys
# db/ holds the v2 modules; api imports `auth` before it adds db/ to sys.path, so
# make this import-order-independent (idempotent). Piece 5 / 5c: MySQL-native auth.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "db"))
import db_v2   # noqa: E402
import users   # noqa: E402

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


def _otp_provider() -> str:
    """Which OTP backend to use. Honour an explicit OTP_PROVIDER, else auto-detect:
    Message Central if its customerId is set, then Twilio Verify, else the dev
    fallback."""
    p = os.getenv("OTP_PROVIDER", "").strip().lower()
    if p:
        return p
    if _mc_customer_id():
        return "messagecentral"
    if _twilio_verify_sid():
        return "twilio"
    return "dev"


# --- Message Central (Verify Now) config, all read at call time -------------- #
def _mc_base() -> str:
    return os.getenv(
        "MESSAGECENTRAL_BASE_URL", "https://cpaas.messagecentral.com").rstrip("/")


def _mc_customer_id() -> str:
    return os.getenv("MESSAGECENTRAL_CUSTOMER_ID", "").strip()


def _mc_password() -> str:
    return os.getenv("MESSAGECENTRAL_PASSWORD", "")


def _mc_email() -> str:
    return os.getenv("MESSAGECENTRAL_EMAIL", "").strip()


def _mc_country() -> str:
    # numeric dialling code (no '+'); India by default
    return os.getenv("MESSAGECENTRAL_COUNTRY_CODE", "91").strip() or "91"


def _mc_otp_length() -> str:
    return os.getenv("MESSAGECENTRAL_OTP_LENGTH", "6").strip() or "6"


def _mc_timeout() -> float:
    try:
        return float(os.getenv("MESSAGECENTRAL_TIMEOUT", "20"))
    except ValueError:
        return 20.0


def _demo_mode() -> bool:
    return os.getenv("DEMO_MODE") == "1"


def cookie_secure() -> bool:
    """Only mark the session cookie Secure when we're actually served over https,
    otherwise the cookie would be dropped on a plain-http local dev server."""
    return os.getenv("PUBLIC_BASE_URL", "").startswith("https")


# Schema note (Piece 5 / 5c): the v1 ensure_tables() is gone — the v2 login_otps
# (keyed by `msisdn`) and login_sessions tables are provisioned by db/schema_v2.sql.


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
    Never raises to the caller for a delivery failure — returns ok=False instead.
    Dispatches to the configured provider (Message Central / Twilio / dev)."""
    mobile = _norm(mobile)
    if not mobile or len(mobile) < 8:
        return {"ok": False, "error": "invalid_mobile"}

    provider = _otp_provider()
    if provider == "messagecentral":
        return _mc_send_otp(db, mobile)
    if provider == "twilio":
        return _twilio_send_otp(mobile)
    return _dev_send_otp(db, mobile)


def check_otp(db, mobile: str, code: str) -> bool:
    """Verify `code` for `mobile`. True on success. Consumes the code (single-use)
    on success. Dispatches to the same provider that sent it."""
    mobile = _norm(mobile)
    code = (code or "").strip()
    if not (mobile and code.isdigit()):
        return False

    provider = _otp_provider()
    if provider == "messagecentral":
        return _mc_check_otp(db, mobile, code)
    if provider == "twilio":
        return _twilio_check_otp(mobile, code)
    return _dev_check_otp(db, mobile, code)


# --------------------------------------------------------------------------- #
# provider readiness (health check — no SMS sent, no secrets returned)
# --------------------------------------------------------------------------- #
def provider_health() -> dict:
    """Non-secret readiness snapshot of the active OTP provider, safe to expose on
    an admin endpoint. For Message Central it actually mints (or reuses a cached)
    auth token — proving customerId + password/token are accepted — WITHOUT sending
    an OTP. Never returns the token, password, or any secret."""
    provider = _otp_provider()
    out = {"provider": provider, "ok": False}
    if provider == "messagecentral":
        out["customer_id_set"] = bool(_mc_customer_id())
        out["base_url"] = _mc_base()
        out["auth_mode"] = ("static_token"
                            if os.getenv("MESSAGECENTRAL_AUTH_TOKEN", "").strip()
                            else "password")
        out["country_code"] = _mc_country()
        out["otp_length"] = _mc_otp_length()
        token = _mc_auth_token()          # catches its own errors -> "" on failure
        out["ok"] = bool(token)
        if not token:
            out["error"] = "token_unavailable"  # creds missing or rejected (see logs)
        return out
    if provider == "twilio":
        out["channel"] = _verify_channel()
        out["ok"] = bool(_twilio_verify_sid() and _twilio_client() is not None)
        if not out["ok"]:
            out["error"] = "twilio_not_configured"
        return out
    out["ok"] = True
    out["note"] = "dev fallback — OTP codes are logged to the console, not sent"
    return out


# --------------------------------------------------------------------------- #
# provider: Message Central (Verify Now) — stdlib HTTP, no SDK
# --------------------------------------------------------------------------- #
# auth token is valid ~24h; cache it per-process to avoid a round-trip per OTP
_MC_TOKEN_CACHE = {"token": "", "exp": None}


def _mc_split(mobile: str):
    """Split a normalised '+<cc><national>' number into (countryCode, national)
    as Message Central wants them. Falls back to the configured country code and
    the last 10 digits when the prefix doesn't match (India-first; set
    MESSAGECENTRAL_COUNTRY_CODE for other single-country deployments)."""
    cc = _mc_country()
    digits = "".join(ch for ch in mobile if ch.isdigit())
    if digits.startswith(cc):
        return cc, digits[len(cc):]
    return cc, digits[-10:]


def _mc_request(method: str, url: str, headers: dict) -> dict:
    """GET/POST a Message Central endpoint and return the parsed JSON. Params ride
    in the query string (the API takes no request body). A 4xx/5xx whose body is
    JSON is returned as-is (so callers can read verificationStatus / responseCode);
    anything else propagates."""
    data = b"" if method == "POST" else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=_mc_timeout()) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            return json.loads(body)
        except ValueError:
            raise


def _mc_auth_token() -> str:
    """Return a Message Central auth token. Prefers a static MESSAGECENTRAL_AUTH_TOKEN
    if provided, else generates one from customerId + base64(password) and caches it."""
    static = os.getenv("MESSAGECENTRAL_AUTH_TOKEN", "").strip()
    if static:
        return static
    cid, pwd = _mc_customer_id(), _mc_password()
    if not (cid and pwd):
        return ""
    now = datetime.utcnow()
    if _MC_TOKEN_CACHE["token"] and _MC_TOKEN_CACHE["exp"] and _MC_TOKEN_CACHE["exp"] > now:
        return _MC_TOKEN_CACHE["token"]
    params = urllib.parse.urlencode({
        "customerId": cid,
        "key": base64.b64encode(pwd.encode()).decode(),
        "scope": "NEW",
        "country": _mc_country(),
        "email": _mc_email(),
    })
    url = f"{_mc_base()}/auth/v1/authentication/token?{params}"
    try:
        resp = _mc_request("GET", url, {"accept": "application/json"})
    except Exception as e:
        logger.error("[auth] MessageCentral token request failed: %s", e)
        return ""
    token = str(resp.get("token") or "")
    if token:
        _MC_TOKEN_CACHE["token"] = token
        _MC_TOKEN_CACHE["exp"] = now + timedelta(hours=23)
    else:
        logger.error("[auth] MessageCentral token response had no token: %s", resp)
    return token


def _mc_send_otp(db, mobile: str) -> dict:
    token = _mc_auth_token()
    if not token:
        return {"ok": False, "error": "messagecentral_not_configured"}
    cc, national = _mc_split(mobile)
    params = urllib.parse.urlencode({
        "countryCode": cc,
        "customerId": _mc_customer_id(),
        "flowType": "SMS",
        "mobileNumber": national,
        "otpLength": _mc_otp_length(),
    })
    url = f"{_mc_base()}/verification/v3/send?{params}"
    try:
        resp = _mc_request("POST", url, {"authToken": token})
    except Exception as e:
        logger.error("[auth] MessageCentral send failed for %s: %s", mobile, e)
        return {"ok": False, "error": "send_failed"}
    vid = str((resp.get("data") or {}).get("verificationId") or "")
    if not vid:
        logger.error("[auth] MessageCentral send returned no verificationId: %s", resp)
        return {"ok": False, "error": "send_failed"}
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM login_otps WHERE msisdn=%s", (mobile,))
            cur.execute("INSERT INTO login_otps(msisdn, code_hash, mc_verification_id, "
                        "expires_at, attempts) VALUES(%s, '', %s, "
                        "DATE_ADD(NOW(), INTERVAL %s MINUTE), 0)",
                        (mobile, vid, OTP_TTL_MINUTES))
        conn.commit()
    finally:
        conn.close()
    try:
        from dashboard.store import otp_log_add
        otp_log_add(db, mobile, "Message Central")
    except Exception:
        pass
    return {"ok": True, "channel": "sms"}


def _mc_check_otp(db, mobile: str, code: str) -> bool:
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT mc_verification_id, (expires_at < NOW()) AS expired, "
                        "attempts FROM login_otps WHERE msisdn=%s", (mobile,))
            row = cur.fetchone()
        if not row:
            return False
        vid, expired, attempts = row[0], row[1], (row[2] or 0)
        if not vid or attempts >= OTP_MAX_ATTEMPTS or expired:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM login_otps WHERE msisdn=%s", (mobile,))
            conn.commit()
            return False
        token = _mc_auth_token()
        if not token:
            return False
        params = urllib.parse.urlencode({
            "customerId": _mc_customer_id(),
            "verificationId": vid,
            "code": code,
        })
        url = f"{_mc_base()}/verification/v3/validateOtp?{params}"
        try:
            resp = _mc_request("GET", url, {"authToken": token})
        except Exception as e:
            logger.error("[auth] MessageCentral validate failed for %s: %s", mobile, e)
            with conn.cursor() as cur:
                cur.execute("UPDATE login_otps SET attempts=attempts+1 WHERE msisdn=%s",
                            (mobile,))
            conn.commit()
            return False
        status = str((resp.get("data") or {}).get("verificationStatus") or "").upper()
        ok = status == "VERIFICATION_COMPLETED"
        with conn.cursor() as cur:
            if ok:
                cur.execute("DELETE FROM login_otps WHERE msisdn=%s", (mobile,))
            else:
                cur.execute("UPDATE login_otps SET attempts=attempts+1 WHERE msisdn=%s",
                            (mobile,))
        conn.commit()
    finally:
        conn.close()
    try:
        from dashboard.store import otp_log_update_status
        if ok:
            otp_log_update_status(db, mobile, "verified")
        elif attempts + 1 >= OTP_MAX_ATTEMPTS:
            otp_log_update_status(db, mobile, "locked", attempts + 1)
        else:
            otp_log_update_status(db, mobile, "sent", attempts + 1)
    except Exception:
        pass
    return ok


# --------------------------------------------------------------------------- #
# provider: Twilio Verify
# --------------------------------------------------------------------------- #
def _twilio_send_otp(mobile: str) -> dict:
    """Twilio Verify owns code generation, storage and expiry."""
    sid = _twilio_verify_sid()
    if not sid:
        return {"ok": False, "error": "twilio_not_configured"}
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


def _twilio_check_otp(mobile: str, code: str) -> bool:
    sid = _twilio_verify_sid()
    if not sid:
        return False
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


# --------------------------------------------------------------------------- #
# provider: dev fallback — self-managed code, logged (echoed only in DEMO_MODE)
# --------------------------------------------------------------------------- #
def _dev_send_otp(db, mobile: str) -> dict:
    code = f"{secrets.randbelow(1000000):06d}"
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM login_otps WHERE msisdn=%s", (mobile,))
            cur.execute("INSERT INTO login_otps(msisdn, code_hash, expires_at, attempts) "
                        "VALUES(%s, %s, DATE_ADD(NOW(), INTERVAL %s MINUTE), 0)",
                        (mobile, _hash_code(mobile, code), OTP_TTL_MINUTES))
        conn.commit()
    finally:
        conn.close()
    logger.warning("[auth][DEV] OTP for %s is %s (no OTP provider configured)",
                   mobile, code)
    out = {"ok": True, "channel": "dev"}
    if _demo_mode():
        out["dev_code"] = code          # surfaced to the UI only in DEMO_MODE
    return out


def _dev_check_otp(db, mobile: str, code: str) -> bool:
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT code_hash, (expires_at < NOW()) AS expired, attempts "
                        "FROM login_otps WHERE msisdn=%s", (mobile,))
            row = cur.fetchone()
            if not row:
                return False
            code_hash, expired, attempts = row[0], row[1], (row[2] or 0)
            if attempts >= OTP_MAX_ATTEMPTS or expired:
                cur.execute("DELETE FROM login_otps WHERE msisdn=%s", (mobile,))
                conn.commit()
                return False
            ok = hmac.compare_digest(code_hash or "", _hash_code(mobile, code))
            if ok:
                cur.execute("DELETE FROM login_otps WHERE msisdn=%s", (mobile,))
            else:
                cur.execute("UPDATE login_otps SET attempts=attempts+1 WHERE msisdn=%s",
                            (mobile,))
        conn.commit()
        return ok
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# sessions
# --------------------------------------------------------------------------- #
def create_session(db, user_id: str, mobile: str) -> str:
    # `mobile` is kept for call-site compatibility but v2 login_sessions has no
    # mobile column — the user row carries the number.
    token = "s_" + secrets.token_urlsafe(24)
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO login_sessions(token, user_id, expires_at) "
                        "VALUES(%s, %s, DATE_ADD(NOW(), INTERVAL %s DAY))",
                        (token, user_id, SESSION_TTL_DAYS))
        conn.commit()
    finally:
        conn.close()
    return token


def user_for_session(db, token: str):
    """Return the user dict for a valid, unexpired session token, else None."""
    if not token:
        return None
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, (expires_at < NOW()) AS expired "
                        "FROM login_sessions WHERE token=%s", (token,))
            row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        return None
    user_id, expired = row[0], row[1]
    if expired:
        destroy_session(db, token)
        return None
    return users.get_user(db, user_id)


def destroy_session(db, token: str):
    if not token:
        return
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM login_sessions WHERE token=%s", (token,))
        conn.commit()
    finally:
        conn.close()


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
