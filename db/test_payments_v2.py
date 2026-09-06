"""
test_payments_v2.py — tests for the payment flows (record order, capture with the
idempotency guards, free-pass redemption), run against real MySQL. `conn` fixture
is in conftest.py.

RUN (from repo root):
    DB_PASSWORD='<your local mysql password>' python3 -m pytest db/ -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import db_v2       # noqa: E402
import payments_v2  # noqa: E402


def _user_and_report(conn, mobile):
    uid = db_v2.create_or_get_user(conn, "+91", mobile)
    rid = db_v2.create_report(conn, uid, "marriage", {"t": 1})
    return uid, rid


def test_record_order_creates_created_payment(conn):
    uid, rid = _user_and_report(conn, "9000000001")
    pid = payments_v2.record_order(conn, rid, uid, 49900, "order_1")
    with conn.cursor() as c:
        c.execute("SELECT status, razorpay_order_id FROM payments WHERE id=%s", (pid,))
        assert c.fetchone() == ("created", "order_1")


def test_capture_marks_paid_and_delivers_once(conn):
    uid, rid = _user_and_report(conn, "9000000002")
    payments_v2.record_order(conn, rid, uid, 49900, "order_2")
    won = payments_v2.capture_payment(
        conn, report_id=rid, amount_paise=49900, razorpay_order_id="order_2",
        razorpay_payment_id="pay_realid12345678", event_id="evt_1",
        method="upi", upi_vpa="a@okhdfc", payment_contact="9999999999")
    assert won is True
    with conn.cursor() as c:
        c.execute("SELECT status FROM reports WHERE id=%s", (rid,))
        assert c.fetchone()[0] == "paid"
        c.execute("SELECT status, method, razorpay_payment_id FROM payments "
                  "WHERE razorpay_order_id=%s", ("order_2",))
        assert c.fetchone() == ("captured", "upi", "pay_realid12345678")


def test_duplicate_webhook_event_not_redelivered(conn):
    uid, rid = _user_and_report(conn, "9000000003")
    payments_v2.record_order(conn, rid, uid, 49900, "order_3")
    a = payments_v2.capture_payment(conn, report_id=rid, amount_paise=49900,
                                    razorpay_order_id="order_3",
                                    razorpay_payment_id="pay_x1", event_id="evt_dup")
    b = payments_v2.capture_payment(conn, report_id=rid, amount_paise=49900,
                                    razorpay_order_id="order_3",
                                    razorpay_payment_id="pay_x1", event_id="evt_dup")
    assert a is True and b is False        # same event id → 2nd is ignored


def test_webhook_then_verify_delivers_once(conn):
    uid, rid = _user_and_report(conn, "9000000004")
    payments_v2.record_order(conn, rid, uid, 49900, "order_4")
    webhook = payments_v2.capture_payment(conn, report_id=rid, amount_paise=49900,
                                          razorpay_order_id="order_4",
                                          razorpay_payment_id="pay_y1", event_id="evt_w")
    verify = payments_v2.capture_payment(conn, report_id=rid, amount_paise=49900,
                                         razorpay_order_id="order_4",
                                         razorpay_payment_id="pay_y1", event_id=None)
    assert webhook is True and verify is False   # report already paid → verify won't re-deliver


def test_redeem_free_pass(conn):
    uid, rid = _user_and_report(conn, "9000000005")
    with conn.cursor() as c:
        c.execute("INSERT INTO passes(token, used) VALUES('PASS1', 0)")
    assert payments_v2.redeem_free_pass(conn, token="PASS1", report_id=rid, user_id=uid) is True
    with conn.cursor() as c:
        c.execute("SELECT status FROM reports WHERE id=%s", (rid,))
        assert c.fetchone()[0] == "paid"
        c.execute("SELECT used, used_by_payment_id FROM passes WHERE token='PASS1'")
        used, pmt = c.fetchone()
        assert used == 1 and pmt is not None
        c.execute("SELECT amount_paise, method, status FROM payments WHERE id=%s", (pmt,))
        assert c.fetchone() == (0, "free_pass", "captured")


def test_redeem_used_pass_returns_false(conn):
    uid, rid = _user_and_report(conn, "9000000006")
    with conn.cursor() as c:
        c.execute("INSERT INTO passes(token, used) VALUES('PASS2', 1)")   # already used
    assert payments_v2.redeem_free_pass(conn, token="PASS2", report_id=rid, user_id=uid) is False


def test_redeem_invalid_pass_returns_false(conn):
    uid, rid = _user_and_report(conn, "9000000007")
    assert payments_v2.redeem_free_pass(conn, token="NOPE", report_id=rid, user_id=uid) is False
