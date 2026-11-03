"""Pre-order mode: OFF unless the owner supplies the delivery promise and the refund page; never unlocks an incomplete
report; same verified payment as a normal order; every order can be fulfilled once its content is approved."""
import hashlib
import hmac
import itertools
import json
import re
from datetime import date

import pytest

import api
import db_v2
import mulank_content as mc
import mulank_fulfilment as mf
import mulank_payment as mp
import mulank_preorder as po
import numerology
import numerology_preview as P
import reports_v2

PIN = date(2026, 11, 3)
SECRET = "rzp_key_secret_preorder_test"
PROMISE = "within 7 days of your order"
_ph = itertools.count(1)


@pytest.fixture(autouse=True)
def pinned(monkeypatch):
    monkeypatch.setattr(mc, "_today", lambda: PIN)


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setenv("MULANK_PREORDER", "1")
    monkeypatch.setenv("MULANK_DELIVERY_PROMISE", PROMISE)
    monkeypatch.setenv("MULANK_REFUND_URL", "/refund")


def _btn(h, action):
    return re.findall(r"<(?:button|a)\b[^>]*data-action=\"%s\"" % action, h)


def _cards(h):
    return re.findall(r'<section class="page[^"]*">.*?</section>', h, re.S)


def _text(h):
    import html
    t = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", h, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))


class Rzp:
    def __init__(self):
        self.orders, self.entity = [], {}
        outer = self

        class order:
            @staticmethod
            def create(d):
                outer.orders.append(d)
                return {"id": "order_" + d["receipt"][-30:], "amount": d["amount"], "currency": d["currency"]}

            @staticmethod
            def payments(oid):
                return {"items": []}

        class payment:
            @staticmethod
            def fetch(pid):
                return dict(outer.entity)
        self.order, self.payment = order, payment


@pytest.fixture
def rz(monkeypatch):
    s = Rzp()
    monkeypatch.setattr(api, "RZP_SECRET", SECRET)
    monkeypatch.setattr(api, "RZP_KEY", "rzp_test_key")
    monkeypatch.setattr(api, "rzp_client", lambda: s)
    return s


@pytest.fixture
def pdfs(monkeypatch, tmp_path):
    import pdfgen
    monkeypatch.setattr(pdfgen, "PDF_DIR", str(tmp_path))
    seen = {"keys": []}

    def fake(key, html):
        seen["keys"].append(key)
        data = b"%PDF-1.4 preorder " + hashlib.sha256(html.encode()).digest() * 40
        pdfgen.save(key, data)
        return data
    monkeypatch.setattr(pdfgen, "get_or_generate", fake)
    return seen


@pytest.fixture(autouse=True)
def quiet(monkeypatch):
    sent = []
    for n in ("send_whatsapp_report", "email_report"):
        monkeypatch.setattr(api, n, lambda *a, **k: sent.append(a), raising=False)
    return sent


def _make(client, dob="29/07/1990", name="Priya Sharma"):
    r = client.post("/api/mulank", json={"name": name, "dob": dob, "country_code": "+91", "phone": "95%08d" % (10000000 + next(_ph)),
                                         "consent_terms": True})
    assert r.status_code == 200, r.text
    return r.json()["report_id"]


def _ent(oid, **kw):
    e = {"id": "pay_" + oid[-30:], "order_id": oid, "amount": 29900, "currency": "INR", "status": "captured", "method": "upi"}
    e.update(kw)
    return e


def _pay(client, rz, oid, **kw):
    rz.entity = _ent(oid, **kw)
    pid = rz.entity["id"]
    sig = hmac.new(SECRET.encode(), f"{oid}|{pid}".encode(), hashlib.sha256).hexdigest()
    return client.post("/api/mulank/verify", json={"razorpay_order_id": oid, "razorpay_payment_id": pid, "razorpay_signature": sig})


def _row(rid):
    conn = db_v2.get_conn()
    try:
        return reports_v2.read_report(conn, rid)
    finally:
        conn.close()


def _approve_2_1(monkeypatch):
    E = numerology.compute_mulank(29, 7, 1990, today=PIN)
    monkeypatch.setattr(mc, "REGISTRY", {k: mc.Entry(mc.OWNER_APPROVED, editor="Editor", approved_by="Owner", approved_on="2026-11-03")
                                         for k in mc.required_keys(E)})


# ------------------------------------------------------------------ configuration: closed unless everything is supplied
def test_preorder_is_off_by_default():
    assert po.config()["enabled"] is False


