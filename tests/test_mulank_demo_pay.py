"""Numerology through /api/_demo_pay/{report_id} (DEMO_MODE only), and the playbook gaps closed with it.

Owner decision (14 Nov 2026): locally there are no Razorpay Test Mode keys, so Numerology unlocks through demo pay, like every other product in development and in
tests/e2e/checkout.spec.js. What must stay true:
  * same eligibility rule as a real purchase (an incomplete pair is refused);
  * a demo unlock is never a sale: no payment row, no server Purchase, no WhatsApp message to the number on the report, the page fires no Purchase event;
  * the route exists only in DEMO_MODE, and DEMO_MODE cannot stay on in production (tests/test_demo_guard.py);
and the playbook gaps: a proper product name and icon, the account page opening the Numerology report, the shared /report/... addresses sending a Numerology
report to its own page, and the admin refund route working on a Numerology payment."""
import hashlib
import hmac
import itertools
import re

import pytest

import api
import auth
import db_v2
import mulank_content as mc
import mulank_fulfilment
import mulank_payment as mp
import mulank_routes
import numerology
import payments
import pdfgen
import reports_v2
import tracking

SECRET = "rzp_key_secret_demo_pay_test"
_seq = itertools.count(1)


# ------------------------------------------------------------------ fixtures and helpers
class Stub:
    def __init__(self):
        self.entity = None
        stub = self

        class order:
            @staticmethod
            def create(d):
                return {"id": "order_" + d["receipt"], "amount": d["amount"], "currency": d["currency"]}

        class payment:
            @staticmethod
            def fetch(pid):
                return dict(stub.entity)
        self.order, self.payment = order, payment


@pytest.fixture
def rz(monkeypatch):
    s = Stub()
    monkeypatch.setattr(api, "RZP_SECRET", SECRET)
    monkeypatch.setattr(api, "rzp_client", lambda: s)
    return s


@pytest.fixture
def eligible(monkeypatch):
    d = numerology.compute_mulank(29, 7, 1990, today=mc._today())
    monkeypatch.setattr(mc, "REGISTRY", {k: mc.Entry(mc.VERIFIED, "Test Reviewer", "2026-11-03") for k in mc.required_keys(d)})


@pytest.fixture
def fulfilled(monkeypatch):
    """Fulfilment would render a PDF with Chrome; record the call instead."""
    calls = []
    monkeypatch.setattr(mulank_fulfilment, "run_fulfilment", lambda rid: calls.append(rid) or {"status": "ready"})
    return calls


@pytest.fixture
def vendors(monkeypatch):
    sent = []
    monkeypatch.setattr(tracking, "_post_json", lambda url, payload, headers=None: (sent.append(url) or (200, "{}")))
    for name, val in dict(META_CAPI_TOKEN="m", GA4_API_SECRET="g", LINKEDIN_CAPI_TOKEN="l", LINKEDIN_CONV_PURCHASE_CAPI="1", OAIQ_CAPI_TOKEN="o", X_PIXEL_TOKEN="x").items():
        monkeypatch.setattr(tracking, name, val)
    return sent


def _lead(client):
    phone = "97%08d" % (82000000 + next(_seq))
    r = client.post("/api/mulank", json={"name": "Priya Sharma", "dob": "29/07/1990", "gender": "female", "country_code": "+91", "phone": phone,
                                         "consent_terms": True, "marketing_optin": False})
    assert r.status_code == 200, r.text
    return r.json()["report_id"], phone


def _rec(rid):
    conn = db_v2.get_conn()
    try:
        return reports_v2.read_report(conn, rid)
    finally:
        conn.close()


def _payment_rows(rid):
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT status, amount_paise, method FROM payments WHERE report_id=%s", (rid,))
            return cur.fetchall()
    finally:
        conn.close()


def _pay_for_real(client, rz, rid):
    """The real path: server order, signed verification, 'captured' payment."""
    oid = client.post("/api/mulank/order", json={"report_id": rid}).json()["razorpay_order_id"]
    pid = "pay_demo" + oid[-24:]
    rz.entity = {"id": pid, "order_id": oid, "amount": 29900, "currency": "INR", "status": "captured", "method": "upi", "contact": "+919800000000"}
    sig = hmac.new(SECRET.encode(), f"{oid}|{pid}".encode(), hashlib.sha256).hexdigest()
    r = client.post("/api/mulank/verify", json={"razorpay_order_id": oid, "razorpay_payment_id": pid, "razorpay_signature": sig})
    assert r.status_code == 200 and r.json()["status"] == "paid", r.text
    return pid


