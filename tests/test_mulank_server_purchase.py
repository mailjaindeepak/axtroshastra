"""R2: server-side Purchase and ad attribution for a paid Mulank report.

What this pins down (NUMEROLOGY-REMEDIATION-SPEC.md R2, FUNNEL-EVENTS-CONTRACT.md, decision C3):
  * one event id, "mk_" + 16 hex of SHA-256(report id), identical in Python and in the page's JavaScript;
  * a verified payment sends ONE server Purchase to each of Meta, GA4, LinkedIn, OpenAI and X, however many times
    verify / webhook / recovery repeat;
  * nothing private reaches a vendor: no raw report id, no private path, no name, date of birth or raw phone number;
  * a free-pass unlock sends nothing; an unpaid or foreign report sends nothing;
  * ad-click context is stored at order time and used by the server Purchase;
  * every other product's Purchase payloads are unchanged (the new `source_url` argument defaults to the old value);
  * the first-party events table accepts the hashed id (it is not a reports.id).
Razorpay and every vendor call are stubbed; the database is the real throwaway MySQL from conftest."""
import hashlib
import itertools
import json
import os
import re
from pathlib import Path

import pytest

import api
import db_v2
import events_v2
import mulank_content as mc
import mulank_fulfilment
import mulank_payment as mp
import mulank_tracking
import numerology
import payments_v2
import reports_v2
import tracking

SECRET = "rzp_key_secret_mulank_purchase"
DOB_FORM, DOB_ISO, NAME = "29/07/1990", "1990-07-29", "Priya Sharma"
_seq = itertools.count(1)
PAGE = Path(__file__).resolve().parent.parent / "pages" / "numerology.html"


# ------------------------------------------------------------------ fixtures and helpers
class Stub:
    """Razorpay client double."""
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
def no_pdf(monkeypatch):
    """Fulfilment would render a PDF; this file is about tracking, so it does nothing."""
    monkeypatch.setattr(mulank_fulfilment, "run_fulfilment", lambda rid: {"status": "ready"})


@pytest.fixture
def vendors(monkeypatch):
    """Every vendor destination configured; the network call is captured instead of made."""
    sent = []
    monkeypatch.setattr(tracking, "_post_json", lambda url, payload, headers=None: (sent.append((url, payload, headers)) or (200, "{}")))
    for name, val in dict(META_CAPI_TOKEN="meta-token", GA4_API_SECRET="ga4-secret", LINKEDIN_CAPI_TOKEN="li-token",
                          LINKEDIN_CONV_PURCHASE_CAPI="4242", OAIQ_CAPI_TOKEN="oaiq-token", X_PIXEL_TOKEN="x-token").items():
        monkeypatch.setattr(tracking, name, val)
    return sent


def _lead(client):
    phone = "98%08d" % (60000000 + next(_seq))
    r = client.post("/api/mulank", json={"name": NAME, "dob": DOB_FORM, "gender": "female", "country_code": "+91", "phone": phone,
                                         "consent_terms": True, "marketing_optin": False})
    assert r.status_code == 200, r.text
    return r.json()["report_id"], phone


def _order(client, rid, **extra):
    r = client.post("/api/mulank/order", json={"report_id": rid, **extra},
                    headers={"Cookie": "ax_li_fat=LIFAT-abc123; ax_twclid=TWCLID-xyz789", "User-Agent": "TestBrowser/1.0"})
    assert r.status_code == 200, r.text
    return r.json()["razorpay_order_id"]


def _ent(oid, **kw):
    e = {"id": "pay_" + oid[-30:], "order_id": oid, "amount": 29900, "currency": "INR", "status": "captured", "method": "upi",
         "contact": "+919800000000", "email": "buyer@example.com"}
    e.update(kw)
    return e


def _verify(client, rz, oid):
    import hmac
    ent = _ent(oid)
    rz.entity = ent
    sig = hmac.new(SECRET.encode(), f"{oid}|{ent['id']}".encode(), hashlib.sha256).hexdigest()
    return client.post("/api/mulank/verify", json={"razorpay_order_id": oid, "razorpay_payment_id": ent["id"], "razorpay_signature": sig})


def _by_host(sent):
    out = {}
    for url, payload, _h in sent:
        for host in ("graph.facebook.com", "google-analytics.com", "api.linkedin.com", "bzr.openai.com", "ads-api.x.com"):
            if host in url:
                out[host] = (url, payload)
    return out


