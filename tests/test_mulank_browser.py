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
    mobile = size[0] <= 640

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
        opened = []
        page.on("popup", lambda pg: opened.append(pg.url))

        # 1. landing: the form only. No price, no payment button, no 'how it is worked out' section, consent unticked
        body = page.inner_text("body")
        assert "₹" not in body and "How your two numbers are worked out" not in body and page.locator(".how").count() == 0
        assert not page.is_visible("#mkModal") and not page.is_visible("#mkFoot")
        assert not page.is_checked("#f-consent") and page.locator("#f-marketing").count() == 0
        assert page.evaluate("document.documentElement.scrollWidth") <= size[0]

        # 2. submitting without accepting the Terms is refused in the page (no request is made)
        page.fill("#f-name", "Priya Sharma")
        page.fill("#f-dd", "29")
        page.select_option("#f-mm", "7")
        page.fill("#f-yy", "1990")
        page.fill("#f-phone", "98%08d" % (int(time.time()) % 100000000))
        posted = []
        page.on("request", lambda r: posted.append(r.url) if r.url.endswith("/api/mulank") and r.method == "POST" else None)
        page.click("#mkGo")
        page.wait_for_selector("#h-consent", state="visible", timeout=5000)
        assert not posted and not page.is_visible("#mkModal")

        # 3. accept, submit: the loading screen shows, then the preview opens in a modal on the SAME url
        page.check("#f-consent")
        page.click("#mkGo")
        page.wait_for_selector("#mkModal", state="visible", timeout=20000)
        page.wait_for_selector("#mkFrame section.page", state="visible", timeout=20000)
        assert page.url == url0 and "/preview/" not in page.url and not opened and page.locator("iframe").count() == 0
        assert page.locator("#mkFrame section.page").count() == 5
        assert page.evaluate("document.body.classList.contains('mk-lock') && getComputedStyle(document.body).overflow === 'hidden'")   # page behind does not scroll
        assert page.evaluate("document.activeElement.id") == "mkClose" and page.get_attribute("#mkModal", "aria-modal") == "true"
        sheet = page.evaluate("(() => { const r=document.getElementById('mkSheet').getBoundingClientRect(); return {w:Math.round(r.width),h:Math.round(r.height),l:Math.round(r.left)}; })()")
        if mobile:
            assert sheet["w"] == size[0] and sheet["h"] == size[1] and sheet["l"] == 0, sheet          # full-screen on phones
        else:
            assert sheet["w"] <= 780 and sheet["h"] < size[1] and sheet["l"] > 0, sheet                # a large centred dialog with the page dimmed behind
            assert page.evaluate("getComputedStyle(document.getElementById('mkModal')).backgroundColor").startswith("rgba(18, 24, 50")

        # 4. the modal scrolls on its own, one scroll container, nothing overflows sideways
        info = page.evaluate("""() => { const b=document.getElementById('mkBody'), c=document.querySelector('#mkFrame').shadowRoot.querySelector('section.page').getBoundingClientRect();
            return {sh:b.scrollHeight, ch:b.clientHeight, cl:Math.round(c.left), cr:Math.round(c.right), cw:Math.round(c.width), bw:b.scrollWidth, bcw:b.clientWidth}; }""")
        assert info["sh"] > info["ch"] and info["cl"] >= 0 and info["cr"] <= size[0] and info["cw"] <= 430 and info["bw"] <= info["bcw"], info
        y0 = page.evaluate("window.scrollY")
        page.evaluate("document.getElementById('mkBody').scrollTo(0, 400)")
        page.wait_for_timeout(500)
        assert page.evaluate("document.getElementById('mkBody').scrollTop") > 100 and page.evaluate("window.scrollY") == y0   # only the modal scrolls

        # 5. the offer sits after the preview inside the modal: price, the unlock button, and the unlock bar
        page.evaluate("document.getElementById('mkUnlock').scrollIntoView()")
        assert page.is_visible("#mkUnlock") and page.is_visible("#mkFoot")
        assert "₹299" in page.inner_text("#mkPrice") and "₹499" not in page.inner_text("#mkUnlock")
        assert re.sub(r"\s+", " ", page.inner_text("#mkBuy")) == "Unlock My Full Numerology Report — ₹299"

        # 6. close (button, Escape, backdrop) and reopen: nothing is lost and the address never changes
        page.click("#mkClose")
        assert not page.is_visible("#mkModal") and page.is_visible("#mkReopen") and page.url == url0
        assert page.evaluate("getComputedStyle(document.body).overflow") != "hidden"
        page.click("#mkView")
        assert page.is_visible("#mkModal") and page.locator("#mkFrame section.page").count() == 5
        page.keyboard.press("Escape")
        assert not page.is_visible("#mkModal")
        page.click("#mkView")
        if not mobile:
            page.mouse.click(5, 5)                                              # the dimmed backdrop closes it too
            assert not page.is_visible("#mkModal")
            page.click("#mkView")
        assert page.is_visible("#mkModal")

        # 7. a failed payment, then a dismissed checkout: still locked, clear message, retry possible
        outcome["mode"] = "fail"
        page.click("#mkBuy")
        page.wait_for_selector("#mkMsg.on", timeout=10000)
        assert "did not go through" in page.inner_text("#mkMsg") and not page.is_visible("#mkPaid")
        outcome["mode"] = "dismiss"
        page.click("#mkBuy")
        page.wait_for_function("document.getElementById('mkMsg').textContent.indexOf('not completed')>-1", timeout=10000)
        assert not page.is_visible("#mkPaid") and page.is_visible("#mkUnlock") and page.is_visible("#mkModal")

        # 8. a purchase button inside the preview itself starts the same checkout, and the payment succeeds
        outcome["mode"] = "ok"
        page.locator('#mkFrame [data-action="checkout"]').first.scroll_into_view_if_needed()
        page.locator('#mkFrame [data-action="checkout"]').first.click()
        page.wait_for_selector("#mkPaid", state="visible", timeout=30000)
        assert page.url == url0 and page.is_visible("#mkModal")
        assert "Your full report is ready" in page.inner_text("#mkPaid") and page.inner_text("#mkModalT") == "Your full report"
        pf = page.locator("#mkPaidFrame")
        pf.locator("section.page").first.wait_for(timeout=30000)
        assert pf.locator("section.page").count() == 15 and "Priya Sharma" in pf.evaluate("e => e.shadowRoot.textContent")
        assert not page.is_visible("#mkFoot") and not page.is_visible("#mkUnlock")

        # 9. the PDF downloads at once; close, reload (the report comes back from the saved id) and download again, no second payment
        with page.expect_download(timeout=90000) as dl:
            page.click("#mkPaid .btn[data-dl-paid]")
        data = open(dl.value.path(), "rb").read()
        assert data.startswith(b"%PDF") and len(re.findall(rb"/Type\s*/Page(?![s\w])", data)) == 15
        page.click("#mkClose")
        page.reload()
        page.wait_for_selector("#mkReopen", state="visible", timeout=30000)
        assert page.url == url0 and not page.is_visible("#mkModal") and "full report" in page.inner_text("#rpT").lower()
        page.click("#mkView")
        page.wait_for_selector("#mkPaid", state="visible", timeout=30000)
        with page.expect_download(timeout=90000) as dl2:
            page.click("#mkPaid .btn[data-dl-paid]")
        assert open(dl2.value.path(), "rb").read().startswith(b"%PDF")
        assert len({o["receipt"] for o in rz.orders}) == 1                  # the same single order every time, however many clicks and retries
        browser.close()


def test_a_failed_document_request_can_be_retried_by_closing_and_reopening(live):
    base = live["base"]
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, headless=True)
        page = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
        fail = {"on": True}

        def handler(route):
            url = route.request.url
            if url.startswith(base):
                if "fragment=1" in url and fail["on"]:
                    return route.abort()
                return route.continue_()
            return route.abort()
        page.route("**/*", handler)
        page.goto(base + "/en/numerology")
        page.fill("#f-name", "Asha Rao"); page.fill("#f-dd", "15"); page.select_option("#f-mm", "3"); page.fill("#f-yy", "1985")
        page.fill("#f-phone", "97%08d" % (int(time.time()) % 100000000)); page.check("#f-consent"); page.click("#mkGo")
        page.wait_for_selector("#mkModal", state="visible", timeout=20000)
        page.wait_for_selector("#mkMsg.on", timeout=10000)
        assert "could not load" in page.inner_text("#mkMsg") and page.locator("#mkFrame section.page").count() == 0
        fail["on"] = False
        page.click("#mkClose"); page.click("#mkView")                                    # reopening tries again
        page.wait_for_selector("#mkFrame section.page", timeout=20000)
        assert page.locator("#mkFrame section.page").count() == 5
        browser.close()
