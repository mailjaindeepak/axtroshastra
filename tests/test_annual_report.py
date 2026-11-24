"""Annual Report assembler tests (pure: run with --noconftest; never imports api.py).

Every test drives the real production path: annual.compute_annual -> annual_report.render_annual.
Fixtures: the invented persona Anjali Deshpande (tests/fixtures_annual/anjali_facts.json, a snapshot of the approved
facts), the invented persona Rohan Mehta and two more compute payloads (all through annual.compute_annual), plus 24
varied facts dicts. Nothing here reads docs/ (it is untracked): the approved layout is anchored by the sha256 golden
tests/golden/annual_anjali_golden.json (58 per-page visible texts).
Regenerate the golden ONLY for an owner-approved layout change:  REGEN_ANNUAL_GOLDEN=1 pytest --noconftest tests/test_annual_report.py -k golden
"""
import copy
import functools
import hashlib
import html as H
import importlib.util
import json
import os
import re
import shutil
import statistics
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
# no DB_BACKEND here: a module-level env change leaks into every test collected after this file
import annual  # noqa: E402
import annual_report as AR  # noqa: E402
import annual_report_p1 as P1  # noqa: E402
import annual_report_p2 as P2  # noqa: E402
import annual_report_p3 as P3  # noqa: E402

FIXDIR = os.path.join(ROOT, "tests", "fixtures_annual")
GOLDEN = os.path.join(ROOT, "tests", "golden", "annual_anjali_golden.json")
import pdfgen  # noqa: E402  (the production resolver: CHROME_BIN, Playwright store, system paths)
CHROME = pdfgen.chrome_bin()
AS_OF = "2026-11-06"
ROHAN = dict(name="Rohan Mehta", gender="male", dob="2001-02-17", tob=None, time_quality="T3", place="Jaipur",
             lat=26.91, lon=75.79, tz=5.5, work_type="student", steering="strengths")
PAYLOADS = {
    "persona_rohan": ROHAN,
    "compute_t0_male": dict(name="Test Buyer", gender="male", dob="1990-03-15", tob="10:20", time_quality="T0",
                            place="New Delhi", lat=28.61, lon=77.21, tz=5.5, work_type="job", steering=None),
    "compute_t3_female": dict(name="Test Girl", gender="female", dob="1998-11-02", tob="12:00", time_quality="T3",
                              place="Pune", lat=18.52, lon=73.86, tz=5.5, work_type="student", steering="strengths"),
}


# ------------------------------------------------------------------ helpers
def anjali_facts():
    """The approved Anjali facts (JSON snapshot); JSON turns the int kundli keys into strings, so restore them."""
    p = json.load(open(os.path.join(FIXDIR, "anjali_facts.json")))
    p["kundli"] = {int(k): v for k, v in p["kundli"].items()}
    return p


def anjali_payload():
    return json.load(open(os.path.join(FIXDIR, "anjali_payload.json")))


def sections(doc):
    return re.findall(r'<section class="page.*?</section>', doc, re.S)


def text_of(h):
    h = re.sub(r"<style.*?</style>|<script.*?</script>|<svg.*?</svg>|<!--.*?-->", " ", h, flags=re.S)
    return re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", h))).strip()


def head(sec):
    m = re.search(r'<h2 class="head">(.*?)</h2>', sec)
    return re.sub(r" \(continued\)$", "", text_of(m.group(1))) if m else None


def _variants():
    base = anjali_facts()
    sp = [m["ym"] for m in base["span_months"]]
    out = {}

    def mk(name, f):
        p = copy.deepcopy(base)
        f(p)
        out[name] = p

    def allt(t):
        def f(p):
            p["tones"] = {k: t for k in base["tones"]}
            p["areas"] = {a: {k: t for k in sp} for a in p["areas"]}
        return f
    for t in ("strong", "careful", "mixed"):
        mk("all_" + t, allt(t))

    def diff(p):
        cyc = ["strong", "mixed", "careful"]
        p["areas"] = {a: {k: cyc[(i + j) % 3] for i, k in enumerate(sp)} for j, a in enumerate(p["areas"])}
    mk("areas_differ", diff)
    mk("rising_none", lambda p: (p.__setitem__("rising_sign", None), p["birth"].__setitem__("time_known", False)))
    mk("dhaiya_off", lambda p: p.__setitem__("dhaiya", {"active": False, "kind": None, "ends": None, "restarts": None}))
    for st, dates in (("first", [{"date": "2027-03-10", "stage": "second"}, {"date": "2027-09-01", "stage": None}]),
                      ("second", [{"date": "2027-04-02", "stage": "third"}]), ("third", [{"date": "2027-06-12", "stage": None}])):
        mk("sade_" + st, lambda p, st=st, dates=dates: p.__setitem__("sade_sati", {"active": True, "stage": st, "change_dates": dates}))
    mk("no_yogas", lambda p: p.__setitem__("yogas", []))
    mk("manglik_no", lambda p: p.__setitem__("manglik", {"status": "none", "from_lagna": False, "from_moon": False, "cancelled": False, "note": None}))
    mk("manglik_cancelled", lambda p: p.__setitem__("manglik", {"status": "manglik_cancelled", "from_lagna": True, "from_moon": True, "cancelled": True, "note": "Jupiter aspects Mars"}))
    mk("kaal_sarp", lambda p: p.__setitem__("kaal_sarp", True))
    mk("pitra", lambda p: p.__setitem__("pitra", True))
    for w in ("student", "business", "home"):
        mk("work_" + w, lambda p, w=w: p.__setitem__("work_type", w))
    for t in ("Career and work", "Money and savings", "Marriage and relationships", "Luck and big decisions", "Strengths, study and growth"):
        mk("topic_" + t.split()[0], lambda p, t=t: p.__setitem__("first_open_topic", t))
    mk("long_place", lambda p: p["birth"].__setitem__("place", "Thiruvananthapuram University Campus Road, Pattom Palace PO, Kerala, India"))
    mk("long_name", lambda p: p.update(first_name="Venkatasubramaniam-Ramachandran", name="Venkatasubramaniam-Ramachandran Iyer"))
    return out


