"""Mulank paid report: renderer rules (verified-only, no substitution, sample labelling), calculations across
birth dates, and the paid journey (payment outcomes, secure re-download, retries, recovery). Razorpay and
Chrome are stubbed except in the single real-PDF test."""
import hashlib
import hmac
import itertools
import re
from datetime import date

import pytest

import api
import db_v2
import mulank_content as mc
import mulank_fulfilment as mf
import mulank_payment as mp
import mulank_recovery as mrec
import mulank_routes
import numerology
import numerology_report as R
import payments_v2
import reports_v2

PIN = date(2026, 11, 3)
SECRET = "rzp_key_secret_report_test"
_ph = itertools.count(1)


@pytest.fixture(autouse=True)
def pinned_today(monkeypatch):
    monkeypatch.setattr(mc, "_today", lambda: PIN)


def _ver(d=29, m=7, y=1990, status=mc.VERIFIED, by="Test Reviewer"):
    E = numerology.compute_mulank(d, m, y, today=PIN)
    return {k: mc.Entry(status, by, "2026-11-03") for k in mc.required_keys(E)}


def _text(html):
    t = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))


def _cards(html):
    return re.findall(r'<section class="page[^"]*">.*?</section>', html, re.S)


# ------------------------------------------------------------------ renderer: what may be shown
def test_production_refuses_every_pair_with_the_shipped_registry():
    seen = set()
    for y in range(1950, 2010):
        for m in range(1, 13):
            for d in range(1, 10):
                try:
                    R.build_report(d, m, y, "Test", today=PIN)
                except R.ReportNotAvailable as e:
                    assert e.missing
                    seen.add(numerology.compute_mulank(d, m, y, today=PIN)["pair_key"])
                else:
                    pytest.fail("production rendered with nothing verified")
    assert len(seen) == 81


@pytest.mark.parametrize("status", [mc.SAMPLE_OK, mc.NEEDS_REVIEW, mc.PENDING])
def test_only_verified_content_can_render_in_production(status):
    with pytest.raises(R.ReportNotAvailable):
        R.build_report(29, 7, 1990, "Kiran Mehta", today=PIN, registry=_ver(status=status))


def test_verified_without_a_named_reviewer_does_not_count():
    reg = _ver()
    reg["M2"] = mc.Entry(mc.VERIFIED, "", "2026-11-03")
    with pytest.raises(R.ReportNotAvailable) as e:
        R.build_report(29, 7, 1990, "Kiran Mehta", today=PIN, registry=reg)
    assert "M2" in e.value.missing


def test_every_single_missing_key_blocks_production():
    base = _ver()
    for k in list(base):
        reg = {x: v for x, v in base.items() if x != k}
        with pytest.raises(R.ReportNotAvailable):
            R.build_report(29, 7, 1990, "Kiran Mehta", today=PIN, registry=reg)


def test_verified_registry_renders_the_full_unlabelled_report():
    r = R.build_report(29, 7, 1990, "Kiran Mehta", today=PIN, registry=_ver())
    assert r["n_cards"] == 15 and len(_cards(r["html"])) == 15 and r["mode"] == "production"
    h = r["html"]
    assert "Sample report" not in h and "SAMPLE" not in h and "not production-verified" not in h and "PENDING EXPERT REVIEW" not in h
    assert "Your Mulank Numerology Report" in h and 'name="robots" content="noindex' in h
    assert not [t for t, _ in r["trace"] if t.startswith(("F-", "4i", "8i", "8j", "9g", "14g", "10a", "13a"))]


def test_approved_but_undrafted_block_never_borrows_another_numbers_reading(monkeypatch):
    import mulank_bank as bank
    monkeypatch.delitem(bank.PG, 5)
    with pytest.raises(R.ReportNotAvailable) as e:
        R.build_report(15, 3, 1985, "Test", today=PIN, registry=_ver(15, 3, 1985))              # Bhagyank 5 has no text
    assert "text:PG5" in e.value.missing


