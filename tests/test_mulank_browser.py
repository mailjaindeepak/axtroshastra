"""Real-browser journey for /en/numerology, on mobile and desktop: form -> preview on the SAME URL -> unlock offer -> Razorpay (faked in the
browser, verified by the real server routes) -> instant 15-card report and PDF -> download again after a reload.

Runs only where Playwright for Python and a Chrome are available (set CHROME_BIN, or have Chrome installed); otherwise it is skipped.
Content approval is a TEST FIXTURE here (a registry patched in for one date of birth); the shipped ledger is untouched. No real payment is made."""
import hashlib
import hmac
import os
import re
import socket
import threading
import time
from datetime import date

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

import api  # noqa: E402
import mulank_content as mc  # noqa: E402
import numerology  # noqa: E402
import pdfgen  # noqa: E402
from test_mulank_report import Rzp, SECRET  # noqa: E402

PIN = date(2026, 11, 3)
CHROMES = [os.getenv("CHROME_BIN", ""), r"C:\Program Files\Google\Chrome\Application\chrome.exe",
           r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", "/usr/bin/google-chrome", "/usr/bin/chromium"]
CHROME = next((c for c in CHROMES if c and os.path.exists(c)), "")
pytestmark = pytest.mark.skipif(not CHROME, reason="no Chrome available (set CHROME_BIN)")

RAZORPAY_STUB = """
window.Razorpay=function(o){this.o=o;this.h={};};
window.Razorpay.prototype.on=function(e,f){this.h[e]=f;};
window.Razorpay.prototype.open=function(){var o=this.o,h=this.h;
  window.__mkPay(o.order_id).then(function(r){
    if(r.dismiss){ o.modal.ondismiss(); }
    else if(r.fail){ h['payment.failed'] && h['payment.failed']({}); }
    else { o.handler(r); }
  });};
"""


@pytest.fixture
def live(monkeypatch, tmp_path):
    import uvicorn
    E = numerology.compute_mulank(29, 7, 1990, today=PIN)
    monkeypatch.setattr(mc, "_today", lambda: PIN)
    monkeypatch.setattr(mc, "REGISTRY", {k: mc.Entry(mc.OWNER_APPROVED, editor="Test Editor", approved_by="Test Owner", approved_on="2026-11-03")
                                         for k in mc.required_keys(E)})
    rz = Rzp()
    monkeypatch.setattr(api, "RZP_SECRET", SECRET)
    monkeypatch.setattr(api, "RZP_KEY", "rzp_test_browser")
    monkeypatch.setattr(api, "rzp_client", lambda: rz)
    if CHROME:
        monkeypatch.setenv("CHROME_BIN", CHROME)
    monkeypatch.setattr(pdfgen, "PDF_DIR", str(tmp_path))
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    server = uvicorn.Server(uvicorn.Config(api.app, host="127.0.0.1", port=port, log_level="error"))
    th = threading.Thread(target=server.run, daemon=True)
    th.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield {"base": f"http://127.0.0.1:{port}", "rz": rz}
    server.should_exit = True
    th.join(timeout=10)


def _route(page, base):
    def handler(route):
        url = route.request.url
        if url.startswith(base):
            return route.continue_()
        if "checkout.razorpay.com" in url:
            return route.fulfill(status=200, content_type="application/javascript", body=RAZORPAY_STUB)
        return route.abort()                                             # no analytics or fonts from the network in tests
    page.route("**/*", handler)


@pytest.mark.parametrize("size", [(360, 740), (390, 844), (1280, 800)], ids=["mobile-360", "mobile-390", "desktop-1280"])
def test_the_whole_journey_in_a_real_browser(live, size):
    base, rz = live["base"], live["rz"]
    outcome = {"mode": "fail"}

    def pay(order_id):
        if outcome["mode"] == "dismiss":
            return {"dismiss": True}
        if outcome["mode"] == "fail":
            return {"fail": True}
        pid = "pay_" + order_id[-30:]
        rz.entity = {"id": pid, "order_id": order_id, "amount": 29900, "currency": "INR", "status": "captured", "method": "upi"}
        sig = hmac.new(SECRET.encode(), f"{order_id}|{pid}".encode(), hashlib.sha256).hexdigest()
        return {"razorpay_order_id": order_id, "razorpay_payment_id": pid, "razorpay_signature": sig}

    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, headless=True)
        ctx = browser.new_context(viewport={"width": size[0], "height": size[1]}, accept_downloads=True)
        page = ctx.new_page()
        page.expose_function("__mkPay", pay)
        _route(page, base)
        page.goto(base + "/en/numerology")
        url0 = page.url

        # 1. landing: the form only, no price and no payment button
        body = page.inner_text("body")
        assert "₹" not in body and not page.is_visible("#mkUnlock") and not page.is_visible("#mkBar") and not page.is_visible("#mkResult")
        assert page.evaluate("document.documentElement.scrollWidth") <= size[0]

        # 2. the form (three-control date, optional gender), then the preview opens on the SAME url
        page.fill("#f-name", "Priya Sharma")
        page.fill("#f-dd", "29")
        page.select_option("#f-mm", "7")
        page.fill("#f-yy", "1990")
        page.fill("#f-phone", "98%08d" % (int(time.time()) % 100000000))
        page.check("#f-consent")
        page.click("#mkGo")
        page.wait_for_selector("#mkFrame", state="visible", timeout=20000)
        frame = page.frame_locator("#mkFrame")
        frame.locator("section.page").first.wait_for(timeout=20000)
        assert page.url == url0 and "/preview/" not in page.url
        assert frame.locator("section.page").count() == 5
        assert not page.is_visible("#f-name")                               # the form made way for the preview

        # 3. mobile layout: one scroll container, nothing overflows sideways, the frame is exactly as tall as its content
        page.wait_for_timeout(600)
        info = page.evaluate("""() => { const f=document.getElementById('mkFrame'), d=f.contentDocument;
            return {fh:f.getBoundingClientRect().height, ch:Math.ceil(d.body.getBoundingClientRect().height), sh:d.documentElement.scrollHeight,
                    fw:d.documentElement.scrollWidth, cw:f.clientWidth, pw:document.documentElement.scrollWidth}; }""")
        assert abs(info["fh"] - info["ch"]) <= 6 and info["sh"] <= info["fh"] + 2, info          # no inner scrolling
        assert info["fw"] <= info["cw"] + 1 and info["pw"] <= size[0], info                       # no horizontal scrolling

        # 4. only now does the offer appear: price, the unlock button and (on every screen) the sticky bar
        assert page.is_visible("#mkUnlock") and page.is_visible("#mkBar")
        assert "₹299" in page.inner_text("#mkPrice") and "₹499" not in page.inner_text("#mkUnlock")
        assert re.sub(r"\s+", " ", page.inner_text("#mkBuy")) == "Unlock My Full Numerology Report \u2014 \u20b9299"

        # 5. a failed payment, then a dismissed checkout: still locked, clear message, retry possible
        outcome["mode"] = "fail"
        page.click("#mkBuy")
        page.wait_for_selector("#mkMsg.on", timeout=10000)
        assert "did not go through" in page.inner_text("#mkMsg") and not page.is_visible("#mkPaid")
        outcome["mode"] = "dismiss"
        page.click("#mkBuy")
        page.wait_for_function("document.getElementById('mkMsg').textContent.indexOf('not completed')>-1", timeout=10000)
        assert not page.is_visible("#mkPaid") and page.is_visible("#mkUnlock")

        # 6. a purchase button inside the preview frame hands off to the page's checkout, then payment succeeds
        outcome["mode"] = "ok"
        frame.locator('[data-action="checkout"]').first.click()
        page.wait_for_selector("#mkPaid", state="visible", timeout=30000)
        assert page.url == url0
        assert "Your full report is ready" in page.inner_text("#mkPaid")
        pf = page.frame_locator("#mkPaidFrame")
        pf.locator("section.page").first.wait_for(timeout=30000)
        assert pf.locator("section.page").count() == 15 and "Priya Sharma" in pf.locator("body").inner_text()
        assert not page.is_visible("#mkBar") and not page.is_visible("#mkUnlock")

        # 7. the PDF downloads at once, and again after a reload, with no second payment
        for attempt in range(2):
            with page.expect_download(timeout=90000) as dl:
                page.click("#mkPaid .btn[data-dl-paid]")
            path = dl.value.path()
            data = open(path, "rb").read()
            assert data.startswith(b"%PDF")
            assert len(re.findall(rb"/Type\s*/Page(?![s\w])", data)) == 15
            if attempt == 0:
                page.reload()
                page.wait_for_selector("#mkPaid", state="visible", timeout=30000)      # restored from the opaque id: back on the paid report
                assert page.url == url0 and not page.is_visible("#mkUnlock")
        assert len({o["receipt"] for o in rz.orders}) == 1                  # the same single order every time (receipt), however many clicks and retries
        browser.close()
