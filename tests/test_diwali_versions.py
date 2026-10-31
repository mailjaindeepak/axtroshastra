"""PRODUCT: every version a buyer can get, engine -> bank -> render, NO AI (bank only).

28 real, different charts (born 1950-2008, cities across India) cover every option of every input at
least once (spec §3/§11): steering 6 + skipped, work type 4, gender 2, birth time T0-T3, age band 4,
gift off / on with name+message / on empty. Pure: no DB, no api.py, no network. Run with --noconftest.
Chrome checks (PDF size/pages/links, overflow) are marked slow and FAIL (never skip) without Chrome/Playwright.

    python3 -m pytest tests/test_diwali_versions.py -q -p no:cacheprovider --noconftest
    python3 tests/test_diwali_versions.py --report     # prints the per-version table + saves page shots
"""
import functools
import html as H
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from html.parser import HTMLParser

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import diwali  # noqa: E402
import diwali_bank  # noqa: E402
import diwali_report  # noqa: E402
from test_diwali_pipeline import _EDGES_JS, MONTH_PAGES, cards, cid, visible  # noqa: E402
import pdfgen  # noqa: E402

CHROME = pdfgen.chrome_bin()   # same lookup the product uses; '' when absent -> slow tests FAIL, never skip


def _need_chrome():
    assert CHROME, "no Chrome found by pdfgen.chrome_bin(); set CHROME_BIN or install Playwright chromium (slow tests must not skip)"

STEER = ["money", "career", "business", "family", "marriage", "luck", None]
WORK = ["job", "business", "student", "home"]
TIMES = ["T0", "T1", "T2", "T3"]
BANDS = ["u25", "25_40", "40_60", "60p"]
GIFTS = ["off", "named", "empty"]
YEAR = {"u25": [2008, 2004, 2002, 2006, 2003, 2005, 2007], "25_40": [1995, 1989, 1999, 1992, 1987, 1997, 2000],
        "40_60": [1979, 1970, 1984, 1975, 1968, 1982, 1972], "60p": [1950, 1958, 1963, 1955, 1961, 1952, 1965]}
CITIES = [("Delhi", 28.6139, 77.2090), ("Mumbai", 19.0760, 72.8777), ("Bengaluru", 12.9716, 77.5946),
          ("Chennai", 13.0827, 80.2707), ("Kolkata", 22.5726, 88.3639), ("Hyderabad", 17.3850, 78.4867),
          ("Ahmedabad", 23.0225, 72.5714), ("Jaipur", 26.9124, 75.7873), ("Lucknow", 26.8467, 80.9462),
          ("Patna", 25.5941, 85.1376), ("Bhopal", 23.2599, 77.4126), ("Kochi", 9.9312, 76.2673),
          ("Guwahati", 26.1445, 91.7362), ("Chandigarh", 30.7333, 76.7794), ("Bhubaneswar", 20.2961, 85.8245),
          ("Indore", 22.7196, 75.8577), ("Nagpur", 21.1458, 79.0882), ("Surat", 21.1702, 72.8311),
          ("Coimbatore", 11.0168, 76.9558), ("Varanasi", 25.3176, 82.9739), ("Amritsar", 31.6340, 74.8723),
          ("Thiruvananthapuram", 8.5241, 76.9366), ("Ranchi", 23.3441, 85.3096), ("Dehradun", 30.3165, 78.0322),
          ("Mangaluru", 12.9141, 74.8560), ("Visakhapatnam", 17.6868, 83.2185), ("Raipur", 21.2514, 81.6296),
          ("Srinagar", 34.0837, 74.7973)]
MALE = ["Aarav Menon", "Chirag Bansal", "Eshan Ghosh", "Gaurav Saxena", "Indrajit Sen", "Kunal Chawla",
        "Manohar Patil", "Omkar Deshpande", "Qasim Ansari", "Siddharth Hegde", "Udayan Das", "Waseem Khan",
        "Zubin Mistry", "Anirudh Shetty", "Balwinder Gill", "Tejas Pandya"]
FEMALE = ["Bhavna Kapoor", "Deepika Nair", "Falguni Desai", "Harini Subramaniam", "Jyotsna Reddy",
          "Lavanya Pillai", "Nandini Bhatt", "Pallavi Mishra", "Ritika Agarwal", "Tanvi Kulkarni",
          "Yamini Thakur", "Charulata Mukherjee", "Sunanda Barua", "Gulnaz Mirza", "Vaidehi Joglekar",
          "Oindrila Basu"]
GIVERS = ["Neel", "Mausi", "Kabir", "Didi", "Arnav", "Papa", "Simran", "Chotu", "Rehana", "Bhaiya"]
MESSAGES = ["For your new start. Light every lamp, beta.", "Happy Diwali! Read slowly, plan well.",
            "With love from all of us at home.", "May the months ahead be kind to you.",
            "Shubh Deepavali. Keep this for the whole year ahead."]


