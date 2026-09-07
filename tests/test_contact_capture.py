"""T1-CONTACT: the pre-payment popup's contact must be captured server-side.

POST /api/order carries `phone` (the buyer's WhatsApp/account number) and `email`
(optional, for the PDF copy). v2 behaviour:
  * the normalised popup number becomes the report's linked USER (attach_user) —
    this is the delivery/account number the webhook must PREFER over Razorpay's,
  * the popup email is stored on that user account,
  * the Razorpay payment contact is kept on the payment row (payments.payment_contact),
    never used for delivery (CLAUDE.md §1),
  * a v2 payment REQUIRES a user (payments.user_id NOT NULL), so an order/free-pass
    with NO contact is rejected with 400 contact_required (the popup number is a
    mandatory field; this replaces v1's silent "no contact still works" path).

Razorpay creds are absent in tests, so order creation stubs api.rzp_client. The
signed-webhook helper is the shared `pay_webhook` fixture in conftest.py.
"""
import api
import db_v2

KUNDLI = {"name": "Popup Tester", "dob": "1992-03-15", "tob": "11:40",
          "time_quality": "T0", "place": "Delhi", "gender": "female"}

MILAN = {"p1_name": "Priya", "p1_dob": "1996-01-20", "p1_tob": "14:00",
         "p1_place": "Mumbai",
         "p2_name": "Ravi", "p2_dob": "1995-08-15", "p2_tob": "10:30",
         "p2_place": "Delhi"}


def _new_report(client, **overrides):
    r = client.post("/api/kundli", json={**KUNDLI, **overrides})
    assert r.status_code == 200, r.text
    return r.json()["report_id"]


class _StubOrders:
    def create(self, payload):
        # Unique per report (receipt=rid). A FIXED id collides across the shared
        # test DB: the webhook's capture looks payments up by razorpay_order_id and
        # would hit another test's row (real Razorpay order ids are unique).
        return {"id": "order_" + payload["receipt"], "amount": payload["amount"]}


class _StubRzp:
    order = _StubOrders()


def _stub_rzp(monkeypatch):
    monkeypatch.setattr(api, "rzp_client", lambda: _StubRzp())


# --------------------------------------------------------- v2 DB peek helpers
def _user_of(rid):
    """The user linked to a report as {mobile(+CC), email, name}, or None."""
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT u.country_code, u.mobile, u.email, u.name FROM reports r "
                        "JOIN users u ON u.id = r.user_id WHERE r.id=%s", (rid,))
            row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return {"mobile": f"{row[0] or ''}{row[1] or ''}", "email": row[2], "name": row[3]}


def _meta_email(rid):
    conn = db_v2.get_conn()
    try:
        rec = db_v2.get_report(conn, rid)
    finally:
        conn.close()
    return ((rec.get("report_data") or {}).get("meta") or {}).get("_email")


def _payment_contact(rid):
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT payment_contact FROM payments WHERE report_id=%s "
                        "ORDER BY created_at DESC LIMIT 1", (rid,))
            row = cur.fetchone()
    finally:
        conn.close()
    return (row[0] if row else None)


# ------------------------------------------------ /api/order persists contact
def test_order_persists_popup_phone_and_email(client, monkeypatch):
    rid = _new_report(client)
    _stub_rzp(monkeypatch)
    r = client.post("/api/order", json={"report_id": rid,
                                        "phone": "98765 00001",
                                        "email": "pdf@example.com"})
    assert r.status_code == 200, r.text
    assert r.json().get("razorpay_order_id")      # a real (unique) order id was returned
    u = _user_of(rid)
    assert u is not None
    assert u["mobile"] == "+919876500001"        # normalised popup number
    assert u["email"] == "pdf@example.com"        # v2: popup email on the account


def test_kundli_form_phone_creates_account_at_submit(client, monkeypatch):
    """Lead-at-submit for the MAIN-FORM kundli funnels (marriage-v2/v3, business-growth):
    they send `phone` to /api/kundli, so the account is created + linked at REPORT
    CREATION (like milan), not only at checkout — capturing the lead even if the
    visitor never pays. Checkout then needs no phone (no contact_required)."""
    r = client.post("/api/kundli", json={**KUNDLI, "phone": "98765 00042"})
    assert r.status_code == 200, r.text
    rid = r.json()["report_id"]
    u = _user_of(rid)
    assert u is not None
    assert u["mobile"] == "+919876500042"        # account created at SUBMIT

    _stub_rzp(monkeypatch)
    o = client.post("/api/order", json={"report_id": rid})   # no phone in the body
    assert o.status_code == 200, o.text
    assert o.json().get("razorpay_order_id")     # succeeds — the user is already attached


def test_kundli_without_phone_stays_unattached(client):
    """Popup funnels omit `phone` on /api/kundli -> user_id stays NULL at create
    (attached later at /api/order via the popup). Unchanged behaviour."""
    rid = _new_report(client)                     # KUNDLI has no phone
    assert _user_of(rid) is None