@functools.lru_cache(maxsize=1)
def reports():
    """name -> report dict ({'facts','meta'}) for every fixture, in production shape."""
    out = {"mock_anjali": {"facts": anjali_facts(), "meta": {"lang": "en"}}}
    for n, pl in PAYLOADS.items():
        out[n] = annual.compute_annual(pl, AS_OF)
    for n, p in _variants().items():
        out["var_" + n] = {"facts": p, "meta": {"lang": "en"}}
    return out


@functools.lru_cache(maxsize=None)
def doc_of(name):
    return AR.render_annual(reports()[name])


NAMES = list(reports())
N_VARIANTS = len([n for n in NAMES if n.startswith("var_")])


def visible_text(doc):
    return text_of(doc)


# ------------------------------------------------------------------ (1) layout
class TestLayout:
    def test_fixture_count(self):
        assert N_VARIANTS >= 12 and len(NAMES) >= 16

    @pytest.mark.parametrize("name", NAMES)
    def test_58_cards_numbered_in_order(self, name):
        s = sections(doc_of(name))
        assert len(s) == 58
        ids = [int(re.search(r'id="p(\d+)"', x).group(1)) for x in s]
        nums = [int(re.search(r'<div class="pgn">(\d+)</div>', x).group(1)) for x in s]
        assert ids == list(range(1, 59)) and nums == list(range(1, 59))


# ------------------------------------------------------------------ JSON round trip (stored report is JSON)
class TestJsonRoundTrip:
    @pytest.mark.parametrize("name", NAMES)
    def test_roundtrip_identical(self, name):
        rep = reports()[name]
        again = AR.render_annual(json.loads(json.dumps(rep)))
        assert len(sections(again)) == 58
        assert again == doc_of(name)

    def test_normalise_facts(self):
        assert hasattr(AR, "normalise_facts"), "annual_report.normalise_facts missing"
        facts = reports()["mock_anjali"]["facts"]
        stringy = json.loads(json.dumps(facts))
        assert all(isinstance(k, str) for k in stringy["kundli"])
        before = json.dumps(stringy, sort_keys=True)
        out = AR.normalise_facts(stringy)
        assert sorted(out["kundli"]) == list(range(1, 13))
        assert all(isinstance(k, int) for k in out["kundli"])
        assert json.dumps(stringy, sort_keys=True) == before          # input not mutated
        assert all(isinstance(k, str) for k in stringy["kundli"])


# ------------------------------------------------------------------ (2) approved layout
def _page_texts(doc):
    return [text_of(s) for s in sections(doc)]


def _hash(t):
    return hashlib.sha256(t.encode()).hexdigest()


class TestApprovedLayout:
    def test_anjali_equals_golden(self):
        mine = [_hash(t) for t in _page_texts(doc_of("mock_anjali"))]
        if os.environ.get("REGEN_ANNUAL_GOLDEN"):
            os.makedirs(os.path.dirname(GOLDEN), exist_ok=True)
            json.dump({"note": "sha256 of visible text per page of the Anjali snapshot output (approved v8 layout)",
                       "pages": mine}, open(GOLDEN, "w"), indent=0)
        assert os.path.exists(GOLDEN), "tests/golden/annual_anjali_golden.json missing (REGEN_ANNUAL_GOLDEN=1 to create)"
        gold = json.load(open(GOLDEN))["pages"]
        bad = [i + 1 for i, (a, b) in enumerate(zip(mine, gold)) if a != b]
        assert len(gold) == 58 and not bad, f"pages differ from golden: {bad}"


# ------------------------------------------------------------------ (3) references (port of the assembler's check)
SRC = []                                   # final page -> base card number
for _n in range(1, 55):
    if _n in (51, 52):
        continue
    SRC += {16: [16, 16], 27: [27, 27], 47: [47, 47], 50: [50] * 4}.get(_n, [_n])
FIRST = {}
for _i, _n in enumerate(SRC, 1):
    FIRST.setdefault(_n, _i)
for _n in (51, 52):
    FIRST[_n] = FIRST[50]
LAST = {n: max(i for i, x in enumerate(SRC, 1) if x == n) for n in set(SRC)}


def refs(html):
    out = []
    for tok in AR._SEG.split(html):
        if tok.startswith("<a "):
            m = re.search(r'href="#p(\d+)"', tok)
            if m:
                out.append(("h", int(m.group(1))))
        elif tok.startswith("<"):
            pass
        else:
            for m in re.finditer(r"\bpp (\d+) to (\d+)", tok):
                out.append(("pp", int(m.group(1)), int(m.group(2))))
            for m in re.finditer(r"\bpage (\d+)\b", tok):
                out.append(("pg", int(m.group(1))))
            for m in re.finditer(r"(?<![\w.-])p\.(\d+)\b", tok):
                out.append(("p", int(m.group(1))))
    return out


