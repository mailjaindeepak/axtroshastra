"""One test that walks the whole customer journey across Pieces 1-6 (registry, payment, preview, form,
shared guards, paid report): landing -> form -> preview -> locked content -> CTA -> verified payment ->
paid report -> PDF. Test fixtures and stubbed Razorpay only; nothing here can reach a live gateway."""
import hashlib
import hmac
import re
from datetime import date

import pytest

import api
import db_v2
import mulank_content as mc
import mulank_fulfilment
import mulank_payment as mp
import numerology
import reports_v2

PIN = date(2026, 11, 3)
SECRET = "rzp_key_secret_journey_test"


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


def _cards(h):
    return re.findall(r'<section class="page[^"]*">.*?</section>', h, re.S)


def _words(h):
    t = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", h, flags=re.S)
    import html
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))


def test_the_whole_customer_journey_from_landing_page_to_paid_pdf(client, monkeypatch, tmp_path):
    import pdfgen
    monkeypatch.setattr(mc, "_today", lambda: PIN)
    monkeypatch.setenv("MULANK_LIST_PRICE_CONFIRMED", "1")                  # the owner has confirmed Rs 499 as the regular price
    monkeypatch.setattr(pdfgen, "PDF_DIR", str(tmp_path))
    pdf_calls = []

    def fake_pdf(key, html):
        pdf_calls.append(key)
        data = b"%PDF-1.4 journey " + hashlib.sha256(html.encode()).digest() * 40
        pdfgen.save(key, data)
        return data
    monkeypatch.setattr(pdfgen, "get_or_generate", fake_pdf)
    rz = Rzp()
    monkeypatch.setattr(api, "RZP_SECRET", SECRET)
    monkeypatch.setattr(api, "RZP_KEY", "rzp_test_journey")
    monkeypatch.setattr(api, "rzp_client", lambda: rz)
    sent = []
    monkeypatch.setattr(api, "send_whatsapp_report", lambda *a, **k: sent.append(a), raising=False)

    # 1. landing page: four fields, separate consents, no price, not indexed
    land = client.get("/en/numerology")
    assert land.status_code == 200
    for needle in ('id="f-name"', 'id="f-dd"', 'id="f-mm"', 'id="f-yy"', 'id="f-gender"', 'id="f-phone"', 'id="f-consent"'):
        assert needle in land.text

    # 2. the registry says nothing is verified yet: the SAME customer sees "unavailable", with no price or checkout
    form = {"name": "Priya Sharma", "dob": "29/07/1990", "gender": "female", "country_code": "+91", "phone": "9755500001", "consent_terms": True}
    monkeypatch.setattr(mc, "REGISTRY", {})                                  # nothing approved
    rid0 = client.post("/api/mulank", json=form).json()["report_id"]
    p0 = client.get(f"/en/numerology/preview/{rid0}")
    assert "not ready for your numbers yet" in p0.text and "₹" not in _words(p0.text) and 'data-action="checkout"' not in p0.text
    assert client.post("/api/mulank/order", json={"report_id": rid0}).status_code == 409
    assert client.get(f"/en/numerology/report/{rid0}.pdf").status_code == 404

    # 3. content is verified (TEST FIXTURE only) -> the same journey becomes purchasable
    E = numerology.compute_mulank(29, 7, 1990, today=PIN)
    monkeypatch.setattr(mc, "REGISTRY", {k: mc.Entry(mc.VERIFIED, "Test Reviewer", "2026-11-03") for k in mc.required_keys(E)})
    form["phone"] = "9755500002"
    r = client.post("/api/mulank", json=form)
    assert r.status_code == 200
    rid = r.json()["report_id"]
    rec = _report(rid)
    assert rec["payload"]["dob"] == "1990-07-29" and rec["product"] == mp.PRODUCT and not rec["paid"]

    # 4. the five-page preview: personal pages 1-2, locked page 3, CTA directly after page 3, locked page 5
    page = client.get(f"/en/numerology/preview/{rid}")
    cards = _cards(page.text)
    assert len(cards) == 5
    t = [_words(c) for c in cards]
    assert "Priya Sharma" in t[0] and "Mulank 2" in t[1] and "Locked" in t[2]
    assert "Your Numbers Are Just the Beginning." in t[3] and "₹499" in t[3] and "₹299" in t[3]
    assert cards[3] == page.text[page.text.index(cards[2]) + len(cards[2]):].lstrip("\n").split("</section>")[0] + "</section>"   # page 4 follows page 3 directly
    import numerology_preview as P
    assert P.CTA2.replace("\u00a0", " ") in t[4] and "\u20b9299" in t[4]                           # the 299 button is repeated on page 5
    for locked in cards[2:]:                                                # nothing personal or paid-only on pages 3-5
        txt = _words(locked)
        for secret in ("Priya", "Sharma", "1990", "Moon steadies", "Pearl", "Attentive listening", "Tend to pair easily"):
            assert secret not in txt
    assert 'id="vwBar"' in page.text and "checkout.razorpay.com" in page.text      # CTA also visible outside the PDF

    # 5. the five-page PDF the customer downloads
    pdf = client.get(f"/en/numerology/preview/{rid}.pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF") and pdf_calls[-1] == f"pv1_{rid}"

    # 6. the CTA starts a server-side order at the fixed price
    o = client.post("/api/mulank/order", json={"report_id": rid, "amount": 1})
    assert o.status_code == 200 and o.json()["amount"] == 29900 and o.json()["currency"] == "INR" and rz.orders[-1]["amount"] == 29900
    oid = o.json()["razorpay_order_id"]

    # 7. the shared (other-product) payment paths cannot unlock it
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 404 and client.post("/api/order", json={"report_id": rid}).status_code == 404
    assert not _report(rid)["paid"]

    # 8. a payment that fails verification changes nothing
    pid = "pay_" + oid[-30:]
    sig = hmac.new(SECRET.encode(), f"{oid}|{pid}".encode(), hashlib.sha256).hexdigest()
    body = {"razorpay_order_id": oid, "razorpay_payment_id": pid, "razorpay_signature": sig}
    rz.entity = {"id": pid, "order_id": oid, "amount": 100, "currency": "INR", "status": "captured"}
    assert client.post("/api/mulank/verify", json=body).status_code == 409 and not _report(rid)["paid"]

    # 9. the verified, captured payment unlocks it, exactly once
    rz.entity = {"id": pid, "order_id": oid, "amount": 29900, "currency": "INR", "status": "captured", "method": "upi"}
    assert client.post("/api/mulank/verify", json=body).json()["ok"] is True
    assert client.post("/api/mulank/verify", json=body).status_code == 200
    assert _report(rid)["paid"] and pdf_calls.count(rid) == 1

    # 10. the preview now leads to the paid report: 15 cards, the customer's own numbers, a PDF that downloads again and again
    assert client.get(f"/en/numerology/preview/{rid}", follow_redirects=False).headers["location"] == f"/en/numerology/report/{rid}"
    rep = client.get(f"/en/numerology/report/{rid}")
    assert len(_cards(rep.text)) == 15 and "Priya Sharma" in rep.text and "Sample report" not in rep.text
    d1, d2 = client.get(f"/en/numerology/report/{rid}.pdf"), client.get(f"/en/numerology/report/{rid}.pdf")
    assert d1.status_code == 200 and d1.content == d2.content and pdf_calls.count(rid) == 1
    assert client.post("/api/mulank/order", json={"report_id": rid}).json() == {"already_paid": True}

    # 11. nobody else gets in, nothing was messaged, and the customer was charged once
    assert client.get(f"/en/numerology/report/{rid0}.pdf").status_code == 404
    assert client.get("/en/numerology/report/guessedguessed12").status_code == 404
    assert sent == [] and len(rz.orders) == 1
    state = mulank_fulfilment.get_state(_report(rid)["payload"])
    assert state["status"] == "ready"


def _report(rid):
    conn = db_v2.get_conn()
    try:
        return reports_v2.read_report(conn, rid)
    finally:
        conn.close()
