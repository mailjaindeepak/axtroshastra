"""Round-trip tests for the v2-migrated users.py account layer.

Imports users (-> db_v2/flows_v2/dbcompat, NO api, so no .env/RDS). users.* open
their own v2 connection via db_v2.get_conn(), which reads DB_NAME — so we point
DB_NAME at the throwaway test DB that conftest's `conn` fixture builds+loads.

Run: DB_PASSWORD='<local>' python3 -m pytest db/test_users_v2.py -v
"""
import json
import os

import pytest

import users

TEST_DB = os.getenv("DBV2_TEST_NAME", "axtroshastra_v2_test")


@pytest.fixture
def db_env(conn):                       # `conn` (conftest) builds + loads TEST_DB
    old = os.environ.get("DB_NAME")
    os.environ["DB_NAME"] = TEST_DB     # so users.* internal get_conn() hits the test DB
    yield conn
    if old is None:
        os.environ.pop("DB_NAME", None)
    else:
        os.environ["DB_NAME"] = old


def _insert_report(cur, rid, *, user_id=None, status="paid", data=None):
    cur.execute("INSERT INTO reports(id,user_id,product,lang,status,report_data) "
                "VALUES(%s,%s,'marriage','en',%s,%s)",
                (rid, user_id, status, json.dumps(data) if data is not None else None))


def test_upsert_get_name_and_reports_roundtrip(db_env):
    uid = users.upsert_user_from_payment(None, "+91 98765 43210", email="buyer@x.com")
    assert uid
    assert users.upsert_user_from_payment(None, "9876543210") == uid   # dedup, same user
    u = users.get_user(None, uid)
    assert u["mobile"] == "+919876543210"      # reassembled +CC number
    assert u["email"] == "buyer@x.com"
    assert u["city"] is None                   # v2 has no city column
    assert users.set_user_name(None, uid, "Asha J")
    assert users.get_user(None, uid)["name"] == "Asha J"
    # only PAID reports show; a preview one does not
    with db_env.cursor() as c:
        _insert_report(c, "rep_paid", user_id=uid, status="paid", data={"meta": {"name": "Asha"}})
        _insert_report(c, "rep_prev", user_id=uid, status="preview", data={})
        _insert_report(c, "rep_link", user_id=None, status="paid", data={})
    db_env.commit()
    reps = users.get_user_reports(None, uid)
    assert [r["id"] for r in reps] == ["rep_paid"]
    assert reps[0]["product"] == "marriage" and reps[0]["subject"] == "Asha"
    # link_report attaches an owner after the fact
    users.link_report(None, "rep_link", uid)
    assert users.get_user_for_report(None, "rep_link")["id"] == uid


def test_missing_lookups_return_none(db_env):
    with db_env.cursor() as c:
        _insert_report(c, "rep_noone", user_id=None, status="paid", data={})
    db_env.commit()
    assert users.get_user_for_report(None, "rep_noone") is None   # paid but unlinked
    assert users.get_user(None, "u_missing") is None


def test_backfill_is_obsolete_noop(db_env):
    out = users.backfill(None)
    assert out["linked"] == 0 and "obsolete" in out["note"]