def test_each_pair_gets_its_own_numbers_text_and_never_anothers():
    a = R.build_report(29, 7, 1990, "Kiran Mehta", today=PIN, registry=_ver())["html"]                 # 2-1
    b = R.build_report(15, 3, 1985, "Kiran Mehta", today=PIN, registry=_ver(15, 3, 1985))["html"]      # 6-5
    ta, tb = _text(a), _text(b)
    assert "Moon steadies, Sun leads" in ta and "Moon steadies, Sun leads" not in tb
    assert "Venus" in tb and "Mercury" in tb
    assert a != b

def test_sample_mode_is_labelled_on_every_page_and_refused_with_live_keys(monkeypatch):
    r = R.build_report(29, 7, 1990, "Kiran Mehta", today=PIN, mode="sample")
    assert r["html"].count("Sample report") == r["n_cards"] and "SAMPLE (test document" in r["html"]
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_live_NOT_A_REAL_KEY")
    with pytest.raises(RuntimeError):
        R.build_report(29, 7, 1990, "Kiran Mehta", today=PIN, mode="sample")
    with pytest.raises(ValueError):
        R.build_report(29, 7, 1990, "Kiran Mehta", today=PIN, mode="draft")


def test_unverified_registry_entries_can_never_make_a_pair_sellable():
    for status in (mc.SAMPLE_OK, mc.NEEDS_REVIEW, mc.PENDING):
        reg = _ver(status=status)
        assert mc.pair_readiness(29, 7, 1990, today=PIN, registry=reg)["eligible"] is False
    assert mc.pair_readiness(29, 7, 1990, today=PIN, registry=_ver())["eligible"] is True
    assert not [k for k, e in mc.REGISTRY.items() if e.status == mc.VERIFIED]


def test_renderer_key_gate_itself_is_strict():
    ok = R._ok
    assert ok({"K": mc.Entry(mc.VERIFIED, "Rev", "2026-11-03")}, "K", False) is True
    assert ok({"K": mc.Entry(mc.VERIFIED, "", "2026-11-03")}, "K", False) is False
    assert ok({"K": mc.Entry(mc.VERIFIED, "Rev", "")}, "K", False) is False
    for st in (mc.SAMPLE_OK, mc.NEEDS_REVIEW, mc.PENDING):
        assert ok({"K": mc.Entry(st, "Rev", "2026-11-03")}, "K", False) is False
    assert ok({"K": mc.Entry(mc.SAMPLE_OK)}, "K", True) is True and ok({"K": mc.Entry(mc.NEEDS_REVIEW)}, "K", True) is False
    assert ok({}, "K", True) is False


def test_text_must_exist_for_the_production_ledger(monkeypatch):
    monkeypatch.setattr(mc, "REGISTRY", _ver(15, 3, 1985))
    r = mc.pair_readiness(15, 3, 1985, today=PIN)
    assert r["eligible"] is True
    import mulank_bank as bank
    monkeypatch.delitem(bank.PG, 5)
    assert mc.pair_readiness(15, 3, 1985, today=PIN)["eligible"] is False
    monkeypatch.setattr(mc, "REGISTRY", _ver())
    assert mc.pair_readiness(29, 7, 1990, today=PIN)["eligible"] is True


# ------------------------------------------------------------------ calculations across dates
@pytest.mark.parametrize("dob,mulank,bhagyank", [
    ((29, 7, 1990), "Birth day 29<br>2 + 9 = 11<br>1 + 1 = <b>2</b>", "2+9+0+7+1+9+9+0 = 37<br>3 + 7 = 10, then 1 + 0 = <b>1</b>"),
    ((15, 3, 1985), "Birth day 15<br>1 + 5 = <b>6</b>", "1+5+0+3+1+9+8+5 = 32<br>3 + 2 = <b>5</b>"),
    ((22, 11, 2000), "Birth day 22<br>2 + 2 = <b>4</b>", "2+2+1+1+2+0+0+0 = <b>8</b>"),
    ((9, 9, 1999), "Birth day 9 = <b>9</b>", "0+9+0+9+1+9+9+9 = 46<br>4 + 6 = 10, then 1 + 0 = <b>1</b>"),
    ((1, 1, 1901), "Birth day 1 = <b>1</b>", "0+1+0+1+1+9+0+1 = 13<br>1 + 3 = <b>4</b>"),
])
def test_calculations_are_exact_for_many_birth_dates(dob, mulank, bhagyank):
    r = R.build_report(*dob, "Test Person", today=PIN, mode="sample")
    h = _cards(r["html"])[2]
    assert mulank in h and bhagyank in h
    E = numerology.compute_mulank(*dob, today=PIN)
    assert f'<div class="hg" style="font-size:54px;line-height:1">{E["mulank"]["number"]}</div>' in h


