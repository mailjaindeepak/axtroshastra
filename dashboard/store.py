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


def _ensure(db):
    with db() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS dash_delivery(
                rid TEXT PRIMARY KEY,
                status TEXT,
                note TEXT,
                updated_at TEXT)"""
        )


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
def _ensure_team(db):
    with db() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS dash_team(
                value TEXT PRIMARY KEY,
                kind TEXT,
                label TEXT,
                added_at TEXT)"""
        )


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
    """Return {"phones":[{value,label}], "emails":[{value,label}]}."""
    _ensure_team(db)
    with db() as c:
        rows = c.execute("SELECT value,kind,label FROM dash_team").fetchall()
    out = {"phones": [], "emails": []}
    for value, kind, label in rows:
        bucket = "phones" if kind == "phone" else "emails"
        out[bucket].append({"value": value, "label": label or ""})
    return out


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
