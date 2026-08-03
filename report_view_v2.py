"""
Marriage report renderer — v2 (blueprint LOCKED v2).

Report structure (one topic = one chapter, no repetition):
  Cover → Answer page (hero cards + Kundli) → Detailed Report (windows once
  with actions folded in, quiet phases, why-not-yet, next 3 years, partner,
  Manglik, Sade Sati, remedies) → The Astrology (method, charts, calculations)

Design:
  * English is the deterministic base. Every prose slot is `_prose(p, slot, bank)`
    → LLM prose (narrative.py) when present, else the English bank. With the LLM
    disabled the banks alone render a complete, coherent report.
  * FACTS ARE DETERMINISTIC. Charts, dates, scores, tables, verdicts all come from
    the payload; the LLM only writes the interpretive prose beside them.
  * Manglik pages are fully deterministic (no slot) — sensitive framing.
  * Every content section carries a 1-2 word headline chip summarising the page.
  * Only windows within ~4 years are shown when a near window exists (far windows
    are meaningless to the reader).
  * MD/AD are always spelled out (Mahadasha / Antardasha).
  * The Hindi (Devanagari) report is this same HTML run through shaadi_hi.localize.
"""
import re
from datetime import datetime, timedelta
from html import escape

import report_addons
from narrative import narr
from report_view import (north_chart_svg, _weak_periods,
                         GRADE_ACTION, GRADE_COLOR, SIGN_PARTNER, DK_PARTNER)
from jyotish_maps import MANGLIK_DOSDONTS, WEAK_PERIOD_ACTION


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _prose(p: dict, slot: str, bank: str) -> str:
    """LLM prose for a slot (already html-escaped in narrative.py) or the English
    bank. Banks are our own trusted copy, so they are inserted as-is."""
    v = narr(p, slot)
    return v if v else bank


def _pretty(ym: str) -> str:
    return datetime.strptime(ym, "%Y-%m").strftime("%b %Y")


def _fmt_dob(s: str) -> str:
    if not s:
        return ""
    try:
        return datetime.strptime(s, "%Y-%m-%d").strftime("%d %b %Y")
    except Exception:
        return str(s)


def _expand_dasha(s: str) -> str:
    """MD/AD → Mahadasha/Antardasha for reader-facing text."""
    return (s or "").replace(" MD ", " Mahadasha ").replace(" AD", " Antardasha")


def _today(meta: dict) -> datetime:
    try:
        return datetime.strptime(meta.get("generated", ""), "%Y-%m-%d")
    except Exception:
        return datetime(2025, 1, 1)


def _visible_windows(windows: list, meta: dict, years: int = 4) -> list:
    """Show only windows starting within `years` of today when at least one such
    near window exists — windows 4+ years out are meaningless if a nearer one is
    already indicated. Falls back to all windows if none are near."""
    if not windows:
        return []
    cutoff = _today(meta) + timedelta(days=int(years * 365.25))
    near = [w for w in windows if datetime.strptime(w["start"], "%Y-%m") <= cutoff]
    return near if near else windows


def _clean_windows(windows: list, meta: dict) -> list:
    """Reader-facing view of the engine windows, in chronological order:
    windows already over are dropped, an ongoing window starts 'now' (never a
    past month), and peak months in the past are removed — a report generated
    today must never present past dates as the future."""
    today = _today(meta)
    cur = today.strftime("%Y-%m")            # "YYYY-MM" compares correctly as text
    out = []
    for w in windows:
        if w["end"] < cur:
            continue
        w = dict(w)
        if w["start"] < cur:
            w["start"] = cur
        if w.get("core_end") and w["core_end"] < cur:
            w["core_start"] = w["start"]     # core fully past — card hides it
        elif w.get("core_start") and w["core_start"] < cur:
            w["core_start"] = cur
        if w.get("peak_months"):
            kept = []
            for m in w["peak_months"]:
                try:
                    if datetime.strptime(m, "%b %Y") >= datetime(today.year, today.month, 1):
                        kept.append(m)
                except Exception:
                    kept.append(m)
            w["peak_months"] = kept
        out.append(w)
    out.sort(key=lambda w: w["start"])
    return out


def _confidence(grade: str, tq: str):
    base = {"Strong": "High", "Moderate": "Moderate", "Building": "Emerging"}.get(grade, "Moderate")
    note = " · approx. birth time" if tq in ("T2", "T3") else ""
    return base, note


# --------------------------------------------------------------------------- #
# deterministic vocab (English)
# --------------------------------------------------------------------------- #
DIGNITY_TXT = {
    "own": "in its own sign — a strong placement",
    "exalted": "exalted — the best possible dignity",
    "debilitated": "debilitated — timing deserves extra care",
    "neutral": "neutral dignity",
}
MG_SHORT = {"non_manglik": "No", "manglik_cancelled": "Cancelled (effectively no)",
            "manglik": "Yes — see the Manglik section"}
MG_CHIP = {"non_manglik": "Clear", "manglik_cancelled": "Cleared", "manglik": "Manageable"}
# one-line card copy for the answer page's Manglik card
MG_CARD = {
    "non_manglik": "No obstacle on this front — nothing to remedy.",
    "manglik_cancelled": "Technically yes, but cancelled — practically no.",
    "manglik": "Manageable — the impact and remedies are explained in the Manglik section.",
}
# why the confidence sits where it does (answer-page Confidence card), by grade —
# fallback for when a window carries no scored rules to list
CONF_REASON = {
    "Strong": "Several timing factors — your running dasha and the supporting transits — all point to this same period.",
    "Moderate": "The main timing factors agree here, with a few mixed signals.",
    "Building": "The supporting factors are still gathering strength — treat this as a direction, not a date.",
}
# short explanations for the Kundli-at-a-glance rows
GLANCE_WHY = {
    "Lagna": "The base of your personality and whole chart — every house is counted from here.",
    "Moon": "Your mind and emotions — and the engine of your timing, since your dasha calendar runs from your Moon.",
    "7th house": "The house of marriage, partner and commitment — the main area for this report.",
    "7th lord": "The main switch for marriage; its condition shapes how clear and smooth the timing is.",
    "karaka": "The natural indicator of love and marriage (Venus, plus Jupiter for a woman) — it shows the marriage promise.",
    "darakaraka": "The Jaimini spouse-significator — a second, independent glimpse of the partner.",
}
# reader-facing birth-time accuracy for the cover (engine tiers T0..T3)
TQ_COVER = {
    "T0": "Exact",
    "T1": "Approximate (±45 min)",
    "T2": "Approximate (±3 hours)",
    "T3": "Unknown — Moon-chart method used",
}
# short partner-nature (2-3 words) keyed by 7th sign — for the partner cards
SIGN_PARTNER_SHORT = {
    "Mesha": "Direct & energetic", "Vrishabha": "Steady & loyal",
    "Mithuna": "Witty & sociable", "Karka": "Caring & family-first",
    "Simha": "Warm & confident", "Kanya": "Practical & sincere",
    "Tula": "Charming & balanced", "Vrishchika": "Intense & loyal",
    "Dhanu": "Optimistic & principled", "Makara": "Mature & ambitious",
    "Kumbha": "Independent & unconventional", "Meena": "Gentle & artistic",
}
# short meeting context (3-4 words) keyed by 7th-lord house (1..12)
MEETING_SHORT = [
    "Through your own efforts", "Family networks", "Neighbours or short travels",
    "The home circle", "Social settings", "Workplace or daily circles",
    "Direct proposals", "In-law networks", "Different community or place",
    "Career settings", "A friend's introduction", "Quiet or private settings",
]
# meeting context keyed by 7th-lord house (1..12)
MEETING_EN = [
    "self-initiated, through your own efforts",
    "family networks or finances",
    "siblings, neighbours, or short travels",
    "the home circle or mother's side",
    "social settings, children's events, or romance first",
    "the workplace or daily circles",
    "direct proposals — partnership-driven",
    "in-law networks or transformative settings",
    "distant places, education circles, or a different community",
    "career settings or father's network",
    "friends' circles — a friend's introduction",
    "quiet or private settings, possibly at some distance",
]