# ------------------------------------------------ /api/milan captures WhatsApp
def test_milan_form_captures_whatsapp_number(client):
    r = client.post("/api/milan", json={**MILAN, "whatsapp": "98765 00002"})
    assert r.status_code == 200, r.text
    rid = r.json()["report_id"]
    assert _user_of(rid)["mobile"] == "+919876500002"   # normalised, same as popup path


def test_milan_form_without_whatsapp_still_works(client):
    """whatsapp stays optional -- callers that don't send it must not break; no
    user is attached (attached later at order)."""
    r = client.post("/api/milan", json=MILAN)
    assert r.status_code == 200, r.text
    rid = r.json()["report_id"]
    assert _user_of(rid) is None


def test_milan_form_bad_whatsapp_never_breaks_report_creation(client):
    """A value the client-side check should have caught (too short) must never
    crash report creation server-side, whatever split_phone does with it --
    the real gate is the form's own axNormPhone() validation before submit."""
    r = client.post("/api/milan", json={**MILAN, "whatsapp": "123"})
    assert r.status_code == 200, r.text


def test_order_does_not_clobber_existing_form_email(client, monkeypatch):
    """The email captured on the report body (meta._email, from the form) is left
    untouched by a later /api/order — the order email lands on the user account,
    not the report body."""
    rid = _new_report(client, email="form@example.com")
    _stub_rzp(monkeypatch)
    client.post("/api/order", json={"report_id": rid,
                                    "phone": "9876500009",
                                    "email": "other@example.com"})
    assert _meta_email(rid) == "form@example.com"


def test_order_without_contact_requires_contact(client, monkeypatch):
    """v2: a payment needs a user (payments.user_id NOT NULL). An order with no
    popup contact is rejected up front rather than hitting a DB constraint. (v1
    let a contactless legacy body through; the popup number is mandatory now.)"""
    rid = _new_report(client)
    _stub_rzp(monkeypatch)
    r = client.post("/api/order", json={"report_id": rid, "pass": None})
    assert r.status_code == 400
    assert r.json()["detail"] == "contact_required"
    assert _user_of(rid) is None                 # nothing invented


# --------------------------------------- webhook prefers the popup number
def test_webhook_prefers_popup_number_over_payment_contact(client, monkeypatch, pay_webhook):
    rid = _new_report(client)
    _stub_rzp(monkeypatch)
    o = client.post("/api/order", json={"report_id": rid, "phone": "9876500022"})
    oid = o.json()["razorpay_order_id"]
    # The customer pays from a DIFFERENT number — expected and fine. Carry order_id
    # (as a real Razorpay webhook does) so the capture updates the one payment row.
    pay_webhook(client, rid, "pay_t1_1", "+911112223334", order_id=oid)

    body = client.get(f"/api/report/{rid}").json()
    assert body["paid"] is True
    assert body["account"]["mobile"] == "+919876500022"   # account = popup number

    assert _payment_contact(rid) == "+911112223334"       # payment number kept verbatim
    assert _user_of(rid)["mobile"] == "+919876500022"     # user keyed on the POPUP number

    # The account banner card is gone: neither the account mobile nor the
    # payment number is rendered on the report page any more.
    html = client.get(f"/report/{rid}").text
    assert "acct-banner" not in html
    assert "+91 98765 00022" not in html
    assert "+91 11122 23334" not in html


def test_webhook_account_email_prefers_popup_over_payment(client, monkeypatch, pay_webhook):
    """The ACCOUNT email must be the POPUP email, not the Razorpay/transaction
    email. When the two differ, the account keeps the popup email."""
    rid = _new_report(client)
    _stub_rzp(monkeypatch)
    o = client.post("/api/order", json={"report_id": rid,
                                        "phone": "9876500007",
                                        "email": "popup@example.com"})
    oid = o.json()["razorpay_order_id"]
    # Razorpay reports a DIFFERENT contact email for the transaction.
    pay_webhook(client, rid, "pay_email_1", "+911112223334",
                email="razorpay@example.com", order_id=oid)

    acct = client.get(f"/api/report/{rid}").json()["account"]
    assert acct is not None
    assert acct["email"] == "popup@example.com"    # account = POPUP email
    assert acct["email"] != "razorpay@example.com"


def test_webhook_falls_back_to_payment_contact(client, pay_webhook):
    """No popup number on file -> the Razorpay contact still creates the account
    (the safety net if the popup is skipped / a pre-popup orphan)."""
    rid = _new_report(client)
    pay_webhook(client, rid, "pay_t1_2", "+919444455556")
    acct = client.get(f"/api/report/{rid}").json()["account"]
    assert acct["mobile"] == "+919444455556"


