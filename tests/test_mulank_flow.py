"""Mulank customer journey: landing page, POST /api/mulank, preview viewer, preview PDF, access control,
rate limiting and privacy. Real throwaway MySQL from conftest; Razorpay and (mostly) Chrome stubbed."""
import itertools
import logging
import re

import pytest

import api
import db_v2
import mulank_content as mc
import mulank_form as mf
import mulank_payment as mp
import mulank_routes
import numerology
import reports_v2

_ph = itertools.count(1)


def _body(**kw):
    b = {"name": "Priya Sharma", "dob": "29/07/1990", "gender": "female", "country_code": "+91",
         "phone": "98%08d" % (50000000 + next(_ph)), "consent_terms": True, "marketing_optin": False}
    b.update(kw)
    return b


def _create(client, **kw):
    return client.post("/api/mulank", json=_body(**kw))


def _rid(client, **kw):
    r = _create(client, **kw)
    assert r.status_code == 200, r.text
    return r.json()["report_id"]


def _report_row(rid):
    conn = db_v2.get_conn()
    try:
        return reports_v2.read_report(conn, rid)
    finally:
        conn.close()


@pytest.fixture
def eligible(monkeypatch):
    res = numerology.compute_mulank(29, 7, 1990, today=mc._today())
    monkeypatch.setattr(mc, "REGISTRY", {k: mc.Entry(mc.VERIFIED, "Test Reviewer", "2026-11-03")
                                         for k in mc.required_keys(res)})


# ------------------------------------------------------------------ validators
@pytest.mark.parametrize("raw,ok", [
    ("29/07/1990", (29, 7, 1990)), ("1990-07-29", (29, 7, 1990)), ("1/2/2000", (1, 2, 2000)), (" 29-07-1990 ", (29, 7, 1990))])
def test_parse_dob_accepts_ddmmyyyy_and_iso(raw, ok):
    assert mf.parse_dob(raw) == ok


@pytest.mark.parametrize("raw,code", [
    ("", "dob_required"), ("abc", "dob_format"), ("29071990", "dob_format"), ("07/29/1990", "dob_invalid"),
    ("31/02/1990", "dob_invalid"), ("29/02/2001", "dob_invalid"), ("01/01/1899", "dob_too_old"),
    ("01/01/2999", "dob_future"), ("1990-13-01", "dob_invalid")])
def test_parse_dob_rejects(raw, code):
    with pytest.raises(mf.FormError) as e:
        mf.parse_dob(raw)
    assert e.value.field == "dob" and e.value.code == code


def test_leap_day_ok_and_tomorrow_rejected():
    from datetime import date, timedelta
    assert mf.parse_dob("29/02/2000") == (29, 2, 2000)
    t = date.today() + timedelta(days=1)
    with pytest.raises(mf.FormError) as e:
        mf.parse_dob(t.strftime("%d/%m/%Y"))
    assert e.value.code == "dob_future"


@pytest.mark.parametrize("cc,raw,out", [
    ("+91", "98765 43210", "9876543210"), ("+91", "098765-43210", "9876543210"), ("+91", "+919876543210", "9876543210"),
    ("91", "919876543210", "9876543210"), (None, "9876543210", "9876543210")])
def test_clean_phone_ok(cc, raw, out):
    assert mf.clean_phone(cc, raw) == out


@pytest.mark.parametrize("cc,raw,code", [
    ("+44", "9876543210", "country_unsupported"), ("+91", "", "phone_required"), ("+91", "12345", "phone_invalid"),
    ("+91", "5876543210", "phone_invalid"), ("+91", "98765432101", "phone_invalid"), ("+91", "abcdefghij", "phone_invalid")])
def test_clean_phone_rejects(cc, raw, code):
    with pytest.raises(mf.FormError) as e:
        mf.clean_phone(cc, raw)
    assert e.value.code == code


def test_validate_rules():
    ok = mf.validate(_body())
    assert ok["dob_iso"] == "1990-07-29" and ok["gender"] == "female" and ok["marketing_optin"] is False
    for bad, field in ((dict(consent_terms=False), "consent_terms"), (dict(name=""), "name"), (dict(name="1234"), "name"),
                       (dict(name="x" * 81), "name"), (dict(gender="robot"), "gender"), (dict(phone="1"), "phone")):
        with pytest.raises(mf.FormError) as e:
            mf.validate(_body(**bad))
        assert e.value.field == field
    assert mf.validate(_body(gender=""))["gender"] is None
    assert mf.validate(_body(gender="prefer_not_to_say"))["gender"] == "prefer_not_to_say"
    assert mf.validate(_body(marketing_optin=True))["marketing_optin"] is True


