"""Round-trip test for the v2-migrated auth.py (OTP via login_otps.msisdn + sessions
via login_sessions). Uses the dev OTP provider so no external calls are made.

Imports auth (-> users/db_v2/flows_v2, NO api). auth.* open their own v2 connection,
so we point DB_NAME at the throwaway test DB conftest builds.

Run: DB_PASSWORD='<local>' python3 -m pytest db/test_auth_v2.py -v
"""
import os

import pytest

import auth

TEST_DB = os.getenv("DBV2_TEST_NAME", "axtroshastra_v2_test")


@pytest.fixture
def db_env(conn, monkeypatch):
    monkeypatch.setenv("DB_NAME", TEST_DB)      # auth.* internal get_conn() -> test DB
    monkeypatch.setenv("OTP_PROVIDER", "dev")   # self-managed code, no external call
    monkeypatch.setenv("DEMO_MODE", "1")        # dev_send returns the code so we can verify
    yield conn


def test_dev_otp_then_login_and_session(db_env):
    mobile = "+919000012345"
    sent = auth.send_otp(None, mobile)
    assert sent["ok"] and sent.get("dev_code")          # dev code surfaced in DEMO_MODE
    code = sent["dev_code"]
    # the OTP row landed under msisdn (v2 column), not `mobile`.
    # rollback() first: refresh this conn's REPEATABLE-READ snapshot so it sees rows
    # the separate auth.* connections committed.
    db_env.rollback()
    with db_env.cursor() as c:
        c.execute("SELECT COUNT(*) FROM login_otps WHERE msisdn=%s", (mobile,))
        assert c.fetchone()[0] == 1

    assert auth.check_otp(None, mobile, "000000") is False   # wrong code -> attempt++
    assert auth.check_otp(None, mobile, code) is True        # right code -> consumed
    db_env.rollback()
    with db_env.cursor() as c:
        c.execute("SELECT COUNT(*) FROM login_otps WHERE msisdn=%s", (mobile,))
        assert c.fetchone()[0] == 0                          # single-use: row gone

    # login = verify + upsert account + mint session
    again = auth.send_otp(None, mobile)
    token, user = auth.login(None, mobile, again["dev_code"])
    assert token and user and user["mobile"] == mobile      # user created on the number

    # a valid session resolves to that user; destroy invalidates it
    assert auth.user_for_session(None, token)["id"] == user["id"]
    db_env.rollback()
    with db_env.cursor() as c:
        c.execute("SELECT COUNT(*) FROM login_sessions WHERE token=%s", (token,))
        assert c.fetchone()[0] == 1
    auth.destroy_session(None, token)
    assert auth.user_for_session(None, token) is None


def test_expired_session_is_rejected(db_env):
    # insert a user + an already-expired session directly, then look it up
    uid = __import__("users").upsert_user_from_payment(None, "+919111122223")
    with db_env.cursor() as c:
        c.execute("INSERT INTO login_sessions(token, user_id, expires_at) "
                  "VALUES('s_expired', %s, DATE_SUB(NOW(), INTERVAL 1 DAY))", (uid,))
    db_env.commit()
    assert auth.user_for_session(None, "s_expired") is None   # expired -> None (and purged)
    with db_env.cursor() as c:
        c.execute("SELECT COUNT(*) FROM login_sessions WHERE token='s_expired'")
        assert c.fetchone()[0] == 0