def test_personal_years_are_correct_and_roll_with_the_calendar():
    h = _text(R.build_report(29, 7, 1990, "Test", today=PIN, mode="sample")["html"])
    assert "59 days remain" in h and "begins on 1 January 2027" in h and "11 + 7 + 10 = 28" in h
    r2 = R.build_report(29, 7, 1990, "Test", today=date(2027, 3, 1), mode="sample")
    h2 = _text(r2["html"])
    assert "2027 &middot; this year" in h2 and "2028 &middot; next year" in h2 and "306 days remain" in h2


def test_eleven_and_twenty_two_are_always_reduced_with_the_note():
    h = _cards(R.build_report(29, 7, 1990, "T", today=PIN, mode="sample")["html"])[2]
    assert "passes through 11 before reducing to 2" in h and R.bank.row("3a") in h.replace("&amp;", "&")


def test_equal_number_pairs_and_all_81_pairs_render_without_error():
    pairs = {}
    for y in range(1950, 2010):
        for m in range(1, 13):
            for d in range(1, 29):
                pairs.setdefault(numerology.compute_mulank(d, m, y, today=PIN)["pair_key"], (d, m, y))
    assert len(pairs) == 81
    for pk, dob in pairs.items():
        r = R.build_report(*dob, "Pair Test", today=PIN, mode="sample")
        assert r["pair_key"] == pk and r["n_cards"] in (12, 15) and f"Mulank</div><div class=\"hg\"" in r["html"]


def test_name_is_escaped_and_validated():
    h = R.build_report(29, 7, 1990, '<script>alert(1)</script> "Q"', today=PIN, mode="sample")["html"]
    assert "<script>alert" not in h and "&lt;script&gt;" in h
    for bad in ("", "  ", "x" * 81):
        with pytest.raises(ValueError):
            R.build_report(29, 7, 1990, bad, today=PIN, mode="sample")
    with pytest.raises(numerology.NumerologyInputError):
        R.build_report(31, 2, 1990, "Name", today=PIN, mode="sample")


def test_wording_matches_the_approved_rows_verbatim():
    t = _text(R.build_report(29, 7, 1990, "Kiran Mehta", today=PIN, registry=_ver())["html"])
    norm = lambda s: re.sub(r"\s+", " ", s.replace("&amp;", "&")).strip()
    for rid in ("2a", "2b", "2c", "3a", "3b", "7b", "9c", "11a", "11c", "13c", "15b", "D"):
        assert norm(R.bank.row(rid)) in norm(t), rid


# ------------------------------------------------------------------ the paid journey
class Rzp:
    def __init__(self):
        self.entity, self.by_order, self.orders = {}, {}, []
        outer = self

        class order:
            @staticmethod
            def create(d):
                outer.orders.append(d)
                return {"id": "order_" + d["receipt"][-30:], "amount": d["amount"], "currency": d["currency"]}

            @staticmethod
            def payments(oid):
                return {"items": outer.by_order.get(oid, [])}

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
    calls = {"n": 0, "fail": False}

    def fake(key, html):
        calls["n"] += 1
        if calls["fail"]:
            return None
        data = b"%PDF-1.4 fake " + hashlib.sha256(html.encode()).digest() * 40
        pdfgen.save(key, data)
        return data
    monkeypatch.setattr(pdfgen, "get_or_generate", fake)
    return calls


