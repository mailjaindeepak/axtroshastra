"""Vastu Career Report: landing page, create route, price and tracking contract.

Spec: docs/vastu-career-report-spec.md sections 1, 2, 6, 8. The page is checked against the repo rules (CLAUDE.md
sections 2, 3, 5, 5b, 6): head block, sitemap, no dead links, no Meta Health and Wellness words, no invented reviews,
no sample persona, no other product's text. The paid report renderer is NOT built yet, so nothing here covers it.
"""
import html as _html
import re

import pytest

import api
import vastu_career as vc

PHONES = iter(f"98765910{n:02d}" for n in range(1, 60))      # unique range for this file (shared-DB contract, section 12)
FLAGGED = (r"anxi", r"stress", r"depress", r"panic", r"trauma", r"therap", r"counsel", r"mental", r"well-?being", r"wellness",
           r"burn-?out", r"overwhelm", r"healing", r"\bheal\b", r"diagnos", r"symptom", r"disorder", r"treatment", r"\bcure\b",
           r"remedy", r"disease", r"illness", r"patient", r"clinical", r"medic", r"doctor", r"health", r"weight", r"\bdiet\b",
           r"\bcalm", r"relief", r"peace of mind")
PERSONAS = ("Asha", "Rohan", "Neha", "Karan", "Vikram", "Sana")


def _text(h):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S)
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", t)))


def _body(**kw):
    b = {"name": "Page Tester", "dob": "1999-03-14", "segment": "student", "desk_direction": "W",
         "desk_flexibility": "a_little", "door_direction": "N", "phone": next(PHONES),
         "consent_ts": "2026-11-20T00:00:00Z", "consent_v": "2026-11"}
    b.update(kw)
    return b


@pytest.fixture(scope="module")
def page(client):
    return client.get("/en/vastu-career").text


# ---------------------------------------------------------------- the page
def test_page_is_served_and_bare_url_redirects(client):
    assert client.get("/en/vastu-career").status_code == 200
    r = client.get("/vastu-career?x=1", follow_redirects=False)
    assert r.status_code == 301 and r.headers["location"] == "/en/vastu-career?x=1"


def test_head_block_matches_the_repo_rule(page):
    for needle in ('rel="canonical" href="https://www.axtroshastra.com/en/vastu-career"',
                   'hreflang="en" href="https://www.axtroshastra.com/en/vastu-career"',
                   'hreflang="x-default" href="https://www.axtroshastra.com/en/vastu-career"',
                   'property="og:title"', 'property="og:description"', 'property="og:image"',
                   'property="og:url" content="https://www.axtroshastra.com/en/vastu-career"',
                   'property="og:type"', 'name="description"'):
        assert needle in page, needle
    assert 'hreflang="hi"' not in page                      # Hindi twin ships after English is approved (owner)
    assert 'name="robots"' not in page                      # indexable


def test_page_is_in_the_sitemap_and_not_a_dead_link_anywhere(client, page):
    assert "/en/vastu-career" in client.get("/sitemap.xml").text
    for href in set(re.findall(r'href="(/[^"#]*)"', page)):
        if href.startswith("//"):
            continue
        assert client.get(href, follow_redirects=False).status_code in (200, 301, 302), href


def test_tracking_contract(page):
    assert "fbq('init'" in page and "fbq('track','Lead'" in page
    for ev in ("form_start", "generate_lead", "begin_checkout", "purchase"):
        assert f"gtag('event','{ev}'" in page, ev
    for ev in ("'InitiateCheckout'", "'Purchase'"):
        assert ev in page
    assert "eventID:RID" in page                            # report id is the event id (owner decision, spec section 8)


def test_form_options_match_the_engine(page):
    def opts(select_id):
        blk = re.search(r'<select id="%s".*?</select>' % select_id, page, re.S).group(0)
        return set(re.findall(r'<option value="([^"]+)"', blk))
    assert opts("f-segment") == set(vc.SEGMENTS)
    assert opts("f-desk") == set(vc.DIR_OR_UNSURE)
    assert opts("f-flex") == set(vc.FLEXIBILITY)
    assert opts("f-door") == set(vc.DIR_OR_UNSURE)          # plus the empty "skip" option, which has value=""