def _meta_of(rid):
    conn = db_v2.get_conn()
    try:
        return (reports_v2.read_report(conn, rid)["payload"].get("meta") or {})
    finally:
        conn.close()


# ------------------------------------------------------------------ the event id
def test_event_id_has_a_fixed_known_value_and_shape():
    assert mp.numerology_event_id("abc") == "mk_ba7816bf8f01cfea"          # first 16 hex of the well-known SHA-256("abc")
    rid = "Zk3_-pQ9wXyA1b2C"
    eid = mp.numerology_event_id(rid)
    assert re.fullmatch(r"mk_[0-9a-f]{16}", eid) and rid not in eid
    assert mp.numerology_event_id(rid) == eid and mp.numerology_event_id(rid + "x") != eid


def test_the_page_computes_the_same_event_id_as_the_server():
    """Browser and server must produce one value or the two copies of a Purchase never deduplicate. Run the page's own evId() in Chrome."""
    chrome = next((p for p in (os.getenv("CHROME_BIN", ""), r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                               r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", "/usr/bin/google-chrome", "/usr/bin/chromium")
                   if p and os.path.exists(p)), None)
    if not chrome:
        pytest.skip("no Chrome available (set CHROME_BIN)")
    from playwright import sync_api
    src = next(line.strip() for line in PAGE.read_text(encoding="utf-8").splitlines() if "function evId()" in line)
    rids = ["abc", "Zk3_-pQ9wXyA1b2C", "EHQdLgGulL95PS8r"]
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chrome, headless=True)
        page = browser.new_page()
        page.route("**/*", lambda route: route.fulfill(status=200, content_type="text/html", body="<html><body></body></html>"))
        page.goto("http://127.0.0.1:9/")                     # a secure context, so crypto.subtle exists
        for rid in rids:
            got = page.evaluate("async ([src, rid]) => { const f = new Function('RID', src + '; return evId();'); return await f(rid); }", [src, rid])
            assert got == mp.numerology_event_id(rid)
        browser.close()


# ------------------------------------------------------------------ attribution at order
def test_order_stores_ad_click_context_for_the_server_purchase(client, rz, eligible):
    rid, _ = _lead(client)
    _order(client, rid, fbc="fb.1.1700000000.AbCdEf", fbp="fb.1.1700000000.123456")
    m = _meta_of(rid)
    assert m["_fbc"] == "fb.1.1700000000.AbCdEf" and m["_fbp"] == "fb.1.1700000000.123456"
    assert m["_li_fat_id"] == "LIFAT-abc123" and m["_twclid"] == "TWCLID-xyz789"
    assert m["_ua"] == "TestBrowser/1.0" and m["_ip"]


def test_order_without_click_context_still_works_and_stores_only_what_exists(client, rz, eligible):
    rid, _ = _lead(client)
    r = client.post("/api/mulank/order", json={"report_id": rid})
    assert r.status_code == 200 and r.json()["amount"] == mp.MULANK_PRICE_PAISE
    m = _meta_of(rid)
    assert "_fbc" not in m and "_fbp" not in m and "_twclid" not in m


def test_attribution_is_not_stored_on_another_products_report_or_an_unknown_id(client, rz, eligible):
    conn = db_v2.get_conn()
    try:
        other = "ot%030d" % next(_seq)
        reports_v2.save_report(conn, other, {"product": "marriage", "dob": DOB_ISO, "meta": {}}, [], product="marriage",
                               phone="98%08d" % (61000000 + next(_seq)))
        conn.commit()
    finally:
        conn.close()
    assert client.post("/api/mulank/order", json={"report_id": other, "fbc": "fb.1.1.x"}).status_code == 404
    assert client.post("/api/mulank/order", json={"report_id": "no-such-report-id", "fbc": "fb.1.1.x"}).status_code == 404
    assert "_fbc" not in _meta_of(other)


def test_oversized_click_context_is_truncated_not_stored_whole(client, rz, eligible):
    rid, _ = _lead(client)
    _order(client, rid, fbc="f" * 5000, fbp="p" * 5000)
    m = _meta_of(rid)
    assert len(m["_fbc"]) == 300 and len(m["_fbp"]) == 300


