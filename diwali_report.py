"""Diwali Wealth & Prosperity Report renderer (RENDER-A).

render_diwali(payload) -> one complete standalone HTML document, card per page.
Markup, classes and pictures are copied from the approved Mock 3C v2 kit
(docs/diwali/mock/kit-3c/m3_1..m3_3); only data and text come from the payload
and from prose(key) = payload["narrative"][key] or diwali_bank.bank(payload)[key].
This module owns the front pages, the Part 1 opener, the months before Diwali and
the 5 area sections; diwali_report_back.cards_back() supplies everything after.
The assembler orders the cards, numbers them and fills every p.@@<card-id>@@.
"""
import math
import re
from calendar import month_abbr, month_name
from datetime import datetime
from html import escape

from diwali_assets import DIWALI_CSS, DIWALI_DEFS, FONTS_LINK

AREA_LABEL = {"money": "Money", "career": "Career", "business": "Business",
              "family": "Family & children", "marriage": "Marriage", "luck": "Better luck"}
AREA_EYEBROW = {"money": "Your money months", "career": "Your work months",
                "business": "How it looks", "family": "", "marriage": ""}
ANSWER_NOUN = {"money": "money", "career": "career", "business": "business",
               "family": "family", "marriage": "relationship", "luck": "fresh-start"}
WORK_PHRASE = {"job": "someone in a job", "business": "a business owner",
               "student": "a student", "home": "someone who runs the home"}
ORD = ["first", "second", "third", "fourth", "fifth", "sixth"]
NUM = ["no", "one", "two", "three", "four", "five", "six"]
WHEN = {"best": "best time", "good": "good time", "careful": "careful time", "steady": "steady time"}
BADGE = {"good": '<span class="wg grn">Good</span>', "steady": '<span class="wg">Steady</span>',
         "careful": '<span class="wg mod">Careful</span>'}
PILL = {"good": "m31-wgood", "steady": "m31-wsteady", "careful": "m31-wcare", "best": "m31-wbest"}
GREEN, TERRA, GOLD, GOLD2, INK, GREY = "#3E7D5A", "#B4572B", "#B9862E", "#8A6420", "#1B1D2A", "#4C4A57"

# Card-head short label for each topic title the bank sends (diwali_bank MONEY/CAREER/BUSINESS/FAMILY/MARRIAGE).
# Keyed by title, so the head always names the topics actually on the card; unknown titles fall back to the title.
SHORT = {
    "Will money get better after this Diwali?": "Better money",
    "When does your next good money time start?": "your next good time",
    "Which months suit saving, and which suit spending?": "Saving and spending",
    "When is a good time to clear loans?": "clearing loans",
    "If you had a loss, when do things recover?": "Recovering from a loss",
    "Where does your money come from most easily?": "where money comes from",
    "Your wealth combination": "Your wealth combination",
    "When could your next big break or promotion come?": "Your next big break",
    "Should you switch or stay?": "switch or stay",
    "When is a good time to ask for a raise?": "Asking for a raise",
    "If you lost your job, when do things pick up?": "after a job loss",
    "What kind of work suits you most?": "Work that suits you",
    "Work abroad or travel for work: which months suit a move?": "work abroad and travel",
    "When do your studies go best?": "Your studies",
    "How may exams and results go?": "exams and results",
    "When might your first job or internship come?": "Your first job or internship",
    "Study abroad: which months suit it?": "Study abroad",
    "Learning a new skill": "a new skill",
    "When is a good time to return to work?": "Returning to work",
    "Can a home-run income work for you?": "home-run income",
    "Fitting work around home": "Fitting work around home",
    "Travel for work or family": "travel",
    "Leading your people": "Your role as the owner",
    "When to step up": "when to step up",
    "Your name and reputation": "Your name",
    "Delegation": "your team",
    "Work travel": "Work travel",
    "A second line of leaders": "your next leaders",
    "How does your business look from this Diwali to the next?": "How it looks",
    "When is a good time to start or expand?": "Growing",
    "Partner or alone?": "Partner or alone",
    "When do new deals, hiring and new account books fit?": "Deals and books",
    "When to go slow on spending and credit?": "slower months",
    "Does your chart lean to business or a job?": "Business or job",
    "When is a good time to start a side income?": "side income",
    "Partner or alone for a side plan?": "Partner or alone",
    "How small to start, and which months suit it?": "starting small",
    "Which months to go slow on new spending?": "Slower months",
    "Business or a job: where does your chart lean?": "Business or job",
    "When could you try a small project?": "a small project",
    "Which months suit learning trade skills?": "Trade skills",
    "Which months to go slow on spending?": "slower months",
    "Could a small home venture suit you?": "A small home venture",
    "When is a good time to start?": "when to start",
    "With a partner or alone?": "Partner or alone",
    "The family money picture": "the family money picture",
    "The whole family": "How home life may go",
    "Family events and celebrations": "family events",
    "House move or property": "Home and property",
    "Moving city or abroad": "moving",
    "Which months may bring happy news in your family?": "Happy news in your family",
    "Care in family talks": "family talks",
    "More warmth in your relationships": "Warmth",
    "Important relationship decisions": "decisions",
    "Care in close talks": "Talking things through",
    "Your partnership traits": "Partnership in your chart",
}
TOC_TITLES = {  # card id -> contents line, for cards made by diwali_report_back
    "a-luck": "Better luck and a fresh beginning", "s-1-sadesati": "Sade Sati check",
    "s-1-strengths": "Your 3 strengths", "s-1-slow": "Months to go slow", "s-1-months": "Your 12 months",
    "part-2": "Part 2 · Your Diwali", "s-2-1": "Diwali across India", "s-2-2": "Lakshmi Puja time",
    "s-2-3": "Good months for gold and big buys", "s-2-4": "Lakshmi practices",
    "s-2-5": "Your fresh-start plan", "s-2-6": "A Diwali blessing", "e-1": "Your priorities",
    "e-2": "Your next 30, 90 and 365 days", "e-3": "5 takeaways", "b-1": "Your birth chart",
    "b-2": "Your planets", "b-3": "Houses used in this report", "b-4": "Astrology made simple",
    "b-5": "Your doubts answered", "b-6": "Methodology & disclaimer", "b-7": "Thank you"}
TOC_HEADS = {"part-2": "Part 2 · Your Diwali", "e-1": "Your plan", "b-1": "Back pages"}
PART1_AFTER = ["s-1-sadesati", "s-1-strengths", "s-1-slow", "s-1-months"]

CHROME_CSS = ("@media print{body>*:not(.page):not(svg){display:none!important}"
              "#axlang,#ax-pdf,.ax-share,.ax-report-disclaimer{display:none!important}"
              "section.page>.col{zoom:var(--fit,1)}}")

# Print fit: a printed card is a fixed 430x830 box with overflow hidden, and AI text lengths vary, so a card
# whose content is taller than the box is shrunk (print only) instead of being clipped. The column is measured
# at its print width (430 - 2 x 23.65px padding); the budget lets content reach 18px into the top/bottom
# padding, as the approved mock does, while staying clear of the Contents link. Screen view is untouched.
FIT_W, FIT_BUDGET = 382.7, 830 - 46 - 50 + 36
FIT_JS = ("<script>(function(){function fit(){document.querySelectorAll('section.page>.col').forEach(function(c){"
          "var p=c.parentElement,w=c.style.width;p.style.removeProperty('--fit');c.style.width='" + str(FIT_W) + "px';"
          "var h=c.getBoundingClientRect().height;c.style.width=w;"
          "if(h>" + str(FIT_BUDGET) + ")p.style.setProperty('--fit',(" + str(FIT_BUDGET) + "/h).toFixed(3));});}"
          "fit();if(document.fonts&&document.fonts.ready)document.fonts.ready.then(fit);"
          "window.addEventListener('load',fit);window.addEventListener('beforeprint',fit);})();</script>")


def E(s):
    # '@' escaped too: the assembler's p.@@id@@ pass must never touch buyer or AI text (a gift message)
    return escape(str(s or ""), quote=True).replace("@", "&#64;")


def _best_time(p):
    """The overall best time = payload.summary.best (the engine's one source), only when the chart has one
    (spec §2 rule 10: none for T2/T3)."""
    from diwali_bank import has_best
    return ((p.get("summary") or {}).get("best") or {}) if has_best(p) else {}


# ---------- months ----------
def _ym(ym):
    y, m = str(ym).split("-")[:2]
    return int(y), int(m)


def _mon(ym):
    return month_abbr[_ym(ym)[1]]


def _add(ym, n):
    y, m = _ym(ym)
    k = y * 12 + m - 1 + n
    return f"{k // 12:04d}-{k % 12 + 1:02d}"


def _span(a, b):
    out, cur = [], a
    while cur <= b and len(out) < 24:
        out.append(cur)
        cur = _add(cur, 1)
    return out


def _runs(yms):
    out = []
    for ym in sorted(set(yms or [])):
        if out and _add(out[-1][-1], 1) == ym:
            out[-1].append(ym)
        else:
            out.append([ym])
    return out


def _fmt_run(run, short=False):
    a, b = run[0], run[-1]
    yr = (lambda ym: str(_ym(ym)[0])[2:]) if short else (lambda ym: str(_ym(ym)[0]))
    if a == b:
        return f"{_mon(a)} {yr(a)}"
    if _ym(a)[0] == _ym(b)[0]:
        return f"{_mon(a)}–{_mon(b)} {yr(b)}"
    return f"{_mon(a)} {yr(a)}–{_mon(b)} {yr(b)}"


def _rng(yms, short=False):
    return " and ".join(_fmt_run(r, short) for r in _runs(yms))


def _mons(run):
    """Month names only: every month occurs once in the Diwali-to-Diwali span."""
    return _mon(run[0]) if run[0] == run[-1] else f"{_mon(run[0])}–{_mon(run[-1])}"


def _area_tone(area_d, ym):
    w = (area_d or {}).get("windows") or {}
    for k in ("best", "careful", "good"):
        if ym in (w.get(k) or []):
            return k
    return "steady"


def _mark(area_d, score=0, top=0):
    """Best / Good / Careful mark for a whole area (diya path). The engine gives every area
    some best month, so "best" needs more: the area is among the most active by the
    period/Jupiter score (payload.scores, 0-3). Careful when the state says so or careful
    months outnumber the good and best ones."""
    ad = area_d or {}
    w = ad.get("windows") or {}
    nb, ng, nc = (len(w.get(k) or []) for k in ("best", "good", "careful"))
    if ad.get("state") == "careful" or nc > nb + ng:
        return "careful"
    return "best" if nb and ad.get("state", "good") == "good" and top and score == top else "good"


def _sign(s):
    return str(s or "").replace(" (Cancer)", "").replace("Cancer", "Karka")


def _wrap(text, width, max_lines=3):
    lines, cur = [], ""
    for w in str(text).split():
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    # never drop words: anything past max_lines joins the last line
    return lines[:max_lines - 1] + [" ".join(lines[max_lines - 1:])] if len(lines) > max_lines else lines


def _strip_label(s, label):
    s = str(s or "").strip()
    return re.sub(rf"^{label}\s*:\s*", "", s, flags=re.I)


# ---------- prose ----------
class _Prose:
    """prose(key) = narrative[key] or bank[key]. opt(key, default) for keys the
    bank may not define (renderer-side fallbacks)."""

    def __init__(self, payload):
        self.payload, self.narr, self._bank = payload, payload.get("narrative") or {}, None

    @property
    def bank(self):
        if self._bank is None:
            import diwali_bank  # written in parallel; imported lazily
            self._bank = diwali_bank.bank(self.payload)
        return self._bank

    def __call__(self, key):
        return self.narr.get(key) or self.bank[key]

    def opt(self, key, default=""):
        return self.narr.get(key) or self.bank.get(key) or default


# ---------- card shell ----------
TOCL = '<a class="tocl" href="#contents">Contents</a>'
GARLAND = '<svg class="garland"><use href="#i-garland"/></svg>'
DIYA_I = '<svg class="diya-i" style="display:inline-block"><use href="#i-diya"/></svg>'


def _card(body, cls="", cid=None, pre="", tocl=True):
    c = f"page {cls}".strip()
    i = f' id="{cid}"' if cid else ""
    return f'<section class="{c}"{i}>{pre}<div class="col">{body}</div>{TOCL if tocl else ""}<div class="pgn"></div></section>'


def _xr(cid, text, page=True):
    p = f", p.@@{cid}@@" if page else ""
    return f'<a class="xr" href="#{cid}">{text}{p}</a>'


def _pill(state, w=58):
    return (f'<svg style="width:{w}px;height:16px;flex:0 0 {w}px;vertical-align:-3px" '
            f'aria-label="{state.title()}"><use href="#{PILL.get(state, PILL["steady"])}"/></svg>')


# ---------- order lines ----------
class _Ctx:
    def __init__(self, p):
        self.p, self.meta = p, p.get("meta") or {}
        self.order = list(p.get("area_order") or ["money", "career", "business", "family", "marriage"])
        self.steer = self.meta.get("steering")
        self.luck_first = self.steer == "luck"
        self.picked = p.get("first_reason") == "picked" and bool(self.steer)
        self.work = self.meta.get("work_type") or "job"
        self.areas = p.get("areas") or {}
        self.first = self.meta.get("first_name") or (self.meta.get("name") or "").split(" ")[0] or "friend"
        self.lead_area = "luck" if self.luck_first else self.order[0]

    def label(self, a):
        if a == "career" and self.work == "student":
            # 60+ never reads "first job" (spec §9 age lint; the bank swaps it for "next role" too)
            return "Career: studies & " + ("next role" if self.meta.get("age_band") == "60p" else "first job")
        return AREA_LABEL[a]

    def first_line(self, verb="comes first"):
        a = self.lead_area
        if self.picked:
            return f"You picked {self.label(a)}, so it {verb}."
        return f"As {WORK_PHRASE.get(self.work, 'you')}, your report starts with {self.label(a)}."


# ---------- diya / flower drawings ----------
def _diya(state, x, y, s):
    inner = {"best": _D_BEST, "careful": _D_CARE}.get(state, _D_GOOD)
    return f'<g transform="translate({x} {y}) scale({s})">{inner}</g>'


