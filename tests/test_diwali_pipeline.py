"""INTEGRATE: engine -> bank -> render for 6 real charts, no narrative (bank only).
Pure: no DB, no api.py, no network. Run with --noconftest."""
import functools
import html as H
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import diwali  # noqa: E402
import diwali_bank  # noqa: E402
import diwali_report  # noqa: E402

CHARTS = [  # Vikram = docs/diwali/mock/persona.json; the rest cover the branches the brief names
    dict(name="Vikram Rao", dob="1984-08-14", tob="07:40", tz=5.5, lat=18.5204, lon=73.8567, place="Pune",
         gender="male", work_type="business", steering="money"),
    dict(name="Ananya Iyer", dob="2004-02-03", tob="11:15", tz=5.5, lat=13.0827, lon=80.2707, place="Chennai",
         gender="female", work_type="student", steering=None),                       # 22, skipped the area
    dict(name="Sushila Devi", dob="1963-06-21", tob="05:30", tz=5.5, lat=26.9124, lon=75.7873, place="Jaipur",
         gender="female", work_type="home", steering="family"),                      # 63, home-maker, Family
    dict(name="Rohit Sharma", dob="1991-11-30", tob="12:00", tz=5.5, lat=28.6139, lon=77.2090, place="Delhi",
         gender="male", work_type="job", steering="career", time_quality="T3"),      # unsure birth time
    dict(name="Farhan Qureshi", dob="1978-04-09", tob="21:50", tz=5.5, lat=22.5726, lon=88.3639, place="Kolkata",
         gender="male", work_type="business", steering="luck"),                      # Better luck
    dict(name="Meera Joshi", dob="1996-09-17", tob="16:20", tz=5.5, lat=19.0760, lon=72.8777, place="Mumbai",
         gender="female", work_type="job", steering="marriage",
         gift_on=True, giver_name="", gift_message=""),                              # gift, empty message
]
IDS = [c["name"].split()[0] for c in CHARTS]
MONTH_PAGES = {"s-0-1", "s-0-6", "s-1-months", "s-2-1", "s-2-2", "s-2-3"}   # cover dob, the date pages, date tables
# opt() keys the renderer may read with a built-in default (chrome labels, optional extras)
OPTIONAL = {"lookback.all", "lookback.all.short", "lookback.headline", "lookback.good.label", "lookback.hard.label",
            "lookback.good.short", "lookback.hard.short"}


class _Track(dict):
    def __init__(self, d):
        super().__init__(d)
        self.used, self.miss = set(), set()

    def __getitem__(self, k):
        self.used.add(k)
        return super().__getitem__(k)

    def get(self, k, d=None):
        self.used.add(k)
        if k not in self:
            self.miss.add(k)
        return super().get(k, d)


@functools.lru_cache(maxsize=None)
def build(i):
    c = dict(CHARTS[i])
    args = [c.pop(k) for k in ("name", "dob", "tob", "tz", "lat", "lon")]
    p = diwali.compute_diwali(*args, **c)
    assert not p.get("narrative")
    orig, box = diwali_bank.bank, {}

    def tracked(pl):
        box["t"] = _Track(orig(pl))
        return box["t"]
    diwali_bank.bank = tracked
    try:
        html = diwali_report.render_diwali(p)
    finally:
        diwali_bank.bank = orig
    return p, html, box["t"]


def visible(fragment):
    f = re.sub(r"<(style|script|defs)\b.*?</\1>", " ", fragment, flags=re.S)
    f = re.sub(r"<svg\b.*?</svg>", " ", f, flags=re.S)       # pictures may carry months
    return re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", f))).strip()


def cards(html):
    return re.findall(r'<section class="page.*?</section>', html, flags=re.S)


def cid(card):
    m = re.match(r'<section [^>]*\bid="([^"]+)"', card)
    return m.group(1) if m else ""


@pytest.mark.parametrize("i", range(len(CHARTS)), ids=IDS)
def test_renders_complete_doc(i):
    p, html, _ = build(i)
    assert html.startswith("<!DOCTYPE html>") and html.rstrip().endswith("</html>")
    cs = cards(html)
    assert 55 <= len(cs) <= 64 and html.count('<section class="page') == len(cs)
    assert "p.@@" not in html and "@@" not in html
    v = visible(html)
    assert "None" not in v and "{" not in v and "}" not in v
    for lab in ("Money", "Business", "Career", "Marriage", "Family", "Better luck"):   # label printed once
        assert f"{lab}: {lab}" not in v and "Family: Family" not in v


