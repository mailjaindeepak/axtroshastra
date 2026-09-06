"""
test_db_v2.py — tests for the MySQL-native v2 data layer, run against a REAL MySQL
(the point: exercise the engine we ship on, not SQLite). The throwaway-schema
`conn` fixture lives in conftest.py.

RUN (from repo root, with pymysql + pytest installed):
    DB_PASSWORD='<your local mysql password>' python3 -m pytest db/ -v
"""
import sys
from pathlib import Path

import pymysql
import pytest

sys.path.insert(0, str(Path(__file__).parent))
import db_v2  # noqa: E402


def _count(conn, table):
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        return cur.fetchone()[0]


# ---- users ----

def test_user_dedupes_by_mobile(conn):
    a = db_v2.create_or_get_user(conn, "+91", "9990000001")
    b = db_v2.create_or_get_user(conn, "+91", "9990000001")   # same person again
    assert a == b
    assert _count(conn, "users") == 1                          # one row, not two

    db_v2.create_or_get_user(conn, "+91", "9990000002")        # a different person
    assert _count(conn, "users") == 2


def test_user_email_backfills_only_when_blank(conn):
    uid = db_v2.create_or_get_user(conn, "+91", "9990000003")          # no email
    db_v2.create_or_get_user(conn, "+91", "9990000003", email="real@x.com")
    with conn.cursor() as cur:
        cur.execute("SELECT email FROM users WHERE id=%s", (uid,))
        assert cur.fetchone()[0] == "real@x.com"                       # filled
    db_v2.create_or_get_user(conn, "+91", "9990000003", email="other@x.com")
    with conn.cursor() as cur:
        cur.execute("SELECT email FROM users WHERE id=%s", (uid,))
        assert cur.fetchone()[0] == "real@x.com"                       # not overwritten


# ---- reports + subjects ----

def test_solo_report_has_one_subject(conn):
    uid = db_v2.create_or_get_user(conn, "+91", "9990000010")
    rid = db_v2.create_report(conn, uid, "marriage", {"teaser": "x"}, status="paid")
    db_v2.add_subject(conn, rid, "self", name="Aarav", gender="male",
                      dob="1996-07-14", tob="09:25", time_quality="T1",
                      birth_place="Jaipur", birth_lat=26.9124, birth_lon=75.7873, birth_tz=5.50)
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM report_subjects WHERE report_id=%s", (rid,))
        assert cur.fetchone()[0] == 1
    got = db_v2.get_report(conn, rid)
    assert got["status"] == "paid" and got["report_data"] == {"teaser": "x"}


def test_milan_report_has_two_subjects(conn):
    uid = db_v2.create_or_get_user(conn, "+91", "9990000011")
    rid = db_v2.create_report(conn, uid, "milan", {"total": 24}, status="paid")
    db_v2.add_subject(conn, rid, "self", name="A")
    db_v2.add_subject(conn, rid, "partner", name="B")
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM report_subjects WHERE report_id=%s", (rid,))
        assert cur.fetchone()[0] == 2


# ---- payments ----

def test_payment_create_then_capture(conn):
    uid = db_v2.create_or_get_user(conn, "+91", "9990000020")
    rid = db_v2.create_report(conn, uid, "marriage", {"t": 1})
    pid = db_v2.record_payment(conn, rid, uid, 49900, razorpay_order_id="order_x")
    db_v2.mark_payment_captured(conn, pid, razorpay_payment_id="pay_abc123def45678",
                                method="upi", upi_vpa="a@okhdfc", paid_at="2026-09-06 10:00:00")
    with conn.cursor() as cur:
        cur.execute("SELECT status, method, razorpay_payment_id FROM payments WHERE id=%s", (pid,))
        status, method, rzp = cur.fetchone()
    assert status == "captured" and method == "upi" and rzp == "pay_abc123def45678"


def test_repeat_payment_upsert_does_not_duplicate(conn):
    uid = db_v2.create_or_get_user(conn, "+91", "9990000021")
    rid = db_v2.create_report(conn, uid, "marriage", {"t": 1})
    db_v2.record_payment(conn, rid, uid, 49900, payment_id="pmt_fixed", status="created")
    db_v2.record_payment(conn, rid, uid, 49900, payment_id="pmt_fixed", status="captured")
    assert _count(conn, "payments") == 1                          # upsert, not a 2nd row


# ---- integrity (the whole point of the redesign) ----

def test_orphan_payment_is_rejected_by_fk(conn):
    uid = db_v2.create_or_get_user(conn, "+91", "9990000030")
    with pytest.raises(pymysql.err.IntegrityError):     # report_id points nowhere
        db_v2.record_payment(conn, "rep_does_not_exist", uid, 49900)


def test_orphan_subject_is_rejected_by_fk(conn):
    with pytest.raises(pymysql.err.IntegrityError):     # report_id points nowhere
        db_v2.add_subject(conn, "rep_nope", "self", name="X")
