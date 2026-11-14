"""Real-browser journey for /en/numerology, on mobile and desktop: form -> preview INLINE in the page on the SAME URL -> unlock offer -> Razorpay (faked in the
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
        assert not page.is_visible("#mkModal") and not page.is_visible("#mkResult") and page.locator("#mkFoot").count() == 0
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


        # 3. accept, submit: the loading screen shows, then the preview appears INLINE in the page, on the SAME url (no overlay, no new page)
        page.check("#f-consent")
        page.click("#mkGo")
        page.wait_for_selector("#mkResult", state="visible", timeout=20000)
        page.wait_for_selector("#mkFrame .tz-cover", state="visible", timeout=20000)
        assert page.url == url0 and "/preview/" not in page.url and not opened and page.locator("iframe").count() == 0
        assert not page.is_visible("#mkModal") and not page.evaluate("document.body.classList.contains('mk-lock')")      # nothing covers the page; the page still scrolls
        assert page.locator("#mkFrame .tz-card").count() == 2 and page.locator("#mkFrame .tz-lock").count() == 1
        order = page.evaluate("""() => { const q = s => document.querySelector(s); const pos = (a, b) => !!(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
            return {hero_trust_result_proof: pos(q('.hero'), q('.trust')) && pos(q('.trust'), q('#mkResult')) && pos(q('#mkResult'), q('section.proof')) && pos(q('section.proof'), q('section.faq'))}; }""")
        assert order["hero_trust_result_proof"]                                    # the preview sits under the hero, and the rest of the page is still there below it
        page.wait_for_function("Math.abs(document.getElementById('mkResult').getBoundingClientRect().top) < 140", timeout=10000)   # scrolled to it, smoothly
        assert page.evaluate("document.documentElement.scrollWidth") <= size[0]                                          # nothing overflows sideways
        assert page.evaluate("getComputedStyle(document.getElementById('mkResult')).backgroundColor") == "rgb(233, 225, 211)"       # the warm beige canvas
        stack = page.evaluate("""() => { const r=document.querySelector('#mkFrame').shadowRoot.querySelector('.tz').getBoundingClientRect(); return {w:Math.round(r.width), cx:Math.round(r.left+r.width/2)}; }""")
        assert abs(stack["cx"] - size[0] / 2) <= 12 and stack["w"] <= 430, stack                      # a narrow stack centred horizontally
        cover = page.locator("#mkFrame .tz-cover")
        assert cover.count() == 1 and "Priya Sharma" in cover.inner_text() and "Born 29 July 1990" in cover.inner_text()
        assert page.evaluate("getComputedStyle(document.querySelector('#mkFrame').shadowRoot.querySelector('.tz-cover')).backgroundColor") == "rgb(31, 30, 28)"   # the dark cover
        assert page.is_visible("#mkReopen") and not page.is_visible("#mkForm")                                          # the form folds into a "your preview is ready" card

        # 4. the whole page scrolls (one scroll container), the result and the rest of the page share it
        y0 = page.evaluate("window.scrollY")
        page.evaluate("window.scrollBy(0, 500)")
        page.wait_for_timeout(500)
        assert page.evaluate("window.scrollY") > y0 + 100

        # 5. as on Career: a locked "answers are ready" card with the unlock button, then the white sticky bar is the unlock bar
        page.evaluate("document.querySelector('#mkFrame').shadowRoot.querySelector('.tz-lock').scrollIntoView()")
        cta = page.locator("#mkFrame .tz-cta")
        assert cta.is_visible() and page.is_visible("#stickyBar") and page.locator("#mkFrame .tz-ans").count() == 5 and page.locator("#mkFrame .tz-chip").count() == 4
        assert re.sub(r"\s+", " ", cta.inner_text()) == "Unlock My Full Numerology Report — ₹299" and "₹499" not in page.inner_text("#mkResult")
        assert page.inner_text("#stL1") == "Numerology Report" and "₹299" in page.inner_text("#stL2") and page.inner_text("#stickyBtn") == "Unlock ₹299"
        assert page.evaluate("getComputedStyle(document.getElementById('stickyBar')).backgroundColor") == "rgb(255, 255, 255)"      # the white sticky bar
        assert "left" not in page.inner_text("#stickyBar") and "Launch offer" not in page.inner_text("#mkResult")                  # no countdown
        assert not re.search(r"★|reviews|NASA|IIT", page.inner_text("#mkResult"))                                           # nothing borrowed from Career inside the report

        # 6. "View my preview" brings the result back into view; the address never changes and nothing is lost
        page.evaluate("window.scrollTo(0, 0)")
        page.click("#mkView")
        page.wait_for_function("Math.abs(document.getElementById('mkResult').getBoundingClientRect().top) < 140", timeout=10000)
        assert page.url == url0 and page.locator("#mkFrame .tz-card").count() == 2 and not page.is_visible("#mkModal")

        # 7. a failed payment, then a dismissed checkout: still locked, clear message, retry possible
        outcome["mode"] = "fail"
        page.click("#stickyBtn")                                                   # the sticky bar IS the unlock button once the report is offered
        page.wait_for_selector("#mkMsg.on", timeout=10000)
        assert "did not go through" in page.inner_text("#mkMsg") and not page.is_visible("#mkPaid")
        outcome["mode"] = "dismiss"
        cta.click()
        page.wait_for_function("document.getElementById('mkMsg').textContent.indexOf('not completed')>-1", timeout=10000)
        assert not page.is_visible("#mkPaid") and cta.is_visible()

        # 8. the sticky bar and a purchase button inside the preview start the same checkout; the payment succeeds and the report appears inline
        outcome["mode"] = "ok"
        page.locator('#mkFrame [data-action="checkout"]').first.scroll_into_view_if_needed()
        page.locator('#mkFrame [data-action="checkout"]').first.click()
        page.wait_for_selector("#mkPaid", state="visible", timeout=30000)
        assert page.url == url0 and not page.is_visible("#mkModal") and page.is_visible("#mkResult")
        assert "Your full report is ready" in page.inner_text("#mkPaid")
        pf = page.locator("#mkPaidFrame")
        pf.locator("section.page").first.wait_for(timeout=30000)
        assert pf.locator("section.page").count() == 15 and "Priya Sharma" in pf.evaluate("e => e.shadowRoot.textContent")
        assert page.inner_text("#stL1") == "Your full report is ready" and page.inner_text("#stickyBtn") == "View Report"       # the bar no longer offers to buy

        # 9. the PDF downloads at once; reload (the report comes back inline from the saved id) and download again, no second payment
        with page.expect_download(timeout=90000) as dl:
            page.click("#mkPaid .btn[data-dl-paid]")
        data = open(dl.value.path(), "rb").read()
        assert data.startswith(b"%PDF") and len(re.findall(rb"/Type\s*/Page(?![s\w])", data)) == 15
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


def test_a_failed_document_request_can_be_retried_with_view_my_preview(live):
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
        page.wait_for_selector("#mkResult", state="visible", timeout=20000)
        page.wait_for_selector("#mkMsg.on", timeout=10000)
        assert "could not load" in page.inner_text("#mkMsg") and page.locator("#mkFrame .tz-cover").count() == 0
        fail["on"] = False
        page.click("#mkView")                                                            # "View my preview" tries again
        page.wait_for_selector("#mkFrame .tz-cover", timeout=20000)
        assert page.locator("#mkFrame .tz-card").count() == 2 and not page.is_visible("#mkMsg.on")
        browser.close()


def test_demo_pay_unlocks_the_paid_report_through_the_real_page(live):
    """The way tests/e2e/checkout.spec.js does it for the other products: the Razorpay popup is stubbed, the stub calls /api/_demo_pay/{id} (DEMO_MODE) and
    then fires the page's own success handler. Nothing else is faked: the form, the order route, the preview, the page's confirmation, the paid report.
    The handler's signature is deliberately not a real one, so the page must find the payment through the saved state (as Career Intelligence polls until
    paid), show the report inline, and fire NO Purchase event, because a demo unlock is not a sale."""
    import urllib.request
    base = live["base"]
    demo = []

    def pay(order_id):
        rid = order_id[len("order_"):]
        with urllib.request.urlopen(urllib.request.Request(f"{base}/api/_demo_pay/{rid}", method="POST"), timeout=60) as r:
            demo.append((rid, r.status))
        return {"razorpay_order_id": order_id, "razorpay_payment_id": "pay_TEST", "razorpay_signature": "not-a-real-signature"}

    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, headless=True)
        page = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
        page.expose_function("__mkPay", pay)
        _route(page, base)
        verify = []
        page.on("response", lambda r: verify.append(r.status) if r.url.endswith("/api/mulank/verify") else None)
        page.goto(base + "/en/numerology")
        url0 = page.url
        page.fill("#f-name", "Demo Buyer"); page.fill("#f-dd", "29"); page.select_option("#f-mm", "7"); page.fill("#f-yy", "1990")
        page.fill("#f-phone", "98%08d" % (int(time.time()) % 100000000)); page.check("#f-consent"); page.click("#mkGo")
        page.wait_for_selector("#mkFrame .tz-cover", state="visible", timeout=25000)
        assert page.inner_text("#stickyBtn") == "Unlock \u20b9299"

        page.click("#stickyBtn")                                                          # opens the (stubbed) popup, which demo-pays and fires the handler
        page.wait_for_selector("#mkPaid", state="visible", timeout=60000)
        pf = page.locator("#mkPaidFrame")
        pf.locator("section.page").first.wait_for(timeout=30000)
        assert pf.locator("section.page").count() == 15 and "Demo Buyer" in pf.evaluate("e => e.shadowRoot.textContent")
        assert page.url == url0 and not page.is_visible("#mkModal")
        assert demo and demo[0][1] == 200                                                 # the demo-pay route was really called
        assert verify and set(verify) == {400}                                            # the fake signature was refused by the server: only the saved state unlocked the page
        events = page.evaluate("[...window.dataLayer].filter(a => a[0] === 'event').map(a => a[1])")
        assert "begin_checkout" in events and "purchase" not in events                    # checkout started, but a demo unlock is never reported as a sale

        page.reload()                                                                      # and the paid report comes back from the saved id
        page.wait_for_selector("#mkReopen", state="visible", timeout=30000)
        assert "full report" in page.inner_text("#rpT").lower()
        browser.close()
