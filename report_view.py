"""
AstroShastra report renderer — 9-page mobile-first report from engine JSON.
Deterministic templates only; every fact comes from the payload.
LLM narrative layer can later replace individual section texts via the same slots.
"""
from datetime import datetime

SIGNS = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
         "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena"]
SIGN_NUM = {s: i for i, s in enumerate(SIGNS)}

# ---- partner-indication vocab (classical, bounded, warm) ----
SIGN_PARTNER = {
    "Mesha": "direct, energetic, quick to decide — someone who takes initiative",
    "Vrishabha": "steady, comfort-loving, loyal — someone who values stability and family",
    "Mithuna": "communicative, witty, sociable — someone you can talk to for hours",
    "Karka": "caring, family-oriented, emotionally deep — a nurturing presence",
    "Simha": "confident, warm, dignified — someone with presence and generosity",
    "Kanya": "practical, detail-minded, helpful — someone organised and sincere",
    "Tula": "balanced, charming, partnership-minded — marriage matters deeply to them",
    "Vrishchika": "intense, private, deeply loyal — a bond that runs deep once formed",
    "Dhanu": "optimistic, principled, freedom-loving — someone with strong beliefs",
    "Makara": "responsible, ambitious, mature — often settled or career-established",
    "Kumbha": "independent, idealistic, unconventional — a friend first",
    "Meena": "gentle, intuitive, adaptable — emotionally giving and artistic",
}
DK_PARTNER = {
    "Sun": "a dignified, self-respecting partner, possibly from an established family",
    "Moon": "an emotionally attuned, caring partner; family approval flows easily",
    "Mars": "an energetic, protective partner with strong drive",
    "Mercury": "a younger-feeling, intelligent, talkative partner",
    "Jupiter": "a wise, well-educated, principled partner — often traditional values",
    "Venus": "an attractive, artistic, pleasure-loving partner; strong mutual affection",
    "Saturn": "a mature, dutiful, patient partner — possibly older or met later",
}
GRADE_ACTION = {
    "Strong": ("Lean in.", "Treat serious conversations in this period seriously — "
               "involve family early, say yes to meetings, and don't postpone "
               "decisions that feel right. This is your highest-activation phase."),
    "Moderate": ("Stay active.", "Keep profiles current and meetings on — matches "
                 "formed here can absolutely convert, especially in the strongest "
                 "months. Don't force outcomes; do keep doors open."),
    "Building": ("Prepare.", "Use this phase to get ready — clarity on what you "
                 "want, conversations with family, self-work. Momentum built here "
                 "pays off in the next stronger window."),
}
GRADE_COLOR = {"Strong": "#C93B2E", "Moderate": "#E4B04A", "Building": "#8F92AB"}

# North Indian chart: house polygon centers (viewBox 0 0 400 400), houses 1-12
HOUSE_POS = {1: (200, 105), 2: (105, 58), 3: (55, 105), 4: (105, 200),
             5: (55, 295), 6: (105, 345), 7: (200, 295), 8: (295, 345),
             9: (345, 295), 10: (295, 200), 11: (345, 105), 12: (295, 58)}
PLANET_ABBR = {"Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me",
               "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa",
               "Rahu": "Ra", "Ketu": "Ke"}


def _houses_from(ref: int, target: int) -> int:
    return ((target - ref) % 12) + 1