# ------------------------------------------------------------------ demo pay unlocks Numerology, as it does every other product
def test_demo_pay_unlocks_a_numerology_report_and_is_never_a_payment(client, eligible, fulfilled):
    rid, _ = _lead(client)
    assert not _rec(rid)["paid"]
    r = client.post(f"/api/_demo_pay/{rid}")
    assert r.status_code == 200 and r.json() == {"ok": True}
    rec = _rec(rid)
    assert rec["paid"] and mp.is_demo_unlock(rec["payload"])
    assert list(_payment_rows(rid)) == []                                       # no payment row, so no dashboard or revenue figure can count it
    assert fulfilled == [rid]                                                    # the PDF is prepared, as for a real purchase


def test_demo_pay_twice_does_nothing_the_second_time(client, eligible, fulfilled):
    rid, _ = _lead(client)
    assert client.post(f"/api/_demo_pay/{rid}").json() == {"ok": True}
    assert client.post(f"/api/_demo_pay/{rid}").json() == {"ok": True, "already_paid": True}
    assert fulfilled == [rid]


def test_demo_pay_keeps_numerologys_eligibility_rule(client, monkeypatch, fulfilled):
    monkeypatch.setattr(mc, "REGISTRY", {})                                      # nothing approved for these numbers
    rid, _ = _lead(client)
    r = client.post(f"/api/_demo_pay/{rid}")
    assert r.status_code == 409 and r.json()["detail"] == "not_available"
    assert not _rec(rid)["paid"] and fulfilled == []
    assert client.post("/api/_demo_pay/no-such-report").status_code == 404


def test_demo_pay_does_not_touch_other_products(client):
    rid = client.post("/api/kundli", json={"name": "Guard Buyer", "dob": "1990-05-10", "tob": "09:20", "time_quality": "T0", "place": "Delhi",
                                           "gender": "male"}).json()["report_id"]
    assert client.post(f"/api/_demo_pay/{rid}").json() == {"ok": True} and _rec(rid)["paid"]


def test_the_paid_numerology_report_is_served_after_demo_pay(client, eligible, fulfilled):
    rid, _ = _lead(client)
    assert client.get(f"/en/numerology/report/{rid}", follow_redirects=False).status_code == 302          # unpaid: back to the preview
    client.post(f"/api/_demo_pay/{rid}")
    frag = client.get(f"/en/numerology/report/{rid}?fragment=1")
    assert frag.status_code == 200 and len(re.findall(r'<section class="page', frag.json()["html"])) == 15
    page = client.get(f"/en/numerology/report/{rid}")
    assert page.status_code == 200 and "Priya Sharma" in page.text and page.headers["cache-control"] == "no-store"


# ------------------------------------------------------------------ a demo unlock is never a sale
def test_a_demo_unlock_sends_no_purchase_to_any_platform_but_a_real_payment_does(client, rz, eligible, fulfilled, vendors):
    demo, _ = _lead(client)
    client.post(f"/api/_demo_pay/{demo}")
    assert vendors == [] and mulank_tracking_run(demo) is False
    real, _ = _lead(client)
    _pay_for_real(client, rz, real)
    assert len(vendors) == 5                                                     # control: the same setup does report a real payment


def mulank_tracking_run(rid):
    import mulank_tracking
    return mulank_tracking.run(rid)


def test_a_demo_unlock_never_messages_the_number_on_the_report_but_a_real_payment_does(client, rz, eligible, monkeypatch):
    sent = []
    monkeypatch.setattr(mulank_fulfilment, "_send_wa", lambda phone, name, link: sent.append((phone, link)))
    monkeypatch.setattr(pdfgen, "get_cached", lambda rid: b"%PDF-1.4 cached")     # skip rendering: this test is about the message
    for name, val in (("TWILIO_SID", "sid"), ("TWILIO_TOKEN", "tok"), ("TWILIO_FROM", "whatsapp:+10000000000"), ("TWILIO_CONTENT_SID_TEXT", "HX1"),
                      ("PUBLIC_BASE_URL", "https://example.test")):
        monkeypatch.setattr(api, name, val)
    demo, _ = _lead(client)
    client.post(f"/api/_demo_pay/{demo}")                                         # the real fulfilment runs after the response
    assert mulank_fulfilment.get_state(_rec(demo)["payload"]).get("status") == "ready" and sent == []
    real, _ = _lead(client)
    _pay_for_real(client, rz, real)
    assert len(sent) == 1 and sent[0][1].endswith(f"/en/numerology/report/{real}")