@pytest.fixture
def fulfilled(monkeypatch):
    calls = []
    real = mf.schedule
    monkeypatch.setattr(mulank_routes, "FULFIL", lambda rid, bg: (calls.append(rid), real(rid, None)))
    return calls


@pytest.fixture(autouse=True)
def no_whatsapp(monkeypatch):
    sent = []
    for name in ("send_whatsapp_report", "email_report"):
        monkeypatch.setattr(api, name, lambda *a, **k: sent.append(a), raising=False)
    return sent


@pytest.fixture
def eligible(monkeypatch):
    monkeypatch.setattr(mc, "REGISTRY", _ver())


def _make(client, name="Priya Sharma", dob="29/07/1990"):
    r = client.post("/api/mulank", json={"name": name, "dob": dob, "country_code": "+91", "phone": "96%08d" % (70000000 + next(_ph)),
                                         "consent_terms": True})
    assert r.status_code == 200, r.text
    rid = r.json()["report_id"]
    o = client.post("/api/mulank/order", json={"report_id": rid})
    assert o.status_code == 200, o.text
    return rid, o.json()["razorpay_order_id"]


def _ent(oid, **kw):
    e = {"id": "pay_" + oid[-30:], "order_id": oid, "amount": 29900, "currency": "INR", "status": "captured", "method": "upi",
         "contact": "+919800000000", "email": "x@example.com"}
    e.update(kw)
    return e


def _verify(client, rz, oid, **kw):
    rz.entity = _ent(oid, **kw)
    pid = rz.entity["id"]
    sig = hmac.new(SECRET.encode(), f"{oid}|{pid}".encode(), hashlib.sha256).hexdigest()
    return client.post("/api/mulank/verify", json={"razorpay_order_id": oid, "razorpay_payment_id": pid, "razorpay_signature": sig})


def _paid(rid):
    conn = db_v2.get_conn()
    try:
        return reports_v2.read_report(conn, rid)["paid"]
    finally:
        conn.close()


def _payment_rows(rid):
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*), SUM(status='captured') FROM payments WHERE report_id=%s", (rid,))
            return cur.fetchone()
    finally:
        conn.close()


def _state(rid):
    conn = db_v2.get_conn()
    try:
        return mf.get_state(reports_v2.read_report(conn, rid)["payload"])
    finally:
        conn.close()


def test_successful_payment_unlocks_the_report_and_pdf_and_it_can_be_downloaded_again(client, rz, eligible, pdfs, fulfilled, no_whatsapp):
    rid, oid = _make(client)
    assert client.get(f"/en/numerology/report/{rid}.pdf").status_code == 404           # locked before payment
    assert client.get(f"/en/numerology/report/{rid}", follow_redirects=False).status_code == 302
    r = _verify(client, rz, oid)
    assert r.status_code == 200 and r.json()["ok"] is True and _paid(rid)
    page = client.get(f"/en/numerology/report/{rid}")
    assert page.status_code == 200 and len(_cards(page.text)) == 15 and "Priya Sharma" in page.text and "Download My Full Report" in page.text
    assert "Sample report" not in page.text
    assert page.headers["cache-control"] == "no-store" and "noindex" in page.headers["x-robots-tag"]
    pdf1 = client.get(f"/en/numerology/report/{rid}.pdf")
    assert pdf1.status_code == 200 and pdf1.content.startswith(b"%PDF") and pdf1.headers["cache-control"] == "no-store"
    assert pdf1.headers["content-disposition"] == 'attachment; filename="Axtroshastra-Numerology-Report.pdf"'
    pdf2 = client.get(f"/en/numerology/report/{rid}.pdf")
    assert pdf2.content == pdf1.content and pdfs["n"] == 1                               # cached, generated once
    assert client.post("/api/mulank/order", json={"report_id": rid}).json() == {"already_paid": True}   # never pays twice
    assert fulfilled == [rid] and _state(rid)["status"] == mf.READY
    assert no_whatsapp == []                                                              # no WhatsApp message is sent


