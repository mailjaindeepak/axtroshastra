"""Vastu Career Report: the six per-option landing pages (/en/vastu-career/<option>).

Owner decision (24 Nov 2026): one COMMON hook on all six pages. They differ from the main page only in the option preselected in the
form (the form still asks the question). They are ad destinations: always noindex and out of the sitemap, so the main page is the one
for search. While an option is not on sale (vastu_career.READY_SEGMENTS) its page also says the complete report is coming soon.
"""
import html as _html
import re
from pathlib import Path

import pytest

import api
import vastu_career as vc

SLUGS = {"student": "student", "exam-aspirant": "exam_aspirant", "working-professional": "professional",
         "work-from-home": "wfh", "business-owner": "owner", "job-seeker": "job_seeker"}
FLAGGED = (r"anxi", r"stress", r"depress", r"panic", r"trauma", r"therap", r"counsel", r"mental", r"well-?being", r"wellness",
           r"burn-?out", r"overwhelm", r"healing", r"\bheal\b", r"diagnos", r"symptom", r"disorder", r"treatment", r"\bcure\b",
           r"remedy", r"disease", r"illness", r"patient", r"clinical", r"medic", r"doctor", r"health", r"weight", r"\bdiet\b",
           r"\bcalm", r"relief", r"peace of mind")
PERSONAS = ("Asha", "Rohan", "Neha", "Karan", "Vikram", "Sana")
PAGES = Path(api.__file__).parent / "pages"


def _text(h):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S)
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", t)))


def _h1(h):
    return re.sub(r"<[^>]+>", "", re.search(r"<h1>(.*?)</h1>", h, re.S).group(1))


@pytest.mark.parametrize("slug,seg", list(SLUGS.items()))
def test_page_is_served_and_the_option_is_preselected(client, slug, seg):
    r = client.get(f"/en/vastu-career/{slug}")
    assert r.status_code == 200
    h = r.text
    blk = re.search(r'<select id="f-segment".*?</select>', h, re.S).group(0)
    assert f'<option value="{seg}" selected>' in blk and blk.count("selected") == 1
    assert 'id="g-segment" hidden' not in h and "What best describes you?" in h        # the form still asks, with the right option already chosen
    assert set(re.findall(r'<option value="([^"]+)"', blk)) == set(vc.SEGMENTS)
    assert f"variant:'/en/vastu-career/{slug}'" in h
    assert "See all options" not in h and "Not a " not in _text(h)      # no redirect line: the form asks the question itself
    assert "<!--VC_" not in h                                  # helper markers never ship


@pytest.mark.parametrize("slug,seg", list(SLUGS.items()))
def test_every_option_page_is_noindex_with_no_canonical_and_the_notice_only_while_not_on_sale(client, slug, seg):
    h = client.get(f"/en/vastu-career/{slug}").text
    assert 'name="robots" content="noindex,follow"' in h and 'rel="canonical"' not in h and "hreflang" not in h
    notice = "Your free preview is ready now. The complete report for this option is coming soon."
    assert (notice in _text(h)) == (seg not in vc.READY_SEGMENTS)


def test_the_sitemap_lists_the_main_page_and_no_option_page(client):
    sm = client.get("/sitemap.xml").text
    assert "/en/vastu-career<" in sm and "/en/vastu-career/" not in sm


def test_all_six_pages_share_the_one_common_hook_with_the_main_page():
    main = (PAGES / "vastu-career.html").read_text(encoding="utf-8")
    for slug in SLUGS:
        h = (PAGES / f"vastu-career-{slug}.html").read_text(encoding="utf-8")
        assert _h1(h) == _h1(main) == "You spend hours at your desk. Does it face the right way?"
        for pat in (r"<title>.*?</title>", r'name="description" content="[^"]*"', r'property="og:title" content="[^"]*"', r'<p class="tag1">.*?</p>',
                    r'<div class="eyebrow ico">.*?</div>'):
            assert re.search(pat, h, re.S).group(0) == re.search(pat, main, re.S).group(0), (slug, pat)


@pytest.mark.parametrize("slug", list(SLUGS))
def test_vocabulary_personas_reviews_and_no_other_products(slug):
    h = (PAGES / f"vastu-career-{slug}.html").read_text(encoding="utf-8")
    t = _text(h)
    for pat in FLAGGED:
        assert not re.search(pat, t, re.I), (slug, pat)
    for p in PERSONAS:
        assert p not in t
    for other in ("Career Intelligence", "Business Growth", "Numerology Report", "NASA", "planetary data"):
        assert other not in t, other
    assert re.findall(r'<div class="who">(.*?)</div>', h) == ["Mallika, 21", "Kamal, 34"]
    assert "fbq('init'" in h and "fbq('track','Lead'" in h and "eventID:RID" in h


def test_unknown_option_is_a_404_and_bare_urls_redirect(client):
    assert client.get("/en/vastu-career/astronaut").status_code == 404
    r = client.get("/vastu-career/student?x=1", follow_redirects=False)
    assert r.status_code == 301 and r.headers["location"] == "/en/vastu-career/student?x=1"


def test_internal_links_resolve(client):
    for slug in SLUGS:
        h = (PAGES / f"vastu-career-{slug}.html").read_text(encoding="utf-8")
        for href in set(re.findall(r'href="(/[^"#]*)"', h)):
            if not href.startswith("//"):
                assert client.get(href, follow_redirects=False).status_code in (200, 301, 302), (slug, href)


def test_main_page_is_unchanged_by_the_option_pages(client):
    h = client.get("/en/vastu-career").text
    assert "Choose one" in h and 'rel="canonical" href="https://www.axtroshastra.com/en/vastu-career"' in h and 'name="robots"' not in h
