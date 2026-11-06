"""Banned-word scan for the Annual Report: rendered output of every fixture, annual.py's teaser banks, the product
page's visible text and the on-page review blocks. STRICT: zero visible hits (a hit prints file/source + sentence).
Pure: run with --noconftest; never imports api.py. Fixtures come from tests/test_annual_report.py.
"""
import html as H
import os
import re
import sys
from html.parser import HTMLParser

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import annual  # noqa: E402
import test_annual_report as T  # noqa: E402

BANNED = (
    "slow slower slowest fastest costlier stretch window phase tendency tended tends steadier favourable favorable "
    "pivotal culminate auspicious pressure karma dasha house bhav transit dues patient squeeze pressing heavy "
    "AstroSage refund IIT IIM Lahiri"
).split() + ["exact planet positions"]
HEALTH = (  # CLAUDE.md 5b list as given in the task
    "anxiety anxious stress depression panic trauma therapy counselling mental wellbeing wellness burnout overwhelmed "
    "healing heal coping cope self-care diagnosis symptom disorder treatment cure remedy disease illness patient medical "
    "health doctor medicine weight diet fat calm relief tension worry breathe"
).split()
FESTIVAL = "diwali deepavali lantern kandil toran diya rangoli firework puja muhurat lakshmi garland marigold".split()
WORDS = BANNED + HEALTH + FESTIVAL


def _rx(w):
    # whole word, optional plural: 'house' hits 'houses' but never 'household'; 'cope' never hits 'scope';
    # 'patient' never hits 'patience'.
    return re.compile(r"(?<![\w-])" + re.escape(w) + r"(?:e?s)?(?![\w-])", re.I)


PATTERNS = {w: _rx(w) for w in WORDS}
EXTRA = {
    "month N of 12": re.compile(r"month \d+ of 12", re.I),
    "Watch: Watch": re.compile(r"Watch:\s*Watch", re.I),
    "on see p": re.compile(r"\bon see p\b", re.I),
    # 'year' used as a verdict: an adjective before it, or 'year is/will be/looks ...'
    "year as verdict": re.compile(r"\b(?:good|bad|strong|careful|mixed|hard|easy|best|worst|big|slow|lucky|difficult|tough|heavy|"
                                  r"great|poor|quiet|busy)\s+year\b|\byear\s+(?:is|will be|looks|may be|could be)\b", re.I),
}


def sentences(text):
    return re.split(r"(?<=[.!?])\s+", text)


def scan(text, own_names=()):
    for n in own_names:                                  # a person's own name is never a hit
        for part in re.split(r"[\s-]+", n or ""):
            if part:
                text = re.sub(re.escape(part), "NAME", text)
    hits = []
    for s in sentences(text):
        for w, rx in {**PATTERNS, **EXTRA}.items():
            if rx.search(s):
                hits.append(f"[{w}] {s.strip()[:160]}")
    return hits


def headings_dosha(doc):
    return [text for text in (T.text_of(m) for m in re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", doc, re.S))
            if re.search(r"\bdosha\b", text, re.I)]


class _Visible(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip, self.out = 0, []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, d):
        if not self.skip and d.strip():
            self.out.append(d.strip())


def visible_of(html):
    p = _Visible()
    p.feed(html)
    return " ".join(p.out)


def strings_in(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from strings_in(v)
    elif isinstance(o, (list, tuple)):
        for v in o:
            yield from strings_in(v)


# ---------------------------------------------------------------- rendered fixtures
@pytest.mark.parametrize("name", T.NAMES)
def test_rendered_report_has_no_banned_words(name):
    f = T.reports()[name]["facts"]
    doc = T.doc_of(name)
    hits = scan(T.text_of(doc), [f.get("name"), f.get("first_name")])
    assert not hits, f"{name}: {len(hits)} hits\n" + "\n".join(sorted(set(hits)))
    assert not headings_dosha(doc), headings_dosha(doc)


@pytest.mark.parametrize("name", ["compute_t0_male", "compute_t3_female"])
def test_compute_teaser_has_no_banned_words(name):
    rep = T.reports()[name]
    hits = scan(" . ".join(strings_in(rep["teaser"])), [rep["facts"].get("name"), rep["facts"].get("first_name")])
    assert not hits, "\n".join(sorted(set(hits)))


def test_annual_py_teaser_banks_have_no_banned_words():
    strs = []
    for k, v in vars(annual).items():
        if k.startswith("__") or not isinstance(v, (dict, list, tuple, str)):
            continue
        strs += [s for s in strings_in(v) if len(s) > 2]
    assert len(strs) > 100                                # the banks really were collected
    hits = scan(" . ".join(strs))
    assert not hits, "\n".join(sorted(set(hits)))


# ---------------------------------------------------------------- product page + reviews
PAGE = os.path.join(ROOT, "pages", "annual-report.html")
HOME = os.path.join(ROOT, "pages", "home.html")
REV = re.compile(r'<div class="rev">(?:(?!<div class="rev">).)*?</p><div class="who">.*?</div></div>', re.S)


def _reviews():
    page = [r for r in REV.findall(open(PAGE, encoding="utf-8").read())]
    home = [r for r in REV.findall(open(HOME, encoding="utf-8").read()) if '<div class="tag">Annual Report</div>' in r]
    return page, home


def test_product_page_visible_text_has_no_banned_words():
    hits = scan(visible_of(open(PAGE, encoding="utf-8").read()))
    assert not hits, "pages/annual-report.html:\n" + "\n".join(sorted(set(hits)))


def test_review_blocks_found():
    page, home = _reviews()
    assert len(page) >= 5, len(page)
    assert len(home) >= 5, len(home)


def test_review_blocks_have_no_dashes():
    page, home = _reviews()
    bad = [(src, T.text_of(r)) for src, rs in (("annual-report.html", page), ("home.html", home)) for r in rs
           if re.search("[—–]", H.unescape(r))]
    assert not bad, bad


def test_review_blocks_have_no_banned_words():
    page, home = _reviews()
    hits = [f"{src}: {h}" for src, rs in (("annual-report.html", page), ("home.html", home))
            for r in rs for h in scan(T.text_of(r))]
    assert not hits, "\n".join(hits)