# --------------------------------------------------------------------------- #
# Hindi (Devanagari) compose-time helpers for the bank twins.
# The *_bank fallbacks below are interpolated f-strings (dates, grades, signs),
# so the exact-text-node localizer in shaadi_hi can never translate them after
# render. Instead, when meta.lang == "hi" every bank is COMPOSED in Devanagari
# here, reusing shaadi_hi's month/grade/proper-noun maps so vocabulary stays
# identical to the localized shell. English stays the deterministic base.
# --------------------------------------------------------------------------- #
from shaadi_hi import (MONTHS as _HI_MONTHS, GRADE as _HI_GRADE,
                       TOK as _HI_TOK, HI as _HI_DICT, MEETING as _HI_MEETING)

_HI_D9_BAND = {"strong": "मज़बूत", "steady": "स्थिर", "tender": "कोमल"}
_HI_SS_PHASE = {"rising phase": "आरंभिक चरण", "peak phase": "शिखर चरण",
                "setting phase": "उतरता चरण"}


def _hi_date(s: str) -> str:
    """'Jun 2027' -> 'जून 2027'; 'beyond 10 years' -> '10 साल से आगे'."""
    m = re.match(r"^beyond (\d+) years$", s or "")
    if m:
        return f"{m.group(1)} साल से आगे"
    return " ".join(_HI_MONTHS.get(x, x) for x in (s or "").split())


def _hi_pretty(ym: str) -> str:
    return _hi_date(_pretty(ym))


def _hi_grade(g: str) -> str:
    return _HI_GRADE.get(g, g)


def _hi_tok(x: str) -> str:
    return _HI_TOK.get(x, x)


def _hi_phrase(x: str) -> str:
    """English content-map value (SIGN_PARTNER / DK_PARTNER / dignity phrase /
    nakshatra line...) -> its authored Devanagari twin from shaadi_hi.HI, or
    the input unchanged when no twin exists (graceful degradation)."""
    return _HI_DICT.get(x, x)


