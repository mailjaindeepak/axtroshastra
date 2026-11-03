"""Mulank free preview: five cards, personal pages 1-2, static pages 3-5, eligibility variants,
no leaks, safe CTA. HTML-level tests run anywhere; the PDF test needs headless Chrome."""
import html
import inspect
import re
from datetime import date

import pytest

import mulank_content as mc
import numerology
import numerology_preview as P

TODAY = date(2026, 11, 3)
PAGE = re.compile(r'<section class="page[^"]*">.*?</section>', re.S)


def _reg(d, m, y):
    res = numerology.compute_mulank(d, m, y, today=TODAY)
    return {k: mc.Entry(mc.VERIFIED, "Test Reviewer", "2026-11-03") for k in mc.required_keys(res)}


def _build(d=29, m=7, y=1990, name="Kiran Mehta", eligible=True, **kw):
    reg = _reg(d, m, y) if eligible else None
    return P.build_preview(d, m, y, name, today=TODAY, registry=reg, **kw)


def _pages(r):
    return PAGE.findall(r["html"])


def _text(fragment):
    t = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", fragment, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))


def _one_dob_per_pair():
    seen = {}
    for y in range(1950, 2010):
        for m in range(1, 13):
            for d in range(1, 29):
                seen.setdefault(numerology.compute_mulank(d, m, y, today=TODAY)["pair_key"], (d, m, y))
    assert len(seen) == 81
    return list(seen.values())


def test_always_exactly_five_pages_eligible_or_not():
    for elig in (True, False):
        for d, m, y in ((29, 7, 1990), (22, 11, 2000), (1, 1, 1901), (9, 9, 1999)):
            r = _build(d, m, y, eligible=elig)
            assert len(_pages(r)) == 5 and r["pages"] == 5 and r["eligible"] is elig


def test_shipped_registry_makes_every_pair_unavailable():
    for d, m, y in _one_dob_per_pair():
        r = P.build_preview(d, m, y, "Test", today=TODAY)
        assert r["eligible"] is False
        assert "data-action=\"checkout\"" not in r["html"] and "₹" not in r["html"]


def test_static_pages_identical_for_all_81_pairs_and_any_name():
    base = None
    for i, (d, m, y) in enumerate(_one_dob_per_pair()):
        r = _build(d, m, y, name=f"Person {i} <b>")
        p = _pages(r)
        assert len(p) == 5
        if base is None:
            base = p[2:]
        assert p[2:] == base, (d, m, y)
    assert _pages(_build(15, 3, 1985))[0] != _pages(_build(29, 7, 1990))[0]


def test_unavailable_static_pages_identical_and_result_free():
    seen = None
    for d, m, y in _one_dob_per_pair():
        p = _pages(_build(d, m, y, name="Anyone", eligible=False))
        seen = seen or p[2:]
        assert p[2:] == seen


def test_static_builders_take_no_result_arguments():
    for fn in (P.render_page3, P.render_locked_quickref, P.render_cta_visual, P.render_unlock_minis):
        assert not inspect.signature(fn).parameters
    assert set(inspect.signature(P.render_page4).parameters) == {"cta_url"}
    assert set(inspect.signature(P.render_page5).parameters) == {"buyable", "cta_url"}
    params = set(inspect.signature(P.build_preview).parameters)
    assert not {"gender", "sex"} & params


def test_locked_pages_have_no_values_names_planets_or_dates():
    r = _build(29, 7, 1990, name="Kiran Mehta")
    p3, p4, p5 = (_text(x) for x in _pages(r)[2:])
    assert not re.search(r"\d", p3) and not re.search(r"\d", p5)
    assert re.sub(r"\u20b9\d+", "", p4).strip() and not re.search(r"\d", re.sub(r"\u20b9\d+", "", p4))
    forbidden = (r"Kiran", r"Mehta", r"1990", r"Sun", r"Moon", r"Jupiter", r"Rahu", r"Mercury", r"Venus", r"Ketu",
                 r"Saturn", r"Mars", r"Ruby", r"Pearl", r"Emerald", r"Sapphire", r"Monday", r"Tuesday", r"Wednesday",
                 r"Thursday", r"Friday", r"Saturday", r"Sunday", r"Red", r"Green", r"Blue", r"Yellow", r"White")
    for t in (p3, p4, p5):
        for w in forbidden:
            assert not re.search(rf"\b{w}\b", t), w
    raw = "".join(_pages(r)[2:])
    assert "<!--" not in raw and "display:none" not in raw and 'type="hidden"' not in raw
    assert "Kiran" not in raw and "Mehta" not in raw and "1990" not in raw

def test_pages_one_and_two_carry_the_computed_values():
    p = _pages(_build(29, 7, 1990))
    assert "Kiran Mehta" in p[0] and "Born 29 July 1990" in p[0]
    assert "2 + 9 = 11" in p[0] and "1 + 1 = <b>2</b>" in p[0] and "3 + 7 = 10, then 1 + 0 = <b>1</b>" in p[0]
    assert P.W_3A in p[0]
    assert "Mulank 2 with Bhagyank 1" in p[1]
    assert P.W_3A not in _pages(_build(15, 3, 1985))[0]