def test_no_flagged_vocabulary_in_visible_text():
    # The served page also carries the site-wide legal disclaimer injected by the shared footer chain (it says "medical",
    # exactly as on /en/numerology). That sentence is not this page's copy, so scan the page's own file.
    from pathlib import Path
    own = (Path(api.__file__).parent / "pages" / "vastu-career.html").read_text(encoding="utf-8")
    t = _text(own)
    assert len(t) > 3000
    for pat in FLAGGED:
        assert not re.search(pat, t, re.I), pat


def test_no_invented_reviews_no_persona_no_other_products(page):
    assert 'class="rev"' not in page.replace("'", '"') and '<div class="rev ' not in page
    t = _text(page)
    for p in PERSONAS:
        assert p not in t, p
    for other in ("Career Intelligence", "Business Growth", "Numerology Report", "Mulank and Bhagyank", "NASA", "planetary data"):
        assert other not in t, other


def test_honest_claims_only(page):
    t = _text(page)
    assert "belief system" in t and "not a science" in t
    assert not re.search(r"guarantee(d)? (marks|a job|income|promotion)", t, re.I)
    assert "We don't guarantee" in t.replace("’", "'")
    assert "Swiss" not in t and "ephemeris" not in t.lower()


# ---------------------------------------------------------------- the create route
def test_create_returns_report_id_and_free_teaser_only(client):
    r = client.post("/api/vastu-career", json=_body())
    assert r.status_code == 200
    d = r.json()
    assert re.fullmatch(r"[A-Za-z0-9_-]{16}", d["report_id"])     # secrets.token_urlsafe(12): opaque, no personal data
    assert "page" not in d["report_id"].lower() and "tester" not in d["report_id"].lower()
    t = d["teaser"]
    assert t["verdict"] == "acceptable" and t["segment"] == "student" and t["number"]["mulank"] == 5
    assert len(t["questions"]) == 5
    blob = repr(t).lower()
    for k in ("'fixes'", "'cards'", "'colours'", "'colour'"):
        assert k not in blob


def test_create_saves_a_vastu_career_report_and_it_is_unpaid(client):
    rid = client.post("/api/vastu-career", json=_body()).json()["report_id"]
    r = client.get(f"/api/report/{rid}")
    assert r.status_code == 200 and r.json().get("paid") is not True


def test_rule_b_reaches_the_preview_through_the_api(client):
    up = client.post("/api/vastu-career", json=_body(segment="professional", desk_direction="NE", dob="1995-06-03")).json()["teaser"]
    assert up["verdict"] == "ideal" and up["rule_b"] is True
    same = client.post("/api/vastu-career", json=_body(segment="professional", desk_direction="NE", dob="1995-06-04")).json()["teaser"]
    assert same["verdict"] == "acceptable"


@pytest.mark.parametrize("patch,field", [
    ({"name": ""}, "name"), ({"dob": "2031-01-01"}, "dob"), ({"dob": "garbage"}, "dob"),
    ({"segment": "pilot"}, "segment"), ({"desk_direction": "up"}, "desk_direction"),
    ({"desk_flexibility": "maybe"}, "desk_flexibility"), ({"door_direction": "sideways"}, "door_direction"),
    ({"phone": "12345"}, "phone"),
])
def test_bad_input_gets_an_inline_field_error_never_a_default(client, patch, field):
    r = client.post("/api/vastu-career", json=_body(**patch))
    assert r.status_code == 422
    assert r.json()["detail"]["field"] == field and r.json()["detail"]["message"]


def test_honeypot_blocks_bots(client):
    assert client.post("/api/vastu-career", json=_body(website="http://spam")).status_code == 400


def test_phone_formats_are_normalised(client):
    for p in ("+91 98765 91900", "09876591901", "919876591902"):
        assert client.post("/api/vastu-career", json=_body(phone=p)).status_code == 200


# ---------------------------------------------------------------- money
def test_server_price_is_99_by_product_never_the_499_default():
    assert api.VASTU_CAREER_PRICE_PAISE == 9900
    assert api._order_amount_paise({"product": "vastu_career"}) == 9900
    assert api._order_amount_paise({"product": "vastu_career", "payload": {"meta": {"variant": "/en/marriage-v4"}}}) == 9900
    assert api.PRODUCT_LABEL["vastu_career"] == "Vastu Career Report"
