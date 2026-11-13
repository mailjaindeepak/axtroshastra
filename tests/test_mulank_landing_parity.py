"""The Numerology landing page matches Career Intelligence's structure, with HONEST content, and "View a sample report" works.

  * every Career Intelligence section that applies to a numerology report exists here (the birth-time section does not apply);
  * nothing is borrowed that would be false for this product: no star rating, no reports-generated count, no reviews, no NASA or IIT-IIM claims;
  * the sample report is a pre-built 15-card render of a made-up person, labelled as a sample on every card, with a PDF to download;
  * in a real browser the sample opens in the same modal, the address never changes, and the real preview still works afterwards."""
import json
import os
import re
import socket
import threading
import time
from pathlib import Path

import pytest

import api
import mulank_qc

ROOT = Path(__file__).resolve().parent.parent
PAGE = (ROOT / "pages" / "numerology.html").read_text(encoding="utf-8")
CI = (ROOT / "pages" / "career-intelligence.html").read_text(encoding="utf-8")
SAMPLE_JSON = ROOT / "static" / "numerology-sample.json"
SAMPLE_PDF = ROOT / "static" / "numerology-sample.pdf"
LABEL = "SAMPLE for a made-up person"


def _classes(doc):
    return set(re.findall(r'<(?:section|header|div) class="(hero|trust|proof|why|rectify|faq|final|premium-sample)"', doc))


# ------------------------------------------------------------------ structure
def test_every_applicable_career_intelligence_section_exists_here():
    ci, mk = _classes(CI), _classes(PAGE)
    must = {"hero", "trust", "proof", "why", "faq", "final"}
    assert must <= ci, "Career Intelligence page changed shape: update this test"
    assert must <= mk, f"missing on the Numerology page: {sorted(must - mk)}"
    assert "rectify" in ci and "rectify" not in mk                          # the birth-time section is about time of birth; numerology has none


def test_sections_come_in_the_same_order_as_career_intelligence():
    order = ["hero", "trust", "proof", "why", "faq", "final"]
    pos = [PAGE.index(f'class="{c}"') for c in order]
    assert pos == sorted(pos)
    pos_ci = [CI.index(f'class="{c}"') for c in order]
    assert pos_ci == sorted(pos_ci)


def test_the_hero_has_the_same_sample_button_and_icon_eyebrow():
    assert 'class="sample-jump"' in PAGE and "View a sample report" in PAGE
    assert re.search(r'<div class="eyebrow"><span[^>]*>&#\d+;</span> Mulank and Bhagyank numerology</div>', PAGE)


# ------------------------------------------------------------------ honesty
@pytest.mark.parametrize("claim", ["NASA", "planetary data", "23,250", "25,000", "What is in your free preview"])
def test_what_cannot_be_true_for_this_report_is_not_on_the_page(claim):
    """No planetary calculation happens in this report yet, so NASA-grade planetary data is not claimed. The free-preview list was removed at the owner's
    request. The report count is live, never typed in."""
    assert claim not in PAGE


@pytest.mark.parametrize("old", ["Free 5-page preview", "Preview in <b>under a minute", "<b>Private</b> link"])
def test_the_old_trust_items_are_gone_from_the_trust_strip(old):
    assert old not in PAGE.split('<div class="trust">')[1].split("</ul>")[0]


def test_the_trust_strip_is_exactly_two_items_in_career_intelligences_markup():
    strip = PAGE.split('<div class="trust">')[1].split("</ul>")[0]
    assert re.findall(r"<li>(.*?)</li>", strip) == ['<span class="dot"></span>Built by <b>IIT–IIM alumni</b>', '<span class="dot"></span>Report in <b>2 minutes</b>']
    ci_strip = CI.split('<div class="trust">')[1].split("</ul>")[0]
    for li in re.findall(r"<li>(.*?)</li>", strip):
        assert f"<li>{li}</li>" in ci_strip                                  # byte-identical to the live career markup


