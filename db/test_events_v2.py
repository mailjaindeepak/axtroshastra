"""
test_events_v2.py — tests for the first-party analytics backend (events_v2),
run against real MySQL. `conn` fixture is in conftest.py.

RUN (from repo root):
    DB_PASSWORD='<your local mysql password>' python3 -m pytest db/ -v
"""
import sys
from pathlib import Path

import pymysql
import pytest

sys.path.insert(0, str(Path(__file__).parent))
import db_v2      # noqa: E402
import events_v2  # noqa: E402


def test_page_view_creates_visitor_visit_and_event(conn):
    eid = events_v2.record_event(
        conn, visitor_id="vis_1", visit_id="vst_1", event_name="page_view",
        page_url="/", sequence=1,
        session={"utm_source": "instagram", "referrer": "instagram.com",
                 "landing_url": "/", "ga_client_id": "GA1.2.5"})
    assert eid
    with conn.cursor() as c:
        c.execute("SELECT COUNT(*) FROM visitors WHERE visitor_id='vis_1'")
        assert c.fetchone()[0] == 1
        c.execute("SELECT page_count, utm_source, ga_client_id FROM visit_sessions WHERE visit_id='vst_1'")
        assert c.fetchone() == (1, "instagram", "GA1.2.5")   # source + ga_client_id captured
        c.execute("SELECT COUNT(*) FROM events WHERE visitor_id='vis_1'")
        assert c.fetchone()[0] == 1


def test_second_page_view_bumps_page_count(conn):
    events_v2.record_event(conn, visitor_id="vis_2", visit_id="vst_2", event_name="page_view", page_url="/")
    events_v2.record_event(conn, visitor_id="vis_2", visit_id="vst_2", event_name="page_view", page_url="/about")
    with conn.cursor() as c:
        c.execute("SELECT page_count FROM visit_sessions WHERE visit_id='vst_2'")
        assert c.fetchone()[0] == 2
        c.execute("SELECT COUNT(*) FROM events WHERE visit_id='vst_2'")
        assert c.fetchone()[0] == 2


def test_first_touch_source_preserved(conn):
    events_v2.record_event(conn, visitor_id="vis_3", visit_id="vst_3a",
                           event_name="page_view", session={"utm_source": "instagram"})
    events_v2.record_event(conn, visitor_id="vis_3", visit_id="vst_3b",
                           event_name="page_view", session={"utm_source": "google"})
    with conn.cursor() as c:
        c.execute("SELECT first_utm_source FROM visitors WHERE visitor_id='vis_3'")
        assert c.fetchone()[0] == "instagram"        # first-touch kept on the visitor
        c.execute("SELECT utm_source FROM visit_sessions WHERE visit_id='vst_3b'")
        assert c.fetchone()[0] == "google"           # per-visit source still recorded


def test_identify_backfills_prior_anonymous_events(conn):
    events_v2.record_event(conn, visitor_id="vis_4", visit_id="vst_4", event_name="page_view")
    events_v2.record_event(conn, visitor_id="vis_4", visit_id="vst_4", event_name="form_start")
    uid = db_v2.create_or_get_user(conn, "+91", "9000000100")   # user born at lead
    events_v2.identify(conn, "vis_4", uid)
    with conn.cursor() as c:
        c.execute("SELECT user_id FROM visitors WHERE visitor_id='vis_4'")
        assert c.fetchone()[0] == uid
        c.execute("SELECT COUNT(*) FROM events WHERE visitor_id='vis_4' AND user_id=%s", (uid,))
        assert c.fetchone()[0] == 2                  # both earlier anon events now attributed
        c.execute("SELECT user_id FROM visit_sessions WHERE visit_id='vst_4'")
        assert c.fetchone()[0] == uid


def test_purchase_event_carries_value_and_report(conn):
    uid = db_v2.create_or_get_user(conn, "+91", "9000000101")
    rid = db_v2.create_report(conn, uid, "marriage", {"t": 1})
    events_v2.record_event(conn, visitor_id="vis_5", visit_id="vst_5", event_name="purchase",
                           user_id=uid, report_id=rid, value_paise=49900, currency="INR")
    with conn.cursor() as c:
        c.execute("SELECT value_paise, report_id FROM events WHERE event_name='purchase'")
        assert c.fetchone() == (49900, rid)


def test_unknown_event_name_rejected(conn):
    with pytest.raises(ValueError):
        events_v2.record_event(conn, visitor_id="vis_6", event_name="bogus")


def test_event_with_bad_report_id_rejected_by_fk(conn):
    with pytest.raises(pymysql.err.IntegrityError):
        events_v2.record_event(conn, visitor_id="vis_7", visit_id="vst_7",
                               event_name="generate_lead", report_id="rep_nope")
