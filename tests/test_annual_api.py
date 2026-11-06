"""Annual Report: the REAL wired path through api.py (clone of test_diwali_api.py).

kundli (work types, steering, genders, time quality) -> teaser -> /api/order (49900 by
product, stored) -> /api/verify -> delivery (_deliver_annual_task: text -> PDF -> WhatsApp
to the popup number only) -> /report/{id} chrome. Razorpay, Chrome (pdfgen), Twilio and
the LLM are stubbed: no network. Phones 99880003xx are unique across the suite (CLAUDE.md s12).
Tests needing annual_report.render_annual skip if that module is missing.
"""
import hashlib
import hmac
import json
import re
import time

import pytest
import twilio.rest

import api
import db_v2
import narrative
import pdfgen

SECRET = "rzp_key_secret_annual"
FAKE_PDF = b"%PDF-1.4 annual-test" + b"0" * 2048
PAYER = "+919999900001"          # Razorpay's PAYMENT contact: must never get a WhatsApp (s1)
FESTIVAL = re.compile(r"diwali|deepavali|dhanteras|lakshmi|muhurat", re.I)


def _sign(oid, pid):
    return hmac.new(SECRET.encode(), f"{oid}|{pid}".encode(), hashlib.sha256).hexdigest()


class _StubRzp:
    class order:
        @staticmethod
        def create(d):
            return {"id": "order_" + d["receipt"], "amount": d["amount"], "currency": "INR"}

    class payment:
        @staticmethod
        def fetch(pid):
            return {"contact": PAYER, "email": "", "amount": 49900, "method": "upi"}


@pytest.fixture
def wired(monkeypatch):
    events = []
    monkeypatch.setattr(api, "RZP_SECRET", SECRET)
    monkeypatch.setattr(api, "rzp_client", lambda: _StubRzp())
    monkeypatch.setattr(pdfgen, "get_or_generate",
                        lambda rid, html: events.append(("pdf", rid, html)) or FAKE_PDF)
    monkeypatch.setattr(pdfgen, "invalidate", lambda rid: events.append(("invalidate", rid)) or False)
    monkeypatch.setattr(api, "send_whatsapp_report",
                        lambda phone, rid, name, product="marriage":
                        events.append(("wa", rid, phone, product)))
    monkeypatch.setattr(api, "send_whatsapp_text",
                        lambda phone, rid, name: events.append(("text", rid, phone)))
    return events


def _base(**kw):
    body = {"name": "Kavita Sharma", "dob": "1990-07-18", "tob": "10:30",
            "time_quality": "T0", "place": "Delhi", "gender": "female",
            "product": "annual_report", "variant": "/en/annual-report", "work_type": "job",
            "steering": None}
    body.update(kw)
    return body


def _kundli(client, **kw):
    r = client.post("/api/kundli", json=_base(**kw))
    assert r.status_code == 200, r.text
    return r.json()


def _amounts(rid):
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT amount_paise FROM payments WHERE report_id=%s", (rid,))
            return [r[0] for r in c.fetchall()]
    finally:
        conn.close()


def _pay(client, rid, phone, tag):
    oid = client.post("/api/order", json={"report_id": rid, "phone": phone}).json()["razorpay_order_id"]
    pid = "pay_annual_" + tag
    r = client.post("/api/verify", json={"razorpay_order_id": oid, "razorpay_payment_id": pid,
                                         "razorpay_signature": _sign(oid, pid)})
    assert r.status_code == 200, r.text


def _render_annual():
    try:
        import annual_report
    except ImportError:
        pytest.skip("annual_report.py not built yet")
    return annual_report


# ------------------------------------------------------------------ (1) price
def test_price_by_product(monkeypatch):
    assert api._order_amount_paise({"product": "annual_report", "payload": {}}) == 49900
    assert api._order_amount_paise({"product": "annual_report",
                                    "payload": {"meta": {"variant": "/milan"}}}) == 49900
    assert api._order_amount_paise({"product": "diwali", "payload": {}}) == 29900
    # annual has its own branch: moving the generic fall-through price must not move it
    # (an unknown product DOES fall to generic PRICE_PAISE, same as every other product)
    monkeypatch.setattr(api, "PRICE_PAISE", 1)
    assert api._order_amount_paise({"product": "annual_report", "payload": {}}) == 49900
    assert api._order_amount_paise({"product": "nonsense_x", "payload": {}}) == 1