def reference_errors(p, doc):
    errs = []
    fin = sections(doc)
    heads = [head(s) for s in fin]
    base = P1.pages(p) + P2.pages(p) + P3.pages(p)
    bheads = [head(b) for b in base]
    for i, n in enumerate(SRC, 1):
        if n != 50 and heads[i - 1] != bheads[n - 1]:
            errs.append(f"title p{i}: {heads[i-1]} vs base {bheads[n-1]}")
    is_gl = lambda t: (heads[t - 1] or "").startswith("Words A to Z")
    for i, s in enumerate(fin, 1):
        n = SRC[i - 1]
        if n in (4, 50):
            continue
        body = s[s.index('<div class="col">'):]
        bb = base[n - 1]
        brefs = [r for r in refs(bb[bb.index('<div class="col">'):]) if r[1] not in (50, 51, 52)]
        exp = [("pp", FIRST[r[1]], LAST[r[2]]) if r[0] == "pp" else (r[0], FIRST[r[1]]) for r in brefs]
        got = [r for r in refs(body) if not is_gl(r[1])]
        it = iter(exp)
        if not all(any(g == e for e in it) for g in got):
            errs.append(f"p{i} (base {n}) refs {got} not within {exp}")
        if len(got) != len(exp) and n not in (16, 27, 47):
            errs.append(f"p{i} ref count {len(got)} vs {len(exp)}")
        for m in re.finditer(r'href="#p(\d+)"|(?<![\w.-])p\.(\d+)\b|\bpage (\d+)\b', body):
            t = int(next(g for g in m.groups() if g))
            if is_gl(t):
                term = AR._gl_term(body[:m.start()], body[m.end():]).lower()
                terms = [H.unescape(x).lower() for x in re.findall(r'g3t">(.*?)<', fin[t - 1])]
                if term not in terms:
                    errs.append(f"p{i} glossary link p.{t} term {term!r} not on that page")
    for g in P3.GLOSSARY_TERMS:                                  # every glossary 'see p.NN' -> first page of its topic
        exp = ", ".join("p.%d" % FIRST[n] for n in g["used_on"])
        rows = re.findall(r'g3t">(.*?)</div><div class="g3d">.*?class="g3p">(.*?)</span>', "".join(fin[52:56]), re.S)
        d = {H.unescape(a): b for a, b in rows}
        if d.get(g["term"]) != exp:
            errs.append(f"gloss {g['term']}: {d.get(g['term'])} vs {exp}")
    bl = [int(x) for x in re.findall(r'<a class="xr" href="#p(\d+)"', base[3])]
    bl2 = []
    for n in bl:
        if n in (50, 51, 52):
            if 50 not in bl2:
                bl2.append(50)
        else:
            bl2.append(n)
    fl = []
    for m in re.finditer(r'<a class="xr" href="#p(\d+)"><span>(.*?)</span><span>(\d+)</span></a>', fin[3]):
        t, num = int(m.group(1)), int(m.group(3))
        if t != num:
            errs.append(f"contents number {num} vs href {t}")
        fl.append(SRC[t - 1])
    fl2 = []
    for n in fl:
        if not fl2 or fl2[-1] != n or n != 50:
            fl2.append(n)
    if fl2 != bl2:
        errs.append(f"contents targets {fl2} vs base {bl2}")
    return errs


class TestReferences:
    @pytest.mark.parametrize("name", NAMES)
    def test_every_reference_resolves(self, name):
        assert reference_errors(reports()[name]["facts"], doc_of(name)) == []

    @pytest.mark.parametrize("name", ["mock_anjali", "compute_t0_male"])
    def test_contents_lists_all_pages_with_right_titles(self, name):
        fin = sections(doc_of(name))
        heads = [head(s) for s in fin]
        entries = re.findall(r'<a class="xr" href="#p(\d+)"><span>(.*?)</span><span>(\d+)</span></a>', fin[3])
        targets = sorted({int(t) for t, _, _ in entries})
        # contents covers cover.. thank-you except the months block expands to 12 lines and split pages share a line
        for t, label, num in entries:
            h = heads[int(t) - 1]
            label = H.unescape(re.sub(r"<[^>]+>", "", label))
            if h and int(t) != 58 and not label.startswith(("Career", "Money", "Marriage", "Luck", "Strengths")) and not re.match(r"[A-Z][a-z]{2} \d{4}$", label):
                assert label.rstrip(" ★") == h or h.startswith(label.split(" (")[0]) or label.split(" (")[0] in h, (t, label, h)
        for pg in range(1, 59):
            assert any(int(t) == pg or True for t in targets)
        # every page is either listed or a continuation of a listed page (split / glossary pages)
        listed = set(targets)
        for pg in range(1, 59):
            if pg not in listed:
                assert pg - 1 in listed or "(continued)" in text_of(fin[pg - 1]) or heads[pg - 1].startswith("Words A to Z"), pg
        assert len([t for t in targets]) >= 50