@pytest.mark.parametrize("i", range(len(CHARTS)), ids=IDS)
def test_every_prose_key_resolves(i):
    p, _, t = build(i)
    assert not (t.miss - OPTIONAL), sorted(t.miss - OPTIONAL)
    for k in t.used - t.miss:
        assert isinstance(t[k], str), k
        if not k.startswith("gift."):
            assert t[k].strip(), f"empty prose {k}"
    narr = [k for k, _, _ in diwali_bank.NARR_KEYS]
    assert set(narr) <= set(t), sorted(set(narr) - set(t))


@pytest.mark.parametrize("i", range(len(CHARTS)), ids=IDS)
def test_used_prose_lints_clean(i):
    _, _, t = build(i)
    bad = {}
    for k in t.used - t.miss:
        dates = k.startswith(("timeline.", "months.", "wrapped."))
        probs = diwali_bank.lint_text(t[k], allow_dates=dates)
        if probs:
            bad[k] = (probs, t[k][:120])
    assert not bad, bad


@pytest.mark.parametrize("i", range(len(CHARTS)), ids=IDS)
def test_visible_text_lints_clean(i):
    p, html, _ = build(i)
    span = p["meta"]["span"]
    cs = cards(html)
    after_months = {cs.index(c) + 1 for c in cs if cid(c) == "s-1-months"}
    bad = []
    for n, c in enumerate(cs):
        v = visible(c).replace(f"({span})", "").replace(span, "")
        v = re.sub(r"Diwali 20\d\d", "Diwali", v)               # "Diwali 2026 to Diwali 2027" chrome
        if cid(c) == "b-3":   # the houses table pairs each house number with its plain name by design
            v = re.sub(r"\b(1st|2nd|3rd|[4-9]th|1[0-2]th)\b", "", v)
        dates = cid(c) in MONTH_PAGES or n in after_months or "Your Wrapped card" in v
        for s in re.split(r"(?<=[.!?])\s+", v):
            probs = diwali_bank.lint_text(s, allow_dates=dates)
            if probs:
                bad.append((n + 1, cid(c), probs, s[:120]))
    assert not bad, bad


@pytest.mark.parametrize("i", range(len(CHARTS)), ids=IDS)
def test_every_href_resolves(i):
    _, html, _ = build(i)
    ids = set(re.findall(r'\bid="([^"]+)"', html))
    hrefs = set(re.findall(r'href="#([^"]+)"', html))
    assert hrefs and not (hrefs - ids), sorted(hrefs - ids)
    for card in cards(html):
        for ref, txt in re.findall(r'<a [^>]*href="#([^"]+)"[^>]*>(.*?)</a>', card, flags=re.S):
            m = re.search(r"p\.(\d+)", txt)
            if m:   # page number points at the card that holds the id
                k = next(j for j, c in enumerate(cards(html), 1) if f'id="{ref}"' in c)
                assert int(m.group(1)) == k, (ref, txt, k)


@pytest.mark.parametrize("i", range(len(CHARTS)), ids=IDS)
def test_no_persona_leak(i):
    p, html, _ = build(i)
    v = visible(html)
    assert "Priya" not in v
    if p["meta"]["first_name"] != "Vikram":
        assert "Vikram" not in v
    assert p["meta"]["first_name"] in v


@pytest.mark.parametrize("i", range(len(CHARTS)), ids=IDS)
def test_gift_page(i):
    p, html, _ = build(i)
    gift = [c for c in cards(html) if cid(c) == "s-0-2"]
    if not p["meta"]["gift"]["on"]:
        assert not gift and "A Diwali gift for you" not in visible(html)
        return
    assert len(gift) == 1
    g = visible(gift[0])
    assert "A Diwali gift for you" in g
    assert visible(diwali_bank.DEFAULT_GIFT_MESSAGE) in g          # empty message -> ready-written one
    assert cards(html).index(gift[0]) == 1                          # right after the cover