def _flower(state, x):
    if state == "best":
        out = ""
        for k in range(12):
            a = k * 30
            ex, ey = x + 12.5 * math.cos(math.radians(a)), 120 + 12.5 * math.sin(math.radians(a))
            out += (f'<ellipse cx="{ex:.1f}" cy="{ey:.1f}" rx="7.8" ry="5.8" fill="#E39B2B" stroke="#B9862E" '
                    f'stroke-width=".6" transform="rotate({a} {ex:.1f} {ey:.1f})"/>')
        return out + (f'<circle cx="{x:.1f}" cy="120" r="8.8" fill="#F2C14E" stroke="#B9862E" stroke-width=".6"/>'
                      f'<circle cx="{x:.1f}" cy="120" r="3.2" fill="#D9692A"/>')
    if state == "careful":
        return (f'<ellipse cx="{x:.1f}" cy="121.6" rx="7.2" ry="11.2" fill="#E39B2B" stroke="#B9862E" stroke-width=".6"/>'
                f'<path d="M{x - 8.8:.1f} 118.4 Q{x:.1f} 102.4 {x + 8.8:.1f} 118.4 Q{x:.1f} 124.8 {x - 8.8:.1f} 118.4Z" fill="#3E7D5A"/>')
    out = f'<path d="M{x - 7.5:.1f} 117.5 Q{x:.1f} 105.0 {x + 7.5:.1f} 117.5" fill="#3E7D5A"/>'
    for a in (19, 54, 90, 126, 161):
        ex, ey = x + 8.25 * math.cos(math.radians(a)), 120 + 8.25 * math.sin(math.radians(a))
        out += (f'<ellipse cx="{ex:.1f}" cy="{ey:.1f}" rx="6.9" ry="5.0" fill="#E39B2B" stroke="#B9862E" '
                f'stroke-width=".6" transform="rotate({a} {ex:.1f} {ey:.1f})"/>')
    return out + f'<circle cx="{x:.1f}" cy="121.2" r="6.2" fill="#F2C14E" stroke="#B9862E" stroke-width=".6"/>'


def _garland(strands, aria):
    """No. 9 door garland: one strand per {label, state, months_label}."""
    n = max(1, len(strands))
    xs = [20 + 340 * (2 * i + 1) / (2 * n) for i in range(n)]
    pts = [20] + xs + [360]
    swag = "M20 32 " + " ".join(f"Q{(pts[i] + pts[i + 1]) / 2:.1f} 48 {pts[i + 1]:.1f} 32" for i in range(len(pts) - 1))
    out = [_G_FRAME, f'<path d="{swag}" fill="none" stroke="#3E7D5A" stroke-width="1.2"/>']
    for i in range(len(pts) - 1):
        mx = (pts[i] + pts[i + 1]) / 2
        out.append(f'<path d="M{mx:.1f} 40 q5 9 0 19 q-5 -10 0 -19z" fill="#3E7D5A" opacity=".85"/>')
    width = 9 if n >= 6 else 12 if n >= 5 else 14
    bottom = 200
    for x, s in zip(xs, strands):
        st = s.get("state") or "good"
        out.append(f'<circle cx="{x:.1f}" cy="32" r="4.2" fill="#E39B2B"/><circle cx="{x:.1f}" cy="32" r="1.8" fill="#F2C14E"/>'
                   f'<line x1="{x:.1f}" y1="36" x2="{x:.1f}" y2="104" stroke="#3E7D5A" stroke-width="1"/>'
                   f'<circle cx="{x:.1f}" cy="62" r="3.6" fill="#E39B2B"/><circle cx="{x:.1f}" cy="86" r="3.6" fill="#E39B2B"/>')
        out.append(_flower(st, x))
        y = 208
        for ln in _wrap(s.get("label", ""), width, 2):
            out.append(f'<text x="{x:.1f}" y="{y}" text-anchor="middle" font-family="Fraunces,Georgia,serif" '
                       f'font-weight="600" font-size="11.5" fill="#1B1D2A">{E(ln)}</text>')
            y += 13
        col, word = {"best": (GREEN, "Best time"), "careful": (TERRA, "Careful time"),
                     "steady": (GOLD, "Steady")}.get(st, (GOLD, "Good time"))
        out.append(f'<text x="{x:.1f}" y="{y + 1}" text-anchor="middle" font-family="Inter,sans-serif" font-style="italic" '
                   f'font-weight="600" font-size="9.5" fill="{col}">{word}</text>')
        y += 14
        ml = s.get("months_label") or ""
        # engine sends short run labels as a list (one line each) and an optional caption list (mock: "talk slowly")
        for ln in (ml if isinstance(ml, list) else str(ml).split("\n"))[:3]:
            out.append(f'<text x="{x:.1f}" y="{y}" text-anchor="middle" font-family="Inter,sans-serif" '
                       f'font-weight="500" font-size="8.8" fill="#4C4A57">{E(ln)}</text>')
            y += 11
        for ln in (s.get("caption") or [])[:2]:
            out.append(f'<text x="{x:.1f}" y="{y}" text-anchor="middle" font-family="Inter,sans-serif" '
                       f'font-weight="500" font-size="8.2" fill="#6E6A78">{E(ln)}</text>')
            y += 10
        bottom = max(bottom, y)
    return (f'<svg viewBox="0 0 380 {bottom}" width="100%" role="img" aria-label="{E(aria)}">'
            + "".join(out) + "</svg>")


def _garland_legend(best_txt, good_txt, bud_txt):
    rows = [(_ICON_FULL, "Full bloom", best_txt), (_ICON_HALF, "Half open", good_txt), (_ICON_BUD, "Bud", bud_txt)]
    return '<div class="leg">' + "".join(f'<div class="lr">{i}<span class="lt"><b>{h}</b>{t}</span></div>'
                                         for i, h, t in rows) + "</div>"


def _diya_strip(c, area, coins=False):
    """No. 1 diyas: 12 months in two rows, state from this area's windows."""
    ad = c.areas.get(area) or {}
    me = c.p.get("money_extra") or {}
    gold, loans = set(me.get("gold_months") or []), set(me.get("loan_months") or [])
    out = []
    for i, m in enumerate((c.p.get("months") or [])[:12]):
        ym = m["ym"]
        x, y = 31 + 62 * (i % 6), 62 if i < 6 else 186
        t = _area_tone(ad, ym)
        out.append(_diya(t, x, y, {"best": 0.78, "careful": 0.8}.get(t, 0.85)))
        out.append(f'<text x="{x}" y="{y + 28}" text-anchor="middle" style="font:600 12px Fraunces,Georgia,serif;fill:#1B1D2A">{_mon(ym)}</text>'
                   f'<text x="{x}" y="{y + 39}" text-anchor="middle" style="font:500 8.5px Inter,sans-serif;fill:#6E6A78">{_ym(ym)[0]}</text>')
        g, l = coins and ym in gold, coins and ym in loans
        if g:
            cx = x - 11 if l else x
            out.append(f'<circle cx="{cx}" cy="{y + 50}" r="4.6" fill="#F2C14E" stroke="#B9862E" stroke-width="1"/>'
                       f'<circle cx="{cx}" cy="{y + 50}" r="2.3" fill="none" stroke="#B9862E" stroke-width=".7"/>')
        if l:
            bx = x + 2 if g else x - 9
            out.append(f'<rect x="{bx}" y="{y + 48.2}" width="18" height="3.6" rx="1.8" fill="#7A2E36"/>')
        if t == "steady":
            out.append(f'<text x="{x}" y="{y + 64}" text-anchor="middle" style="font:700 7.5px Inter,sans-serif;letter-spacing:.1em;fill:#8A6420">STEADY</text>')
    return (f'<svg viewBox="0 0 372 250" width="100%" role="img" aria-label="Your 12 {E(AREA_LABEL[area].lower())} months as diyas" '
            f'style="display:block;margin-top:10px">' + "".join(out) + "</svg>")


DIYA_LEG = ('<div class="lr"><span class="dot" style="background:#E39B2B"></span><span class="lt"><b>The diya.</b> '
            'Bright with rays: best time. One thin ring: good time; with the word “Steady”: steady time. '
            'Dashed and unlit: careful time.</span></div>')


# ---------- R2 topic block ----------
def _topic_title(c, area, t, n, prose):
    # the bank title already carries any ": present"/": building" suffix (money.t7)
    return t.get("title") or prose.opt(f"{t['key']}.title") or f"{c.label(area)}: one more look"


def _topic_short(c, area, t, n, prose):
    q = _topic_title(c, area, t, n, prose)
    return SHORT.get(q) or SHORT.get(q.split(":")[0]) or q.rstrip("?")


def _topic(c, area, t, n, prose):
    k = t["key"]
    return (f'<div class="win" style="margin-top:10px;padding:11px 14px">{BADGE.get(t.get("state"), BADGE["steady"])}'
            f'<div class="wt" style="padding-right:62px">{E(_topic_title(c, area, t, n, prose))}</div>'
            f'<div class="wd">{E(prose(k + ".what"))}</div>'
            f'<div class="wd" style="margin-top:5px"><b>Do:</b> {E(_strip_label(prose(k + ".do"), "do"))}<br>'
            f'<b>Watch:</b> {E(_strip_label(prose(k + ".watch"), "watch"))}</div>'
            f'<div class="wd" style="margin-top:5px;color:var(--muted);font-style:italic">Why: {E(_strip_label(prose(k + ".why"), "why"))}</div>'
            f'<div class="wd" style="margin-top:5px"><b>When:</b> {E(prose.opt(k + ".when", WHEN.get(t.get("when"), "steady time")))} · '
            f'<a class="xr" href="#s-1-months">your 12 months, p.@@s-1-months@@ →</a></div></div>')


def _manglik(c):
    mx = (c.p.get("marriage_extra") or {}).get("manglik") or {}
    ch = c.p.get("chart") or {}

    def rule(v, what, sign):
        if isinstance(v, str):
            return E(v)
        if v is None:
            return "Not used: your birth time is not exact enough to fix the rising sign."
        if isinstance(v, bool):
            return "By this rule, yes." if v else "By this rule, no."
        h = v.get("house")
        yes = v.get("manglik", v.get("yes"))
        pos = f"Mars is {h}{_sfx(h)} from your {what}, {E(_sign(v.get('sign') or sign))}. " if h else ""
        return pos + ("By this rule, yes." if yes else "By this rule, no.")

    canc = mx.get("cancelled")
    reason = mx.get("reason") or ""
    canc_txt = (f"Yes. {E(reason)}" if canc else (E(reason) or "No cancelling rule applies.")) if (canc or reason) else "No cancelling rule applies."
    return ('<div class="win" style="margin-top:10px;padding:11px 14px"><div class="wt">Does your chart show Manglik, and does it matter?</div>'
            '<div class="wd">Manglik is an old rule about where Mars sits in your birth chart. Your plain facts:</div>'
            f'<div class="wd" style="margin-top:5px"><b>Rising-sign rule:</b> {rule(mx.get("lagna_rule"), "rising sign", (ch.get("lagna") or {}).get("sign"))}</div>'
            f'<div class="wd" style="margin-top:5px"><b>Moon rule:</b> {rule(mx.get("moon_rule"), "Moon sign", (ch.get("moon") or {}).get("sign"))}</div>'
            f'<div class="wd" style="margin-top:5px"><b>Cancelled:</b> {canc_txt}</div>'
            '<div class="wd" style="margin-top:5px"><b>What it means:</b> a fact to share with the family if a match is discussed. '
            'It does not need any paid fix.</div></div>')