def north_chart_svg(payload: dict) -> str:
    lagna = SIGN_NUM[payload["chart"]["lagna"]]
    by_house = {h: [] for h in range(1, 13)}
    for pname, pdata in payload["chart"]["planets"].items():
        h = _houses_from(lagna, SIGN_NUM[pdata["sign"]])
        tag = PLANET_ABBR[pname] + ("↺" if pdata["retro"] and pname not in ("Rahu", "Ketu") else "")
        by_house[h].append(tag)
    cells = []
    for h, (cx, cy) in HOUSE_POS.items():
        sign_num = ((lagna + h - 1) % 12) + 1
        cells.append(f"<text x='{cx}' y='{cy-16}' class='sn'>{sign_num}</text>")
        row = " ".join(by_house[h][:4])
        if row:
            cells.append(f"<text x='{cx}' y='{cy+6}' class='pl'>{row}</text>")
        if len(by_house[h]) > 4:
            cells.append(f"<text x='{cx}' y='{cy+24}' class='pl'>{' '.join(by_house[h][4:])}</text>")
    return f"""<svg viewBox="0 0 400 400" class="kchart" role="img" aria-label="Birth chart">
<rect x="8" y="8" width="384" height="384" fill="none" stroke="#E4B04A" stroke-width="2"/>
<path d="M8 8 L392 392 M392 8 L8 392" stroke="#E4B04A" stroke-width="1.5" fill="none"/>
<path d="M200 8 L392 200 L200 392 L8 200 Z" stroke="#E4B04A" stroke-width="2" fill="none"/>
<style>.sn{{font:600 13px sans-serif;fill:#8F92AB;text-anchor:middle}}
.pl{{font:800 15px sans-serif;fill:#F3EFE4;text-anchor:middle}}</style>
{''.join(cells)}</svg>"""


def _weak_periods(payload: dict) -> list:
    """Gaps > 10 months between consecutive windows inside the horizon."""
    ws = payload["windows"]
    if not ws:
        return []
    fmt = lambda s: datetime.strptime(s, "%Y-%m")
    gaps, hz = [], payload["teaser"]["horizon"]
    prev_end = fmt(f"{hz[0]}-01")
    bounds = [(fmt(w["start"]), fmt(w["end"])) for w in ws] + [(fmt(f"{hz[1]}-01"),) * 2]
    for (s, e) in bounds:
        if (s - prev_end).days > 300:
            gaps.append((prev_end.strftime("%b %Y"), s.strftime("%b %Y")))
        prev_end = max(prev_end, e)
    return gaps[:2]