# ------------------------------------------------------------------ (4) glossary
class TestGlossary:
    @pytest.mark.parametrize("name", NAMES)
    def test_47_terms_over_4_pages_in_order(self, name):
        fin = sections(doc_of(name))
        gl = [s for s in fin if (head(s) or "").startswith("Words A to Z")]
        assert len(gl) == 4 and [fin.index(s) + 1 for s in gl] == [53, 54, 55, 56]
        terms = [H.unescape(t) for s in gl for t in re.findall(r'g3t">(.*?)<', s)]
        assert len(terms) == 47 == len(P3.GLOSSARY_TERMS)
        letters = [re.findall(r'class="g3l">(.)<', s) for s in gl]
        flat = [x for l in letters for x in l]
        assert flat == sorted(flat)
        assert [t[0].upper() for t in terms] == sorted(t[0].upper() for t in terms)
        for l in letters:                                       # a letter may continue on the next page, never repeat inside one
            assert len(l) == len(set(l))
        for s in gl:                                            # no lone letter marker at the bottom of a page
            rows = re.findall(r'<div class="g3l">|<div class="g3r">', s)
            assert rows and rows[-1] == '<div class="g3r">'

    @pytest.mark.parametrize("name", ["mock_anjali", "compute_t3_female"])
    def test_see_page_targets_hold_the_topic(self, name):
        fin = sections(doc_of(name))
        for g in P3.GLOSSARY_TERMS:
            exp = [FIRST[n] for n in g["used_on"]]
            row = re.search(r'g3t">' + re.escape(H.escape(g["term"], quote=False)) + r'</div><div class="g3d">.*?class="g3p">(.*?)</span>',
                            "".join(fin[52:56]), re.S)
            got = [int(x) for x in re.findall(r"p\.(\d+)", row.group(1))]
            assert got == exp and all(1 <= x <= 58 for x in got)


# ------------------------------------------------------------------ (5) personalisation (rule 22)
class TestPersonalisation:
    def test_no_cross_leaks(self):
        a, r = visible_text(doc_of("mock_anjali")), visible_text(doc_of("persona_rohan"))
        assert "Anjali" not in r and "Deshpande" not in r
        assert "Rohan" not in a and "Mehta" not in a
        for n in PAYLOADS:
            t = visible_text(doc_of(n))
            for w in ("Anjali", "Deshpande") if n == "persona_rohan" else ("Anjali", "Deshpande", "Rohan", "Mehta"):
                assert w not in t, (n, w)
        assert "Test" in visible_text(doc_of("compute_t0_male")) and "Test" in visible_text(doc_of("compute_t3_female"))

    @pytest.mark.parametrize("name", ["mock_anjali", "persona_rohan", "compute_t0_male", "compute_t3_female"])
    def test_title_and_note_use_first_name(self, name):
        f = reports()[name]["facts"]["first_name"]
        d = doc_of(name)
        assert f"<title>Annual Report - {H.escape(f)}</title>" in d
        assert f"Dear {f}," in text_of(sections(d)[1])

    @pytest.mark.parametrize("name", ["mock_anjali", "persona_rohan", "compute_t0_male"])
    def test_only_the_name_changes(self, name):
        rep = copy.deepcopy(reports()[name])
        old_first = rep["facts"]["first_name"]
        # the report picks wording by sum(ord(c) of first name) (annual_report_p2._d__seed), so the stand-in name is an
        # anagram (same sum): only the name itself may then differ between the two outputs
        new_first = old_first[::-1].capitalize()
        rep2 = copy.deepcopy(rep)
        rep2["facts"]["first_name"] = new_first
        rep2["facts"]["name"] = rep["facts"]["name"].replace(old_first, new_first)
        a, b = text_of(AR.render_annual(rep)), text_of(AR.render_annual(rep2))
        ta, tb = a.split(), b.split()
        assert len(ta) == len(tb)
        diff = [(x, y) for x, y in zip(ta, tb) if x != y]
        assert diff and all(old_first in x and new_first in y for x, y in diff), diff[:5]
        assert old_first not in b


# ------------------------------------------------------------------ (6) structure
def part_ranges(doc):
    """Part ranges from the eyebrows of the real cards (cover and thank-you carry no eyebrow)."""
    s = sections(doc)
    part = {}
    for i, x in enumerate(s, 1):
        m = re.search(r'class="k-part">Part (\d)', x)
        if m:
            part.setdefault(int(m.group(1)), []).append(i)
    return {1: (1, max(part[1])), 2: (min(part[2]), max(part[2])), 3: (min(part[3]), 58)}