# ------------------------------------------------------------------ the server Purchase
def test_a_verified_payment_sends_one_purchase_to_each_platform_and_nothing_private(client, rz, eligible, no_pdf, vendors):
    rid, phone = _lead(client)
    oid = _order(client, rid, fbc="fb.1.1700000000.AbCdEf", fbp="fb.1.1700000000.123456")
    assert _verify(client, rz, oid).json()["status"] == "paid"
    hosts = _by_host(vendors)
    assert len(vendors) == 5 and set(hosts) == {"graph.facebook.com", "google-analytics.com", "api.linkedin.com", "bzr.openai.com", "ads-api.x.com"}

    eid = mp.numerology_event_id(rid)
    site = tracking.PUBLIC_BASE_URL + "/en/numerology"
    meta_ev = hosts["graph.facebook.com"][1]["data"][0]
    assert meta_ev["event_id"] == eid and meta_ev["event_source_url"] == site
    assert meta_ev["custom_data"] == {"currency": "INR", "value": 299.0}
    assert hosts["google-analytics.com"][1]["events"][0]["params"]["transaction_id"] == eid
    assert hosts["google-analytics.com"][1]["client_id"] == tracking._ga4_client_id(eid, None) != tracking._ga4_client_id(rid, None)
    assert hosts["api.linkedin.com"][1]["eventId"] == eid
    oa = hosts["bzr.openai.com"][1]["events"][0]
    assert oa["id"] == eid and oa["source_url"] == site
    xc = hosts["ads-api.x.com"][1]["conversions"][0]
    assert xc["conversion_id"] == eid and xc["event_source_url"] == site

    # the click context travelled with the sale
    assert meta_ev["user_data"]["fbc"] == "fb.1.1700000000.AbCdEf" and meta_ev["user_data"]["fbp"] == "fb.1.1700000000.123456"
    assert meta_ev["user_data"]["client_user_agent"] == "TestBrowser/1.0"
    assert meta_ev["user_data"]["ph"] == [tracking._sha256(tracking._norm_phone("+91" + phone))]
    assert {"idType": "LINKEDIN_FIRST_PARTY_ADS_TRACKING_UUID", "idValue": "LIFAT-abc123"} in hosts["api.linkedin.com"][1]["user"]["userIds"]
    assert xc["identifiers"][0]["twclid"] == "TWCLID-xyz789"

    # privacy (C3): scan every request URL (minus the vendor secret) and payload (minus clock fields, whose digits are arbitrary)
    clocks = {"event_time", "conversionHappenedAt", "timestamp_ms", "conversion_time"}
    scrub = lambda o: ({k: scrub(v) for k, v in o.items() if k not in clocks} if isinstance(o, dict)
                       else [scrub(x) for x in o] if isinstance(o, list) else o)
    blob = json.dumps([(re.sub(r"(access_token|api_secret)=[^&]*", "", u), scrub(p)) for u, p, _h in vendors])
    for private in (rid, "/report/", "/preview/", "numerology/report", NAME, "Priya", "Sharma", DOB_ISO, DOB_FORM, phone, "+91" + phone,
                    "91" + phone, "buyer@example.com"):
        assert private not in blob, f"{private!r} reached a vendor"


def test_replays_and_the_webhook_do_not_send_a_second_purchase(client, rz, eligible, no_pdf, vendors, monkeypatch):
    import hmac
    monkeypatch.setattr(api, "RZP_WEBHOOK_SECRET", "wh-secret-purchase")
    rid, _ = _lead(client)
    oid = _order(client, rid)
    assert _verify(client, rz, oid).status_code == 200
    assert len(vendors) == 5
    assert _verify(client, rz, oid).status_code == 200                              # replay of verify
    raw = json.dumps({"event": "payment.captured", "payload": {"payment": {"entity": _ent(oid)}}}).encode()
    sig = hmac.new(b"wh-secret-purchase", raw, hashlib.sha256).hexdigest()
    assert client.post("/api/mulank/webhook", content=raw, headers={"X-Razorpay-Signature": sig, "X-Razorpay-Event-Id": "evt_" + oid[-20:]}).status_code == 200
    assert len(vendors) == 5                                                        # still one Purchase per platform