def _matrix():
    """28 rows: steering x work type are fully crossed (lcm 7*4); the other inputs rotate so every option
    of every input appears several times and pairs with many different steering/work choices."""
    rows, mi, fi = [], 0, 0
    for i in range(28):
        g = "female" if (i + i // 4) % 2 else "male"
        band = BANDS[(i + i // 7) % 4]
        y = YEAR[band][i % 7]
        mo, d = 1 + (i * 5) % 12, 1 + (i * 11) % 28
        tob = f"{(3 + i * 7) % 24:02d}:{(i * 13) % 60:02d}"
        if g == "male":
            name, mi = MALE[mi], mi + 1
        else:
            name, fi = FEMALE[fi], fi + 1
        city, lat, lon = CITIES[i]
        gift = GIFTS[(i + i // 3) % 3]
        r = dict(name=name, dob=f"{y}-{mo:02d}-{d:02d}", tob=tob, tz=5.5, lat=lat, lon=lon, place=city,
                 gender=g, work_type=WORK[i % 4], steering=STEER[i % 7], time_quality=TIMES[(i + i // 4) % 4])
        if gift != "off":
            r.update(gift_on=True, giver_name=GIVERS[i % 10] if gift == "named" else "",
                     gift_message=MESSAGES[i % 5] if gift == "named" else "")
        rows.append(r)
    return rows


VERSIONS = _matrix()
VIDS = [f"v{i + 1:02d}-{r['name'].split()[0]}" for i, r in enumerate(VERSIONS)]
FIRST_NAMES = {r["name"].split()[0] for r in VERSIONS}
# 5-buyer test, strict form: identical inputs (job, picked Money, male, exact time, self, age 25-40),
# only the chart differs, so any shared paragraph is the bank failing to personalise.
FIVE_SAME = [dict(name=n, dob=dob, tob=t, tz=5.5, lat=la, lon=lo, place=c, gender="male", work_type="job",
                  steering="money", time_quality="T0")
             for n, dob, t, (c, la, lo) in zip(["Aarav Menon", "Chirag Bansal", "Eshan Ghosh", "Gaurav Saxena",
                                                  "Kunal Chawla"],
                                                 ["1990-03-04", "1993-07-19", "1988-11-27", "1996-01-09", "1991-05-30"],
                                                 ["06:15", "13:40", "22:05", "09:50", "17:25"], CITIES[:5])]
FIVE_MIXED = [0, 6, 11, 17, 23]          # 5 varied matrix versions (different steering/work/time/age/gift)


def _args(row):
    c = dict(row)
    return [c.pop(k) for k in ("name", "dob", "tob", "tz", "lat", "lon")], c


@functools.lru_cache(maxsize=None)
def build_row(key):
    a, kw = _args(dict(json.loads(key)))
    p = diwali.compute_diwali(*a, **kw)
    assert not p.get("narrative")
    return p, diwali_report.render_diwali(p)


def build(i):
    return build_row(json.dumps(VERSIONS[i], sort_keys=True))


def card_by_id(html, want):
    return next((c for c in cards(html) if cid(c) == want), "")


# ---- paragraphs: block elements split, inline tags kept --------------------------------------------
_BLOCK = {"p", "div", "td", "th", "li", "h1", "h2", "h3", "h4", "tr", "table", "section", "br"}


class _Paras(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.buf, self.skip = [], [], 0

    def flush(self):
        t = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        if t:
            self.out.append(t)
        self.buf = []

    def handle_starttag(self, tag, a):
        if tag in ("svg", "style", "script", "defs"):
            self.skip += 1
        if tag in _BLOCK:
            self.flush()
        elif tag in ("span", "b"):
            self.buf.append(" ")

    def handle_endtag(self, tag):
        if tag in ("svg", "style", "script", "defs"):
            self.skip -= 1
        if tag in _BLOCK:
            self.flush()
        elif tag in ("span", "b"):
            self.buf.append(" ")

    def handle_data(self, d):
        if not self.skip:
            self.buf.append(d)


def paragraphs(fragment):
    p = _Paras()
    p.feed(fragment)
    p.flush()
    return p.out


# cards whose words are the same for every buyer by design (spec §2 rule 1: chart-independent pages)
FIXED_CARDS = {"s-0-1", "s-0-3", "s-0-4", "contents", "part-1", "part-2", "s-2-1", "s-2-2", "b-1", "b-2", "b-3",
               "b-4", "b-5", "b-6", "b-7", ""}
_SRC = "".join(open(os.path.join(ROOT, f)).read() for f in ("diwali_report.py", "diwali_report_back.py"))
_MON = r"(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"


def _norm(t, first):
    t = t.replace(first, "NAME")
    t = re.sub(r"\b" + _MON + r"\b", "M", t)
    return re.sub(r"\d+", "#", t).lower()


def _chrome_literal(t):
    """Words the renderer writes itself (labels, legends, f-string leads): every sentence starts or ends
    with 25+ characters found verbatim in diwali_report*.py. Fixed questions (spec §6a) also count."""
    if t.rstrip().endswith("?") or t.startswith("When:") or not re.search(r"[.!]\W*$", t):
        return True                                   # fixed questions, timing pointers, titles/labels
    if diwali_bank.DEFAULT_GIFT_MESSAGE in t:
        return True
    t = re.sub(r"^([A-Z]{2,}(?: [A-Z]{2,})* )", "", t)        # legend tag, e.g. "GOOD TIME Good or steady…"
    for s in re.split(r"(?<=[.!?])\s+", re.sub(r"^(Do|Watch|Why|When|Your step|The habit|Why these):\s*", "", t)):
        s = s.strip()
        if len(s) < 25:
            continue
        if not any(x in _SRC or H.escape(x, quote=False) in _SRC for x in (s[:25], s[-25:])):
            return False
    return True


def chart_paragraphs(html, first, min_words=8):
    """Normalised paragraphs from the chart-derived cards (continuation cards inherit the previous id)."""
    out, cur = [], ""
    for c in cards(html):
        cur = cid(c) or cur
        if cur in FIXED_CARDS:
            continue
        for t in paragraphs(c):
            if len(t.split()) >= min_words and not _chrome_literal(t):
                out.append((cur, t, _norm(t, first)))
    return out


# ---- per-version checks: each returns a list of problems (empty = pass) -----------------------------
def chk_cards(p, html):
    cs = cards(html)
    bad = []
    if not (html.startswith("<!DOCTYPE html>") and html.rstrip().endswith("</html>")):
        bad.append("not a complete doc")
    if "@@" in html:
        bad.append("unreplaced @@ page ref")
    v = visible(html)
    for s in ("None", "{", "}", "nan", "undefined"):
        if re.search(r"(?<![A-Za-z])" + re.escape(s) + r"(?![A-Za-z])", v):
            bad.append(f"stray {s!r} in visible text")
    bad += [f"one-month range printed as {a}–{a}" for a in sorted(set(re.findall(r"\b([A-Z][a-z]{2})–\1\b", v)))]
    if not 55 <= len(cs) <= 64:
        bad.append(f"{len(cs)} cards")
    return bad


def chk_links(p, html):
    """Every href lands on an id; every 'p.N' next to a link is the card that holds that id."""
    cs = cards(html)
    where = {}
    for k, c in enumerate(cs, 1):
        for i in re.findall(r'\bid="([^"]+)"', c):
            where.setdefault(i, k)
    ids = set(re.findall(r'\bid="([^"]+)"', html))                  # svg <use href="#i-..."> lives in the defs
    bad = [f"href #{h} has no target" for h in sorted(set(re.findall(r'href="#([^"]+)"', html)) - ids)]
    for c in cs:
        for ref, txt in re.findall(r'<a [^>]*href="#([^"]+)"[^>]*>(.*?)</a>', c, flags=re.S):
            m = re.search(r"p\.(\d+)", txt)
            if m and ref in where and int(m.group(1)) != where[ref]:
                bad.append(f"link to #{ref} says p.{m.group(1)}, card is p.{where[ref]}")
    return bad


def chk_lint(p, html):
    """diwali_bank.lint_text on every visible sentence; dates allowed only on the date pages (O-30)."""
    span = p["meta"]["span"]
    cs = cards(html)
    after = {cs.index(c) + 1 for c in cs if cid(c) == "s-1-months"}
    bad, cur = [], ""
    gm = p["meta"]["gift"].get("message") if p["meta"]["gift"]["on"] else ""
    for n, c in enumerate(cs):
        cur = cid(c) or cur
        dates = cid(c) in MONTH_PAGES or n in after or "Your Wrapped card" in c
        for v in paragraphs(c):                                       # per block, so a signature never runs into the next line
            v = re.sub(r"Diwali 20\d\d", "Diwali", v.replace(f"({span})", "").replace(span, ""))
            if cid(c) == "b-3":
                v = re.sub(r"\b(1st|2nd|3rd|[4-9]th|1[0-2]th)\b", "", v)
            if gm and gm in v:                                        # the giver's own typed words are not our copy
                continue
            for s in re.split(r"(?<=[.!?])\s+", v):
                for pr in diwali_bank.lint_text(s, allow_dates=dates):
                    bad.append(f"p.{n + 1} {cur}: {pr}: {s[:90]}")
    return bad


LEAKS = ["vyapar", "business growth", "rohit", "rajesh menon", "vikram", "priya", "astrosage", "pune-"]


def chk_leak(p, html):
    v = visible(html)
    low = v.lower()
    first = p["meta"]["first_name"]
    bad = [f"leak {w!r}" for w in LEAKS if w in low and w not in p["meta"]["name"].lower()]
    bad += [f"other buyer's name {n!r}" for n in FIRST_NAMES - {first} if re.search(rf"\b{n}\b", v)]
    if first not in v:
        bad.append("own first name missing")
    return bad


def expected_order(work, steer, scores):
    """Spec §5 'Area order', written independently of diwali.area_order."""
    sit = list(diwali.SITUATION_ORDER[work])
    order = [steer] + [a for a in sit if a != steer] if steer in diwali.AREAS else sit
    for i in range(1, 4):                       # rule B: one pass from the top, 1st place pinned
        if scores[order[i + 1]] - scores[order[i]] >= 2:
            order[i], order[i + 1] = order[i + 1], order[i]
    return order


def expected_scores(p, any_month=False):
    """Rule B signals, recomputed from payload facts: period lords rule/sit in the area houses; Jupiter
    is in or aspects (5th/7th/9th) them. Engine reading (diwali.py rule-B comment): Jupiter's main sign,
    held >= 6 of the 12 months; any_month=True is the spec §5 wording "at any point" (reported, see doc)."""
    ch, per = p["chart"], p["period"]
    house_of = {x["name"]: x["house"] for x in ch["planets"]}
    rules = lambda pl: {int(h) for h, v in ch["houses"].items() if v["lord"] == pl}
    from collections import Counter
    hs_j = Counter((m.get("transits") or {}).get("Jupiter", {}).get("house") for m in p["months"])
    main = [h for h, n in hs_j.items() if n >= 6] or [hs_j.most_common(1)[0][0]]
    jup = set()
    for h in (hs_j if any_month else main):
        if h:
            jup |= {h, (h + 3) % 12 + 1, (h + 5) % 12 + 1, (h + 7) % 12 + 1}
    out = {}
    for a, hs in diwali.AREA_HOUSES.items():
        hs = set(hs)
        out[a] = sum([bool((rules(per["md"]) | {house_of.get(per["md"])}) & hs),
                      bool((rules(per["ad"]) | {house_of.get(per["ad"])}) & hs), bool(jup & hs)])
    return out


def chk_order(p, html):
    m, bad = p["meta"], []
    order, steer, work = p["area_order"], m["steering"], m["work_type"]
    es = expected_scores(p)
    if es != p["scores"]:
        bad.append(f"scores {p['scores']} != recomputed {es}")
    exp = expected_order(work, steer, p["scores"])
    if order != exp:
        bad.append(f"order {order} != spec {exp}")
    if p["first_reason"] != ("picked" if steer in diwali.AREAS else "situation"):
        bad.append(f"first_reason {p['first_reason']}")
    seq = [cid(c)[2:] for c in cards(html) if cid(c).startswith("a-")]
    want = (["luck"] + order) if steer == "luck" else (order + ["luck"])
    if seq != want:
        bad.append(f"cards {seq} != {want}")
    picked = set(re.findall(r"You picked ([A-Za-z &]+?), so", visible(html)))
    lab = {"luck": "Better luck", "family": "Family & children"}.get(steer, diwali.AREA_LABEL.get(steer))
    if steer and not (picked and picked <= {lab, diwali.AREA_LABEL.get(steer)}):
        bad.append(f"'You picked' line {picked} for {steer}")
    if not steer and picked:
        bad.append(f"'You picked' line {picked} when skipped")
    return bad


STATUS = ["your wife", "your husband", "your spouse", "your marriage", "your married", "your children",
          "your kids", "your in-laws", "the right person", "marry again", "when children may come",
          "first marriage", "new marriage", "remarr", "after your wedding", "your son", "your daughter"]


def chk_status(p, html):
    low = visible(html).lower()
    return [f"status phrase {s!r}" for s in STATUS if s in low]


# T2/T3 best-time claims: any superlative (best/brightest/strongest/peak/top/luckiest/most...) tied to a time, in any wording.
# Nothing is allowlisted: "strongest good time" names one strongest time too. Only gold months (their own rule) are left out.
# _BMON: exact month names, case-sensitive inside the re.I pattern, so "Mars" and the verb "may" are not months.
# (Own name: reusing _MON here would overwrite the module-level _MON that _norm() reads at call time.)
_BMON = (r"(?-i:(?:January|February|March|April|May|June|July|August|September|October|November|December"
         r"|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\b)")
_WHEN = (r"(?:early\s+on|late\s+on|(?:right|straight|soon|just)\s+after|as\s+soon\s+as|once\s+the"
         r"|from\s+the\s+(?:very\s+)?(?:start|beginning|first)|in\s+the\s+weeks?\s+after"
         r"|(?:in|during|over|within)\s+(?:the\s+)?(?:first|opening|festive|last|closing|final|early|later|coming|next|second)\b"
         r"|(?:at|by|around|near|towards?|before|after)\s+the\s+(?:midpoint|middle|end|start|beginning|halfway)|(?:about\s+)?halfway|midway"
         r"|(?:early|late)\s+in\b"
         r"|between\b|(?:after|before|around|from|during)\s+(?:this\s+)?(?:Diwali|the\s+festival)"
         r"|this\s+Diwali|next\s+Diwali|\u25cf|" + _BMON + r")")
_SUP = (r"(?:best|brightest|strongest|peak|top|luckiest|richest|finest|highest|prime|high\s+point"
        r"|most(?:\s+of\s+all)?(?:\s+(?:favou?rable|promising|auspicious|fortunate|lucky|rewarding))?)")
# superlative -> time gap: up to 8 words inside one sentence, commas/colons/dashes allowed
# ("Lean on it most for money, from the very start"; "Money comes most easily through X, mainly in the first weeks")
_GAP = r"[,:]?\s+(?:[^\s.!?;]+[\s,:\u2013-]+){0,8}?"
_BEST_CLAIM = re.compile(
    r"\b" + _SUP + r"\s+(?:good\s+)?"
    r"(?:months?|times?|weeks|days|period|season|spell|stretch|window|phase|run|patch|moment|hours?"
    r"|part of the (?:run|months|year))\b(?! for gold)(?<!peak phase)"   # Sade Sati's "Peak phase" is a Saturn stage
    r"|\b" + _SUP + r"\b" + _GAP + _WHEN +
    r"|\b" + _BMON + r"[^.!?;]{0,60}?\b(?:best|brightest|strongest|peaks?)\b(?! for gold)"
    r"|\b(?:the\s+)?(?:months?|weeks|days|times?|period|phase|stretch|spell|opening\s+\w+|\w+\s+months?)\b[^.!?;]{0,50}?\b(?:are|is)\s+(?:your\s+|the\s+)?"
    r"(?:best|brightest|strongest|luckiest|richest|finest|highest|peaks?)\b(?! for gold)"
    r"|\b(?:best|strongest|brightest)\s+in\s+the\s+months?\b"
    r"|\b(?:early\s+on|late\s+on|at\s+first|at\s+the\s+start)\s+(?:is\s+when\s+)?[^.!?;]{0,40}?\b(?:does\s+best|is\s+best|runs?\s+strongest|shines?)\b"
    r"|\bis\s+when\b[^.!?;]{0,30}?\bdoes\s+best\b"
    r"|\bsuits? you best\b|\b(?:shines?|burns?|glows?|grows?|moves?|flows?|peaks?) (?:most|brightest|bright|best)\b"
    r"|\b(?:shines|peaks)\b" + _GAP + _WHEN, re.I)


def chk_time(p, html):
    m, bad = p["meta"], []
    ans = visible(card_by_id(html, "s-0-5")).lower()
    note = "less precise" in ans
    if m["basis"] == "moon" and not note:
        bad.append("Moon-sign chart but no less-precise note on Your Diwali answers")
    if m["basis"] == "lagna" and note:
        bad.append("rising-sign chart but less-precise note shown")
    if m["time_quality"] in ("T2", "T3"):
        if m["basis"] != "moon":
            bad.append(f"{m['time_quality']} read from {m['basis']}")
        if "less precise" not in visible(card_by_id(html, "b-6")).lower():
            bad.append("no less-precise line on Methodology")
        body = html[html.index('<section class="page'):]
        v = re.sub(r"Full bloom your best time|Bright with rays: best time|mean a best time", "", visible(body))
        for s in ("your best time", "best time", "single best time", "burn brightest", "burns brightest",
                  "brightest month"):
            if s in v.lower() if s.islower() else s in v:
                bad.append(f"T2/T3 says {s!r}")
        legend = r"Full bloom your best time|Bright with rays: best time|mean a best time"
        for para in paragraphs(body):
            for mt in _BEST_CLAIM.finditer(re.sub(legend, "", para)):
                bad.append(f"T2/T3 best-time claim {mt.group(0)!r}: {para[:90]}")
        if ">BEST TIME<" in body or re.search(r"Best: [A-Z][a-z]{2}", body):
            bad.append("T2/T3 BEST TIME tag")
        if diwali_bank.has_best(p):
            bad.append("has_best true for T2/T3")
        # the free-preview teaser is seen before payment, so it must follow the same rule
        t = json.dumps({k: v for k, v in p["teaser"].items() if k != "preview"}, ensure_ascii=False).lower()
        for s in ("best time", "brightest", "burn bright"):
            if s in t:
                bad.append(f"T2/T3 teaser says {s!r}")
        for line in re.findall(r'"((?:[^"\\]|\\.)*)"', json.dumps(p["teaser"], ensure_ascii=False)):
            for mt in _BEST_CLAIM.finditer(line):
                bad.append(f"T2/T3 teaser best-time claim {mt.group(0)!r}: {line[:90]}")
    return bad


def chk_age(p, html):
    if p["meta"]["age_band"] != "60p":
        return []
    low = visible(html).lower()
    return [f"60+ says {s!r}" for s in ("first job", "first salary") if s in low]


def chk_gift(p, html):
    g, cs, bad = p["meta"]["gift"], cards(html), []
    ids = [cid(c) for c in cs]
    v = visible(html)
    if not g["on"]:
        if "s-0-2" in ids or "A Diwali gift" in v:
            bad.append("gift page/text when gift is off")
        if ids.index("s-0-3") != 1:
            bad.append("Note not p.2 for self")
        return bad
    if ids.count("s-0-2") != 1 or ids.index("s-0-2") != 1:
        return ["gift page not exactly once at p.2"]
    if ids.index("s-0-3") != 2:
        bad.append("Note not p.3 in gift mode")
    gp = visible(cs[1])
    bless = visible(card_by_id(html, "s-2-6"))
    if g["giver_name"]:
        if f"From {g['giver_name']}" not in gp or f"A Diwali gift for you, {p['meta']['first_name']}" not in gp:
            bad.append("gift page lacks 'A Diwali gift for you, <name>' + 'From <giver>' (mock3c-v2)")
        if g["giver_name"] not in bless:
            bad.append("giver's name missing from blessing")
    elif "A Diwali gift for you" not in gp:
        bad.append("no-name gift page lacks 'A Diwali gift for you'")
    msg = g["message"] or diwali_bank.DEFAULT_GIFT_MESSAGE
    if visible(H.escape(msg)) not in gp:
        bad.append("gift message (or the ready-written one) missing")
    return bad


def chk_summary(p, html):
    """Wrapped, 12 months, timeline and takeaways agree with payload.summary (the one source)."""
    import diwali_report_back as B
    sm, months, bad = p["summary"], p["months"], []
    tone = {m["ym"]: m["tone"] for m in months}
    care = {ym for c in sm["careful"] for ym in tone if c["from"] <= ym <= c["to"]}
    if care != {ym for ym, t in tone.items() if t == "careful"}:
        bad.append("summary.careful runs != careful month tones")
    hb = diwali_bank.has_best(p)
    b = sm["best"]
    if hb and any(tone[ym] != "best" for ym in tone if b["from"] <= ym <= b["to"]):
        bad.append("summary.best run holds a non-best month")
    if p["best_time"]["from"] != b["from"] or p["best_time"]["to"] != b["to"]:
        bad.append("best_time != summary.best")
    w = p["wrapped"]
    if (w["best"]["from"], w["best"]["to"]) != (b["from"], b["to"]):
        bad.append("payload wrapped.best != summary.best")
    wc = visible(next(c for c in cards(html) if "Your Wrapped card" in c))
    bb, by = B.range_tile(b)
    if f"{'Best time' if hb else 'Good time'} {bb} {by}" not in wc:
        bad.append(f"Wrapped best tile != summary.best {b['label']}")
    longest = max(sm["careful"], key=lambda c: B._months_between(c["from"], c["to"]), default=None)
    cb, cy = B.range_tile(longest) if longest else ("Clear", "no careful time")
    if f"Careful time {cb} {cy}" not in wc:
        bad.append(f"Wrapped careful tile != summary careful {[c['label'] for c in sm['careful']]}")
    mon = " ".join(visible(c) for c in cards(html) if "Your 12 months" in c)
    for c in sm["careful"]:
        if c["label"] not in mon:
            bad.append(f"12 months note lacks careful {c['label']}")
    tl = visible(card_by_id(html, "s-0-6"))
    if hb and b["label"] not in tl and B.range_tile(b)[0] not in tl:
        bad.append(f"timeline lacks best {b['label']}")
    tk = visible(card_by_id(html, "e-3")).lower()
    if not sm["careful"] and "careful times" in tk and "few months need extra care" not in tk:
        bad.append("takeaways talk about careful times but there are none")
    if not hb and "best time" in tk:
        bad.append("takeaways name a best time with no best time")
    if hb:   # takeaway 4 position phrase sits in the same quarter bucket as summary.best
        i = diwali_bank.MONTH_YMS.index(b["from"]) if b["from"] in diwali_bank.MONTH_YMS else -1
        want = 0 if i <= 1 else 1 if i <= 4 else 2 if i <= 7 else 3
        hit = [k for k, vs in diwali_bank.POSV.items() for s in vs if s.lower() in tk]
        if hit and want not in hit:
            bad.append(f"takeaway best-time position bucket {hit} != month index {i}")
    return bad


_TEASER_BAD = re.compile(r"\b(January|February|March|April|June|July|August|September|October|November|December|"
                         r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\b|\bMay\s*(\d|–|-)|\b(19|20)\d\d\b|\d{4}-\d{2}")


def chk_teaser(p, html):
    t = json.dumps({k: v for k, v in p["teaser"].items() if k != "preview"}, ensure_ascii=False)
    bad = [f"teaser has date text {m.group(0)!r}" for m in _TEASER_BAD.finditer(t)]
    if len(p["teaser"].get("questions") or []) != 5:
        bad.append("teaser questions != 5")
    return bad


def chk_repeats(p, html):
    """Within one report no chart-derived sentence (6+ words) is printed twice, same card included."""
    seen, bad = {}, []
    for c, t, _ in chart_paragraphs(html, p["meta"]["first_name"], min_words=1):
        for s in re.split(r"(?<=[.!?])\s+", t):
            if len(s.split()) >= 6 and not _chrome_literal(s) and not s.startswith("When:") \
                    and p["meta"]["span"] not in s:
                k = s.lower().strip()
                if k in seen:
                    bad.append(f"repeated in {seen[k]} and {c}: {s[:90]}")
                seen.setdefault(k, c)
    return sorted(set(bad))


def chk_month_table(p, html):
    """12-month table Do + Watch cells: a careful month never says gold / a planned buy, and the column is not
    one line repeated (table cells carry no full stop, so chk_repeats cannot see them)."""
    b, bad = diwali_bank.bank(p), []
    dos = [b[f"months.{m['ym']}.do"] for m in p["months"]]
    for m, d in zip(p["months"], dos):
        if m["tone"] == "careful" and re.search(r"gold|planned buy", d, re.I):
            bad.append(f"{m['ym']} careful ({m['care_reason']}) but Do = {d!r}")
    if len(set(dos)) < 3:
        bad.append(f"12-month Do column has only {len(set(dos))} different lines: {sorted(set(dos))}")
    # Watch column: one Mars-house line can fill half the year (Mars retrograde 2027 holds one sign)
    watch, n = Counter(b[f"months.{m['ym']}.watch"] for m in p["months"]).most_common(1)[0]
    if n >= 6:
        bad.append(f"12-month Watch column repeats {watch!r} in {n} of 12 rows")
    return bad


PURE = [chk_cards, chk_links, chk_lint, chk_leak, chk_order, chk_status, chk_time, chk_age, chk_gift,
        chk_summary, chk_teaser, chk_repeats, chk_month_table]


@pytest.mark.parametrize("chk", PURE, ids=[f.__name__[4:] for f in PURE])
@pytest.mark.parametrize("i", range(len(VERSIONS)), ids=VIDS)
def test_version(i, chk):
    p, html = build(i)
    bad = chk(p, html)
    assert not bad, bad[:12]


def test_matrix_covers_every_option():
    ps = [build(i)[0]["meta"] for i in range(len(VERSIONS))]
    assert {m["steering"] for m in ps} == set(STEER)
    assert {m["work_type"] for m in ps} == set(WORK)
    assert {m["gender"] for m in ps} == {"male", "female"}
    assert {m["time_quality"] for m in ps} == set(TIMES)
    assert {m["age_band"] for m in ps} == set(BANDS)
    gifts = {"off" if not m["gift"]["on"] else "named" if m["gift"]["giver_name"] else "empty" for m in ps}
    assert gifts == set(GIFTS)
    assert {m["basis"] for m in ps} == {"lagna", "moon"}
    assert len({(r["dob"], r["tob"], r["place"]) for r in VERSIONS}) == len(VERSIONS) >= 24
    assert {(r["steering"], r["work_type"]) for r in VERSIONS} == {(s, w) for s in STEER for w in WORK}


DOWATCH = re.compile(r"^(Do|Watch|Your step):")


def _five(reports):
    """Paragraphs printed identically (dates/numbers/name aside) in 2+ of the reports."""
    owner = {}
    for n, (p, html) in enumerate(reports):
        for c, t, k in chart_paragraphs(html, p["meta"]["first_name"]):
            owner.setdefault(k, {}).setdefault(n, (c, t))
    return [(len(v), next(iter(v.values()))) for k, v in owner.items() if len(v) >= 2]


@pytest.mark.parametrize("which", ["same_inputs", "mixed_inputs"])
def test_five_buyers_do_watch_not_shared_by_all(which):
    """bugs.md #19: no fixed Do/Watch lists shared by everyone: no Do/Watch line printed for all 5."""
    reps = ([build_row(json.dumps(r, sort_keys=True)) for r in FIVE_SAME] if which == "same_inputs"
            else [build(i) for i in FIVE_MIXED])
    dup = [d for d in _five(reps) if DOWATCH.match(d[1][1]) and d[0] == 5]
    assert not dup, [f"{c}: {t[:80]}" for _, (c, t) in dup[:15]] + [f"total {len(dup)}"]


@pytest.mark.parametrize("which", ["same_inputs", "mixed_inputs"])
def test_five_buyers_facts_differ_fallback_may_be_generic(which):
    """Deterministic fallback may be generic; uniqueness is checked on AI-on output after deploy."""
    if which == "same_inputs":
        reps = [build_row(json.dumps(r, sort_keys=True)) for r in FIVE_SAME]
    else:
        reps = [build(i) for i in FIVE_MIXED]
    dup = [d for d in _five(reps) if not DOWATCH.match(d[1][1])]
    sigs = {json.dumps(p["months"], sort_keys=True, default=str) for p, _ in reps}
    assert len(sigs) > 1, "five different charts gave one month pattern"
    assert len({html for _, html in reps}) == len(reps), "two buyers got byte-identical reports"


# ---- Chrome checks --------------------------------------------------------------------------------
def make_pdf(html, out_dir):
    src, out = os.path.join(out_dir, "r.html"), os.path.join(out_dir, "r.pdf")
    with open(src, "w") as f:
        f.write(html)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=10000",
                    f"--print-to-pdf={out}", f"file://{src}"], capture_output=True, timeout=120, check=True)
    return out


def chk_pdf(p, html, pdf):
    """323x623 pt pages, one per card, and every PDF link jumps to the card that holds its target id."""
    import fitz
    d = fitz.open(pdf)
    cs = cards(html)
    bad = [] if len(d) == len(cs) else [f"{len(d)} PDF pages != {len(cs)} cards"]
    for pg in d:
        if (round(pg.rect.width), round(pg.rect.height)) != (323, 623):
            bad.append(f"page {pg.number + 1} is {pg.rect.width:.0f}x{pg.rect.height:.0f}")
            break
    where = {}
    for k, c in enumerate(cs):
        for i in re.findall(r'\bid="([^"]+)"', c):
            where.setdefault(i, k)
    for pg in d:
        for ln in pg.get_links():
            dest = ln.get("nameddest")
            if dest and where.get(dest) != ln.get("page"):
                bad.append(f"p.{pg.number + 1} link #{dest} goes to p.{ln.get('page', -1) + 1}, card is p.{where.get(dest, -2) + 1}")
            m = re.search(r"p\.(\d+)", pg.get_textbox(ln["from"]) or "")
            if dest and m and int(m.group(1)) != ln.get("page", -1) + 1:
                bad.append(f"p.{pg.number + 1} link text p.{m.group(1)} but jumps to p.{ln['page'] + 1}")
    return bad


def chk_overflow(edges, html):
    bad = [f"p.{n} {c or ''} '{h}' top {round(t)} bottom-gap {round(b)} fit {f}" for n, c, h, t, b, f in edges
           if t < 8 or b < 26]
    topics = {k + 1 for k, cd in enumerate(cards(html)) if re.search(r'class="eyebrow">[^<]* · \d+ of \d+<', cd)}
    bad += [f"p.{n} '{h}' shrunk to fit {f}" for n, _, h, _, _, f in edges if n in topics and f < 1]
    bad += [f"p.{n} '{h}' fit {f} < 0.85" for n, _, h, _, _, f in edges if f < 0.85]
    return bad


@pytest.fixture(scope="module")
def chrome_page():
    import playwright.sync_api as pw
    _need_chrome()
    with pw.sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME)
        pg = b.new_page(viewport={"width": 430, "height": 830})
        pg.emulate_media(media="print")
        yield pg
        b.close()


def measure(pg, html, path):
    with open(path, "w") as f:
        f.write(html)
    pg.goto(f"file://{path}")
    pg.evaluate("document.fonts.ready")
    pg.wait_for_timeout(300)
    return pg.evaluate(_EDGES_JS)


@pytest.mark.slow
@pytest.mark.parametrize("i", range(len(VERSIONS)), ids=VIDS)
def test_version_pdf(i, tmp_path):
    import fitz  # noqa: F401  (missing -> ImportError -> fail)
    _need_chrome()
    p, html = build(i)
    bad = chk_pdf(p, html, make_pdf(html, str(tmp_path)))
    assert not bad, bad[:12]


@pytest.mark.slow
@pytest.mark.parametrize("i", range(len(VERSIONS)), ids=VIDS)
def test_version_no_overflow(i, chrome_page, tmp_path):
    p, html = build(i)
    bad = chk_overflow(measure(chrome_page, html, str(tmp_path / "o.html")), html)
    assert not bad, bad[:12]


# ---- report mode: table for docs/diwali/version-test-report.md + page shots ------------------------
SHOT_DIR = os.path.join(ROOT, "docs", "diwali", "version-shots")
SHOT_VERSIONS = [0, 3, 6, 9, 13, 20, 26]


def _shot_pages(html):
    ids = [cid(c) for c in cards(html)]
    pick = {"front": ids.index("s-0-5"), "opener": next(k for k, x in enumerate(ids) if x.startswith("a-")),
            "topic": next(k for k, x in enumerate(ids) if x.startswith("a-")) + 1, "months": ids.index("s-1-months"),
            "wrapped": next(k for k, c in enumerate(cards(html)) if "Your Wrapped card" in c),
            "takeaways": ids.index("e-3")}
    if "s-0-2" in ids:
        pick["gift"] = ids.index("s-0-2")
    if "a-marriage" in ids:
        pick["marriage"] = ids.index("a-marriage") + 1
    return pick


def report():
    import fitz
    from playwright.sync_api import sync_playwright
    os.makedirs(SHOT_DIR, exist_ok=True)
    cols = [f.__name__[4:] for f in PURE] + ["pdf", "overflow"]
    rows, fails = [], {}
    with sync_playwright() as pw, tempfile.TemporaryDirectory() as tmp:
        b = pw.chromium.launch(executable_path=CHROME)
        pg = b.new_page(viewport={"width": 430, "height": 830})
        pg.emulate_media(media="print")
        for i, r in enumerate(VERSIONS):
            p, html = build(i)
            res = {f.__name__[4:]: f(p, html) for f in PURE}
            pdf = make_pdf(html, tmp)
            res["pdf"] = chk_pdf(p, html, pdf)
            edges = measure(pg, html, os.path.join(tmp, "o.html"))
            res["overflow"] = chk_overflow(edges, html)
            m = p["meta"]
            g = "off" if not m["gift"]["on"] else ("named" if m["gift"]["giver_name"] else "empty")
            rows.append((VIDS[i], m, g, len(cards(html)), min(e[5] for e in edges), res))
            fails.update({(VIDS[i], k): v for k, v in res.items() if v})
            if i in SHOT_VERSIONS:
                d = fitz.open(pdf)
                for tag, k in _shot_pages(html).items():
                    d[k].get_pixmap(dpi=110).save(os.path.join(SHOT_DIR, f"{VIDS[i]}-{tag}-p{k + 1}.png"))
            print(VIDS[i], {k: len(v) for k, v in res.items() if v}, file=sys.stderr)
        b.close()
    print("| version | steer | work | sex | time/basis | age | gift | cards | min fit | " + " | ".join(cols) + " |")
    print("|" + "---|" * (9 + len(cols)))
    for vid, m, g, n, fit, res in rows:
        print(f"| {vid} | {m['steering'] or 'skipped'} | {m['work_type']} | {m['gender'][0].upper()} | "
              f"{m['time_quality']}/{m['basis']} | {m['age_band']} | {g} | {n} | {fit:.2f} | "
              + " | ".join("pass" if not res[c] else f"FAIL {len(res[c])}" for c in cols) + " |")
    print("\n## Failure details\n")
    for (vid, k), v in fails.items():
        print(f"- **{vid} / {k}**: " + " ; ".join(v[:6]) + (f" (+{len(v) - 6} more)" if len(v) > 6 else ""))
    for which, reps in (("same inputs", [build_row(json.dumps(r, sort_keys=True)) for r in FIVE_SAME]),
                        ("mixed inputs", [build(i) for i in FIVE_MIXED])):
        dup = _five(reps)
        print(f"\n### 5-buyer test, {which}: {len(dup)} shared paragraphs\n")
        for n, (c, t) in sorted(dup, reverse=True)[:25]:
            print(f"- x{n} [{c}] {t[:140]}")


if __name__ == "__main__" and "--report" in sys.argv:
    report()