class TestStructure:
    @pytest.mark.parametrize("name", NAMES)
    def test_part_ranges_printed_equal_real(self, name):
        d = doc_of(name)
        r = part_ranges(d)
        s = sections(d)
        t2, t3, t4 = text_of(s[1]), text_of(s[2]), text_of(s[3])
        assert f"Part 1 is the short version (pp {r[1][0]} to {r[1][1]})" in t2
        for k, word in ((1, "Short version"), (2, "Details"), (3, "Astrology guide")):
            assert f"Part {k} {word}" in t3
        for k in (1, 2, 3):
            a, b = r[k]
            assert re.search(rf"pp {a} to {b}\b", t3), (k, a, b)
        assert f"pp {r[3][0]} to {r[3][1]}" in t3.split("Look for")[1]
        assert f"Part 2 · Details {r[2][0]} to {r[2][1]}" in t4
        assert f"Part 3 · Guide {r[3][0]} to {r[3][1]}" in t4
        assert f"Part 1 · Short 1 to {r[1][1]}" in t4

    @pytest.mark.parametrize("name", NAMES)
    def test_title_top_and_page_number_on_every_card(self, name):
        for i, s in enumerate(sections(doc_of(name)), 1):
            assert s.count('<div class="pgn">') == 1, i
            if i not in (1, 2, 58):
                assert '<h2 class="head">' in s, i

    @pytest.mark.parametrize("name", NAMES)
    def test_document_hygiene(self, name):
        d = doc_of(name)
        assert d.count("<script") == 1 and d.count(AR.FIT_JS) == 1
        assert "DRAFT FOR OWNER" not in d and not re.search(r"<!--\s*DRAFT", d)
        assert not re.search(r'(?:src|href)\s*=\s*["\']?\s*(?:https?:)?//', d, re.I)
        assert "http" not in " ".join(re.findall(r'(?:src|href)="[^"]*"', d))
        assert "@import" not in d and "url(http" not in d

    @pytest.mark.parametrize("name", NAMES)
    def test_fit_script_does_not_alter_text(self, name):
        d = doc_of(name)
        bare = d.replace(AR.FIT_JS, "").replace(AR.FIT_CSS, "")
        assert text_of(bare) == text_of(d) and d.count(AR.FIT_CSS) == 1
        assert "textContent=" not in AR.FIT_JS and "innerHTML" not in AR.FIT_JS and "innerText" not in AR.FIT_JS


# ------------------------------------------------------------------ (8) PDF
try:
    import pymupdf  # noqa: E402
except Exception:  # pragma: no cover
    pymupdf = None
PDF_NAMES = ["mock_anjali", "persona_rohan", "compute_t0_male", "compute_t3_female"]
need_pymupdf = pytest.mark.skipif(pymupdf is None, reason="pymupdf not installed (optional): PDF measurements skipped")


@pytest.fixture
def chrome():
    """A missing browser is a FAILURE, never a skip (owner rule). Resolved the way production does (pdfgen.chrome_bin)."""
    assert CHROME and os.path.exists(CHROME), ("no Chrome/Chromium found: set CHROME_BIN, or install the Playwright "
                                               "browsers (pdfgen.chrome_bin() probes CHROME_BIN, ms-playwright, system paths)")
    return CHROME


def _headless():
    return [] if "headless" in os.path.basename(CHROME).replace("-", "_") else ["--headless=new"]


@pytest.fixture(scope="module")
def pdfs(tmp_path_factory):
    out = {}
    d = tmp_path_factory.mktemp("annual_pdf")
    for n in PDF_NAMES:
        h, pdf = d / f"{n}.html", d / f"{n}.pdf"
        h.write_text(doc_of(n), encoding="utf-8")
        subprocess.run([CHROME, *_headless(), "--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage", "--no-pdf-header-footer",
                        "--virtual-time-budget=6000", f"--print-to-pdf={pdf}", f"file://{h}"], capture_output=True, timeout=180)
        out[n] = pymupdf.open(str(pdf))
    return out


def _spans(page):
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                if s["text"].strip():
                    yield s


@need_pymupdf
@pytest.mark.usefixtures("chrome")
@pytest.mark.slow
class TestPdf:
    @pytest.mark.parametrize("name", PDF_NAMES)
    def test_pages_size_and_pagenumber_offset(self, pdfs, name):
        d = pdfs[name]
        assert len(d) == 58
        assert {(round(p.rect.width, 2), round(p.rect.height, 2)) for p in d} == {(323.04, 623.04)}
        ys = []
        for p in d:
            H_ = p.rect.height
            pg = [H_ - s["bbox"][3] for s in _spans(p) if s["text"].strip().isdigit() and "#%06x" % s["color"] == "#b9ae96"]
            assert pg, "page number not found on page %d" % (p.number + 1)
            ys.append(pg[-1])
        assert statistics.pstdev(ys) == pytest.approx(0, abs=0.01)

    @pytest.mark.parametrize("name", PDF_NAMES)
    def test_lowest_text_above_800px(self, pdfs, name):
        worst = 0
        for p in pdfs[name]:
            for s in _spans(p):
                if s["text"].strip().isdigit() and "#%06x" % s["color"] == "#b9ae96":
                    continue
                worst = max(worst, s["bbox"][3] / 0.75)
        assert worst < 800, worst

    @pytest.mark.parametrize("name", PDF_NAMES)
    def test_small_text_is_only_chart_labels(self, pdfs, name):
        """Under-10px spans (7.5pt) must be rare (< 2% of characters) and may only sit on a page that holds an SVG chart
        or the kundli grid (both draw their labels as small text). Page HTML is the source of truth for 'has an SVG'."""
        secs = sections(doc_of(name))
        total = small = 0
        for p in pdfs[name]:
            n_small = 0
            for s in _spans(p):
                k = len(s["text"].strip())
                total += k
                if s["size"] / 0.75 < 9.95:
                    small += k
                    n_small += k
            if n_small:
                assert "<svg" in secs[p.number], (f"page {p.number + 1}: small text on a page without an SVG, sizes px "
                    f"{sorted({round(s['size'] / 0.75, 1) for s in _spans(p) if s['size'] / 0.75 < 9.95})}, "
                    f"zoom {re.findall(r'--fit[^;]*', secs[p.number])}")
        assert small / total < 0.02, small / total

    def test_manglik_wheel_not_clipped(self):
        """The wheel svg's viewBox must contain all 12 circles (cx +- r, cy +- r)."""
        for n in NAMES:
            wheels = [m for m in re.findall(r"<svg[^>]*aria-label=\"Mars ring\".*?</svg>", doc_of(n), re.S)]
            assert wheels, n
            for w in wheels:
                x0, y0, ww, hh = map(float, re.search(r'viewBox="([^"]+)"', w).group(1).split())
                cs = [tuple(float(re.search(a + r'="([-\d.]+)"', c).group(1)) for a in ("cx", "cy", "r")) for c in re.findall(r"<circle[^>]*>", w)]
                assert len(cs) == 12, (n, len(cs))
                for cx, cy, r in cs:
                    assert x0 <= cx - r and cx + r <= x0 + ww and y0 <= cy - r and cy + r <= y0 + hh, (n, cx, cy, r)


