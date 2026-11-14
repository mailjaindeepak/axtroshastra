"""Numerology funnel events: fired by the real page, accepted by /api/event, and SAVED in the `events` table.
Also: the page is registered where the site watches its pages (sitemap, robot page list, robot funnel smoke).

Real Chrome, real server, real database. Razorpay is faked in the browser exactly as test_mulank_browser does; no real payment is made.
Privacy rule under test: the report id is a private link token, so the browser sends only the one-way hash (mk_...) and the server stores
report_id NULL for it. Nothing in `events` may contain the raw report id."""
import hashlib
import hmac
import re
import time
from pathlib import Path

import pytest

import api
import db_v2
from test_mulank_report import SECRET

ROOT = Path(__file__).resolve().parent.parent
ROBOT = (ROOT / "ops" / "robot_customer" / "robot.spec.js").read_text(encoding="utf-8")
PAGE = (ROOT / "pages" / "numerology.html").read_text(encoding="utf-8")


# ---------------------------------------------------------------- registration (no browser needed)

def test_numerology_is_in_the_sitemap():
    from fastapi.testclient import TestClient
    assert "/en/numerology</loc>" in TestClient(api.app).get("/sitemap.xml").text


def test_robot_checks_the_numerology_page_and_funnel():
    assert re.search(r"path:\s*'/en/numerology'", ROBOT), "robot ALL_PAGES must list /en/numerology"
    m = re.search(r"\{\s*name:\s*'numerology',(.*?)\n  \},", ROBOT, re.S)
    assert m, "robot FUNNELS must have a numerology entry"
    block = m.group(1)
    assert "'/en/numerology'" in block and "#mkForm" in block and "fill: fillNumerology" in block
    assert "hasTeaser: true" in block and "teaser: '#mkResult'" in block and "mk_rid" in block


def test_robot_numerology_lead_is_removable_by_the_cleanup_job(client):
    """The robot's lead must be found by the REAL cleanup job (it matches report_subjects.name on unpaid reports), or every
    scheduled run leaves a real-looking lead behind. Create a lead under the robot's exact name and run the cleanup on it."""
    import dashboard.store as store
    name = re.search(r"fill\('#f-name',\s*'([^']+)'\)", ROBOT[ROBOT.index("async function fillNumerology"):]).group(1)
    before = store.robot_cleanup(None, dry_run=True)["would_delete"]
    r = client.post("/api/mulank", json={"name": name, "dob": "29/07/1990", "country_code": "+91",
                                         "phone": "9592%06d" % (int(time.time() * 1000) % 1000000), "consent_terms": True})
    assert r.status_code == 200, r.text
    assert store.robot_cleanup(None, dry_run=True)["would_delete"] == before + 1
    assert store.robot_cleanup(None, dry_run=False)["deleted"] >= 1
    assert store.robot_cleanup(None, dry_run=True)["would_delete"] == 0


def test_the_hash_fallback_keeps_the_mk_prefix():
    """A bare 'mk' reaches the reports FK, the insert fails and the event is lost silently; the server only drops ids that start with mk_."""
    fb = re.search(r"catch\(e\)\{ return Promise\.resolve\('([^']*)'\)", PAGE).group(1)
    assert fb.startswith("mk_")


def test_server_nulls_hashed_ids_and_keeps_the_event():
    import events_v2
    conn = db_v2.get_conn()
    try:
        ids = []
        for rid in ("mk_0123456789abcdef", "mk_nohash"):
            ids.append(events_v2.record_event(conn, visitor_id="vis_mkfe", visit_id="vst_mkfe", event_name="purchase",
                                              report_id=rid, page_url="/en/numerology", value_paise=29900, currency="INR"))
        conn.commit()
        with conn.cursor() as c:
            c.execute("SELECT report_id, value_paise FROM events WHERE id IN (%s,%s)", tuple(ids))
            assert list(c.fetchall()) == [(None, 29900), (None, 29900)]
            c.execute("DELETE FROM events WHERE visitor_id='vis_mkfe'")
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------- the real page in a real browser

try:
    import playwright.sync_api as pw
except ImportError:           # no Playwright: the registration tests above still run, the browser ones skip
    pw = None
if pw:                        # a renamed helper must fail loudly here, never turn into a silent skip
    from test_mulank_browser import CHROME, RAZORPAY_STUB, _route, live  # noqa: E402,F401
else:
    CHROME = ""

    @pytest.fixture
    def live():
        pytest.skip("Playwright for Python is not installed")