def test_failed_pending_and_mismatched_payments_never_unlock(client, rz, eligible, pdfs, fulfilled):
    for kw in ({"status": "failed"}, {"status": "authorized"}, {"amount": 100}, {"currency": "USD"}, {"order_id": "order_other"}):
        rid, oid = _make(client)
        _verify(client, rz, oid, **kw)
        assert not _paid(rid), kw
        assert client.get(f"/en/numerology/report/{rid}", follow_redirects=False).status_code == 302
        assert client.get(f"/en/numerology/report/{rid}.pdf").status_code == 404
    assert fulfilled == [] and pdfs["n"] == 0


def test_pending_payment_that_later_captures_unlocks_without_a_second_charge(client, rz, eligible, pdfs, fulfilled):
    rid, oid = _make(client)
    assert _verify(client, rz, oid, status="authorized").json()["status"] == "pending" and not _paid(rid)
    assert _verify(client, rz, oid).json()["ok"] is True and _paid(rid)
    assert len(rz.orders) == 1 and _payment_rows(rid)[0] == 1


def test_duplicate_callbacks_fulfil_exactly_once(client, rz, eligible, pdfs, fulfilled):
    rid, oid = _make(client)
    for _ in range(3):
        assert _verify(client, rz, oid).status_code == 200
    ev = {"event": "payment.captured", "payload": {"payment": {"entity": _ent(oid)}}}
    raw = __import__("json").dumps(ev).encode()
    sig = hmac.new(api.RZP_WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    for _ in range(2):
        assert client.post("/api/mulank/webhook", content=raw, headers={"X-Razorpay-Signature": sig}).status_code == 200
    assert fulfilled == [rid] and pdfs["n"] == 1 and _payment_rows(rid) == (1, 1)


def test_pdf_failure_is_recorded_then_retried_without_recharging_or_duplicate_fulfilment(client, rz, eligible, pdfs, fulfilled):
    rid, oid = _make(client)
    pdfs["fail"] = True
    assert _verify(client, rz, oid).status_code == 200 and _paid(rid)                   # money confirmed, entitlement recorded
    assert _state(rid)["status"] == mf.FAILED and _state(rid)["last_error"] == "pdf_unavailable"
    assert client.get(f"/en/numerology/report/{rid}.pdf").status_code == 503
    page = client.get(f"/en/numerology/report/{rid}")
    assert page.status_code == 200 and len(_cards(page.text)) == 15                       # the report is still readable online
    assert client.post(f"/api/mulank/report/{rid}/retry").json() == {"status": "failed"}
    pdfs["fail"] = False
    assert client.post(f"/api/mulank/report/{rid}/retry").json() == {"status": "ready"}
    assert client.get(f"/en/numerology/report/{rid}.pdf").status_code == 200
    assert client.post(f"/api/mulank/report/{rid}/retry").json() == {"status": "ready"}   # idempotent
    assert fulfilled == [rid] and _payment_rows(rid) == (1, 1) and len(rz.orders) == 1
    assert set(_state(rid)) <= {"status", "attempts", "last_error", "updated", "prepared_on"}            # no personal data in state


def test_retry_needs_a_paid_report_and_is_rate_limited(client, rz, eligible, pdfs, monkeypatch):
    rid, _ = _make(client)
    assert client.post(f"/api/mulank/report/{rid}/retry").status_code == 404
    assert client.post("/api/mulank/report/nonexistent123/retry").status_code == 404
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "1")
    mulank_routes._hits.clear()
    codes = [client.post("/api/mulank/report/nonexistent123/retry").status_code for _ in range(9)]
    assert codes[:6] == [404] * 6 and 429 in codes[6:]
    mulank_routes._hits.clear()