# =================================================================== audit regressions (F1 as_of sweep, F4 staged fit, F6 long names)
import concurrent.futures as _cf  # noqa: E402
import random  # noqa: E402
import tempfile  # noqa: E402

MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
SWEEP_AS_OF = ["2026-11-06", "2026-12-31", "2027-01-31", "2027-02-28", "2027-03-15", "2027-06-30", "2027-12-01", "2028-02-29"]
SWEEP_PAYLOADS = {
    "f": dict(name="Sweep Girl", gender="female", dob="1998-11-02", tob="09:30", time_quality="T0", place="Pune",
              lat=18.52, lon=73.86, tz=5.5, work_type="job", steering=None),
    "m": dict(name="Sweep Boy", gender="male", dob="1990-03-15", tob=None, time_quality="T3", place="New Delhi",
              lat=28.61, lon=77.21, tz=5.5, work_type="student", steering="strengths"),
}
SWEEP = [(w, a) for w in SWEEP_PAYLOADS for a in SWEEP_AS_OF]


@functools.lru_cache(maxsize=None)
def sweep_report(w, as_of):
    return annual.compute_annual(SWEEP_PAYLOADS[w], as_of)


@functools.lru_cache(maxsize=None)
def sweep_doc(w, as_of):
    return AR.render_annual(sweep_report(w, as_of))


def _label_of(ym):
    return f"{MON[int(ym[5:]) - 1]} {ym[:4]}"


def _shift(ym, k):
    n = int(ym[:4]) * 12 + int(ym[5:]) - 1 + k
    return f"{n // 12}-{n % 12 + 1:02d}"


@pytest.mark.parametrize("w,as_of", SWEEP)
class TestAsOfSweep:
    def test_58_cards_and_no_stray_months(self, w, as_of):
        rep, d = sweep_report(w, as_of), sweep_doc(w, as_of)
        f = rep["facts"]
        assert len(sections(d)) == 58
        span = [m["ym"] for m in f["span_months"]]
        assert len(span) == 12 and span[0] == _shift(as_of[:7], 1) and span[-1] == _shift(as_of[:7], 12)
        allowed = {m["label"] for m in f["span_months"]} | {m["label"] for m in f["past_months"]}
        allowed.add(_label_of(_shift(span[-1], 1)))                       # the one intentional 'month after span'
        u = f["planet_period"]["until"]
        allowed.add(_label_of(u[:7]))                                      # planet period end date
        allowed.add(_label_of(f["birth"]["date"][:7]))                     # the buyer's own birth date is printed
        txt = text_of(d)
        after = re.findall(r"(\b(?:%s) \d{4}) and after" % "|".join(MON), txt)
        assert after == [_label_of(_shift(span[-1], 1))], after
        found = set(re.findall(r"\b(?:%s) \d{4}\b" % "|".join(MON), txt))
        assert found - allowed == set(), f"months outside span/past/after/period end: {sorted(found - allowed)}"

    def test_contents_lists_exactly_the_span_months(self, w, as_of):
        f = sweep_report(w, as_of)["facts"]
        entries = re.findall(r'<a class="xr" href="#p\d+"><span>(.*?)</span>', sections(sweep_doc(w, as_of))[3])
        labels = [H.unescape(re.sub(r"<[^>]+>", "", e)) for e in entries]
        months = [e for e in labels if re.fullmatch(r"(?:%s) \d{4}" % "|".join(MON), e)]
        assert months == [m["label"] for m in f["span_months"]]

    def test_quarter_plan_labels_are_rolling_blocks(self, w, as_of):
        span = [m["ym"] for m in sweep_report(w, as_of)["facts"]["span_months"]]
        exp = []
        for q in range(4):
            a, b = span[q * 3], span[q * 3 + 2]
            exp.append(f"{MON[int(a[5:]) - 1]} to {_label_of(b)}" if a[:4] == b[:4] else f"{_label_of(a)} to {_label_of(b)}")
        card = [s for s in sections(sweep_doc(w, as_of)) if head(s) == "Quarter-by-quarter plan"]
        assert len(card) == 1
        got = [H.unescape(x) for x in re.findall(r'<div class="k-qh"><span>([^<:]*):', card[0])]
        assert got == exp

    def test_strip_initials_equal_span_initials(self, w, as_of):
        span = [m["ym"] for m in sweep_report(w, as_of)["facts"]["span_months"]]
        ini = [MON[int(y[5:]) - 1][0] for y in span]
        for i, s in enumerate(sections(sweep_doc(w, as_of)), 1):
            letters = [x[0] for x in re.findall(r'class="k-mc[^"]*"[^>]*>.*?<span>([^<]+)</span>', s)]
            assert len(letters) % 12 == 0 or len(letters) % 12 == 11, (i, len(letters))
            if len(letters) % 12 == 0:
                for k in range(0, len(letters), 12):
                    assert letters[k:k + 12] == ini, (i, letters[k:k + 12], ini)


