"""dashboard/store.py — the dashboard's OWN storage.

Owns a single new table, dash_delivery, that lets an admin manually mark a paid
report delivered/failed WITHOUT touching the core `reports` table or any of the
api.py send paths. Created lazily via the ctx `db` factory so it works on both
SQLite (local/tests) and MySQL (prod) — the DDL uses only portable syntax
(CREATE TABLE IF NOT EXISTS, TEXT PRIMARY KEY, ? placeholders, INSERT OR
REPLACE), all of which dbcompat.translate() maps for MySQL.

    dash_delivery(rid PRIMARY KEY, status, note, updated_at)
"""
import re
from datetime import datetime


def norm_phone(value):
    """Reduce a phone to its LAST 10 DIGITS so '+91 99671 24332' and
    '9967124332' compare equal. Returns the digit tail (<=10 chars)."""
    digits = re.sub(r"\D", "", value or "")
    return digits[-10:] if len(digits) >= 10 else digits


def norm_email(value):
    return (value or "").strip().lower()


_delivery_ready = False


def _ensure(db):
    global _delivery_ready
    if _delivery_ready:
        return
    with db() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS dash_delivery(
                rid TEXT PRIMARY KEY,
                status TEXT,
                note TEXT,
                updated_at TEXT)"""
        )
    _delivery_ready = True


def get_status(db, rid):
    """Return {"status","note","updated_at"} for rid, or None when unset."""
    _ensure(db)
    with db() as c:
        row = c.execute(
            "SELECT status,note,updated_at FROM dash_delivery WHERE rid=?",
            (rid,),
        ).fetchone()
    if not row:
        return None
    return {"status": row[0] or "", "note": row[1] or "", "updated_at": row[2] or ""}


def set_status(db, rid, status, note=""):
    """Upsert the manual delivery status for a report. Portable upsert:
    INSERT OR REPLACE is rewritten to REPLACE INTO on MySQL by dbcompat."""
    _ensure(db)
    now = datetime.utcnow().isoformat()
    with db() as c:
        c.execute(
            "INSERT OR REPLACE INTO dash_delivery(rid,status,note,updated_at) "
            "VALUES(?,?,?,?)",
            (rid, (status or "").strip(), (note or "").strip(), now),
        )
    return {"rid": rid, "status": (status or "").strip(),
            "note": (note or "").strip(), "updated_at": now}


def all_statuses(db):
    """Return {rid: {"status","note","updated_at"}} for every manually-set row.
    Cheap enough to fetch once per overview/deliveries request and join in-memory."""
    _ensure(db)
    with db() as c:
        rows = c.execute(
            "SELECT rid,status,note,updated_at FROM dash_delivery"
        ).fetchall()
    return {r[0]: {"status": r[1] or "", "note": r[2] or "",
                   "updated_at": r[3] or ""} for r in rows}


# --------------------------------------------------------------------------- #
# dash_team — the team/admin exclusion allowlist. Payments whose phone or email
# match a row here NEVER count as revenue or as a real customer, on ANY date.
#   dash_team(value PRIMARY KEY, kind, label, added_at)   kind in ('phone','email')
# Phones are stored as their last-10-digits; emails lowercased+stripped, so the
# stored value is directly comparable to a normalised lookup key.
# --------------------------------------------------------------------------- #
_team_ready = False


def _ensure_team(db):
    global _team_ready
    if _team_ready:
        return
    with db() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS dash_team(
                value TEXT PRIMARY KEY,
                kind TEXT,
                label TEXT,
                added_at TEXT,
                linked_to TEXT)"""
        )
        try:
            c.execute("ALTER TABLE dash_team ADD COLUMN linked_to TEXT")
        except Exception:
            pass
    _team_ready = True


def team_add(db, kind, value, label=""):
    """Add a phone or email to the exclusion allowlist. Value is normalised
    before storing so lookups match regardless of formatting."""
    _ensure_team(db)
    kind = (kind or "").strip().lower()
    norm = norm_phone(value) if kind == "phone" else norm_email(value)
    if kind not in ("phone", "email") or not norm:
        raise ValueError("kind must be phone|email and value must be non-empty")
    with db() as c:
        c.execute(
            "INSERT OR REPLACE INTO dash_team(value,kind,label,added_at) VALUES(?,?,?,?)",
            (norm, kind, (label or "").strip(), datetime.utcnow().isoformat()),
        )
    return {"value": norm, "kind": kind, "label": (label or "").strip()}