def test_content_that_stops_being_verified_after_payment_shows_nothing_unverified(client, rz, eligible, pdfs, fulfilled, monkeypatch):
    rid, oid = _make(client)
    assert _verify(client, rz, oid).status_code == 200
    monkeypatch.setattr(mc, "REGISTRY", dict(_ver(status=mc.NEEDS_REVIEW)))
    pdfs["n"] = 0
    import pdfgen
    for p in (pdfgen.cache_path(rid),):
        import os
        if os.path.exists(p):
            os.unlink(p)
    page = client.get(f"/en/numerology/report/{rid}")
    assert page.status_code == 200 and "Payment received" in page.text and "Moon steadies" not in page.text
    assert _state(rid)["last_error"] == "content_unavailable"
    assert client.get(f"/en/numerology/report/{rid}.pdf").status_code == 503
    assert client.post(f"/api/mulank/report/{rid}/retry").json() == {"status": "failed"}


def test_other_customers_cannot_reach_a_report(client, rz, eligible, pdfs, fulfilled):
    a, oid_a = _make(client, name="Alpha Customer")
    b, _ = _make(client, name="Bravo Customer")
    _verify(client, rz, oid_a)
    assert "Alpha Customer" in client.get(f"/en/numerology/report/{a}").text
    assert client.get(f"/en/numerology/report/{b}", follow_redirects=False).status_code == 302   # B never paid
    assert client.get(f"/en/numerology/report/{b}.pdf").status_code == 404
    assert client.post(f"/api/mulank/report/{b}/retry").status_code == 404
    other = "ot%030d" % next(_ph)
    conn = db_v2.get_conn()
    try:
        reports_v2.save_report(conn, other, {"product": "iq_test", "meta": {}}, [], product="iq_test", phone="9833300001")
        db_v2.set_report_paid(conn, other)
        conn.commit()
    finally:
        conn.close()
    bodies = {client.get(p).text for p in (f"/en/numerology/report/{other}", f"/en/numerology/report/{other}.pdf",
                                           "/en/numerology/report/zzzzzzzzzzzz", "/en/numerology/report/zzzzzzzzzzzz.pdf")}
    assert len(bodies) == 1 and "Alpha" not in next(iter(bodies))
    r = client.get(f"/en/numerology/report/{b}.pdf", headers={"X-Report-Id": a}, cookies={"rid": a})
    assert r.status_code == 404


def test_real_pdf_for_a_paid_report_is_fifteen_readable_pages(client, rz, eligible, monkeypatch, tmp_path):
    fitz = pytest.importorskip("pymupdf")
    import pdfgen
    monkeypatch.setattr(pdfgen, "PDF_DIR", str(tmp_path))
    monkeypatch.setattr(mulank_routes, "FULFIL", lambda rid, bg: None)
    rid, oid = _make(client)
    assert _verify(client, rz, oid).status_code == 200
    r = client.get(f"/en/numerology/report/{rid}.pdf")
    if r.status_code == 503:
        pytest.skip("headless Chrome not available")
    doc = fitz.open(stream=r.content, filetype="pdf")
    assert len(doc) == 15 and all(round(p.rect.width) == 323 and round(p.rect.height) == 623 for p in doc)
    txt = " ".join(p.get_text() for p in doc)
    assert "Priya Sharma" in txt and "Sample report" not in txt and "Your two numbers" in txt


# ------------------------------------------------------------------ Mulank-specific payment recovery
def _unpaid_with_order(client):
    return _make(client)


def _settle_via_recovery(rz, oid, **kw):
    rz.by_order[oid] = [_ent(oid, **kw)]
    return mrec.recover(rz)


def test_recovery_settles_a_verified_captured_payment_once(client, rz, eligible, pdfs):
    rid, oid = _unpaid_with_order(client)
    res = _settle_via_recovery(rz, oid)
    assert res["recovered"] == 1 and res["paid"] == [rid] and _paid(rid)
    assert mrec.recover(rz)["paid"] == [] and _payment_rows(rid) == (1, 1)                # a second sweep fulfils nothing


@pytest.mark.parametrize("kw", [{"amount": 100}, {"amount": 49900}, {"currency": "USD"}, {"status": "authorized"}, {"status": "failed"},
                                {"order_id": "order_not_ours"}, {"amount_refunded": 100}, {"id": ""}])