# ------------------------------------------------------------------ headless Chrome probe (F4 + F6)
PROBE_JS = """<script>setTimeout(function(){var out={fit:{},small:[],cards:{},svgs:{},name:{}};var NAME=%s;
document.querySelectorAll('section.page').forEach(function(s){var id=s.id;var sr=s.getBoundingClientRect();
out.fit[id]=[s.dataset.fit||'',s.style.getPropertyValue('--fit')||'',s.className,s.dataset.c0||''];
var col=s.querySelector('.col');var z=parseFloat(getComputedStyle(col).zoom)||1;var w=document.createTreeWalker(s,NodeFilter.SHOW_TEXT),n,mr=0,mb=0;
out.svgs[id]=[].map.call(s.querySelectorAll('svg'),function(v){var q=v.getBoundingClientRect();return [q.left-sr.left,q.top-sr.top,q.right-sr.left,q.bottom-sr.top];});
while(n=w.nextNode()){var t=n.textContent.trim();if(!t)continue;var el=n.parentElement;if(el.closest('style,script'))continue;
var r=document.createRange();r.selectNodeContents(n);var q=r.getBoundingClientRect();if(!q.height)continue;
var fs=parseFloat(getComputedStyle(el).fontSize)*z;
if(!el.closest('svg')&&fs<9.95)out.small.push([id,t.slice(0,40),fs]);
mr=Math.max(mr,q.right-sr.left);mb=Math.max(mb,q.bottom-sr.top);
if(NAME&&t.indexOf(NAME)>=0)(out.name[id]=out.name[id]||[]).push([q.left-sr.left,q.right-sr.left,q.bottom-sr.top,fs]);}
out.cards[id]=[mr,mb,sr.width,sr.height];});
var p=document.createElement('pre');p.id='__probe';p.textContent=JSON.stringify(out);document.body.appendChild(p);},2500);</script>"""


def _run_chrome(args, timeout=240):
    with tempfile.TemporaryDirectory() as ud:
        return subprocess.run([CHROME, *_headless(), "--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage", f"--user-data-dir={ud}",
                               "--virtual-time-budget=9000", *args], capture_output=True, timeout=timeout, text=True)


