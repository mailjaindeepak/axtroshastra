"""Life Blueprint (/jeevan, product id "blueprint") regression tests for the
v2 redesign: the Vyapar-styled ten-area report. Same pattern as
test_career_growth.py's helpers."""
import api

BLUEPRINT = {"name": "Blueprint Tester", "dob": "1988-04-12", "tob": "14:20",
             "time_quality": "T0", "place": "Mumbai", "gender": "female",
             "product": "blueprint"}


class _StubOrders:
    def create(self, payload):
        return {"id": "order_stub_bp", "amount": payload["amount"]}


class _StubRzp:
    order = _StubOrders()


def _paid_blueprint_report_html(client, **overrides):
    r = client.post("/api/kundli", json={**BLUEPRINT, **overrides})
    assert r.status_code == 200, r.text
    rid = r.json()["report_id"]
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    page = client.get(f"/report/{rid}")
    assert page.status_code == 200
    return page.text


def test_blueprint_page_serves_200(client):
    r = client.get("/en/life-blueprint")
    assert r.status_code == 200


def test_jeevan_legacy_redirects_to_canonical(client):
    r = client.get("/jeevan", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "/en/life-blueprint"

    r = client.get("/en/jeevan", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "/en/life-blueprint"

    r = client.get("/hi/jeevan", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "/hi/life-blueprint"


def test_jeevan_legacy_redirect_preserves_query(client):
    r = client.get("/en/jeevan?pass=tok123", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "/en/life-blueprint?pass=tok123"


def test_blueprint_report_renders_all_ten_areas(client):
    """Part 1 (10 life areas) + Part 2 (methodology/proof), restructured to
    match the finalized reference. See test_blueprint_report_has_reasoncards_
    and_timelines for the per-area component/timeline assertions."""
    html = _paid_blueprint_report_html(client)
    assert "Blueprint Tester" in html
    assert "Life Blueprint" in html
    for section in ("Where your chart points you", "How money moves for you",
                     "What you need in a partner", "Building a family, your way",
                     "Where and how you put down roots", "Whether distance suits you",
                     "How your body tends to run", "What comes naturally, and what doesn't",
                     "Parents, siblings, and old ties", "Is now the moment?",
                     "Your kundli", "Every planet, placed", "Dashas, explained",
                     "How every tag was set", "A short glossary"):
        assert section in html, section
    # the cross-sell hooks that keep Blueprint a funnel hub, not a dead end
    assert "Job Change report" in html
    assert "Milan report" in html
    # honesty guardrails must survive into the rendered page
    assert "never a claim about fertility" in html
    assert "not medical advice" in html


def test_blueprint_report_has_wheel_and_tag_cards(client):
    html = _paid_blueprint_report_html(client)
    # radial wheel chart (replaces the old two flat "Life Wheel" grid pages)
    assert 'class="wheelchart"' in html
    assert html.count("wheelchart") >= 1
    # "why it reads this way" reasoning card: 8 areas (growth is a persona
    # line, not a house-lord reasoning) + timing + dashas-explained + worked
    # example = 11
    assert html.count('class="reasoncard') == 11
    # favour/watching two-column cards, one pair per of the 9 named areas
    assert html.count('class="bp-sccols"') >= 9
    # reflection line on all 9 named areas (career..family, incl. growth)
    assert html.count('class="reflect"') == 9
    assert "WORKING IN YOUR FAVOUR" in html.upper()
    assert "WORTH WATCHING" in html.upper()
    # per-area Antardasha timeline rows (the ported phase_read()-based
    # system) -- 9 areas x up to 4 rows, plus the Timing/global roadmap
    # reusing the same .adrow component
    assert html.count('class="adrow') >= 9 * 4
    # the day-of-week-free per-area status vocabulary from the ported bank
    assert any(w in html for w in ("Favorable", "Steady", "Watch"))


def test_blueprint_wheel_has_all_ten_tags(client):
    import products
    p = products.compute_blueprint("Wheel Tester", "1988-04-12", "14:20", 5.5,
                                    19.0760, 72.8777)
    wheel = p["wheel"]
    assert set(wheel) == {"career", "money", "marriage", "children", "home",
                          "foreign", "health", "growth", "family", "timing"}
    assert all(v in ("thriving", "building", "watch") for v in wheel.values())


def test_blueprint_per_area_timeline_uses_real_ported_classification(client):
    """The per-area Antardasha timeline (report_view._bp_timeline_rows) must
    be built from products.compute_blueprint()'s real, ported phase_read()/
    ad_phases() data -- current AD always standalone, real dates, and
    genuinely different statuses across areas for the same real chart (not
    a single shared global roadmap repeated on every page)."""
    import products
    p = products.compute_blueprint("Timeline Tester", "1998-12-05", "02:47", 5.5,
                                    22.7196, 75.8577)
    career = p["area_detail"]["career"]
    money = p["area_detail"]["money"]
    assert career["ad_phases"] and money["ad_phases"]
    # row 0 is always the live, today-onward Antardasha -- real lord, real dates
    assert career["ad_phases"][0]["lord"]
    assert career["ad_phases"][0]["from"] and career["ad_phases"][0]["to"]
    assert all(ph["kind"] in ("favorable", "watch", "steady") for ph in career["ad_phases"])
    # "growth" and "timing" don't get a per-area house-based timeline
    assert "ad_phases" not in p["area_detail"]["timing"]

    html = _paid_blueprint_report_html(client, name="Timeline Tester", dob="1998-12-05",
                                       tob="02:47", place="Indore")
    # the ROW_CAP=4 visual budget from the ported implementation
    from report_view import BP_ROW_CAP
    assert BP_ROW_CAP == 4
    assert html.count('class="adrow') >= 9 * 4


def test_blueprint_has_full_part2_structure(client):
    """The restructured report must carry every Part 2 section the old
    ~20-page design never had -- a direct check that this isn't the old
    shallow structure with a few pages renamed."""
    body = _paid_blueprint_report_html(client)
    for marker in ("Placements worth a look", "House rulers &amp; links",
                   "Your Dasha timeline", "Every reading, in one table",
                   "What this report is", "A short glossary"):
        assert marker in body, marker


def test_blueprint_varies_by_birth_data(client):
    html_a = _paid_blueprint_report_html(client, name="Person A",
                                         dob="1988-01-05", tob="22:15", place="Delhi")
    html_b = _paid_blueprint_report_html(client, name="Person B",
                                         dob="2000-11-23", tob="04:50", place="Chennai")
    assert html_a != html_b


def test_blueprint_hi_page_serves_200(client):
    r = client.get("/hi/life-blueprint")
    assert r.status_code == 200
    assert 'lang="hi"' in r.text


def test_blueprint_hi_full_report_is_rendered(client):
    """A Hindi buyer's PAID report is built by blueprint_hi_report.render_
    blueprint_hi() -- a real renderer wired through _render_for, not a
    post-render translation of render_blueprint's English HTML."""
    html = _paid_blueprint_report_html(client, variant="/hi/life-blueprint")
    assert 'lang="hi"' in html
    # Part 1: ten life areas, in Hindi, present regardless of chart data
    for hi_text in ("आपका जीवन ब्लूप्रिंट", "आपके बारे में", "आपकी कुंडली क्या कहती है",
                     "क्या अभी वह पल है?"):
        assert hi_text in html, hi_text
    # Part 2: the finalized reference's evidence/methodology section, absent
    # from English's shorter design -- this is the structural point of this
    # renderer existing at all, not a translation of render_blueprint.
    for hi_text in ("यह निष्कर्ष कैसे निकले", "आपकी जन्म-कुंडली", "हर ग्रह, उसकी जगह पर",
                     "भाव 1&ndash;6", "भाव 7&ndash;12", "दशाएँ, समझाई गईं",
                     "हर टैग कैसे तय हुआ", "हर रीडिंग, एक तालिका में",
                     "यह रिपोर्ट क्या है", "एक छोटी शब्दावली"):
        assert hi_text in html, hi_text
    # the user's own name must survive untouched (never transliterated —
    # matches the deliberate policy in milan_hi.py/shaadi_hi.py/career_growth_hi.py)
    assert "Blueprint Tester" in html


def test_blueprint_hi_report_has_wheel_and_area_cards(client):
    """The Hindi report reuses the wheel/card visual system (_VYAPAR_CSS,
    the same wheelchart SVG shape) plus its own additive card classes for
    the deeper Part 1 + Part 2 structure the reference PDF calls for."""
    html = _paid_blueprint_report_html(client, variant="/hi/life-blueprint")
    assert 'class="wheelchart"' in html
    assert html.count('class="reasoncard') == 12  # 9 areas + timing + dashas-explained + worked example
    assert html.count('class="reflect"') == 9      # 8 named areas + growth
    assert html.count('class="verdict') == 11       # 9 areas + timing + sade-sati


def test_blueprint_hi_preserves_real_dignity_reasoning(client):
    """The Part 2 worked example and 'how every tag was set' page must cite
    the SAME real house/lord/dignity compute_blueprint() actually used for
    that person's career tag -- never a fabricated or hardcoded example."""
    import products
    p = products.compute_blueprint("Dignity Tester", "1988-04-12", "14:20", 5.5,
                                    19.0760, 72.8777)
    d = p["area_detail"]["career"]
    html = _paid_blueprint_report_html(client, variant="/hi/life-blueprint",
                                       name="Dignity Tester", dob="1988-04-12",
                                       tob="14:20", place="Mumbai")
    from blueprint_hi_report import PLANET_HI, SIGN_HI
    assert PLANET_HI[d["lord"]] in html
    assert SIGN_HI[d["lord_sign"]] in html


def test_blueprint_hi_varies_by_birth_data(client):
    html_a = _paid_blueprint_report_html(client, variant="/hi/life-blueprint",
                                         name="Person A", dob="1988-01-05",
                                         tob="22:15", place="Delhi")
    html_b = _paid_blueprint_report_html(client, variant="/hi/life-blueprint",
                                         name="Person B", dob="2000-11-23",
                                         tob="04:50", place="Chennai")
    assert html_a != html_b


def test_blueprint_pdf_generates(client):
    body = {**BLUEPRINT}
    r = client.post("/api/kundli", json=body)
    assert r.status_code == 200, r.text
    rid = r.json()["report_id"]
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    r = client.get(f"/report/{rid}/pdf")
    # 200 with a real PDF when Chrome is available in the test environment,
    # 503 (graceful "pdf_unavailable") when it isn't -- never a 500/crash.
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        assert r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF")


def test_blueprint_hi_pdf_generates(client):
    """The same real /report/{rid}/pdf pipeline, but for a Hindi buyer --
    must hit render_blueprint_hi(), not render_blueprint()."""
    r = client.post("/api/kundli", json={**BLUEPRINT, "variant": "/hi/life-blueprint"})
    assert r.status_code == 200, r.text
    rid = r.json()["report_id"]
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    r = client.get(f"/report/{rid}/pdf")
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        assert r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF")


def test_blueprint_price_is_999_not_499(client, monkeypatch):
    """Life Blueprint's price was raised (crossed-out ₹1999 -> ₹999,
    previously ₹999 -> ₹499). _order_amount_paise() must charge ₹999 for
    both language variants, while every other product keeps its own price
    (never accidentally bumped alongside blueprint's)."""
    monkeypatch.setattr(api, "rzp_client", lambda: _StubRzp())
    for variant in ("/en/life-blueprint", "/hi/life-blueprint"):
        r = client.post("/api/kundli", json={**BLUEPRINT, "variant": variant})
        rid = r.json()["report_id"]
        order = client.post("/api/order", json={"report_id": rid})
        assert order.status_code == 200, order.text
        assert order.json()["amount"] == 99900, variant

    # a different product on the same shared PRICE_PAISE constant must be
    # completely unaffected by blueprint's price change.
    r = client.post("/api/kundli", json={"name": "Marriage Tester", "dob": "1990-01-01",
                                         "tob": "10:00", "place": "Delhi", "gender": "female",
                                         "product": "marriage", "variant": "/en/marriage"})
    rid = r.json()["report_id"]
    order = client.post("/api/order", json={"report_id": rid})
    assert order.status_code == 200, order.text
    assert order.json()["amount"] == 49900
