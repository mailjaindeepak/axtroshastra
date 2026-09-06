#!/usr/bin/env python3
"""
migrate_v2.py — one-off migration of the real paid customers from the OLD schema
into the clean v2 schema (db/schema_v2.sql).

WHAT IT DOES (per source row):
  users            : one row per person, deduped by (country_code, mobile).
                     The customer who paid twice → ONE user, TWO payments.
  reports          : reuses the OLD report id (so /report/{id} still resolves),
                     status='paid', the WHOLE old payload kept in report_data.
  report_subjects  : solo/marriage → 1 row with full birth details;
                     milan (compatibility) → 2 rows, names only (birth NULL,
                     because the old code never stored milan birth inputs).
  payments         : one row; razorpay ids + amount + contact; method NULL
                     (the old DB never stored it).

SAFE BY DESIGN:
  * READS a local JSON file exported from the old DB (never connects to prod).
  * WRITES only to the LOCAL v2 database.
  * Idempotent: re-running does not duplicate (upserts by key; rebuilds a
    report's subjects each run).
  * --dry-run parses + reports what it WOULD do, writing nothing.

USAGE:
  python3 db/migrate_v2.py --dry-run
  python3 db/migrate_v2.py            # real run (asks for local MySQL password)

Connection to the LOCAL v2 db (override via env if yours differs):
  DBV2_HOST (127.0.0.1)  DBV2_PORT (3306)  DBV2_USER (root)
  DBV2_NAME (axtroshastra_v2)  DBV2_PASSWORD (else prompted)
"""
import argparse, getpass, json, os, re, secrets, sys

SRC_DEFAULT = "/Users/shreyanshjain/Desktop/Axtroshastra-Sharing/axtro_migrate_source.json"

# ---- small helpers ---------------------------------------------------------