def test_order_stores_the_real_charged_amount(client, wired):
    rid = _kundli(client, name="Order Amount")["report_id"]
    order = client.post("/api/order", json={"report_id": rid, "phone": "9988000301"}).json()
    assert order["amount"] == 49900
    assert _amounts(rid) == [49900]


# ------------------------------------------------------------------ (2) /api/kundli
@pytest.mark.parametrize("wt,phone", [("job", "9988000302"), ("business", "9988000303"),
                                      ("student", "9988000304"), ("home", "9988000305")])
def test_kundli_each_work_type(client, wt, phone):
    data = _kundli(client, work_type=wt, name="Work " + wt)
    assert set(data) == {"report_id", "teaser"}
    assert api.get_report(data["report_id"])["payload"]["meta"]["work_type"] == wt


@pytest.mark.parametrize("steer", ["career", "money", "marriage", "luck", "strengths", None])
def test_kundli_each_steering(client, steer):
    data = _kundli(client, steering=steer, name="Steer " + str(steer))
    assert set(data) == {"report_id", "teaser"}


@pytest.mark.parametrize("g", ["male", "female"])
def test_kundli_both_genders(client, g):
    assert _kundli(client, gender=g, name="Gender " + g)["teaser"]


@pytest.mark.parametrize("bad", [dict(gender="other"), dict(gender=None), dict(work_type="retired"),
                                 dict(work_type=None), dict(steering="family"), dict(steering="health")])
def test_kundli_bad_input_422(client, bad):
    r = client.post("/api/kundli", json=_base(**bad))
    assert r.status_code == 422
    assert r.json()["detail"]


def test_kundli_bad_messages_are_clear(client):
    assert "gender" in client.post("/api/kundli", json=_base(gender="x")).json()["detail"]
    assert "work_type" in client.post("/api/kundli", json=_base(work_type="x")).json()["detail"]
    assert "steering" in client.post("/api/kundli", json=_base(steering="family")).json()["detail"]


def test_diwali_steering_still_validated_for_diwali(client):
    d = dict(product="diwali", variant="/en/diwali", gift_mode="self")
    assert client.post("/api/kundli", json=_base(steering="family", **d)).status_code == 200
    assert client.post("/api/kundli", json=_base(steering="strengths", **d)).status_code == 422
    assert client.post("/api/kundli", json=_base(steering="health", **d)).status_code == 422


@pytest.mark.parametrize("tq,extra", [("T0", {}), ("T2", {"time_band": "subah", "tob": None}),
                                      ("T3", {"tob": None})])
def test_kundli_time_quality(client, tq, extra):
    data = _kundli(client, time_quality=tq, name="TQ " + tq, **extra)
    assert api.get_report(data["report_id"])["payload"]["meta"]["time_quality"] == tq


def test_kundli_missing_city_422(client):
    r = client.post("/api/kundli", json=_base(place="Nowhereville Xyz"))
    assert r.status_code == 422 and r.json()["detail"] == "city_not_selected"


def test_teaser_leaks_nothing_locked(client):
    t = _kundli(client, name="Leak Check")["teaser"]
    assert "chart" not in t and "north_chart_svg" not in t and "chart_svg" not in t
    strip = t["preview"]["strip"]
    assert len(strip) == 12
    for i, m in enumerate(strip):
        assert ("tone" in m) == (i < 2), m          # only the 2 open months carry a tone
        assert m["open"] == (i < 2)


# ------------------------------------------------------------------ (3) routes
def test_landing_page_and_hooks(client):
    r = client.get("/en/annual-report")
    assert r.status_code == 200
    h = r.text
    assert "axs_annual_offer_end" in h and "annual_report" in h
    assert '<link rel="canonical" href="https://www.axtroshastra.com/en/annual-report">' in h
    assert not FESTIVAL.search(h), FESTIVAL.search(h)


