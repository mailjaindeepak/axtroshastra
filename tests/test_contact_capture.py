"""T1-CONTACT: the pre-payment popup's contact must be captured server-side.

POST /api/order now carries `phone` (the buyer's WhatsApp/account number) and
`email` (optional, for the PDF copy). The backend must:
  * persist the normalised popup number into reports.user_phone,
  * store the popup email into meta._email (only when the report has none),
  * PREFER user_phone over the Razorpay payment contact when the webhook
    creates the account / picks the WhatsApp delivery number,
  * keep storing the Razorpay contact in reports.phone (the payment number),
  * create the account on the popup number even for free-pass unlocks
    (no webhook ever fires for those).

Razorpay creds are absent in tests, so order creation stubs api.rzp_client.
"""
import json

import api

# The signed-webhook helper now lives in tests/conftest.py as the `pay_webhook`
# fixture (shared with test_users / test_tracking).

KUNDLI = {"name": "Popup Tester", "dob": "1992-03-15", "tob": "11:40",
          "time_quality": "T0", "place": "Delhi", "gender": "female"}


def _new_report(client, **overrides):
    r = client.post("/api/kundli", json={**KUNDLI, **overrides})
    assert r.status_code == 200, r.text
    return r.json()["report_id"]


class _StubOrders:
    def create(self, payload):
        return {"id": "order_stub_1", "amount": payload["amount"]}


class _StubRzp:
    order = _StubOrders()


def _stub_rzp(monkeypatch):
    monkeypatch.setattr(api, "rzp_client", lambda: _StubRzp())


# ------------------------------------------------ /api/order persists contact
def test_order_persists_popup_phone_and_email(client, monkeypatch):
    rid = _new_report(client)
    _stub_rzp(monkeypatch)
    r = client.post("/api/order", json={"report_id": rid,
                                        "phone": "98765 00001",
                                        "email": "pdf@example.com"})
    assert r.status_code == 200, r.text
    assert r.json().get("razorpay_order_id") == "order_stub_1"
    with api.db() as c:
        row = c.execute("SELECT user_phone, payload FROM reports WHERE id=?",
                        (rid,)).fetchone()
    assert row[0] == "+919876500001"          # normalised popup number
    meta = json.loads(row[1])["meta"]
    assert meta["_email"] == "pdf@example.com"


def test_order_does_not_clobber_existing_form_email(client, monkeypatch):
    rid = _new_report(client, email="form@example.com")
    _stub_rzp(monkeypatch)
    client.post("/api/order", json={"report_id": rid,
                                    "phone": "9876500009",
                                    "email": "other@example.com"})
    with api.db() as c:
        row = c.execute("SELECT payload FROM reports WHERE id=?", (rid,)).fetchone()
    assert json.loads(row[0])["meta"]["_email"] == "form@example.com"


def test_order_without_contact_still_works(client, monkeypatch):
    """Legacy body ({report_id, pass}) must keep working unchanged."""
    rid = _new_report(client)
    _stub_rzp(monkeypatch)
    r = client.post("/api/order", json={"report_id": rid, "pass": None})
    assert r.status_code == 200, r.text
    assert r.json().get("razorpay_order_id") == "order_stub_1"
    with api.db() as c:
        row = c.execute("SELECT user_phone FROM reports WHERE id=?", (rid,)).fetchone()
    assert not row[0]                          # nothing invented


# --------------------------------------- webhook prefers the popup number
def test_webhook_prefers_popup_number_over_payment_contact(client, monkeypatch, pay_webhook):
    rid = _new_report(client)
    _stub_rzp(monkeypatch)
    client.post("/api/order", json={"report_id": rid, "phone": "9876500002"})
    # The customer pays from a DIFFERENT number — expected and fine.
    pay_webhook(client, rid, "pay_t1_1", "+911112223334")

    body = client.get(f"/api/report/{rid}").json()
    assert body["paid"] is True
    assert body["account"]["mobile"] == "+919876500002"   # account = popup number

    with api.db() as c:
        pay = c.execute("SELECT phone FROM reports WHERE id=?", (rid,)).fetchone()[0]
        um = c.execute("SELECT user_id FROM user_mobiles WHERE mobile=?",
                       ("+919876500002",)).fetchone()
    assert pay == "+911112223334"             # payment number kept verbatim
    assert um is not None                      # user keyed on the POPUP number

    # Banner: account mobile primary + muted "Payment via <payment number>" row.
    html = client.get(f"/report/{rid}").text
    assert "+91 98765 00002" in html
    assert "Payment" in html and "+91 11122 23334" in html


def test_webhook_falls_back_to_payment_contact(client, pay_webhook):
    """No popup number on file -> the Razorpay contact still creates the
    account (pre-popup behaviour, and the safety net if the popup is skipped)."""
    rid = _new_report(client)
    pay_webhook(client, rid, "pay_t1_2", "+919444455556")
    acct = client.get(f"/api/report/{rid}").json()["account"]
    assert acct["mobile"] == "+919444455556"


# -------------------------------------- milan report with no name (past crash)
def test_milan_webhook_without_name_does_not_crash(client, monkeypatch, pay_webhook):
    """A milan report's meta has p1/p2 but NO `name`. Indexing meta['name']
    crashed the webhook mid-way for every milan payment (paid got marked, but
    account creation / WhatsApp never ran). _display_name must yield 'P1 & P2'
    and the webhook must complete: paid + account created, no 500/KeyError."""
    monkeypatch.setattr(api, "_pregenerate_pdf_task", lambda rid: None)
    monkeypatch.setattr(api, "send_whatsapp_report", lambda *a, **k: None)

    rid = "r_milan_noname_1"
    api.save_report(rid, {"product": "milan",
                          "teaser": {"verdict": "ok"},
                          "meta": {"p1": "Asha", "p2": "Vikram"}})

    pay_webhook(client, rid, "pay_milan_1", "+919812300000", "couple@example.com")

    body = client.get(f"/api/report/{rid}").json()
    assert body["paid"] is True
    acct = body["account"]
    assert acct is not None                       # account created despite no name
    assert acct["mobile"] == "+919812300000"

    # the display name is the couple, not a crash
    assert api._display_name(
        {"product": "milan", "meta": {"p1": "Asha", "p2": "Vikram"}}) == "Asha & Vikram"


# --------------------------------------------------- free-pass unlock
def test_free_pass_creates_account_from_popup(client):
    rid = _new_report(client)
    tok = client.get("/api/make_pass?key=test-stats-key&n=1").json()["passes"][0]
    r = client.post("/api/order", json={"report_id": rid, "pass": tok,
                                        "phone": "+91 98765 00003",
                                        "email": "free@example.com"})
    assert r.json().get("free") is True
    body = client.get(f"/api/report/{rid}").json()
    assert body["paid"] is True
    acct = body["account"]
    assert acct is not None
    assert acct["mobile"] == "+919876500003"
    assert acct["email"] == "free@example.com"