# --------------------------------------------------------------------------- #
# CSS + tiny scripts
# --------------------------------------------------------------------------- #
CSS = """
:root{--ink:#2E2317;--midnight:#4A3A2A;--paper:#FAF4E9;--sindoor:#C0562F;
--haldi:#C79A46;--haldi-soft:#F1E4C8;--muted:#8A7A64;--line:#E7DDC9;
--display:'Bricolage Grotesque',sans-serif;--body:-apple-system,'Segoe UI',Roboto,sans-serif}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--body);background:var(--paper);color:var(--ink);line-height:1.6;font-size:17px}
.pg{max-width:640px;margin:0 auto;padding:40px 22px;border-bottom:1.5px dashed var(--line)}
.plabel{display:none} /* label rows above titles are retired; report_addons still emits them */
h1,h2{font-family:var(--display);line-height:1.15}
h2{font-size:26px;font-weight:800;margin-bottom:14px}
p{margin-bottom:10px}
.soft{color:var(--muted);font-size:15.5px;margin-top:14px}
.lead{font-size:18px;margin-bottom:14px}
.tierhead{max-width:640px;margin:0 auto;background:var(--midnight);color:#F3EFE4;text-align:center;padding:32px 22px}
.tierhead .tn{font-family:var(--display);font-weight:800;color:var(--haldi);font-size:13px;letter-spacing:.14em;text-transform:uppercase}
.tierhead h2{color:#fff;margin:8px 0 4px}
.tierhead p{color:#C9B79C;font-size:14.5px;margin:0}
.cover{background:radial-gradient(900px 500px at 50% -10%,#5E4A32,var(--midnight));color:#F3EFE4;text-align:center;border:none;display:flex;flex-direction:column;justify-content:center;min-height:100vh}
.cover .brand{font-family:var(--display);font-weight:800;color:var(--haldi);letter-spacing:.06em;font-size:15.5px;margin-bottom:8px}
.cover .rtitle{font-family:var(--display);font-weight:700;text-transform:uppercase;letter-spacing:.14em;color:#E9E6DC;font-size:13.5px;margin-bottom:22px}
.cover h1{font-size:32px;font-weight:800;color:#fff}
.details{display:inline-block;text-align:left;background:rgba(255,255,255,.06);border:1px solid rgba(228,176,74,.4);border-radius:12px;padding:14px 18px;margin:16px auto 0}
.details .drow{display:flex;gap:14px;font-size:14.5px;padding:3px 0;color:#E9E6DC}
.details .dk{color:#C9B79C;min-width:104px}
.toc{margin-top:18px;min-width:230px}
.toc .th{font-family:var(--display);font-weight:800;font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--haldi);margin-bottom:8px}
.toc .dk{min-width:26px;font-family:var(--display);font-weight:700;color:var(--haldi)}
.kchart{width:100%;max-width:320px;height:auto;display:block;margin:0 auto}
.kwrap{background:var(--midnight);border-radius:14px;padding:14px;margin-top:20px}
.kwrap .kcap{font-size:11.5px;color:#C9B79C;text-transform:uppercase;letter-spacing:.04em;text-align:center;margin:8px 0 0}
.method{font-size:12.5px;color:var(--muted);text-align:center;margin-top:12px}
.answer h2{text-align:center}
.hero{background:var(--midnight);color:#fff;border-radius:16px;padding:28px 22px;text-align:center;margin:4px 0 12px}
.hero-month{font-family:var(--display);font-weight:800;font-size:44px;line-height:1.05;color:#fff;margin:0}
.hero-label{font-family:var(--display);font-weight:700;font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--haldi);margin:8px 0 0}
.duo{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:0 0 12px}
.trio{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin:0 0 12px}
.trio .duocard{padding:14px 10px}
.trio .dv{font-size:16px}
.duocard{background:#fff;border:2px solid var(--haldi);border-radius:14px;padding:16px 14px;text-align:center}
.dl{font-family:var(--display);font-weight:700;font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--sindoor);margin:0 0 6px}
.dv{font-family:var(--display);font-weight:800;font-size:21px;line-height:1.25;margin:0}
.dr{font-size:13px;color:var(--muted);margin:6px 0 0;line-height:1.45}
.chk{font-size:12.5px;color:#2E7D53;margin:6px 0 0;line-height:1.4;text-align:left;font-weight:600}
.mgband{background:#fff;border:2px solid #2E7D53;border-radius:14px;padding:16px 18px;text-align:center}
.mgband.warn{border-color:var(--haldi)}
.facts{background:#fff;border:1.5px solid var(--line);border-radius:14px;padding:6px 18px}
.facts .row{display:flex;justify-content:space-between;gap:14px;padding:11px 0 4px;font-size:16.5px}
.facts .k{color:var(--muted)}.facts .v{font-weight:700;text-align:right}
.facts .why{font-size:13px;color:#8a7a5c;margin:0 0 11px;line-height:1.45;border-bottom:1px dashed var(--line);padding-bottom:11px}
.facts .row:last-of-type,.facts .why:last-child{border-bottom:none}
.tl{background:var(--midnight);border-radius:14px;padding:18px 14px 12px;margin:18px 0}
.tltrack{position:relative;height:40px;background:#5E4A32;border-radius:8px;overflow:hidden}
.tlw{position:absolute;top:0;bottom:0;opacity:.9}
.tlyrs{display:flex;justify-content:space-between;color:#9B8A70;font-size:11.5px;margin-top:7px}
.wcard{background:#fff;border:1.5px solid var(--line);border-left:6px solid;border-radius:14px;padding:18px;margin-bottom:14px}
.wtop{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.wnum{font-family:var(--display);font-weight:700;font-size:13px;text-transform:uppercase;color:var(--muted)}
.wgrade{color:#fff;font-family:var(--display);font-weight:800;font-size:12px;border-radius:20px;padding:4px 12px}
.wdates{font-family:var(--display);font-weight:800;font-size:24px}
.core{font-size:15.5px;color:var(--muted);margin-top:2px}
.peak{font-size:15.5px;color:#2E7D53;font-weight:600;margin-top:6px}
.wdasha{font-size:14.5px;color:var(--muted);margin-top:6px}
.wwhy{margin:10px 0 0 18px;font-size:15.5px}.wwhy li{margin-bottom:4px}
.mgcard{background:var(--haldi-soft);border-radius:14px;padding:20px}
.mgcard b.h{font-family:var(--display);font-size:17px;display:block;margin-bottom:8px}
.dd{display:grid;grid-template-columns:1fr;gap:12px;margin-top:14px}
.dd .col{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:14px 16px}
.dd .col.do{border-left:5px solid #2E7D53}
.dd .col.dont{border-left:5px solid #C93B2E}
.dd b{font-family:var(--display);display:block;margin-bottom:8px}
.dd ul{margin:0 0 0 16px}.dd li{font-size:15.5px;margin-bottom:6px}
.pcard{background:#fff;border:1.5px solid var(--line);border-left:6px solid var(--haldi);border-radius:14px;padding:16px 18px;margin-bottom:12px}
.pcard .pk{font-family:var(--display);font-weight:800;font-size:12px;text-transform:uppercase;color:var(--sindoor);letter-spacing:.04em}
.pcard p{font-size:18px;margin:6px 0 0}
.quiet,.act{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:10px;font-size:16.5px}
.quiet b,.act b{font-family:var(--display)}
.sumcard{background:var(--midnight);color:#F3EFE4;border-radius:16px;padding:24px;text-align:center}
.sumcard .nm{font-family:var(--display);font-weight:800;font-size:22px;color:#fff}
.sline{margin-top:10px;font-size:16.5px}.sumcard .sline b{color:var(--haldi)}
.past{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:10px}
.pl{color:#fff;font-family:var(--display);font-weight:800;font-size:11.5px;border-radius:16px;padding:3px 10px;margin-right:10px}
.pd{font-size:14.5px;color:var(--muted);margin-top:5px}.pw{font-size:15.5px;margin-top:4px}
.ycard{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:15px 16px;margin-bottom:10px}
.ytop{display:flex;justify-content:space-between;align-items:center;font-family:var(--display);font-size:20px;margin-bottom:6px}
.ygrade{color:#fff;font-family:var(--display);font-weight:800;font-size:11.5px;border-radius:16px;padding:4px 10px}
.yd{font-size:14.5px;color:var(--muted);margin-bottom:5px}.ycard p{font-size:16.5px}
.yfav{color:#2E7D53;font-weight:600;font-size:15.5px;margin-top:5px}
.card2{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:16px;margin-bottom:12px}
.card2 b{font-family:var(--display);display:block;margin-bottom:6px}.card2 p{font-size:16.5px}
.ss{background:var(--haldi-soft);border-radius:12px;padding:15px;font-size:16.5px;margin-top:14px}
.rem{margin:12px 0 0 20px}.rem li{margin-bottom:8px;font-size:16.5px}
.remcard{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:10px}
.remcard b{font-family:var(--display)}
.upsell{background:#fff;border:2px solid var(--haldi);border-radius:14px;padding:16px;margin-top:16px;font-size:16.5px}
.btnrow{display:flex;gap:10px;margin-top:20px}
.btn{flex:1;font-family:var(--display);font-weight:800;font-size:16.5px;text-align:center;padding:13px;border-radius:11px;border:0;cursor:pointer;text-decoration:none}
.btn.p{background:var(--sindoor);color:#fff}.btn.s{background:#fff;border:1.5px solid var(--line);color:var(--ink)}
footer{text-align:center;font-size:12.5px;color:var(--muted);padding:26px 20px 44px;max-width:640px;margin:0 auto}
/* print-spacer table: wraps everything after the cover; thead/tfoot rows repeat
   on every printed page, giving paper-coloured breathing room top and bottom */
.ptbl{width:100%;border-collapse:collapse}
.ptbl>tbody>tr>td{padding:0}
.pgt,.pgb{height:0;padding:0}
@media print{.pgt{height:8mm}.pgb{height:7mm}}
.ax-wm{display:none;position:fixed;inset:0;z-index:9998;pointer-events:none;flex-direction:column;align-items:center;justify-content:center;transform:rotate(-28deg);opacity:.08;color:#4A3A2A;font-family:Georgia,serif}
.ax-wm b{font-size:36px;letter-spacing:.1em;line-height:1}.ax-wm span{font-size:12px;letter-spacing:.28em;margin-top:6px}
.ax-share{display:inline-block;background:#25D366;color:#fff;border:0;border-radius:10px;padding:12px 18px;font:600 15px/1 sans-serif;cursor:pointer;text-decoration:none}
.ax-disc{max-width:640px;margin:28px auto 8px;padding:14px 16px;border:1px solid #E7E0D2;border-radius:10px;background:#fbf7ef;font-size:13.5px;line-height:1.5;color:#6b6f80}
.ax-endcard{max-width:640px;margin:12px auto 28px;text-align:center;padding:18px;border-top:2px solid #E4B04A}
.ax-endcard b{font-size:18px;color:#4A3A2A}.ax-endcard a{color:#C93B2E;text-decoration:none;font-weight:600}
/* Phone-shaped page (not A4): a mobile PDF viewer fits page-width to the screen,
   so a narrow page renders ~1:1 and the text stays readable instead of being
   downscaled ~55% the way an A4 page is. */
/* NOTE: @page margins must stay 0 — Chrome always paints the margin area
   white, which shows as white strips on the warm paper background. Breathing
   space on every page instead comes from the .ptbl table wrapper: its
   thead/tfoot spacer rows repeat at the top and bottom of every printed page,
   painted in the page's own paper background. */
@page{size:104mm 300mm;margin:0}
@media print{
*{-webkit-print-color-adjust:exact;print-color-adjust:exact}
/* full-bleed warm paper background, edge to edge (no white page margins) */
html,body{background:var(--paper)!important}
.btnrow{display:none}
/* comfortable four-side padding on the narrow page so text never hugs the edge */
.pg{border:none;padding:26px 22px;max-width:100%;margin:0 auto}
/* keep cohesive blocks whole, but do NOT force each section onto its own page —
   that was the source of the empty half-pages. Content flows continuously. */
.wcard,.mgcard,.quiet,.act,.ycard,.card2,.pcard,.past,.ss,.remcard,.upsell,.hero,.sumcard,.dd,.facts,.tierhead,.duo,.trio,.duocard,.mgband,.kwrap{break-inside:avoid}
/* cover fills the whole first page — the dark card colour runs edge to edge,
   no paper-coloured gap below the content (page box is exactly 300mm tall) */
.cover{break-after:page;padding:40px 22px;min-height:300mm}
.newpg{break-before:page}
.tierhead{margin-top:6px;padding:34px 22px}
h1,h2{break-after:avoid}
.lead,p{orphans:2;widows:2}
.ax-wm{display:flex!important}.ax-share{display:none!important}#ax-pdf{display:none!important}
.cover{background:radial-gradient(900px 500px at 50% -10%,#5E4A32,var(--midnight))!important}}
"""