def test_legacy_redirect_hindi_and_sitemap(client):
    r = client.get("/annual-report?utm_source=x", follow_redirects=False)
    assert r.status_code == 301 and r.headers["location"] == "/en/annual-report?utm_source=x"
    # real behaviour: /hi/annual-report is not registered (falls to the 404 handler)
    assert client.get("/hi/annual-report", follow_redirects=False).status_code == 404
    assert "/en/annual-report</loc>" in client.get("/sitemap.xml").text


# ------------------------------------------------------------------ (4) narrative
def test_narrative_is_no_llm_and_marks_ready(client, wired, monkeypatch):
    monkeypatch.setenv("NARRATIVE_ENABLED", "1")
    monkeypatch.setattr(narrative, "_call",
                        lambda *a, **k: pytest.fail("LLM called for annual_report"))
    monkeypatch.setattr(narrative, "_call_anthropic", lambda *a, **k: pytest.fail("LLM called"))
    monkeypatch.setattr(narrative, "_call_openai", lambda *a, **k: pytest.fail("LLM called"))
    rid = _kundli(client, name="No Llm")["report_id"]
    _pay(client, rid, "9988000320", "nollm")
    st = client.get(f"/api/report/{rid}").json()
    assert st["paid"] is True and st["report"]["narrative"].get("_ready") == "1"


# ------------------------------------------------------------------ (5) delivery
def test_delivery_order_and_popup_number_only(client, wired):
    rid = _kundli(client, name="Delivery One")["report_id"]
    _pay(client, rid, "9988000321", "deliv")
    ev = [e for e in wired if e[1] == rid]
    assert [e[0] for e in ev] == ["text", "invalidate", "pdf", "wa"]
    wa = next(e for e in ev if e[0] == "wa")
    assert wa[2] == "+919988000321" and wa[3] == "annual_report"
    assert next(e for e in ev if e[0] == "text")[2] == "+919988000321"
    assert all(PAYER not in str(e) and "9999900001" not in str(e) for e in ev)


def test_delivery_still_on_its_way(client, wired, monkeypatch):
    monkeypatch.setattr(api, "DIWALI_STILL_COMING_S", 0.05)
    monkeypatch.setattr(narrative, "generate_narrative", lambda p: time.sleep(0.4) or {})
    rid = _kundli(client, name="Slow One")["report_id"]
    _pay(client, rid, "9988000322", "slow")
    assert [e[0] for e in wired if e[1] == rid] == ["text", "text", "invalidate", "pdf", "wa"]


def test_delivery_fast_sends_no_nudge(client, wired, monkeypatch):
    monkeypatch.setattr(api, "DIWALI_STILL_COMING_S", 0.3)
    rid = _kundli(client, name="Fast One")["report_id"]
    _pay(client, rid, "9988000323", "fast")
    time.sleep(0.5)
    assert [e[0] for e in wired if e[1] == rid].count("text") == 1


_TW = {"TWILIO_SID": "AC_t", "TWILIO_TOKEN": "t", "TWILIO_FROM": "whatsapp:+14155238886",
       "PUBLIC_BASE_URL": "https://axtroshastra.example",
       "TWILIO_CONTENT_SID": "HXmedia0000000000000000000000000",
       "TWILIO_CONTENT_SID_TEXT": "HXtext00000000000000000000000000"}