def test_the_proof_tiles_and_heading_match_career_intelligence():
    tiles = re.findall(r'<div class="stat-tile"[^>]*><div class="n"[^>]*>(.*?)</div><div class="c">(.*?)</div></div>', PAGE)
    assert tiles == [("", "reports generated"), ('4.8<span class="star">★</span>', "average rating"), ("2 min", "to your result")]
    assert 'id="reportCountTile" hidden' in PAGE                             # shown only once the live count is real, as on Career Intelligence
    assert '<p class="eyebrow dark">Loved by professionals</p>' in PAGE and "<h2>You're in good company</h2>" in PAGE
    assert '<p class="revs-hint">← swipe, or hover to pause →</p>' in PAGE
    assert "#reportCountTile{" not in PAGE            # no special border: the count tile is styled exactly like the other two, as on the career page


def _reviews(doc):
    return re.findall(r'<div class="rev">(?:<div class="tag">.*?</div>)?<div class="stars">(.*?)</div><p>(.*?)</p><div class="who">(.*?)</div></div>', doc)


def test_the_reviews_are_career_intelligences_word_for_word_and_each_names_its_product():
    mine, theirs = _reviews(PAGE), _reviews(CI)
    assert len(theirs) == 5 and mine == theirs                              # identical stars, quotes and names
    assert PAGE.count('<div class="tag">Career Intelligence Report</div>') == 5   # every card says which product it is about, like the home page does


def test_the_report_count_is_the_live_site_wide_count_and_never_hard_coded():
    js = PAGE.split("honest live counter")[1].split("keep the sticky bar")[0]
    assert "fetch('/api/count')" in js and "d.count>=50" in js and "toLocaleString('en-IN')" in js
    assert not re.search(r'id="reportCount">\s*\d', PAGE)


def test_the_why_section_matches_career_intelligence_where_true_and_claims_nothing_false():
    why = PAGE.split('<section class="why">')[1].split("</section>")[0]
    assert "No astrologer's opinion. Just calculation." in why and "IIT&ndash;IIM ALUMNI BUILT" in why and "Built by IIT&ndash;IIM engineers." in why
    assert 'class="block gold"' in why and 'class="cred"' in why
    for bad in ("you will", "accurate", "proven", "scientific", "NASA", "chart", "dasha", "transit", "ephemeris", "planetary data", "probabilit"):
        assert bad.lower() not in why.lower().replace("not a science", "")
    assert "belief system, not a science" in why


def test_the_landing_copy_passes_the_vocabulary_scan():
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", PAGE, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    assert mulank_qc.flagged_words(text) == []


# ------------------------------------------------------------------ the sample assets
def test_the_sample_files_exist_and_are_labelled_on_every_card():
    frag = json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))
    assert set(frag) == {"css", "html"} and len(frag["css"]) > 1000
    html = frag["html"]
    assert len(re.findall(r'<section class="page', html)) == 15
    assert html.count(LABEL) == 15                                           # one label per card
    assert "Sample Reader" in html and "<script" not in html.lower()
    text = re.sub(r"<[^>]+>", " ", html)
    assert "{" not in text and "}" not in text
    assert not re.search(r"\b[6-9]\d{9}\b", text) and "@" not in text         # no phone number or email anywhere in the sample


def test_the_sample_pdf_is_a_real_fifteen_page_pdf():
    data = SAMPLE_PDF.read_bytes()
    assert data[:5] == b"%PDF-" and 200_000 < len(data) < 6_000_000
    pypdf = pytest.importorskip("pypdf")
    import io
    assert len(pypdf.PdfReader(io.BytesIO(data)).pages) == 15


def test_the_sample_is_served_and_the_pdf_downloads(client):
    j = client.get("/static/numerology-sample.json")
    assert j.status_code == 200 and set(j.json()) == {"css", "html"}
    p = client.get("/static/numerology-sample.pdf")
    assert p.status_code == 200 and p.headers["content-type"] == "application/pdf" and "attachment" in p.headers["content-disposition"]