@pytest.mark.parametrize("env", [
    {"MULANK_PREORDER": "1"},                                                                             # no promise, no refund page
    {"MULANK_PREORDER": "1", "MULANK_DELIVERY_PROMISE": PROMISE},                                         # no refund page
    {"MULANK_PREORDER": "1", "MULANK_REFUND_URL": "/refund"},                                             # no promise
    {"MULANK_DELIVERY_PROMISE": PROMISE, "MULANK_REFUND_URL": "/refund"},                                 # switch off
    {"MULANK_PREORDER": "1", "MULANK_DELIVERY_PROMISE": PROMISE, "MULANK_REFUND_URL": "javascript:x"},    # unsafe link
    {"MULANK_PREORDER": "1", "MULANK_DELIVERY_PROMISE": PROMISE, "MULANK_REFUND_URL": "//evil.test/x"},
    {"MULANK_PREORDER": "1", "MULANK_DELIVERY_PROMISE": "instantly after you pay", "MULANK_REFUND_URL": "/refund"},
    {"MULANK_PREORDER": "1", "MULANK_DELIVERY_PROMISE": "<b>soon</b> maybe", "MULANK_REFUND_URL": "/refund"},
    {"MULANK_PREORDER": "1", "MULANK_DELIVERY_PROMISE": "x", "MULANK_REFUND_URL": "/refund"},
])
def test_preorder_stays_closed_unless_every_value_is_present_and_safe(monkeypatch, env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    assert po.config()["enabled"] is False


def test_preorder_opens_only_with_promise_and_refund_page(on):
    c = po.config()
    assert c["enabled"] and c["promise"] == PROMISE and c["refund_url"] == "/refund" and len(c["version"]) == 8


# ------------------------------------------------------------------ the preview
def test_disabled_preorder_leaves_the_unavailable_preview_untouched(client):
    t = client.get(f"/en/numerology/preview/{_make(client)}").text
    assert "not ready for your numbers yet" in t and "₹" not in _text(t) and "preorder" not in t.lower().replace("pre-order", "")
    assert not _btn(t, "preorder")


def test_enabled_preorder_page_is_clearly_labelled_and_never_says_instant(client, on):
    t = client.get(f"/en/numerology/preview/{_make(client)}").text
    cards = _cards(t)
    assert len(cards) == 5
    p4, p5 = _text(cards[3]), _text(cards[4])
    assert "Pre-order Your Complete Report" in p4 and "₹299" in p4 and PROMISE in p4
    assert "This is a pre-order, not an instant download" in p4 and 'href="/refund"' in cards[3]
    assert "₹499" not in p4 and "You save" not in p4 and "Unlock" not in p4 and "Unlock" not in p5
    assert _btn(cards[3], "preorder") and not _btn(t, "checkout")
    assert "Pre-order My Report for ₹299" in p4 and "Pre-order My Report" in p5 and "What Your Report Will Include" in p5
    assert "/api/mulank/preorder" in t and 'id="vwBar"' in t and "Pre-order" in _text(t[t.index('id="vwBar"'):])
    for bad in ("download now", "instant access", "unlock"):
        assert bad not in _text(t).lower().replace("not an instant download", "")


def test_preorder_pages_are_identical_for_every_pair_and_escape_the_promise(client, monkeypatch):
    monkeypatch.setenv("MULANK_PREORDER", "1")
    monkeypatch.setenv("MULANK_DELIVERY_PROMISE", "within 5 days & a bit")
    monkeypatch.setenv("MULANK_REFUND_URL", "/refund")
    seen = []
    for dob in ("29/07/1990", "15/03/1985", "22/11/2000", "09/09/1999"):
        cards = _cards(client.get(f"/en/numerology/preview/{_make(client, dob)}").text)
        seen.append(cards[2:])
    assert all(s == seen[0] for s in seen)
    assert "within 5 days &amp; a bit" in seen[0][1]


def test_a_sellable_pair_gets_the_normal_purchase_page_even_when_preorder_is_on(client, on, monkeypatch):
    _approve_2_1(monkeypatch)
    t = client.get(f"/en/numerology/preview/{_make(client)}").text
    assert _btn(t, "checkout") and not _btn(t, "preorder") and "₹499" in _text(_cards(t)[3])
    assert "Pre-order Your" not in t


# ------------------------------------------------------------------ the order and the payment
def test_preorder_endpoint_is_closed_unless_enabled(client, rz):
    rid = _make(client)
    r = client.post("/api/mulank/preorder", json={"report_id": rid})
    assert r.status_code == 409 and r.json()["detail"] == "preorder_closed" and rz.orders == []


def test_a_sellable_pair_cannot_use_the_preorder_route(client, rz, on, monkeypatch):
    _approve_2_1(monkeypatch)
    rid = _make(client)
    r = client.post("/api/mulank/preorder", json={"report_id": rid})
    assert r.status_code == 409 and r.json()["detail"] == "use_order" and rz.orders == []


def test_preorder_creates_a_fixed_price_order_and_snapshots_the_promise(client, rz, on):
    rid = _make(client)
    r = client.post("/api/mulank/preorder", json={"report_id": rid, "amount": 1, "currency": "USD"})
    assert r.status_code == 200
    assert r.json()["amount"] == 29900 and r.json()["currency"] == "INR" and rz.orders[0]["amount"] == 29900
    assert rz.orders[0]["notes"]["preorder"] == "1"
    snap = po.get(_row(rid)["payload"])
    assert snap["promise"] == PROMISE and snap["refund_url"] == "/refund" and snap["at"] and snap["version"] == po.config()["version"]
    assert client.post("/api/mulank/order", json={"report_id": rid}).status_code == 409        # the normal route stays closed to it


def test_preorder_is_refused_for_other_products_and_unknown_reports(client, rz, on):
    assert client.post("/api/mulank/preorder", json={"report_id": "nope1234567"}).status_code == 404
    assert client.post("/api/mulank/preorder", json={}).status_code == 404 and rz.orders == []


def test_paid_preorder_records_the_payment_but_unlocks_nothing(client, rz, on, pdfs, quiet):
    rid = _make(client)
    oid = client.post("/api/mulank/preorder", json={"report_id": rid}).json()["razorpay_order_id"]
    r = _pay(client, rz, oid)
    assert r.status_code == 200 and r.json()["ok"] is True and _row(rid)["paid"]
    page = client.get(f"/en/numerology/report/{rid}")
    assert page.status_code == 200 and len(_cards(page.text)) == 0
    t = _text(page.text)
    assert "Pre-order received" in t and "This is not an instant download" in t and PROMISE in t and "Download PDF" not in t
    assert 'href=\'/refund\'' in page.text or 'href="/refund"' in page.text
    assert client.get(f"/en/numerology/report/{rid}.pdf").status_code == 503 and pdfs["keys"] == []
    assert mf.get_state(_row(rid)["payload"])["status"] == mf.AWAITING
    assert quiet == []
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 404 and client.post("/api/order", json={"report_id": rid}).status_code == 404


def test_preorder_payment_goes_through_the_same_verification(client, rz, on):
    for kw in ({"amount": 100}, {"currency": "USD"}, {"status": "authorized"}, {"status": "failed"}):
        rid = _make(client)
        oid = client.post("/api/mulank/preorder", json={"report_id": rid}).json()["razorpay_order_id"]
        _pay(client, rz, oid, **kw)
        assert not _row(rid)["paid"], kw


def test_duplicate_callbacks_do_not_double_record_a_preorder(client, rz, on, pdfs):
    rid = _make(client)
    oid = client.post("/api/mulank/preorder", json={"report_id": rid}).json()["razorpay_order_id"]
    for _ in range(3):
        assert _pay(client, rz, oid).status_code == 200
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*), SUM(status='captured') FROM payments WHERE report_id=%s", (rid,))
            assert cur.fetchone() == (1, 1)
    finally:
        conn.close()