def test_recovery_rejects_anything_that_fails_verification(client, rz, eligible, pdfs, kw):
    rid, oid = _unpaid_with_order(client)
    res = _settle_via_recovery(rz, oid, **kw)
    assert res["recovered"] == 0 and res["paid"] == [] and not _paid(rid)


def test_recovery_ignores_other_products_and_unpaid_orders_without_a_capture(client, rz, eligible, pdfs):
    rid, oid = _unpaid_with_order(client)
    assert mrec.recover(rz)["recovered"] == 0 and not _paid(rid)
    other = "rc%030d" % next(_ph)
    conn = db_v2.get_conn()
    try:
        uid = reports_v2.save_report(conn, other, {"product": "iq_test", "meta": {}}, [], product="iq_test", phone="9844400001")
        payments_v2.record_order(conn, other, uid, 4900, "order_iq_rec_" + other[-12:])
        conn.commit()
    finally:
        conn.close()
    rz.by_order["order_iq_rec_" + other[-12:]] = [_ent("order_iq_rec_" + other[-12:], amount=4900)]
    assert mrec.recover(rz)["recovered"] == 0 and not _paid(other)


def test_returning_to_the_preview_recognises_a_payment_that_was_never_confirmed(client, rz, eligible, pdfs, fulfilled):
    rid, oid = _unpaid_with_order(client)
    rz.by_order[oid] = [_ent(oid)]
    r = client.get(f"/en/numerology/preview/{rid}", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == f"/en/numerology/report/{rid}"
    assert _paid(rid) and fulfilled == [rid]
    assert client.get(f"/en/numerology/preview/{rid}", follow_redirects=False).status_code == 302


def test_preview_does_not_unlock_on_a_bad_payment(client, rz, eligible, pdfs, fulfilled):
    rid, oid = _unpaid_with_order(client)
    rz.by_order[oid] = [_ent(oid, amount=100)]
    r = client.get(f"/en/numerology/preview/{rid}", follow_redirects=False)
    assert r.status_code == 200 and not _paid(rid) and fulfilled == []


def test_recovery_loop_only_starts_with_payment_keys(monkeypatch):
    monkeypatch.setattr(api, "RZP_KEY", "")
    monkeypatch.setattr(api, "RZP_SECRET", "")
    monkeypatch.setattr(mrec, "_started", False)
    mulank_routes._start_mulank_recovery()
    assert mrec._started is False


def test_shared_reconcile_is_unchanged_for_other_products_and_still_skips_mulank(client, rz, eligible, pdfs, monkeypatch):
    import payments
    rid, oid = _unpaid_with_order(client)
    monkeypatch.setattr(payments, "configured", lambda: True)
    monkeypatch.setattr(payments, "_rzp", lambda: rz)
    rz.by_order[oid] = [_ent(oid)]
    api._reconcile_and_deliver()
    assert not _paid(rid)                                                               # the shared sweep never grants Mulank access

def test_a_delivered_report_does_not_change_after_new_year(client, rz, eligible, pdfs, fulfilled, monkeypatch):
    """The report date is frozen at first fulfilment: the web page and the PDF keep the personal years and the
    prepared date that were delivered, even if the customer opens them after 1 January."""
    rid, oid = _make(client)
    assert _verify(client, rz, oid).status_code == 200
    assert mf.prepared_on(_state_payload(rid)).isoformat() == "2026-11-03"
    first = client.get(f"/en/numerology/report/{rid}").text
    assert "Report prepared 3 November 2026" in first and "2026 &middot; this year" in first
    pdf1 = client.get(f"/en/numerology/report/{rid}.pdf").content
    monkeypatch.setattr(mc, "_today", lambda: date(2027, 2, 10))                      # the customer comes back after New Year
    later = client.get(f"/en/numerology/report/{rid}").text
    assert "Report prepared 3 November 2026" in later and "2026 &middot; this year" in later and "2027 &middot; this year" not in later
    assert client.get(f"/en/numerology/report/{rid}.pdf").content == pdf1


def _state_payload(rid):
    conn = db_v2.get_conn()
    try:
        return reports_v2.read_report(conn, rid)["payload"]
    finally:
        conn.close()
