"""Account layer: a real (HMAC-signed) Razorpay payment.captured webhook must
create a user from the payment's mobile + email, link the report to that user,
and surface the saved details back to the buyer. Also guards mobile de-dupe
(two purchases from one number => one account) and that non-Razorpay unlocks
(demo/free-pass) create no account."""
import hashlib
import hmac
import json

import users

WEBHOOK_SECRET = b"test-webhook-secret"   # matches conftest's RAZORPAY_WEBHOOK_SECRET

KUNDLI = {"name": "Login Tester", "dob": "1990-05-10", "tob": "09:20",
          "time_quality": "T0", "place": "Delhi", "gender": "male"}


def _new_report(client, **overrides):
    r = client.post("/api/kundli", json={**KUNDLI, **overrides})
    assert r.status_code == 200, r.text
    return r.json()["report_id"]


def _pay_webhook(client, rid, payment_id, contact, email=None):
    ent = {"id": payment_id, "contact": contact, "notes": {"report_id": rid}}
    if email is not None:
        ent["email"] = email
    event = {"event": "payment.captured",
             "payload": {"payment": {"entity": ent}}}
    body = json.dumps(event).encode()
    sig = hmac.new(WEBHOOK_SECRET, body, hashlib.sha256).hexdigest()
    r = client.post("/api/webhook", content=body,
                    headers={"X-Razorpay-Signature": sig})
    assert r.status_code == 200, r.text
    return r.json()


def test_webhook_creates_and_links_account(client):
    rid = _new_report(client)
    _pay_webhook(client, rid, "pay_acc_1", "+919812345678", "buyer@example.com")

    body = client.get(f"/api/report/{rid}").json()
    assert body["paid"] is True
    acct = body["account"]
    assert acct is not None
    assert acct["mobile"] == "+919812345678"
    assert acct["email"] == "buyer@example.com"

    # The saved details are shown on the paid report page (banner: "Account
    # created" with the mobile formatted as +91 XXXXX XXXXX).
    html = client.get(f"/report/{rid}").text
    assert "+91 98123 45678" in html
    assert "buyer@example.com" in html
    assert "account created" in html.lower()


def test_bare_ten_digit_mobile_is_normalised(client):
    rid = _new_report(client)
    _pay_webhook(client, rid, "pay_acc_2", "9800011122", email=None)
    acct = client.get(f"/api/report/{rid}").json()["account"]
    assert acct["mobile"] == "+919800011122"


def test_same_mobile_two_reports_one_account(client):
    rid1 = _new_report(client)
    rid2 = _new_report(client)
    _pay_webhook(client, rid1, "pay_acc_3", "+919900099000", "one@example.com")
    _pay_webhook(client, rid2, "pay_acc_4", "+919900099000")  # no email this time

    a1 = client.get(f"/api/report/{rid1}").json()["account"]
    a2 = client.get(f"/api/report/{rid2}").json()["account"]
    assert a1["id"] == a2["id"]                 # de-duped to a single user
    assert a2["email"] == "one@example.com"     # earlier email preserved, not blanked


def test_demo_pay_creates_no_account(client):
    """Free/demo unlocks have no mobile or email, so no account is created."""
    rid = _new_report(client)
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    body = client.get(f"/api/report/{rid}").json()
    assert body["paid"] is True
    assert body["account"] is None


def test_backfill_links_prepaid_reports(client):
    """A report paid before the accounts code existed (paid + phone, no user_id)
    gets an account created and linked by the backfill endpoint, and is then shown
    to the user like any webhook-created account."""
    import api
    rid = _new_report(client)
    with api.db() as c:   # simulate an old, pre-accounts paid report
        c.execute("UPDATE reports SET paid=1, payment_id='pay_old', "
                  "phone='+919650973345' WHERE id=?", (rid,))

    r = client.get("/api/backfill_users?key=test-stats-key")
    assert r.status_code == 200, r.text
    assert r.json()["linked"] >= 1

    acct = client.get(f"/api/report/{rid}").json()["account"]
    assert acct is not None and acct["mobile"] == "+919650973345"
    # re-running is a no-op for already-linked rows
    assert client.get("/api/backfill_users?key=test-stats-key").json()["linked"] == 0


def test_backfill_requires_admin_key(client):
    assert client.get("/api/backfill_users").status_code == 403
    assert client.get("/api/backfill_users?key=wrong").status_code == 403


def test_norm_mobile_unit():
    assert users._norm_mobile("+91 98120-45678") == "+919812045678"
    assert users._norm_mobile("9812345678") == "+919812345678"
    assert users._norm_mobile("098-1234-5678") == "+919812345678"
    assert users._norm_mobile("") == ""
