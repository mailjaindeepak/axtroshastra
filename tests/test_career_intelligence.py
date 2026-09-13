"""Career Intelligence Report (/en/career-intelligence, product id
"career_intelligence") regression tests. Premium English-only product, ₹199.
Same pattern as test_career_growth.py: create via /api/kundli, bypass payment via
DEMO_MODE's /api/_demo_pay, fetch the served report HTML. English only — no /hi/
twin, no Hindi assertions (deliberate, per docs/career-intelligence-report-spec.md)."""

import api
import db_v2

# exactly the 5 fields the funnel form sends — no employment_situation/experience.
CAREER_INTEL = {"name": "Intel Tester", "dob": "1972-03-14", "tob": "10:30",
                "time_quality": "T0", "place": "Bengaluru", "gender": "male",
                "product": "career_intelligence"}


def _create(client, **overrides):
    r = client.post("/api/kundli", json={**CAREER_INTEL, **overrides})
    assert r.status_code == 200, r.text
    return r.json()


def _paid_report_html(client, **overrides):
    rid = _create(client, **overrides)["report_id"]
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    page = client.get(f"/report/{rid}")
    assert page.status_code == 200
    return page.text


def test_career_intelligence_page_serves_200(client):
    r = client.get("/en/career-intelligence")
    assert r.status_code == 200
    assert "career-intelligence" in r.text  # canonical / og
    # premium product carries the shared funnel machinery
    assert "kundliForm" in r.text and "startPayment" in r.text


def test_career_intelligence_preview_is_bars_not_radar(client):
    """The redesigned preview renders the six dimensions as a BAR chart with the
    'Your Career DNA' framing, the 'what stands out' block and the 5 locked
    questions — and no longer the old hexagon radar."""
    html = client.get("/en/career-intelligence").text
    assert "Your Career DNA" in html
    assert "function drawBars(" in html and "id=\"tv-bars\"" in html
    assert "What stands out" in html and "id=\"tv-combo\"" in html and "id=\"tv-env\"" in html
    for q in ("When are your strongest career years?",
              "How are you most likely to build wealth?",
              "What career moves should you avoid right now?",
              "What do the next 3 years look like?",
              "What should you prioritize over the next 12 months?"):
        assert q in html, q
    # the old radar is gone
    assert "function drawRadar(" not in html and "tv-radar" not in html


