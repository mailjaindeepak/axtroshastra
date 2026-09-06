"""
db_v2.py — MySQL-native data access for the clean v2 schema (db/schema_v2.sql).

Written directly for MySQL — NO SQLite dialect and NO dbcompat translation —
because v2 is a deliberately-MySQL schema (real types, ENUMs, foreign keys), and
the old translate() shim is a proven bug source (it turned every TEXT into
LONGTEXT, breaks on literal `%`, and its INSERT-OR-REPLACE cascades away child
rows under v2's FKs).

Rules this module follows:
  * Every query is parameterized with %s — never string-formatted.
  * Upserts use `INSERT ... ON DUPLICATE KEY UPDATE`, NEVER `REPLACE`
    (REPLACE = delete-then-insert, which cascade-deletes children under FKs).
  * Functions take an open connection and DO NOT commit — the caller owns the
    transaction, so a whole flow (user + report + subjects + payment) is atomic.

Connection env (local defaults for dev/tests; EB sets these in prod):
  DB_HOST(127.0.0.1)  DB_PORT(3306)  DB_USER(root)  DB_PASSWORD('')  DB_NAME(axtroshastra_v2)
"""
import json
import os
import secrets


def _new_id(prefix: str) -> str:
    """Opaque, URL-safe id, e.g. 'u_ab12cd34ef'. Won't leak volume; safe in URLs."""
    return prefix + secrets.token_urlsafe(9)


def get_conn(db_name: str | None = None):
    """Open a fresh MySQL connection (autocommit OFF — caller commits)."""
    import pymysql
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=db_name or os.getenv("DB_NAME", "axtroshastra_v2"),
        charset="utf8mb4",
        autocommit=False,
    )


# --------------------------------------------------------------- users -------

def create_or_get_user(conn, country_code: str, mobile: str, email: str | None = None) -> str:
    """Return the user id for (country_code, mobile), creating the row if new.

    Deduped by the UNIQUE(country_code, mobile) key, so a repeat buyer stays ONE
    user. Worker-safe: the atomic upsert means two concurrent callers can't create
    two rows. Email is filled only when we have a real one and none is stored yet;
    `name` is left NULL (it's user-editable on /account, never auto-set).
    """
    candidate = _new_id("u_")
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users(id, country_code, mobile, email, mobile_verified, "
            "email_verified, status) VALUES(%s,%s,%s,%s,0,0,'active') "
            "ON DUPLICATE KEY UPDATE email = COALESCE(NULLIF(email,''), VALUES(email))",
            (candidate, country_code, mobile, email),
        )
        cur.execute(
            "SELECT id FROM users WHERE country_code=%s AND mobile=%s",
            (country_code, mobile),
        )
        return cur.fetchone()[0]


# -------------------------------------------------------------- reports ------

def create_report(conn, user_id: str | None, product: str, report_data: dict | None,
                  *, lang: str = "en", variant: str | None = None,
                  status: str = "preview", extra_inputs: dict | None = None,
                  report_id: str | None = None) -> str:
    """Insert a report row and return its id (reuses `report_id` if given, so a
    migration can keep old /report/{id} links)."""
    rid = report_id or _new_id("rep_")
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO reports(id, user_id, product, variant, lang, status, "
            "extra_inputs, report_data) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
            (rid, user_id, product, variant, lang, status,
             json.dumps(extra_inputs) if extra_inputs is not None else None,
             json.dumps(report_data) if report_data is not None else None),
        )
        return rid


def add_subject(conn, report_id: str, role: str, *, name=None, gender=None, dob=None,
                tob=None, time_quality=None, birth_place=None, birth_lat=None,
                birth_lon=None, birth_tz=None) -> int:
    """Add one person to a report (solo = 1 call, compatibility = 2)."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO report_subjects(report_id, role, name, gender, dob, tob, "
            "time_quality, birth_place, birth_lat, birth_lon, birth_tz) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (report_id, role, name, gender, dob, tob, time_quality,
             birth_place, birth_lat, birth_lon, birth_tz),
        )
        return cur.lastrowid


def set_report_paid(conn, report_id: str) -> None:
    """Flip a report preview -> paid (same row; status is not a new report)."""
    with conn.cursor() as cur:
        cur.execute("UPDATE reports SET status='paid' WHERE id=%s", (report_id,))


# ------------------------------------------------------------- payments ------

def record_payment(conn, report_id: str, user_id: str, amount_paise: int, *,
                   payment_id: str | None = None, razorpay_order_id=None,
                   razorpay_payment_id=None, status: str = "created", method=None,
                   upi_vpa=None, payment_email=None, payment_contact=None,
                   paid_at=None, currency: str = "INR") -> str:
    """Create (or upsert) a payment row and return its id. Uses ON DUPLICATE KEY
    UPDATE — never REPLACE — so re-processing the same payment can't delete
    anything. A free-pass unlock is just method='free_pass', amount_paise=0."""
    pid = payment_id or _new_id("pmt_")
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO payments(id, report_id, user_id, razorpay_order_id, "
            "razorpay_payment_id, amount_paise, currency, status, method, upi_vpa, "
            "payment_email, payment_contact, paid_at) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON DUPLICATE KEY UPDATE status=VALUES(status), "
            "amount_paise=VALUES(amount_paise), "
            "method=COALESCE(VALUES(method), method), "
            "razorpay_payment_id=COALESCE(VALUES(razorpay_payment_id), razorpay_payment_id), "
            "paid_at=COALESCE(VALUES(paid_at), paid_at)",
            (pid, report_id, user_id, razorpay_order_id, razorpay_payment_id,
             amount_paise, currency, status, method, upi_vpa, payment_email,
             payment_contact, paid_at),
        )
        return pid


def mark_payment_captured(conn, payment_id: str, *, razorpay_payment_id=None, method=None,
                          upi_vpa=None, payment_email=None, payment_contact=None,
                          paid_at=None) -> None:
    """Mark a payment captured and fill the settlement detail we now know."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE payments SET status='captured', "
            "razorpay_payment_id=COALESCE(%s, razorpay_payment_id), "
            "method=COALESCE(%s, method), upi_vpa=COALESCE(%s, upi_vpa), "
            "payment_email=COALESCE(%s, payment_email), "
            "payment_contact=COALESCE(%s, payment_contact), "
            "paid_at=COALESCE(%s, paid_at) WHERE id=%s",
            (razorpay_payment_id, method, upi_vpa, payment_email, payment_contact,
             paid_at, payment_id),
        )


# --------------------------------------------------------------- reads -------

def get_report(conn, report_id: str) -> dict | None:
    """Fetch a report as a dict (report_data parsed back from JSON), or None."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, user_id, product, lang, status, report_data, created_at "
            "FROM reports WHERE id=%s", (report_id,))
        row = cur.fetchone()
    if not row:
        return None
    return {"id": row[0], "user_id": row[1], "product": row[2], "lang": row[3],
            "status": row[4],
            "report_data": json.loads(row[5]) if row[5] else None,
            "created_at": row[6]}


def get_user_reports(conn, user_id: str) -> list[str]:
    """Report ids owned by a user, newest first."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM reports WHERE user_id=%s ORDER BY created_at DESC",
                    (user_id,))
        return [r[0] for r in cur.fetchall()]