@pytest.mark.parametrize("i", range(len(CHARTS)), ids=IDS)
def test_area_order_respected(i):
    p, html, _ = build(i)
    order, steer, work = p["area_order"], p["meta"]["steering"], p["meta"]["work_type"]
    assert sorted(order) == sorted(diwali.AREAS)
    if steer in diwali.AREAS:
        assert order[0] == steer and p["first_reason"] == "picked"
    else:
        assert order[0] == diwali.SITUATION_ORDER[work][0]
    seq = [cid(c)[2:] for c in cards(html) if cid(c).startswith("a-")]
    expect = (["luck"] + order) if steer == "luck" else (order + ["luck"])
    assert seq == expect
    picked = re.findall(r"You picked ([A-Za-z &]+?), so", visible(html))
    if steer:
        assert picked and set(picked) == {diwali.AREA_LABEL[steer]}
    else:
        assert not picked


@pytest.mark.parametrize("i", range(len(CHARTS)), ids=IDS)
def test_unsure_time_has_no_best_time_label(i):
    """Spec §2 rule 10: T2/T3 never shows a 'Best time' label, diya or headline."""
    p, html, _ = build(i)
    if p["meta"]["time_quality"] not in ("T2", "T3"):
        bt = p["best_time"]
        real = any(m["tone"] == "best" and bt["from"] <= m["ym"] <= bt["to"] for m in p["months"])
        assert diwali_bank.has_best(p) == (real and any(a["windows"]["best"] for a in p["areas"].values()))
        return
    assert not diwali_bank.has_best(p)
    body = html[html.index('<section class="page'):]                   # skip the shared symbol defs
    v = re.sub(r"Full bloom your best time|Bright with rays: best time|mean a best time", "", visible(body))  # picture keys
    assert "your best time" not in v.lower() and "Best time" not in v and "single best time" not in v.lower()
    assert ">BEST TIME<" not in body and not re.search(r"Best: [A-Z][a-z]{2}", body)
    assert "burn brightest" not in v and "burns brightest" not in v


@pytest.mark.parametrize("i", range(len(CHARTS)), ids=IDS)
def test_timeline_page_reads_once(i):
    """s-0-6: the headline never goes from the best time to the best time, "single best time" only for a
    real best run, and no legend line or theme repeats."""
    p, html, _ = build(i)
    card = next(c for c in cards(html) if cid(c) == "s-0-6")
    head = visible(re.search(r'<h2 class="action">(.*?)</h2>', card).group(1))
    assert head.lower().count("best time") <= 1 and not head.startswith("From "), head
    has = diwali_bank.has_best(p)
    assert ("single best time" in visible(card).lower()) == has
    if not has:
        assert "best time" not in head.lower()
    legs = re.findall(r'<span class="lt">(.*?)</span>', card, flags=re.S)
    lines = [re.sub(r"^<b>.*?</b>\s*", "", x) for x in legs]
    themes = [t["theme"] for t in p["timeline"]]
    assert len(set(lines)) == len(lines) and len(set(themes)) == len(themes), (themes, lines)


@pytest.mark.parametrize("i", range(len(CHARTS)), ids=IDS)
def test_why_lines_never_name_a_planet_place_twice(i):
    """A Why line never restates the same planet sitting in the same part (Vikram career.t5 once did)."""
    _, _, t = build(i)
    for k in [k for k in t.used if k.endswith(".why")]:
        sits = re.findall(r"\b(Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)\b[^.;]*?\bsits in (the part for yourself|the [a-z -]+? part)", t[k])
        assert len(sits) == len(set(sits)), (k, t[k])


@pytest.mark.parametrize("i", range(len(CHARTS)), ids=IDS)
def test_blessing_heading_not_eyebrow(i):
    _, html, _ = build(i)
    card = next(c for c in cards(html) if cid(c) == "s-2-6")
    assert "A Diwali blessing" not in visible(re.search(r'<div class="nh">(.*?)</div>', card).group(1))


@pytest.mark.parametrize("i", range(len(CHARTS)), ids=IDS)
def test_mock3c_area_shapes(i):
    """Mock 3C v2: Business opener = dials + topic 1; a business owner's Career opener = plain card + topics 1-2."""
    p, html, _ = build(i)
    d = p["areas"]["business"]["dials"]
    assert [(x["left"], x["right"]) for x in d] == [("Job", "Business"), ("Alone", "Partner")]
    assert all(0 <= x["value"] <= 1 for x in d)
    cs = {cid(c): c for c in cards(html)}
    b = visible(cs["a-business"])
    assert "two dials" in b
    assert b.count("Do:") <= 1 and "Business · 1 of" not in visible(html)   # topic 1 unless too long to fit
    car = cs["a-career"]
    if p["meta"]["work_type"] == "business":
        assert car.startswith('<section class="page" ') and 1 <= visible(car).count("Do:") <= 2
    else:
        assert car.startswith('<section class="page ex" ') and "Do:" not in visible(car)