def test_career_intelligence_bare_path_redirects_to_en(client):
    r = client.get("/career-intelligence", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "/en/career-intelligence"


def test_career_intelligence_is_english_only(client):
    """No Hindi twin exists for this product (deliberate)."""
    assert client.get("/hi/career-intelligence").status_code == 404


def test_career_intelligence_report_renders_57_cards(client):
    html = _paid_report_html(client)
    assert html.count('<section class="page') == 57
    assert "Intel Tester" in html            # identity injected
    assert "Rajesh Menon" not in html        # the mock persona must not leak


def test_career_intelligence_teaser_fields(client):
    """The free preview returns exactly the keys pages/career-intelligence.html's
    renderTeaser() reads — and none of the paid-report internals."""
    teaser = _create(client)["teaser"]
    for key in ("name", "archetype", "archetype_blurb", "top_dimension", "phase",
                "entrepreneurial_10", "quote", "best_environment"):
        assert key in teaser, key
    assert teaser["archetype_blurb"] and teaser["best_environment"]
    # the six calibrated dimensions ARE included so the landing-page teaser can draw
    # the person's own bar chart (a deliberate preview hook, not a leak).
    assert set(teaser["dimensions"]) == {"leadership", "strategic", "independence",
                                         "entrepreneurial", "risk", "stability"}
    assert all(0 <= v <= 100 for v in teaser["dimensions"].values())
    # deeper paid internals must still not leak into the free teaser
    for leaked in ("life_stage", "windows", "decision_style", "three_year"):
        assert leaked not in teaser, leaked


def test_career_intelligence_best_environment_matches_report_map(client):
    """The teaser's 'best_environment' must equal the report's own dimension->environment
    phrase for the person's top dimension — keeps the landing line and the paid report's
    §33 consistent (chart-driven, not a generic string). CLAUDE.md §8/§22."""
    from ci_narr_part4 import NEED_BY_DIM
    teaser = _create(client, name="Env Tester", dob="1969-11-02", tob="16:40",
                     place="Chennai")["teaser"]
    assert teaser["best_environment"] == NEED_BY_DIM[teaser["top_dimension"]]


def test_career_intelligence_price_is_199(client):
    """Server-side price for this product is ₹199 (19900 paise), regardless of
    the client — distinct from the base ₹499 products' price point."""
    rec = {"payload": {"product": "career_intelligence",
                       "meta": {"variant": "/en/career-intelligence"}}}
    assert api._order_amount_paise(rec) == 19900


def test_career_intelligence_varies_by_birth_data(client):
    a = _paid_report_html(client, name="Person A", dob="1988-01-05",
                          tob="22:15", place="Delhi")
    b = _paid_report_html(client, name="Person B", dob="2000-11-23",
                          tob="04:50", place="Mumbai", gender="female")
    assert a != b


def test_career_intelligence_no_mock_persona_leak(client):
    """Rule 2: a real buyer's report must carry NONE of the mock persona's name,
    numbers, or hardcoded prose (regression for the narrative personalization)."""
    html = _paid_report_html(client, name="Meera Nair", dob="1985-09-22", tob="03:40",
                             place="Mumbai", gender="female")
    for leak in ("Rajesh", "Menon", "Strategic thinking <span>92", "Follow-through",
                 "Quiet authority", "Public visibility", "Reliability fit (85)"):
        assert leak not in html, f"mock-persona leak in real report: {leak!r}"


def test_career_intelligence_narrative_varies(client):
    """Rule 2: the chart-derived pages must differ between two different charts —
    most of the 57 cards, not just the data exhibits."""
    a = _paid_report_html(client, name="Person A", dob="1972-03-14", tob="10:30", place="Bengaluru")
    b = _paid_report_html(client, name="Person B", dob="1991-06-18", tob="14:05",
                          place="Ahmedabad", gender="female")
    import re
    pa = [s for s in re.split(r'(?=<section class="page)', a) if 'class="page' in s]
    pb = [s for s in re.split(r'(?=<section class="page)', b) if 'class="page' in s]
    differ = sum(1 for x, y in zip(pa, pb) if x != y)
    assert differ >= 40, f"only {differ}/57 pages differ — narrative not personalized"


def test_career_intelligence_form_sends_phone_to_kundli(client):
    """Regression: this page REQUIRES the WhatsApp number in the main form, so it must
    send it with /api/kundli — otherwise the lead is created only at /api/order and
    every visitor who gets the free snapshot but doesn't click unlock is dropped
    (their number lived only in the browser). Guards the exact bug that shipped."""
    html = client.get("/en/career-intelligence").text
    assert 'id="f-whatsapp"' in html           # the number IS collected up front in the form
    assert "phone: waPhone" in html            # ...and IS sent in the /api/kundli create body


def test_career_intelligence_phone_creates_lead_at_submit(client):
    """Real-path: posting the funnel payload WITH phone (as the page now does) creates
    + links the account at report creation, capturing the lead even if the visitor
    never reaches checkout — same lead-at-submit contract as the main-form funnels."""
    rid = _create(client, phone="98765 01199")["report_id"]
    conn = db_v2.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT u.country_code, u.mobile FROM reports r "
                        "JOIN users u ON u.id = r.user_id WHERE r.id=%s", (rid,))
            row = cur.fetchone()
    finally:
        conn.close()
    assert row is not None, "no user linked at submit — lead not captured"
    assert f"{row[0] or ''}{row[1] or ''}" == "+919876501199"


def test_career_intelligence_pdf_generates(client):
    rid = _create(client)["report_id"]
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    r = client.get(f"/report/{rid}/pdf")
    # 200 with a real PDF when Chrome is available, 503 graceful otherwise — never 500.
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        assert r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF")
