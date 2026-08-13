"""V3 parent-focused Marriage page (/en/marriage-parent, /hi/marriage-parent).

Review-only variant of /en/marriage2 & /hi/marriage2, copy-adapted for a parent
asking about their child's marriage. These tests only cover the page routes and
their static copy; the underlying kundli/payment flow is already covered by the
marriage2 tests since both variants share the same JS/API contract.
"""


def test_en_marriage_parent_200(client):
    r = client.get("/en/marriage-parent")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_en_marriage_parent_headline_and_placeholder(client):
    r = client.get("/en/marriage-parent")
    body = r.text
    assert "When will my child <em>get married?</em>" in body
    assert "placeholder=\"Enter your child's name\"" in body


def test_hi_marriage_parent_200(client):
    r = client.get("/hi/marriage-parent")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_hi_marriage_parent_headline_and_placeholder(client):
    r = client.get("/hi/marriage-parent")
    body = r.text
    assert "मेरे बच्चे की शादी" in body
    assert "अपने बच्चे का नाम दर्ज करें" in body


def test_marriage_parent_pages_do_not_link_cta_to_original_variant(client):
    # Sanity: the parent page's own CTA copy is parent-framed, not the
    # original subject-framed copy from /en/marriage2.
    en = client.get("/en/marriage-parent").text
    assert "Get your child report" in en
    assert "Get my report" not in en
    assert "When will I <em>get married?</em>" not in en


def test_marriage_parent_sticky_bar_cta_is_parent_framed(client):
    # Regression guard: the sticky bar CTA is a separate string from the
    # main CTA button and was previously missed by earlier copy passes
    # (it read "Get Child's Report" / "बच्चे की रिपोर्ट पाइए" -- missing the
    # "your"/"अपने" that the rest of the page's CTAs use).
    en = client.get("/en/marriage-parent").text
    assert 'id="stickyBtn"' in en
    assert "Get Your Child Report" in en
    assert "Get Child's Report" not in en

    hi = client.get("/hi/marriage-parent").text
    assert "अपने बच्चे की रिपोर्ट पाइए" in hi


def test_existing_marriage2_routes_unaffected(client):
    """Regression guard: creating the parent variant must not touch the
    live /en/marriage2 and /hi/marriage2 routes or their copy."""
    en = client.get("/en/marriage2")
    assert en.status_code == 200
    assert "When will I <em>get married?</em>" in en.text

    hi = client.get("/hi/marriage2")
    assert hi.status_code == 200
    assert "शादी <em>कब</em> होगी?" in hi.text