# ------------------------------------------------------------------ fulfilment once the content is approved
def test_a_preorder_is_fulfilled_when_its_content_becomes_approved_and_complete(client, rz, on, pdfs, monkeypatch):
    rid = _make(client)                                                                 # pair 2-1: complete text, nothing approved yet
    oid = client.post("/api/mulank/preorder", json={"report_id": rid}).json()["razorpay_order_id"]
    assert _pay(client, rz, oid).status_code == 200
    assert client.get(f"/en/numerology/report/{rid}.pdf").status_code == 503
    h = {"X-Stats-Key": api.STATS_KEY}
    first = client.get("/api/mulank/admin/orders", headers=h).json()
    assert first["counts"] == {"awaiting_content": 1} or first["counts"].get("awaiting_content", 0) >= 1
    mine = [o for o in first["orders"] if o["pair"] == "2-1" and o["state"] == "awaiting_content"]
    assert mine and not any(o["can_fulfil_now"] for o in mine)
    _approve_2_1(monkeypatch)                                                           # the owner approves the content
    nxt = client.get("/api/mulank/admin/orders", headers=h).json()
    assert any(o["can_fulfil_now"] for o in nxt["orders"] if o["pair"] == "2-1")
    done = client.post("/api/mulank/admin/fulfil", headers=h).json()
    assert done["attempted"] >= 1 and done["results"].get("ready", 0) >= 1
    page = client.get(f"/en/numerology/report/{rid}")
    assert len(_cards(page.text)) == 15 and "Priya Sharma" in page.text and "Download PDF" in page.text
    assert client.get(f"/en/numerology/report/{rid}.pdf").status_code == 200
    again = client.post("/api/mulank/admin/fulfil", headers=h).json()                      # idempotent: a ready order is not re-fulfilled
    assert again["results"].get("ready", 0) == 0
    assert client.post("/api/mulank/order", json={"report_id": rid}).json() == {"already_paid": True}