def test_user_text_never_becomes_a_page_reference():
    p = diwali.compute_diwali("Ravi", "1990-01-01", "10:00", 5.5, 28.6, 77.2, gender="male", work_type="job",
                              steering="money", gift_on=True, giver_name="A@@b-1@@", gift_message="Hi p.@@b-1@@ @@x@@")
    html = diwali_report.render_diwali(p)
    assert "@@" not in html and "Hi p.&#64;&#64;b-1&#64;&#64; &#64;&#64;x&#64;&#64;" in html


# ---- print checks: real headless Chrome, found the way the app finds it (pdfgen.chrome_bin: CHROME_BIN,
# Playwright's browser store, then /usr/bin/google-chrome etc., which the ubuntu-latest CI runner ships).
# A missing Chrome or Playwright FAILS these checks with a clear message; they never skip silently. ----
import pdfgen  # noqa: E402

CHROME = pdfgen.chrome_bin()


def need_chrome():
    """The Chrome binary, or a test failure that says how to get one."""
    if not CHROME:
        pytest.fail("no Chrome found by pdfgen.chrome_bin(): set CHROME_BIN, or install one "
                    "(python -m playwright install chromium; CI's ubuntu-latest ships /usr/bin/google-chrome)")
    return CHROME


def need_playwright():
    try:
        from playwright import sync_api
    except ImportError:
        pytest.fail("python package 'playwright' missing: pip install playwright (the print checks need it)")
    return sync_api
_FIT_JS = """() => [...document.querySelectorAll('section.page')].map((s, n) => {
  const c = s.querySelector(':scope > .col') || s, r = s.getBoundingClientRect(), b = c.getBoundingClientRect();
  return [n + 1, s.id, b.top - r.top, r.bottom - b.bottom, parseFloat(s.style.getPropertyValue('--fit') || 1)];
})"""


@pytest.fixture(scope="module")
def chrome_page():
    pw = need_playwright()
    with pw.sync_playwright() as p:
        b = p.chromium.launch(executable_path=need_chrome())
        pg = b.new_page(viewport={"width": 430, "height": 830})
        pg.emulate_media(media="print")
        yield pg
        b.close()


@pytest.mark.parametrize("i", range(len(CHARTS)), ids=IDS)
def test_print_cards_fit(i, chrome_page, tmp_path):
    """In print every card is a fixed 430x830 box (overflow hidden): its column must stay clear of the top
    edge and of the Contents link / page number at the bottom, and the print fit may shrink text only a little."""
    _, html, _ = build(i)
    f = tmp_path / f"d{i}.html"
    f.write_text(html)
    chrome_page.goto(f"file://{f}")
    chrome_page.evaluate("document.fonts.ready")
    chrome_page.wait_for_timeout(300)
    bad = [(n, cid_, round(top), round(bot), fit) for n, cid_, top, bot, fit in chrome_page.evaluate(_FIT_JS)
           if top < 10 or bot < 28 or fit < 0.85]
    assert not bad, bad


@pytest.mark.parametrize("i", [0, 3, 5], ids=[IDS[0], IDS[3], IDS[5]])
def test_pdf_pages(i, tmp_path):
    """Headless Chrome PDF: 323x623 pt pages, one page per card."""
    import subprocess

    import fitz                                                        # pymupdf: a runtime dependency
    chrome = need_chrome()
    _, html, _ = build(i)
    src, out = tmp_path / "r.html", tmp_path / "r.pdf"
    src.write_text(html)
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=10000",
                    f"--print-to-pdf={out}", f"file://{src}"], capture_output=True, timeout=120, check=True)
    d = fitz.open(str(out))
    assert len(d) == len(cards(html))
    for pg in d:
        assert (round(pg.rect.width), round(pg.rect.height)) == (323, 623)