def test_unconfigured_vendors_send_nothing_and_never_raise(client, rz, eligible, no_pdf, monkeypatch):
    sent = []
    monkeypatch.setattr(tracking, "_post_json", lambda *a, **k: sent.append(a))
    for name in ("META_CAPI_TOKEN", "GA4_API_SECRET", "LINKEDIN_CAPI_TOKEN", "OAIQ_CAPI_TOKEN", "X_PIXEL_TOKEN"):
        monkeypatch.setattr(tracking, name, "")
    rid, _ = _lead(client)
    assert _verify(client, rz, _order(client, rid)).json()["status"] == "paid"
    assert sent == []


def test_a_free_pass_unlock_sends_no_purchase(client, rz, eligible, vendors):
    rid, _ = _lead(client)
    tok = "MK-test-%d" % next(_seq)
    conn = db_v2.get_conn()
    try:
        uid = db_v2.get_report(conn, rid)["user_id"]
        with conn.cursor() as cur:
            cur.execute("INSERT INTO passes(token) VALUES(%s)", (tok,))
        assert payments_v2.redeem_free_pass(conn, token=tok, report_id=rid, user_id=uid) is True
        conn.commit()
    finally:
        conn.close()
    assert mulank_tracking.run(rid) is False and vendors == []


def test_unpaid_and_foreign_reports_send_nothing(client, eligible, vendors):
    rid, _ = _lead(client)
    assert mulank_tracking.run(rid) is False                                        # not paid
    assert mulank_tracking.run("no-such-report-id") is False
    conn = db_v2.get_conn()
    try:
        other = "ot%030d" % next(_seq)
        reports_v2.save_report(conn, other, {"product": "marriage", "dob": DOB_ISO, "meta": {}}, [], product="marriage",
                               phone="98%08d" % (62000000 + next(_seq)))
        conn.commit()
    finally:
        conn.close()
    assert mulank_tracking.run(other) is False
    assert vendors == []


def test_a_tracking_failure_never_breaks_the_report(client, rz, eligible, no_pdf, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("vendor down")
    monkeypatch.setattr(tracking, "track_purchase", boom)
    rid, _ = _lead(client)
    r = _verify(client, rz, _order(client, rid))
    assert r.status_code == 200 and r.json()["status"] == "paid"


# ------------------------------------------------------------------ other products are unchanged
def test_other_products_keep_their_old_ids_and_source_urls(vendors):
    tracking.track_purchase("rid_abc123", 499, "INR", "9876543210", "a@b.com", fbc="fb.1.1.x", fbp="fb.1.2.y",
                            client_user_agent="UA", client_ip_address="1.2.3.4", li_fat_id="LI", twclid="TW")
    hosts = _by_host(vendors)
    site = tracking.PUBLIC_BASE_URL + "/report/rid_abc123"
    assert hosts["graph.facebook.com"][1]["data"][0]["event_id"] == "rid_abc123"
    assert hosts["graph.facebook.com"][1]["data"][0]["event_source_url"] == site
    assert hosts["google-analytics.com"][1]["events"][0]["params"]["transaction_id"] == "rid_abc123"
    assert hosts["api.linkedin.com"][1]["eventId"] == "rid_abc123"
    assert hosts["bzr.openai.com"][1]["events"][0]["source_url"] == site
    assert hosts["ads-api.x.com"][1]["conversions"][0]["event_source_url"] == site
    assert hosts["ads-api.x.com"][1]["conversions"][0]["conversion_id"] == "rid_abc123"


# ------------------------------------------------------------------ first-party events
def test_first_party_event_with_a_hashed_numerology_id_is_stored_without_a_report_link(client):
    conn = db_v2.get_conn()
    try:
        hashed = mp.numerology_event_id("some-private-report-id")
        eid = events_v2.record_event(conn, visitor_id="vis-mk-%d" % next(_seq), event_name="purchase", report_id=hashed,
                                     product=mp.PRODUCT, value_paise=29900, currency="INR")
        real = events_v2.record_event(conn, visitor_id="vis-mk-%d" % next(_seq), event_name="page_view", product=mp.PRODUCT)
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("SELECT report_id, value_paise FROM events WHERE id=%s", (eid,))
            assert cur.fetchone() == (None, 29900)
            cur.execute("SELECT COUNT(*) FROM events WHERE id=%s", (real,))
            assert cur.fetchone()[0] == 1
    finally:
        conn.close()