def norm_mobile(raw):
    """'+91 94708 32578' -> ('+91', '9470832578'). Country code = whatever digits
    precede the last 10; defaults to +91 when only 10 digits are present."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) < 10:
        return None, None
    national = digits[-10:]
    cc = digits[:-10]
    return ("+" + cc) if cc else "+91", national

def clean_email(raw):
    """Real email or None. Never store the void@razorpay.com sentinel or test addrs."""
    e = (raw or "").strip().lower()
    if not e or e == "void@razorpay.com" or e.endswith("@axtroshastra.test"):
        return None
    return e

def map_gender(raw):
    g = (raw or "").strip().lower()
    if g in ("male", "m", "man", "boy", "groom"):   return "male"
    if g in ("female", "f", "woman", "girl", "bride"): return "female"
    return "other" if g else None

def map_lang(raw):
    return "hi" if (raw or "").strip().lower() in ("hi", "hindi") else "en"

def to_dt(raw):
    """'2026-08-08T05:10:26.028156' -> '2026-08-08 05:10:26' (MySQL DATETIME)."""
    if not raw:
        return None
    return raw.replace("T", " ")[:19]

def blank_to_none(v):
    v = (v or "").strip() if isinstance(v, str) else v
    return v or None

def new_id(prefix):
    return prefix + secrets.token_urlsafe(9)

# ---- main ------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=SRC_DEFAULT, help="path to the exported JSON")
    ap.add_argument("--dry-run", action="store_true", help="parse + report, write nothing")
    args = ap.parse_args()

    with open(args.source) as f:
        rows = json.load(f)
    if not isinstance(rows, list):
        sys.exit("expected a JSON array of rows")
    print(f"source: {args.source}  ({len(rows)} rows)")

    conn = None
    if not args.dry_run:
        import pymysql
        pw = os.environ.get("DBV2_PASSWORD") or getpass.getpass("Local MySQL password: ")
        conn = pymysql.connect(
            host=os.environ.get("DBV2_HOST", "127.0.0.1"),
            port=int(os.environ.get("DBV2_PORT", "3306")),
            user=os.environ.get("DBV2_USER", "root"),
            password=pw,
            database=os.environ.get("DBV2_NAME", "axtroshastra_v2"),
            charset="utf8mb4", autocommit=False,
        )
    cur = conn.cursor() if conn else None
    user_by_mobile = {}   # (cc, mobile) -> user_id, so the twice-payer stays one user
    stats = {"users": 0, "reports": 0, "subjects": 0, "payments": 0, "milan": 0, "solo": 0}

    def upsert_user(cc, mobile, email):
        key = (cc, mobile)
        if key in user_by_mobile:
            uid = user_by_mobile[key]
            if email and cur:                       # fill email if we now have one
                cur.execute("UPDATE users SET email=COALESCE(NULLIF(email,''),%s) WHERE id=%s", (email, uid))
            return uid
        if cur:
            cur.execute("SELECT id FROM users WHERE country_code=%s AND mobile=%s", (cc, mobile))
            hit = cur.fetchone()
            if hit:
                uid = hit[0]
            else:
                uid = new_id("u_")
                cur.execute(
                    "INSERT INTO users(id,country_code,mobile,email,mobile_verified,email_verified,status) "
                    "VALUES(%s,%s,%s,%s,0,0,'active')", (uid, cc, mobile, email))
                stats["users"] += 1
        else:
            uid = new_id("u_"); stats["users"] += 1
        user_by_mobile[key] = uid
        return uid

    for r in rows:
        payload = r["payload"]
        payload = json.loads(payload) if isinstance(payload, str) else payload
        meta = payload.get("meta") or {}
        product = payload.get("product") or "marriage"
        is_milan = (product == "milan")
        stats["milan" if is_milan else "solo"] += 1

        cc, mobile = norm_mobile(r.get("user_phone") or r.get("phone"))
        if not mobile:
            print(f"  ! skip {r.get('payment_id')}: no usable phone")
            continue
        email = clean_email(meta.get("_email"))
        uid = upsert_user(cc, mobile, email)

        rid = r["id"]                                # reuse the OLD report id
        created = to_dt(r.get("created_at"))
        if cur:
            cur.execute(
                "INSERT INTO reports(id,user_id,product,variant,lang,status,report_data,created_at) "
                "VALUES(%s,%s,%s,%s,%s,'paid',%s,%s) "
                "ON DUPLICATE KEY UPDATE user_id=VALUES(user_id),status='paid',report_data=VALUES(report_data)",
                (rid, uid, product, blank_to_none(meta.get("variant")), map_lang(meta.get("lang")),
                 json.dumps(payload), created))
            cur.execute("DELETE FROM report_subjects WHERE report_id=%s", (rid,))  # clean re-run
        stats["reports"] += 1

        # subjects
        subs = []
        if is_milan:
            subs.append(("self", meta.get("p1"), None, None, None, None, None, None, None, None))
            subs.append(("partner", meta.get("p2"), None, None, None, None, None, None, None, None))
        else:
            b = meta.get("_birth") or {}
            subs.append(("self", meta.get("name"), map_gender(meta.get("_gender")),
                         blank_to_none(b.get("dob")), blank_to_none(b.get("tob")),
                         blank_to_none(meta.get("time_quality")),
                         blank_to_none(b.get("place")), b.get("lat"), b.get("lon"), b.get("tz")))
        for role, name, gender, dob, tob, tq, place, lat, lon, tz in subs:
            if cur:
                cur.execute(
                    "INSERT INTO report_subjects(report_id,role,name,gender,dob,tob,time_quality,"
                    "birth_place,birth_lat,birth_lon,birth_tz) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (rid, role, blank_to_none(name), gender, dob, tob, tq, place, lat, lon, tz))
            stats["subjects"] += 1

        # payment (id = the razorpay id; deterministic → idempotent)
        pid = r["payment_id"]
        if cur:
            cur.execute(
                "INSERT INTO payments(id,report_id,user_id,razorpay_order_id,razorpay_payment_id,"
                "amount_paise,currency,status,method,payment_email,payment_contact,paid_at,created_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,'INR','captured',NULL,%s,%s,%s,%s) "
                "ON DUPLICATE KEY UPDATE status='captured',amount_paise=VALUES(amount_paise)",
                (pid, rid, uid, blank_to_none(r.get("order_id")), pid,
                 int(r.get("amount_paise") or 0), email, blank_to_none(r.get("phone")),
                 created, created))
        stats["payments"] += 1

    if conn:
        conn.commit(); conn.close()

    print("\n" + ("DRY RUN — nothing written." if args.dry_run else "DONE — committed."))
    print(f"  solo/marriage rows : {stats['solo']}")
    print(f"  milan rows         : {stats['milan']}")
    print(f"  users created      : {stats['users']}  (deduped by mobile)")
    print(f"  reports            : {stats['reports']}")
    print(f"  report_subjects    : {stats['subjects']}")
    print(f"  payments           : {stats['payments']}")

if __name__ == "__main__":
    main()