def test_the_customer_can_check_again_and_gets_the_report_once_it_is_ready(client, rz, on, pdfs, monkeypatch):
    rid = _make(client)
    oid = client.post("/api/mulank/preorder", json={"report_id": rid}).json()["razorpay_order_id"]
    _pay(client, rz, oid)
    assert client.post(f"/api/mulank/report/{rid}/retry").json() == {"status": "awaiting_content"}
    _approve_2_1(monkeypatch)
    assert client.post(f"/api/mulank/report/{rid}/retry").json() == {"status": "ready"}


def test_admin_endpoints_need_the_key_and_return_no_personal_data(client, rz, on):
    rid = _make(client, name="Zelda Quartermain")
    oid = client.post("/api/mulank/preorder", json={"report_id": rid}).json()["razorpay_order_id"]
    _pay(client, rz, oid)
    assert client.get("/api/mulank/admin/orders").status_code == 403
    assert client.get("/api/mulank/admin/orders", headers={"X-Stats-Key": "wrong"}).status_code == 403
    assert client.post("/api/mulank/admin/fulfil", headers={"X-Stats-Key": "wrong"}).status_code == 403
    r = client.get("/api/mulank/admin/orders", headers={"X-Stats-Key": api.STATS_KEY})
    assert r.status_code == 200
    body = r.text
    for secret in ("Zelda", "Quartermain", rid, "1990", "9510"):
        assert secret not in body
    assert set(r.json()["orders"][0]) == {"n", "paid_at", "pair", "preorder", "state", "can_fulfil_now"}


def test_admin_is_disabled_when_no_key_is_configured(client, monkeypatch):
    monkeypatch.setattr(api, "STATS_KEY", "")
    assert client.get("/api/mulank/admin/orders", headers={"X-Stats-Key": ""}).status_code == 503


# ------------------------------------------------------------------ PDF cache, landing notice, nav
def test_preview_pdf_cache_key_changes_with_the_promise(client, monkeypatch, pdfs):
    monkeypatch.setenv("MULANK_PREORDER", "1")
    monkeypatch.setenv("MULANK_REFUND_URL", "/refund")
    rid = _make(client)
    monkeypatch.setenv("MULANK_DELIVERY_PROMISE", "within 7 days of your order")
    assert client.get(f"/en/numerology/preview/{rid}.pdf").status_code == 200
    monkeypatch.setenv("MULANK_DELIVERY_PROMISE", "within 10 days of your order")
    assert client.get(f"/en/numerology/preview/{rid}.pdf").status_code == 200
    k1, k2 = pdfs["keys"][-2:]
    assert k1.startswith("pvp") and k2.startswith("pvp") and k1 != k2 and k1 != rid


def test_preview_pdf_links_use_absolute_urls_and_state_the_promise(client, on, monkeypatch, tmp_path):
    fitz = pytest.importorskip("pymupdf")
    import pdfgen
    monkeypatch.setattr(pdfgen, "PDF_DIR", str(tmp_path))
    r = client.get(f"/en/numerology/preview/{_make(client)}.pdf")
    if r.status_code == 503:
        pytest.skip("headless Chrome not available")
    doc = fitz.open(stream=r.content, filetype="pdf")
    assert len(doc) == 5
    txt = doc[3].get_text()
    assert "Pre-order Your Complete Report" in txt and "not an instant download" in txt and PROMISE in txt.replace("\n", " ")
    uris = [l["uri"] for q in (doc[3], doc[4]) for l in q.get_links() if l.get("uri")]
    assert uris and all(u.startswith("https://") for u in uris)


def test_landing_notice_mentions_the_preorder_and_promise_only_when_enabled(client, on):
    h = client.get("/en/numerology").text
    assert "pre-order for ₹299" in h and PROMISE in h and "nothing to buy" not in h


def test_landing_without_preorder_still_says_nothing_to_buy(client):
    assert "nothing to buy on this page" in client.get("/en/numerology").text


def test_nav_entry_is_off_unless_the_owner_enables_it(client, monkeypatch):
    assert "Numerology Report" not in api._nav_html("en")
    monkeypatch.setenv("NAV_NUMEROLOGY", "1")
    nav = api._nav_html("en")
    assert 'href="/en/numerology"' in nav and "Numerology Report" in nav and nav.index("Celebrity") < nav.index("Numerology Report") < nav.index("Login")
    assert "Numerology Report" not in api._nav_html("hi")
    assert "Numerology Report" in client.get("/en/iq-test").text
