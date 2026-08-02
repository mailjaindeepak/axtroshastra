"""
Marriage report renderer — v2 (blueprint LOCKED v2).

Rebuilds the marriage report into the four delivery tiers:
  Tier 1  Main page          — cover + the narrowest wedding-timing answer
  Tier 2  Summary (6 pp)     — the whole report, digestible
  Tier 3  Detailed report    — full depth (timing / partner / remedies)
  Tier 4  Astrology details  — every classical calculation, one topic per page

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
MG_LINE = {
    "non_manglik": "Manglik: No — no obstacle on this front.",
    "manglik_cancelled": "Manglik: technically yes, but cancelled — practically No.",
    "manglik": "Manglik: Yes — see the detail and cancellation check in the Manglik section.",
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
# CSS + tiny scripts
# --------------------------------------------------------------------------- #
CSS = """
:root{--ink:#2E2317;--midnight:#4A3A2A;--paper:#FAF4E9;--sindoor:#C0562F;
--haldi:#C79A46;--haldi-soft:#F1E4C8;--muted:#8A7A64;--line:#E7DDC9;
--display:'Bricolage Grotesque',sans-serif;--body:-apple-system,'Segoe UI',Roboto,sans-serif}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--body);background:var(--paper);color:var(--ink);line-height:1.6;font-size:17px}
.pg{max-width:640px;margin:0 auto;padding:40px 22px;border-bottom:1.5px dashed var(--line)}
.plabel{font-family:var(--display);font-weight:700;font-size:12px;text-transform:uppercase;color:var(--sindoor);margin-bottom:10px}
.shead{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:6px}
.shead .plabel{margin-bottom:0}
.chip{flex:none;font-family:var(--display);font-weight:800;font-size:12px;letter-spacing:.02em;
background:var(--haldi-soft);color:#8a5a12;border:1px solid var(--haldi);border-radius:20px;padding:4px 12px;white-space:nowrap}
h1,h2{font-family:var(--display);line-height:1.15}
h2{font-size:26px;font-weight:800;margin-bottom:14px}
p{margin-bottom:10px}
.soft{color:var(--muted);font-size:15.5px;margin-top:14px}
.lead{font-size:18px;margin-bottom:14px}
.tierhead{max-width:640px;margin:0 auto;background:var(--midnight);color:#F3EFE4;text-align:center;padding:32px 22px}
.tierhead .tn{font-family:var(--display);font-weight:800;color:var(--haldi);font-size:13px;letter-spacing:.14em;text-transform:uppercase}
.tierhead h2{color:#fff;margin:8px 0 4px}
.tierhead p{color:#C9B79C;font-size:14.5px;margin:0}
.cover{background:radial-gradient(900px 500px at 50% -10%,#5E4A32,var(--midnight));color:#F3EFE4;text-align:center;border:none}
.cover .brand{font-family:var(--display);font-weight:800;color:var(--haldi);letter-spacing:.06em;font-size:15.5px;margin-bottom:8px}
.cover .rtitle{font-family:var(--display);font-weight:700;text-transform:uppercase;letter-spacing:.14em;color:#E9E6DC;font-size:13.5px;margin-bottom:22px}
.cover h1{font-size:32px;font-weight:800;color:#fff}
.details{display:inline-block;text-align:left;background:rgba(255,255,255,.06);border:1px solid rgba(228,176,74,.4);border-radius:12px;padding:14px 18px;margin:16px auto 0}
.details .drow{display:flex;gap:14px;font-size:14.5px;padding:3px 0;color:#E9E6DC}
.details .dk{color:#C9B79C;min-width:104px}
.kchart{max-width:320px;margin:0 auto}
.cover .method{font-size:12.5px;color:#A8977F;margin-top:20px}
.hero{background:var(--midnight);color:#fff;border-radius:16px;padding:24px 22px;text-align:center;margin:4px 0 6px}
.hero-label{font-family:var(--display);font-weight:700;font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--haldi);margin-bottom:6px}
.hero-month{font-family:var(--display);font-weight:800;font-size:40px;line-height:1.05;color:#fff;margin:0}
.hero-range{font-size:14.5px;color:#D8C7AE;margin-top:6px}
.hero-conf{display:inline-block;margin-top:12px;font-family:var(--display);font-weight:800;font-size:13px;background:#2E7D53;color:#fff;border-radius:20px;padding:5px 14px}
.ans{background:#fff;border:2px solid var(--haldi);border-radius:16px;padding:20px}
.ans .plabel{color:#B8860B}
.ans-mg{margin:.55em 0 .2em;font-weight:600}
.ans-note{font-size:13px;color:var(--muted);margin-top:.6em;line-height:1.5}
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
.dd{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:14px}
.dd .col{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:14px 16px}
.dd .col.do{border-left:5px solid #2E7D53}
.dd .col.dont{border-left:5px solid #C93B2E}
.dd b{font-family:var(--display);display:block;margin-bottom:8px}
.dd ul{margin:0 0 0 16px}.dd li{font-size:15.5px;margin-bottom:6px}
@media (max-width:520px){.dd{grid-template-columns:1fr}}
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
.ax-wm{display:none;position:fixed;inset:0;z-index:9998;pointer-events:none;flex-direction:column;align-items:center;justify-content:center;transform:rotate(-28deg);opacity:.08;color:#4A3A2A;font-family:Georgia,serif}
.ax-wm b{font-size:66px;letter-spacing:.12em;line-height:1}.ax-wm span{font-size:18px;letter-spacing:.35em;margin-top:6px}
.ax-share{display:inline-block;background:#25D366;color:#fff;border:0;border-radius:10px;padding:12px 18px;font:600 15px/1 sans-serif;cursor:pointer;text-decoration:none}
.ax-disc{max-width:640px;margin:28px auto 8px;padding:14px 16px;border:1px solid #E7E0D2;border-radius:10px;background:#fbf7ef;font-size:13.5px;line-height:1.5;color:#6b6f80}
.ax-endcard{max-width:640px;margin:12px auto 28px;text-align:center;padding:18px;border-top:2px solid #E4B04A}
.ax-endcard b{font-size:18px;color:#4A3A2A}.ax-endcard a{color:#C93B2E;text-decoration:none;font-weight:600}
/* Phone-shaped page (not A4): a mobile PDF viewer fits page-width to the screen,
   so a narrow page renders ~1:1 and the text stays readable instead of being
   downscaled ~55% the way an A4 page is. */
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
.wcard,.mgcard,.quiet,.act,.ycard,.card2,.pcard,.past,.ss,.remcard,.upsell,.hero,.sumcard,.dd,.facts,.tierhead{break-inside:avoid}
.cover{break-after:page;padding:40px 22px}
.tierhead{margin-top:6px;padding:34px 22px}
h1,h2,.plabel,.shead{break-after:avoid}
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
    c = f'<span class="chip">{chip}</span>' if chip else ""
    return (f'<section class="pg"><div class="shead"><p class="plabel">{plabel}</p>{c}</div>'
            f'<h2>{h2}</h2>{body}</section>')


def _tier(n: str, title: str, sub: str) -> str:
    return (f'<section class="tierhead"><p class="tn">{n}</p>'
            f'<h2>{title}</h2><p>{sub}</p></section>')


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


def _first_word(s: str) -> str:
    return (s or "").split(",")[0].split()[0].strip().capitalize() if s else ""


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

    all_windows = p.get("windows") or []
    windows = _visible_windows(all_windows, meta)     # (#3) hide far windows when near ones exist
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
    d9_band = (nav.get("strength") or "steady").upper()
    love = ex.get("checks", {}).get("love_leaning")
    lv_line = ("Your chart leans toward a love or self-chosen match." if love
               else "Your chart leans toward an arranged or introduction-led match.")
    nature = SIGN_PARTNER.get(seventh_sign, "a well-matched partner")

    def peak_line(w):
        return (f" The strongest months look like {', '.join(w['peak_months'])}."
                if w and w.get("peak_months") else "")

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
    details = ("<div class='details'>" + "".join(
        f"<div class='drow'><span class='dk'>{k}</span><span>{escape(str(v))}</span></div>"
        for k, v in drows) + "</div>") if drows else ""
    parts.append(f"""<section class="pg cover">
  <p class="brand">✦ AXTROSHASTRA</p>
  <p class="rtitle">Marriage Timing Report</p>
  <h1>{name}</h1>
  {details}
  <div style="margin-top:22px">{north_chart_svg(p)}</div>
  <p class="method">Generated {meta.get('generated','')} · NASA JPL data (Swiss Ephemeris) · Lahiri ayanamsa · Whole-sign houses · {system_note}</p>
</section>""")

    # ---- The Answer (#2 prominent headline month + confidence) ----
    if w1:
        strongest_month = w1["peak_months"][0] if w1.get("peak_months") else _pretty(w1["core_start"])
        conf, conf_note = _confidence(w1["grade"], tq)
        ts_bank = (f"Your strongest window for marriage is {_pretty(w1['start'])}–{_pretty(w1['end'])} "
                   f"({w1['grade']}).{peak_line(w1)} Everything that follows explains why, and what to do about it.")
        after = (f"<p class='sline' style='color:var(--muted)'>After that: {_pretty(w2['start'])} – {_pretty(w2['end'])} ({w2['grade']})</p>"
                 if w2 else "")
        hero = (f'<div class="hero"><p class="hero-label">Most likely marriage window</p>'
                f'<p class="hero-month">{strongest_month}</p>'
                f'<p class="hero-range">Full window: {_pretty(w1["start"])} – {_pretty(w1["end"])}</p>'
                f'<span class="hero-conf">{conf} confidence{conf_note}</span></div>')
        parts.append(f"""<section class="pg"><div class="ans">
<p class="plabel">Your answer — at a glance</p>
<h2>When will you get married?</h2>
{hero}
<p class="lead">{_prose(p, 'top_summary', ts_bank)}</p>
{after}
<p class="ans-mg">{MG_LINE[mg['status']]}</p>
<p class="ans-note">This answer comes from your full chart. The rest of the report shows every window, your Navamsa, and your past periods — so you can check it yourself.</p>
</div></section>""")

    # ============================================ TIER 2 — summary
    parts.append(_tier("Tier 2", "Summary", "The whole report, in six pages."))

    wi_bank = (f"You have {len(windows)} marriage window{'s' if len(windows) != 1 else ''} on the horizon. "
               "Think of them as a timeline of higher-probability phases, not fixed dates.")
    quick = "".join(_window_card(i, w, deep=False) for i, w in enumerate(windows, 1))
    parts.append(_sec("The answer", f"{len(windows)} window{'s' if len(windows)!=1 else ''}",
                      "Your marriage windows",
                      f'<p class="lead">{_prose(p, "windows_intro", wi_bank)}</p>{_timeline_html(windows, meta)}{quick}'))

    ct_bank = ("At a glance, your chart sets marriage in a clear frame: the 7th house, its lord, "
               "and the natural karakas together shape both the timing and the kind of bond.")
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
    parts.append(_sec("Chart snapshot", "Snapshot", "Your Kundli at a glance",
                      f'<p class="lead">{_prose(p, "chart_teaser", ct_bank)}</p>{glance}'))

    pt_bank = (f"Your indications point to {nature}. Where and how you meet is written into the chart too — "
               "the detailed pages draw the full picture.")
    person_cards = (f'<div class="pcard"><span class="pk">Nature</span><p>{nature}.</p></div>'
                    f'<div class="pcard"><span class="pk">Love vs Arranged</span><p>{lv_line}</p></div>')
    parts.append(_sec("Your person", _first_word(nature), "Your potential partner",
                      f'<p class="lead">{_prose(p, "partner_teaser", pt_bank)}</p>{person_cards}'))

    past_n = len(ex.get("past", []))
    st_bank = ("If it hasn't happened yet, your past periods usually explain why — the timing simply "
               "wasn't activated. The good news is that momentum is turning toward your windows ahead.")
    parts.append(_sec("Your timing story", "Turning", "Why not yet — and what's changing",
                      f'<p class="lead">{_prose(p, "story_teaser", st_bank)}</p>'
                      f'<p class="soft">The detailed report breaks down your last {max(past_n,3)} years period by period, and the next three years month by month.</p>'))

    ss = ex.get("sade_sati", {}) or {}
    ss_status = "currently running" if ss.get("active") else "not currently running"
    big_q = f"""<div class="facts">
  <div class="row"><span class="k">Manglik</span><span class="v">{MG_SHORT[mg['status']]}</span></div>
  <div class="row"><span class="k">Sade Sati</span><span class="v">{ss_status}</span></div>
  <div class="row"><span class="k">Navamsa promise</span><span class="v">{d9_band}</span></div>
</div><p class="soft">Each of these has its own detailed page ahead, with the reasoning and what it means for you.</p>"""
    parts.append(_sec("The big questions", "3 checks", "The three things everyone asks", big_q))

    at_bank = ("The single most useful thing right now is to line up your effort with your timing — "
               "lean in during strong windows, and prepare during the quiet ones.")
    parts.append(_sec("Your move", "Act", "What to do now",
                      f'<p class="lead">{_prose(p, "action_teaser", at_bank)}</p>'))

    # ============================================ TIER 3 — detailed
    parts.append(_tier("Tier 3", "Detailed Report", "Full depth on your timing, your partner, and your remedies."))

    if w1:
        w1_bank = (f"Your strongest window runs {_pretty(w1['start'])}–{_pretty(w1['end'])} and grades {w1['grade']}. "
                   "It lights up because the running periods connect directly to your house of marriage, and the "
                   "supporting transits back them up.")
        parts.append(_sec("Window 1", "Strongest", "Your strongest window",
                          f'<p class="lead">{_prose(p, "window_1", w1_bank)}</p>{_window_card(1, w1)}'))
    if w2:
        w2_bank = (f"Your second window, {_pretty(w2['start'])}–{_pretty(w2['end'])} ({w2['grade']}), is a distinct "
                   "opportunity with its own driving periods — useful if the first passes or as a second run at it.")
        parts.append(_sec("Window 2", "Second", "Your second window",
                          f'<p class="lead">{_prose(p, "window_2", w2_bank)}</p>{_window_card(2, w2)}'))
    if w3:
        w3_bank = (f"A third window opens {_pretty(w3['start'])}–{_pretty(w3['end'])} ({w3['grade']}) — the longer "
                   "arc, worth keeping on your radar.")
        parts.append(_sec("Window 3", "Longer arc", "Your third window",
                          f'<p class="lead">{_prose(p, "window_3", w3_bank)}</p>{_window_card(3, w3)}'))

    as_bank = ("In a strong or moderate window, the odds of a match converting are at their highest — so this is "
               "the time to say yes to meetings, involve family, and not postpone decisions that feel right.")
    acts = ""
    for i, w in enumerate(windows, 1):
        head, body = GRADE_ACTION.get(w["grade"], ("Stay active.", ""))
        acts += (f"<div class='act'><b>Window {i} ({_pretty(w['start'])} – {_pretty(w['end'])}): {head}</b>"
                 f"<p>{body}</p></div>")
    parts.append(_sec("Action plan", "Lean in", "What you need to do for better results",  # (#7)
                      f'<p class="lead">{_prose(p, "action_strong", as_bank)}</p>{acts}'
                      '<p class="soft">Your chart shows the timing; the effort and the choice stay in your hands. '
                      'Even in a strong window you still have to look — the conversion rate is just far better.</p>'))

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
    aw_bank = WEAK_PERIOD_ACTION["line"]
    weak_rows = "".join(
        f"<div class='quiet'><b>{lab}</b><p>A low-activation phase — matches may come but tend not to convert. "
        f"Delays here are pattern, not personal failure.</p></div>" for lab in weak_labels)
    parts.append(_sec("Quiet periods", "Prepare", "Make your quiet phases count",  # (#8)
                      f'<p class="lead">{_prose(p, "action_weak", aw_bank)}</p>{weak_rows}{_dosdont(WEAK_PERIOD_ACTION)}'))

    past_rows = ""
    lbl = {"active": ("#2E7D53", "ACTIVE"), "mild": ("#E4B04A", "MILD"), "quiet": ("#A8977F", "QUIET")}
    for pp in ex.get("past", []):
        c, t = lbl.get(pp["label"], ("#A8977F", pp["label"].upper()))
        past_rows += (f"<div class='past'><span class='pl' style='background:{c}'>{t}</span>"
                      f"<b>{pp['from']} – {pp['to']}</b><p class='pd'>{_expand_dasha(pp['dasha'])}</p>"
                      f"<p class='pw'>{' · '.join(pp['why'])}</p></div>")
    pp_bank = ("Looking back, the periods that passed quietly did so because the timing simply wasn't activated for "
               "marriage — not because of anything you did or didn't do. That distinction matters.")
    parts.append(_sec("Past years", "Why not yet", "Why it hasn't happened yet",
                      f'<p class="lead">{_prose(p, "past_pattern", pp_bank)}</p>{past_rows}'))

    y_rows = ""
    for y in ex.get("year_outlook", []):
        gr = (f"<span class='ygrade' style='background:{GRADE_COLOR[y['grade']]}'>{y['grade'].upper()} WINDOW</span>"
              if y.get("grade") else "<span class='ygrade' style='background:#A8977F'>NO MAJOR WINDOW</span>")
        jup = ("Jupiter's transit this year sits in supportive houses — it helps carry conversations forward."
               if y.get("jupiter_supportive") else
               "Jupiter's transit this year is neutral — lean a little more on effort than on luck.")
        fav = (f"<p class='yfav'>⭐ Favourable months: {', '.join(y['fav_months'])}</p>" if y.get("fav_months") else "")
        y_rows += (f"<div class='ycard'><div class='ytop'><b>{y['year']}</b>{gr}</div>"
                   f"<p class='yd'>{' / '.join(y.get('dashas', []))}</p><p>{jup}</p>{fav}</div>")
    ol_bank = ("Across the next three years the momentum builds toward your windows — watch the favourable months, "
               "and treat the quieter stretches as preparation time.")
    parts.append(_sec("Year by year", "Next 3 yrs", "The next three years",
                      f'<p class="lead">{_prose(p, "outlook", ol_bank)}</p>{y_rows}'))

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
    else:
        ss_fact = (f"Sade Sati is not currently running. The next phase begins around {ss.get('next_starts','—')}. "
                   "For now, Saturn is not adding delay-pressure from this angle.")
    parts.append(_sec("Sade Sati", "Active phase" if ss.get("active") else "Not now",
                      "Sade Sati — the Saturn cycle",
                      f'<p class="lead">{_prose(p, "sade_sati_note", ss_fact)}</p><div class="ss">{ss_fact}</div>'))

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
    parts.append(_sec("Remedies", "Optional", "Remedies for your dasha periods",
                      f'<p class="lead">{_prose(p, "remedies_note", rn_bank)}</p>{rem7_html}'
                      '<h2 style="font-size:18px;margin:18px 0 10px">For weak periods ahead</h2>'
                      f'{dr_html}<p class="soft">Remember the order: action first — actively looking during a strong window. '
                      'This is support, not a substitute.</p>'))

    pp2_bank = f"Your 7th sign, {seventh_sign}, points to {nature}."
    parts.append(_sec("Your partner", _first_word(nature), "Their likely personality",
                      f'<p class="lead">{_prose(p, "partner_personality", pp2_bank)}</p>'
                      f'<div class="pcard"><span class="pk">Nature</span><p>{nature}.</p></div>'))

    meet = MEETING_EN[sl_house - 1] if 1 <= sl_house <= 12 else "your own circles"
    foreign = ex.get("checks", {}).get("foreign_or_intercommunity")
    for_line = ("There is also a signature for a partner from a different community, background, or place."
                if foreign else "The indications lean toward your own circle and community.")
    mc_bank = (f"Your darakaraka {dk} suggests {DK_PARTNER.get(dk,'a compatible partner')}. The 7th lord's placement "
               f"points to meeting {meet}. {lv_line} {for_line}")
    parts.append(_sec("How you'll meet", "Love" if love else "Arranged", "Their background &amp; how you'll meet",
                      f'<p class="lead">{_prose(p, "meeting_context", mc_bank)}</p>'
                      f'<div class="pcard"><span class="pk">Love vs Arranged</span><p>{lv_line}</p></div>'
                      f'<div class="pcard"><span class="pk">Darakaraka ({dk})</span><p>{DK_PARTNER.get(dk,"—")}.</p></div>'
                      f'<div class="pcard"><span class="pk">Meeting context</span><p>The connection may come through {meet}.</p></div>'
                      '<p class="soft">These are indications, not a portrait — the chart gives the direction; life fills in the detail.</p>'))

    nakp = ex.get("nak_profile", {}) or {}
    lp_bank = (f"With your Moon in {nakp.get('nakshatra','your birth star')} and your Venus placement, "
               f"{nakp.get('relationship','you love with care and depth')}.")
    parts.append(_sec("Your pattern", _first_word(ex.get("venus_style", "")) or "Your love", "How you love",
                      f'<p class="lead">{_prose(p, "love_pattern", lp_bank)}</p>'
                      f'<div class="card2"><b>Your nakshatra: {nakp.get("nakshatra","—")} ({nakp.get("symbol","")})</b>'
                      f'<p>{nakp.get("nature","")}.</p><p style="margin-top:8px">{nakp.get("relationship","")}.</p></div>'
                      f'<div class="card2"><b>Your Venus</b><p>Your love-style is {ex.get("venus_style","—")}.</p></div>'))

    # ============================================ TIER 4 — astrology
    parts.append(_tier("Tier 4", "The Astrology", "Every classical calculation behind this report."))

    mi_bank = ("This report uses the sidereal zodiac with the Lahiri ayanamsa and whole-sign houses — the classical "
               "Parashari framework. Every position is computed from NASA JPL ephemeris data, so any astrologer can verify it.")
    parts.append(_sec("Method", "Foundations", "Method &amp; foundations",
                      f'<p class="lead">{_prose(p, "method_intro", mi_bank)}</p>'
                      f'<div class="facts"><div class="row"><span class="k">Ayanamsa</span><span class="v">{meta.get("ayanamsa","Lahiri")}</span></div>'
                      f'<div class="row"><span class="k">Houses</span><span class="v">Whole sign</span></div>'
                      f'<div class="row"><span class="k">System</span><span class="v">{"Chandra Lagna" if meta.get("system")=="chandra_lagna" else "Lagna"}</span></div>'
                      f'<div class="row"><span class="k">Birth-time quality</span><span class="v">{tq}</span></div></div>'))

    cr_bank = ("Read as a whole, your birth chart sets the stage for marriage through the balance of its planets and "
               "the strength of the houses that govern partnership.")
    parts.append(_sec("Birth chart · D1", "Your chart", "Your birth chart (D1)",
                      f'<p class="lead">{_prose(p, "chart_reading", cr_bank)}</p>'
                      f'<div style="text-align:center">{north_chart_svg(p)}</div>'))
    parts.append(report_addons.planet_table_html(p, lang))

    lm_bank = ("Two lenses matter most: the Lagna (ascendant) governs your body, personality and the frame of the "
               "whole chart, while the Moon governs your mind and emotions — and drives your dasha timeline.")
    parts.append(_sec("Lagna &amp; Moon", "Two lenses", "Lagna &amp; Moon",
                      f'<p class="lead">{_prose(p, "lagna_moon", lm_bank)}</p>'
                      f'<div class="facts"><div class="row"><span class="k">Lagna</span><span class="v">{p["chart"]["lagna"]}</span></div>'
                      f'<div class="row"><span class="k">Moon sign · Nakshatra</span><span class="v">{teaser.get("moon_sign","—")} · {teaser.get("nakshatra","—")}</span></div></div>'))

    ps_bank = ("Each planet's dignity — whether it sits in its own sign, exalted, debilitated or neutral — tells you "
               "how freely it can act. Strong dignities support clear timing; weaker ones simply ask for more patience.")
    parts.append(_sec("The nine planets", "9 planets", "The nine planets",
                      f'<p class="lead">{_prose(p, "planet_strengths", ps_bank)}</p>'
                      '<p class="soft">The full placement table with each planet\'s sign, nakshatra, house and state is on the birth-chart page above.</p>'))

    nd_bank = (f"Your Moon sits in {teaser.get('nakshatra','your birth star')} — the nakshatra colours your instincts, "
               "your emotional style, and how you approach closeness.")
    parts.append(_sec("Nakshatra &amp; pada", "Birth star", "Your birth star",
                      f'<p class="lead">{_prose(p, "nakshatra_deep", nd_bank)}</p>'
                      f'<div class="card2"><b>{nakp.get("nakshatra","—")} ({nakp.get("symbol","")})</b><p>{nakp.get("nature","")}.</p></div>'))

    sh_bank = (f"The 7th house — {seventh_sign} in your chart — is the seat of marriage, partnership and commitment. "
               "It is the primary area every marriage judgement is built on.")
    parts.append(_sec("The 7th house", "Marriage seat", "The 7th house — seat of marriage",
                      f'<p class="lead">{_prose(p, "seventh_house", sh_bank)}</p>{report_addons.occupants_html(p, lang)}'))

    sln_bank = (f"Your 7th lord is {seventh_lord}, {DIGNITY_TXT.get(sl_dignity, sl_dignity)}. Think of it as the main "
                "switch for marriage: its condition shapes the quality and clarity of the timing.")
    parts.append(_sec("The 7th lord", "The switch", "The 7th lord — the marriage switch",
                      f'<p class="lead">{_prose(p, "seventh_lord", sln_bank)}</p>'
                      f'<div class="facts"><div class="row"><span class="k">7th lord</span><span class="v">{seventh_lord}</span></div>'
                      f'<div class="row"><span class="k">Dignity</span><span class="v">{sl_dignity}</span></div>'
                      f'<div class="row"><span class="k">House from Lagna</span><span class="v">{sl_house}</span></div></div>'))

    k_bank = ("Venus is the natural significator (karaka) of love and marriage for everyone; for a woman's chart, "
              "Jupiter joins it as the significator of the husband. Their condition supports the promise of union.")
    parts.append(_sec("Karakas", "Significators", "The marriage karakas",
                      f'<p class="lead">{_prose(p, "karakas", k_bank)}</p>'
                      f'<div class="facts"><div class="row"><span class="k">Karaka(s)</span><span class="v">{" + ".join(sig["karakas"])}</span></div></div>'))

    dkn_bank = (f"In the Jaimini system, the darakaraka is the planet at the lowest degree — here, {dk} — and it acts "
                "as a second, independent significator of the spouse, adding another layer to the partner picture.")
    parts.append(_sec("Darakaraka", "Jaimini", "Darakaraka (Jaimini)",
                      f'<p class="lead">{_prose(p, "darakaraka", dkn_bank)}</p>'
                      f'<div class="card2"><b>{dk}</b><p>{DK_PARTNER.get(dk,"—")}.</p></div>'))

    node_on = sig.get("node_on_7th_axis")
    na_bank = ("Rahu and Ketu on the 7th axis add a karmic dimension to relationships — often an unconventional or "
               "fated quality." if node_on else
               "In your chart, Rahu and Ketu do not fall on the 7th axis — the partnership area is free of that "
               "particular karmic overlay.")
    parts.append(_sec("The nodes", "Karmic axis", "Rahu / Ketu on the 7th axis",
                      f'<p class="lead">{_prose(p, "node_axis", na_bank)}</p>'))

    cur = p.get("current_period", {}) or {}
    dp_bank = (f"You are currently in {cur.get('md','—')} Mahadasha / {cur.get('ad','—')} Antardasha. Your marriage "
               "windows are simply the periods within this timeline whose lords connect to your 7th house — which is "
               "exactly what the scorecard below shows.")
    parts.append(_sec("Dashas", "Your periods", "The dasha system &amp; your periods",
                      f'<p class="lead">{_prose(p, "dasha_periods", dp_bank)}</p>'
                      f'<div class="facts"><div class="row"><span class="k">Current Mahadasha</span><span class="v">{cur.get("md","—")}</span></div>'
                      f'<div class="row"><span class="k">Current Antardasha</span><span class="v">{cur.get("ad","—")}</span></div></div>'))
    parts.append(report_addons.scoring_box_html(p, lang))

    tr_bank = ("Transits are the moving sky read against your birth chart: Jupiter is the 'go' signal that opens "
               "doors when it touches your marriage houses, while Saturn is the 'slow' signal that asks for patience.")
    parts.append(_sec("Gochar · transits", "Go / slow", "Jupiter &amp; Saturn transits",
                      f'<p class="lead">{_prose(p, "transits", tr_bank)}</p>'))

    nr_bank = ("The Navamsa (D9) is the marriage-promise chart — it shows how solid and how lasting the union is, "
               f"beyond mere timing. Your D9 reads as a {(nav.get('strength') or 'steady')} promise.")
    parts.append(_sec("Navamsa · D9", d9_band.title(), "The Navamsa (D9)",
                      f'<p class="lead">{_prose(p, "navamsa_reading", nr_bank)}</p>'))
    parts.append(report_addons.d9_section_html(p, lang))

    cn_bank = ("Whatever the dates, remember this: your chart shows a real and reachable promise of partnership. "
               "Use the timing as a guide, meet it with honest effort, and trust the process. Wishing you a warm, lasting union.")
    parts.append(f"""<section class="pg"><div class="shead"><p class="plabel">Closing</p><span class="chip">For you</span></div>
<h2>A note to you</h2>
<p class="lead">{_prose(p, 'closing_note', cn_bank)}</p>
<div class="sumcard">
  <p class="nm">{name}</p>
  {f'<p class="sline"><b>Top window:</b> {_pretty(w1["start"])} – {_pretty(w1["end"])} ({w1["grade"]})</p>' if w1 else ''}
  <p class="sline"><b>Manglik:</b> {MG_SHORT[mg['status']]}</p>
  <p class="sline"><b>Partner direction:</b> {dk}-type — see the partner pages</p>
</div>
<div class="upsell"><b>One more question, from the same chart: when will your career lift?</b>
<p>Career Timing Report — same precision, ₹299 for report holders. <a href="https://wa.me/919599827297?text=CAREER" style="color:#C93B2E;font-weight:700">Send CAREER on WhatsApp →</a></p></div>
<div class="btnrow">
  <a class="btn p" id="ax-pdf" href="#" onclick="window.print();return false;">Download PDF</a>
  <button class="ax-share" onclick="axShare()">Share on WhatsApp</button>
  <a class="btn s" href="https://wa.me/919599827297?text=Hi%20Axtroshastra">WhatsApp Support</a>
</div></section>""")

    parts.append("""<footer>Windows are probability estimates from classical dasha–transit principles,
not guarantees. <a href='https://wa.me/919599827297' style='color:inherit'>WhatsApp +91 95998 27297</a> · support@axtroshastra.com<br>Axtroshastra · Computational Vedic Astrology · by Cultnuts · <a href="/privacy" style="color:inherit">Privacy</a> · <a href="/terms" style="color:inherit">Terms</a> · <a href="/refunds" style="color:inherit">Refund Policy</a></footer>
<div class="ax-wm" aria-hidden="true"><b>AXTROSHASTRA</b><span>axtroshastra.com</span></div>
<section class="pg"><div class="ax-disc"><b>Disclaimer:</b> This report is computed from classical Vedic Jyotish (dasha–transit) principles — for guidance, not a guarantee. Timing windows are probabilities, not fixed dates. This is not legal, medical or financial advice. Make your own life decisions using your own judgement; Axtroshastra takes no responsibility for any outcome.</div><div class="ax-endcard"><b>Axtroshastra</b><br>Made with Axtroshastra — get your own report: <a href="https://www.axtroshastra.com/shaadi">axtroshastra.com</a></div></section>""")

    head = (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{name} — Marriage Timing Report | Axtroshastra</title>'
            f'<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&display=swap" rel="stylesheet">'
            f'<style>{CSS}</style></head><body>')
    return head + "\n".join(parts) + SCRIPT + "</body></html>"