def team_remove(db, value):
    """Remove by stored value; also tries the normalised phone/email form so a
    raw '+91…' or mixed-case email still deletes the stored row."""
    _ensure_team(db)
    candidates = {value or "", norm_phone(value), norm_email(value)}
    candidates.discard("")
    with db() as c:
        for v in candidates:
            c.execute("DELETE FROM dash_team WHERE value=?", (v,))
    return {"removed": sorted(candidates)}


def team_all(db):
    """Return {"phones":[{value,label,linked_to}], "emails":[{value,label}]}."""
    _ensure_team(db)
    with db() as c:
        rows = c.execute("SELECT value,kind,label,linked_to FROM dash_team").fetchall()
    out = {"phones": [], "emails": []}
    for value, kind, label, linked_to in rows:
        bucket = "phones" if kind == "phone" else "emails"
        entry = {"value": value, "label": label or ""}
        if kind == "phone" and linked_to:
            entry["linked_to"] = linked_to
        out[bucket].append(entry)
    return out


def team_link(db, secondary, primary):
    """Link a secondary phone to a primary phone. Both must already exist in
    dash_team. The primary must not itself be linked to another number."""
    _ensure_team(db)
    sec = norm_phone(secondary)
    pri = norm_phone(primary)
    if not sec or not pri or sec == pri:
        raise ValueError("need two distinct phone numbers")
    with db() as c:
        s_row = c.execute("SELECT kind, linked_to FROM dash_team WHERE value=?", (sec,)).fetchone()
        p_row = c.execute("SELECT kind, linked_to FROM dash_team WHERE value=?", (pri,)).fetchone()
        if not s_row:
            raise ValueError(f"{sec} not in team list")
        if not p_row:
            raise ValueError(f"{pri} not in team list")
        if p_row[1]:
            raise ValueError(f"{pri} is already linked to {p_row[1]} — unlink it first")
        c.execute("UPDATE dash_team SET linked_to=? WHERE value=?", (pri, sec))
    return {"secondary": sec, "primary": pri}


def team_unlink(db, value):
    """Remove the linked_to pointer from a phone number."""
    _ensure_team(db)
    norm = norm_phone(value)
    with db() as c:
        c.execute("UPDATE dash_team SET linked_to=NULL WHERE value=?", (norm,))
    return {"unlinked": norm}


def team_sets(db):
    """Fast membership sets for the request path: (phone_set, email_set)."""
    data = team_all(db)
    return ({p["value"] for p in data["phones"]},
            {e["value"] for e in data["emails"]})


# --------------------------------------------------------------------------- #
# dash_ledger — manual top-up / usage entries for the Money & Feasibility tab.
# Each row is a deposit (money added) or usage (money spent) for a service.
# --------------------------------------------------------------------------- #
def _ensure_ledger(db):
    with db() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS dash_ledger(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT,
                entry TEXT,
                amount TEXT,
                date TEXT,
                note TEXT,
                added_at TEXT)"""
        )


def ledger_add(db, service, entry, amount, date, note=""):
    _ensure_ledger(db)
    if entry not in ("deposit", "usage"):
        raise ValueError("entry must be deposit or usage")
    if not service or not amount:
        raise ValueError("service and amount are required")
    now = datetime.utcnow().isoformat()
    with db() as c:
        c.execute(
            "INSERT INTO dash_ledger(service,entry,amount,date,note,added_at) "
            "VALUES(?,?,?,?,?,?)",
            ((service or "").strip(), entry, (amount or "").strip(),
             (date or now[:10]).strip(), (note or "").strip(), now),
        )
    return {"service": service, "entry": entry, "amount": amount,
            "date": date or now[:10], "note": note}


def ledger_all(db):
    _ensure_ledger(db)
    with db() as c:
        rows = c.execute(
            "SELECT service, entry, amount, date, note "
            "FROM dash_ledger ORDER BY date DESC, added_at DESC"
        ).fetchall()
    return [{"service": r[0], "entry": r[1], "amount": r[2],
             "date": r[3], "note": r[4]} for r in rows]


# --------------------------------------------------------------------------- #
# dash_llm_log — one row per Claude call for report narrative generation.
# Captures timing, token usage, mode (live/fallback/error), model, and product.
# --------------------------------------------------------------------------- #
def _ensure_llm_log(db):
    with db() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS dash_llm_log(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rid TEXT,
                product TEXT,
                mode TEXT,
                model TEXT,
                latency_s REAL,
                input_tokens INTEGER,
                output_tokens INTEGER,
                sections INTEGER,
                total_sections INTEGER,
                created_at TEXT)"""
        )


