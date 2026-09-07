"""Account layer: a real (HMAC-signed) Razorpay payment.captured webhook must
create a user from the payment's mobile + email, link the report to that user,
and surface the saved details back to the buyer. Also guards mobile de-dupe
(two purchases from one number => one account) and that non-Razorpay unlocks
(demo/free-pass) create no account."""
import users

# The signed-webhook helper now lives in tests/conftest.py as the `pay_webhook`
# fixture (shared with test_contact_capture / test_tracking).

KUNDLI = {"name": "Login Tester", "dob": "1990-05-10", "tob": "09:20",
          "time_quality": "T0", "place": "Delhi", "gender": "male"}


def _new_report(client, **overrides):
    r = client.post("/api/kundli", json={**KUNDLI, **overrides})
    assert r.status_code == 200, r.text
    return r.json()["report_id"]


def test_webhook_creates_and_links_account(client, pay_webhook):
    rid = _new_report(client)
    pay_webhook(client, rid, "pay_acc_1", "+919812345678", "buyer@example.com")

    body = client.get(f"/api/report/{rid}").json()
    assert body["paid"] is True
    acct = body["account"]
    assert acct is not None
    assert acct["mobile"] == "+919812345678"
    assert acct["email"] == "buyer@example.com"

    # The "Account created" banner CARD is gone from the paid report page —
    # the saved details are no longer rendered inline. Only the auto-hiding
    # toast (JS snippet, localStorage-guarded) remains, armed via __HASACCT__.
    html = client.get(f"/report/{rid}").text
    assert "acct-banner" not in html
    assert "Saved from this purchase" not in html
    assert "+91 98123 45678" not in html
    assert "buyer@example.com" not in html
    assert "axs_acct_toast_" in html               # toast snippet present
    assert 'hasAcct=("1"==="1")' in html           # toast armed: account exists


def test_bare_ten_digit_mobile_is_normalised(client, pay_webhook):
    rid = _new_report(client)
    pay_webhook(client, rid, "pay_acc_2", "9800011122", email=None)
    acct = client.get(f"/api/report/{rid}").json()["account"]
    assert acct["mobile"] == "+919800011122"


def test_same_mobile_two_reports_one_account(client, pay_webhook):
    rid1 = _new_report(client)
    rid2 = _new_report(client)
    pay_webhook(client, rid1, "pay_acc_3", "+919900099000", "one@example.com")
    pay_webhook(client, rid2, "pay_acc_4", "+919900099000")  # no email this time

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


def test_backfill_is_a_safe_noop_in_v2(client):
    """v2: users are attached at form-fill / order / OTP login, so there are no
    paid-but-unlinked reports to sweep — backfill is an idempotent no-op. It stays
    as an endpoint so the admin URL keeps responding (see users.backfill)."""
    r = client.get("/api/backfill_users?key=test-stats-key")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["linked"] == 0
    assert body["scanned"] == 0


def test_backfill_requires_admin_key(client):
    assert client.get("/api/backfill_users").status_code == 403
    assert client.get("/api/backfill_users?key=wrong").status_code == 403


def test_norm_mobile_unit():
    assert users._norm_mobile("+91 98120-45678") == "+919812045678"
    assert users._norm_mobile("9812345678") == "+919812345678"
    assert users._norm_mobile("098-1234-5678") == "+919812345678"
    assert users._norm_mobile("") == ""
