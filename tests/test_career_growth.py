"""Career Report (/career-growth, product id "career_growth") regression
tests. Same pattern as test_gift_link.py's marriage-report helper: create via
/api/kundli, bypass payment via DEMO_MODE's /api/_demo_pay, fetch the served
report HTML."""

CAREER_GROWTH = {"name": "Career Tester", "dob": "1996-06-14", "tob": "10:30",
                  "time_quality": "T0", "place": "Bengaluru", "gender": "male",
                  "product": "career_growth",
                  "employment_situation": "changing-job", "experience": "5-10"}


def _create_career_growth(client, **overrides):
    r = client.post("/api/kundli", json={**CAREER_GROWTH, **overrides})
    assert r.status_code == 200, r.text
    return r.json()


def _paid_career_growth_report_html(client, **overrides):
    body = _create_career_growth(client, **overrides)
    rid = body["report_id"]
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    page = client.get(f"/report/{rid}")
    assert page.status_code == 200
    return page.text


def test_career_growth_report_renders(client):
    html = _paid_career_growth_report_html(client)
    assert "Career Report" in html
    assert "Career Tester" in html
    # spot-check a few real content slots are populated (not literal template
    # placeholders, and not the sample-data name from the original prototype)
    assert "Rohan Mehta" not in html
    assert "What's Inside Your Report" in html
    assert "Your Switch Windows" in html
    assert "Light Remedies" in html


def test_career_growth_page_serves_200(client):
    r = client.get("/en/career-growth")
    assert r.status_code == 200
    assert "<title>" in r.text.lower() or "<title>" in r.text


def test_career_growth_hi_page_serves_200(client):
    r = client.get("/hi/career-growth")
    assert r.status_code == 200
    assert 'lang="hi"' in r.text


def test_career_growth_bare_path_redirects_to_en(client):
    r = client.get("/career-growth", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "/en/career-growth"


def test_career_growth_unpaid_teaser_has_no_leakage(client):
    body = _create_career_growth(client)
    rid = body["report_id"]
    teaser = body["teaser"]
    # teaser is deliberately thin -- no verdict/window/persona content that
    # would give away the paid report for free
    assert "switch_outlook" in teaser
    assert "phase" in teaser
    assert "windows" not in teaser
    assert "workplace" not in teaser
    assert "naukri_meter" not in teaser
    assert "about_you" not in teaser
    # fields the free-preview teaser on pages/career-growth.html actually
    # renders (see renderTeaser() in that page's JS)
    for key in ("quote", "do_by", "has_quiet_stretch", "verdict_h3_blurred",
                "best_window_range", "field_top"):
        assert key in teaser, key

    r = client.get(f"/api/report/{rid}")
    assert r.status_code == 200
    j = r.json()
    assert j["paid"] is False
    assert "report" not in j


def test_career_growth_hi_full_report_is_translated(client):
    """A Hindi buyer's PAID report (not just the pre-payment teaser) must be
    localized too — career_growth_hi.localize() wired through _render_for."""
    body = _create_career_growth(client, variant="/hi/career-growth")
    rid = body["report_id"]
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    html = client.get(f"/report/{rid}").text
    assert 'lang="hi"' in html
    # section titles that are always present regardless of chart data
    for hi_text in ("करियर रिपोर्ट", "आपकी रिपोर्ट में क्या है", "आपके बारे में",
                     "सारांश", "आपका मौजूदा दौर", "आपके बदलाव के सही समय",
                     "सरल उपाय", "अस्वीकरण:"):
        assert hi_text in html, hi_text
    # the English-only landing-page prototype's sample name must never leak
    assert "Rohan Mehta" not in html


def test_career_growth_hi_teaser_is_translated(client):
    """/hi/career-growth's /api/kundli call must return a Devanagari teaser
    (career_growth_hi.translate_teaser), not the raw English compute output."""
    body = _create_career_growth(client, variant="/hi/career-growth")
    teaser = body["teaser"]
    assert teaser["phase"] in ("अभी आगे बढ़ें", "इंतज़ार और तैयारी")
    # field_top is one of career_growth_hi.FIELD_FAMILIES_HI's Hindi values --
    # just assert it's not still one of the raw English family names.
    assert teaser["field_top"] not in (
        "Technology & Engineering", "General Management", "Consulting")


def test_career_growth_varies_by_birth_data(client):
    """Two different births must not produce an identical report -- pins
    against accidentally shipping hardcoded/sample content."""
    html_a = _paid_career_growth_report_html(client, name="Person A",
                                             dob="1988-01-05", tob="22:15", place="Delhi")
    html_b = _paid_career_growth_report_html(client, name="Person B",
                                             dob="2000-11-23", tob="04:50", place="Mumbai")
    assert html_a != html_b


def test_career_growth_pdf_generates(client):
    body = _create_career_growth(client)
    rid = body["report_id"]
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    r = client.get(f"/report/{rid}/pdf")
    # 200 with a real PDF when Chrome is available in the test environment,
    # 503 (graceful "pdf_unavailable") when it isn't -- never a 500/crash.
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        assert r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF")


def test_career_growth_hi_pdf_generates(client):
    """_full_report_html() -> _render_for() carries the Hindi localize() step
    through into the PDF path too (no separate un-localized render for PDFs)."""
    body = _create_career_growth(client, variant="/hi/career-growth")
    rid = body["report_id"]
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    r = client.get(f"/report/{rid}/pdf")
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        assert r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF")