def llm_log_add(db, rid, meta):
    _ensure_llm_log(db)
    now = datetime.utcnow().isoformat()
    with db() as c:
        c.execute(
            "INSERT INTO dash_llm_log(rid,product,mode,model,latency_s,"
            "input_tokens,output_tokens,sections,total_sections,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            (rid, (meta.get("product") or ""),
             (meta.get("mode") or ""),
             (meta.get("model") or ""),
             meta.get("latency_s", 0),
             meta.get("input_tokens", 0),
             meta.get("output_tokens", 0),
             meta.get("sections", 0),
             meta.get("total_sections", 0),
             now),
        )


def llm_log_recent(db, limit=50):
    _ensure_llm_log(db)
    with db() as c:
        rows = c.execute(
            "SELECT rid, product, mode, model, latency_s, "
            "input_tokens, output_tokens, sections, total_sections, created_at "
            "FROM dash_llm_log ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"rid": r[0], "product": r[1], "mode": r[2], "model": r[3],
             "latency_s": r[4], "input_tokens": r[5], "output_tokens": r[6],
             "sections": r[7], "total_sections": r[8], "time": r[9]} for r in rows]


def llm_log_stats(db):
    """Summary stats for the LLM tab cards: today's count, fallback count,
    average latency, slowest call."""
    _ensure_llm_log(db)
    today = datetime.utcnow().date().isoformat()
    with db() as c:
        rows = c.execute(
            "SELECT mode, latency_s FROM dash_llm_log WHERE created_at >= ?",
            (today,),
        ).fetchall()
    if not rows:
        return {"live_today": 0, "fallbacks": 0, "avg_gen_s": None,
                "slowest_s": None}
    live = sum(1 for r in rows if r[0] == "live Claude")
    fallbacks = sum(1 for r in rows if r[0] != "live Claude")
    latencies = [r[1] for r in rows if r[1] and r[1] > 0]
    return {
        "live_today": live,
        "fallbacks": fallbacks,
        "avg_gen_s": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "slowest_s": round(max(latencies), 1) if latencies else None,
    }


# --------------------------------------------------------------------------- #
# dash_otp_log — append-only log of every OTP send request. Unlike login_otps
# (which is a pending-OTP table with PRIMARY KEY on mobile — rows get deleted on
# successful verification), this table NEVER deletes rows, so the dashboard
# always has a complete history of every OTP we asked MC to send.
# --------------------------------------------------------------------------- #
def _ensure_otp_log(db):
    with db() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS dash_otp_log(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mobile TEXT,
                provider TEXT,
                status TEXT,
                attempts INTEGER DEFAULT 0,
                created_at TEXT)"""
        )


def otp_log_add(db, mobile, provider="Message Central"):
    _ensure_otp_log(db)
    now = datetime.utcnow().isoformat()
    with db() as c:
        c.execute(
            "INSERT INTO dash_otp_log(mobile,provider,status,attempts,created_at) "
            "VALUES(?,?,?,0,?)",
            (mobile or "", provider, "sent", now),
        )


def otp_log_update_status(db, mobile, status, attempts=None):
    _ensure_otp_log(db)
    with db() as c:
        # MySQL forbids referencing the target table in a subquery of the same
        # UPDATE (error 1093), so read the latest id first, then update it.
        row = c.execute(
            "SELECT MAX(id) FROM dash_otp_log WHERE mobile=?", (mobile,)).fetchone()
        if not row or row[0] is None:
            return
        mid = row[0]
        if attempts is not None:
            c.execute("UPDATE dash_otp_log SET status=?, attempts=? WHERE id=?",
                      (status, attempts, mid))
        else:
            c.execute("UPDATE dash_otp_log SET status=? WHERE id=?", (status, mid))


def otp_log_recent(db, limit=200):
    _ensure_otp_log(db)
    with db() as c:
        rows = c.execute(
            "SELECT mobile, provider, status, attempts, created_at "
            "FROM dash_otp_log ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"phone": r[0], "provider": r[1], "status": r[2],
             "attempts": r[3], "time": r[4]} for r in rows]


# --------------------------------------------------------------------------- #
# dash_ops_log — ops event store (run results, rollbacks, alerts).
# Replaces the ephemeral ops_history.jsonl with a durable DB table that the
# dashboard can query directly. GitHub Actions workflows POST events here.
# --------------------------------------------------------------------------- #
def _ensure_ops_log(db):
    with db() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS dash_ops_log(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT,
                status TEXT,
                detail TEXT,
                run_url TEXT,
                from_ver TEXT,
                to_ver TEXT,
                severity TEXT,
                created_at TEXT)"""
        )