# -------------------------------------- milan report with no name (past crash)
def test_milan_webhook_without_name_does_not_crash(client, monkeypatch, pay_webhook):
    """A milan report's meta has p1/p2 but NO top-level `name`. The webhook must
    complete: paid + account created, no 500/KeyError; _display_name yields the
    couple string."""
    monkeypatch.setattr(api, "_pregenerate_pdf_task", lambda rid: None)
    monkeypatch.setattr(api, "send_whatsapp_report", lambda *a, **k: None)

    rid = client.post("/api/milan", json=MILAN).json()["report_id"]  # no whatsapp -> orphan
    pay_webhook(client, rid, "pay_milan_1", "+919812300000", "couple@example.com")

    body = client.get(f"/api/report/{rid}").json()
    assert body["paid"] is True
    acct = body["account"]
    assert acct is not None                       # account created despite no name
    assert acct["mobile"] == "+919812300000"      # orphan fallback: Razorpay contact

    # the display name is the couple, not a crash
    assert api._display_name(
        {"product": "milan", "meta": {"p1": "Asha", "p2": "Vikram"}}) == "Asha & Vikram"


# -------------------------------- account is NOT auto-named from the report
def test_webhook_does_not_auto_name_account_from_report(client, monkeypatch, pay_webhook):
    """A milan report's display name is a COUPLE ("A & B") — wrong as a person's
    account name. Payment must create the account with a BLANK name; the user sets
    it later on /account."""
    monkeypatch.setattr(api, "_pregenerate_pdf_task", lambda rid: None)
    monkeypatch.setattr(api, "send_whatsapp_report", lambda *a, **k: None)
    rid = client.post("/api/milan", json=MILAN).json()["report_id"]
    pay_webhook(client, rid, "pay_noname_1", "+919812311111")

    acct = client.get(f"/api/report/{rid}").json()["account"]
    assert acct is not None
    assert not acct.get("name")                    # blank, NOT "Priya & Ravi"


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


# ------------------------------- free-pass unlock delivers WhatsApp too
def _record_delivery(monkeypatch):
    """Stub the two delivery tasks with recorders. TestClient executes FastAPI
    background tasks before the response returns, so calls are visible
    synchronously after client.post()."""
    wa_calls, pdf_calls = [], []
    monkeypatch.setattr(api, "send_whatsapp_report",
                        lambda *a, **k: wa_calls.append((a, k)))
    monkeypatch.setattr(api, "_pregenerate_pdf_task",
                        lambda rid: pdf_calls.append(rid))
    return wa_calls, pdf_calls


def test_free_pass_sends_whatsapp_like_paid_path(client, monkeypatch):
    """Pass redemption must trigger the SAME WhatsApp delivery a payment does:
    PDF pregeneration first, then send_whatsapp_report with the normalised popup
    number, the rid, the display name and the product."""
    wa_calls, pdf_calls = _record_delivery(monkeypatch)
    rid = _new_report(client)
    tok = client.get("/api/make_pass?key=test-stats-key&n=1").json()["passes"][0]
    r = client.post("/api/order", json={"report_id": rid, "pass": tok,
                                        "phone": "98765 00013"})
    assert r.json().get("free") is True
    assert pdf_calls == [rid]                       # PDF cached before the send
    assert len(wa_calls) == 1
    args, _ = wa_calls[0]
    assert args[0] == "+919876500013"               # normalised popup number
    assert args[1] == rid
    assert args[2] == "Popup Tester"                # _display_name(payload)
    assert args[3] == "marriage"                    # product


def test_free_pass_whatsapp_sent_exactly_once(client, monkeypatch):
    """Idempotency: retrying the unlocked report -> already_paid, and reusing the
    burnt pass on another report -> invalid_pass. Neither re-sends."""
    wa_calls, _ = _record_delivery(monkeypatch)
    rid1 = _new_report(client)
    tok = client.get("/api/make_pass?key=test-stats-key&n=1").json()["passes"][0]
    assert client.post("/api/order", json={"report_id": rid1, "pass": tok,
                                           "phone": "9876500014"}
                       ).json().get("free") is True
    assert len(wa_calls) == 1
    # same rid retried (double-click / reload) -> short-circuits on paid
    r2 = client.post("/api/order", json={"report_id": rid1, "pass": tok,
                                         "phone": "9876500014"})
    assert r2.json().get("already_paid") is True
    # burnt pass on a fresh report -> invalid, nothing delivered
    rid2 = _new_report(client)
    r3 = client.post("/api/order", json={"report_id": rid2, "pass": tok,
                                         "phone": "9876500015"})
    assert r3.json().get("error") == "invalid_pass"
    assert len(wa_calls) == 1                       # still exactly one send


def test_free_pass_without_phone_requires_contact(client, monkeypatch):
    """v2: a free-pass unlock also needs a contact (the account/delivery number).
    With no popup phone the unlock is rejected up front (contact_required), rather
    than v1's "unlock succeeds, WhatsApp skipped" headless path."""
    wa_calls, pdf_calls = _record_delivery(monkeypatch)
    rid = _new_report(client)
    tok = client.get("/api/make_pass?key=test-stats-key&n=1").json()["passes"][0]
    r = client.post("/api/order", json={"report_id": rid, "pass": tok})
    assert r.status_code == 400
    assert r.json()["detail"] == "contact_required"
    assert client.get(f"/api/report/{rid}").json()["paid"] is False
    assert wa_calls == [] and pdf_calls == []
