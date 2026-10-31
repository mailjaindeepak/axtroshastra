"""Diwali Wealth & Prosperity Report: the REAL wired path through api.py.

kundli (each work type, gift on/off, both genders) -> month-free teaser -> /api/order
(amount 49900 chosen by product and stored) -> /api/verify -> delivery (text -> PDF
-> WhatsApp to the popup number) -> /report/{id} HTML with the PDF + WhatsApp buttons
-> /report/{id}.pdf. Plus the landing route, the legacy 301, the sitemap, the gift-text
validation, the narrative wiring (4 parallel calls, guards, gift never sent to the AI),
and that every other product's delivery order is unchanged (bugs.md #1 fixed for
Diwali only).

Uses the conftest throwaway MySQL. Razorpay, Chrome (pdfgen), Twilio and the AI are
stubbed: no network. Phones 912347700xx are unique across the suite (CLAUDE.md §12).
"""
import hashlib
import hmac
import json
import re

import pytest

import api
import db_v2
import diwali_bank
import narrative
import pdfgen

SECRET = "rzp_key_secret_diwali"
FAKE_PDF = b"%PDF-1.4 diwali-test" + b"0" * 2048


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
            # Razorpay's PAYMENT contact: must never receive the WhatsApp (§1)
            return {"contact": "+919999900000", "email": "", "amount": 49900, "method": "upi"}


@pytest.fixture
def wired(monkeypatch):
    """Stub the external edges only; every api.py step between them runs for real.
    Returns the list of delivery events in the order they happened."""
    events = []
    monkeypatch.setattr(api, "RZP_SECRET", SECRET)
    monkeypatch.setattr(api, "rzp_client", lambda: _StubRzp())

    def fake_pdf(rid, html):
        events.append(("pdf", rid, html))
        return FAKE_PDF
    monkeypatch.setattr(pdfgen, "get_or_generate", fake_pdf)
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
            "product": "diwali", "variant": "/en/diwali", "work_type": "job",
            "steering": None, "gift_mode": "self"}
    body.update(kw)
    return body


_YM = re.compile(r"\b20\d\d-\d\d\b")


def _assert_month_free(teaser):
    # preview fields carry months by design; tests/test_diwali_preview.py guards them strictly
    blob = json.dumps({k: v for k, v in teaser.items() if k != "preview"}, ensure_ascii=False)
    assert not diwali_bank._MONTH_RE.search(blob), diwali_bank._MONTH_RE.search(blob)
    assert not diwali_bank._YEAR_RE.search(blob), diwali_bank._YEAR_RE.search(blob)
    assert not _YM.search(blob)


def _amounts(rid):
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT amount_paise FROM payments WHERE report_id=%s", (rid,))
            return [r[0] for r in c.fetchall()]
    finally:
        conn.close()


CASES = [  # every work type at least once, gift on/off, both genders, skipped/picked area, T3
    dict(work_type="job", gender="female", gift_mode="gift", giver_name="Rohan",
         gift_message="Happy Diwali Maa, here is to a bright one.", phone="9123477001"),
    dict(work_type="business", gender="male", steering="money", name="Arjun Mehta",
         dob="1982-01-25", tob="06:15", phone="9123477002"),
    dict(work_type="student", gender="female", time_quality="T3", tob=None,
         name="Isha Rao", dob="2005-03-09", phone="9123477003"),
    dict(work_type="home", gender="male", steering="luck", gift_mode="gift",
         name="Mohan Lal", dob="1958-11-02", tob="21:40", phone="9123477004"),
]