def ops_log_add(db, kind, **kwargs):
    _ensure_ops_log(db)
    now = datetime.utcnow().isoformat()
    with db() as c:
        c.execute(
            "INSERT INTO dash_ops_log(kind,status,detail,run_url,"
            "from_ver,to_ver,severity,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (kind,
             (kwargs.get("status") or ""),
             (kwargs.get("detail") or ""),
             (kwargs.get("run_url") or ""),
             (kwargs.get("from_ver") or ""),
             (kwargs.get("to_ver") or ""),
             (kwargs.get("severity") or ""),
             now),
        )
    return {"kind": kind, "created_at": now}


def ops_log_recent(db, limit=50, kind=None):
    _ensure_ops_log(db)
    with db() as c:
        if kind:
            rows = c.execute(
                "SELECT kind, status, detail, run_url, from_ver, to_ver, "
                "severity, created_at FROM dash_ops_log "
                "WHERE kind=? ORDER BY created_at DESC LIMIT ?",
                (kind, limit),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT kind, status, detail, run_url, from_ver, to_ver, "
                "severity, created_at FROM dash_ops_log "
                "ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [{"kind": r[0], "status": r[1], "detail": r[2], "run_url": r[3],
             "from_ver": r[4], "to_ver": r[5], "severity": r[6],
             "time": r[7]} for r in rows]


def ops_log_last(db, kind):
    rows = ops_log_recent(db, limit=1, kind=kind)
    return rows[0] if rows else None


# --------------------------------------------------------------------------- #
# Robot cleanup — remove all reports created by the robot customer.
# Robot reports are identified by payload containing 'Robot Customer',
# 'Robot Student', 'Robot Aisha', or 'Robot Arjun'.
# --------------------------------------------------------------------------- #
_ROBOT_PATTERNS = ["%Robot Customer%", "%Robot Student%", "%Robot Aisha%", "%Robot Arjun%"]


def robot_report_count(db):
    import db_v2                       # v2: robot marker lives in report_data JSON
    clauses = " OR ".join(["report_data LIKE %s" for _ in _ROBOT_PATTERNS])
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) FROM reports WHERE " + clauses,
                      tuple(_ROBOT_PATTERNS))
            row = c.fetchone()
    finally:
        conn.close()
    return row[0] if row else 0


def robot_cleanup(db, dry_run=True):
    import db_v2
    clauses = " OR ".join(["report_data LIKE %s" for _ in _ROBOT_PATTERNS])
    params = tuple(_ROBOT_PATTERNS)
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) FROM reports WHERE " + clauses, params)
            count = c.fetchone()[0]
            if dry_run:
                return {"deleted": 0, "would_delete": count, "dry_run": True}
            if count:
                # report_subjects cascade; a robot report with a payment (FK
                # RESTRICT) would block, but robot rows are unpaid test data.
                c.execute("DELETE FROM reports WHERE " + clauses, params)
                conn.commit()
    finally:
        conn.close()
    return {"deleted": count, "would_delete": count, "dry_run": False}
