"""Integration tests for /en/marriage-v3 and /hi/marriage-v3 — the parent-voice
variant of marriage-v2 (same direct-to-payment funnel, copy rewritten for a
parent asking about their child's marriage timing)."""

_TRACKERS = ("G-NKRQM1HJ97", "1498790608627206", "clarity.ms/tag")


def test_marriage_v3_en_serves_200(client):
    r = client.get("/en/marriage-v3")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_marriage_v3_hi_serves_200(client):
    r = client.get("/hi/marriage-v3")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_marriage_v3_en_has_parent_voice_copy(client):
    html = client.get("/en/marriage-v3").text
    assert "When will my child" in html
    assert "Enter your child's name" in html
    assert "Get their report" in html


def test_marriage_v3_hi_has_parent_voice_copy(client):
    html = client.get("/hi/marriage-v3").text
    assert "मेरे बच्चे की शादी" in html
    assert "अपने बच्चे का नाम दर्ज करें" in html


def test_marriage_v3_en_seo_tags(client):
    html = client.get("/en/marriage-v3").text
    assert "<title>" in html and "</title>" in html
    assert 'name="description"' in html
    assert "<h1>" in html
    assert 'rel="canonical" href="https://www.axtroshastra.com/en/marriage-v3"' in html


def test_marriage_v3_hi_seo_tags(client):
    html = client.get("/hi/marriage-v3").text
    assert "<title>" in html and "</title>" in html
    assert 'name="description"' in html
    assert "<h1>" in html
    assert 'rel="canonical" href="https://www.axtroshastra.com/hi/marriage-v3"' in html


def test_marriage_v3_pages_have_all_trackers(client):
    for path in ("/en/marriage-v3", "/hi/marriage-v3"):
        html = client.get(path).text
        for t in _TRACKERS:
            assert t in html, f"{path} missing tracker {t}"
        assert html.count("clarity.ms/tag") == 1


def test_marriage_v3_funnel_posts_to_api_kundli(client):
    # The v3 form must submit to the same /api/kundli endpoint as v2 — the
    # funnel logic is byte-identical, only display copy differs.
    html = client.get("/en/marriage-v3").text
    assert "/api/kundli" in html
    assert 'id="kundliForm"' in html


def test_marriage_v3_does_not_affect_marriage_v2(client):
    # Regression guard: adding v3 must not change v2's copy or routes.
    en = client.get("/en/marriage-v2").text
    hi = client.get("/hi/marriage-v2").text
    assert "When will I <em>get married?</em>" in en
    assert "शादी <em>कब</em> होगी?" in hi
    assert 'href="/en/marriage-v2"' in en
    assert 'href="/hi/marriage-v2"' in hi
