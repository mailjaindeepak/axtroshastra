"""
test_flows_v2.py — tests for the "report + lead" flow (flows_v2.submit_report),
run against real MySQL. The `conn` fixture lives in conftest.py.

RUN (from repo root):
    DB_PASSWORD='<your local mysql password>' python3 -m pytest db/ -v
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import flows_v2  # noqa: E402


def test_submit_solo_creates_user_report_and_one_subject(conn):
    rid, uid = flows_v2.submit_report(
        conn, product="marriage", phone="+91 98765 43210",
        report_data={"teaser": "x"},
        subjects=[{"role": "self", "name": "Aarav", "gender": "male",
                   "dob": "1996-07-14", "tob": "09:25", "time_quality": "T1",
                   "birth_place": "Jaipur", "birth_lat": 26.9124,
                   "birth_lon": 75.7873, "birth_tz": 5.50}])
    with conn.cursor() as c:
        c.execute("SELECT country_code, mobile FROM users WHERE id=%s", (uid,))
        assert c.fetchone() == ("+91", "9876543210")          # user born at lead, phone split
        c.execute("SELECT user_id, status FROM reports WHERE id=%s", (rid,))
        assert c.fetchone() == (uid, "preview")                # report linked, preview
        c.execute("SELECT COUNT(*) FROM report_subjects WHERE report_id=%s", (rid,))
        assert c.fetchone()[0] == 1


def test_submit_milan_creates_two_subjects(conn):
    rid, _ = flows_v2.submit_report(
        conn, product="milan", phone="9990001111",
        report_data={"total": 24},
        subjects=[{"role": "self", "name": "A"}, {"role": "partner", "name": "B"}])
    with conn.cursor() as c:
        c.execute("SELECT COUNT(*) FROM report_subjects WHERE report_id=%s", (rid,))
        assert c.fetchone()[0] == 2


def test_submit_dedupes_user_across_two_reports(conn):
    r1, u1 = flows_v2.submit_report(conn, product="marriage", phone="+919998887777",
                                    report_data={}, subjects=[{"role": "self", "name": "X"}])
    r2, u2 = flows_v2.submit_report(conn, product="marriage", phone="+91 99988 87777",
                                    report_data={}, subjects=[{"role": "self", "name": "Y"}])
    assert u1 == u2 and r1 != r2       # same person (even formatted differently), two reports
    with conn.cursor() as c:
        c.execute("SELECT COUNT(*) FROM users")
        assert c.fetchone()[0] == 1
        c.execute("SELECT COUNT(*) FROM reports")
        assert c.fetchone()[0] == 2


def test_submit_drops_void_email(conn):
    _, uid = flows_v2.submit_report(conn, product="marriage", phone="+919000000001",
                                    report_data={}, email="void@razorpay.com",
                                    subjects=[{"role": "self", "name": "X"}])
    with conn.cursor() as c:
        c.execute("SELECT email FROM users WHERE id=%s", (uid,))
        assert c.fetchone()[0] is None      # sentinel stored as NULL, not as data


def test_submit_rejects_bad_phone(conn):
    with pytest.raises(ValueError):
        flows_v2.submit_report(conn, product="marriage", phone="123",
                               report_data={}, subjects=[{"role": "self", "name": "X"}])