def test_unreviewed_interpretations_are_not_rendered():
    t = _text("".join(_pages(_build())[:2])).lower()
    for bad in ("friend", "adversary", "complement", "empathetic", "suits you", "you are a "):
        assert bad not in t


def test_eligible_shows_prices_and_checkout_but_unavailable_does_not():
    e = _build(cta_url="/en/numerology-checkout")
    p4 = _pages(e)[3]
    assert "₹499" in p4 and "₹299" in p4 and "You save ₹200" in p4
    assert p4.count('data-action="checkout"') == 1 and 'href="/en/numerology-checkout"' in p4
    assert P.CTA1 in p4 and P.CTA_HEAD in p4
    p5 = _pages(e)[4]
    assert P.CTA2 in p5 and p5.count('data-action="checkout"') == 1
    u = _build(eligible=False)
    for p in _pages(u)[3:]:
        assert "₹" not in p and "checkout" not in p and "pv-cta" not in p
    assert "not ready for your numbers yet" in _pages(u)[3]


def test_waitlist_only_rendered_with_owner_supplied_consent_text():
    assert "waitlist" not in _pages(_build(eligible=False))[3]
    w = _pages(_build(eligible=False, waitlist_consent_text='I agree <script>x</script>'))[3]
    assert 'name="waitlist_consent"' in w and "checked" not in w
    assert "<script>x" not in w and "&lt;script&gt;" in w


def test_cta_without_url_is_a_button_for_the_page_script():
    assert '<button type="button" class="pv-cta wide" data-action="checkout"' in _pages(_build())[3]


@pytest.mark.parametrize("bad", ["javascript:alert(1)", "//evil.example/x", "http://insecure.test", "data:text/html,x", " /x"])
def test_unsafe_cta_url_rejected(bad):
    with pytest.raises(ValueError):
        _build(cta_url=bad)


def test_cta_url_is_escaped():
    p4 = _pages(_build(cta_url='https://pay.example/c?a=1&b="2"'))[3]
    assert "&amp;b=&quot;2&quot;" in p4


def test_name_escaped_cleaned_and_validated():
    p1 = _pages(_build(name='<script>alert(1)</script>"&\'Z'))[0]
    assert "<script>" not in p1 and "&lt;script&gt;" in p1
    assert 'data-slot="name">A B<' in _pages(_build(name="A\n\t  B"))[0]
    for bad in ("", "   ", None, "x" * 81):
        with pytest.raises(ValueError):
            _build(name=bad)
    assert "x" * 80 in _pages(_build(name="x" * 80))[0]


def test_bad_dob_rejected():
    for args in ((31, 2, 1990), (1, 1, 2999), (1, 13, 1990), (1, 1, 1899)):
        with pytest.raises(numerology.NumerologyInputError):
            P.build_preview(*args, "Name", today=TODAY)


def test_document_has_no_pii_in_head_and_is_noindex():
    html = _build(name="Kiran Mehta")["html"]
    head = html[: html.index("<body>")]
    assert "Kiran" not in head and "1990" not in head
    assert 'name="robots" content="noindex,nofollow"' in head and "no-referrer" in head


def test_equal_number_pair_wording():
    for y in range(1950, 2010):
        for m in range(1, 13):
            for d in range(1, 29):
                E = numerology.compute_mulank(d, m, y, today=TODAY)
                if E["mulank"]["number"] == E["bhagyank"]["number"]:
                    assert "are both" in _pages(P.build_preview(d, m, y, "Name", today=TODAY))[1]
                    return
    pytest.fail("no equal pair")


def test_price_text_comes_from_pricing_module():
    import mulank_pricing as pr
    assert P.inr(pr.MULANK_PRICE_PAISE) == "₹299" and P.inr(pr.MULANK_LIST_PRICE_PAISE) == "₹499"


# ------------------------------------------------------------------ real PDF (needs Chrome)
def test_pdf_is_exactly_five_pages_323x623_with_no_locked_text():
    fitz = pytest.importorskip("pymupdf")
    import pdfgen
    pdf = P.render_pdf(_build(cta_url="/en/numerology-checkout")["html"])
    if not pdf:
        pytest.skip("headless Chrome not available")
    doc = fitz.open(stream=pdf, filetype="pdf")
    assert len(doc) == 5
    for pg in doc:
        assert round(pg.rect.width) == 323 and round(pg.rect.height) == 623
    for i in (2, 4):
        body = re.sub(r"\n0\d\n", "\n", doc[i].get_text())      # the printed page number is not locked content
        assert not re.search(r"\d", body)
    assert "₹299" in doc[3].get_text() and "Kiran" not in doc[2].get_text() + doc[3].get_text() + doc[4].get_text()
    meta = " ".join(str(v) for v in (doc.metadata or {}).values())
    assert "Kiran" not in meta and "1990" not in meta