browser_only = pytest.mark.skipif(not CHROME, reason="no Chrome / Playwright available (set CHROME_BIN)")


def _last_event_id():
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT COALESCE(MAX(id),0) FROM events")
            return c.fetchone()[0]
    finally:
        conn.close()


def _events_after(mark, want, timeout=8.0):
    """Beacons are fire-and-forget, so poll until every wanted event name has arrived."""
    end = time.time() + timeout
    rows = []
    while time.time() < end:
        conn = db_v2.get_conn()
        try:
            with conn.cursor() as c:
                c.execute("SELECT event_name, report_id, page_url, value_paise, currency FROM events WHERE id>%s ORDER BY id", (mark,))
                rows = list(c.fetchall())
        finally:
            conn.close()
        if want <= {r[0] for r in rows}:
            break
        time.sleep(0.3)
    return rows


def _journey(live, no_subtle=False):
    base, rz = live["base"], live["rz"]
    seen = {"rid": None}

    def pay(order_id):
        pid = "pay_" + order_id[-30:]
        rz.entity = {"id": pid, "order_id": order_id, "amount": 29900, "currency": "INR", "status": "captured", "method": "upi"}
        sig = hmac.new(SECRET.encode(), f"{order_id}|{pid}".encode(), hashlib.sha256).hexdigest()
        return {"razorpay_order_id": order_id, "razorpay_payment_id": pid, "razorpay_signature": sig}

    mark = _last_event_id()
    with pw.sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, headless=True)
        page = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
        page.expose_function("__mkPay", pay)
        if no_subtle:
            page.add_init_script("Object.defineProperty(window.crypto,'subtle',{value:undefined,configurable:true})")
        _route(page, base)
        page.on("request", lambda r: live.setdefault("posted", []).append(r.post_data or "")
                if r.url.endswith("/api/mulank") and r.method == "POST" else None)
        page.goto(base + "/en/numerology")
        assert page.locator("#f-gender").count() == 0          # the gender field is gone from the real form
        page.fill("#f-name", "Funnel Check")
        page.fill("#f-dd", "29")
        page.select_option("#f-mm", "7")
        page.fill("#f-yy", "1990")
        page.fill("#f-phone", "9591%06d" % (int(time.time() * 1000) % 1000000))
        page.check("#f-consent")
        page.click("#mkGo")
        page.wait_for_selector("#mkFrame .tz-cover", state="visible", timeout=20000)
        seen["rid"] = page.evaluate("sessionStorage.getItem('mk_rid')")
        page.locator('#mkFrame [data-action="checkout"]').first.scroll_into_view_if_needed()
        page.locator('#mkFrame [data-action="checkout"]').first.click()
        page.wait_for_selector("#mkPaid", state="visible", timeout=30000)
        browser.close()
    want = {"page_view", "form_start", "generate_lead", "begin_checkout", "purchase"}
    return seen["rid"], _events_after(mark, want)


@browser_only
def test_every_funnel_event_reaches_the_events_table(live):
    rid, rows = _journey(live)
    assert live["posted"] and all("gender" not in b for b in live["posted"]), live["posted"]      # the lead request carries no gender
    names = [r[0] for r in rows]
    for ev in ("page_view", "form_start", "generate_lead", "begin_checkout", "purchase"):
        assert ev in names, f"{ev} never reached the events table: {names}"
    assert names.count("purchase") == 1, "one sale must be one purchase event"
    assert names.index("form_start") < names.index("generate_lead") < names.index("begin_checkout") < names.index("purchase")
    assert all(r[2] == "/en/numerology" for r in rows), [r[2] for r in rows]
    by = {r[0]: r for r in rows}
    assert by["begin_checkout"][3:] == (29900, "INR") and by["purchase"][3:] == (29900, "INR")      # 299 rupees in paise, same as the server price
    assert all(r[1] is None for r in rows)                                                          # the hash never becomes a report id
    assert rid and not any(rid in str(r) for r in rows)                                             # the raw private id is nowhere in the saved events


@browser_only
def test_purchase_is_still_saved_when_the_browser_cannot_hash(live):
    """crypto.subtle is missing on plain http. The old fallback id 'mk' broke the foreign key and silently dropped the PURCHASE event
    (only purchase carries the id to /api/event; lead and checkout are asserted too as a baseline)."""
    rid, rows = _journey(live, no_subtle=True)
    names = [r[0] for r in rows]
    assert "generate_lead" in names and "purchase" in names, names
    assert all(r[1] is None for r in rows)