@pytest.mark.parametrize("fetchable,phone", [(True, "9988000324"), (False, "9988000325")])
def test_real_twilio_templates_media_and_text_fallback(client, monkeypatch, fetchable, phone):
    """The real send functions through the real paid path: media template when the PDF is
    fetchable, text template otherwise. Every message goes to the popup number only."""
    calls = []

    class _Client:
        def __init__(self, *a, **k):
            self.messages = type("M", (), {"create": staticmethod(
                lambda **kw: calls.append(kw) or type("Msg", (), {"sid": "SM"})())})()
    for k, v in _TW.items():
        monkeypatch.setattr(api, k, v)
    monkeypatch.setattr(twilio.rest, "Client", _Client)
    monkeypatch.setattr(api, "RZP_SECRET", SECRET)
    monkeypatch.setattr(api, "rzp_client", lambda: _StubRzp())
    monkeypatch.setattr(pdfgen, "get_or_generate", lambda rid, html: FAKE_PDF)
    monkeypatch.setattr(pdfgen, "get_cached", lambda rid: FAKE_PDF)
    monkeypatch.setattr(api, "_pdf_is_fetchable", lambda rid: fetchable)
    rid = _kundli(client, name="Twilio Real " + str(fetchable))["report_id"]
    _pay(client, rid, phone, "tw" + str(fetchable))
    assert calls, "no WhatsApp sent"
    assert all(c["to"] == "whatsapp:+91" + phone for c in calls), calls
    last = calls[-1]
    want = _TW["TWILIO_CONTENT_SID"] if fetchable else _TW["TWILIO_CONTENT_SID_TEXT"]
    assert last["content_sid"] == want
    if fetchable:
        assert json.loads(last["content_variables"])["3"] == rid


# ------------------------------------------------------------------ (6) report chrome
def test_report_page_chrome(client):
    _render_annual()
    rid = _kundli(client, name="Rohan Mehta")["report_id"]
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    page = client.get(f"/report/{rid}")
    assert page.status_code == 200
    h = page.text
    assert "axPdfDl" in h and "axShare" in h
    assert "window.print();return false;" not in h
    pages = re.findall(r'<(?:div|section)[^>]*class="[^"]*\bpage\b', h)
    assert len(pages) == 58, len(pages)
    assert 'class="pgn"' in h
    assert not FESTIVAL.search(h), FESTIVAL.search(h)
    for invented in ("Anjali", "Deshpande"):          # no sample persona leaks (rule 22)
        assert invented not in h, invented


# ------------------------------------------------------------------ audit regressions
def test_f3_future_dob_422_never_500(client):
    for dob in ("2035-01-01", "2099-01-01"):
        r = client.post("/api/kundli", json=_base(dob=dob))
        assert r.status_code == 422, (dob, r.status_code, r.text)
        assert r.json()["detail"] == "dob must be before the report date"


def test_f3_recent_and_ancient_dob_ok(client):
    import datetime
    yday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    for dob in (yday, "1900-01-01"):
        r = client.post("/api/kundli", json=_base(dob=dob, name="Dob " + dob[:4]))
        assert r.status_code == 200, (dob, r.status_code, r.text)


@pytest.mark.parametrize("bad", [
    dict(name="x" * 5000), dict(name="x" * 61), dict(name="     "), dict(place="y" * 121),
    dict(lat=91.0, lon=77.2, tz="Asia/Kolkata"), dict(lat=28.6, lon=181.0, tz="Asia/Kolkata"),
    dict(dob="1990-07-18" + "0" * 20), dict(tob="10:30" + "0" * 20), dict(tz="Z" * 65),
    dict(phone="9" * 21), dict(email="e" * 255), dict(variant="/" + "v" * 64)],
    ids=["name5000", "name61", "name_spaces", "place121", "lat91", "lon181",
         "dob_long", "tob_long", "tz_long", "phone_long", "email_long", "variant_long"])
def test_f5_annual_guards_422_not_500(client, bad):
    r = client.post("/api/kundli", json=_base(**bad))
    assert r.status_code == 422, (r.status_code, r.text[:200])


def test_f5_name_60_chars_ok(client):
    assert client.post("/api/kundli", json=_base(name="n" * 60)).status_code == 200


def test_f5_guard_is_annual_only(client):
    """The name cap is annual-only. CURRENT behaviour of the other products (not fixed here,
    out of scope): a 5000-char name is NOT rejected with 422; it reaches the DB and the
    name column overflows (pymysql DataError, a 500 in production). Annual returns 422."""
    import pymysql
    long = "q" * 5000
    assert client.post("/api/kundli", json=_base(name=long)).status_code == 422   # annual: capped
    for body in (_base(name=long, product="diwali", variant="/en/diwali", gift_mode="self"),
                 {"name": long, "dob": "1993-02-11", "tob": "08:00", "time_quality": "T0",
                  "place": "Delhi", "gender": "male"}):
        try:
            r = client.post("/api/kundli", json=body)
            assert r.status_code != 422, r.text[:200]      # never the annual guard
        except pymysql.err.DataError:
            pass                                           # current behaviour: DB overflow