# ------------------------------------------------------------------ POST /api/mulank
def test_create_saves_iso_dob_and_returns_only_an_opaque_link(client):
    b = _body(phone="9811100001")
    r = client.post("/api/mulank", json=b)
    assert r.status_code == 200
    d = r.json()
    assert set(d) == {"report_id", "preview_url"} and d["preview_url"] == f"/en/numerology/preview/{d['report_id']}"
    assert re.fullmatch(r"[A-Za-z0-9_-]{16}", d["report_id"])
    for secret in ("Priya", "Sharma", "9811100001", "1990", "29"):
        assert secret not in r.text
    assert r.headers["cache-control"] == "no-store" and "noindex" in r.headers["x-robots-tag"]
    rec = _report_row(d["report_id"])
    assert rec["product"] == mp.PRODUCT and rec["payload"]["dob"] == "1990-07-29" and rec["payload"]["name"] == "Priya Sharma"
    assert rec["user_phone"].endswith("9811100001")
    assert mp.dob_of(rec) == (29, 7, 1990)                         # exactly what the payment code reads
    meta = rec["payload"]["meta"]
    assert meta["marketing_optin"] is False and meta["marketing_optin_ts"] is None and meta["consent_ts"] and meta["consent_v"]
    assert rec["payload"]["numbers"] == {"mulank": 2, "bhagyank": 1, "pair_key": "2-1"}
    assert not rec["paid"]


def test_marketing_optin_is_separate_and_timestamped(client):
    on = _report_row(_rid(client, marketing_optin=True))["payload"]["meta"]
    assert on["marketing_optin"] is True and on["marketing_optin_ts"]
    off = _report_row(_rid(client))["payload"]["meta"]
    assert off["marketing_optin"] is False


def test_each_submission_gets_a_unique_report(client):
    assert len({_rid(client) for _ in range(5)}) == 5


@pytest.mark.parametrize("bad,field", [
    (dict(consent_terms=False), "consent_terms"), (dict(dob="31/02/1990"), "dob"), (dict(dob="01/01/2999"), "dob"),
    (dict(name=" "), "name"), (dict(phone="123"), "phone"), (dict(country_code="+44"), "phone"), (dict(gender="x"), "gender")])
def test_create_rejects_bad_input_with_field(client, bad, field):
    r = _create(client, **bad)
    assert r.status_code == 422 and r.json()["detail"]["field"] == field and r.json()["detail"]["message"]


def test_honeypot_and_non_json_rejected(client):
    assert _create(client, website="http://spam.test").status_code == 400
    assert client.post("/api/mulank", content=b"nope", headers={"content-type": "application/json"}).status_code == 422


def test_gender_never_changes_the_preview(client, eligible):
    pages = []
    for g in ("female", "male", "other", "prefer_not_to_say", ""):
        rid = _rid(client, gender=g)
        html = client.get(f"/en/numerology/preview/{rid}").text
        pages.append(re.sub(r'data-slot="name">[^<]*', "", html).replace(rid, ""))
    assert len(set(pages)) == 1


def test_prefer_not_to_say_is_stored_as_no_gender(client):
    rid = _rid(client, gender="prefer_not_to_say")
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT gender FROM report_subjects WHERE report_id=%s", (rid,))
            assert cur.fetchone()[0] is None
    finally:
        conn.close()


def test_no_personal_data_in_logs(client, caplog):
    caplog.set_level(logging.DEBUG)
    b = _body(name="Zorbathustra Quillfeather", phone="9877712345")
    rid = client.post("/api/mulank", json=b).json()["report_id"]
    client.get(f"/en/numerology/preview/{rid}")
    log = caplog.text
    for secret in ("Zorbathustra", "Quillfeather", "9877712345", "1990-07-29", "29/07/1990"):
        assert secret not in log, secret


# ------------------------------------------------------------------ preview viewer
def test_preview_shows_five_cards_with_the_customers_numbers(client):
    rid = _rid(client)
    r = client.get(f"/en/numerology/preview/{rid}")
    assert r.status_code == 200 and r.text.count('<section class="page') == 5
    assert "Priya Sharma" in r.text and "Born 29 July 1990" in r.text and "Mulank 2 with Bhagyank 1" in r.text
    assert r.headers["cache-control"] == "no-store" and "noindex" in r.headers["x-robots-tag"]
    assert r.headers["referrer-policy"] == "no-referrer"
    assert "googletagmanager" not in r.text and "fbq(" not in r.text and "clarity" not in r.text.lower()


def test_ineligible_visitor_sees_unavailable_message_and_no_checkout(client):
    rid = _rid(client)                                    # shipped registry: nothing is verified
    t = client.get(f"/en/numerology/preview/{rid}").text
    assert "not ready for your numbers yet" in t
    assert "₹" not in t and 'data-action="checkout"' not in t and 'id="vwBar"' not in t
    assert client.post("/api/mulank/order", json={"report_id": rid}).status_code == 409