def _sfx(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


# ---------- front pages ----------
def _fmt_dob(s):
    for f in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y"):
        try:
            d = datetime.strptime(str(s), f)
            return f"{d.day} {month_name[d.month]} {d.year}"
        except ValueError:
            pass
    return str(s or "")


def _fmt_tob(s):
    m = re.match(r"^(\d{1,2}):(\d{2})", str(s or ""))
    if not m:
        return str(s or "")
    h, mi = int(m.group(1)), m.group(2)
    return f"{(h % 12) or 12}:{mi} {'am' if h < 12 else 'pm'}"


def _cover(c):
    m, moon = c.meta, (c.p.get("chart") or {}).get("moon") or {}
    # T2/T3 tob is a server placeholder (band midpoint / 12:00), never the buyer's real time
    tq = m.get("time_quality")
    tob = ("birth time not known" if tq == "T3" else "birth time approximate" if tq == "T2"
           else f"about {_fmt_tob(m.get('tob'))}" if tq == "T1" and m.get("tob") else _fmt_tob(m.get("tob")))
    born = " · ".join(x for x in (_fmt_dob(m.get("dob")), tob, m.get("place")) if x)
    return _card(
        f'<div class="cov-brand">Axtroshastra</div>{_CONSTEL}'
        '<div class="cov-title">Diwali<br>Wealth &amp; Prosperity<br>Report</div>'
        '<div class="cov-sub">From this Diwali to the next<br>Diwali 2026 to Diwali 2027</div><div class="cov-line"></div>'
        f'<div class="cov-person"><div class="cov-name2">{E(m.get("name"))}</div><div class="cov-born">{E(born)}</div></div>'
        f'<div class="cov-type"><svg class="ti pi"><use href="#i-moon"/></svg><span>Moon sign {E(_sign(moon.get("sign")))} · '
        f'birth star {E(moon.get("nakshatra"))}</span></div><div class="cov-div"></div>'
        f'<div class="cov-sys">Report prepared {E(_fmt_dob(m.get("as_of")))}<span class="pw">Powered by personalised Vedic astrological analysis</span></div>'
        '<div class="cov-trust">Swiss Ephemeris · Lahiri ayanamsa</div>',
        "sand", "s-0-1", pre='<svg class="garland" style="width:100%"><use href="#i-garland"/></svg>', tocl=False)


def _gift(c, prose):
    g = c.meta.get("gift") or {}
    giver = (g.get("giver_name") or "").strip()
    msg = (g.get("message") or "").strip() or prose.opt(
        "gift.message", "You give so much to the people around you. I wanted you to have a clear view of "
                        "the months ahead, and a little light for them.")
    ch = f"From {E(giver)}, because…" if giver else "A wish for you"
    sig = (f'<p style="font-family:var(--sans);font-weight:700;font-size:12px;color:var(--gold);margin-top:10px">— {E(giver)}</p>'
           if giver else "")
    return _card(
        f'<div class="eyebrow">{DIYA_I}A Diwali gift</div>'
        f'<h2 class="head">A Diwali gift for you, {E(c.first)}</h2><div class="rule"></div>'
        f'<div class="callout" style="margin-top:22px;padding:20px 22px"><div class="ch">{ch}</div>'
        f'<p style="font-family:var(--serif);font-size:16px;color:var(--ink);line-height:1.55;font-style:italic">“{E(msg)}”</p>{sig}</div>'
        '<p class="lead" style="text-align:center;font-style:italic;color:var(--gold2);margin-top:20px">'
        'May this Diwali fill your home with light, and the months ahead with steady steps.</p>' + _MITHAI,
        "", "s-0-2")


def _note(c, prose):
    # chart-independent framing (CLAUDE.md §22 allows generic); no NARR_KEYS key for it
    ps = ["Diwali is a time to clean the house, light a diya and look ahead. This report is written for that moment.",
          "It reads your birth chart from this Diwali to the next: when money may move well, which months may need more care, and small steps that could help.",
          "A chart shows tendencies. Your own choices still lead. Keep this close, and come back to it month by month."]
    return _card(
        f'<div class="noteframe">{_NOTE_TOP}<div class="notebox"><div class="ne">A note for you</div>'
        f'<div class="nh">Dear {E(c.first)}, a bright Diwali to you</div>' + "".join(f"<p>{E(x)}</p>" for x in ps) +
        f'<div class="sig">— Your Axtroshastra analyst</div></div>{_NOTE_BOT}</div>', "note", "s-0-3")


def _howto(c, prose):
    span = c.meta.get("span") or "Nov 2026 – Oct 2027"
    rest = [c.label(a) for a in (c.order + ["luck"]) if a != c.lead_area]
    follow = ", ".join(rest[:-1]) + " and " + rest[-1]
    lead = f"You picked {c.label(c.lead_area)}, so it leads." if c.picked else f"As {WORK_PHRASE.get(c.work, 'you')}, {c.label(c.lead_area)} leads."
    row = lambda st, word, txt: (f'<div style="display:flex;gap:9px;align-items:flex-start;margin-top:5px;font-size:12px;line-height:1.45">'
                                 f'{_pill(st)}<span><b>{word}:</b> {txt}</span></div>')
    mark = lambda s, t: (f'<span style="display:inline-flex;flex-direction:column;align-items:center;gap:2px"><svg style="width:46px;height:46px">'
                         f'<use href="#m31-d{s}"/></svg><svg style="width:80px;height:14px"><use href="#m31-t{t}"/></svg></span>')
    return _card(
        f'<div class="eyebrow">{DIYA_I}Before you begin</div><h2 class="head" style="font-size:24px">How to read this report</h2><div class="rule"></div>'
        f'<p class="lead" style="margin-top:10px;font-size:14px">This report covers <b>from this Diwali to the next ({E(span)})</b>.</p>'
        '<div class="callout" style="margin-top:10px;padding:10px 14px"><div class="ch">One word for every answer</div>'
        + row("good", "Good", "things look in your favour. A fine time to act.")
        + row("steady", "Steady", "things hold. Keep going as you are.")
        + row("careful", "Careful", "go slowly and plan first. It gets better after.") +
        '</div><div class="callout" style="margin-top:10px;padding:10px 14px"><div class="ch">Three marks for time</div>'
        '<div style="display:flex;gap:8px;justify-content:center;width:100%;margin-top:6px">'
        + mark("best", "best") + mark("good", "good") + mark("care", "care") +
        '</div><p style="font-size:11.5px;line-height:1.45;margin-top:6px">Rays and a warm glow mean a <b>best time</b>. One thin ring means a '
        '<b>good time</b>. Unlit and dashed means a <b>careful time</b>. The lanterns, flowers and fountains in later pages follow the same rule.</p></div>'
        '<div class="leg" style="margin-top:12px">'
        f'<div class="lr"><span class="dot" style="background:#C9A34E"></span><span class="lt"><b>Dates live in two places:</b> '
        f'{_xr("s-0-6", "Your months at a glance", False)} and {_xr("s-1-months", "Your 12 months", False)}. '
        'Other pages say best, good or careful time and link back.</span></div>'
        f'<div class="lr"><span class="dot" style="background:#C9A34E"></span><span class="lt"><b>Your area comes first.</b> {E(prose.opt("note.order", f"{lead} {follow} follow."))}</span></div>'
        '<div class="lr"><span class="dot" style="background:#C9A34E"></span><span class="lt"><b>Each area ends with “The read”:</b> one line to remember.</span></div></div>'
        '<div class="take" style="margin-top:12px;font-size:13.5px"><b>Our promise</b>This report never predicts a figure. '
        'A chart shows tendencies; your own choices still lead.</div>', "", "s-0-4")


def _answers(c, prose):
    a = c.lead_area
    qs = ""
    for i, ans in enumerate((c.p.get("answers") or [])[:5], 1):
        st = ans.get("state") or "steady"
        qs += (f'<div class="vq"><div class="vn">{i}</div><div class="vb"><div class="vql">{E(ans.get("q"))}</div>'
               f'<div style="display:flex;gap:8px;align-items:flex-start;margin-top:4px">{_pill(st)}'
               f'<div class="vt" style="font-size:12px;line-height:1.45;color:var(--body)">{E(prose(f"answers.q{i}"))}</div></div></div></div>')
    fine = prose.opt("note.answers_intro", f"You picked {c.label(a)}, so your answers start there." if c.picked
                     else f"Your answers start with {c.label(a)}, your first area.")
    if c.meta.get("basis") == "moon":
        fine += " " + prose.opt("note.less_precise", "Read from your Moon sign, so a little less precise.")
    return _card(
        f'<div class="eyebrow">{DIYA_I}Your Diwali answers</div>'
        f'<h2 class="head" style="font-size:20px;line-height:1.3">Your 5 {ANSWER_NOUN[a]} questions, answered</h2><div class="rule"></div>'
        f'<p class="fine" style="text-align:center;margin-top:6px">{E(fine)}</p><div class="vdash">{qs}</div>'
        f'<div class="take" style="margin-top:12px"><b>Where to look next</b><span style="font-size:13px">'
        f'{_xr("s-0-6", "Your timeline")} shows the months for each answer. Each answer is explained in full in the {_xr("a-" + a, AREA_LABEL[a] + " section")}.</span></div>',
        "", "s-0-5")


def _timeline_headline(p, best_yms, best_txt):
    """Mock 3C v2 shape: "A steady start, a careful Feb–Apr, then your best time in Jun–Jul 2027."
    Overall ranges come from payload.summary only: the careful part named is the first summary.careful run
    before the best time (or the first at all when there is none); the start is the first month's tone."""
    months = p.get("months") or []
    tone0 = (months[0] if months else {}).get("tone")
    care = (p.get("summary") or {}).get("careful") or []
    if best_txt and months and months[0]["ym"] in best_yms:
        return f"Your best time comes first, in {best_txt}, so start the steps that matter soon after Diwali."
    start = {"careful": "A careful start", "best": "A strong start"}.get(tone0, "A steady start")
    first = months[0]["ym"] if months else ""
    care = [r for r in care if r["from"] > first and (not best_yms or r["from"] < best_yms[0])]
    mid = f", a careful {_mons(_span(care[0]['from'], care[0]['to']))}" if care else ""
    if best_txt:
        return f"{start}{mid}, then your best time in {best_txt}."
    return f"{start}{mid}: take one good step at a time."


def _timeline(c, prose):
    p = c.p
    months = {m["ym"]: m for m in p.get("months") or []}
    bt = _best_time(p)
    best_yms = _span(bt["from"], bt["to"]) if bt.get("from") else []
    best_txt = _rng(best_yms)
    segs = (p.get("timeline") or [])[:4]
    tone_col = {"best": GOLD, "good": GOLD, "careful": TERRA}
    head_txt, svg, leg = [], [], []
    for i, s in enumerate(segs):
        cx, x = 39 + 78 * i, 3 + 78 * i
        yms = _span(s["from"], s["to"])
        seg_best = [ym for ym in yms if ym in best_yms]  # best time may span two quarters
        is_best = bool(seg_best)
        lab = _mons([s['from'], s['to']]).upper()
        head_txt.append(f'<text x="{cx}" y="14">{lab}</text>')
        if is_best:
            svg.append(f'<rect x="{x}" y="18" width="72" height="82" rx="8" fill="rgba(201,163,78,.28)" stroke="#B9862E" stroke-width="2"/>')
        elif s.get("tone") == "careful":
            svg.append(f'<rect x="{x}" y="24" width="72" height="70" rx="8" fill="#F7E6DC" stroke="#D9A88C"/>')
        else:
            svg.append(f'<rect x="{x}" y="24" width="72" height="70" rx="8" fill="#F3EAD6" stroke="#C9A34E"/>')
        theme = str(s.get("theme") or "").rstrip(".")
        tl = _wrap(theme, 11, 3)
        y0 = {1: 61, 2: 54, 3: 47}.get(len(tl), 61)
        fill = ' fill="#8A5F14"' if is_best else ""
        svg.append("".join(f'<text x="{cx}" y="{y0 + 14 * j}"{fill} font-family="Fraunces,Georgia,serif" font-size="11" '
                           f'font-weight="600" text-anchor="middle">{E(t)}</text>' for j, t in enumerate(tl)))
        tones = [(months.get(ym) or {}).get("tone", "steady") for ym in yms]
        step = min(17, 56 / max(len(yms) - 1, 1))       # every month gets a dot, up to 6 in the 72px box
        for j, (ym, t) in enumerate(zip(yms, tones)):
            dx = round(cx - step * (len(yms) - 1) / 2 + step * j, 1)
            if t == "best":
                svg.append(f'<circle cx="{dx}" cy="118" r="5.5" fill="#B9862E"/>')
            elif t == "steady":
                svg.append(f'<circle cx="{dx}" cy="118" r="3.5" fill="#FFFDF8" stroke="#B9862E" stroke-width="1.4"/>')
            else:
                svg.append(f'<circle cx="{dx}" cy="118" r="3.5" fill="{tone_col.get(t, GOLD)}"/>')
        if is_best:
            svg.append(f'<text x="{cx}" y="138" font-weight="700" fill="{GREEN}">BEST: {E(_mons(seg_best).upper())}</text>')
        elif len(set(tones)) == 1:
            col = f' fill="{TERRA}"' if tones[0] == "careful" else ""
            svg.append(f'<text x="{cx}" y="138"{col}>{tones[0].upper()}</text>')
        else:
            # one line per tone (at most 3), naming every month of that tone as runs
            by = {}
            for ym, t in zip(yms, tones):
                by.setdefault("good" if t == "best" and len(set(tones)) > 3 else t, []).append(ym)
            for j, (t, tyms) in enumerate(by.items()):
                col = f' fill="{TERRA}"' if t == "careful" else ""
                lab = f"{t.upper()} " + ", ".join(_mons(r) for r in _runs(tyms)).upper()
                fit = ' textLength="74" lengthAdjust="spacingAndGlyphs"' if len(lab) > 13 else ""
                svg.append(f'<text x="{cx}" y="{134 + 11 * j}"{col}{fit}>{E(lab)}</text>')
        default = ", ".join(f"{_mon(ym)} {t}" for ym, t in zip(yms, tones)) + "."
        if is_best:
            default += f" Your best time is {best_txt}."
        # bank/AI value = "<range> · <theme>. <line>"; the bold head already shows range + theme
        line = re.sub(r"^[^.]*·[^.]*\.\s*", "", str(prose.opt(f"timeline.{i + 1}", ""))) or default
        dot = {"careful": TERRA, "best": GOLD}.get("best" if is_best else s.get("tone"), "#C9A34E")
        # a careful or best part names only the summary runs it holds (engine timeline.core), never its steady edges
        core_txt = " and ".join(_mons([r["from"], r["to"]]) for r in (s.get("core") or [s]))
        leg.append(f'<div class="lr"><span class="dot" style="background:{dot}"></span><span class="lt">'
                   f'<b>{core_txt} · {E(theme)}.</b> {E(line)}</span></div>')
    headline = _timeline_headline(p, best_yms, best_txt)
    span = c.meta.get("span") or "Nov 2026 – Oct 2027"
    svg_html = ('<svg viewBox="0 0 313 162" width="100%" style="max-width:300px;margin-top:6px" role="img" '
                'aria-label="Four-part timeline from this Diwali to the next">'
                '<g font-family="Inter,sans-serif" font-size="8.5" font-weight="700" fill="#8A8199" text-anchor="middle">' + "".join(head_txt) + '</g>'
                + "".join(s for s in svg if "<rect" in s)
                + '<g fill="#1B1D2A">' + "".join(s for s in svg if 'font-family="Fraunces' in s) + '</g>'
                + '<line x1="3" y1="118" x2="309" y2="118" stroke="#DCCFB2" stroke-width="1.2"/>'
                + "".join(s for s in svg if "<circle" in s)
                + '<g font-family="Inter,sans-serif" font-size="8" fill="#8A8199" text-anchor="middle">'
                + "".join(s for s in svg if s.startswith("<text") and "Fraunces" not in s) + '</g></svg>')
    callout = ""
    if best_txt:
        callout = ('<div class="callout" style="margin-top:10px;padding:9px 14px"><div class="ch" style="margin-bottom:2px">Your single best time: '
                   f'<span style="font-family:var(--serif);font-size:15px;color:var(--ink);letter-spacing:0;text-transform:none">{E(re.sub(r"^\s*your single best time:\s*", "", str(prose.opt("timeline.best", best_txt)), flags=re.I))}</span></div>'
                   f'<div style="font-size:11px;color:var(--muted);margin-top:4px">Month by month: {_xr("s-1-months", "Your 12 months")} · '
                   f'Cautions: {_xr("s-1-slow", "Months to go slow")}</div></div>')
    return _card(
        f'<div class="exlabel">{DIYA_I}Your months at a glance</div><h2 class="action">{E(headline)}</h2>'
        f'<div class="subtit">From this Diwali to the next ({E(span)})</div><div class="exrule"></div>'
        + svg_html + '<div class="leg" style="margin-top:8px">' + "".join(leg) + "</div>" + callout, "ex", "s-0-6")


def _diya_path(c, prose):
    items = (["luck"] + c.order) if c.luck_first else (c.order + ["luck"])
    svg, leg, nbest = [_DOOR], [], 0
    bt = _best_time(c.p)
    sc = c.p.get("scores") or {}
    top = max([sc.get(a) or 0 for a in c.order] or [0])
    for i, a in enumerate(items[:6]):
        left = i % 2 == 0
        dx, y = (148, 166 + 58 * i) if left else (256, 166 + 58 * i)
        # side label = state pill + at most one short months line (the mock); the read goes in the legend below
        if a == "luck":
            mark = "best" if bt.get("from") else "good"
            run = _span(bt["from"], bt["to"]) if bt.get("from") else []
        else:
            ad = c.areas.get(a) or {}
            mark = _mark(ad, sc.get(a) or 0, top)
            runs = _runs((ad.get("windows") or {}).get(mark) or [])
            run = max(runs, key=len) if runs else []
        word = {"best": "Best", "good": "Good", "careful": "Careful"}[mark]
        lines = [(f"{word}: {_mons(run)}", TERRA if mark == "careful" else GREY)] if run else []
        nbest += mark == "best"
        svg.append(_diya(mark, dx, y, 1.12 if mark == "best" else 1.0))
        tx, anc = ((98 if mark == "best" else 114), "end") if left else (306, "start")
        name = _wrap(c.label(a), 12, 3)
        for j, ln in enumerate(name):
            svg.append(f'<text x="{tx}" y="{y - 14 - 15 * (len(name) - 1 - j)}" text-anchor="{anc}" '
                       f'style="font:600 13.5px Fraunces,Georgia,serif;fill:#1B1D2A">{E(ln)}</text>')
        tw = 70 if mark == "careful" else 62.6
        rx = tx - tw if left else tx
        tag = {"best": (f'fill="{GREEN}"', "#fff", "BEST TIME"),
               "good": ('fill="#FFFDF8" stroke="#B9862E" stroke-width="1.2"', GOLD2, "GOOD TIME"),
               "careful": (f'fill="none" stroke="{TERRA}" stroke-width="1.1" stroke-dasharray="3.2 2.4"', TERRA, "CAREFUL TIME")}[mark]
        svg.append(f'<rect x="{rx:.1f}" y="{y - 9.6:.1f}" width="{tw}" height="14.6" rx="7.3" {tag[0]}/>'
                   f'<text x="{rx + tw / 2:.1f}" y="{y + 0.8:.1f}" text-anchor="middle" style="font:700 7.6px Inter,sans-serif;'
                   f'letter-spacing:.08em;fill:{tag[1]}">{tag[2]}</text>')
        for j, (ln, col) in enumerate(lines):
            svg.append(f'<text x="{tx}" y="{y + 17 + 12.5 * j:.1f}" text-anchor="{anc}" style="font:500 10px Inter,sans-serif;fill:{col}">{E(ln)}</text>')
        # the legend says the mark itself, so drop the bank/AI's own leading "Best time." etc.
        read = re.sub(r"^\s*(best|good|steady|careful) time( first)?\.\s*", "", str(prose.opt(f"glance.{a}") or ""), flags=re.I)
        if not read and a != "luck":
            first = re.split(r"(?<=[.!?])\s", str(prose.opt(f"{a}.read") or ""))[0]
            read = first if len(first.split()) <= 14 else ""
        leg.append(f'<div class="lr" style="font-size:11.5px"><span class="lt"><a class="xr" href="#a-{a}"><b>{E(c.label(a))}</b></a> · '
                   f'{mark.title()} time. {E(read)}</span></div>')
    head = "Six diyas light Lakshmi’s way in" + {0: ".", 1: ", and one burns brightest.", 6: ", and all six burn brightest."}.get(
        nbest, f", and {NUM[nbest]} burn brightest.")
    span = c.meta.get("span") or "Nov 2026 – Oct 2027"
    return _card(
        f'<div class="exlabel">{DIYA_I}Your areas at a glance</div><h2 class="action">{head}</h2>'
        f'<div class="subtit">From this Diwali to the next ({E(span)})</div><div class="exrule"></div>'
        '<svg viewBox="0 0 400 500" width="100%" style="max-width:330px;margin-top:6px" role="img" '
        'aria-label="Six diyas along Lakshmi\'s footprints into the home, one per area">' + "".join(svg) + "</svg>"
        '<div class="leg" style="margin-top:6px;gap:3px">' + "".join(leg) + "</div>", "ex", "s-0-7")


# ---------- Part 1 ----------
def _part1(c, part1_ids):
    rows = "".join(f'<a class="xr" href="#{i}"><span>{E(t)}</span><span>p.@@{i}@@</span></a>' for i, t in part1_ids)
    return _card(
        f'<div class="eyebrow"><svg class="diya-i"><use href="#i-diya"/></svg>Part 1</div><div class="partno">1</div>'
        f'<h2 class="head">From this Diwali to the next</h2><div class="rule"></div>'
        f'<p class="lead" style="text-align:center">Every part of your life, in your order. {E(c.first_line())}</p>'
        f'<div class="mtoc" style="margin-top:16px">{rows}</div>', "part", "part-1", pre=GARLAND)


def _lookback(c, prose):
    lb = c.p.get("lookback") or {}
    good, hard = set(lb.get("good") or []), set(lb.get("hard") or [])
    start = _add(c.meta.get("as_of", "2026-11")[:7], -12)
    yms = [_add(start, i) for i in range(12)]
    rects, letters, years, marks = [], [], [], []
    for i, ym in enumerate(yms):
        x = 11 + 25.5 * i
        col = GREEN if ym in good else TERRA if ym in hard else "#C9BFA6"
        rects.append(f'<rect x="{x}" y="30" width="24" height="56" rx="4" fill="{col}"/>')
        letters.append(f'<text x="{x + 12}" y="62">{_mon(ym)[0]}</text>')
        if i == 0 or _ym(ym)[1] == 1:
            years.append(f'<text x="{x + 1}" y="20">{_ym(ym)[0]}</text>')
            if i:
                marks.append(f'<line x1="{x - 1}" y1="12" x2="{x - 1}" y2="92" stroke="#DCCFB2" stroke-dasharray="2 3"/>')
    for kind, col, txt in (("good", GREEN, prose.opt("lookback.good.label", "The good months")),
                           ("hard", TERRA, prose.opt("lookback.hard.label", "The hard months"))):
        runs = _runs([ym for ym in yms if ym in (good if kind == "good" else hard)])
        if not runs:
            continue
        r = max(runs, key=len)
        x1, x2 = 11 + 25.5 * yms.index(r[0]) + 1, 11 + 25.5 * yms.index(r[-1]) + 23
        marks.append(f'<path d="M{x1} 100 v6 h{x2 - x1} v-6" stroke="{col}" stroke-width="1.2" fill="none"/>')
        for j, ln in enumerate(_wrap(txt, 22, 2)):
            marks.append(f'<text x="{(x1 + x2) / 2:.1f}" y="{121 + 12 * j}" font-size="8.6" font-weight="600" '
                         f'fill="{col}" text-anchor="middle">{E(ln)}</text>')
    allthru = prose.opt("lookback.all")
    if allthru:
        marks.append(f'<line x1="11" y1="150" x2="316" y2="150" stroke="#C9A34E" stroke-width="1.4" stroke-dasharray="4 4"/>'
                     f'<text x="163" y="168" font-size="8.6" font-weight="600" fill="#B9862E" text-anchor="middle">{E(allthru)}</text>')
    svg = ('<svg viewBox="0 0 322 180" width="100%" style="max-width:340px;margin-top:12px" role="img" aria-label="12-month look-back strip">'
           '<g font-family="Inter,sans-serif"><g font-size="8.5" font-weight="700" fill="#8A8199">' + "".join(years) + "</g>"
           + '<g stroke="#FFFFFF" stroke-width="1.5">' + "".join(rects) + "</g>"
           + '<g font-size="10" font-weight="700" fill="#FFFFFF" text-anchor="middle">' + "".join(letters) + "</g>"
           + "".join(marks) + "</g></svg>")
    ng, nh = len(good & set(yms)), len(hard & set(yms))
    head = prose.opt("lookback.headline", f"The months before this Diwali: {_count(ng, 'good month')} "
                                          f"and {_count(nh, 'slower one')}.")
    leg = ""
    if ng:
        leg += (f'<div class="lr"><span class="dot" style="background:{GREEN}"></span><span class="lt"><b>Green: the good months.</b> '
                f'{E(prose.opt("lookback.good.short", "Things tended to move more easily."))}</span></div>')
    if nh:
        leg += (f'<div class="lr"><span class="dot" style="background:{TERRA}"></span><span class="lt"><b>Red: the hard months.</b> '
                f'{E(prose.opt("lookback.hard.short", "Replies came slowly and plans needed more effort."))}</span></div>')
    if ng + nh < 12:
        leg += ('<div class="lr"><span class="dot" style="background:#C9BFA6"></span><span class="lt"><b>Sand: steady months.</b> '
                'Neither push nor pull.</span></div>')
    if allthru:
        leg += ('<div class="lr"><span class="dot" style="background:#C9A34E"></span><span class="lt"><b>Dashed line: all through.</b> '
                f'{E(prose.opt("lookback.all.short", "One slow theme ran under every month."))}</span></div>')
    card1 = _card(
        f'<div class="exlabel">Looking back · From your chart only</div><h2 class="action">{E(head)}</h2>'
        f'<div class="subtit">Diwali {_ym(start)[0]} to Diwali {_ym(start)[0] + 1}, one block per month</div><div class="exrule"></div>'
        + svg + f'<div class="leg" style="margin-top:14px">{leg}</div>', "ex", "s-1-1")

    def pt(kind, icon, warn, pill_svg, title, what, do, watch):
        why = prose.opt(f"lookback.{kind}.why")
        return (f'<div class="pt{" warn" if warn else ""}"><svg class="pi"><use href="#{icon}"/></svg>'
                f'<div class="tx" style="line-height:1.5;font-size:13px"><b>{pill_svg}{title}</b>'
                f'<span>{E(prose.opt(f"lookback.{kind}.what", what))}</span><br>'
                f'<span><b style="display:inline;font:600 12.5px var(--sans);color:var(--green)">Do:</b> {E(prose.opt(f"lookback.{kind}.do", do))} '
                f'<b style="display:inline;font:600 12.5px var(--sans);color:var(--terra)">Watch:</b> {E(prose.opt(f"lookback.{kind}.watch", watch))}</span><br>'
                + (f'<span style="color:var(--muted)"><i>Why:</i> {E(why)}</span><br>' if why else "")
                + f'<span><i>When:</i> the {"green" if kind == "good" else "red"} blocks in your look-back strip&nbsp;·&nbsp;'
                  f'<a class="xr" href="#s-1-1">strip&nbsp;→</a></span></div></div>')

    pts = ""
    if ng:
        pts += pt("good", "i-trend", False, _LB_GOOD, "The good months",
                  "Income and help from others tended to come more easily. If a plan moved forward then, your chart was helping your effort along.",
                  "note what worked in those months; you can use it again.", "expecting every month to feel like that.")
    if nh:
        pts += pt("hard", "i-hourglass", True, _LB_CARE, "The hard months",
                  "Plans may have kept changing, costs may have gone up and answers came slowly. This was about timing, not about you.",
                  "let go of what stayed slow.", "judging yourself by those months.")
    nxt = prose.opt("lookback.from", "From this Diwali, a new set of months begins. Your timeline shows where they lead.")
    card2 = _card(
        '<div class="eyebrow">Looking back · What it means</div><h2 class="head" style="font-size:25px">What those months were about</h2>'
        f'<div class="rule"></div><div class="pts" style="gap:16px">{pts}</div>'
        f'<div class="callout"><div class="ch">From here</div><p>{E(nxt)}</p></div>')
    return [card1, card2]


# ---------- areas ----------
def _area_opener(c, i, a, prose, folded=()):
    ad = c.areas.get(a) or {}
    if a == "career" and folded:  # mock 3C v2 a-career: a business owner's own role, plain card, no picture
        title = _topic_short(c, a, folded[0][1], folded[0][0], prose)
        return _card(f'<div class="eyebrow">{E(c.label(a))}</div><h2 class="head" style="font-size:25px">'
                     f'{E(title[:1].upper() + title[1:])}</h2><div class="rule"></div>'
                     f'<p class="lead" style="font-size:13.5px;margin-top:8px">{E(prose(a + ".opener"))}</p>'
                     + "".join(_topic(c, a, t, n, prose) for n, t in folded), "", "a-" + a)
    eb = AREA_EYEBROW.get(a, "")
    eyebrow = f"{E(c.label(a))}{' · ' + eb if eb else ''}"
    lead = prose(a + ".opener")  # position line (NARR_KEYS contract)
    head = f'<h2 class="action">{E(prose(a + ".headline"))}</h2>'
    span = c.meta.get("span") or "Nov 2026 – Oct 2027"
    if a in ("family", "marriage"):
        expl = (" Each strand below is one part of family life. The flower shows its time." if a == "family" else
                " This section is about your closest relationships. Each strand is one time from this Diwali to the next.")
        pic = _garland(ad.get("picture") or [], "Door garland: one strand per topic, flower shows best, good or careful time")
        leg = (_garland_legend("your best time for this part of family life", "a good time to plan and act",
                               "a careful time: go slowly, it opens later") if a == "family" else
               _garland_legend("your best time for relationships", "a good time for plans and time with loved ones",
                               "a careful time: talk slowly, it opens later"))
        return _card(f'<div class="exlabel">{eyebrow}</div>{head}<div class="subtit">From this Diwali to the next ({E(span)})</div>'
                     f'<div class="exrule"></div><p class="lead" style="font-size:13.5px;margin-top:2px;margin-bottom:8px">{E(lead + expl)}</p>'
                     + pic + leg, "ex", "a-" + a)
    leadp = f'<p class="lead" style="text-align:center;margin-top:4px;font-size:14px;color:var(--gold)">{E(lead)}</p>'
    if a == "money":
        body = (f'<div class="subtit">One diya per month, from this Diwali to the next</div><div class="exrule"></div>{_diya_strip(c, a, True)}'
                f'<div class="leg" style="margin-top:4px">{DIYA_LEG}'
                '<div class="lr"><span class="dot" style="background:#F2C14E;border:1px solid #B9862E"></span><span class="lt"><b>Gold coin: gold '
                'and large buys, our method.</b> Months when Jupiter or Venus pass your money or gains part, or when your current sub-period '
                'planet rules those parts.</span></div><div class="lr"><span class="dot" style="background:#7A2E36;border-radius:2px;height:4px">'
                '</span><span class="lt"><b>Maroon bar: pay down loans.</b> Good months to clear what you owe.</span></div></div>')
    elif a == "business":
        # Dials only from engine facts (areas.business.dials: [{left, right, value 0-1}]); never a renderer-made position.
        dials = "".join(_dial(d) for d in _dials(ad))
        if dials and folded:  # mock 3C v2 a-business: the dials, then topic 1 on the same card
            sub = "Where your chart sits on two dials" if dials.count('class="sp"') == 2 else "Where your chart sits"
            body = (f'<div class="subtit">{sub}</div><div class="exrule"></div>'
                    f'<div class="spec" style="gap:16px;margin-top:12px">{dials}</div>'
                    f'<div style="margin-top:14px">{"".join(_topic(c, a, t, n, prose) for n, t in folded)}</div>')
        elif dials:
            sub = "Where your chart sits on two dials" if dials.count('class="sp"') == 2 else "Where your chart sits"
            body = (f'<div class="subtit">{sub}, and one diya per month</div><div class="exrule"></div>'
                    f'<div class="spec" style="gap:12px;margin-top:10px">{dials}</div>{_diya_strip(c, a)}'
                    f'<div class="leg" style="margin-top:4px">{DIYA_LEG}</div>')
        else:
            body = (f'<div class="subtit">One diya per month, from this Diwali to the next</div><div class="exrule"></div>{_diya_strip(c, a)}'
                    f'<div class="leg" style="margin-top:4px">{DIYA_LEG}</div>')
    else:
        body = (f'<div class="subtit">One diya per month, from this Diwali to the next</div><div class="exrule"></div>{_diya_strip(c, a)}'
                f'<div class="leg" style="margin-top:4px">{DIYA_LEG}</div>')
    return _card(f'<div class="exlabel">{eyebrow}</div>{leadp}{head}{body}', "ex", "a-" + a)


DIAL_TITLE = {("Job", "Business"): "Job or business", ("Alone", "Partner"): "Alone or with a partner"}


def _dials(ad):
    return [d for d in (ad.get("dials") or []) if isinstance(d, dict) and d.get("value") is not None][:2]


def _dial(d):
    l, r = str(d.get("left") or ""), str(d.get("right") or "")
    t = DIAL_TITLE.get((l, r)) or f"{l} or {r.lower()}"
    v = max(0.0, min(1.0, float(d["value"])))
    return (f'<div class="sp"><div class="spt">{E(t)}</div><div class="spl"><span>{E(l)}</span><span>{E(r)}</span></div>'
            f'<div class="spline"><span class="spd" style="left:{v * 100:.0f}%"></span></div></div>')


# ---------- card fit: estimated heights (px at print width) ----------
# Calibrated 2026-10-26 against headless Chrome print layout of 37 real charts (the mock persona, the 28 version charts,
# the 8 overflow charts: 942 topic blocks, 185 reads, 59 callouts): with the character widths below every
# estimate is >= the real block (topic: real - lines = 15.7..52px of padding/margins, so 52 is used), and the
# fullest real topic card stays under FIT_BUDGET. ponytail: a width-class model, not real font metrics; the
# print-fit script (FIT_JS) still shrinks a card that beats the estimate, and test_no_card_overflows catches it.
CARD_BUDGET = 755          # estimated .col height a card may use; real limit FIT_BUDGET (770), estimates run >= real
_CW = {**dict.fromkeys("ijl.,;:'!|", .5), **dict.fromkeys("frt()-’‘", .65), **dict.fromkeys("mwMW", 1.5)}


def _nlines(text, cpl):
    n, cur = 0, 0
    for w in str(text or "").split():
        if cur and cur + 1 + len(w) > cpl:
            n, cur = n + 1, len(w)
        else:
            cur += (1 if cur else 0) + len(w)
    return n + (1 if cur else 0)


def _wlines(text, cap):
    """Lines a text wraps to, by width class (narrow .5, wide 1.5, capitals/digits 1.2, space .4)."""
    n, cur = 0, 0.0
    for w in str(text or "").split():
        x = sum(_CW.get(ch, 1.2 if ch.isupper() or ch.isdigit() else 1.0) for ch in w)
        if cur and cur + .4 + x > cap:
            n, cur = n + 1, x
        else:
            cur += (.4 if cur else 0) + x
    return n + (1 if cur else 0)


def _h_topic(c, a, t, n, prose):
    k = t["key"]
    body = [prose(k + ".what"), "Do: " + _strip_label(prose(k + ".do"), "do"),
            "Watch: " + _strip_label(prose(k + ".watch"), "watch"), "Why: " + _strip_label(prose(k + ".why"), "why"),
            "When: " + prose.opt(k + ".when", WHEN.get(t.get("when"), "steady time")) + " · your 12 months, p.37 →"]
    return 52 + 24.1 * _wlines(_topic_title(c, a, t, n, prose), 31.5) + 18.2 * sum(_wlines(x, 48) for x in body)


def _h_head(title):
    return 17 + 9 + 32 + 27 * (_wlines(title, 27) - 1) + 15      # eyebrow + h2.head + rule


def _h_take(text):
    return 44 + 23 * _wlines(text, 45.5)


def _h_callout(text):
    return 10 + 46 + 19 * _nlines(text, 48)


def _title(shorts):
    if not shorts:
        return ""
    s = [shorts[0][:1].upper() + shorts[0][1:]] + [x[:1].lower() + x[1:] for x in shorts[1:]]
    return s[0] if len(s) == 1 else ", ".join(s[:-1]) + ", and " + s[-1]


def _h_opener(c, a, prose, fold):
    """Height of the opener's own parts above the topics it holds (only openers that hold topics)."""
    if a == "career":
        return 17 + 9 + 32 + 15 + 8 + 22 * _nlines(prose(a + ".opener"), 50)
    return (16 + 4 + 24 * _nlines(prose(a + ".opener"), 40) + 7 + 26 * _nlines(prose(a + ".headline"), 32)
            + 21 + 14 + 132 + 14)                                  # business: subtit, rule, two dials, gap


def _pack(blocks, first_cap, first_budget):
    """Split blocks [(kind, html, h, short)] into cards, in order. Card 0 is the opener when first_cap is
    given: it takes up to first_cap topics within first_budget (then the tail when every topic fits).
    The rest go to _split."""
    if first_cap is None:
        return _split(blocks)
    opener, used = [], 0.0
    for blk in blocks:
        ntop = sum(b[0] == "topic" for b in opener)
        if not ((ntop < first_cap if blk[0] == "topic" else ntop == first_cap) and used + blk[2] <= first_budget):
            break
        opener.append(blk)
        used += blk[2]
    return [opener] + _split(blocks[len(opener):])


# mock 3C v2: a card holding 3 topics sets them tighter (margin 8px, padding 9px 13px): 6px less each
_WIN_STYLE, _WIN_DENSE, DENSE_SAVE = "margin-top:10px;padding:11px 14px", "margin-top:8px;padding:9px 13px", 6


def _dense(block_html):
    return block_html.replace(_WIN_STYLE, _WIN_DENSE, 1)


def _split(blocks):
    """Fewest cards, then the most even fill (the fullest card as low as it can be), over every in-order
    split. A card fits when its blocks plus its head (which names its own topics) stay within CARD_BUDGET;
    every card holds a topic or the Manglik box, so a callout or the read never stands alone. A block too
    tall for any card still gets one (the print fit shrinks it). ponytail: exact DP over <= ~12 blocks."""
    n, memo = len(blocks), {}

    def fill(cd):
        nt = sum(b[0] == "topic" for b in cd)
        return (sum(b[2] for b in cd) - (DENSE_SAVE * nt if nt >= 3 else 0)
                + _h_head(_title([b[3] for b in cd if b[0] == "topic"]) or "x"))

    def best(i):                                    # -> ((over, cards, fullest), cut points)
        if i == n:
            return (0, 0, 0.0), ()
        if i not in memo:
            opts = []
            for j in range(i + 1, n + 1):
                cd = blocks[i:j]
                if not any(b[0] in ("topic", "box") for b in cd):
                    continue
                f = fill(cd)
                (ov, k, mx), cuts = best(j)
                opts.append(((ov + (f > CARD_BUDGET), k + 1, max(mx, f)), (j,) + cuts))
            memo[i] = min(opts, default=((n, n, 0.0), (n,)))
        return memo[i]

    cuts, out, i = best(0)[1], [], 0
    for j in cuts:
        out.append(blocks[i:j])
        i = j
    return out


def _area_cards(c, i, a, prose):
    ad = c.areas.get(a) or {}
    topics = [(n, t) for n, t in enumerate(ad.get("topics") or [], 1) if t.get("key") != "marriage.t5"]
    blocks = [("topic", _topic(c, a, t, n, prose), _h_topic(c, a, t, n, prose), _topic_short(c, a, t, n, prose))
              for n, t in topics]
    if a == "marriage":
        helpline = prose.opt("note.helpline", "If a conflict at home feels serious, please talk to someone you trust or a trained helper.")
        helps = prose.opt("marriage.helps")
        if helps:
            blocks.append(("tail", f'<div class="callout" style="margin-top:10px"><div class="ch">What helps most</div><p>{E(helps)}</p></div>',
                           _h_callout(helps), None))
        blocks.append(("tail", f'<div class="wd" style="margin-top:10px;font-size:12px;color:var(--muted);text-align:left;width:100%">{E(helpline)}</div>',
                       10 + 18.2 * _nlines(helpline, 56), None))
        blocks.append(("box", _manglik(c), 250 + 18.2 * _nlines((c.p.get("marriage_extra") or {}).get("manglik", {}).get("reason") or "", 50), None))
    elif a == "family" and (ad.get("windows") or {}).get("careful"):
        talks = prose.opt("family.talks")
        if talks:  # mock 3C v2: careful-time callout after the last family topic
            blocks.append(("tail", f'<div class="callout terra" style="margin-top:10px"><div class="ch">Careful time for family talks</div>'
                                   f'<p>{E(talks)} <a class="xr" href="#s-1-months">your 12 months, p.@@s-1-months@@ →</a></p></div>',
                           _h_callout(talks + " your 12 months, p.37 →"), None))
    read = prose(a + ".read")
    blocks.append(("tail", f'<div class="take" style="margin-top:14px;padding-top:10px"><b>The read</b>{E(read)}</div>', _h_take(read), None))
    # mock 3C v2: topic 1 sits on the Business opener (under the dials); a business owner's Career opener is a
    # plain card holding topics 1-2. They hold fewer when the topics are long. The opener is card 1 of the count.
    fold = 1 if a == "business" and _dials(ad) and topics else \
        2 if a == "career" and c.meta.get("work_type") == "business" and len(topics) >= 2 else 0
    packed = _pack(blocks, fold, CARD_BUDGET - _h_opener(c, a, prose, fold)) if fold else None
    if not packed or not any(b[0] == "topic" for b in packed[0]):  # no fold, or topic 1 too long for the opener
        packed = [[]] + _pack(blocks, None, 0)
    folded = topics[:sum(b[0] == "topic" for b in packed[0])]
    cards = [_area_opener(c, i, a, prose, folded)]
    if folded and any(b[0] != "topic" for b in packed[0]):    # every topic sat on the opener: the tail closes it
        tail = "".join(b[1] for b in packed[0] if b[0] != "topic")
        cards[0] = cards[0].replace('</div><a class="tocl"', tail + '</div><a class="tocl"', 1)
    rest = packed[1:]
    total = len(rest) + (1 if folded else 0)
    for j, cd in enumerate(rest):
        shorts = [b[3] for b in cd if b[0] == "topic"]
        title = _title(shorts) or ("The Manglik facts" if a == "marriage" and any("Manglik" in b[1] for b in cd) else c.label(a))
        cards.append(_card(f'<div class="eyebrow">{E(c.label(a))} · {j + 1 + (total - len(rest))} of {total}</div>'
                           f'<h2 class="head" style="font-size:25px">{E(title)}</h2><div class="rule"></div>'
                           + "".join(_dense(b[1]) if len(shorts) >= 3 else b[1] for b in cd)))
    return cards


# ---------- contents + assembler ----------
_ID = re.compile(r'<section class="[^"]*"[^>]*\bid="([^"]+)"')
_TOC_ATTR = re.compile(r'<section [^>]*\bdata-toc="([^"]+)"')


def _cid(card):
    m = _ID.match(card)
    return m.group(1) if m else None


def _row(cid, title, head=False):
    return f'<a class="xr{" h" if head else ""}" href="#{cid}"><span>{E(title)}</span><span>p.@@{cid}@@</span></a>'


def _contents(rows1, rows2):
    c1 = _card(f'<div class="eyebrow">{DIYA_I}What\'s inside</div><h2 class="head">Your report, page by page</h2><div class="rule"></div>'
               '<p class="fine" style="text-align:center;margin-top:6px">Tap any line to jump to it; tap “Contents” at the foot of a page to come back.</p>'
               f'<div class="mtoc dense">{"".join(rows1)}</div>', "", "contents")
    c2 = _card(f'<div class="eyebrow">{DIYA_I}What\'s inside · 2 of 2</div><h2 class="head">Your report, page by page</h2><div class="rule"></div>'
               f'<div class="mtoc dense">{"".join(rows2)}</div>')
    return [c1, c2]


def _assemble(cards):
    """Number cards, fill p.@@id@@, unwrap links to cards that do not exist."""
    pg = {}
    for n, card in enumerate(cards, 1):
        cid = _cid(card)
        if cid:
            pg.setdefault(cid, n)
    html = "\n".join(cards)

    def link(m):
        if m.group(1) in pg:
            return m.group(0)
        return re.sub(r",? ?p\.@@[\w-]+@@", "", m.group(2))
    html = re.sub(r'<a [^>]*href="#([^"]+)"[^>]*>(.*?)</a>', link, html, flags=re.S)
    html = re.sub(r"p\.@@([\w-]+)@@", lambda m: f"p.{pg[m.group(1)]:02d}" if m.group(1) in pg else "", html)
    return html


def _with_tocl(card):
    k = card.rfind('<div class="pgn">')
    return card if 'class="tocl"' in card or k < 0 else card[:k] + TOCL + card[k:]


def _count(n, word):
    return f"{NUM[n] if n < len(NUM) else n} {word}{'' if n == 1 else 's'}"


def render_diwali(payload):
    import diwali_report_back  # written in parallel; imported lazily
    c, prose = _Ctx(payload), _Prose(payload)
    gift_on = bool((c.meta.get("gift") or {}).get("on"))

    front = [_cover(c)] + ([_gift(c, prose)] if gift_on else []) + [
        _note(c, prose), _howto(c, prose), _answers(c, prose), _timeline(c, prose), _diya_path(c, prose)]
    lookback = _lookback(c, prose)
    areas = []
    for i, a in enumerate(c.order):
        areas += _area_cards(c, i, a, prose)

    back = list(diwali_report_back.cards_back(payload, prose))
    back = [_with_tocl(b) for b in back]
    luck = []
    if c.luck_first and any(_cid(b) == "a-luck" for b in back):
        k = next(j for j, b in enumerate(back) if _cid(b) == "a-luck")
        e = next((j for j in range(k + 1, len(back)) if _cid(back[j])), len(back))
        luck, back = back[k:e], back[:k] + back[e:]
    back_ids = {_cid(b): b for b in back if _cid(b)}
    if luck:
        back_ids["a-luck"] = luck[0]

    def title(cid):
        m = _TOC_ATTR.match(back_ids.get(cid, ""))
        return m.group(1) if m else TOC_TITLES.get(cid, cid)

    seq = (["a-luck"] if luck else []) + ["a-" + a for a in c.order] + ([] if luck else ["a-luck"]) + PART1_AFTER
    seq = [i for i in seq if i in back_ids or (i.startswith("a-") and i[2:] in c.order)]
    p1 = [("s-1-1", "The months before this Diwali")] + [
        (i, "Better luck" if i == "a-luck" else c.label(i[2:]) if i.startswith("a-") else title(i)) for i in seq]
    part1 = _part1(c, p1)

    gift_title = "A Diwali gift"
    g = c.meta.get("gift") or {}
    if gift_on:
        gift_title = f"A Diwali gift from {g['giver_name'].strip()}" if (g.get("giver_name") or "").strip() else "A Diwali gift for you"
    first_front = "s-0-2" if gift_on else "s-0-3"
    rows1 = [_row(first_front, "Front pages", True)] + ([_row("s-0-2", gift_title)] if gift_on else []) + [
        _row("s-0-3", "A note for you"), _row("s-0-4", "How to read this report"), _row("s-0-5", "Your Diwali answers"),
        _row("s-0-6", "Your months at a glance"), _row("s-0-7", "Your areas at a glance"),
        _row("part-1", "Part 1 · From this Diwali to the next", True),
        _row("s-1-1", "Looking back: the months before this Diwali")]
    rows1 += [_row(i, c.label(i[2:]) if i.startswith("a-") and i != "a-luck" else title(i)) for i in seq]
    rows2, used = [], set(seq) | {"a-luck"}
    for b in back:
        cid = _cid(b)
        if not cid or cid in used:
            continue
        if cid in TOC_HEADS:
            rows2.append(_row(cid, TOC_HEADS[cid], True))
            if cid == "part-2":
                continue
        rows2.append(_row(cid, title(cid)))

    cards = front + _contents(rows1, rows2) + [part1] + lookback + luck + areas + back
    name = c.meta.get("name") or ""
    return ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Diwali Wealth &amp; Prosperity Report · {E(name)}</title>{FONTS_LINK}'
            f'<style>{DIWALI_CSS}\n{CHROME_CSS}</style></head><body>{DIWALI_DEFS}{_M31_DEFS}\n'
            + _assemble(cards) + "\n" + FIT_JS + "</body></html>")