def render_report(p: dict) -> str:
    meta, sig, mg = p["meta"], p["significators"], p["manglik"]
    name = meta["name"]
    system_note = ("Chandra Lagna system (Moon-as-ascendant) — the classical Parashari "
                   "method used when birth time is approximate. Fully traditional; "
                   "windows are shown with honest wider ranges."
                   if meta["system"] == "chandra_lagna" else
                   "Lagna-based analysis with full house precision.")

    # ---- page 3: windows + timeline ----
    hz = p["teaser"]["horizon"]
    tl_windows = ""
    for i, w in enumerate(p["windows"]):
        s = datetime.strptime(w["start"], "%Y-%m"); e = datetime.strptime(w["end"], "%Y-%m")
        left = max(0, (s - datetime(hz[0], 1, 1)).days / ((hz[1] - hz[0]) * 365.25) * 100)
        width = max(6, (e - s).days / ((hz[1] - hz[0]) * 365.25) * 100)
        tl_windows += (f"<div class='tlw' style='left:{left:.1f}%;width:{min(width, 100-left):.1f}%;"
                       f"background:{GRADE_COLOR[w['grade']]}'></div>")
    years_axis = "".join(f"<span>{y}</span>" for y in range(hz[0], hz[1] + 1, 2))

    window_cards = ""
    for i, w in enumerate(p["windows"], 1):
        pretty = lambda ym: datetime.strptime(ym, "%Y-%m").strftime("%b %Y")
        core = (f"<p class='core'>Core period: {pretty(w['core_start'])} – {pretty(w['core_end'])}</p>"
                if w["start"] != w["core_start"] else "")
        peak = (f"<p class='peak'>⭐ Strongest months: {', '.join(w['peak_months'])}</p>"
                if w["peak_months"] else "")
        reasons = "".join(f"<li>{r['why']}</li>" for r in w["rules_fired"]
                          if not r["id"].startswith(("AD_WEAK", "AD_DRY", "TR_SAT")))[:600]
        window_cards += f"""
<div class="wcard" style="border-left-color:{GRADE_COLOR[w['grade']]}">
  <div class="wtop"><span class="wnum">Window {i}</span>
  <span class="wgrade" style="background:{GRADE_COLOR[w['grade']]}">{w['grade'].upper()}</span></div>
  <p class="wdates">{pretty(w['start'])} → {pretty(w['end'])}</p>
  {core}{peak}
  <p class="wdasha">{w['dasha']}</p>
  <ul class="wwhy">{reasons}</ul>
</div>"""

    # ---- page 5: manglik ----
    mg_head = {"non_manglik": "Aap manglik nahi hain ✅",
               "manglik_cancelled": "Manglik placement hai — par cancelled hai ✅",
               "manglik": "Manglik placement hai — calmly samjhiye"}[mg["status"]]
    mg_body = {
        "non_manglik": "Mars aapke chart mein manglik houses (1, 2, 4, 7, 8, 12) mein "
                       "nahi hai — lagna se bhi, Moon se bhi. Rishtey ki baat-cheet mein "
                       "yeh sawaal aaye toh confidently 'nahi' kah sakte hain.",
        "manglik_cancelled": "Mars manglik position mein hai, lekin classical cancellation "
                             "rules apply hote hain: <b>" + ", ".join(mg["cancellations"]) +
                             "</b>. Tradition mein cancelled manglik ko manglik nahi mana "
                             "jaata — matching mein isse issue nahi banna chahiye.",
        "manglik": "Mars manglik houses mein hai. Yeh koi shraap nahi hai — classical "
                   "texts iske liye simple remedial framing dete hain, aur manglik-manglik "
                   "matching mein yeh neutral ho jaata hai. Dar ki nahi, jaankari ki baat hai.",
    }[mg["status"]]

    # ---- page 6: weak periods ----
    weak = _weak_periods(p)
    weak_html = ""
    if weak:
        rows = "".join(f"<div class='quiet'><b>{a} – {b}</b><p>Low-activation phase: "
                       f"matches may come but tend not to convert. Delays here are "
                       f"pattern, not personal failure.</p></div>" for a, b in weak)
        weak_html = f"""
<section class="pg"><p class="plabel">Page 6</p>
<h2>Quiet periods — aur unka matlab</h2>
<p>Jitna important yeh jaanna hai ki kab yog strong hai, utna hi yeh ki kab नहीं hai.
In periods mein rishtey aa sakte hain, par convert hone ka pattern weak rehta hai:</p>
{rows}
<p class="soft">Agar pichhle saalon mein baat banti-banti reh gayi ho — chart mein
aksar uski wajah dikh jaati hai. Yeh aapki kami nahi thi; timing thi.</p></section>"""

    # ---- page 7: partner ----
    seventh_sign = sig["seventh_sign"]
    partner_html = f"""
<p><b>7th house — {seventh_sign}:</b> {SIGN_PARTNER[seventh_sign]}.</p>
<p><b>Darakaraka {sig['darakaraka']}:</b> indications of {DK_PARTNER[sig['darakaraka']]}.</p>
<p><b>Meeting context:</b> {"7th lord in house " + str(sig['seventh_lord_house']) +
" suggests the connection may come through that area of life — " +
["self-initiated or through your own efforts", "family networks or finances",
 "siblings, neighbours, or short travels", "home circle or mother's side",
 "social settings, children's events, or romance first", "workplace or daily circles",
 "direct proposals — partnership-driven", "in-law networks or transformative settings",
 "distant places, education circles, or a different community",
 "career settings or father's network", "friends' circles — a friend's introduction",
 "quiet or private settings, possibly at some distance"][sig['seventh_lord_house']-1] + "."}</p>
<p class="soft">Yeh indications hain, portrait nahi — chart directions batata hai,
details zindagi bharti hai.</p>"""

    # ---- page 8: actions ----
    actions = ""
    for i, w in enumerate(p["windows"], 1):
        head, body = GRADE_ACTION[w["grade"]]
        pretty = lambda ym: datetime.strptime(ym, "%Y-%m").strftime("%b %Y")
        actions += (f"<div class='act'><b>Window {i} ({pretty(w['start'])} – "
                    f"{pretty(w['end'])}): {head}</b><p>{body}</p></div>")

    # ---- page 9: summary ----
    w1 = p["windows"][0] if p["windows"] else None
    pretty = lambda ym: datetime.strptime(ym, "%Y-%m").strftime("%b %Y")
    summary = (f"<p class='sline'><b>Top window:</b> {pretty(w1['start'])} – "
               f"{pretty(w1['end'])} ({w1['grade']})</p>" if w1 else "")
    mg_short = {"non_manglik": "No", "manglik_cancelled": "Cancelled (effectively no)",
                "manglik": "Yes — see page 5"}[mg["status"]]

    rectify_hook = ""
    if meta["time_quality"] in ("T1", "T2", "T3"):
        rectify_hook = """<div class="upsell"><b>Birth time approximate tha?</b>
<p>Rectification analysis aapke life events se exact time narrow karta hai —
windows 6 months tak refine ho sakte hain. WhatsApp par 'RECTIFY' likhiye.</p></div>"""

    facts = p["chart"]["planets"]
    sl = sig["seventh_lord"]
    sl_d = facts[sl]["dignity"]
    dignity_txt = {"own": "apne hi sign mein — strong placement",
                   "exalted": "exalted — best possible dignity",
                   "debilitated": "debilitated — timing par extra dhyaan",
                   "neutral": "neutral dignity"}[sl_d]

    return f"""<!DOCTYPE html><html lang="hi-IN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} — Marriage Timing Report | AstroShastra</title>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&display=swap" rel="stylesheet">
<style>
:root{{--ink:#23253B;--midnight:#151C39;--paper:#FAF6ED;--sindoor:#C93B2E;
--haldi:#E4B04A;--haldi-soft:#F6E7C6;--muted:#6B6D82;--line:#E7E0D2;
--display:'Bricolage Grotesque',sans-serif;
--body:-apple-system,'Segoe UI',Roboto,sans-serif}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:var(--body);background:var(--paper);color:var(--ink);line-height:1.6;font-size:15.5px}}
.pg{{max-width:640px;margin:0 auto;padding:40px 22px;border-bottom:1.5px dashed var(--line)}}
.plabel{{font-family:var(--display);font-weight:700;font-size:11px;letter-spacing:.16em;
text-transform:uppercase;color:var(--sindoor);margin-bottom:10px}}
h1,h2{{font-family:var(--display);line-height:1.15}}
h2{{font-size:24px;font-weight:800;margin-bottom:14px}}
.soft{{color:var(--muted);font-size:13.5px;margin-top:14px}}
/* cover */
.cover{{background:radial-gradient(900px 500px at 50% -10%,#1D2547,var(--midnight));
color:#F3EFE4;text-align:center;border:none}}
.cover .brand{{font-family:var(--display);font-weight:800;color:var(--haldi);
letter-spacing:.06em;font-size:14px;margin-bottom:26px}}
.cover h1{{font-size:30px;font-weight:800;color:#fff}}
.cover .bd{{color:#A9ABC0;font-size:13.5px;margin:8px 0 24px}}
.kchart{{max-width:320px;margin:0 auto}}
.cover .method{{font-size:11.5px;color:#8F92AB;margin-top:20px}}
/* snapshot */
.facts{{background:#fff;border:1.5px solid var(--line);border-radius:14px;padding:6px 18px}}
.facts .row{{display:flex;justify-content:space-between;gap:14px;padding:11px 0;
border-bottom:1px dashed var(--line);font-size:14.5px}}
.facts .row:last-child{{border:none}}
.facts .k{{color:var(--muted)}}.facts .v{{font-weight:700;text-align:right}}
/* timeline + windows */
.tl{{background:var(--midnight);border-radius:14px;padding:18px 14px 12px;margin:18px 0}}
.tltrack{{position:relative;height:40px;background:#1D2547;border-radius:8px;overflow:hidden}}
.tlw{{position:absolute;top:0;bottom:0;opacity:.9}}
.tlyrs{{display:flex;justify-content:space-between;color:#7C7F99;font-size:10.5px;margin-top:7px}}
.wcard{{background:#fff;border:1.5px solid var(--line);border-left:6px solid;
border-radius:14px;padding:18px;margin-bottom:14px}}
.wtop{{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}}
.wnum{{font-family:var(--display);font-weight:700;font-size:12px;letter-spacing:.1em;
text-transform:uppercase;color:var(--muted)}}
.wgrade{{color:#fff;font-family:var(--display);font-weight:800;font-size:11px;
letter-spacing:.08em;border-radius:20px;padding:4px 12px}}
.wdates{{font-family:var(--display);font-weight:800;font-size:22px}}
.core{{font-size:13px;color:var(--muted);margin-top:2px}}
.peak{{font-size:13.5px;color:#2E7D53;font-weight:600;margin-top:6px}}
.wdasha{{font-size:12.5px;color:var(--muted);margin-top:6px}}
.wwhy{{margin:10px 0 0 18px;font-size:13.5px}}.wwhy li{{margin-bottom:4px}}
/* manglik */
.mgcard{{background:var(--haldi-soft);border-radius:14px;padding:20px}}
.mgcard b.h{{font-family:var(--display);font-size:17px;display:block;margin-bottom:8px}}
/* quiet + actions */
.quiet,.act{{background:#fff;border:1.5px solid var(--line);border-radius:12px;
padding:14px 16px;margin-bottom:10px;font-size:14.5px}}
.quiet b,.act b{{font-family:var(--display)}}
/* summary */
.sumcard{{background:var(--midnight);color:#F3EFE4;border-radius:16px;padding:24px;text-align:center}}
.sumcard .nm{{font-family:var(--display);font-weight:800;font-size:20px;color:#fff}}
.sline{{margin-top:10px;font-size:15px}}
.sumcard .sline b{{color:var(--haldi)}}
.upsell{{background:#fff;border:2px solid var(--haldi);border-radius:14px;
padding:16px;margin-top:16px;font-size:14px}}
.btnrow{{display:flex;gap:10px;margin-top:20px}}
.btn{{flex:1;font-family:var(--display);font-weight:800;font-size:14px;text-align:center;
padding:13px;border-radius:11px;border:0;cursor:pointer;text-decoration:none}}
.btn.p{{background:var(--sindoor);color:#fff}}.btn.s{{background:#fff;border:1.5px solid var(--line);color:var(--ink)}}
footer{{text-align:center;font-size:11.5px;color:var(--muted);padding:26px 20px 44px;max-width:640px;margin:0 auto}}
@media print{{.btnrow{{display:none}}.pg{{border:none;page-break-after:always;padding:28px 8px}}
body{{background:#fff}}.cover{{background:var(--midnight)!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}}}}
</style></head><body>

<section class="pg cover">
  <p class="brand">✦ ASTROSHASTRA</p>
  <h1>{name}</h1>
  <p class="bd">Marriage Timing Report · Generated {meta['generated']}</p>
  {north_chart_svg(p)}
  <p class="method">Swiss Ephemeris · Lahiri ayanamsa · Whole-sign houses · {system_note}</p>
</section>

<section class="pg"><p class="plabel">Page 2</p>
<h2>Aapka chart — marriage lens se</h2>
<div class="facts">
  <div class="row"><span class="k">Lagna</span><span class="v">{p['chart']['lagna']}</span></div>
  <div class="row"><span class="k">Moon · Nakshatra</span><span class="v">{p['teaser']['moon_sign']} · {p['teaser']['nakshatra']}</span></div>
  <div class="row"><span class="k">7th house</span><span class="v">{seventh_sign}</span></div>
  <div class="row"><span class="k">7th lord</span><span class="v">{sl} — {dignity_txt}</span></div>
  <div class="row"><span class="k">Marriage karaka</span><span class="v">{' + '.join(sig['karakas'])}</span></div>
  <div class="row"><span class="k">Darakaraka</span><span class="v">{sig['darakaraka']}</span></div>
  <div class="row"><span class="k">Current period</span><span class="v">{p['teaser']['current_dasha']}<br>till {p['teaser']['dasha_till']}</span></div>
</div>
<p class="soft">Yeh 6-7 factors milkar aapki marriage timing decide karte hain.
Agle page par inhi se nikale gaye aapke windows hain.</p></section>

<section class="pg"><p class="plabel">Page 3 · The Answer</p>
<h2>Aapke marriage windows</h2>
<div class="tl"><div class="tltrack">{tl_windows}</div>
<div class="tlyrs">{years_axis}</div></div>
{window_cards}</section>

<section class="pg"><p class="plabel">Page 4</p>
<h2>Yeh windows kaise nikle</h2>
<p>Har window ke card mein uske reasons diye hain — kaunsi dasha, kaunsa connection.
Broad logic: <b>marriage typically triggers jab dasha/antardasha lord aapke 7th house
ya uske lord se connect hota hai, aur Jupiter ka transit usko confirm karta hai.</b></p>
<p style="margin-top:10px">Timing windows probability bands hain, appointments nahi —
±15 minute ka birth time difference bhi boundaries ko months tak shift kar sakta hai.
Isliye hum honest ranges dete hain, fake precision nahi.</p></section>

<section class="pg"><p class="plabel">Page 5</p>
<h2>Manglik check</h2>
<div class="mgcard"><b class="h">{mg_head}</b><p>{mg_body}</p></div>
<p class="soft">Technical: Mars from lagna — {'manglik houses mein' if mg['from_lagna'] else 'clear'};
from Moon — {'manglik houses mein' if mg['from_moon'] else 'clear'}.</p></section>

{weak_html}

<section class="pg"><p class="plabel">Page 7</p>
<h2>Partner indications</h2>
{partner_html}</section>

<section class="pg"><p class="plabel">Page 8</p>
<h2>Ab karna kya hai</h2>
{actions}
<p class="soft">Kundli timing batati hai; effort aur choice aapke haath mein hai.
Strong window mein bhi rishtey dhoondhne padte hain — bas conversion rate better hota hai.</p></section>

<section class="pg"><p class="plabel">Page 9 · Summary</p>
<div class="sumcard">
  <p class="nm">{name}</p>
  {summary}
  <p class="sline"><b>Manglik:</b> {mg_short}</p>
  <p class="sline"><b>Partner direction:</b> {sig['darakaraka']}-type — see page 7</p>
</div>
{rectify_hook}
<div class="upsell"><b>Ek aur sawaal, usi chart se: career kab lift hoga?</b>
<p>Career Timing Report — same precision, ₹299 for report holders. WhatsApp par 'CAREER' likhiye.</p></div>
<div class="btnrow">
  <button class="btn p" onclick="window.print()">Download PDF</button>
  <a class="btn s" href="https://wa.me/91XXXXXXXXXX?text=Hi">WhatsApp Support</a>
</div></section>

<footer>Windows are probability estimates from classical dasha–transit principles,
not guarantees. 100% refund within 7 days, no questions asked.<br>
AstroShastra · Computational Vedic Astrology</footer>
</body></html>"""