SCRIPT = """<script>
window.axShare=function(){var url=location.href;var t='Check out my marriage timing report from Axtroshastra';
if(navigator.share){navigator.share({title:'Axtroshastra',text:t,url:url}).catch(function(){});}
else{window.open('https://wa.me/?text='+encodeURIComponent(t+' '+url),'_blank');}};
</script>"""


# --------------------------------------------------------------------------- #
# section / component helpers
# --------------------------------------------------------------------------- #
def _sec(plabel: str, chip: str, h2: str, body: str) -> str:
    # plabel/chip args are kept for call-site stability but are no longer
    # rendered — every page starts directly with its title (owner request).
    return f'<section class="pg"><h2>{h2}</h2>{body}</section>'


def _tier(n: str, title: str, sub: str, cls: str = "") -> str:
    # `n` (the "Tier N" label) is no longer rendered — dividers show the title
    # alone, with an optional one-line subtitle.
    s = f"<p>{sub}</p>" if sub else ""
    return f'<section class="tierhead{" " + cls if cls else ""}"><h2>{title}</h2>{s}</section>'


def _timeline_html(windows: list, meta: dict) -> str:
    today = _today(meta)
    y0 = today.year
    y1 = max([datetime.strptime(w["end"], "%Y-%m").year for w in windows] + [y0 + 1])
    span = max(1, (y1 - y0)) * 365.25
    bars = ""
    for w in windows:
        s = datetime.strptime(w["start"], "%Y-%m"); e = datetime.strptime(w["end"], "%Y-%m")
        left = max(0.0, (s - datetime(y0, 1, 1)).days / span * 100)
        width = max(6.0, (e - s).days / span * 100)
        bars += (f"<div class='tlw' style='left:{left:.1f}%;width:{min(width, 100 - left):.1f}%;"
                 f"background:{GRADE_COLOR[w['grade']]}'></div>")
    step = 1 if (y1 - y0) <= 5 else 2
    yrs = "".join(f"<span>{y}</span>" for y in range(y0, y1 + 1, step))
    return f"<div class='tl'><div class='tltrack'>{bars}</div><div class='tlyrs'>{yrs}</div></div>"


def _window_card(i: int, w: dict, deep: bool = True) -> str:
    core = (f"<p class='core'>Core period: {_pretty(w['core_start'])} – {_pretty(w['core_end'])}</p>"
            if w["start"] != w["core_start"] else "")
    peak = (f"<p class='peak'>⭐ Strongest months: {', '.join(w['peak_months'])}</p>"
            if w.get("peak_months") else "")
    reasons = ""
    if deep:
        items = "".join(f"<li>{r['why']}</li>" for r in w.get("rules_fired", [])
                        if not r["id"].startswith(("AD_WEAK", "AD_DRY", "TR_SAT")))
        reasons = f"<ul class='wwhy'>{items}</ul>"
    return (f"<div class='wcard' style='border-left-color:{GRADE_COLOR[w['grade']]}'>"
            f"<div class='wtop'><span class='wnum'>Window {i}</span>"
            f"<span class='wgrade' style='background:{GRADE_COLOR[w['grade']]}'>{w['grade'].upper()}</span></div>"
            f"<p class='wdates'>{_pretty(w['start'])} → {_pretty(w['end'])}</p>"
            f"{core}{peak}<p class='wdasha'>{_expand_dasha(w['dasha'])}</p>{reasons}</div>")


def _dosdont(block: dict) -> str:
    do = "".join(f"<li>{x}</li>" for x in block["do"])
    dont = "".join(f"<li>{x}</li>" for x in block["dont"])
    return (f"<div class='dd'><div class='col do'><b>Do</b><ul>{do}</ul></div>"
            f"<div class='col dont'><b>Don't</b><ul>{dont}</ul></div></div>")