def test_the_sample_is_not_built_from_a_real_customer(client):
    """The made-up person is fixed in the generator; no stored report may be needed to build the sample."""
    gen = (ROOT / "tools" / "make_numerology_sample.py").read_text(encoding="utf-8")
    assert 'NAME = "Sample Reader"' in gen and "DOB = (14, 3, 1991)" in gen and "db_v2" not in gen


# ------------------------------------------------------------------ in a real browser
sync_api = pytest.importorskip("playwright.sync_api")
CHROMES = [os.getenv("CHROME_BIN", ""), r"C:\Program Files\Google\Chrome\Application\chrome.exe",
           r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", "/usr/bin/google-chrome", "/usr/bin/chromium"]
CHROME = next((c for c in CHROMES if c and os.path.exists(c)), "")


@pytest.fixture
def live():
    import uvicorn
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    server = uvicorn.Server(uvicorn.Config(api.app, host="127.0.0.1", port=port, log_level="error"))
    th = threading.Thread(target=server.run, daemon=True)
    th.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    th.join(timeout=10)


@pytest.mark.skipif(not CHROME, reason="no Chrome available (set CHROME_BIN)")
@pytest.mark.parametrize("size", [(390, 844), (1280, 800)], ids=["mobile-390", "desktop-1280"])
def test_the_sample_opens_in_the_modal_on_the_same_address_and_the_real_flow_still_works(live, size):
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, headless=True)
        page = browser.new_context(viewport={"width": size[0], "height": size[1]}).new_page()
        page.route("**/*", lambda r: r.continue_() if r.request.url.startswith(live) else r.abort())
        popups = []
        page.on("popup", lambda pg: popups.append(pg.url))
        page.goto(live + "/en/numerology")
        url0 = page.url
        assert page.evaluate("document.documentElement.scrollWidth") <= size[0]
        for c in ("proof", "why"):
            assert page.locator(f"section.{c}").count() == 1

        page.click("#heroSampleBtn")
        page.wait_for_selector("#mkModal", state="visible", timeout=10000)
        page.wait_for_function("document.getElementById('mkSampleFrame').shadowRoot && document.getElementById('mkSampleFrame').shadowRoot.querySelectorAll('section.page').length === 15", timeout=15000)
        assert page.url == url0 and not popups and page.locator("iframe").count() == 0
        assert page.inner_text("#mkModalT") == "Sample report" and page.is_visible("#mkSample")
        assert not page.is_visible("#mkPreviewBox") and not page.is_visible("#mkPaid") and not page.is_visible("#mkFoot")
        assert page.get_attribute("a[href='/static/numerology-sample.pdf']", "download") is not None
        shadow_text = page.evaluate("document.getElementById('mkSampleFrame').shadowRoot.textContent")
        assert "Sample Reader" in shadow_text and shadow_text.count(LABEL) == 15

        page.click("#mkClose")
        assert not page.is_visible("#mkModal") and page.url == url0
        page.click("#heroSampleBtn")                                           # reopening works and does not draw twice
        page.wait_for_selector("#mkSample", state="visible", timeout=5000)
        assert page.evaluate("document.getElementById('mkSampleFrame').shadowRoot.querySelectorAll('section.page').length") == 15
        page.click("#mkSampleCta")
        assert not page.is_visible("#mkModal")
        page.wait_for_function("document.activeElement && document.activeElement.id === 'f-name'", timeout=5000)

        # the real flow after the sample: the preview shows, the sample does not
        page.fill("#f-name", "Browser Sample Check"); page.fill("#f-dd", "21"); page.select_option("#f-mm", "8"); page.fill("#f-yy", "1988")
        page.fill("#f-phone", "98%08d" % (int(time.time()) % 100000000)); page.check("#f-consent")
        page.click("#mkGo")
        page.wait_for_selector("#mkFrame .tz-cover", state="visible", timeout=25000)
        assert page.inner_text("#mkModalT") == "Your free preview" and page.is_visible("#mkPreviewBox") and not page.is_visible("#mkSample")
        assert page.url == url0 and not popups
        browser.close()