# ---------- static kit SVG, copied verbatim from docs/diwali/mock/kit-3c ----------
_M31_DEFS = '<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs><radialGradient id="m31halo"><stop offset="0" stop-color="#F2C14E" stop-opacity=".85"/><stop offset=".6" stop-color="#F2C14E" stop-opacity=".45"/><stop offset="1" stop-color="#F2C14E" stop-opacity="0"/></radialGradient><linearGradient id="m31lit" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F8D978"/><stop offset="1" stop-color="#E39B2B"/></linearGradient><symbol id="m31-dbest" viewBox="-40 -54 80 80" overflow="visible"><circle cx="0" cy="-14" r="36" fill="url(#m31halo)"/><line x1="0.0" y1="-39.0" x2="0.0" y2="-50.0" stroke="#B9862E" stroke-width="2" stroke-linecap="round"/><line x1="12.5" y1="-35.7" x2="18.0" y2="-45.2" stroke="#B9862E" stroke-width="2" stroke-linecap="round"/><line x1="21.7" y1="-26.5" x2="31.2" y2="-32.0" stroke="#B9862E" stroke-width="2" stroke-linecap="round"/><line x1="25.0" y1="-14.0" x2="36.0" y2="-14.0" stroke="#B9862E" stroke-width="2" stroke-linecap="round"/><line x1="-25.0" y1="-14.0" x2="-36.0" y2="-14.0" stroke="#B9862E" stroke-width="2" stroke-linecap="round"/><line x1="-21.7" y1="-26.5" x2="-31.2" y2="-32.0" stroke="#B9862E" stroke-width="2" stroke-linecap="round"/><line x1="-12.5" y1="-35.7" x2="-18.0" y2="-45.2" stroke="#B9862E" stroke-width="2" stroke-linecap="round"/><path d="M0 -31.0 C14.3 -12.3 12.9 3 0 3 C-12.9 3 -14.3 -12.3 0 -31.0Z" fill="#E39B2B" stroke="#D9692A" stroke-width=".8"/><path d="M0 -14.7 C5.7 -5.2 5.0 3 0 3 C-5.0 3 -5.7 -5.2 0 -14.7Z" fill="#FFF3C2"/><path d="M-24 0 Q0 24 24 0 Q0 5 -24 0Z" fill="url(#m31lit)" stroke="#B9862E" stroke-width="1.9" stroke-linejoin="round" /><path d="M-13 7 Q0 13 13 7" fill="none" stroke="#7A2E36" stroke-width="1" stroke-dasharray="1.5 2.5"/></symbol><symbol id="m31-dgood" viewBox="-40 -54 80 80" overflow="visible"><circle cx="0" cy="-6" r="17" fill="none" stroke="#B9862E" stroke-width="1.3"/><path d="M0 -15.0 C7.6 -5.1 6.8 3 0 3 C-6.8 3 -7.6 -5.1 0 -15.0Z" fill="#E39B2B" stroke="#D9692A" stroke-width=".8"/><path d="M0 -6.4 C3.0 -1.3 2.6 3 0 3 C-2.6 3 -3.0 -1.3 0 -6.4Z" fill="#FFF3C2"/><path d="M-24 0 Q0 24 24 0 Q0 5 -24 0Z" fill="#FBF4E7" stroke="#B9862E" stroke-width="1.5" stroke-linejoin="round" /><path d="M-13 7 Q0 13 13 7" fill="none" stroke="#C9A34E" stroke-width="1" stroke-dasharray="1.5 2.5"/></symbol><symbol id="m31-dcare" viewBox="-40 -54 80 80" overflow="visible"><circle cx="0" cy="0" r="1.8" fill="#9C907A"/><path d="M0 -3 q-3 -4 0 -8 q3 -4 0 -8" fill="none" stroke="#9C907A" stroke-width="1" stroke-linecap="round" opacity=".8"/><path d="M-24 0 Q0 24 24 0 Q0 5 -24 0Z" fill="#E9E3D6" stroke="#9C907A" stroke-width="1.5" stroke-linejoin="round" stroke-dasharray="3.2 2.4"/><path d="M-13 7 Q0 13 13 7" fill="none" stroke="#9C907A" stroke-width="1" stroke-dasharray="1.5 2.5"/></symbol><symbol id="m31-foot" viewBox="-8 -20 16 22" overflow="visible"><path d="M0 0c-3.4 0-4.6-3.6-4.3-7.6c.4-4.4 2.2-6.9 4.6-6.9c2.5 0 3.9 2.6 3.7 6.8C3.8-3.5 3 0 0 0z"/><circle cx="-2.6" cy="-16.6" r="1.4"/><circle cx="-.3" cy="-17.4" r="1.2"/><circle cx="1.7" cy="-17" r="1.1"/><circle cx="3.3" cy="-15.9" r="1"/><circle cx="4.5" cy="-14.3" r=".9"/></symbol><symbol id="m31-tbest" viewBox="0 0 92 16"><rect x="13.4" y="1" width="65.3" height="14.6" rx="7.3" fill="#3E7D5A"/><text x="46" y="11.4" text-anchor="middle" style="font:700 8px Inter,sans-serif;letter-spacing:.08em;fill:#fff">BEST TIME</text></symbol><symbol id="m31-tgood" viewBox="0 0 92 16"><rect x="13.4" y="1" width="65.3" height="14.6" rx="7.3" fill="#FFFDF8" stroke="#B9862E" stroke-width="1.2"/><text x="46" y="11.4" text-anchor="middle" style="font:700 8px Inter,sans-serif;letter-spacing:.08em;fill:#8A6420">GOOD TIME</text></symbol><symbol id="m31-tcare" viewBox="0 0 92 16"><rect x="4.5" y="1" width="83" height="14.6" rx="7.3" fill="none" stroke="#B4572B" stroke-width="1.1" stroke-dasharray="3.2 2.4"/><text x="46" y="11.4" text-anchor="middle" style="font:700 8px Inter,sans-serif;letter-spacing:.08em;fill:#B4572B">CAREFUL TIME</text></symbol><symbol id="m31-wgood" viewBox="0 0 64 18"><rect x="1" y="1" width="62" height="16" rx="8" fill="#FFFDF8" stroke="#3E7D5A" stroke-width="1.2"/><text x="32" y="12.6" text-anchor="middle" style="font:700 9px Inter,sans-serif;letter-spacing:.1em;fill:#3E7D5A">GOOD</text></symbol><symbol id="m31-wbest" viewBox="0 0 64 18"><rect x="1" y="1" width="62" height="16" rx="8" fill="#3E7D5A"/><text x="32" y="12.6" text-anchor="middle" style="font:700 9px Inter,sans-serif;letter-spacing:.1em;fill:#fff">BEST</text></symbol><symbol id="m31-wsteady" viewBox="0 0 64 18"><rect x="1" y="1" width="62" height="16" rx="8" fill="#FFFDF8" stroke="#B9862E" stroke-width="1.2"/><text x="32" y="12.6" text-anchor="middle" style="font:700 9px Inter,sans-serif;letter-spacing:.1em;fill:#8A6420">STEADY</text></symbol><symbol id="m31-wcare" viewBox="0 0 64 18"><rect x="1" y="1" width="62" height="16" rx="8" fill="none" stroke="#B4572B" stroke-width="1.1" stroke-dasharray="3.2 2.4"/><text x="32" y="12.6" text-anchor="middle" style="font:700 9px Inter,sans-serif;letter-spacing:.1em;fill:#B4572B">CAREFUL</text></symbol></defs></svg>'
_D_BEST = '<circle cx="0" cy="-14" r="36" fill="url(#m31halo)"/><line x1="0.0" y1="-39.0" x2="0.0" y2="-50.0" stroke="#B9862E" stroke-width="2" stroke-linecap="round"/><line x1="12.5" y1="-35.7" x2="18.0" y2="-45.2" stroke="#B9862E" stroke-width="2" stroke-linecap="round"/><line x1="21.7" y1="-26.5" x2="31.2" y2="-32.0" stroke="#B9862E" stroke-width="2" stroke-linecap="round"/><line x1="25.0" y1="-14.0" x2="36.0" y2="-14.0" stroke="#B9862E" stroke-width="2" stroke-linecap="round"/><line x1="-25.0" y1="-14.0" x2="-36.0" y2="-14.0" stroke="#B9862E" stroke-width="2" stroke-linecap="round"/><line x1="-21.7" y1="-26.5" x2="-31.2" y2="-32.0" stroke="#B9862E" stroke-width="2" stroke-linecap="round"/><line x1="-12.5" y1="-35.7" x2="-18.0" y2="-45.2" stroke="#B9862E" stroke-width="2" stroke-linecap="round"/><path d="M0 -31.0 C14.3 -12.3 12.9 3 0 3 C-12.9 3 -14.3 -12.3 0 -31.0Z" fill="#E39B2B" stroke="#D9692A" stroke-width=".8"/><path d="M0 -14.7 C5.7 -5.2 5.0 3 0 3 C-5.0 3 -5.7 -5.2 0 -14.7Z" fill="#FFF3C2"/><path d="M-24 0 Q0 24 24 0 Q0 5 -24 0Z" fill="url(#m31lit)" stroke="#B9862E" stroke-width="1.9" stroke-linejoin="round" /><path d="M-13 7 Q0 13 13 7" fill="none" stroke="#7A2E36" stroke-width="1" stroke-dasharray="1.5 2.5"/>'
_D_GOOD = '<circle cx="0" cy="-6" r="17" fill="none" stroke="#B9862E" stroke-width="1.3"/><path d="M0 -15.0 C7.6 -5.1 6.8 3 0 3 C-6.8 3 -7.6 -5.1 0 -15.0Z" fill="#E39B2B" stroke="#D9692A" stroke-width=".8"/><path d="M0 -6.4 C3.0 -1.3 2.6 3 0 3 C-2.6 3 -3.0 -1.3 0 -6.4Z" fill="#FFF3C2"/><path d="M-24 0 Q0 24 24 0 Q0 5 -24 0Z" fill="#FBF4E7" stroke="#B9862E" stroke-width="1.5" stroke-linejoin="round" /><path d="M-13 7 Q0 13 13 7" fill="none" stroke="#C9A34E" stroke-width="1" stroke-dasharray="1.5 2.5"/>'
_D_CARE = '<circle cx="0" cy="0" r="1.8" fill="#9C907A"/><path d="M0 -3 q-3 -4 0 -8 q3 -4 0 -8" fill="none" stroke="#9C907A" stroke-width="1" stroke-linecap="round" opacity=".8"/><path d="M-24 0 Q0 24 24 0 Q0 5 -24 0Z" fill="#E9E3D6" stroke="#9C907A" stroke-width="1.5" stroke-linejoin="round" stroke-dasharray="3.2 2.4"/><path d="M-13 7 Q0 13 13 7" fill="none" stroke="#9C907A" stroke-width="1" stroke-dasharray="1.5 2.5"/>'
_MITHAI = '<svg viewBox="0 0 370 166" width="100%" style="max-width:250px;display:block;margin:18px auto 0" aria-hidden="true"><path d="M30 46 L48 8 L322 8 L340 46Z" fill="#F1E2C2" stroke="#B9862E" stroke-width="1.4" stroke-linejoin="round"/><path d="M44 40 L58 14 L312 14 L326 40" fill="none" stroke="#C9A34E" stroke-width=".8" stroke-dasharray="1 3"/><text x="185" y="32" text-anchor="middle" style="font:italic 500 13px Fraunces,Georgia,serif;fill:#7A2E36">Shubh Deepavali</text><rect x="8" y="44" width="354" height="118" rx="10" fill="#EAD7B0" stroke="#B9862E" stroke-width="1.6"/><rect x="20" y="54" width="330" height="100" rx="4" fill="#FBF4E7" stroke="#C9A34E" stroke-width="1"/><line x1="130" y1="54" x2="130" y2="154" stroke="#C9A34E" stroke-width="1"/><line x1="240" y1="54" x2="240" y2="154" stroke="#C9A34E" stroke-width="1"/><path d="M111.0 106 Q115.6 111.8 109.5 116.1 Q112.3 123.0 105.3 125.5 Q106.0 132.8 98.6 133.2 Q97.2 140.5 90.0 138.7 Q86.6 145.3 80.1 141.6 Q75.0 147.0 69.9 141.6 Q63.4 145.3 60.0 138.7 Q52.8 140.5 51.4 133.2 Q44.0 132.8 44.7 125.5 Q37.7 123.0 40.5 116.1 Q34.4 111.8 39.0 106.0 Q34.4 100.2 40.5 95.9 Q37.7 89.0 44.7 86.5 Q44.0 79.2 51.4 78.8 Q52.8 71.5 60.0 73.3 Q63.4 66.7 69.9 70.4 Q75.0 65.0 80.1 70.4 Q86.6 66.7 90.0 73.3 Q97.2 71.5 98.6 78.8 Q106.0 79.2 105.3 86.5 Q112.3 89.0 109.5 95.9 Q115.6 100.2 111.0 106.0Z" fill="#FFFDF8" stroke="#C9A34E" stroke-width="1"/><circle cx="75.0" cy="106" r="29" fill="none" stroke="#EADFC6" stroke-width="1"/><g transform="translate(75.0 106) scale(1.0)"><path d="M0 -21 L28 0 L0 21 L-28 0Z" fill="#EFE4CF" stroke="#B9A07A" stroke-width="1.3" stroke-linejoin="round"/><path d="M0 -14 L19 0 L0 14 L-19 0Z" fill="#FAF8F3" opacity=".9"/><path d="M-6 -6 L6 -6 M-3 2 L9 2 M-10 6 L2 6" stroke="#D8D2C6" stroke-width=".8"/><ellipse cx="-8" cy="-5" rx="6" ry="3.2" transform="rotate(-30 -8 -5)" fill="#fff" opacity="0.8"/></g><path d="M104.0 76 Q104.0 82 110.0 82 Q104.0 82 104.0 88 Q104.0 82 98.0 82 Q104.0 82 104.0 76Z" fill="#F2C14E" stroke="#B9862E" stroke-width=".6"/><path d="M45.0 88 Q45.0 92 49.0 92 Q45.0 92 45.0 96 Q45.0 92 41.0 92 Q45.0 92 45.0 88Z" fill="#F2C14E" stroke="#B9862E" stroke-width=".6"/><path d="M221.0 106 Q225.6 111.8 219.5 116.1 Q222.3 123.0 215.3 125.5 Q216.0 132.8 208.6 133.2 Q207.2 140.5 200.0 138.7 Q196.6 145.3 190.1 141.6 Q185.0 147.0 179.9 141.6 Q173.4 145.3 170.0 138.7 Q162.8 140.5 161.4 133.2 Q154.0 132.8 154.7 125.5 Q147.7 123.0 150.5 116.1 Q144.4 111.8 149.0 106.0 Q144.4 100.2 150.5 95.9 Q147.7 89.0 154.7 86.5 Q154.0 79.2 161.4 78.8 Q162.8 71.5 170.0 73.3 Q173.4 66.7 179.9 70.4 Q185.0 65.0 190.1 70.4 Q196.6 66.7 200.0 73.3 Q207.2 71.5 208.6 78.8 Q216.0 79.2 215.3 86.5 Q222.3 89.0 219.5 95.9 Q225.6 100.2 221.0 106.0Z" fill="#FFFDF8" stroke="#C9A34E" stroke-width="1"/><circle cx="185.0" cy="106" r="29" fill="none" stroke="#EADFC6" stroke-width="1"/><g transform="translate(185.0 106) scale(1.0)"><circle r="22" fill="#F4B740" stroke="#C98A22" stroke-width="1.3"/><circle cx="-9" cy="4" r="1.5" fill="#D98A1E"/><circle cx="-2" cy="-3" r="1.5" fill="#D98A1E"/><circle cx="6" cy="7" r="1.5" fill="#D98A1E"/><circle cx="10" cy="-4" r="1.5" fill="#D98A1E"/><circle cx="-4" cy="12" r="1.5" fill="#D98A1E"/><circle cx="3" cy="15" r="1.5" fill="#D98A1E"/><circle cx="-13" cy="-6" r="1.5" fill="#D98A1E"/><circle cx="12" cy="9" r="1.5" fill="#D98A1E"/><circle cx="0" cy="5" r="1.5" fill="#D98A1E"/><circle cx="-8" cy="-14" r="1.5" fill="#D98A1E"/><circle cx="7" cy="-13" r="1.5" fill="#D98A1E"/><ellipse cx="-7" cy="-9" rx="6" ry="3.2" transform="rotate(-30 -7 -9)" fill="#fff" opacity="0.8"/></g><path d="M214.0 76 Q214.0 82 220.0 82 Q214.0 82 214.0 88 Q214.0 82 208.0 82 Q214.0 82 214.0 76Z" fill="#F2C14E" stroke="#B9862E" stroke-width=".6"/><path d="M155.0 88 Q155.0 92 159.0 92 Q155.0 92 155.0 96 Q155.0 92 151.0 92 Q155.0 92 155.0 88Z" fill="#F2C14E" stroke="#B9862E" stroke-width=".6"/><path d="M331.0 106 Q335.6 111.8 329.5 116.1 Q332.3 123.0 325.3 125.5 Q326.0 132.8 318.6 133.2 Q317.2 140.5 310.0 138.7 Q306.6 145.3 300.1 141.6 Q295.0 147.0 289.9 141.6 Q283.4 145.3 280.0 138.7 Q272.8 140.5 271.4 133.2 Q264.0 132.8 264.7 125.5 Q257.7 123.0 260.5 116.1 Q254.4 111.8 259.0 106.0 Q254.4 100.2 260.5 95.9 Q257.7 89.0 264.7 86.5 Q264.0 79.2 271.4 78.8 Q272.8 71.5 280.0 73.3 Q283.4 66.7 289.9 70.4 Q295.0 65.0 300.1 70.4 Q306.6 66.7 310.0 73.3 Q317.2 71.5 318.6 78.8 Q326.0 79.2 325.3 86.5 Q332.3 89.0 329.5 95.9 Q335.6 100.2 331.0 106.0Z" fill="#FFFDF8" stroke="#C9A34E" stroke-width="1"/><circle cx="295.0" cy="106" r="29" fill="none" stroke="#EADFC6" stroke-width="1"/><g transform="translate(295.0 106) scale(1.0)"><rect x="-19" y="-19" width="38" height="38" rx="4" fill="#F4EBD8" stroke="#C9A877" stroke-width="1.3"/><ellipse cx="-6" cy="-5" rx="4" ry="1.8" transform="rotate(-25 -6 -5)" fill="#7FA35A"/><ellipse cx="6" cy="4" rx="4" ry="1.8" transform="rotate(30 6 4)" fill="#7FA35A"/><ellipse cx="-3" cy="9" rx="3.6" ry="1.6" transform="rotate(-10 -3 9)" fill="#7FA35A"/><ellipse cx="-9" cy="-11" rx="6" ry="3.2" transform="rotate(-30 -9 -11)" fill="#fff" opacity="0.8"/></g><path d="M324.0 76 Q324.0 82 330.0 82 Q324.0 82 324.0 88 Q324.0 82 318.0 82 Q324.0 82 324.0 76Z" fill="#F2C14E" stroke="#B9862E" stroke-width=".6"/><path d="M265.0 88 Q265.0 92 269.0 92 Q265.0 92 265.0 96 Q265.0 92 261.0 92 Q265.0 92 265.0 88Z" fill="#F2C14E" stroke="#B9862E" stroke-width=".6"/></svg>'
_CONSTEL = '<svg class="constel" viewBox="1000 0 230 80" fill="none" style="width:min(210px,72%);margin:16px auto 4px;display:block" stroke-linecap="round" stroke-linejoin="round">\n  <g transform="translate(1000 0)">\n  <polyline points="14,66 60,54 104,42 150,31 210,13" stroke="currentColor" stroke-width="1.1" stroke-dasharray="2 5" opacity=".5"/>\n  <circle cx="14" cy="66" r="3" fill="currentColor"/><circle cx="60" cy="54" r="3" fill="currentColor"/><circle cx="104" cy="42" r="3" fill="currentColor"/>\n  <g transform="translate(150 31)" stroke="currentColor" stroke-width="1.4"><path d="M0 -7V7M-7 0H7M-5 -5l10 10M5 -5l-10 10"/></g>\n  <g transform="translate(210 13)"><path d="M0 -9V9M-9 0H9M-6 -6l12 12M6 -6l-12 12" stroke="currentColor" stroke-width="1.6"/><circle r="3.6" fill="var(--sand)" stroke="currentColor" stroke-width="1.5"/></g>\n  </g>\n</svg>'
_NOTE_TOP = '<svg class="fan nftop" viewBox="0 0 54 30" fill="none"><rect x="6" y="13" width="42" height="20" fill="#FBF7EE"/><g stroke="currentColor" stroke-width="1" stroke-linecap="round"><path d="M27 27 L12 15M27 27 L18 12M27 27 L27 9M27 27 L36 12M27 27 L42 15"/><path d="M12 15 A19 19 0 0 1 42 15"/></g></svg>\n    <svg class="crn ctl" viewBox="0 0 13 13"><path d="M6.5 0 L13 6.5 L6.5 13 L0 6.5 Z" fill="currentColor"/></svg>\n    <svg class="crn ctr" viewBox="0 0 13 13"><path d="M6.5 0 L13 6.5 L6.5 13 L0 6.5 Z" fill="currentColor"/></svg>\n    <svg class="crn cbl" viewBox="0 0 13 13"><path d="M6.5 0 L13 6.5 L6.5 13 L0 6.5 Z" fill="currentColor"/></svg>\n    <svg class="crn cbr" viewBox="0 0 13 13"><path d="M6.5 0 L13 6.5 L6.5 13 L0 6.5 Z" fill="currentColor"/></svg>'
_NOTE_BOT = '<svg class="fan nfbot" viewBox="0 0 54 30" fill="none"><rect x="6" y="13" width="42" height="20" fill="#FBF7EE"/><g stroke="currentColor" stroke-width="1" stroke-linecap="round"><path d="M27 27 L12 15M27 27 L18 12M27 27 L27 9M27 27 L36 12M27 27 L42 15"/><path d="M12 15 A19 19 0 0 1 42 15"/></g></svg>'
_DOOR = '<path d="M155 104 V40 Q155 6 200 6 Q245 6 245 40 V104" fill="#FBEFD3" stroke="#B9862E" stroke-width="1.6"/><path d="M155 104 V42 L171 48 V104Z M245 104 V42 L229 48 V104Z" fill="#EADBBE" stroke="#B9862E" stroke-width="1.2" stroke-linejoin="round"/><path d="M155 36 Q177 48 200 36 Q223 48 245 36" fill="none" stroke="#3E7D5A" stroke-width="1.1"/><circle cx="166" cy="41" r="3" fill="#E39B2B"/><circle cx="177" cy="43" r="3" fill="#E39B2B"/><circle cx="189" cy="40" r="3" fill="#E39B2B"/><circle cx="211" cy="40" r="3" fill="#E39B2B"/><circle cx="223" cy="43" r="3" fill="#E39B2B"/><circle cx="234" cy="41" r="3" fill="#E39B2B"/><path d="M141 104 H259 L267 114 H133Z" fill="#FBF4E7" stroke="#B9862E" stroke-width="1.4" stroke-linejoin="round"/><g transform="translate(193 494) scale(-0.95 0.95)" fill="#7A2E36" opacity=".55"><path d="M0 0c-3.4 0-4.6-3.6-4.3-7.6c.4-4.4 2.2-6.9 4.6-6.9c2.5 0 3.9 2.6 3.7 6.8C3.8-3.5 3 0 0 0z"/><circle cx="-2.6" cy="-16.6" r="1.4"/><circle cx="-.3" cy="-17.4" r="1.2"/><circle cx="1.7" cy="-17" r="1.1"/><circle cx="3.3" cy="-15.9" r="1"/><circle cx="4.5" cy="-14.3" r=".9"/></g><g transform="translate(207 467) scale(0.95 0.95)" fill="#7A2E36" opacity=".55"><path d="M0 0c-3.4 0-4.6-3.6-4.3-7.6c.4-4.4 2.2-6.9 4.6-6.9c2.5 0 3.9 2.6 3.7 6.8C3.8-3.5 3 0 0 0z"/><circle cx="-2.6" cy="-16.6" r="1.4"/><circle cx="-.3" cy="-17.4" r="1.2"/><circle cx="1.7" cy="-17" r="1.1"/><circle cx="3.3" cy="-15.9" r="1"/><circle cx="4.5" cy="-14.3" r=".9"/></g><g transform="translate(193 440) scale(-0.95 0.95)" fill="#7A2E36" opacity=".55"><path d="M0 0c-3.4 0-4.6-3.6-4.3-7.6c.4-4.4 2.2-6.9 4.6-6.9c2.5 0 3.9 2.6 3.7 6.8C3.8-3.5 3 0 0 0z"/><circle cx="-2.6" cy="-16.6" r="1.4"/><circle cx="-.3" cy="-17.4" r="1.2"/><circle cx="1.7" cy="-17" r="1.1"/><circle cx="3.3" cy="-15.9" r="1"/><circle cx="4.5" cy="-14.3" r=".9"/></g><g transform="translate(207 413) scale(0.95 0.95)" fill="#7A2E36" opacity=".55"><path d="M0 0c-3.4 0-4.6-3.6-4.3-7.6c.4-4.4 2.2-6.9 4.6-6.9c2.5 0 3.9 2.6 3.7 6.8C3.8-3.5 3 0 0 0z"/><circle cx="-2.6" cy="-16.6" r="1.4"/><circle cx="-.3" cy="-17.4" r="1.2"/><circle cx="1.7" cy="-17" r="1.1"/><circle cx="3.3" cy="-15.9" r="1"/><circle cx="4.5" cy="-14.3" r=".9"/></g><g transform="translate(193 386) scale(-0.95 0.95)" fill="#7A2E36" opacity=".55"><path d="M0 0c-3.4 0-4.6-3.6-4.3-7.6c.4-4.4 2.2-6.9 4.6-6.9c2.5 0 3.9 2.6 3.7 6.8C3.8-3.5 3 0 0 0z"/><circle cx="-2.6" cy="-16.6" r="1.4"/><circle cx="-.3" cy="-17.4" r="1.2"/><circle cx="1.7" cy="-17" r="1.1"/><circle cx="3.3" cy="-15.9" r="1"/><circle cx="4.5" cy="-14.3" r=".9"/></g><g transform="translate(207 359) scale(0.95 0.95)" fill="#7A2E36" opacity=".55"><path d="M0 0c-3.4 0-4.6-3.6-4.3-7.6c.4-4.4 2.2-6.9 4.6-6.9c2.5 0 3.9 2.6 3.7 6.8C3.8-3.5 3 0 0 0z"/><circle cx="-2.6" cy="-16.6" r="1.4"/><circle cx="-.3" cy="-17.4" r="1.2"/><circle cx="1.7" cy="-17" r="1.1"/><circle cx="3.3" cy="-15.9" r="1"/><circle cx="4.5" cy="-14.3" r=".9"/></g><g transform="translate(193 332) scale(-0.95 0.95)" fill="#7A2E36" opacity=".55"><path d="M0 0c-3.4 0-4.6-3.6-4.3-7.6c.4-4.4 2.2-6.9 4.6-6.9c2.5 0 3.9 2.6 3.7 6.8C3.8-3.5 3 0 0 0z"/><circle cx="-2.6" cy="-16.6" r="1.4"/><circle cx="-.3" cy="-17.4" r="1.2"/><circle cx="1.7" cy="-17" r="1.1"/><circle cx="3.3" cy="-15.9" r="1"/><circle cx="4.5" cy="-14.3" r=".9"/></g><g transform="translate(207 305) scale(0.95 0.95)" fill="#7A2E36" opacity=".55"><path d="M0 0c-3.4 0-4.6-3.6-4.3-7.6c.4-4.4 2.2-6.9 4.6-6.9c2.5 0 3.9 2.6 3.7 6.8C3.8-3.5 3 0 0 0z"/><circle cx="-2.6" cy="-16.6" r="1.4"/><circle cx="-.3" cy="-17.4" r="1.2"/><circle cx="1.7" cy="-17" r="1.1"/><circle cx="3.3" cy="-15.9" r="1"/><circle cx="4.5" cy="-14.3" r=".9"/></g><g transform="translate(193 278) scale(-0.95 0.95)" fill="#7A2E36" opacity=".55"><path d="M0 0c-3.4 0-4.6-3.6-4.3-7.6c.4-4.4 2.2-6.9 4.6-6.9c2.5 0 3.9 2.6 3.7 6.8C3.8-3.5 3 0 0 0z"/><circle cx="-2.6" cy="-16.6" r="1.4"/><circle cx="-.3" cy="-17.4" r="1.2"/><circle cx="1.7" cy="-17" r="1.1"/><circle cx="3.3" cy="-15.9" r="1"/><circle cx="4.5" cy="-14.3" r=".9"/></g><g transform="translate(207 251) scale(0.95 0.95)" fill="#7A2E36" opacity=".55"><path d="M0 0c-3.4 0-4.6-3.6-4.3-7.6c.4-4.4 2.2-6.9 4.6-6.9c2.5 0 3.9 2.6 3.7 6.8C3.8-3.5 3 0 0 0z"/><circle cx="-2.6" cy="-16.6" r="1.4"/><circle cx="-.3" cy="-17.4" r="1.2"/><circle cx="1.7" cy="-17" r="1.1"/><circle cx="3.3" cy="-15.9" r="1"/><circle cx="4.5" cy="-14.3" r=".9"/></g><g transform="translate(193 224) scale(-0.95 0.95)" fill="#7A2E36" opacity=".55"><path d="M0 0c-3.4 0-4.6-3.6-4.3-7.6c.4-4.4 2.2-6.9 4.6-6.9c2.5 0 3.9 2.6 3.7 6.8C3.8-3.5 3 0 0 0z"/><circle cx="-2.6" cy="-16.6" r="1.4"/><circle cx="-.3" cy="-17.4" r="1.2"/><circle cx="1.7" cy="-17" r="1.1"/><circle cx="3.3" cy="-15.9" r="1"/><circle cx="4.5" cy="-14.3" r=".9"/></g><g transform="translate(207 197) scale(0.95 0.95)" fill="#7A2E36" opacity=".55"><path d="M0 0c-3.4 0-4.6-3.6-4.3-7.6c.4-4.4 2.2-6.9 4.6-6.9c2.5 0 3.9 2.6 3.7 6.8C3.8-3.5 3 0 0 0z"/><circle cx="-2.6" cy="-16.6" r="1.4"/><circle cx="-.3" cy="-17.4" r="1.2"/><circle cx="1.7" cy="-17" r="1.1"/><circle cx="3.3" cy="-15.9" r="1"/><circle cx="4.5" cy="-14.3" r=".9"/></g><g transform="translate(193 170) scale(-0.95 0.95)" fill="#7A2E36" opacity=".55"><path d="M0 0c-3.4 0-4.6-3.6-4.3-7.6c.4-4.4 2.2-6.9 4.6-6.9c2.5 0 3.9 2.6 3.7 6.8C3.8-3.5 3 0 0 0z"/><circle cx="-2.6" cy="-16.6" r="1.4"/><circle cx="-.3" cy="-17.4" r="1.2"/><circle cx="1.7" cy="-17" r="1.1"/><circle cx="3.3" cy="-15.9" r="1"/><circle cx="4.5" cy="-14.3" r=".9"/></g><g transform="translate(207 143) scale(0.95 0.95)" fill="#7A2E36" opacity=".55"><path d="M0 0c-3.4 0-4.6-3.6-4.3-7.6c.4-4.4 2.2-6.9 4.6-6.9c2.5 0 3.9 2.6 3.7 6.8C3.8-3.5 3 0 0 0z"/><circle cx="-2.6" cy="-16.6" r="1.4"/><circle cx="-.3" cy="-17.4" r="1.2"/><circle cx="1.7" cy="-17" r="1.1"/><circle cx="3.3" cy="-15.9" r="1"/><circle cx="4.5" cy="-14.3" r=".9"/></g>'
_G_FRAME = '<rect x="20" y="30" width="340" height="146" fill="#F5ECDC"/><line x1="190" y1="30" x2="190" y2="176" stroke="#E2D3B6" stroke-width="1.2"/><circle cx="180" cy="148" r="5" fill="none" stroke="#C9A34E" stroke-width="1.3"/><circle cx="180" cy="142" r="1.6" fill="#C9A34E"/><circle cx="200" cy="148" r="5" fill="none" stroke="#C9A34E" stroke-width="1.3"/><circle cx="200" cy="142" r="1.6" fill="#C9A34E"/><rect x="8" y="14" width="364" height="16" rx="2" fill="#E8D7B5" stroke="#B9862E" stroke-width="1.4"/><rect x="8" y="30" width="12" height="146" fill="#E8D7B5" stroke="#B9862E" stroke-width="1.4"/><rect x="360" y="30" width="12" height="146" fill="#E8D7B5" stroke="#B9862E" stroke-width="1.4"/><path d="M0 176 H380 L372 188 H8Z" fill="#FBF4E7" stroke="#B9862E" stroke-width="1.4" stroke-linejoin="round"/>'
_ICON_FULL = '<svg viewBox="-13 -14 26 27" width="18" style="flex:0 0 auto;margin-top:1px"><ellipse cx="9.4" cy="0.0" rx="5.8" ry="4.3" fill="#E39B2B" stroke="#B9862E" stroke-width=".6" transform="rotate(0 9.4 0.0)"/><ellipse cx="8.1" cy="4.7" rx="5.8" ry="4.3" fill="#E39B2B" stroke="#B9862E" stroke-width=".6" transform="rotate(30 8.1 4.7)"/><ellipse cx="4.7" cy="8.1" rx="5.8" ry="4.3" fill="#E39B2B" stroke="#B9862E" stroke-width=".6" transform="rotate(60 4.7 8.1)"/><ellipse cx="0.0" cy="9.4" rx="5.8" ry="4.3" fill="#E39B2B" stroke="#B9862E" stroke-width=".6" transform="rotate(90 0.0 9.4)"/><ellipse cx="-4.7" cy="8.1" rx="5.8" ry="4.3" fill="#E39B2B" stroke="#B9862E" stroke-width=".6" transform="rotate(120 -4.7 8.1)"/><ellipse cx="-8.1" cy="4.7" rx="5.8" ry="4.3" fill="#E39B2B" stroke="#B9862E" stroke-width=".6" transform="rotate(150 -8.1 4.7)"/><ellipse cx="-9.4" cy="0.0" rx="5.8" ry="4.3" fill="#E39B2B" stroke="#B9862E" stroke-width=".6" transform="rotate(180 -9.4 0.0)"/><ellipse cx="-8.1" cy="-4.7" rx="5.8" ry="4.3" fill="#E39B2B" stroke="#B9862E" stroke-width=".6" transform="rotate(210 -8.1 -4.7)"/><ellipse cx="-4.7" cy="-8.1" rx="5.8" ry="4.3" fill="#E39B2B" stroke="#B9862E" stroke-width=".6" transform="rotate(240 -4.7 -8.1)"/><ellipse cx="-0.0" cy="-9.4" rx="5.8" ry="4.3" fill="#E39B2B" stroke="#B9862E" stroke-width=".6" transform="rotate(270 -0.0 -9.4)"/><ellipse cx="4.7" cy="-8.1" rx="5.8" ry="4.3" fill="#E39B2B" stroke="#B9862E" stroke-width=".6" transform="rotate(300 4.7 -8.1)"/><ellipse cx="8.1" cy="-4.7" rx="5.8" ry="4.3" fill="#E39B2B" stroke="#B9862E" stroke-width=".6" transform="rotate(330 8.1 -4.7)"/><circle cx="0" cy="0" r="6.6" fill="#F2C14E" stroke="#B9862E" stroke-width=".6"/><circle cx="0" cy="0" r="2.4" fill="#D9692A"/></svg>'
_ICON_HALF = '<svg viewBox="-13 -14 26 27" width="18" style="flex:0 0 auto;margin-top:1px"><path d="M-5.6 -1.9 Q0 -11.2 5.6 -1.9" fill="#3E7D5A"/><ellipse cx="5.9" cy="2.0" rx="5.2" ry="3.8" fill="#E39B2B" stroke="#B9862E" stroke-width=".6" transform="rotate(19 5.9 2.0)"/><ellipse cx="3.7" cy="5.0" rx="5.2" ry="3.8" fill="#E39B2B" stroke="#B9862E" stroke-width=".6" transform="rotate(54 3.7 5.0)"/><ellipse cx="0.0" cy="6.2" rx="5.2" ry="3.8" fill="#E39B2B" stroke="#B9862E" stroke-width=".6" transform="rotate(90 0.0 6.2)"/><ellipse cx="-3.7" cy="5.0" rx="5.2" ry="3.8" fill="#E39B2B" stroke="#B9862E" stroke-width=".6" transform="rotate(126 -3.7 5.0)"/><ellipse cx="-5.9" cy="2.0" rx="5.2" ry="3.8" fill="#E39B2B" stroke="#B9862E" stroke-width=".6" transform="rotate(161 -5.9 2.0)"/><circle cx="0" cy="0.9" r="4.7" fill="#F2C14E" stroke="#B9862E" stroke-width=".6"/></svg>'
_ICON_BUD = '<svg viewBox="-13 -14 26 27" width="18" style="flex:0 0 auto;margin-top:1px"><ellipse cx="0" cy="1.2" rx="5.4" ry="8.4" fill="#E39B2B" stroke="#B9862E" stroke-width=".6"/><path d="M-6.6 -1.2 Q0 -13.2 6.6 -1.2 Q0 3.6 -6.6 -1.2Z" fill="#3E7D5A"/></svg>'
_LB_GOOD = '<svg width="58" height="16" viewBox="0 0 58 16" role="img" aria-label="Good" style="vertical-align:-2px;margin-right:7px"><rect x=".6" y=".6" width="56.8" height="14.8" rx="7.4" fill="#FFFDF8" stroke="#3E7D5A" stroke-width="1.2"/><text x="29" y="11" text-anchor="middle" style="font:700 8px Inter,sans-serif;letter-spacing:.1em;fill:#3E7D5A">GOOD</text></svg>'
_LB_CARE = '<svg width="58" height="16" viewBox="0 0 58 16" role="img" aria-label="Careful" style="vertical-align:-2px;margin-right:7px"><rect x=".6" y=".6" width="56.8" height="14.8" rx="7.4" fill="#FFFDF8" stroke="#B4572B" stroke-width="1.2" stroke-dasharray="3.2 2.4"/><text x="29" y="11" text-anchor="middle" style="font:700 8px Inter,sans-serif;letter-spacing:.1em;fill:#B4572B">CAREFUL</text></svg>'