def test_f7_no_page_counts_in_marketing_copy():
    from pathlib import Path
    pages = Path(api.__file__).parent / "pages"
    pc = re.compile(r"\b\d+[- ]pages?\b", re.I)
    ann = (pages / "annual-report.html").read_text(encoding="utf-8")
    assert not pc.search(ann), pc.search(ann)
    home = (pages / "home.html").read_text(encoding="utf-8")
    card = re.search(r'<a class="card" href="/en/annual-report">.*?</a>', home, re.S).group(0)
    assert not pc.search(card), pc.search(card)
    for t in ("career", "money", "marriage", "luck", "strengths"):
        assert t in card
    revs = re.findall(r'<div class="rev"><div class="tag">Annual Report</div>.*?</div></div>', home, re.S)
    assert len(revs) >= 5
    for rv in revs:
        assert not pc.search(rv), rv


def _paid_annual(client, name):
    rid = _kundli(client, name=name)["report_id"]
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    return rid


def test_report_58_pages_after_json_roundtrip_and_pdf_route(client, wired):
    """The stored payload went through JSON (int dict keys become str): /report must still
    render all 58 pages. Then the PDF route, Chrome stubbed exactly as in the Diwali test."""
    rid = _paid_annual(client, "Json Trip")
    stored = api.get_report(rid)["payload"]
    assert json.loads(json.dumps(stored)) == stored        # really JSON-clean
    page = client.get(f"/report/{rid}")
    assert page.status_code == 200
    assert len(re.findall(r'<(?:div|section)[^>]*class="[^"]*\bpage\b', page.text)) == 58
    r = client.get(f"/report/{rid}.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    pdf_html = [e[2] for e in wired if e[0] == "pdf" and e[1] == rid][-1]
    assert "ax-dwbar" not in pdf_html


# ------------------------------------------------------------------ R2-4 time/date guards
@pytest.mark.parametrize("bad", [
    dict(tob="99:99"), dict(tob="25:61"), dict(tob="ab:cd"),
    dict(dob="abc"), dict(dob="2020-13-45"), dict(dob=""), dict(dob="2020-1-5"),
    dict(time_quality="T2", time_band="din", tob="zz"), dict(time_quality="T2", time_band="din", tob="99:99"),
    dict(time_quality="T2", time_band="noon", tob=None), dict(time_quality="T9")],
    ids=["tob9999", "tob2561", "tobabcd", "dob_abc", "dob_month13", "dob_empty", "dob_nopad",
         "T2_bad_tob", "T2_tob9999", "band_noon", "tq_T9"])
def test_r24_bad_time_or_date_422_not_500(client, bad):
    r = client.post("/api/kundli", json=_base(**bad))
    assert r.status_code == 422, (r.status_code, r.text[:200])


@pytest.mark.parametrize("ok", [
    dict(tob="09:30"), dict(time_quality="T2", time_band="din", tob=None),
    dict(time_quality="T3", tob=None), dict(time_quality="T1", tob="07:45")],
    ids=["T0", "T2_din", "T3", "T1"])
def test_r24_good_time_200(client, ok):
    assert client.post("/api/kundli", json=_base(name="Good Time", **ok)).status_code == 200


def test_r24_guard_is_annual_only(client):
    """Diwali with dob 'abc': CURRENT behaviour, a pre-existing unhandled error (500 in
    production), out of scope here. Proves the annual 422 guard does not apply to it."""
    d = _base(dob="abc", product="diwali", variant="/en/diwali", gift_mode="self")
    try:
        status = client.post("/api/kundli", json=d).status_code
    except ValueError:
        status = 500                       # TestClient re-raises the server error
    assert status != 422, status