def test_eligible_visitor_sees_price_and_cta_after_page_three(client, eligible):
    rid = _rid(client)
    t = client.get(f"/en/numerology/preview/{rid}").text
    secs = re.findall(r'<section class="page[^"]*">.*?</section>', t, re.S)
    assert len(secs) == 5
    assert "₹299" in secs[3] and "₹499" in secs[3] and 'data-action="checkout"' in secs[3]
    assert "Your Numbers Are Just the Beginning." in secs[3] and "Locked" in secs[2]
    assert 'id="vwBar"' in t and "/api/mulank/order" in t and "checkout.razorpay.com" in t
    assert "razorpay_signature" in t                       # verify is posted to our server, never trusted client-side


def test_locked_values_are_not_in_the_served_preview(client, eligible):
    rid = _rid(client)
    t = client.get(f"/en/numerology/preview/{rid}").text
    secs = re.findall(r'<section class="page[^"]*">.*?</section>', t, re.S)
    for s in secs[2:]:
        txt = re.sub(r"<[^>]+>", " ", re.sub(r"<style.*?</style>", "", s, flags=re.S))
        assert "Priya" not in txt and "1990" not in txt and "Moon" not in txt


def test_unknown_malformed_and_other_product_ids_are_identical_404s(client):
    other = "ot%030d" % next(_ph)
    conn = db_v2.get_conn()
    try:
        reports_v2.save_report(conn, other, {"product": "iq_test", "meta": {}}, [], product="iq_test", phone="9822200001")
        conn.commit()
    finally:
        conn.close()
    bodies = set()
    for rid in ("doesnotexist12345", other, "a", "x" * 60):
        for path in (f"/en/numerology/preview/{rid}", f"/en/numerology/preview/{rid}.pdf", f"/en/numerology/report/{rid}"):
            r = client.get(path)
            assert r.status_code == 404, (path, r.status_code)
            bodies.add(r.text)
    assert len(bodies) == 1
    assert client.get("/en/numerology/preview/../../etc/passwd").status_code == 404


def test_one_customer_cannot_open_anothers_preview_without_their_link(client):
    a, b = _rid(client, name="Alpha Person"), _rid(client, name="Bravo Person")
    assert "Alpha Person" in client.get(f"/en/numerology/preview/{a}").text
    assert "Bravo Person" not in client.get(f"/en/numerology/preview/{a}").text
    assert a != b


def test_cookies_or_headers_cannot_substitute_for_the_link(client):
    rid = _rid(client, name="Charlie Person")
    r = client.get("/en/numerology/preview/guessed-id-1234567", headers={"X-Report-Id": rid}, cookies={"rid": rid})
    assert r.status_code == 404


# ------------------------------------------------------------------ preview PDF
def test_pdf_route_headers_cache_key_and_no_name_in_filename(client, monkeypatch):
    import pdfgen
    seen = {}

    def fake(key, html):
        seen["key"], seen["html"] = key, html
        return b"%PDF-1.4 fake" + b"0" * 2000
    monkeypatch.setattr(pdfgen, "get_or_generate", fake)
    rid = _rid(client)
    r = client.get(f"/en/numerology/preview/{rid}.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"] == 'attachment; filename="Axtroshastra-Numerology-Preview.pdf"'
    assert r.headers["cache-control"] == "no-store"
    assert seen["key"] == f"pv0_{rid}" and seen["key"] != rid          # never the paid report's cache key
    assert seen["html"].count('<section class="page') == 5


def test_pdf_failure_is_a_clean_503(client, monkeypatch):
    import pdfgen
    monkeypatch.setattr(pdfgen, "get_or_generate", lambda k, h: None)
    r = client.get(f"/en/numerology/preview/{_rid(client)}.pdf")
    assert r.status_code == 503 and r.json()["detail"] == "pdf_unavailable"


def test_real_pdf_has_five_pages_and_no_locked_text(client, monkeypatch, tmp_path, eligible):
    fitz = pytest.importorskip("pymupdf")
    import pdfgen
    monkeypatch.setattr(pdfgen, "PDF_DIR", str(tmp_path))
    r = client.get(f"/en/numerology/preview/{_rid(client)}.pdf")
    if r.status_code == 503:
        pytest.skip("headless Chrome not available")
    doc = fitz.open(stream=r.content, filetype="pdf")
    assert len(doc) == 5 and all(round(p.rect.width) == 323 and round(p.rect.height) == 623 for p in doc)
    assert "Priya Sharma" in doc[0].get_text() and "₹299" in doc[3].get_text()
    assert "Priya" not in doc[2].get_text() + doc[4].get_text()