def test_the_state_says_whether_a_paid_report_was_a_real_sale(client, rz, eligible, fulfilled):
    """The page fires its browser Purchase event only when `real` is true."""
    demo, _ = _lead(client)
    client.post(f"/api/_demo_pay/{demo}")
    assert client.get(f"/api/mulank/state/{demo}").json() == {"paid": True, "real": False}
    real, _ = _lead(client)
    _pay_for_real(client, rz, real)
    assert client.get(f"/api/mulank/state/{real}").json() == {"paid": True, "real": True}
    unpaid, _ = _lead(client)
    assert client.get(f"/api/mulank/state/{unpaid}").json()["paid"] is False


# ------------------------------------------------------------------ playbook gaps
def test_the_product_has_a_proper_name_and_its_own_icon():
    assert api.PRODUCT_LABEL["numerology_mulank"] == "Numerology Report"
    assert api.PRODUCT_SVG["numerology_mulank"] != api.PRODUCT_SVG["marriage"] and "<svg" in api.PRODUCT_SVG["numerology_mulank"]


def _login(client, mobile):
    code = client.post("/api/auth/request-otp", json={"mobile": mobile}).json()["dev_code"]
    assert client.post("/api/auth/verify-otp", json={"mobile": mobile, "code": code}).status_code == 200


def test_the_account_page_names_and_opens_a_numerology_report_correctly(client, eligible, fulfilled):
    rid, phone = _lead(client)
    client.post(f"/api/_demo_pay/{rid}")
    _login(client, phone)
    page = client.get("/account").text
    assert "Numerology Report" in page
    assert f'href="/en/numerology/report/{rid}"' in page and f'href="/report/{rid}"' not in page      # its own report page, not the shared renderer
    assert api.PRODUCT_SVG["numerology_mulank"] in page and api.PRODUCT_SVG["marriage"] not in page
    client.post("/api/auth/logout")


def test_the_shared_report_addresses_send_a_numerology_report_to_its_own_pages(client, eligible, fulfilled):
    rid, _ = _lead(client)
    assert client.get(f"/report/{rid}", follow_redirects=False).status_code == 404                  # unpaid: nothing, as for every product
    client.post(f"/api/_demo_pay/{rid}")
    r = client.get(f"/report/{rid}", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == f"/en/numerology/report/{rid}"
    for path in (f"/report/{rid}.pdf", f"/report/{rid}/pdf"):
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 302 and r.headers["location"] == f"/en/numerology/report/{rid}.pdf"
    other = client.post("/api/kundli", json={"name": "Guard Buyer", "dob": "1990-05-10", "tob": "09:20", "time_quality": "T0", "place": "Delhi",
                                             "gender": "male"}).json()["report_id"]
    client.post(f"/api/_demo_pay/{other}")
    assert client.get(f"/report/{other}", follow_redirects=False).status_code == 200                  # other products are unchanged


def test_the_admin_refund_route_works_on_a_numerology_payment(client, rz, eligible, fulfilled, monkeypatch):
    rid, _ = _lead(client)
    pid = _pay_for_real(client, rz, rid)
    monkeypatch.setattr(api, "STATS_KEY", "refund-test-key")

    class _Refund:
        class payment:
            @staticmethod
            def refund(payment_id, data):
                assert payment_id == pid and data == {}
                return {"id": "rfnd_demo1", "amount": 29900, "status": "processed"}
    monkeypatch.setattr(payments, "_rzp", lambda: _Refund())
    assert client.post(f"/api/refund?key=wrong&payment_id={pid}").status_code == 403
    r = client.post(f"/api/refund?key=refund-test-key&payment_id={pid}")
    assert r.status_code == 200 and r.json()["status"] == "processed"
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT rf.amount_paise, rf.status FROM refunds rf JOIN payments p ON p.id = rf.payment_id WHERE p.razorpay_payment_id=%s", (pid,))
            assert cur.fetchone() == (29900, "processed")                        # recorded against the Numerology payment
    finally:
        conn.close()