# ---- real overflow check: 8 varied charts, laid out by headless Chrome in print mode ----
OVERFLOW_CHARTS = [   # every work type, both genders, T0/T3, gift with name+message, gift empty, every steering
    dict(name="Arjun Mehta", dob="1988-05-12", tob="09:20", tz=5.5, lat=28.6139, lon=77.2090, place="Delhi",
         gender="male", work_type="job", steering="money"),
    dict(name="Kavita Shah", dob="1979-12-02", tob="14:45", tz=5.5, lat=23.0225, lon=72.5714, place="Ahmedabad",
         gender="female", work_type="business", steering="business", gift_on=True, giver_name="Neel",
         gift_message="For the shop and for you. Have a bright year, didi."),
    dict(name="Ishita Rao", dob="2005-07-30", tob="12:00", tz=5.5, lat=12.9716, lon=77.5946, place="Bengaluru",
         gender="female", work_type="student", steering="career", time_quality="T3"),
    dict(name="Ramesh Pillai", dob="1958-01-19", tob="06:10", tz=5.5, lat=13.0827, lon=80.2707, place="Chennai",
         gender="male", work_type="home", steering="family", gift_on=True, giver_name="", gift_message=""),
    dict(name="Sneha Kulkarni", dob="1993-03-08", tob="19:35", tz=5.5, lat=18.5204, lon=73.8567, place="Pune",
         gender="female", work_type="job", steering="marriage"),
    dict(name="Imran Sheikh", dob="1975-10-25", tob="23:15", tz=5.5, lat=17.3850, lon=78.4867, place="Hyderabad",
         gender="male", work_type="business", steering="luck", time_quality="T3"),
    dict(name="Lata Bose", dob="1969-08-04", tob="03:50", tz=5.5, lat=22.5726, lon=88.3639, place="Kolkata",
         gender="female", work_type="home", steering=None),
    dict(name="Dev Malhotra", dob="2002-02-14", tob="16:05", tz=5.5, lat=26.9124, lon=75.7873, place="Jaipur",
         gender="male", work_type="student", steering="money"),
]
OVERFLOW_IDS = [c["name"].split()[0] for c in OVERFLOW_CHARTS]
# per card: the lowest and highest edge of anything drawn inside the column, after the print-fit script ran
_EDGES_JS = """() => [...document.querySelectorAll('section.page')].map((s, n) => {
  const r = s.getBoundingClientRect(), c = s.querySelector(':scope > .col');
  let top = Infinity, bot = -Infinity;
  for (const el of (c ? [c, ...c.querySelectorAll('*')] : [])) {
    const b = el.getBoundingClientRect();
    if (b.width && b.height) { top = Math.min(top, b.top); bot = Math.max(bot, b.bottom); }
  }
  const h = (s.querySelector('h2') || s).textContent.trim().slice(0, 40);
  return [n + 1, s.id, h, top - r.top, r.bottom - bot, parseFloat(s.style.getPropertyValue('--fit') || 1)];
})"""


@pytest.mark.parametrize("i", range(len(OVERFLOW_CHARTS)), ids=OVERFLOW_IDS)
def test_no_card_overflows(i, chrome_page, tmp_path):
    """Every card's content ends inside its 430x830 box, above the Contents link and page number (the
    bottom 26px), and starts below the top edge. Area topic cards must also fit without the print shrink."""
    c = dict(OVERFLOW_CHARTS[i])
    args = [c.pop(k) for k in ("name", "dob", "tob", "tz", "lat", "lon")]
    html = diwali_report.render_diwali(diwali.compute_diwali(*args, **c))
    f = tmp_path / f"o{i}.html"
    f.write_text(html)
    chrome_page.goto(f"file://{f}")
    chrome_page.evaluate("document.fonts.ready")
    chrome_page.wait_for_timeout(300)
    edges = chrome_page.evaluate(_EDGES_JS)
    assert len(edges) == len(cards(html))
    bad = [(n, cid_, h, round(top), round(bot), fit) for n, cid_, h, top, bot, fit in edges if top < 8 or bot < 26]
    assert not bad, bad
    area_html = {k + 1 for k, cd in enumerate(cards(html)) if re.search(r'class="eyebrow">[^<]* · \d+ of \d+<', cd)}
    shrunk = [(n, h, fit) for n, _, h, _, _, fit in edges if n in area_html and fit < 1]
    assert not shrunk, shrunk