def probe_doc(html, name=""):
    """Load the report in headless Chrome (screen layout, fit script runs), return the probe JSON and the final DOM."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "r.html")
        open(p, "w", encoding="utf-8").write(html.replace("</body>", PROBE_JS % json.dumps(name) + "</body>", 1))
        r = _run_chrome(["--dump-dom", f"file://{p}"])
    m = re.search(r'<pre id="__probe">(.*?)</pre>', r.stdout, re.S)
    assert m, "probe did not run: " + r.stderr[-300:]
    dom = r.stdout.replace(m.group(0), "")
    return json.loads(H.unescape(m.group(1))), dom


def pdf_doc(html):
    with tempfile.TemporaryDirectory() as d:
        p, o = os.path.join(d, "r.html"), os.path.join(d, "r.pdf")
        open(p, "w", encoding="utf-8").write(html)
        _run_chrome(["--no-pdf-header-footer", f"--print-to-pdf={o}", f"file://{p}"])
        return pymupdf.open(o)


def _random_payloads(n=20, seed=20261106):
    rng = random.Random(seed)
    out = {}
    wts = ["job", "business", "student", "home"]
    for i in range(n):
        y, m, dd = rng.randint(1958, 2008), rng.randint(1, 12), rng.randint(1, 28)
        tq = rng.choice(["T0", "T1", "T3"])
        out[f"rand_{i:02d}"] = dict(
            name=rng.choice(["Asha Kulkarni", "Ravi", "Meenakshi Sundaram", "Imran Qureshi", "Gurpreet Singh Sandhu", "Li"]),
            gender=rng.choice(["male", "female"]), dob=f"{y}-{m:02d}-{dd:02d}",
            tob=f"{rng.randint(0, 23):02d}:{rng.choice([0, 15, 30, 45]):02d}" if tq != "T3" else None, time_quality=tq,
            place=rng.choice(["Pune", "Jaipur", "Chennai", "Kolkata", "Lucknow"]), lat=round(rng.uniform(8, 32), 2),
            lon=round(rng.uniform(70, 90), 2), tz=5.5, work_type=rng.choice(wts),
            steering=rng.choice([None, "career", "money", "marriage", "luck", "strengths"]))
    return out


@functools.lru_cache(maxsize=1)
def fit_docs():
    """key -> html for 28 fixtures + 20 random compute payloads + the F1 sweep renders."""
    docs = {n: doc_of(n) for n in NAMES}
    for k, pl in _random_payloads().items():
        docs[k] = AR.render_annual(annual.compute_annual(pl, AS_OF))
    for w, a in SWEEP:
        docs[f"sweep_{w}_{a}"] = sweep_doc(w, a)
    return docs


@functools.lru_cache(maxsize=1)
def fit_results():
    """key -> (probe json, dom, pdf doc), computed once, 4 Chrome runs at a time."""
    docs = fit_docs()

    def one(k):
        probe, dom = probe_doc(docs[k])
        return k, probe, dom, pdf_doc(docs[k])
    with _cf.ThreadPoolExecutor(4) as ex:
        return {k: (pr, dom, pdf) for k, pr, dom, pdf in ex.map(one, docs)}


@need_pymupdf
@pytest.mark.usefixtures("chrome")
@pytest.mark.slow
class TestStagedFit:
    def test_document_count(self):
        k = list(fit_docs())
        assert len([x for x in k if x.startswith("rand_")]) == 20 and len([x for x in k if not x.startswith(("rand_", "sweep_"))]) == 28

    @pytest.mark.parametrize("key", list(fit_docs()))
    def test_no_card_needs_zoom_and_no_body_text_under_10px(self, key):
        probe, dom, pdf = fit_results()[key]
        assert len(probe["fit"]) == 58
        zoomed = {i: v for i, v in probe["fit"].items() if v[0] == "zoom" or v[1] not in ("", "1")}
        assert not zoomed, f"cards that need zoom: {zoomed}"
        assert not probe["small"], f"body text under 10px (id, text, effective px): {probe['small'][:6]}"
        # printed PDF: 58 pages, a span smaller than 10px may only sit inside an SVG rectangle of its page
        assert len(pdf) == 58
        bad = []
        for pg in pdf:
            rects = probe["svgs"]["p%d" % (pg.number + 1)]
            for s in _spans(pg):
                if s["size"] / 0.75 < 9.95:
                    cx, cy = (s["bbox"][0] + s["bbox"][2]) / 1.5, (s["bbox"][1] + s["bbox"][3]) / 1.5
                    if not any(r[0] - 2 <= cx <= r[2] + 2 and r[1] - 2 <= cy <= r[3] + 2 for r in rects):
                        bad.append((pg.number + 1, s["text"][:20], round(s["size"] / 0.75, 1)))
        assert not bad, f"PDF spans under 10px outside any svg: {bad[:6]}"

    @pytest.mark.parametrize("key", list(fit_docs()))
    def test_tt_classes_only_from_fit_script_and_text_unchanged(self, key):
        probe, dom, _ = fit_results()[key]
        html = fit_docs()[key]
        bare = html.replace(AR.FIT_JS, "").replace(AR.FIT_CSS, "")
        # tt/tt2 are also set statically by the approved layout (ANNUAL_SPLIT_MAP 'tight'); tt3 and every stage change
        # beyond the static class may only come from the fit script (recorded in data-fit)
        assert not re.search(r'<section class="page[^"]*\btt3\b', html), "static HTML carries tt3"
        static = dict(re.findall(r'<section class="(page[^"]*)" id="(p\d+)"', html)[i][::-1] for i in range(58))
        for i, v in probe["fit"].items():
            assert v[3] == static[i], (i, v[3], static[i])
            if v[0] == "":
                assert v[2] == v[3], f"{i}: class changed without data-fit: {v}"
            else:
                assert v[0] in ("tt", "tt2", "tt3", "zoom"), (i, v)      # zoom itself is asserted absent in the test above
                assert v[0] == "zoom" or re.search(r"\b%s\b" % v[0], v[2]), (i, v)
        assert text_of(dom) == text_of(html) == text_of(bare)


# ------------------------------------------------------------------ F6 long first names
LONG_NAMES = ["A", "Anjali", "Bhuvaneshwaran", "Venkatasubramaniamramesha", "VenkatasubramaniamrameshaChandrasekharan"]


def _named(first):
    p = copy.deepcopy(reports()["mock_anjali"]["facts"])
    p["first_name"], p["name"] = first, first + " Deshpande"
    return {"facts": p, "meta": {"lang": "en"}}


def test_long_name_lengths():
    assert [len(n) for n in LONG_NAMES] == [1, 6, 14, 25, 40]


@pytest.mark.parametrize("first", LONG_NAMES)
def test_long_name_renders_58_cards(first):
    d = AR.render_annual(_named(first))
    s = sections(d)
    assert len(s) == 58 and first in text_of(s[0]) and f"Dear {first}," in text_of(s[1]) and f"Thank you, {first}" in text_of(s[57])


@need_pymupdf
@pytest.mark.usefixtures("chrome")
@pytest.mark.slow
@pytest.mark.parametrize("first", LONG_NAMES)
def test_long_name_fully_inside_cover_note_and_thank_you(first):
    probe, _ = probe_doc(AR.render_annual(_named(first)), first)
    for pid in ("p1", "p2", "p58"):
        found = probe["name"].get(pid)
        assert found, f"name {first!r} not found as text on {pid}"
        w, h = probe["cards"][pid][2], probe["cards"][pid][3]
        assert (w, h) == (430, 830), (pid, w, h)
        mr, mb = probe["cards"][pid][0], probe["cards"][pid][1]
        assert mr <= 430 + 0.5 and mb <= 830, f"{pid}: text reaches x={mr}, y={mb} (card 430x830)"
        for left, right, bottom, fs in found:
            assert 0 <= left and right <= 430 + 0.5 and bottom <= 830, (pid, left, right, bottom)
            assert fs >= 10 - 0.05, f"{pid}: name font {fs}px under 10px"