@pytest.mark.parametrize("case", CASES, ids=[c["work_type"] for c in CASES])
def test_diwali_full_paid_path(client, wired, case):
    case = dict(case)
    phone = case.pop("phone")
    body = _base(**case)

    # 1) kundli -> only report_id + teaser, and the teaser never carries a month
    r = client.post("/api/kundli", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert set(data) == {"report_id", "teaser"}
    rid, teaser = data["report_id"], data["teaser"]
    _assert_month_free(teaser)
    assert len(teaser["questions"]) == 5
    # the unpaid status read (what the page polls) stays month-free too
    unpaid = client.get(f"/api/report/{rid}").json()
    assert unpaid["paid"] is False
    _assert_month_free(unpaid["teaser"])

    # 2) order: ₹499 chosen by product, stored on the payment row
    r = client.post("/api/order", json={"report_id": rid, "phone": phone})
    assert r.status_code == 200, r.text
    order = r.json()
    assert order["amount"] == 49900
    assert _amounts(rid) == [49900]

    # 3) verify -> paid -> delivery runs (TestClient runs background tasks inline)
    pid = "pay_diwali_" + case["work_type"]
    oid = order["razorpay_order_id"]
    r = client.post("/api/verify", json={"razorpay_order_id": oid, "razorpay_payment_id": pid,
                                         "razorpay_signature": _sign(oid, pid)})
    assert r.status_code == 200, r.text
    assert _amounts(rid) == [49900]
    kinds = [e[0] for e in wired if e[1] == rid]
    assert kinds == ["text", "invalidate", "pdf", "wa"]     # instant text first (O-10 3)
    wa = next(e for e in wired if e[0] == "wa")
    assert wa[2] == "+91" + phone and wa[3] == "diwali"     # popup number, never Razorpay's
    assert next(e for e in wired if e[0] == "text")[2] == "+91" + phone

    # 4) the progress screen's poll: paid + text step done (AI is off in tests)
    st = client.get(f"/api/report/{rid}").json()
    assert st["paid"] is True and st["report"]["narrative"]

    # 5) the report page: full report + PDF + WhatsApp buttons
    page = client.get(f"/report/{rid}")
    assert page.status_code == 200
    html = page.text
    assert "axPdfDl" in html and "axShare" in html
    assert "window.print();return false;" not in html
    assert 'class="page' in html and body["name"].split()[0] in html
    assert ('id="s-0-2"' in html) == (body.get("gift_mode") == "gift")    # gift page only for gifts
    if body.get("gift_message"):
        assert "Happy Diwali Maa" in html

    # 6) the PDF route serves the report HTML as a PDF (chrome stubbed), no action bar inside
    r = client.get(f"/report/{rid}.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    pdf_html = [e[2] for e in wired if e[0] == "pdf" and e[1] == rid][-1]
    assert "ax-dwbar" not in pdf_html and body["name"].split()[0] in pdf_html


def test_diwali_delivery_puts_ai_text_into_the_pdf(client, wired, monkeypatch):
    """bugs.md #1, Diwali: narrative is generated and saved BEFORE the PDF is built,
    so the PDF carries the AI text, then WhatsApp goes out."""
    line = "Your money tends to move well when you plan ahead."

    def fake_narr(payload):
        wired.append(("narrative", "-", ""))
        return {"answers.q1": line}
    monkeypatch.setattr(narrative, "generate_narrative", fake_narr)
    rid = client.post("/api/kundli", json=_base(name="Sunita Verma")).json()["report_id"]
    oid = client.post("/api/order", json={"report_id": rid, "phone": "9123477010"}).json()["razorpay_order_id"]
    client.post("/api/verify", json={"razorpay_order_id": oid, "razorpay_payment_id": "pay_dw_order",
                                     "razorpay_signature": _sign(oid, "pay_dw_order")})
    kinds = [e[0] for e in wired]
    assert kinds == ["text", "narrative", "invalidate", "pdf", "wa"]
    pdf_html = next(e[2] for e in wired if e[0] == "pdf")
    assert line in pdf_html


def test_other_products_delivery_order_unchanged(client, wired, monkeypatch):
    """Marriage keeps PDF -> narrative -> WhatsApp and never invalidates (unchanged)."""
    monkeypatch.setattr(narrative, "generate_narrative",
                        lambda p: wired.append(("narrative", "-", "")) or {})
    rid = client.post("/api/kundli", json={"name": "Order Check", "dob": "1993-02-11", "tob": "08:00",
                                           "time_quality": "T0", "place": "Delhi",
                                           "gender": "male"}).json()["report_id"]
    oid = client.post("/api/order", json={"report_id": rid, "phone": "9123477011"}).json()["razorpay_order_id"]
    client.post("/api/verify", json={"razorpay_order_id": oid, "razorpay_payment_id": "pay_dw_marriage",
                                     "razorpay_signature": _sign(oid, "pay_dw_marriage")})
    assert [e[0] for e in wired] == ["pdf", "narrative", "wa"]
    assert _amounts(rid) == [49900]


def test_diwali_input_validation(client):
    assert client.post("/api/kundli", json=_base(work_type=None)).status_code == 422
    assert client.post("/api/kundli", json=_base(gender=None)).status_code == 422
    assert client.post("/api/kundli", json=_base(steering="health")).status_code == 422
    assert client.post("/api/kundli", json=_base(gift_mode="gift", gift_message="x" * 201)).status_code == 422
    assert client.post("/api/kundli", json=_base(gift_mode="gift", giver_name="y" * 41)).status_code == 422


def test_gift_text_is_stored_as_plain_text(client):
    rid = client.post("/api/kundli", json=_base(gift_mode="gift", giver_name="<i>Ravi</i>",
                                                gift_message="Happy <b>Diwali</b>\x07 to you")).json()["report_id"]
    gift = api.get_report(rid)["payload"]["meta"]["gift"]
    assert gift == {"on": True, "giver_name": "Ravi", "message": "Happy Diwali to you"}


def test_landing_route_redirect_and_sitemap(client):
    r = client.get("/en/diwali")
    assert r.status_code == 200
    assert '<link rel="canonical" href="https://www.axtroshastra.com/en/diwali">' in r.text
    assert 'og:url' in r.text and 'name="description"' in r.text
    assert "axs-nav" in r.text or "<nav" in r.text                 # served through the nav chain
    r = client.get("/diwali?utm_source=x", follow_redirects=False)
    assert r.status_code == 301 and r.headers["location"] == "/en/diwali?utm_source=x"
    assert "/en/diwali</loc>" in client.get("/sitemap.xml").text


def test_price_is_by_product_not_variant():
    assert api._order_amount_paise({"product": "diwali",
                                    "payload": {"meta": {"variant": "/milan"}}}) == 49900


# ----------------------------------------------------------------- narrative wiring
def _payload(client):
    rid = client.post("/api/kundli", json=_base(gift_mode="gift", giver_name="Secret Giver",
                                                gift_message="secret gift words here")).json()["report_id"]
    return api.get_report(rid)["payload"]


def test_narrative_four_parallel_calls_guards_and_no_gift(client, monkeypatch):
    payload = _payload(client)
    monkeypatch.setenv("NARRATIVE_ENABLED", "1")
    groups = {g for _k, _b, g in diwali_bank.NARR_KEYS}
    assert groups == {"A", "B", "C", "D"}
    prompts = []

    def fake_call(system, user, max_tokens, timeout):
        prompts.append(user)
        assert max_tokens == narrative.MAX_TOKENS_BY_PRODUCT["diwali"]
        assert timeout == narrative.TIMEOUT_BY_PRODUCT["diwali"]
        return json.dumps({
            "answers.q1": "Money may move well for you soon.",          # good -> kept
            "answers.q2": "This is guaranteed to work.",                # banned word -> dropped
            "answers.q3": "Expect a gain in March.",                    # month outside date pages -> dropped
            "answers.q4": "Saturn in Aries helps here.",                # placement check runs
            "months.2027-03.do": "Plan in March",                       # month allowed on the 12 months
            "money.read": "Keep 37% aside.",                            # invented figure -> dropped
            "money.opener": "Money comes first for you (by chart).",    # bracket -> dropped
        })
    monkeypatch.setattr(narrative, "_call", fake_call)
    out = narrative.generate_narrative(payload)
    assert len(prompts) == 4
    for u in prompts:
        assert "Secret Giver" not in u and "secret gift words" not in u
        assert payload["meta"]["_birth"]["dob"] not in u
    assert out["answers.q1"] == "Money may move well for you soon."
    assert out["months.2027-03.do"] == "Plan in March"
    for k in ("answers.q2", "answers.q3", "money.read", "money.opener"):
        assert k not in out
    saturn = next(p["sign"] for p in payload["chart"]["planets"] if p["name"] == "Saturn")
    assert ("answers.q4" in out) == (saturn == "Aries")
    assert narrative.last_generation["sections"] == len(out)


def test_narrative_disabled_returns_empty_so_bank_fills(client, monkeypatch):
    payload = _payload(client)
    monkeypatch.setenv("NARRATIVE_ENABLED", "0")
    monkeypatch.setattr(narrative, "_call", lambda *a, **k: pytest.fail("AI called while disabled"))
    assert narrative.generate_narrative(payload) == {}


def test_diwali_still_on_its_way_after_the_wait(client, wired, monkeypatch):
    """O-10 (4): when the report isn't out by DIWALI_STILL_COMING_S, a second text
    (report link) goes to the popup number before the report message."""
    import time as _t
    monkeypatch.setattr(api, "DIWALI_STILL_COMING_S", 0.05)
    monkeypatch.setattr(narrative, "generate_narrative", lambda p: _t.sleep(0.4) or {})
    rid = client.post("/api/kundli", json=_base(name="Lata Joshi")).json()["report_id"]
    oid = client.post("/api/order", json={"report_id": rid, "phone": "9123477012"}).json()["razorpay_order_id"]
    client.post("/api/verify", json={"razorpay_order_id": oid, "razorpay_payment_id": "pay_dw_slow",
                                     "razorpay_signature": _sign(oid, "pay_dw_slow")})
    kinds = [e[0] for e in wired if e[1] == rid]
    assert kinds == ["text", "text", "invalidate", "pdf", "wa"]


def test_diwali_fast_delivery_sends_no_nudge(client, wired, monkeypatch):
    monkeypatch.setattr(api, "DIWALI_STILL_COMING_S", 0.3)
    rid = client.post("/api/kundli", json=_base(name="Meera Iyer")).json()["report_id"]
    oid = client.post("/api/order", json={"report_id": rid, "phone": "9123477013"}).json()["razorpay_order_id"]
    client.post("/api/verify", json={"razorpay_order_id": oid, "razorpay_payment_id": "pay_dw_fast",
                                     "razorpay_signature": _sign(oid, "pay_dw_fast")})
    import time as _t
    _t.sleep(0.5)                       # the cancelled timer must not fire late
    assert [e[0] for e in wired if e[1] == rid].count("text") == 1


def _kavita():
    import diwali
    return diwali.compute_diwali("Kavita Sharma", "1990-07-18", "10:30", 5.5, 28.61, 77.2,
                                 gender="female", work_type="job", steering=None, place="Pune")


def test_narrative_failed_group_retries_then_flags_fallback(monkeypatch):
    """O-10 (4): each failed group call is retried; a group that still fails is
    named in last_generation (never a silent bank fallback)."""
    monkeypatch.setenv("NARRATIVE_ENABLED", "1")
    calls = []
    monkeypatch.setattr(narrative, "_call", lambda *a, **k: calls.append(1) or "")
    out = narrative.generate_narrative(_kavita())
    assert out == {}
    assert len(calls) == 4 * (1 + narrative.DIWALI_RETRIES)
    lg = narrative.last_generation
    assert lg["mode"] == "fallback" and sorted(lg["fallback_groups"]) == sorted(
        {g for _k, _b, g in diwali_bank.NARR_KEYS})


def test_placement_guard_reads_the_nearest_planet():
    """'Jupiter ... your Sun in Karka' is a Sun claim; the guard must not pin Karka on Jupiter."""
    s = "Jupiter looks at the home part, in your Jupiter main period, with your Sun in Karka."
    assert [m.groups() for m in narrative._DIWALI_PLACEMENT_RE.finditer(s)] == [("Sun", "Karka")]
    assert [m.groups() for m in narrative._DIWALI_PLACEMENT_RE.finditer("Jupiter in Leo")] == [("Jupiter", "Leo")]
    # other products keep the original (unscoped) regex
    assert narrative._claims_ok.__defaults__[0] is narrative._PLACEMENT_RE
    assert [m.group(1) for m in narrative._PLACEMENT_RE.finditer(s)][0] == "Jupiter"