# --------------------------------------------------------------------------- #
# main entry
# --------------------------------------------------------------------------- #
def render_report_v2(p: dict) -> str:
    meta, sig, mg = p["meta"], p["significators"], p["manglik"]
    nav = p.get("navamsa") or {}
    ex = p.get("extras", {}) or {}
    teaser = p.get("teaser", {}) or {}
    birth = meta.get("_birth", {}) or {}
    name = escape(meta.get("name", ""))
    tq = meta.get("time_quality", "T0")
    lang = "hi" if meta.get("lang") == "hi" else "en"   # report_addons emits Devanagari directly for hi
    hi = lang == "hi"   # Devanagari bank twins below (LLM prose slots override either way)

    all_windows = p.get("windows") or []
    # chronological, future-facing, and near-horizon only
    windows = _visible_windows(_clean_windows(all_windows, meta), meta)
    w1 = windows[0] if windows else None
    w2 = windows[1] if len(windows) > 1 else None
    w3 = windows[2] if len(windows) > 2 else None

    system_note = ("Chandra Lagna system (Moon-as-ascendant) — the classical Parashari "
                   "method used when the birth time is approximate; windows are shown with "
                   "honest, wider ranges."
                   if meta.get("system") == "chandra_lagna" else
                   "Lagna-based analysis with full house precision.")

    seventh_sign = sig["seventh_sign"]
    seventh_lord = sig["seventh_lord"]
    sl_dignity = sig.get("seventh_lord_dignity", "neutral")
    sl_house = sig.get("seventh_lord_house", 1)
    dk = sig["darakaraka"]
    love = ex.get("checks", {}).get("love_leaning")
    lv_line = ("Your chart leans toward a love or self-chosen match." if love
               else "Your chart leans toward an arranged or introduction-led match.")
    nature = SIGN_PARTNER.get(seventh_sign, "a well-matched partner")

    parts = []

    # ============================================ TIER 1 — cover (#1)
    drows = []
    dob = _fmt_dob(meta.get("dob") or birth.get("dob"))
    tob = meta.get("tob") or birth.get("tob")
    place = meta.get("place") or birth.get("place") or ""
    if dob:
        drows.append(("Date of birth", dob))
    if tob:
        drows.append(("Time of birth", tob))
    if place:
        drows.append(("Place of birth", place))
    drows.append(("Birth-time accuracy", TQ_COVER.get(tq, tq)))
    details = ("<div class='details'>" + "".join(
        f"<div class='drow'><span class='dk'>{k}</span><span>{escape(str(v))}</span></div>"
        for k, v in drows) + "</div>") if drows else ""
    toc_items = ["Your marriage windows", "Why it hasn't happened yet",
                 "Next 3 Year Forecast", "Your potential partner",
                 "Manglik &amp; Sade Sati", "Remedies", "The full astrology behind it"]
    toc = ('<div class="details toc"><p class="th">What\'s inside</p>' +
           "".join(f'<div class="drow"><span class="dk">{i:02d}</span><span>{t}</span></div>'
                   for i, t in enumerate(toc_items, 1)) + "</div>")
    parts.append(f"""<section class="pg cover">
  <p class="brand">✦ AXTROSHASTRA</p>
  <p class="rtitle">Marriage Timing Report</p>
  <h1>{name}</h1>
  {details}
  {toc}
</section>""")

    # everything after the cover lives inside the spacer table (.ptbl): its
    # thead/tfoot rows repeat on every printed page as paper-coloured gaps
    parts.append("<table class='ptbl'><thead><tr><td class='pgt'></td></tr></thead>"
                 "<tfoot><tr><td class='pgb'></td></tr></tfoot><tbody><tr><td>")

    # ---- The Answer (page 2): big scannable cards only, then the Kundli + method note.
    # No prose here — everything below is covered in depth later in the report.
    if w1:
        strongest_month = w1["peak_months"][0] if w1.get("peak_months") else _pretty(w1["core_start"])
        conf, _ = _confidence(w1["grade"], tq)
        time_note = ('<p class="dr">Birth time is approximate, so the window is kept honestly wide.</p>'
                     if tq in ("T2", "T3") else "")
        # the factors behind the confidence — the window's scored rules, as ✓ lines
        rdesc = report_addons.RULE_DESC_HI if hi else report_addons.RULE_DESC
        factors = [r["id"] for r in w1.get("rules_fired", [])
                   if report_addons.RULE_PTS.get(r["id"], 0) > 0][:3]
        why = ("".join(f'<p class="chk">✓ {rdesc.get(f, f)}</p>' for f in factors)
               or f'<p class="dr">{CONF_REASON.get(w1["grade"], CONF_REASON["Moderate"])}</p>')
        hero = (f'<div class="hero"><p class="hero-month">{strongest_month}</p>'
                f'<p class="hero-label">Most likely marriage window</p></div>')
        duo = (f'<div class="duo"><div class="duocard"><p class="dl">Full marriage window</p>'
               f'<p class="dv">{_pretty(w1["start"])} – {_pretty(w1["end"])}</p></div>'
               f'<div class="duocard"><p class="dl">Confidence</p><p class="dv">{conf}</p>'
               f'{why}{time_note}</div></div>')
    else:
        hero = duo = ""
    mgband = (f'<div class="mgband{" warn" if mg["status"] == "manglik" else ""}">'
              f'<p class="dl">Manglik</p><p class="dv">{MG_SHORT[mg["status"]]}</p>'
              f'<p class="dr">{MG_CARD[mg["status"]]}</p></div>')
    # partner snapshot cards — shown here on the answer page, and again atop the
    # full partner chapter (the Kundli itself lives in The Astrology)
    meet_short = MEETING_SHORT[sl_house - 1] if 1 <= sl_house <= 12 else "Your own circles"
    partner_cards = (
        f'<div class="trio">'
        f'<div class="duocard"><p class="dl">Love or arranged</p>'
        f'<p class="dv">{"Love Marriage" if love else "Arranged Marriage"}</p></div>'
        f'<div class="duocard"><p class="dl">Nature</p>'
        f'<p class="dv">{SIGN_PARTNER_SHORT.get(seventh_sign, "Well-matched")}</p></div>'
        f'<div class="duocard"><p class="dl">Where will you guys meet</p>'
        f'<p class="dv">{meet_short}</p></div></div>')
    parts.append(f"""<section class="pg answer">
<h2>When will you get married?</h2>
{hero}
{duo}
{mgband}
<h2 style="font-size:22px;margin:26px 0 12px">Your potential partner</h2>
{partner_cards}
<p class="method">Generated {meta.get('generated','')} · NASA JPL data (Swiss Ephemeris) · Lahiri ayanamsa · Whole-sign houses · {system_note}</p>
</section>""")

    # ============================================ THE REPORT (one topic = one chapter)
    parts.append(_tier("", "Detailed Report", ""))

    # ---- Windows chapter: the ONLY place windows appear in full. Timeline,
    # each window's deep card, and what to do in it — together, once. ----
    wi_bank = (f"You have {len(windows)} marriage window{'s' if len(windows) != 1 else ''} on the horizon. "
               "These are the stretches when a match is most likely to click — your best seasons to act, "
               "not fixed dates.")
    if hi:
        wi_bank = (f"आपके सामने {len(windows)} विवाह विंडो{'ज़' if len(windows) != 1 else ''} हैं। "
                   "इन्हें तय तारीख़ें नहीं, बल्कि वे मौसम समझिए जब रिश्ता बनने की संभावना सबसे ज़्यादा "
                   "होती है — यही क़दम उठाने के सबसे अच्छे दौर हैं।")
    wrows = ""
    for i, w in enumerate(windows, 1):
        head, body = GRADE_ACTION.get(w["grade"], ("Stay active.", ""))
        wrows += (_window_card(i, w, deep=True) +
                  f"<div class='act'><b>{head}</b><p>{body}</p></div>")
    parts.append(_sec("", "", f"Your marriage windows ({len(windows)})",
                      f'<p class="lead">{_prose(p, "windows_intro", wi_bank)}</p>{_timeline_html(windows, meta)}{wrows}'
                      '<p class="soft">Your chart shows the timing; the effort and the choice stay in your hands. '
                      'Even in a strong window you still have to look — the odds are just far better.</p>'))

    # ---- Why it hasn't happened yet — past-period cards first, then the text ----
    past_rows = ""
    lbl = {"active": ("#2E7D53", "ACTIVE"), "mild": ("#E4B04A", "MILD"), "quiet": ("#A8977F", "QUIET")}
    for pp in ex.get("past", []):
        c, t = lbl.get(pp["label"], ("#A8977F", pp["label"].upper()))
        past_rows += (f"<div class='past'><span class='pl' style='background:{c}'>{t}</span>"
                      f"<b>{pp['from']} – {pp['to']}</b><p class='pd'>{_expand_dasha(pp['dasha'])}</p>"
                      f"<p class='pw'>{' · '.join(pp['why'])}</p></div>")
    pp_bank = ("Looking back, the periods that passed quietly did so because the timing simply wasn't activated for "
               "marriage — not because of anything you did or didn't do. That distinction matters.")
    if hi:
        pp_bank = ("पीछे मुड़कर देखें, तो जो दौर चुपचाप निकल गए, वे इसलिए निकले क्योंकि विवाह के लिए समय "
                   "सक्रिय ही नहीं था — इसलिए नहीं कि आपने कुछ किया या नहीं किया। यह फ़र्क़ मायने रखता है।")
    parts.append(_sec("", "", "Why it hasn't happened yet",
                      f'{past_rows}<p class="lead">{_prose(p, "past_pattern", pp_bank)}</p>'))

    # ---- Page 6: the next three years — fav months first, dasha last in each card ----
    y_rows = ""
    for y in ex.get("year_outlook", []):
        gr = (f"<span class='ygrade' style='background:{GRADE_COLOR[y['grade']]}'>{y['grade'].upper()} WINDOW</span>"
              if y.get("grade") else "<span class='ygrade' style='background:#A8977F'>NO MAJOR WINDOW</span>")
        jup = ("Jupiter's transit this year sits in supportive houses — it helps carry conversations forward."
               if y.get("jupiter_supportive") else
               "Jupiter's transit this year is neutral — lean a little more on effort than on luck.")
        fav = (f"<p class='yfav'>⭐ Favourable months: {', '.join(y['fav_months'])}</p>" if y.get("fav_months") else "")
        y_rows += (f"<div class='ycard'><div class='ytop'><b>{y['year']}</b>{gr}</div>"
                   f"{fav}<p>{jup}</p><p class='yd' style='margin:6px 0 0'>{' / '.join(y.get('dashas', []))}</p></div>")
    ol_bank = ("Across the next three years the momentum builds toward your windows — watch the favourable months, "
               "and treat the quieter stretches as preparation time.")
    if hi:
        ol_bank = ("अगले तीन सालों में रुझान आपकी विंडोज़ की ओर बढ़ता जाता है — अनुकूल महीनों पर नज़र रखिए, "
                   "और शांत दौर को तैयारी का समय मानिए।")
    parts.append(_sec("", "", "Next 3 Year Forecast",
                      f'<p class="lead">{_prose(p, "outlook", ol_bank)}</p>{y_rows}'))

    ss = ex.get("sade_sati", {}) or {}

    # weak periods, clamped to the same near horizon as the windows (#3): never
    # surface a quiet stretch that runs into a hidden far window.
    cutoff = _today(meta) + timedelta(days=int(4 * 365.25))
    weak_labels = []
    for a, b in _weak_periods(p):
        try:
            sa = datetime.strptime(a, "%b %Y"); sb = datetime.strptime(b, "%b %Y")
        except Exception:
            weak_labels.append(f"{a} – {b}"); continue
        if sa > cutoff:
            continue
        weak_labels.append(f"{a} – {b}" if sb <= cutoff else f"{a} onwards")
    aw_bank = _hi_phrase(WEAK_PERIOD_ACTION["line"]) if hi else WEAK_PERIOD_ACTION["line"]
    weak_rows = "".join(
        f"<div class='quiet'><b>{lab}</b><p>A quieter stretch — matches may come along, but they rarely stick. "
        f"That is the pattern of the period, not a failing.</p></div>" for lab in weak_labels)
    parts.append(_sec("Quiet periods", "Prepare", "Make your quiet phases count",  # (#8)
                      f'<p class="lead">{_prose(p, "action_weak", aw_bank)}</p>{weak_rows}{_dosdont(WEAK_PERIOD_ACTION)}'))

    # ---- Partner chapter: everything about the partner, once. Scannable cards
    # up top, then each dimension exactly one card. ----
    pt_bank = (f"Your indications point to {nature}. Where and how you meet is written into the chart too — "
               "here is the full picture, dimension by dimension.")
    if hi:
        pt_bank = (f"संकेत बताते हैं कि आपका जीवनसाथी {_hi_phrase(nature)} हो सकता है। आप कहाँ और कैसे "
                   "मिलेंगे, यह भी कुंडली में लिखा है — नीचे पूरी तस्वीर है, पहलू-दर-पहलू।")
    meet = MEETING_EN[sl_house - 1] if 1 <= sl_house <= 12 else "your own circles"
    foreign = ex.get("checks", {}).get("foreign_or_intercommunity")
    for_line = ("There is also a signature for a partner from a different community, background, or place."
                if foreign else "The indications lean toward your own circle and community.")
    nakp = ex.get("nak_profile", {}) or {}
    partner_detail = (
        f'<div class="pcard"><span class="pk">Their personality</span><p>{nature}.</p></div>'
        f'<div class="pcard"><span class="pk">Love vs Arranged</span><p>{lv_line}</p></div>'
        f'<div class="pcard"><span class="pk">Darakaraka ({dk})</span><p>{DK_PARTNER.get(dk, "—")}.</p></div>'
        f'<div class="pcard"><span class="pk">How you\'ll meet</span><p>The connection may come through {meet}.</p></div>'
        f'<div class="pcard"><span class="pk">Community &amp; background</span><p>{for_line}</p></div>'
        f'<div class="card2"><b>How you love — your Venus</b><p>Your love-style is {ex.get("venus_style", "—")}.</p></div>'
        f'<div class="card2"><b>Your nakshatra: {nakp.get("nakshatra", "—")} ({nakp.get("symbol", "")})</b>'
        f'<p>{nakp.get("nature", "")}.</p><p style="margin-top:8px">{nakp.get("relationship", "")}.</p></div>'
        '<p class="soft">These are indications, not a portrait — the chart gives the direction; life fills in the detail.</p>')
    parts.append(_sec("", "", "Your potential partner",
                      f'{partner_cards}<p class="lead">{_prose(p, "partner_teaser", pt_bank)}</p>{partner_detail}'))

    mgd = MANGLIK_DOSDONTS[mg["status"]]
    mg_head = {"non_manglik": "You are not Manglik ✅",
               "manglik_cancelled": "Manglik placement — but cancelled ✅",
               "manglik": "Manglik placement — let's understand it calmly"}[mg["status"]]
    cancel_line = (f"<p class='soft'>Cancellation(s) that apply: <b>{', '.join(mg.get('cancellations', [])) or '—'}</b>.</p>"
                   if mg["status"] == "manglik_cancelled" else "")
    mg_body = (f'<div class="mgcard"><b class="h">{mg_head}</b><p>{mgd["line"]}</p></div>{cancel_line}'
               f'<p class="soft">Technical: Mars from Lagna — {"in a Manglik house" if mg["from_lagna"] else "clear"};'
               f' from Moon — {"in a Manglik house" if mg["from_moon"] else "clear"}.</p>{_dosdont(mgd)}')
    parts.append(_sec("Manglik", MG_CHIP[mg["status"]], "Manglik — impact, dos &amp; don'ts", mg_body))

    if ss.get("active"):
        ss_fact = (f"Sade Sati is currently running ({ss.get('phase','')}), until <b>{ss.get('ends','—')}</b>. "
                   "This tends to bring a maturing pressure rather than denial — marriages formed under Saturn are "
                   "considered among the most durable.")
        if hi:
            ss_fact = (f"साढ़ेसाती अभी चल रही है ({_HI_SS_PHASE.get(ss.get('phase',''), ss.get('phase',''))}), "
                       f"<b>{_hi_date(ss.get('ends','—'))}</b> तक। यह इनकार नहीं, बल्कि परिपक्व करने वाला "
                       "दबाव लाती है — शनि के दौर में बने विवाह सबसे टिकाऊ माने जाते हैं।")
    else:
        ss_fact = (f"Sade Sati is not currently running. The next phase begins around {ss.get('next_starts','—')}. "
                   "For now, Saturn is not adding delay-pressure from this angle.")
        if hi:
            ss_fact = (f"साढ़ेसाती अभी नहीं चल रही। अगला चरण {_hi_date(ss.get('next_starts','—'))} के आसपास "
                       "शुरू होगा। फ़िलहाल शनि इस कोण से कोई देरी-दबाव नहीं डाल रहा।")
    # the fact renders once: as the LLM's note when present, else as the bank line
    parts.append(_sec("Sade Sati", "Active phase" if ss.get("active") else "Not now",
                      "Sade Sati — the Saturn cycle",
                      f'<div class="ss">{_prose(p, "sade_sati_note", ss_fact)}</div>'))

    rem = ex.get("remedies", {}) or {}
    gem_html = (f"<li><b>Gemstone:</b> {rem['gem']} — only after a trial, via a qualified jeweller/astrologer.</li>"
                if rem.get("gem") else
                (f"<li><b>Gemstone:</b> {rem['gem_note']}</li>" if rem.get("gem_note") else ""))
    rem7_html = (f"""<div class="remcard"><b>Support for your 7th lord ({rem.get('lord','')})</b>
<ul class="rem"><li><b>Fast day:</b> {rem.get('fast_day','')}</li>
<li><b>Mantra:</b> {rem.get('mantra','')} — 108 times, on {rem.get('fast_day','')}</li>{gem_html}</ul></div>"""
                 if rem else "")
    dr_html = ""
    for d in ex.get("dasha_remedies", []):
        gem = (f"<li><b>Gemstone:</b> {d['gem']} — only after expert trial.</li>" if d.get("gem")
               else "<li><b>Gemstone:</b> not advised for this period — the mantra and fast are enough.</li>")
        dr_html += (f"""<div class="remcard"><b>{d['lord']} {d['role']} · {d['from']} – {d['to']}</b>
<p class="pd">{d['reason']}</p>
<ul class="rem"><li><b>Fast day:</b> {d['fast_day']}</li>
<li><b>Mantra:</b> {d['mantra']} — 108 times, on {d['fast_day']}</li>{gem}</ul></div>""")
    if not dr_html:
        dr_html = ("<p class='soft'>No weak Mahadasha/Antardasha periods are flagged in the near term — "
                   "no period-specific remedy is needed right now.</p>")
    rn_bank = ("Remedies here are optional support, never a substitute for action. The order matters: the first "
               "remedy is always to act during your strong windows. Treat the rest as gentle reinforcement, with zero pressure.")
    if hi:
        rn_bank = ("यहाँ दिए उपाय वैकल्पिक सहारा हैं, कर्म का विकल्प कभी नहीं। क्रम मायने रखता है: पहला उपाय "
                   "हमेशा यही है कि अपनी मज़बूत विंडो में सक्रिय रहें। बाक़ी को हल्का सहारा मानिए — बिना किसी दबाव के।")
    parts.append(_sec("Remedies", "Optional", "Remedies for your dasha periods",
                      f'<p class="lead">{_prose(p, "remedies_note", rn_bank)}</p>{rem7_html}'
                      '<h2 style="font-size:18px;margin:18px 0 10px">For weak periods ahead</h2>'
                      f'{dr_html}<p class="soft">Remember the order: action first — actively looking during a strong window. '
                      'This is support, not a substitute.</p>'))

    # ============================================ THE ASTROLOGY (starts a fresh page)
    parts.append(_tier("", "The Astrology", "Every classical calculation behind this report.", cls="newpg"))

    mi_bank = ("This report uses the sidereal zodiac with the Lahiri ayanamsa and whole-sign houses — the classical "
               "Parashari framework. Every position is computed from NASA JPL ephemeris data, so any astrologer can verify it.")
    if hi:
        mi_bank = ("यह रिपोर्ट निरयन राशिचक्र, लाहिरी अयनांश और पूर्ण-राशि भाव पद्धति पर आधारित है — यही "
                   "शास्त्रीय पाराशरी ढाँचा है। हर ग्रह-स्थिति NASA JPL पंचांग-डेटा से गणना की गई है, इसलिए "
                   "कोई भी ज्योतिषी इसे जाँच सकता है।")
    parts.append(_sec("Method", "Foundations", "Method &amp; foundations",
                      f'<p class="lead">{_prose(p, "method_intro", mi_bank)}</p>'
                      f'<div class="facts"><div class="row"><span class="k">Ayanamsa</span><span class="v">{meta.get("ayanamsa","Lahiri")}</span></div>'
                      f'<div class="row"><span class="k">Houses</span><span class="v">Whole sign</span></div>'
                      f'<div class="row"><span class="k">System</span><span class="v">{"Chandra Lagna" if meta.get("system")=="chandra_lagna" else "Lagna"}</span></div>'
                      f'<div class="row"><span class="k">Birth-time quality</span><span class="v">{tq}</span></div></div>'))

    cr_bank = ("Read as a whole, your birth chart sets the stage for marriage through the balance of its planets and "
               "the strength of the houses that govern partnership.")
    if hi:
        cr_bank = ("पूरी कुंडली को एक साथ पढ़ें, तो आपके ग्रहों का संतुलन और साझेदारी के भावों की मज़बूती "
                   "मिलकर विवाह की पृष्ठभूमि तैयार करते हैं।")
    parts.append(_sec("Birth chart · D1", "Your chart", "Your birth chart (D1)",
                      f'<p class="lead">{_prose(p, "chart_reading", cr_bank)}</p>'
                      f'<div class="kwrap">{north_chart_svg(p)}<p class="kcap">Your birth chart (Kundli) · North Indian style</p></div>'))
    parts.append(report_addons.planet_table_html(p, lang))

    # Kundli-at-a-glance: the six keys of the chart with plain-language "why"
    # lines — this is the single reference card for Lagna/Moon/7th/karakas.
    ct_bank = ("At a glance, your chart sets marriage in a clear frame: the 7th house, its lord, "
               "and the natural karakas together shape both the timing and the kind of bond.")
    if hi:
        ct_bank = ("एक नज़र में, आपकी कुंडली विवाह को एक साफ़ चौखट में रखती है: सातवाँ भाव, उसका स्वामी "
                   "और स्वाभाविक कारक मिलकर समय और रिश्ते का स्वरूप — दोनों तय करते हैं।")
    glance = f"""<div class="facts">
  <div class="row"><span class="k">Lagna (ascendant)</span><span class="v">{p['chart']['lagna']}</span></div>
  <p class="why">{GLANCE_WHY['Lagna']}</p>
  <div class="row"><span class="k">Moon · Nakshatra</span><span class="v">{teaser.get('moon_sign','—')} · {teaser.get('nakshatra','—')}</span></div>
  <p class="why">{GLANCE_WHY['Moon']}</p>
  <div class="row"><span class="k">7th house</span><span class="v">{seventh_sign}</span></div>
  <p class="why">{GLANCE_WHY['7th house']}</p>
  <div class="row"><span class="k">7th lord</span><span class="v">{seventh_lord} — {DIGNITY_TXT.get(sl_dignity, sl_dignity)}</span></div>
  <p class="why">{GLANCE_WHY['7th lord']}</p>
  <div class="row"><span class="k">Marriage karaka</span><span class="v">{' + '.join(sig['karakas'])}</span></div>
  <p class="why">{GLANCE_WHY['karaka']}</p>
  <div class="row"><span class="k">Darakaraka</span><span class="v">{dk}</span></div>
  <p class="why">{GLANCE_WHY['darakaraka']}</p>
</div>"""
    parts.append(_sec("", "", "Your Kundli at a glance",
                      f'<p class="lead">{_prose(p, "chart_teaser", ct_bank)}</p>{glance}'))

    nd_bank = (f"Your Moon sits in {teaser.get('nakshatra','your birth star')} — the nakshatra colours your instincts, "
               "your emotional style, and how you approach closeness.")
    if hi:
        nd_bank = (f"आपका चंद्रमा {_hi_tok(teaser.get('nakshatra', 'आपके जन्म-नक्षत्र'))} नक्षत्र में है — "
                   "नक्षत्र आपकी सहज-प्रवृत्तियों, भावनात्मक शैली और नज़दीकी के अंदाज़ को रंग देता है।")
    parts.append(_sec("Nakshatra &amp; pada", "Birth star", "Your birth star",
                      f'<p class="lead">{_prose(p, "nakshatra_deep", nd_bank)}</p>'
                      f'<div class="card2"><b>{nakp.get("nakshatra","—")} ({nakp.get("symbol","")})</b><p>{nakp.get("nature","")}.</p></div>'))

    sh_bank = (f"The 7th house — {seventh_sign} in your chart — is the seat of marriage, partnership and commitment. "
               "It is the primary area every marriage judgement is built on.")
    if hi:
        sh_bank = (f"सातवाँ भाव — आपकी कुंडली में {_hi_tok(seventh_sign)} — विवाह, साझेदारी और प्रतिबद्धता "
                   "का स्थान है। हर विवाह-निर्णय इसी बुनियाद पर खड़ा होता है।")
    parts.append(_sec("The 7th house", "Marriage seat", "The 7th house — seat of marriage",
                      f'<p class="lead">{_prose(p, "seventh_house", sh_bank)}</p>{report_addons.occupants_html(p, lang)}'))

    sln_bank = (f"Your 7th lord is {seventh_lord}, {DIGNITY_TXT.get(sl_dignity, sl_dignity)}. Think of it as the main "
                "switch for marriage: its condition shapes the quality and clarity of the timing.")
    if hi:
        sln_bank = (f"आपके सातवें भाव का स्वामी {_hi_tok(seventh_lord)} है — "
                    f"{_hi_phrase(DIGNITY_TXT.get(sl_dignity, sl_dignity))}। इसे विवाह का मुख्य स्विच समझिए: "
                    "इसकी हालत ही समय की गुणवत्ता और स्पष्टता तय करती है।")
    parts.append(_sec("The 7th lord", "The switch", "The 7th lord — the marriage switch",
                      f'<p class="lead">{_prose(p, "seventh_lord", sln_bank)}</p>'
                      f'<div class="facts"><div class="row"><span class="k">7th lord</span><span class="v">{seventh_lord}</span></div>'
                      f'<div class="row"><span class="k">Dignity</span><span class="v">{sl_dignity}</span></div>'
                      f'<div class="row"><span class="k">House from Lagna</span><span class="v">{sl_house}</span></div></div>'))

    k_bank = ("Venus is the natural significator (karaka) of love and marriage for everyone; for a woman's chart, "
              "Jupiter joins it as the significator of the husband. Their condition supports the promise of union.")
    if hi:
        k_bank = ("शुक्र हर किसी के लिए प्रेम और विवाह का स्वाभाविक कारक है; स्त्री की कुंडली में गुरु भी पति "
                  "के कारक के रूप में जुड़ते हैं। इनकी स्थिति मिलन के वादे को सहारा देती है।")
    parts.append(_sec("Karakas", "Significators", "The marriage karakas",
                      f'<p class="lead">{_prose(p, "karakas", k_bank)}</p>'))

    dkn_bank = (f"In the Jaimini system, the darakaraka is the planet at the lowest degree — here, {dk} — and it acts "
                "as a second, independent significator of the spouse, adding another layer to the partner picture.")
    if hi:
        dkn_bank = (f"जैमिनी पद्धति में दारकारक वह ग्रह है जो सबसे कम अंश पर हो — यहाँ, {_hi_tok(dk)} — और "
                    "यह जीवनसाथी का एक दूसरा, स्वतंत्र कारक बनकर साथी की तस्वीर में एक और परत जोड़ता है।")
    parts.append(_sec("Darakaraka", "Jaimini", "Darakaraka (Jaimini)",
                      f'<p class="lead">{_prose(p, "darakaraka", dkn_bank)}</p>'))

    node_on = sig.get("node_on_7th_axis")
    na_bank = ("Rahu and Ketu on the 7th axis add a karmic dimension to relationships — often an unconventional or "
               "fated quality." if node_on else
               "In your chart, Rahu and Ketu do not fall on the 7th axis — the partnership area is free of that "
               "particular karmic overlay.")
    if hi:
        na_bank = ("राहु और केतु का सातवें अक्ष पर होना रिश्तों में एक कार्मिक आयाम जोड़ता है — अक्सर एक "
                   "अनोखा या नियति-सा जुड़ाव।" if node_on else
                   "आपकी कुंडली में राहु और केतु सातवें अक्ष पर नहीं हैं — साझेदारी का क्षेत्र उस ख़ास "
                   "कार्मिक परत से मुक्त है।")
    parts.append(_sec("The nodes", "Karmic axis", "Rahu / Ketu on the 7th axis",
                      f'<p class="lead">{_prose(p, "node_axis", na_bank)}</p>'))

    cur = p.get("current_period", {}) or {}
    # scorecard describes the top DISPLAYED window (cleaned list), never a stale
    # engine window; when it has nothing to show, don't promise it in the prose
    scorebox = report_addons.scoring_box_html({**p, "windows": windows}, lang)
    dp_bank = (f"You are currently in {cur.get('md','—')} Mahadasha / {cur.get('ad','—')} Antardasha. Your marriage "
               "windows are simply the periods within this timeline whose lords connect to your 7th house"
               + (" — which is exactly what the scorecard below shows." if scorebox else "."))
    if hi:
        dp_bank = (f"आप अभी {_hi_tok(cur.get('md','—'))} महादशा / {_hi_tok(cur.get('ad','—'))} अंतर्दशा में हैं। "
                   "आपकी विवाह-विंडोज़ इसी टाइमलाइन के वे दौर हैं जिनके स्वामी आपके सातवें भाव से जुड़ते हैं"
                   + (" — नीचे का स्कोरकार्ड ठीक यही दिखाता है।" if scorebox else "।"))
    parts.append(_sec("Dashas", "Your periods", "The dasha system &amp; your periods",
                      f'<p class="lead">{_prose(p, "dasha_periods", dp_bank)}</p>'
                      f'<div class="facts"><div class="row"><span class="k">Current Mahadasha</span><span class="v">{cur.get("md","—")}</span></div>'
                      f'<div class="row"><span class="k">Current Antardasha</span><span class="v">{cur.get("ad","—")}</span></div></div>'))
    if scorebox:
        parts.append(scorebox)

    tr_bank = ("Transits are the moving sky read against your birth chart: Jupiter is the 'go' signal that opens "
               "doors when it touches your marriage houses, while Saturn is the 'slow' signal that asks for patience.")
    if hi:
        tr_bank = ("गोचर यानी चलता आसमान, आपकी जन्म कुंडली पर पढ़ा हुआ: गुरु 'आगे बढ़ो' का संकेत है जो "
                   "आपके विवाह-भावों को छूते ही दरवाज़े खोलता है, जबकि शनि 'धीरे चलो' का संकेत है जो धैर्य माँगता है।")
    parts.append(_sec("Gochar · transits", "Go / slow", "Jupiter &amp; Saturn transits",
                      f'<p class="lead">{_prose(p, "transits", tr_bank)}</p>'))

    # the D9 add-on section is the full Navamsa chapter — no stub before it
    parts.append(report_addons.d9_section_html(p, lang))

    cn_bank = ("Whatever the dates, remember this: your chart shows a real and reachable promise of partnership. "
               "Use the timing as a guide, meet it with honest effort, and trust the process. Wishing you a warm, lasting union.")
    if hi:
        cn_bank = ("तारीख़ें जो भी हों, यह याद रखिए: आपकी कुंडली साझेदारी का एक सच्चा और पहुँच में आता वादा "
                   "दिखाती है। समय को मार्गदर्शक मानिए, उस पर ईमानदार मेहनत कीजिए, और प्रक्रिया पर भरोसा "
                   "रखिए। आपको एक गर्मजोश, टिकाऊ साथ की शुभकामनाएँ।")
    parts.append(f"""<section class="pg">
<h2>A note to you</h2>
<p class="lead">{_prose(p, 'closing_note', cn_bank)}</p>
<div class="sumcard">
  <p class="nm">{name}</p>
  {f'<p class="sline"><b>Top window:</b> {_pretty(w1["start"])} – {_pretty(w1["end"])} ({w1["grade"]})</p>' if w1 else ''}
  <p class="sline"><b>Manglik:</b> {MG_SHORT[mg['status']]}</p>
  <p class="sline"><b>Partner direction:</b> {dk}-type — see the partner pages</p>
</div>
<div class="btnrow">
  <a class="btn p" id="ax-pdf" href="#" onclick="window.print();return false;">Download PDF</a>
  <button class="ax-share" onclick="axShare()">Share on WhatsApp</button>
  <a class="btn s" href="https://wa.me/919599827297?text=Hi%20Axtroshastra">WhatsApp Support</a>
</div></section>""")

    parts.append("""<footer>Windows are probability estimates from classical dasha–transit principles,
not guarantees. <a href='https://wa.me/919599827297' style='color:inherit'>WhatsApp +91 95998 27297</a> · support@axtroshastra.com<br>Axtroshastra · Computational Vedic Astrology · by Cultnuts · <a href="/privacy" style="color:inherit">Privacy</a> · <a href="/terms" style="color:inherit">Terms</a> · <a href="/refunds" style="color:inherit">Refund Policy</a></footer>
<div class="ax-wm" aria-hidden="true"><b>AXTROSHASTRA</b><span>axtroshastra.com</span></div>
<section class="pg"><div class="ax-disc"><b>Disclaimer:</b> This report is computed from classical Vedic Jyotish (dasha–transit) principles — for guidance, not a guarantee. Timing windows are probabilities, not fixed dates. This is not legal, medical or financial advice. Make your own life decisions using your own judgement; Axtroshastra takes no responsibility for any outcome.</div><div class="ax-endcard"><b>Axtroshastra</b><br>Made with Axtroshastra — get your own report: <a href="https://www.axtroshastra.com/shaadi">axtroshastra.com</a></div></section>
</td></tr></tbody></table>""")

    head = (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{name} — Marriage Timing Report | Axtroshastra</title>'
            f'<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&display=swap" rel="stylesheet">'
            f'<style>{CSS}</style></head><body>')
    return head + "\n".join(parts) + SCRIPT + "</body></html>"