# ------------------------------------------------------------------ rate limiting
def test_create_is_rate_limited(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "1")
    mulank_routes._hits.clear()
    codes = [client.post("/api/mulank", json=_body(dob="bad")).status_code for _ in range(8)]
    assert codes[:6] == [422] * 6 and codes[6:] == [429, 429]
    mulank_routes._hits.clear()


def test_pdf_and_view_are_rate_limited(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "1")
    mulank_routes._hits.clear()
    codes = [client.get("/en/numerology/preview/nope1234567890.pdf").status_code for _ in range(10)]
    assert codes[:8] == [404] * 8 and 429 in codes[8:]
    mulank_routes._hits.clear()


# ------------------------------------------------------------------ after payment
def test_report_page_redirects_until_paid_then_confirms(client):
    rid = _rid(client)
    r = client.get(f"/en/numerology/report/{rid}", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == f"/en/numerology/preview/{rid}"
    conn = db_v2.get_conn()
    try:
        db_v2.set_report_paid(conn, rid)
        conn.commit()
    finally:
        conn.close()
    r = client.get(f"/en/numerology/report/{rid}")
    assert r.status_code == 200 and "Payment received" in r.text and "noindex" in r.text
    assert client.get(f"/en/numerology/preview/{rid}", follow_redirects=False).status_code == 302


# ------------------------------------------------------------------ landing page
FLAGGED = (r"anxi", r"stress", r"depress", r"panic", r"trauma", r"therap", r"counsel", r"mental", r"well-?being", r"wellness",
           r"burn-?out", r"overwhelm", r"breakdown", r"spiral", r"coping", r"\bcope\b", r"self-care", r"healing", r"\bheal\b",
           r"peace of mind", r"inner peace", r"diagnos", r"symptom", r"disorder", r"treatment", r"\bcure\b", r"remedy", r"disease",
           r"illness", r"patient", r"clinical", r"medic", r"prescription", r"doctor", r"health", r"cancer", r"chronic", r"disabilit",
           r"adhd", r"weight", r"\bdiet\b", r"calorie", r"nutrition", r"\bfat\b", r"obes", r"detox")


def _visible(html):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)).lower()


def test_landing_page_has_the_four_fields_and_separate_consents(client):
    r = client.get("/en/numerology")
    assert r.status_code == 200
    h = r.text
    for needle in ('id="f-name"', 'id="f-dob"', 'id="f-gender"', 'id="f-phone"', "DD/MM/YYYY", "Prefer not to say", "+91",
                   'id="f-consent"', 'id="f-marketing"', 'href="/privacy"', 'href="/terms"', "See My Free Preview"):
        assert needle in h, needle
    assert re.search(r'id="f-marketing"[^>]*checked', h) is None and re.search(r'id="f-consent"[^>]*checked', h) is None
    assert h.count('id="f-consent"') == 1                       # the shared injector did not add a second consent box
    assert "Not used in your calculation" in h
    assert 'name="robots" content="noindex' in h
    assert "₹" not in _visible(h)


def test_landing_says_the_complete_report_is_not_available_until_content_is_approved(client, monkeypatch):
    h = client.get("/en/numerology").text
    assert "The complete numerology report is not available yet" in h and "<!--MK_NOTICE-->" not in h
    assert not mc.any_verified()
    res = numerology.compute_mulank(29, 7, 1990, today=mc._today())
    monkeypatch.setattr(mc, "REGISTRY", {k: mc.Entry(mc.OWNER_APPROVED, editor="Editor", approved_by="Owner", approved_on="2026-11-03")
                                         for k in mc.required_keys(res)})
    h2 = client.get("/en/numerology").text
    assert "not available yet" not in h2 and "<!--MK_NOTICE-->" not in h2 and "mk-notice{" in h2


def test_landing_page_avoids_meta_flagged_vocabulary():
    t = _visible(open("pages/numerology.html", encoding="utf-8").read())
    hits = [w for w in FLAGGED if re.search(w, t)]
    assert not hits, hits


def test_preview_cards_avoid_meta_flagged_vocabulary(client, eligible):
    t = _visible(client.get(f"/en/numerology/preview/{_rid(client)}").text)
    hits = [w for w in FLAGGED if re.search(w, t)]
    assert not hits, hits


def test_landing_has_no_name_dob_or_phone_in_urls():
    js = open("pages/numerology.html", encoding="utf-8").read()
    assert "location.href=d.preview_url" in js and "?name=" not in js and "?dob=" not in js and "localStorage" not in js
    assert "sessionStorage" not in js


def test_existing_pages_and_products_unaffected(client):
    assert client.get("/en/iq-test").status_code == 200
    assert client.get("/en/career-intelligence").status_code == 200


@pytest.fixture(autouse=True)
def _pin_today(monkeypatch):
    """Personal years depend on the calendar; pin it so these tests do not age."""
    from datetime import date
    monkeypatch.setattr(mc, "_today", lambda: date(2026, 11, 3))