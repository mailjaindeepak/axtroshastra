"""
Axtroshastra report renderer — 9-page mobile-first report from engine JSON.
Deterministic templates only; every fact comes from the payload.
LLM narrative layer can later replace individual section texts via the same slots.
"""
import json
import math
from datetime import datetime, timedelta
from html import escape
import report_addons  # escape user-supplied fields (name/place) before HTML interpolation
from narrative import narr   # LLM prose slot (returns None -> use the bank text below)

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
<style>.sn{{font:600 13px sans-serif;fill:#A8977F;text-anchor:middle}}
.pl{{font:800 15px sans-serif;fill:#F3EFE4;text-anchor:middle}}</style>
{''.join(cells)}</svg>"""


_BLUEPRINT_WHEEL_ORDER = ["career", "money", "marriage", "children", "home",
                          "foreign", "health", "growth", "family", "timing"]
_BLUEPRINT_WHEEL_LABEL = {"career": "Career", "money": "Money", "marriage": "Marriage",
                           "children": "Children", "home": "Home", "foreign": "Foreign",
                           "health": "Health", "growth": "Growth", "family": "Family",
                           "timing": "Now"}
_BLUEPRINT_WHEEL_COLOR = {"thriving": "#3E7D5A", "building": "#B9862E", "watch": "#B4572B"}


def blueprint_wheel_svg(wheel: dict, name: str, dasha_label: str) -> str:
    """Radial 'Life Wheel' for the Life Blueprint report — one point per area,
    placed around a circle and colored by its thriving/building/watch tag
    (already computed in `wheel`; no new astrology here)."""
    cx, cy, r, lr = 160, 160, 92, 122
    n = len(_BLUEPRINT_WHEEL_ORDER)
    spokes, dots, labels = [], [], []
    for i, area in enumerate(_BLUEPRINT_WHEEL_ORDER):
        ang = -math.pi / 2 + i * (2 * math.pi / n)
        col = _BLUEPRINT_WHEEL_COLOR.get(wheel.get(area, "building"), _BLUEPRINT_WHEEL_COLOR["building"])
        x, y = cx + r * math.cos(ang), cy + r * math.sin(ang)
        lx, ly = cx + lr * math.cos(ang), cy + lr * math.sin(ang)
        spokes.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{col}" stroke-width="1.3" opacity=".5"/>')
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.5" fill="{col}"/>')
        anchor = "middle"
        if lx < cx - 8: anchor = "end"
        elif lx > cx + 8: anchor = "start"
        labels.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" dominant-baseline="middle" class="wl" fill="{col}">{_BLUEPRINT_WHEEL_LABEL[area]}</text>')
    return f"""<svg viewBox="0 0 320 320" class="wheelchart" role="img" aria-label="Your Life Wheel">
<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#E9E1D0" stroke-width="1.4"/>
<circle cx="{cx}" cy="{cy}" r="{r*0.64:.0f}" fill="none" stroke="#E9E1D0" stroke-width="1"/>
{''.join(spokes)}
{''.join(dots)}
<circle cx="{cx}" cy="{cy}" r="44" fill="#FAF5ED" stroke="#B9862E" stroke-width="1.4"/>
<text x="{cx}" y="{cy-5}" text-anchor="middle" class="wn">{name}</text>
<text x="{cx}" y="{cy+12}" text-anchor="middle" class="wd">{dasha_label}</text>
<style>.wl{{font:700 11px sans-serif}}.wn{{font:700 14px 'Fraunces',Georgia,serif;fill:#2A2338}}.wd{{font:600 9.5px sans-serif;fill:#8A8199}}</style>
{''.join(labels)}
</svg>"""


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


# ---------------------------------------------------------------- vidyarthi (/padhai) unified report helpers
GRADE_FILL = {"Strong": "linear-gradient(90deg,#2E7D53,#3fae7a)",
              "Moderate": "linear-gradient(90deg,#E4B04A,#C9922E)",
              "Building": "linear-gradient(90deg,#8F92AB,#6b6f80)"}
CAREER_BAR_COLORS = ["linear-gradient(90deg,#E4B04A,#C9922E)",
                     "linear-gradient(90deg,#2E7D53,#1F5E3D)",
                     "linear-gradient(90deg,#6C5CE7,#4C3FC4)"]


def _nearterm(p):
    """The smallest horizon (2/5/10y) that contains the soonest window, so the
    near-term outlook shows the shortest truthful timeline instead of a full
    decade by default."""
    windows = p["windows"]
    if not windows:
        return None
    today = datetime.strptime(p["meta"]["generated"], "%Y-%m-%d")
    soonest = min(windows, key=lambda w: w["start"])
    start = datetime.strptime(soonest["start"], "%Y-%m")
    full_horizon = p["teaser"]["horizon"][1] - p["teaser"]["horizon"][0]
    horizon_years = next((h for h in (2, 5, 10) if start <= today + timedelta(days=int(h * 365.25))),
                         full_horizon)
    return {"window": soonest, "horizon_years": horizon_years, "today": today}


def _nearterm_html(p):
    nt = _nearterm(p)
    if not nt:
        return ""
    w, hz, today = nt["window"], nt["horizon_years"], nt["today"]
    w_start = datetime.strptime(w["start"], "%Y-%m")
    w_end = datetime.strptime(w["end"], "%Y-%m")
    total_days = hz * 365.25
    left_pct = max(0.0, min(100.0, (w_start - today).days / total_days * 100))
    end_off_days = min(total_days, (w_end - today).days)
    width_pct = max(6.0, min(100 - left_pct, (end_off_days - max(0, (w_start - today).days)) / total_days * 100))
    is_active = w["start"] <= today.strftime("%Y-%m") <= w["end"]
    label = f"{w['grade']} window — right now" if is_active else f"{w['grade']} window ahead"
    fill = GRADE_FILL.get(w["grade"], GRADE_FILL["Building"])

    peak_html = ""
    if w.get("peak_months"):
        try:
            p_start = datetime.strptime(w["peak_months"][0], "%b %Y")
            p_end = datetime.strptime(w["peak_months"][-1], "%b %Y")
            p_left = max(0.0, min(100.0, (p_start - today).days / total_days * 100))
            p_width = max(4.0, min(100 - p_left, (p_end - p_start).days / total_days * 100 + 4))
            peak_html = f"<div class='peak' style='left:{p_left:.1f}%;width:{p_width:.1f}%'></div>"
        except ValueError:
            pass

    labels = [(today + timedelta(days=int(total_days * i / 4))).strftime("%b %Y") for i in range(5)]
    yrs_html = "".join(f"<span>{l}</span>" for l in labels)

    peak_note = (f" Dashed outline marks your <b>peak stretch — {', '.join(w['peak_months'])}</b>."
                if w.get("peak_months") else "")
    beyond_note = (f" This {w['grade']} window actually runs through {w_end.strftime('%b %Y')}; we're only "
                  f"showing you the next {hz} year{'s' if hz != 1 else ''} so the headline stays easy to act on."
                  if (w_end - today).days > total_days else "")
    expand_note = (" If nothing had shown up in this window, we'd have automatically expanded to a 5-year, "
                  "then 10-year view — you're seeing the shortest horizon that actually applies to you."
                  if hz <= 5 else "")

    return f"""<h2>Your near-term outlook</h2>
<p class="lead">We check the next 1–2 years first — not a decade of dates you don't need yet.</p>
<div class="near">
<div class="track"><div class="fill" style="left:{left_pct:.1f}%;width:{width_pct:.1f}%;background:{fill}">{label}</div>{peak_html}</div>
<div class="yrs">{yrs_html}</div>
<p class="note">{peak_note}{beyond_note}{expand_note}</p>
</div>"""


def _nowcard_html(p):
    today_ym = p["meta"]["generated"][:7]
    active = next((w for w in p["windows"] if w["start"] <= today_ym <= w["end"]), None)
    verdict = (f"✅ You're already inside a {active['grade']} window" if active
              else "🌱 Between windows right now — a good stretch to prepare.")
    translation = ("you're in a productive stretch — this dasha combination is actively supporting your goals."
                  if active else
                  "this is a \"put in the reps\" phase. It can feel slow, but effort you invest now is the "
                  "kind that lasts — you're building the base your next breakthrough stands on.")
    return f"""<div class="nowcard">
<p class="k">📍 Where you are right now</p>
<p class="big">{p['teaser']['current_dasha']} · until {p['teaser']['dasha_till']}</p>
<p>Translation: {translation}</p>
<span class="verdict">{verdict}</span></div>"""


def _split_html(five_factors):
    strong = [f for f in five_factors if f["status"] == "strong"]
    watch = [f for f in five_factors if f["status"] == "watch"]
    strong_li = "".join(f"<li>{f['emoji']} {escape(f['label'])}</li>" for f in strong) or "<li>None right now</li>"
    watch_li = "".join(f"<li>{f['emoji']} {escape(f['label'])}</li>" for f in watch) or "<li>None right now</li>"
    return f"""<h2>What's working / what needs attention</h2>
<p class="lead">Five things that decide whether effort actually pays off. Here's where your chart already helps you, and where it doesn't.</p>
<div class="split">
<div class="splitcol good"><p class="st">✅ Naturally strong ({len(strong)} of 5)</p><ul>{strong_li}</ul></div>
<div class="splitcol watch"><p class="st">⚠️ Needs attention ({len(watch)} of 5)</p><ul>{watch_li}</ul></div>
</div>"""


def _qa_html(p, ex, w1):
    today_ym = p["meta"]["generated"][:7]
    active_now = w1 and w1["start"] <= today_ym <= w1["end"]
    dir_text = ex.get("career_direction", "")
    if w1:
        q3 = (f"You're already in it — strongest right now through "
              f"{datetime.strptime(w1['end'], '%Y-%m').strftime('%b %Y')}. That's when doors open most easily, "
              f"so line up applications and exams for this stretch." if active_now else
              f"Your nearest window opens {datetime.strptime(w1['start'], '%Y-%m').strftime('%b %Y')} — "
              f"that's when to line up applications and exams.")
    else:
        q3 = "No standout window in this horizon yet — steady effort still compounds either way."
    track_line = " You're inside a Strong window right now." if active_now else ""
    return f"""<h2>Your 3 biggest questions, answered</h2>
<p class="lead">The stuff actually running through your head — straight answers first.</p>
<div class="qa">
<div class="item"><p class="q"><span class="em">🧭</span> Am I even on the right track?</p>
<p class="a">Yes — {dir_text}.{track_line} The direction isn't your problem; consistency is.</p></div>
<div class="item"><p class="q"><span class="em">🎯</span> What should I actually focus on?</p>
<p class="a">One fixed daily study routine, and protecting your calm before exams. Those two habits move your results more than anything else in your chart.</p></div>
<div class="item"><p class="q"><span class="em">⏳</span> When will the effort pay off?</p>
<p class="a">{q3}</p></div>
</div>"""


def _career_html(candidates):
    if not candidates:
        return ""
    rows = ""
    for i, c in enumerate(candidates):
        a = c["archetype"]
        rows += (f"""<div class="careerrow"><span class="cr-label">{a['emoji']} {escape(a['name'])}</span>
<div class="cr-track"><div class="cr-fill" style="width:{c['score']}%;background:{CAREER_BAR_COLORS[i % 3]}">"""
                f"""<span>{c['score']}%</span></div></div></div>
<p class="career-desc">{escape(a['tagline'])} — {a['body']}</p>""")
    plural = "are your strongest" if len(candidates) > 1 else "is your strongest"
    return f"""<h2>Your career type {candidates[0]['archetype']['emoji']}</h2>
<p class="lead">Every chart leans toward more than one direction. Here {plural}, ranked.</p>
<div class="careerbar-wrap">{rows}</div>"""


FACTOR_PLAIN = {"strong": "This one's already working in your favour",
                "watch": "This one takes deliberate effort"}


def _factor_cards_html(five_factors):
    out = ""
    for f in five_factors:
        cls = f["status"]
        status_label = "Naturally strong" if cls == "strong" else "Needs attention"
        color = "var(--green)" if cls == "strong" else "var(--rose)"
        dropdown = (f"<details><summary>What can I do about this?</summary><p>{f['advice']}</p></details>"
                   if f["status"] == "watch" and f.get("advice") else "")
        out += f"""<div class="factor">
<div class="ftop"><span class="fname">{f['emoji']} {escape(f['label'])}</span><span class="fstatus {cls}">{status_label}</span></div>
<div class="meter"><div style="width:{f['score']}%;background:{color}"></div></div>
<p class="fplain {cls}">{FACTOR_PLAIN[cls]} — {f['score']}%</p>
<p class="fexpl">{f['explanation']}.</p>
{dropdown}</div>"""
    return out


def _do_next_html(ex, w1):
    factors = ex.get("five_factors", [])
    weakest = min(factors, key=lambda f: f["score"]) if factors else None
    step1 = (weakest["advice"] if weakest and weakest.get("advice")
            else (f"Keep reinforcing {weakest['label']} — it's already one of your steadier areas."
                  if weakest else "Keep your current habits consistent."))
    if w1:
        peak = f", especially {', '.join(w1['peak_months'])}" if w1.get("peak_months") else ""
        step3 = (f"Line up applications, exams, or course starts around your nearest window "
                f"({datetime.strptime(w1['start'], '%Y-%m').strftime('%b %Y')}{peak}).")
    else:
        step3 = "Keep preparing — no standout window in this horizon yet, so steady effort compounds."
    return f"""<h2>Do this next</h2>
<div class="actionbox"><p class="ak">Your 3-step plan</p><ol>
<li><b>This month:</b> {step1}</li>
<li><b>Before your next exam:</b> protect sleep in the final week more than last-minute revision.</li>
<li><b>Timing:</b> {step3}</li>
</ol></div>"""


def _holdback_html(p):
    gaps = _weak_periods(p)
    if not gaps:
        return ("""<div class="hold">✅ <b>No major quiet stretches in your horizon</b> — your windows are """
                """close enough together that there's rarely a long "just wait" period ahead.</div>""")
    s, e = gaps[0]
    return (f"""<div class="hold">⏸️ <b>Not every month is a "push" month.</b> Your next quiet stretch — """
           f"""where consolidating beats forcing new starts — runs roughly <b>{s} – {e}</b>. Effort there """
           f"""is better spent on skills than outcomes.</div>""")


def _tagpicker_html(candidates):
    rows = ""
    for i, c in enumerate(candidates):
        a = c["archetype"]
        name = f"{a['emoji']} {escape(a['name'])}"
        checked = " checked" if i == 0 else ""
        rows += f"""<div class="tp-row" data-name="{name}" data-pct="{c['score']}">
<label class="tp-check"><input type="checkbox"{checked} onchange="axCheckboxChanged(this)"> {name}</label>
<button type="button" class="tp-pct" onclick="axTogglePctBtn(this)">{c['score']}%</button>
</div>"""
    return rows


AX_PRE = r"""<script>
(function(){
  try{
    var l = localStorage.getItem('axlang') || 'en';
    if(l === 'en') document.documentElement.classList.add('ax-pre');
  }catch(e){}
  setTimeout(function(){ document.documentElement.classList.remove('ax-pre'); }, 1500);
})();
</script>
<style>html.ax-pre body{visibility:hidden}@media print{#axlang{display:none!important}#ax-pdf{display:none!important}.cover{break-after:page;break-inside:avoid}h2,h1,.plabel{break-after:avoid}body{background:#fff}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}.ax-wm{display:flex!important}.ax-share{display:none!important}}.ax-wm{display:none;position:fixed;inset:0;z-index:9998;pointer-events:none;flex-direction:column;align-items:center;justify-content:center;transform:rotate(-28deg);opacity:.08;color:#151C39;font-family:Georgia,serif}.ax-wm b{font-size:66px;letter-spacing:.12em;line-height:1}.ax-wm span{font-size:18px;letter-spacing:.35em;margin-top:6px}.ax-share{display:inline-block;background:#25D366;color:#fff;border:0;border-radius:10px;padding:12px 18px;font:600 15px/1 sans-serif;cursor:pointer;text-decoration:none}.ax-disc{max-width:640px;margin:28px auto 8px;padding:14px 16px;border:1px solid #E7E0D2;border-radius:10px;background:#fbf7ef;font-size:12.5px;line-height:1.5;color:#6b6f80}.ax-endcard{max-width:640px;margin:12px auto 28px;text-align:center;padding:18px;border-top:2px solid #E4B04A}.ax-endcard b{font-size:18px;color:#151C39}.ax-endcard a{color:#C93B2E;text-decoration:none;font-weight:600}.ans{max-width:640px;margin:8px auto 4px;padding:20px 22px;border:1px solid #E4B04A;border-radius:14px;background:#FFF9EC}.ans .plabel{color:#B8860B;margin:0 0 2px}.ans h2{margin:.15em 0 .55em}.ans-win{font-size:17px;margin:.3em 0}.ans-win .g{color:#2E7D53;font-weight:700}.ans-win2{color:#4a4d5e;margin:.15em 0}.ans-mg{margin:.55em 0 .2em;font-weight:600}.ans-note{font-size:12.5px;color:#6b6f80;margin-top:.6em;line-height:1.5}.facts .why{font-size:12px;color:#8a7a5c;margin:3px 0 11px;line-height:1.45}</style>"""


REPORT_I18N = r"""<script>
(function(){
  var FRAG = [
    ["Aapka jawab — ek nazar mein","Your answer — at a glance"],
    ["Shaadi kab hogi? — seedha jawab","When will you get married? — the direct answer"],
    ["Sabse strong window:","Strongest window:"],
    ["Uske baad:","After that:"],
    ["Manglik: Nahi — is taraf koi rukaawat nahi.","Manglik: No — no obstacle on this front."],
    ["Manglik: technically haan, par cancel ho gaya — practically Nahi.","Manglik: technically yes, but cancelled — practically No."],
    ["Manglik: Haan — page 5 par detail aur cancellation check dekhiye.","Manglik: Yes — see the detail and cancellation check on page 5."],
    ["Yeh jawab aapke poore chart se nikla hai. Neeche har window ki wajah, aapka Navamsa, aur beete periods — taaki aap khud milaa sakein.","This answer comes from your full chart. Below: the reason for each window, your Navamsa, and past periods — so you can check it yourself."],
    ["Aapki personality aur poore chart ka base — har bhaav isi se gina jaata hai.","The base of your personality and whole chart — every house is counted from here."],
    ["Aapka mann aur emotional nature. Aapki dasha timeline isi Moon-nakshatra se chalti hai — yahi timing ka engine hai.","Your mind and emotional nature. Your dasha timeline runs from this Moon-nakshatra — this is the engine of timing."],
    ["Shaadi, partner aur commitment ka ghar — marriage ka main area.","The house of marriage, partner and commitment — the main area for marriage."],
    ["Shaadi ka main switch. Iski dignity (upar) timing ki quality batati hai — strong matlab saaf timing, tender matlab zyada soch-samajh.","The main switch for marriage. Its dignity (above) shows the quality of the timing — strong means clear timing, tender means more thought is needed."],
    ["Rishton ka natural indicator (Venus/Jupiter) — yeh shaadi ka promise dikhata hai.","The natural indicator of relationships (Venus/Jupiter) — it shows the marriage promise."],
    ["Jaimini system ka spouse-significator — partner ki ek jhalak.","The spouse-significator in the Jaimini system — a glimpse of the partner."],
    ["Abhi kaunsi dasha chal rahi hai. Windows isi timeline par bante hain — isliye yeh sabse relevant.","Which dasha is running now. The windows form on this timeline — which is why this is the most relevant."],
    ["Yeh report classical Vedic Jyotish (dasha-transit) principles par computed hai — guidance ke liye, guarantee nahi. Timing windows probability hain, fixed dates nahi. Yeh legal, medical ya financial advice nahi hai. Apne life decisions aap apni samajh se lijiye; Axtroshastra kisi outcome ki zimmedari nahi leta.","This report is computed from classical Vedic Jyotish (dasha-transit) principles — for guidance, not a guarantee. Timing windows are probabilities, not fixed dates. This is not legal, medical or financial advice. Make your own life decisions using your own judgement; Axtroshastra takes no responsibility for any outcome."],
    ["Yeh report Axtroshastra ne banayi — apna report paayein:","Made with Axtroshastra — get your own report at:"],
    ["self-respecting, strong-willed partner — individuality rishtey mein central; ek dusre ke ego ko space dena seekhna faydemand","self-respecting, strong-willed partner — individuality is central to the relationship; learning to give each other's ego space pays off"],
    ["emotionally attuned, caring partner — ghar-parivar ka warmth bond ka kendra; mood-tuning dono ki saanjhi zimmedari","emotionally attuned, caring partner — the warmth of home and family is the heart of the bond; mood-tuning is a shared responsibility"],
    ["energetic, passionate bond — kabhi tez-mizaji bhi (Manglik check upar dekhiye); jhagdon ko jaldi suljhana rishtey ko majboot karta hai","energetic, passionate bond — sometimes hot-tempered too (see the Manglik check above); resolving quarrels quickly makes the relationship stronger"],
    ["youthful, communicative partner — baat-cheet aapka asli gum hai; aksar partner young-natured ya age-gap kam","youthful, communicative partner — conversation is your real glue; often the partner is young-natured or the age gap is small"],
    ["wise, principled, often traditional-values partner — 7th house mein Guru ko classical texts shubh maante hain; family-approved yog","wise, principled, often traditional-values partner — classical texts consider Jupiter in the 7th house auspicious; a family-approved match"],
    ["affectionate, harmony-loving partner — romance aur comfort sahaj; marriage karaka apni hi jagah, isliye achha placement","affectionate, harmony-loving partner — romance and comfort come naturally; the marriage karaka is in its own place, so a good placement"],
    ["mature, committed, possibly older ya seriously-minded partner — bond dheere banta hai par tikau; shuruaati sabr baad mein rang laata hai","mature, committed, possibly older or seriously-minded partner — the bond builds slowly but lasts; early patience pays off later"],
    ["unconventional attraction — partner alag background/community/desh se ho sakta hai; shuruaat sudden ya intense","unconventional attraction — the partner may come from a different background/community/country; the start can be sudden or intense"],
    ["gehra par thoda detached bond — partner spiritually-inclined ho sakta hai; over-analysis se bachna, dil se judna","a deep but slightly detached bond — the partner may be spiritually-inclined; avoid over-analysis, connect from the heart"],
    ["Is chart mein koi graha vargottama nahi — normal hai, zyaadatar charts mein 0–2 hote hain.","No planet is vargottama in this chart — that's normal; most charts have only 0–2."],
    ["aapka 7th lord","your 7th lord"],
    ["vargottama hai (D1 aur D9 mein ek hi rashi) — marriage promise strong","is vargottama (same sign in D1 and D9) — a strong marriage promise"],
    ["vargottama hai — sneh aur nibhaav ki strength","is vargottama — strength of affection and commitment"],
    ["debilitated hai — timing par thoda extra dhyaan","is debilitated — a little extra care on timing"],
    ["D9 mein debilitated hai — expression mein narmi ki zaroorat","is debilitated in D9 — expression needs some gentleness"],
    ["(upar windows dekhiye).","(see the windows above)."],
    ["Navamsa thoda tender hai — iska matlab shaadi nahi hoti aisa nahi, balki partner-choice aur timing mein soch-samajh zyada zaroori hai. Yeh warning nahi, awareness hai.","The Navamsa is a bit tender — this doesn't mean marriage won't happen; rather, partner-choice and timing need more thought. This is not a warning, it's awareness."],
    ["Navamsa marriage promise ko steadily support karta hai — koi badi rukaawat nahi, D1 windows hi driver hain.","The Navamsa steadily supports the marriage promise — no major obstacle; the D1 windows are the driver."],
    ["D9 mein koi strong plus ya minus signal nahi — neutral promise, timing D1 se aati hai.","No strong plus or minus signal in D9 — a neutral promise; the timing comes from D1."],
    ["Aapka chart — marriage lens se","Your chart — through a marriage lens"],
    ["Yeh 6-7 factors milkar aapki marriage timing decide karte hain. Agle page par inhi se nikale gaye aapke windows hain.","These 6–7 factors together decide your marriage timing. The next page has your windows, derived from them."],
    ["Yeh 6–7 factors milkar aapki marriage timing decide karte hain. Agle page par inhi se nikale gaye aapke windows hain.","These 6–7 factors together decide your marriage timing. The next page has your windows, derived from them."],
    ["timing par extra dhyaan","pay extra attention to timing"],
    ["apne hi sign mein — strong placement","in its own sign — strong placement"],
    ["theek-thaak","steady"],
    ["Aapka poora chart — verify kijiye","Your full chart — verify it"],
    ["Hum kuch chhupate nahi. Neeche aapke saare 9 grahon ki exact position hai — koi bhi astrologer ise apni panchang se milaa sakta hai. Yahi hamari transparency hai.","We hide nothing. Below are the exact positions of all 9 of your planets — any astrologer can check them against their panchang. That is our transparency."],
    ["Bhaav (house) lagna se gina gaya hai","Houses are counted from the lagna"],
    ["Yeh windows kaise nikle","How these windows were derived"],
    ["Har window ke card mein uske reasons diye hain — kaunsi dasha, kaunsa connection. Broad logic:","Each window's card gives its reasons — which dasha, which connection. Broad logic:"],
    ["marriage typically triggers jab dasha/antardasha lord aapke 7th house ya uske lord se connect hota hai, aur Jupiter ka transit usko confirm karta hai.","marriage typically triggers when the dasha/antardasha lord connects to your 7th house or its lord, and Jupiter's transit confirms it."],
    ["Timing windows probability bands hain, appointments nahi — ±15 minute ka birth time difference bhi boundaries ko months tak shift kar sakta hai. Isliye hum honest ranges dete hain, fake precision nahi.","Timing windows are probability bands, not appointments — even a ±15-minute birth-time difference can shift the boundaries by months. So we give honest ranges, not fake precision."],
    ["Aapke top window ka scorecard","Your top window's scorecard"],
    ["Yeh window","This window"],
    ["ko humne","was scored"],
    ["diye, isliye grade","points, hence grade"],
    ["Har point ke peeche ek classical rule hai","Behind each point is a classical rule"],
    ["neeche exact","the exact breakdown below,"],
    ["mila.","points."],
    ["Koi astrologer chaahe toh in rules ko apne haath se verify kar sakta hai — kyunki yeh judgement nahi, calculation hai.","Any astrologer can verify these rules by hand — because this is not judgement, it is calculation."],
    ["Aap manglik nahi hain","You are not manglik"],
    ["Aap manglik hain","You are manglik"],
    ["Mars aapke chart mein manglik houses","Mars is not in the manglik houses"],
    ["mein nahi hai — lagna se bhi, Moon se bhi.","in your chart — from the lagna, and from the Moon too."],
    ["Rishtey ki baat-cheet mein yeh sawaal aaye toh confidently 'nahi' kah sakte hain.","If this comes up in match discussions, you can confidently say 'no'."],
    ["Rishtey ki baat-cheet mein yeh sawaal aaye toh confidently","If this comes up in match discussions, you can confidently"],
    ["'nahi' kah sakte hain.","say 'no'."],
    ["kah sakte hain.","say so."],
    ["shaadi ka asli sheesha","the true mirror of marriage"],
    ["batata hai; Navamsa","tells; Navamsa"],
    ["nibhega — isiliye classical Jyotish mein shaadi ke liye","will last — which is why, in classical Jyotish, for marriage"],
    ["sabse zaroori divisional chart hai. Aapka","is the most important divisional chart. Your"],
    ["houses ke andar","within the houses"],
    ["Vargottama aur","Vargottama and"],
    ["mein ek hi rashi — extra","in the same sign — an extra"],
    ["Navamsa marriage promise ko strongly support karta hai — yog pakka hai, sirf timing ki baat hai","The Navamsa strongly supports the marriage promise — the promise is solid, it is only a matter of timing"],
    ["(upar windows","(windows above"],
    ["D9 mein 7th lord","In D9, the 7th lord"],
    ["apni acchi dignity mein hai","is in good dignity"],
    ["D9 mein strong hai","is strong in D9"],
    ["mein strong hai","is strong in"],
    ["promise ki baat hai, timing ki nahi — timing upar ke windows batate hain.","this speaks to the promise, not the timing — the windows above give the timing."],
    ["Dono milkar poori tasveer dete hain.","Together they give the full picture."],
    ["Quiet periods — aur unka matlab","Quiet periods — and what they mean"],
    ["Jitna important yeh jaanna hai ki kab yog strong hai, utna hi yeh ki kab नहीं hai.","It is as important to know when the chance is strong as when it is not."],
    ["Jitna important yeh jaanna hai ki kab yog strong hai, utna hi yeh ki kab","It is as important to know when the chance is strong as when it is not"],
    ["In periods mein rishtey aa sakte hain, par convert hone ka pattern weak rehta hai:","In these periods matches may come, but the pattern of converting stays weak:"],
    ["In periods mein rishtey aa sakte hain, par convert hone ka pattern weak rehta","In these periods matches may come, but the pattern of converting stays weak"],
    ["Agar pichhle saalon mein baat banti-banti reh gayi ho — chart mein aksar uski wajah dikh jaati hai. Yeh aapki kami nahi thi; timing thi.","If matches kept almost-happening in past years — the chart often shows why. This was not your shortcoming; it was timing."],
    ["Pichhle saal","Past years"],
    ["Ab tak kya hua — aur kyun","What has happened so far — and why"],
    ["Aapke pichhle periods ka chart-analysis. Agar rishtey aaye par bane nahi, ya bilkul shaant raha — yahan uski wajah","A chart-analysis of your past periods. If matches came but did not work out, or it stayed completely quiet — here is why"],
    ["Yeh section isliye hai taaki aap dekh","This section is here so that you can see"],
    ["timing ek pattern hai, aapki kami nahi. Jo beet gaya usmein bhi chart ka logic tha.","timing is a pattern, not your shortcoming. Even what has passed had the chart's logic in it."],
    ["Saal-dar-saal","Year by year"],
    ["saal — ek nazar mein","years — at a glance"],
    ["Agle ","The next "],
    ["Jupiter ka transit is saal supportive houses mein hai — conversations ko aage badhaane ka saath milega.","Jupiter's transit this year is in supportive houses — it will help move conversations forward."],
    ["Jupiter ka transit is saal neutral zone mein hai — effort par zyada, luck par kam depend kijiye.","Jupiter's transit this year is in a neutral zone — rely more on effort, less on luck."],
    ["Yeh page save kar lijiye — har saal ke shuru mein dobara padhne layak hai.","Save this page — it is worth re-reading at the start of each year."],
    ["Yeh indications hain, portrait nahi — chart directions batata hai, details zindagi bharti hai.","These are indications, not a portrait — the chart gives directions, life fills in the details."],
    ["house khaali hai","house is empty"],
    ["koi graha 7th mein nahi. Yeh normal aur aksar shubh maana jaata hai: partner ka pattern 7th ke","no planet sits in the 7th. This is normal and often considered auspicious: the partner pattern is read from the 7th's"],
    ["koi graha ismein nahi. Yeh normal aur aksar shubh maana jaata hai","no planet sits in it. This is normal and often considered auspicious"],
    ["partner ka pattern","the partner pattern"],
    ["aur karaka se padha jaata hai (upar diya hai), naa ki kisi baithe graha se.","and karaka (given above), not from any planet sitting there."],
    ["Chart ka jhukaav","The chart leans toward"],
    ["ki taraf hai — introductions aur family networks se hi strong yog banta hai.","— the strongest chance forms through introductions and family networks."],
    ["se connection hai — partner doori se, alag community se, ya unexpected background se aane ka yog hai. Surprise ke liye taiyaar rahiye.","connection — the partner may come from a distance, a different community, or an unexpected background. Be ready for a surprise."],
    ["Ab karna kya hai","What to do now"],
    ["Kundli timing batati hai; effort aur choice aapke haath mein hai. Strong window mein bhi rishtey dhoondhne padte hain — bas conversion rate better hota hai.","The chart tells you the timing; effort and choice are in your hands. Even in a strong window you still have to look for matches — the conversion rate is simply better."],
    ["Aap pyaar kaise karte hain — chart ke hisaab se","How you love — according to the chart"],
    ["combust hai, isliye expression mein hesitation aa sakti hai; feelings genuine, awaaz dheemi","is combust, so there can be hesitation in expression; the feelings are genuine, the voice soft"],
    ["Jo aapne nahi poocha, par jaanna chahenge","What you did not ask, but would want to know"],
    ["Saturn ka influence aapke","Saturn's influence is on your"],
    ["house par hai — timing mein maturity-factor hai. Matlab: shaadi thodi der se, par zyada soch-samajh ke. Late ≠ never.","house — there is a maturity-factor in the timing. Meaning: marriage a little later, but with more thought. Late ≠ never."],
    ["abhi nahi chal rahi.","is not running right now."],
    ["se. Filhaal Shani ka is angle se koi delay-pressure nahi.","onwards. For now, no delay-pressure from Saturn on this angle."],
    ["Next phase","Next phase from"],
    ["Weak periods mein","In weak periods"],
    ["Traditional support — bina dar ke","Traditional support — without fear"],
    ["ke hisaab se, weak windows mein classical","accordingly, in weak windows classical"],
    ["baar, Ravivar (Sunday) ko","times, on Ravivar (Sunday)"],
    ["ki current condition mein gemstone recommend nahi karte — mantra aur fast kaafi hain.","in its current condition — we do not recommend a gemstone; mantra and fasting are enough."],
    ["Order yaad","Remember the order"],
    ["pehla remedy hamesha action hai — strong window mein actively dhoondhna. Yeh support hai, substitute nahi.","the first remedy is always action — actively searching in a strong window. This is a support, not a substitute."],
    ["Ek aur sawaal, usi chart","One more question, from the same chart"],
    ["career kab lift hoga?","when will your career take off?"],
    ["par CAREER bhejiye","send CAREER on"],
    // ---- Manglik page (page 5) ----
    ["Manglik placement hai — par cancelled hai","There is a Manglik placement — but it is cancelled"],
    ["Manglik placement hai — calmly samjhiye","There is a Manglik placement — understand it calmly"],
    ["Mars manglik position mein hai, lekin classical cancellation rules apply hote hain:","Mars is in a manglik position, but classical cancellation rules apply:"],
    ["Tradition mein cancelled manglik ko manglik nahi mana jaata — matching mein isse issue nahi banna chahiye.","In tradition a cancelled manglik is not counted as manglik — it should not be an issue in matching."],
    ["Mars manglik houses mein hai. Yeh koi shraap nahi hai — classical texts iske liye simple remedial framing dete hain, aur manglik-manglik matching mein yeh neutral ho jaata hai. Dar ki nahi, jaankari ki baat hai.","Mars is in the manglik houses. This is no curse — classical texts give it a simple remedial framing, and in manglik-manglik matching it becomes neutral. This is a matter of information, not fear."],
    ["manglik houses mein","in the manglik houses"],
    // ---- Sade Sati (in '3 aur sach' section) ----
    ["Sade Sati check: chal rahi hai","Sade Sati check: currently running"],
    ["Iska matlab delay ka pressure, denial nahi — Shani ke period mein bani shaadiyan sabse tikau maani jaati hain. Windows upar isi ko account karke grade hue hain.","This means delay-pressure, not denial — marriages made during Saturn's period are considered the most durable. The windows above are graded taking this into account."],
    ["Sade Sati check: abhi nahi chal rahi.","Sade Sati check: not currently running."],
    ["rising (pehla charan)","rising (first phase)"],
    ["peak (dusra charan)","peak (second phase)"],
    ["setting (aakhri charan)","setting (final phase)"],
    // ---- Section titles / headlines ----
    ["Aapka pattern","Your pattern"],
    ["Aapka nakshatra:","Your nakshatra:"],
    ["Aapka Venus","Your Venus"],
    ["3 aur sach","3 more truths"],
    // ---- Venus love-style suffix (own/exalted) ----
    ["Venus apne hi sign mein strong hai; pyaar mein aapki instinct par bharosa kiya ja sakta hai.","Venus is strong in its own sign; in love, your instincts can be trusted."],
    // ---- '3 aur sach' check bodies (untranslated branches) ----
    ["Saturn ka koi direct influence aapke 7th house par nahi — classical 'late marriage' indicator aapke chart mein absent hai.","Saturn has no direct influence on your 7th house — the classical 'late marriage' indicator is absent from your chart."],
    ["Aapke chart mein 5th–7th connection hai — love-marriage ya self-driven rishtey ka yog. Arranged setup mein bhi pasand aapki hi chalegi.","Your chart has a 5th–7th connection — a leaning toward love-marriage or a self-driven relationship. Even in an arranged setup, your own preference will prevail."],
    ["Rahu/12th ka 7th se connection hai — partner doori se, alag community se, ya unexpected background se aane ka yog hai. Surprise ke liye taiyaar rahiye.","There's a Rahu/12th-to-7th connection — the partner may come from a distance, a different community, or an unexpected background. Be ready for a surprise."],
    ["Partner ka yog aapke apne circle aur community ke aas-paas ka hai — door ka yog chart mein prominent nahi.","The partner is indicated within your own circle and community — a distant match is not prominent in the chart."]
  ];
  var EXACT = {"HAAN":"YES","NAHI":"NO","नहीं":"NO","HAN":"YES","Pichhle saal":"Past years","kab":"when","aur":"and","Graha":"Planet","Bhaav":"House","hai.":"."};
  var TITLE = { en: "Marriage Timing Report | Axtroshastra" };
  function norm(s){ return s.replace(/\u00a0/g," ").replace(/ [‐‑‒–—-] /g," — ").replace(/[‐‑‒–—]/g,"—").replace(/\s+/g," "); }
  var SORTED = FRAG.map(function(p){ return [norm(p[0]), p[1]]; }).sort(function(a,b){ return b[0].length - a[0].length; });
  function walk(node, fn){
    for(var i=0;i<node.childNodes.length;i++){
      var n=node.childNodes[i];
      if(n.nodeType===3){ fn(n); }
      else if(n.nodeType===1 && n.tagName!=='SCRIPT' && n.tagName!=='STYLE' && n.id!=='axlang'){ walk(n, fn); }
    }
  }
  function translate(hi){
    var t=norm(hi), trimmed=t.trim();
    if(Object.prototype.hasOwnProperty.call(EXACT, trimmed)){ return t.replace(trimmed, EXACT[trimmed]); }
    for(var i=0;i<SORTED.length;i++){ if(t.indexOf(SORTED[i][0])>=0){ t = t.split(SORTED[i][0]).join(SORTED[i][1]); } }
    return t;
  }
  function apply(lang){
    walk(document.body, function(tn){
      if(lang!=='en'){ if(tn.__hi!=null) tn.nodeValue = tn.__hi; return; }
      if(tn.__hi==null) tn.__hi = tn.nodeValue;
      if(!tn.__hi.trim()) return;
      tn.nodeValue = translate(tn.__hi);
    });
    document.documentElement.lang = (lang==='en')?'en':'hi-IN';
    if(lang==='en' && TITLE.en){ if(!window.__titlehi) window.__titlehi=document.title; document.title=TITLE.en; }
    else if(window.__titlehi){ document.title=window.__titlehi; }
    try{ localStorage.setItem('axlang', lang); }catch(e){}
    var box=document.getElementById('axlang');
    if(box){ box.querySelector('[data-l=hi]').classList.toggle('on', lang!=='en'); box.querySelector('[data-l=en]').classList.toggle('on', lang==='en'); }
    window.__axlang=lang;
    document.documentElement.classList.remove('ax-pre');
  }
  var css=document.createElement('style');
  css.textContent='#axlang{position:fixed;top:10px;right:10px;z-index:9999;display:flex;background:rgba(21,28,57,.92);border:1px solid #E4B04A;border-radius:20px;overflow:hidden;font:600 12px/1 -apple-system,Segoe UI,sans-serif;box-shadow:0 4px 14px rgba(0,0,0,.25)}#axlang button{background:transparent;color:#C9CBDB;border:0;padding:7px 13px;cursor:pointer;letter-spacing:.02em}#axlang button.on{background:#E4B04A;color:#151C39}@media print{#axlang{display:none}}';
  document.head.appendChild(css);
  var box=document.createElement('div'); box.id='axlang';
  box.innerHTML='<button data-l="hi">Hinglish</button><button data-l="en">English</button>';
  box.addEventListener('click', function(e){ var b=e.target.closest('button'); if(b) apply(b.getAttribute('data-l')); });
  document.body.appendChild(box);
  var saved='en'; try{ saved=localStorage.getItem('axlang')||'en'; }catch(e){}
  apply(saved);
  window.axShare=function(){var url=location.href;var t=(window.__axlang==='en'?'Check out my marriage timing report from Axtroshastra':'Meri marriage timing report Axtroshastra se');if(navigator.share){navigator.share({title:'Axtroshastra',text:t,url:url}).catch(function(){});}else{window.open('https://wa.me/?text='+encodeURIComponent(t+' '+url),'_blank');}};
})();
</script>
"""


MILAN_I18N = r"""<script>
(function(){
  var FRAG = [
    // ---- static strings in render_milan ----
    ["✦ AXTROSHASTRA · KUNDLI MILAN","✦ AXTROSHASTRA · HOROSCOPE MATCHING"],
    ["Ashtakoota — aatho kootas ka breakdown","Ashtakoota — a breakdown of all eight kootas"],
    ["Dosha cancellation ke baad:","After the flaw cancellation:"],
    ["Dosha cancellation check","Flaw cancellation check"],
    ["Cancellations ke baad effective score:","Effective score after cancellations:"],
    ["Is jodi mein dosha ke standard cancellation rules apply nahi hote — dosha effective hai. Iska matlab section 'Score ka matlab' mein neeche padhiye; dar se nahi, samajh se decide kijiye.","For this couple the standard cancellation rules for the flaw do not apply — the flaw is effective. Read what this means in the 'What the score means' section below; decide not from fear but from understanding."],
    ["Is jodi ki taakat — aur dhyaan ki jagah","This couple's strengths — and where to pay attention"],
    ["Aap dono ki energy","Your combined energy"],
    ["Score kam hai — iska matlab kya hai?","The score is low — what does it mean?"],
    ["Pehli baat:","First:"],
    ["guna milan ek classical input hai, poora faisla nahi. Yeh Moon-positions ki compatibility napta hai — values, maturity aur commitment nahi, jo kisi bhi rishtey ke asli pillars hain.","guna milan is one classical input, not the whole verdict. It measures the compatibility of Moon-positions — not values, maturity and commitment, which are the real pillars of any relationship."],
    ["Dusri baat:","Second:"],
    ["upar dekhiye kaunse kootas mein kami hai. Gana ya Graha Maitri ki kami","look above to see which kootas fall short. A shortfall in Gana or Graha Maitri is"],
    ["hai — yeh communication-patterns ki baat hai jo couples seekh lete hain. Nadi/Bhakoot dosha (agar cancelled nahi) traditional weight zyada rakhta hai — wahan family-elders aur apne vivek dono se salaah kijiye.","— this is about communication-patterns that couples learn. The Nadi/Bhakoot flaw (if not cancelled) carries more traditional weight — there, seek counsel from both family-elders and your own judgement."],
    ["Teesri baat:","Third:"],
    ["lakhs of successful marriages kam score ke saath hui hain. Score ko information ki tarah use kijiye — kis cheez par kaam karna hoga yeh jaanne ke liye — verdict ki tarah nahi.","lakhs of successful marriages have happened with a low score. Use the score as information — to learn what you will need to work on — not as a verdict."],
    // ---- manglik_note (products.py) ----
    ["Dono charts mein manglik placement hai — classical rule mein manglik-manglik pairing neutral ho jaati hai. Not an obstacle.","Both charts have a manglik placement — in the classical rule a manglik-manglik pairing becomes neutral. Not an obstacle."],
    ["Ek chart mein manglik placement hai (Moon-based check). Cancellation rules aksar apply hote hain — full lagna-based check ke liye exact birth times chahiye.","One chart has a manglik placement (Moon-based check). Cancellation rules often apply — for a full lagna-based check, exact birth times are needed."],
    ["Kisi bhi chart mein manglik dosha nahi hai (Moon-based check). ✅","Neither chart has a manglik flaw (Moon-based check). ✅"],
    // ---- nadi / bhakoot cancellation rules (products.py) — split around interpolated lord names ----
    ["Same nakshatra, alag pada — classical rule mein Nadi dosha cancelled.","Same nakshatra, different pada — in the classical rule the Nadi flaw is cancelled."],
    ["Moon rashi alag hai — widely-followed classical rule mein Nadi dosha cancelled.","The Moon rashi is different — in a widely-followed classical rule the Nadi flaw is cancelled."],
    ["Dono rashiyon ka lord ek hi hai (","Both signs share the same lord ("],
    [") — Bhakoot dosha cancelled.",") — the Bhakoot flaw is cancelled."],
    ["Rashi lords (","The sign lords ("],
    [") mutual friends hain — Bhakoot dosha cancelled.",") are mutual friends — the Bhakoot flaw is cancelled."],
    // ---- notes (products.py, English but carry the token 'dosha') ----
    ["Nadi dosha present — traditionally the most weighted dosha. Note: cancellation applies if moon signs differ or nakshatra padas differ; a detailed pada-level check is recommended.","Nadi flaw present — traditionally the most weighted affliction. Note: cancellation applies if moon signs differ or nakshatra padas differ; a detailed pada-level check is recommended."],
    ["Low score is spread across kootas rather than one dosha — often improvable factors (understanding, timing) rather than structural.","Low score is spread across kootas rather than one flaw — often improvable factors (understanding, timing) rather than structural."],
    // ---- KOOTA_TEXT couple-voiced bands (jyotish_maps.py) ----
    ["Kaam aur ego ke matters mein aap dono ka natural order milta hai — ghar ke decisions mein tug-of-war kam hoga.","In matters of work and ego you both fall into a natural order — there will be less tug-of-war in household decisions."],
    ["Kaam-kaaj aur ego ke sawaalon mein role-clarity conscious rakhni hogi — kaun kya lead karta hai, yeh baat-cheet se tay karo, assumption se nahi.","On questions of work and ego you will have to keep role-clarity conscious — decide who leads what through conversation, not assumption."],
    ["Aap dono ka ek dusre par sway balanced hai — koi kisi ko 'chala' nahi raha, dono saath chal rahe hain.","Your sway over each other is balanced — neither is 'driving' the other, you are both moving together."],
    ["Influence ek taraf thoda zyada hai — jab tak dominant partner ise care se use kare, yeh stability deta hai.","The influence tilts a little to one side — as long as the dominant partner uses it with care, it lends stability."],
    ["Mutual pull kam hai — matlab rishta convince karne se nahi, respect karne se chalega. Space dena yahan pyaar dikhaane ka tareeka hai.","The mutual pull is low — meaning the relationship will run on respect, not persuasion. Giving space is the way to show love here."],
    ["Nakshatra-count dono taraf shubh hai — saath rehne se dono ki wellbeing badhti hai, classical texts ise strong protection maanti hain.","The nakshatra-count is auspicious both ways — being together raises the wellbeing of both, and classical texts consider this strong protection."],
    ["Ek direction shubh, ek nahi — ek partner ko rishtey se zyada milta hai. Balance ke liye giving conscious rakhni hogi.","One direction is auspicious, one is not — one partner gains more from the relationship. To keep balance, giving will have to stay conscious."],
    ["Tara count inauspicious hai — traditionally health/wellbeing par dhyaan. Practical matlab: ek dusre ki sehat aur stress ka khayal is jodi ka zaroori ritual hona chahiye.","The Tara count is inauspicious — traditionally, attention to health/wellbeing. Practical meaning: caring for each other's health and stress should be an essential ritual for this couple."],
    ["Instinctive aur physical wavelength naturally milti hai — bina koshish ke comfort, jo har jodi ko naseeb nahi hota.","The instinctive and physical wavelength meets naturally — effortless comfort, which not every couple is blessed with."],
    ["Physical-instinctive match neutral hai — chemistry banayi ja sakti hai, bas dono ki pace alag ho sakti hai; patience rakho.","The physical-instinctive match is neutral — chemistry can be built, only your paces may differ; keep patience."],
    ["Yoni enemy-pair hai — instincts alag chalti hain. Yeh attraction ko nahi rokta, par daily-life habits (sona, uthna, touch, space) mein adjustment maangta hai. Naam se mat daro, pattern samjho.","This is a Yoni enemy-pair — instincts run differently. This does not stop attraction, but it asks for adjustment in daily-life habits (sleeping, waking, touch, space). Do not fear the name, understand the pattern."],
    ["Moon-lords doston mein hain — aap dono ka sochne ka tareeka compatible hai. Behas hogi toh bhi bhasha ek hi hogi.","The Moon-lords are friends — the two of you think in compatible ways. Even when there is an argument, the language will be the same."],
    ["Moon-lords neutral hain — mental wavelength banti hai shared experiences se. Saath cheezein karo, wavelength khud align hogi.","The Moon-lords are neutral — mental wavelength builds through shared experiences. Do things together and the wavelength will align on its own."],
    ["Moon-lords ki adaawat hai — matlab default sochne ke tareeke alag hain. Iska ilaaj hai 'translate' karna seekhna: partner ki baat ko uske frame mein samajhna, apne mein nahi.","The Moon-lords are at odds — meaning your default ways of thinking differ. The remedy is learning to 'translate': understanding your partner's point in their frame, not your own."],
    ["Temperament same category ka hai — energy levels, social style, gussa-shanti ka pattern milta hai.","The temperament is of the same category — energy levels, social style, and the anger-and-calm pattern all match."],
    ["Deva-Manushya pairing — ek zyada idealist, ek zyada practical. Achhi jodi, bas expectations ko naam dena seekho.","A Deva-Manushya pairing — one more idealist, one more practical. A good match, just learn to name your expectations."],
    ["Gana mismatch hai — temperament genuinely alag hain (jaise ek ko bheed chahiye, ek ko sannata). Yeh deal-breaker nahi, design-brief hai: ghar aisa banao jismein dono modes ki jagah ho.","There is a Gana mismatch — temperaments are genuinely different (say, one needs a crowd, the other silence). This is not a deal-breaker, it is a design-brief: build a home that has room for both modes."],
    ["Moon-signs ki relative position shubh hai — emotional bond aur family-growth ke liye classical green signal.","The relative position of the Moon-signs is auspicious — a classical green signal for the emotional bond and family-growth."],
    ["Bhakoot dosha hai — 6-8, 2-12 ya 5-9 ki position. Traditionally emotional distance ya financial friction se joda jaata hai. Cancellation check neeche dekho — aksar lords ki dosti ise cancel kar deti hai.","There is a Bhakoot flaw — a 6-8, 2-12 or 5-9 position. Traditionally it is linked to emotional distance or financial friction. See the cancellation check below — often the lords' friendship cancels it."],
    ["Nadi alag hai — sabse heavy koota clear hai. Classical texts iske liye sabse zyada points isi liye deti hain.","The Nadi is different — the heaviest koota is clear. That is exactly why classical texts award the most points for it."],
    ["Nadi same hai — traditionally sabse serious dosha, progeny aur vitality se juda. LEKIN: iske cancellation rules sabse well-defined hain. Neeche ka cancellation-check hi asli verdict hai, yeh zero nahi.","The Nadi is the same — traditionally the most serious flaw, tied to progeny and vitality. BUT: its cancellation rules are the most well-defined. The cancellation-check below is the real verdict, not this zero."],
    // ---- ELEMENT_PAIR couple text (jyotish_maps.py) ----
    ["Do fire moons — passion, speed aur honesty double; conflict bhi bright jalta hai par jaldi bujhta hai. Rule seekhiye: ek waqt par ek hi jale.","Two fire moons — passion, speed and honesty are doubled; conflict too burns bright but dies down fast. Learn the rule: only one burns at a time."],
    ["Do earth moons — stability, saving, building. Rishta ghar jaisa lagta hai; risk sirf yeh ki routine romance ko na kha jaaye.","Two earth moons — stability, saving, building. The relationship feels like home; the only risk is that routine may eat the romance."],
    ["Do air moons — baatein kabhi khatam nahi hongi. Mental match excellent; grounding (routine, decisions) ko conscious effort dena hoga.","Two air moons — the conversations will never end. The mental match is excellent; grounding (routine, decisions) will need conscious effort."],
    ["Do water moons — bina bole samajhna. Emotional depth rare-level ki hai; mood ek dusre par lehron ki tarah aate hain, isliye ek ka calm rehna zaroori.","Two water moons — understanding without words. The emotional depth is rare; moods wash over each other like waves, so it is essential that one stays calm."],
    ["Fire + earth — spark aur zameen. Ek raftaar laata hai, doosra thehraav. Fire ko patience, earth ko thodi spontaneity seekhni hogi — phir yeh builder-jodi hai.","Fire + earth — spark and ground. One brings pace, the other steadiness. Fire will have to learn patience, earth a little spontaneity — then this is a builder-couple."],
    ["Fire + air — hawa aag ko badhaati hai. Energy, plans, adventures — natural chemistry. Dhyaan bas itna: dono udna jaante hain, landing kaun karayega yeh tay kar lo.","Fire + air — air feeds the flame. Energy, plans, adventures — natural chemistry. Just note: both know how to fly, so settle who will handle the landing."],
    ["Fire + water — bhaap banti hai: intense attraction, intense reactions. Fire ko softness, water ko directness seekhni hogi. Mehnat maangta hai, magic deta hai.","Fire + water — steam forms: intense attraction, intense reactions. Fire will have to learn softness, water directness. It demands effort, it gives magic."],
    ["Earth + air — practical milta hai conceptual se. Air ideas laata hai, earth unhe khada karta hai. Pace ka difference hi friction hai, aur wahi complementarity bhi.","Earth + air — the practical meets the conceptual. Air brings ideas, earth stands them up. The difference in pace is the friction, and also the very complementarity."],
    ["Earth + water — mitti aur paani: sabse naturally nourishing pair. Ek security deta hai, doosra depth. Classical texts ise sahaj-anukool maanti hain.","Earth + water — soil and water: the most naturally nourishing pair. One gives security, the other depth. Classical texts consider this innately compatible."],
    ["Air + water — words milte hain feelings se. Air ko seekhna hoga ki har baat logic nahi hoti; water ko, ki har baat kehni padti hai. Bridge bana toh poetry hai.","Air + water — words meet feelings. Air will have to learn that not everything is logic; water, that not everything can go unsaid. Build the bridge and it is poetry."],
    // ---- ELEMENT_HI labels (jyotish_maps.py) ----
    ["Agni (fire)","Fire"],
    ["Prithvi (earth)","Earth"],
    ["Vayu (air)","Air"],
    ["Jal (water)","Water"],
    // ---- catch-all: any residual 'dosha' token -> 'flaw' (applied last, shortest) ----
    ["dosha","flaw"]
  ];
  var EXACT = {"HAAN":"YES","NAHI":"NO","नहीं":"NO","HAN":"YES","Pichhle saal":"Past years","kab":"when","aur":"and","Graha":"Planet","Bhaav":"House","hai.":"."};
  var TITLE = { en: "Horoscope Matching | Axtroshastra" };
  function norm(s){ return s.replace(/ /g," ").replace(/ [‐‑‒–—-] /g," — ").replace(/[‐‑‒–—]/g,"—").replace(/\s+/g," "); }
  var SORTED = FRAG.map(function(p){ return [norm(p[0]), p[1]]; }).sort(function(a,b){ return b[0].length - a[0].length; });
  function walk(node, fn){
    for(var i=0;i<node.childNodes.length;i++){
      var n=node.childNodes[i];
      if(n.nodeType===3){ fn(n); }
      else if(n.nodeType===1 && n.tagName!=='SCRIPT' && n.tagName!=='STYLE' && n.id!=='axlang'){ walk(n, fn); }
    }
  }
  function translate(hi){
    var t=norm(hi), trimmed=t.trim();
    if(Object.prototype.hasOwnProperty.call(EXACT, trimmed)){ return t.replace(trimmed, EXACT[trimmed]); }
    for(var i=0;i<SORTED.length;i++){ if(t.indexOf(SORTED[i][0])>=0){ t = t.split(SORTED[i][0]).join(SORTED[i][1]); } }
    return t;
  }
  function apply(lang){
    walk(document.body, function(tn){
      if(lang!=='en'){ if(tn.__hi!=null) tn.nodeValue = tn.__hi; return; }
      if(tn.__hi==null) tn.__hi = tn.nodeValue;
      if(!tn.__hi.trim()) return;
      tn.nodeValue = translate(tn.__hi);
    });
    document.documentElement.lang = (lang==='en')?'en':'hi-IN';
    if(lang==='en' && TITLE.en){ if(!window.__titlehi) window.__titlehi=document.title; document.title=TITLE.en; }
    else if(window.__titlehi){ document.title=window.__titlehi; }
    try{ localStorage.setItem('axlang', lang); }catch(e){}
    var box=document.getElementById('axlang');
    if(box){ box.querySelector('[data-l=hi]').classList.toggle('on', lang!=='en'); box.querySelector('[data-l=en]').classList.toggle('on', lang==='en'); }
    window.__axlang=lang;
    document.documentElement.classList.remove('ax-pre');
  }
  var css=document.createElement('style');
  css.textContent='#axlang{position:fixed;top:10px;right:10px;z-index:9999;display:flex;background:rgba(21,28,57,.92);border:1px solid #E4B04A;border-radius:20px;overflow:hidden;font:600 12px/1 -apple-system,Segoe UI,sans-serif;box-shadow:0 4px 14px rgba(0,0,0,.25)}#axlang button{background:transparent;color:#C9CBDB;border:0;padding:7px 13px;cursor:pointer;letter-spacing:.02em}#axlang button.on{background:#E4B04A;color:#151C39}@media print{#axlang{display:none}}';
  document.head.appendChild(css);
  apply('en');   // language toggle removed — Milan report is English-only
  window.axShare=function(){var url=location.href;var t=window.AX_SHARE_TEXT||'Check out our compatibility report from Axtroshastra';if(navigator.share){navigator.share({title:'Axtroshastra',text:t,url:url}).catch(function(){});}else{window.open('https://wa.me/?text='+encodeURIComponent(t+' '+url),'_blank');}};
})();
</script>
"""


def render_report(p: dict) -> str:
    meta, sig, mg = p["meta"], p["significators"], p["manglik"]
    name = escape(meta["name"])  # user-supplied: escape to prevent stored XSS
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
<section class="pg"><p class="plabel">Quiet periods</p>
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

    # ---------- NEW: past analysis ----------
    ex = p.get("extras", {})
    past_html = ""
    if ex.get("past"):
        rows_p = ""
        lbl = {"active": ("#2E7D53", "ACTIVE"), "mild": ("#E4B04A", "MILD"),
               "quiet": ("#8F92AB", "QUIET")}
        for pp in ex["past"]:
            c, t = lbl[pp["label"]]
            rows_p += (f"<div class='past'><span class='pl' style='background:{c}'>{t}</span>"
                       f"<b>{pp['from']} – {pp['to']}</b>"
                       f"<p class='pd'>{pp['dasha']}</p>"
                       f"<p class='pw'>{' · '.join(pp['why'])}</p></div>")
        past_html = f"""<section class="pg"><p class="plabel">Pichhle saal</p>
<h2>Ab tak kya hua — aur kyun</h2>
<p>Aapke pichhle periods ka chart-analysis. Agar rishtey aaye par bane nahi,
ya bilkul shaant raha — yahan uski wajah dikhegi:</p>{rows_p}
<p class="soft">Yeh section isliye hai taaki aap dekh sakein: timing ek pattern hai,
aapki kami nahi. Jo beet gaya usmein bhi chart ka logic tha.</p></section>"""

    # ---------- NEW: year-by-year outlook ----------
    yo_html = ""
    if ex.get("year_outlook"):
        cards_y = ""
        for y in ex["year_outlook"]:
            gr = (f"<span class='ygrade' style='background:{GRADE_COLOR[y['grade']]}'>{y['grade'].upper()} WINDOW</span>"
                  if y["grade"] else "<span class='ygrade' style='background:#8F92AB'>NO MAJOR WINDOW</span>")
            jup = ("Jupiter ka transit is saal supportive houses mein hai — conversations ko aage badhaane ka saath milega."
                   if y["jupiter_supportive"] else
                   "Jupiter ka transit is saal neutral zone mein hai — effort par zyada, luck par kam depend kijiye.")
            fav = (f"<p class='yfav'>⭐ Favourable months: {', '.join(y['fav_months'])}</p>"
                   if y["fav_months"] else "")
            cards_y += (f"<div class='ycard'><div class='ytop'><b>{y['year']}</b>{gr}</div>"
                        f"<p class='yd'>{' / '.join(y['dashas'])}</p><p>{jup}</p>{fav}</div>")
        yo_html = f"""<section class="pg"><p class="plabel">Saal-dar-saal</p>
<h2>Agle 3 saal — ek nazar mein</h2>{cards_y}
<p class="soft">Yeh page save kar lijiye — har saal ke shuru mein dobara padhne layak hai.</p></section>"""

    # ---------- NEW: love pattern (nakshatra + venus) ----------
    lp_html = ""
    if ex.get("nak_profile"):
        np_ = ex["nak_profile"]
        lp_html = f"""<section class="pg"><p class="plabel">Aapka pattern</p>
<h2>Aap pyaar kaise karte hain — chart ke hisaab se</h2>
<div class="card2"><b>Aapka nakshatra: {np_['nakshatra']} ({np_['symbol']})</b>
<p>{np_['nature']}.</p><p style="margin-top:8px">{np_['relationship']}.</p></div>
<div class="card2" style="margin-top:12px"><b>Aapka Venus</b>
<p>Your love-style is {ex['venus_style']}.</p></div></section>"""

    # ---------- NEW: three checks + sade sati ----------
    ck_html = ""
    if ex.get("checks"):
        ck = ex["checks"]; ss = ex.get("sade_sati", {})
        def yn(v, yes, no):
            return (f"<div class='chk'><span class='cy'>HAAN</span><p>{yes}</p></div>" if v
                    else f"<div class='chk'><span class='cn'>NAHI</span><p>{no}</p></div>")
        ss_html = ""
        if ss.get("active"):
            ss_html = (f"<div class='ss'><b>Sade Sati check: chal rahi hai</b> — {ss['phase']}, "
                       f"till <b>{ss['ends']}</b>. Iska matlab delay ka pressure, denial nahi — "
                       f"Shani ke period mein bani shaadiyan sabse tikau maani jaati hain. "
                       f"Windows upar isi ko account karke grade hue hain.</div>")
        else:
            ss_html = (f"<div class='ss'><b>Sade Sati check: abhi nahi chal rahi.</b> "
                       f"Next phase {ss.get('next_starts','—')} se. Filhaal Shani ka is angle se koi delay-pressure nahi.</div>")
        ck_html = f"""<section class="pg"><p class="plabel">3 aur sach</p>
<h2>Jo aapne nahi poocha, par jaanna chahenge</h2>
{yn(ck['late_marriage_influence'],
"Saturn ka influence aapke 7th house par hai — timing mein maturity-factor hai. Matlab: shaadi thodi der se, par zyada soch-samajh ke. Late ≠ never.",
"Saturn ka koi direct influence aapke 7th house par nahi — classical 'late marriage' indicator aapke chart mein absent hai.")}
{yn(ck['love_leaning'],
"Aapke chart mein 5th–7th connection hai — love-marriage ya self-driven rishtey ka yog. Arranged setup mein bhi pasand aapki hi chalegi.",
"Chart ka jhukaav traditional/arranged path ki taraf hai — introductions aur family networks se hi strong yog banta hai.")}
{yn(ck['foreign_or_intercommunity'],
"Rahu/12th ka 7th se connection hai — partner doori se, alag community se, ya unexpected background se aane ka yog hai. Surprise ke liye taiyaar rahiye.",
"Partner ka yog aapke apne circle aur community ke aas-paas ka hai — door ka yog chart mein prominent nahi.")}
{ss_html}</section>"""

    # ---------- NEW: remedies (agency-first) ----------
    rem_html = ""
    if ex.get("remedies"):
        rm = ex["remedies"]
        gem_line = (f"<li><b>Gemstone:</b> {rm['gem']} — kisi qualified jeweller/astrologer se " 
                    f"trial ke baad hi.</li>" if rm["gem"] else
                    f"<li><b>Gemstone:</b> {rm['gem_note']}</li>")
        rem_html = f"""<section class="pg"><p class="plabel">Weak periods mein</p>
<h2>Traditional support — bina dar ke</h2>
<p>Aapke 7th lord <b>{rm['lord']}</b> ke hisaab se, weak windows mein classical support:</p>
<ul class="rem"><li><b>Vrat/fast:</b> {rm['fast_day']}</li>
<li><b>Mantra:</b> {rm['mantra']} — 108 baar, {rm['fast_day']} ko</li>{gem_line}</ul>
<p class="soft">Order yaad rakhiye: pehla remedy hamesha action hai — strong window mein
actively dhoondhna. Yeh support hai, substitute nahi.</p></section>"""

    w1 = p["windows"][0] if p["windows"] else None
    pretty = lambda ym: datetime.strptime(ym, "%Y-%m").strftime("%b %Y")
    summary = (f"<p class='sline'><b>Top window:</b> {pretty(w1['start'])} – "
               f"{pretty(w1['end'])} ({w1['grade']})</p>" if w1 else "")
    mg_short = {"non_manglik": "No", "manglik_cancelled": "Cancelled (effectively no)",
                "manglik": "Yes — see page 5"}[mg["status"]]
    w2 = p["windows"][1] if p["windows"] and len(p["windows"]) > 1 else None
    _mg_line = {"non_manglik": "Manglik: Nahi — is taraf koi rukaawat nahi.",
                "manglik_cancelled": "Manglik: technically haan, par cancel ho gaya — practically Nahi.",
                "manglik": "Manglik: Haan — page 5 par detail aur cancellation check dekhiye."}[mg["status"]]
    top_summary = ""
    if w1:
        top_summary = (
            "<section class='pg'><div class='ans'>"
            + "<p class='plabel'>Aapka jawab — ek nazar mein</p>"
            + "<h2>Shaadi kab hogi? — seedha jawab</h2>"
            + f"<p class='ans-win'><b>Sabse strong window:</b> {pretty(w1['start'])} – {pretty(w1['end'])} <span class='g'>({w1['grade']})</span></p>"
            + (f"<p class='ans-win2'>Uske baad: {pretty(w2['start'])} – {pretty(w2['end'])} ({w2['grade']})</p>" if w2 else "")
            + f"<p class='ans-mg'>{_mg_line}</p>"
            + "<p class='ans-note'>Yeh jawab aapke poore chart se nikla hai. Neeche har window ki wajah, aapka Navamsa, aur beete periods — taaki aap khud milaa sakein.</p>"
            + "</div></section>"
        )

    rectify_hook = ""
    if meta["time_quality"] in ("T1", "T2", "T3"):
        rectify_hook = """<div class="upsell"><b>Birth time approximate tha?</b>
<p>Rectification analysis aapke life events se exact time narrow karta hai —
windows 6 months tak refine ho sakte hain. <a href='https://wa.me/919599827297?text=RECTIFY' style='color:#C93B2E;font-weight:700'>WhatsApp par RECTIFY bhejiye →</a></p></div>"""

    facts = p["chart"]["planets"]
    sl = sig["seventh_lord"]
    sl_d = facts[sl]["dignity"]
    dignity_txt = {"own": "apne hi sign mein — strong placement",
                   "exalted": "exalted — best possible dignity",
                   "debilitated": "debilitated — timing par extra dhyaan",
                   "neutral": "neutral dignity"}[sl_d]

    return f"""<!DOCTYPE html><html lang="hi-IN"><head>{AX_PRE}<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} — Marriage Timing Report | Axtroshastra</title>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&display=swap" rel="stylesheet">
<style>
:root{{--ink:#23253B;--midnight:#151C39;--paper:#FAF6ED;--sindoor:#C93B2E;
--haldi:#E4B04A;--haldi-soft:#F6E7C6;--muted:#6B6D82;--line:#E7E0D2;
--display:'Bricolage Grotesque',sans-serif;
--body:-apple-system,'Segoe UI',Roboto,sans-serif}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:var(--body);background:var(--paper);color:var(--ink);line-height:1.6;font-size:15.5px}}
.pg{{max-width:640px;margin:0 auto;padding:40px 22px;border-bottom:1.5px dashed var(--line)}}
.plabel{{font-family:var(--display);font-weight:700;font-size:11px;
text-transform:uppercase;color:var(--sindoor);margin-bottom:10px}}
h1,h2{{font-family:var(--display);line-height:1.15}}
h2{{font-size:24px;font-weight:800;margin-bottom:14px}}
.soft{{color:var(--muted);font-size:14px;margin-top:14px}}
/* cover */
.cover{{background:radial-gradient(900px 500px at 50% -10%,#1D2547,var(--midnight));
color:#F3EFE4;text-align:center;border:none}}
.cover .brand{{font-family:var(--display);font-weight:800;color:var(--haldi);
letter-spacing:.06em;font-size:14px;margin-bottom:26px}}
.cover h1{{font-size:30px;font-weight:800;color:#fff}}
.cover .bd{{color:#A9ABC0;font-size:14px;margin:8px 0 24px}}
.kchart{{max-width:320px;margin:0 auto}}
.cover .method{{font-size:11.5px;color:#8F92AB;margin-top:20px}}
/* snapshot */
.facts{{background:#fff;border:1.5px solid var(--line);border-radius:14px;padding:6px 18px}}
.facts .row{{display:flex;justify-content:space-between;gap:14px;padding:11px 0;
border-bottom:1px dashed var(--line);font-size:15px}}
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
.wnum{{font-family:var(--display);font-weight:700;font-size:12px;
text-transform:uppercase;color:var(--muted)}}
.wgrade{{color:#fff;font-family:var(--display);font-weight:800;font-size:11px;
border-radius:20px;padding:4px 12px}}
.wdates{{font-family:var(--display);font-weight:800;font-size:22px}}
.core{{font-size:14px;color:var(--muted);margin-top:2px}}
.peak{{font-size:14px;color:#2E7D53;font-weight:600;margin-top:6px}}
.wdasha{{font-size:13.5px;color:var(--muted);margin-top:6px}}
.wwhy{{margin:10px 0 0 18px;font-size:14px}}.wwhy li{{margin-bottom:4px}}
/* manglik */
.mgcard{{background:var(--haldi-soft);border-radius:14px;padding:20px}}
.mgcard b.h{{font-family:var(--display);font-size:17px;display:block;margin-bottom:8px}}
/* quiet + actions */
.quiet,.act{{background:#fff;border:1.5px solid var(--line);border-radius:12px;
padding:14px 16px;margin-bottom:10px;font-size:15px}}
.quiet b,.act b{{font-family:var(--display)}}
/* summary */
.sumcard{{background:var(--midnight);color:#F3EFE4;border-radius:16px;padding:24px;text-align:center}}
.sumcard .nm{{font-family:var(--display);font-weight:800;font-size:20px;color:#fff}}
.sline{{margin-top:10px;font-size:15px}}
.sumcard .sline b{{color:var(--haldi)}}
.past{{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:10px}}
.pl{{color:#fff;font-family:var(--display);font-weight:800;font-size:10.5px;border-radius:16px;padding:3px 10px;margin-right:10px}}
.pd{{font-size:13.5px;color:var(--muted);margin-top:5px}}.pw{{font-size:14px;margin-top:4px}}
.ycard{{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:15px 16px;margin-bottom:10px}}
.ytop{{display:flex;justify-content:space-between;align-items:center;font-family:var(--display);font-size:19px;margin-bottom:6px}}
.ygrade{{color:#fff;font-family:var(--display);font-weight:800;font-size:10.5px;border-radius:16px;padding:4px 10px}}
.yd{{font-size:13.5px;color:var(--muted);margin-bottom:5px}}.ycard p{{font-size:15px}}
.yfav{{color:#2E7D53;font-weight:600;font-size:14px;margin-top:5px}}
.card2{{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:16px}}
.card2 b{{font-family:var(--display);display:block;margin-bottom:6px}}.card2 p{{font-size:15px}}
.chk{{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:10px;display:flex;gap:12px;align-items:flex-start}}
.cy,.cn{{flex:none;color:#fff;font-family:var(--display);font-weight:800;font-size:11px;border-radius:16px;padding:4px 11px;margin-top:2px}}
.cy{{background:#2E7D53}}.cn{{background:#8F92AB}}.chk p{{font-size:15px}}
.ss{{background:var(--haldi-soft);border-radius:12px;padding:15px;font-size:15px;margin-top:14px}}
.rem{{margin:12px 0 0 20px}}.rem li{{margin-bottom:8px;font-size:15px}}
.upsell{{background:#fff;border:2px solid var(--haldi);border-radius:14px;
padding:16px;margin-top:16px;font-size:15px}}
.btnrow{{display:flex;gap:10px;margin-top:20px}}
.btn{{flex:1;font-family:var(--display);font-weight:800;font-size:15px;text-align:center;
padding:13px;border-radius:11px;border:0;cursor:pointer;text-decoration:none}}
.btn.p{{background:var(--sindoor);color:#fff}}.btn.s{{background:#fff;border:1.5px solid var(--line);color:var(--ink)}}
footer{{text-align:center;font-size:11.5px;color:var(--muted);padding:26px 20px 44px;max-width:640px;margin:0 auto}}
@media print{{.btnrow{{display:none}}.pg{{border:none;padding:14px 6px;max-width:100%}}
.wcard,.mgcard,.quiet,.act,.ycard,.card2,.chk,.past,.ss,.rem,.upsell,.ans,.sumcard,.review,.facts .row,.acard{{break-inside:avoid}}
.cover{{padding:40px 8px}}
body{{background:#fff}}.cover{{background:var(--midnight)!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}}}}
</style></head><body>

<section class="pg cover">
  <p class="brand">✦ AXTROSHASTRA</p>
  <h1>{name}</h1>
  <p class="bd">Marriage Timing Report · Generated {meta['generated']}</p>
  {north_chart_svg(p)}
  <p class="method">NASA JPL data (Swiss Ephemeris) · Lahiri ayanamsa · Whole-sign houses · {system_note}</p>
</section>

{top_summary}
<section class="pg"><p class="plabel">Chart snapshot</p>
<h2>Aapka chart — marriage lens se</h2>
<div class="facts">
  <div class="row"><span class="k">Lagna</span><span class="v">{p['chart']['lagna']}</span></div>
  <p class="why">Aapki personality aur poore chart ka base — har bhaav isi se gina jaata hai.</p>
  <div class="row"><span class="k">Moon · Nakshatra</span><span class="v">{p['teaser']['moon_sign']} · {p['teaser']['nakshatra']}</span></div>
  <p class="why">Aapka mann aur emotional nature. Aapki dasha timeline isi Moon-nakshatra se chalti hai — yahi timing ka engine hai.</p>
  <div class="row"><span class="k">7th house</span><span class="v">{seventh_sign}</span></div>
  <p class="why">Shaadi, partner aur commitment ka ghar — marriage ka main area.</p>
  <div class="row"><span class="k">7th lord</span><span class="v">{sl} — {dignity_txt}</span></div>
  <p class="why">Shaadi ka main switch. Iski dignity (upar) timing ki quality batati hai — strong matlab saaf timing, tender matlab zyada soch-samajh.</p>
  <div class="row"><span class="k">Marriage karaka</span><span class="v">{' + '.join(sig['karakas'])}</span></div>
  <p class="why">Rishton ka natural indicator (Venus/Jupiter) — yeh shaadi ka promise dikhata hai.</p>
  <div class="row"><span class="k">Darakaraka</span><span class="v">{sig['darakaraka']}</span></div>
  <p class="why">Jaimini system ka spouse-significator — partner ki ek jhalak.</p>
  <div class="row"><span class="k">Current period</span><span class="v">{p['teaser']['current_dasha']}<br>till {p['teaser']['dasha_till']}</span></div>
  <p class="why">Abhi kaunsi dasha chal rahi hai. Windows isi timeline par bante hain — isliye yeh sabse relevant.</p>
</div>
<p class="soft">Yeh 6-7 factors milkar aapki marriage timing decide karte hain.
Agle page par inhi se nikale gaye aapke windows hain.</p></section>
{report_addons.planet_table_html(p)}

<section class="pg"><p class="plabel">The Answer</p>
<h2>Aapke marriage windows</h2>
<div class="tl"><div class="tltrack">{tl_windows}</div>
<div class="tlyrs">{years_axis}</div></div>
{window_cards}</section>

<section class="pg"><p class="plabel">Method</p>
<h2>Yeh windows kaise nikle</h2>
<p>Har window ke card mein uske reasons diye hain — kaunsi dasha, kaunsa connection.
Broad logic: <b>marriage typically triggers jab dasha/antardasha lord aapke 7th house
ya uske lord se connect hota hai, aur Jupiter ka transit usko confirm karta hai.</b></p>
<p style="margin-top:10px">Timing windows probability bands hain, appointments nahi —
±15 minute ka birth time difference bhi boundaries ko months tak shift kar sakta hai.
Isliye hum honest ranges dete hain, fake precision nahi.</p></section>
{report_addons.scoring_box_html(p)}

<section class="pg"><p class="plabel">Manglik</p>
<h2>Manglik check</h2>
<div class="mgcard"><b class="h">{mg_head}</b><p>{mg_body}</p></div>
<p class="soft">Technical: Mars from lagna — {'manglik houses mein' if mg['from_lagna'] else 'clear'};
from Moon — {'manglik houses mein' if mg['from_moon'] else 'clear'}.</p></section>
{report_addons.d9_section_html(p)}

{weak_html}
{past_html}
{yo_html}

<section class="pg"><p class="plabel">Partner</p>
<h2>Partner indications</h2>
{partner_html}
{report_addons.occupants_html(p)}</section>

<section class="pg"><p class="plabel">Action plan</p>
<h2>Ab karna kya hai</h2>
{actions}
<p class="soft">Kundli timing batati hai; effort aur choice aapke haath mein hai.
Strong window mein bhi rishtey dhoondhne padte hain — bas conversion rate better hota hai.</p></section>

{lp_html}
{ck_html}
{rem_html}

<section class="pg"><p class="plabel">Summary</p>
<div class="sumcard">
  <p class="nm">{name}</p>
  {summary}
  <p class="sline"><b>Manglik:</b> {mg_short}</p>
  <p class="sline"><b>Partner direction:</b> {sig['darakaraka']}-type — see page 7</p>
</div>
{rectify_hook}
<div class="upsell"><b>Ek aur sawaal, usi chart se: career kab lift hoga?</b>
<p>Career Timing Report — same precision, ₹299 for report holders. <a href='https://wa.me/919599827297?text=CAREER' style='color:#C93B2E;font-weight:700'>WhatsApp par CAREER bhejiye →</a></p></div>
<div class="btnrow">
  <a class="btn p" id="ax-pdf" href="#" onclick="window.print();return false;">Download PDF</a> <button class="ax-share" onclick="axShare()">Share on WhatsApp</button>
  <a class="btn s" href="https://wa.me/919599827297?text=Hi%20Axtroshastra">WhatsApp Support</a>
</div></section>

<footer>Windows are probability estimates from classical dasha–transit principles,
not guarantees. <a href='https://wa.me/919599827297' style='color:inherit'>WhatsApp +91 95998 27297</a> · support@axtroshastra.com<br>Axtroshastra · Computational Vedic Astrology · by Cultnuts · <a href="/privacy" style="color:inherit">Privacy</a> · <a href="/terms" style="color:inherit">Terms</a> · <a href="/refunds" style="color:inherit">Refund Policy</a></footer>
        <div class="ax-wm" aria-hidden="true"><b>AXTROSHASTRA</b><span>axtroshastra.com</span></div>
<section class="pg"><div class="ax-disc"><b>Disclaimer:</b> Yeh report classical Vedic Jyotish (dasha-transit) principles par computed hai — guidance ke liye, guarantee nahi. Timing windows probability hain, fixed dates nahi. Yeh legal, medical ya financial advice nahi hai. Apne life decisions aap apni samajh se lijiye; Axtroshastra kisi outcome ki zimmedari nahi leta.</div><div class="ax-endcard"><b>Axtroshastra</b><br>Yeh report Axtroshastra ne banayi — apna report paayein: <a href="https://www.axtroshastra.com/shaadi">axtroshastra.com</a></div></section>
{REPORT_I18N}
</body></html>"""


# ============================================================ MILAN RENDERER
VERDICT_COLOR = {"excellent": "#2E7D53", "verygood": "#2E7D53",
                 "ok": "#E4B04A", "weak": "#C93B2E"}

# Plain-language decode of each classical koota — modern label + emoji + real-life meaning.
# Sanskrit name (the dict key) is kept as a small credibility subtitle in the UI.
KOOTA_UI = {
    "Varna":        {"emoji": "🧭", "label": "Drive & Ego Balance",
                     "blurb": "who naturally takes the lead — without it turning into a power struggle"},
    "Vashya":       {"emoji": "🧲", "label": "Mutual Pull",
                     "blurb": "how naturally you're drawn to and influence each other"},
    "Tara":         {"emoji": "🍀", "label": "Luck & Wellbeing",
                     "blurb": "whether being together tends to make life feel smoother for you both"},
    "Yoni":         {"emoji": "🔥", "label": "Physical Chemistry",
                     "blurb": "instinctive, physical and intimate compatibility"},
    "Graha Maitri": {"emoji": "🧠", "label": "Mental Wavelength",
                     "blurb": "how easily your minds click and how you talk things through"},
    "Gana":         {"emoji": "🎭", "label": "Vibe & Temperament",
                     "blurb": "your everyday energy, social style and how your moods land"},
    "Bhakoot":      {"emoji": "❤️", "label": "Emotional Bond",
                     "blurb": "long-term closeness and building a life and family together"},
    "Nadi":         {"emoji": "🧬", "label": "Health & Family",
                     "blurb": "vitality and the classical health / progeny factor"},
}

# 5 relatable themes that group the 8 kootas (each koota belongs to exactly one).
THEMES = [
    {"emoji": "🔥", "name": "Chemistry & Attraction", "kootas": ["Yoni", "Vashya"],
     "blurb": "the spark — physical pull and how you gravitate toward each other"},
    {"emoji": "🎭", "name": "Everyday Vibe", "kootas": ["Gana"],
     "blurb": "your day-to-day energy and whether your moods sync"},
    {"emoji": "🧠", "name": "Mind & Values", "kootas": ["Graha Maitri", "Varna"],
     "blurb": "how your minds click, and who leads what"},
    {"emoji": "❤️", "name": "Love & Long-Term", "kootas": ["Bhakoot", "Tara"],
     "blurb": "long-term closeness and how good you are for each other"},
    {"emoji": "🧬", "name": "Health & Vitality", "kootas": ["Nadi"],
     "blurb": "vitality and the traditional family / progeny factor"},
]

def _theme_rows(kootas: list) -> str:
    """Build the 5-theme 'at a glance' cards, strongest first (confidence-first)."""
    out = ""
    for t in _theme_scores(kootas):
        th, got, mx, pct = t["theme"], t["got"], t["mx"], t["pct"]
        if pct >= 75:
            chip, chip_bg, bar_color, verdict = "Strong 💚", "#2E7D53", "#2E7D53", "You're naturally strong here."
        elif pct >= 45:
            chip, chip_bg, bar_color, verdict = "Solid 💛", "#B4881B", "#E4B04A", "Good foundation — a little effort keeps it easy."
        else:
            chip, chip_bg, bar_color, verdict = "Needs work ❤️‍🔥", "#C93B2E", "#C93B2E", "Takes a little conscious effort — and the exact fix is on this factor's card in the breakdown below. 👇"
        got_disp = int(got) if float(got).is_integer() else got
        out += f"""<div class='theme'>
<div class='ttop'><span class='temoji'>{th['emoji']}</span><b>{th['name']}</b>
<span class='tchip' style='background:{chip_bg}'>{chip}</span></div>
<div class='kbar'><div style='width:{pct:.0f}%;background:{bar_color}'></div></div>
<p class='tblurb'>{th['blurb']}. <b>{verdict}</b></p></div>"""
    return out

# For weak / non-matching factors: a practical thing to work on + an optional
# traditional remedy. Agency-first — the action is the real lever, the remedy is
# a cultural add-on for those who want it. No medical or gemstone-buying claims.
# Each weak factor gets: a shared "together" line, a clear who-does-what split
# (p1/p2 by name where the two jobs genuinely differ, or "each" where the action
# is the same for both), and an optional traditional remedy. Splitting the
# responsibility means neither partner assumes the other will handle it.
REMEDIES = {
    "Varna": {
        "work_on": "Spell out who owns which calls — money, home, plans, social life — out loud, instead of assuming.",
        "p1": "Name the one area you most want to lead — and say it plainly.",
        "p2": "Name the one area you're happy to hand over — and genuinely let go of it.",
        "remedy": "A gentle classical practice: offer water to the rising sun together on Sunday mornings — a small shared ritual said to balance ego and authority."},
    "Vashya": {
        "work_on": "A lower pull just means the bond runs on respect, not gravity — so make closeness deliberate, not left to chance.",
        "p1": "Own the plan — set up one proper, protected date this week.",
        "p2": "Own the daily thread — keep the small check-ins going through the week.",
        "remedy": "Venus rules attraction — on Fridays keep something white nearby and repeat 'Om Shukraya Namah' a few times together."},
    "Tara": {
        "work_on": "Make each other's wellbeing a shared project — sleep, food, stress — instead of assuming the other is fine.",
        "p1": "Keep an eye on the basics — nudge each other on rest, food and sleep.",
        "p2": "Keep an eye on the load — check in on stress and what's draining them.",
        "remedy": "On Thursdays, share a simple home-cooked meal and donate a little food or grain together — a traditional gesture for mutual wellbeing."},
    "Yoni": {
        "work_on": "This is about different instincts, not low attraction — so talk openly about pace, touch and daily rhythms.",
        "each": "Name one rhythm — sleep, space or affection — you'd like the other to understand, and ask for theirs.",
        "remedy": "Venus is your ally here too — Friday is the day; soft, warm tones at home and 'Om Shukraya Namah' are the classical nudges for closeness."},
    "Graha Maitri": {
        "work_on": "You think in different 'languages', so practise translating before you react.",
        "each": "In a disagreement, say your partner's point back in their words before you reply — until they say 'yes, that's it.'",
        "remedy": "For mental harmony: green on Wednesdays with 'Om Budhaya Namah' (Mercury), and an unhurried moonlit walk together on Mondays (Moon)."},
    "Gana": {
        "work_on": "Your energies genuinely differ (say, one loves a crowd, one loves quiet). Don't try to fix it — design around it.",
        "each": "Tell the other plainly what recharges you — a night out or a night in — and agree a simple signal for it.",
        "remedy": "A shared calming ritual helps — light a small oil lamp at dusk and chant 'Om Namah Shivaya' together; traditionally it settles temperament clashes."},
    "Bhakoot": {
        "work_on": "The classic risks here are emotional distance and money friction — get ahead of both, and keep daily affection non-negotiable.",
        "p1": "Own the money rhythm — a light monthly 'us & money' check-in.",
        "p2": "Own the emotional rhythm — a regular, honest 'how are we, really?' talk.",
        "remedy": "A Moon remedy: on Mondays wear white, chant 'Om Somaya Namah', and offer milk or white flowers at a Shiva temple together."},
    "Nadi": {
        "work_on": "Traditionally the heaviest factor, tied to health and children — so the real 'remedy' is proactive care, together.",
        "each": "Book your own basics — a check-up, better sleep, less chronic stress; treat wellbeing as a team sport.",
        "remedy": "A classical Nadi practice is the Maha Mrityunjaya mantra and donating toward medicines/health; the modern equivalent is a simple pre-marriage health check for both."},
}

def _koota_fix_html(k: dict, cancelled: set, names=("Partner 1", "Partner 2")) -> str:
    """Inline fix + who-does-what split + traditional remedy, rendered INSIDE a weak
    koota's own card so the concern and its answer are never separated (anxiety stays
    low). The split divides responsibility so neither partner assumes the other will act."""
    if not (k["max"] and k["score"] / k["max"] < 0.5):
        return ""
    rem = REMEDIES.get(k["name"])
    if not rem or not rem.get("work_on"):
        return ""
    n1, n2 = names
    ap = ACTION_PLAN.get(k["name"])
    canc = ("<p class='wcanc'>✅ Traditionally cancelled for you — treat this as a lighter priority.</p>"
            if k["name"] in cancelled else "")
    # who does what — split the responsibility clearly
    if rem.get("each"):
        split = f"<div class='wsplit'><p><span class='wpk'>👥 Each of you</span> {rem['each']}</p></div>"
    else:
        rows = ""
        if rem.get("p1"): rows += f"<p><span class='wpk'>👤 {n1}</span> {rem['p1']}</p>"
        if rem.get("p2"): rows += f"<p><span class='wpk'>👤 {n2}</span> {rem['p2']}</p>"
        split = f"<div class='wsplit'>{rows}</div>" if rows else ""
    talk = (f"<p class='wtalk'><b>💬 Say this:</b> {ap['talk']}</p>"
            if ap and ap.get("talk") else "")
    rem_line = (f"<p class='wrem'><b>🪔 Traditional remedy:</b> {rem['remedy']}</p>"
                if rem.get("remedy") else "")
    return (f"<div class='kfix'>{canc}"
            f"<p class='wdo'><b>💡 Work on it — together:</b> {rem['work_on']}</p>"
            f"{split}{talk}{rem_line}</div>")

# ---------------- Phase-1 expanded-report content + builders ----------------
ELEMENT_EMOJI = {"fire": "🔥", "earth": "🌿", "air": "💨", "water": "🌊"}

LOVE_LANG = {
    "fire": "being pursued — spontaneity, passion, and a partner who matches your spark",
    "earth": "being shown up for — reliability, steady effort, and physical care",
    "air": "being understood — real conversation, wit, and mental connection",
    "water": "being felt — emotional attunement, tenderness, and a sense of safety",
}

# Couple archetype keyed by the frozenset of the two Moon elements (same-element sets have 1 item).
ARCHETYPE = {
    frozenset({"fire"}): {"name": "The Passionate Pair", "emoji": "🔥", "tagline": "Two sparks, double the passion",
        "body": "You two run hot — big feelings, big fun, and the occasional big argument that's over as fast as it started. Your superpower is intensity; your homework is learning that only one of you needs to catch fire at a time."},
    frozenset({"earth"}): {"name": "The Steady Pair", "emoji": "🏡", "tagline": "Steady, safe, built to last",
        "body": "You're the couple friends call 'solid'. You value security, loyalty and a life built brick by brick. The only risk: don't let the routine quietly replace the romance."},
    frozenset({"air"}): {"name": "The Best Friends", "emoji": "💭", "tagline": "Endless talks, always on the same page",
        "body": "You'll never run out of things to talk about — ideas, plans, jokes only you two get. The thing to practise together: turning all those brilliant plans into actual decisions."},
    frozenset({"water"}): {"name": "The Deep Feelers", "emoji": "🌊", "tagline": "You feel everything, together",
        "body": "Rare, almost wordless understanding — you read each other's moods like weather. Beautiful, but when you're both caught in a wave, someone has to be the calm shore."},
    frozenset({"fire", "earth"}): {"name": "Passion Meets Patience", "emoji": "🔥🌿", "tagline": "Drive meets steadiness",
        "body": "One of you brings the pace, the other the patience. Fire learns to slow down, earth learns to loosen up — and together you actually build the things you dream about."},
    frozenset({"fire", "air"}): {"name": "The Adventurers", "emoji": "🔥💨", "tagline": "Energy that keeps growing",
        "body": "Air feeds the flame — adventures, plans, natural chemistry. You both love to fly; just decide early who's handling the landing."},
    frozenset({"fire", "water"}): {"name": "The Magnetic Pair", "emoji": "🔥🌊", "tagline": "Strong pull, strong feelings",
        "body": "Fire and water make steam — magnetic attraction and big reactions. Fire learns softness, water learns directness. It takes effort, and it makes magic."},
    frozenset({"earth", "air"}): {"name": "The Dreamer & The Builder", "emoji": "🌿💨", "tagline": "Ideas meet real plans",
        "body": "Air brings the ideas, earth makes them real. Your different speeds are the friction — and exactly what makes you complete each other."},
    frozenset({"earth", "water"}): {"name": "The Caring Pair", "emoji": "🌿🌊", "tagline": "The most naturally caring match",
        "body": "Soil and water — classical texts call this innately compatible. One gives security, the other depth. This is the easy, home-feeling kind of love."},
    frozenset({"air", "water"}): {"name": "Head & Heart", "emoji": "💭🌊", "tagline": "Clear thinking meets deep feeling",
        "body": "Air learns that not everything is logic; water learns that not everything can go unsaid. Build that bridge and it's pure poetry."},
}
ARCHETYPE_DEFAULT = {"name": "One of a Kind", "emoji": "✨", "tagline": "Your own kind of match",
    "body": "You don't fit a neat box — which is its own kind of interesting."}

# Rich strength copy, keyed by theme name (shown when a theme is strong).
THEME_DEEP = {
    "Chemistry & Attraction": "The spark is real and it's mutual — you're drawn to each other in a way that doesn't need forcing. That easy physical comfort is something a lot of couples spend years trying to build. Keep novelty alive and it stays a strength, not a given.",
    "Everyday Vibe": "Your day-to-day energies just fit — similar social batteries, similar humour, a similar way of handling good days and bad ones. This is the quiet superpower that makes living together feel light instead of like work.",
    "Mind & Values": "You think in the same language. Even your disagreements will make sense to each other, because your values and mental wiring line up. This is the stuff long conversations — and long marriages — are made of.",
    "Love & Long-Term": "Emotionally, you're built to go the distance. Classical texts read this as a green signal for closeness, family and growing together — the deep, settle-in kind of bond rather than just a spark.",
    "Health & Vitality": "On the heaviest traditional factor, you're clear — read as vitality and a healthy foundation for a life (and a family) together. It's the factor astrologers weigh the most, and it's working in your favour.",
}

# Extra action-plan detail for weak factors, keyed by koota.
ACTION_PLAN = {
    "Varna": {"try": "This week, each of you names one area you'd love to lead and one you'd happily hand over.", "talk": "“Where do you want me to take charge — and where do you want to?”", "green": "You stop quietly keeping score of who decided what."},
    "Vashya": {"try": "Lock one proper date into the calendar for the next two weeks — non-negotiable.", "talk": "“What makes you feel closest to me?”", "green": "Time together starts to feel chosen, not squeezed in."},
    "Tara": {"try": "Do one small health thing together — a walk, cooking a real meal, an early night.", "talk": "“What's been draining you lately, and how can I help?”", "green": "You both feel better after time together, not more tired."},
    "Yoni": {"try": "Compare your daily rhythms — sleep, energy, affection — and pick one to sync.", "talk": "“What does feeling close look like for you, day to day?”", "green": "Different paces stop feeling like rejection."},
    "Graha Maitri": {"try": "One 20-minute, phones-away conversation this week — no fixing, just listening.", "talk": "“Let me say that back — did I get it right?”", "green": "You argue in the same language, not past each other."},
    "Gana": {"try": "Agree a simple signal for 'I need people' vs 'I need quiet' — and honour it once.", "talk": "“What recharges you — a night out, or a night in?”", "green": "Different moods stop getting taken personally."},
    "Bhakoot": {"try": "Do a light 15-minute 'us, money & feelings' check-in.", "talk": "“What's something you've been carrying that I haven't noticed?”", "green": "Small distances get named before they grow."},
    "Nadi": {"try": "Book the unglamorous stuff — check-ups, good sleep, less chronic stress — as a team.", "talk": "“How do we want to look after each other's health?”", "green": "You treat wellbeing as a shared project, not a solo one."},
}


def _theme_scores(kootas: list) -> list:
    """Per-theme aggregate scores, strongest first."""
    by = {k["name"]: k for k in kootas}
    out = []
    for th in THEMES:
        got = sum(by[n]["score"] for n in th["kootas"] if n in by)
        mx = sum(by[n]["max"] for n in th["kootas"] if n in by)
        out.append({"theme": th, "got": got, "mx": mx, "pct": (got / mx * 100) if mx else 0})
    out.sort(key=lambda t: t["pct"], reverse=True)
    return out


def milan_one_breath(kootas: list, *, html: bool = False) -> str:
    """The "Your relationship, in one breath" one-line summary.

    Single source of truth for the poetic one-sentence read of the match, used
    both by the full report (milan_v2._synthesis, the owner's "page 17" section)
    and by the free teaser preview on pages/milan.html — so the two never drift.
    Returns plain text by default; with html=True the key phrases are bolded
    (and user-safe escaped) for the report's serif rendering.
    """
    themes = _theme_scores(kootas)
    strong = [t for t in themes if t["pct"] >= 75]
    st = ", ".join(t["theme"]["name"] for t in strong[:3]) or "your foundations"
    weak = themes[-1]["theme"]["name"] if themes else "one area"
    if html:
        return (f'Two people <b>deeply built to last</b> — strong across {escape(st)} — '
                f'with one honest growth edge: <b>{escape(weak)}</b>.')
    return (f"Two people deeply built to last — strong across {st} — "
            f"with one honest growth edge: {weak}.")


# Devanagari theme names for the Hindi one-breath line. Keep in sync with the
# theme-name entries in milan_hi.HI (the report localiser) so preview and
# localised report never disagree on what a theme is called.
THEME_NAME_HI = {
    "Chemistry & Attraction": "कैमिस्ट्री और आकर्षण",
    "Everyday Vibe": "रोज़मर्रा का तालमेल",
    "Mind & Values": "सोच और मूल्य",
    "Love & Long-Term": "प्यार और लंबा साथ",
    "Health & Vitality": "सेहत और जीवनशक्ति",
}


def milan_one_breath_hi(kootas: list) -> str:
    """Devanagari twin of milan_one_breath — the SAME theme logic (strong themes
    listed, weakest named), rendered as the equivalent warm Hindi sentence. Used
    by the free teaser on pages/milan.hi.html via compute_milan's one_breath_hi.
    Deterministic: static tables only, no runtime translation."""
    themes = _theme_scores(kootas)
    strong = [t for t in themes if t["pct"] >= 75]
    st = ", ".join(THEME_NAME_HI.get(t["theme"]["name"], t["theme"]["name"])
                   for t in strong[:3]) or "आपकी बुनियाद"
    weak = (THEME_NAME_HI.get(themes[-1]["theme"]["name"], themes[-1]["theme"]["name"])
            if themes else "एक क्षेत्र")
    return (f"दो लोग जो गहराई से टिकने के लिए बने हैं — {st} में मज़बूत — "
            f"बस एक ईमानदार ग्रोथ एरिया के साथ: {weak}।")


def _archetype(profiles: dict) -> dict:
    return ARCHETYPE.get(frozenset({profiles["p1"]["element"], profiles["p2"]["element"]}), ARCHETYPE_DEFAULT)


def _match_band(pct: int):
    if pct >= 80: return ("an exceptional match", "#2E7D53")
    if pct >= 67: return ("a strong match", "#2E7D53")
    if pct >= 50: return ("a workable match", "#B4881B")
    return ("a match that'll take some work", "#C93B2E")


def _match_pct(p: dict) -> int:
    return int(p.get("match_pct") or round(p.get("effective", p["total"]) / 36 * 100))


def _share_text(p: dict) -> str:
    """Personalised share caption (couple type + match %). Plain text, not HTML."""
    arche = _archetype(p["profiles"]); pct = _match_pct(p)
    p1 = p["profiles"]["p1"]["name"]; p2 = p["profiles"]["p2"]["name"]
    return (f"{p1} ✕ {p2}: turns out we're {arche['name']} {arche['emoji']} — "
            f"{pct}% compatible on what actually matters 💫 Checked it on Axtroshastra:")


def _opening_note(p: dict) -> str:
    arche = _archetype(p["profiles"])
    ts = _theme_scores(p["kootas"])
    p1 = escape(p["profiles"]["p1"]["name"]); p2 = escape(p["profiles"]["p2"]["name"])
    pct = _match_pct(p); phrase, _ = _match_band(pct)
    top = ts[0]["theme"]; weak = ts[-1]
    strong_line = f"You're strongest in <b>{top['name'].lower()}</b> — {top['blurb']}."
    if weak["pct"] < 55:
        grow_line = (f" The one area worth a little intention is <b>{weak['theme']['name'].lower()}</b> — "
                     "and we've put simple, doable steps for it further down.")
    else:
        grow_line = " And honestly, there's no weak link here worth losing sleep over."
    return (f"<div class='opennote'><p>{p1} &amp; {p2} — on the classical Ashtakoota system you come out as "
            f"<b>{arche['name']}</b> {arche['emoji']}, {phrase} at <b>{pct}%</b> on the things that actually "
            f"matter in a relationship.</p><p>{strong_line}{grow_line}</p>"
            f"<p class='onsub'>Here's the full picture — the good stuff first. 💛</p></div>")


def _sharecard_html(p: dict) -> str:
    arche = _archetype(p["profiles"])
    ts = _theme_scores(p["kootas"])
    strong = [t for t in ts if t["pct"] >= 60][:3] or ts[:2]
    chips = "".join(f"<span class='scchip'>{t['theme']['emoji']} {t['theme']['name']}</span>" for t in strong)
    p1 = escape(p["profiles"]["p1"]["name"]); p2 = escape(p["profiles"]["p2"]["name"])
    pct = _match_pct(p)
    return (f"<div class='sharecard' id='sharecard'>"
            f"<div class='scbrand'>✦ AXTROSHASTRA · COMPATIBILITY</div>"
            f"<div class='scnames'>{p1} <span>✕</span> {p2}</div>"
            f"<div class='scarch'>{arche['emoji']} {arche['name']}</div>"
            f"<div class='scpct'>{pct}<small>% match on what matters</small></div>"
            f"<div class='scchips'>{chips}</div>"
            f"<div class='sctag'>“{arche['tagline']}”</div></div>"
            f"<p class='sctag2'>{arche['body']}</p>"
            f"<div class='sharebtns'>"
            f"<button class='sharebtn' onclick='axShare()'>Share link 💫</button>"
            f"</div>")


def _milan_chart_block(pr: dict) -> str:
    """Render this partner's kundli. Lagna chart when the birth time is known,
    otherwise a Moon chart (stable, honest, and consistent with Moon-based matching)."""
    ch = pr.get("chart")
    if not ch or not ch.get("planets"):
        return ""
    tk = ch.get("time_known")
    house1 = ch["lagna"] if tk else ch.get("moon_sign", ch["lagna"])
    svg = north_chart_svg({"chart": {"lagna": house1, "planets": ch["planets"]}})
    cap = ("Lagna (ascendant) chart — cast from the exact birth time"
           if tk else "Moon chart — from date &amp; place (birth time not given, so the ascendant isn't fixed)")
    return f"<div class='kchartwrap'>{svg}<p class='kcap'>{cap}</p></div>"


def _profiles_html(p: dict) -> str:
    def card(who):
        pr = p["profiles"][who]
        el = pr["element"]
        return (f"<div class='prof'>"
                f"<div class='prtop'><span class='prel'>{ELEMENT_EMOJI.get(el,'✨')}</span>"
                f"<span class='prname'><b>{escape(pr['name'])}</b>"
                f"<span class='prsign'>{pr['sign']} Moon · {pr['nak']} nakshatra</span></span></div>"
                f"<p class='prline'><b>Their nature:</b> {pr['persona']}.</p>"
                f"<p class='prline'><b>In love:</b> {pr['love']}.</p>"
                f"<p class='prline'><b>Feels most loved by:</b> {LOVE_LANG.get(el,'')}.</p>"
                f"{_milan_chart_block(pr)}</div>")
    has_chart = bool(p["profiles"].get("p1", {}).get("chart"))
    legend = ("<p class='klegend'>Chart key: <b>Su</b> Sun · <b>Mo</b> Moon · <b>Ma</b> Mars · "
              "<b>Me</b> Mercury · <b>Ju</b> Jupiter · <b>Ve</b> Venus · <b>Sa</b> Saturn · "
              "<b>Ra</b> Rahu · <b>Ke</b> Ketu · ↺ retrograde. The small numbers are the zodiac "
              "signs (1 Aries … 12 Pisces). This is the North-Indian style your family astrologer uses — "
              "so you can verify every placement yourself.</p>") if has_chart else ""
    return ("<h2>The two of you, decoded 🔮</h2>"
            "<p class='lead'>A quick read on each of you — plus your actual birth chart, "
            "drawn from your Moon sign and birth-star (nakshatra).</p>"
            f"<div class='profwrap'>{card('p1')}{card('p2')}</div>{legend}")


def _strength_deepdive_html(p: dict) -> str:
    strong = [t for t in _theme_scores(p["kootas"]) if t["pct"] >= 60]
    if not strong:
        return ""
    items = "".join(
        f"<div class='deep'><div class='dtop'><span class='demoji'>{t['theme']['emoji']}</span>"
        f"<b>{t['theme']['name']}</b></div><p>{THEME_DEEP.get(t['theme']['name'],'')}</p></div>"
        for t in strong)
    return ("<h2>Why you two work 💚</h2>"
            "<p class='lead'>The areas where you're genuinely strong — and what they'll feel like in real life.</p>"
            + items)


def _certificate_html(p: dict) -> str:
    arche = _archetype(p["profiles"]); pct = _match_pct(p)
    p1 = escape(p["profiles"]["p1"]["name"]); p2 = escape(p["profiles"]["p2"]["name"])
    return ("<h2>Your keepsake ✦</h2>"
            "<div class='cert'><div class='certin'>"
            "<div class='certseal'>✦</div>"
            "<div class='certk'>Certificate of Compatibility</div>"
            f"<div class='certnames'>{p1} <span>&amp;</span> {p2}</div>"
            f"<div class='certarch'>are officially<br><b>{arche['emoji']} {arche['name']}</b></div>"
            f"<div class='certpct'>{pct}% match on what matters</div>"
            f"<div class='certfoot'>Computed {p['meta']['generated']} · Classical Ashtakoota system<br>"
            "✦ AXTROSHASTRA · Computational Vedic Astrology</div>"
            "</div></div>")


def _method_html(p: dict, m: dict) -> str:
    def row(pr):
        return (f"<tr><td>{escape(pr['name'])}</td><td>{pr['sign']}</td>"
                f"<td>{pr['nak']} · pada {pr['pada']}</td><td>{pr['element'].title()}</td></tr>")
    table = ("<table class='meth'><thead><tr><th>Person</th><th>Moon sign</th><th>Birth-star</th>"
             f"<th>Element</th></tr></thead><tbody>{row(p['profiles']['p1'])}{row(p['profiles']['p2'])}</tbody></table>")
    gloss = "".join(
        f"<li><b>{KOOTA_UI[k]['label']}</b> <span class='gsan'>({k} · out of {mx})</span> — {KOOTA_UI[k]['blurb']}.</li>"
        for k, mx in [("Yoni", 4), ("Gana", 6), ("Graha Maitri", 5), ("Bhakoot", 7),
                      ("Nadi", 8), ("Vashya", 2), ("Tara", 3), ("Varna", 1)])
    return ("<h2>How we calculated this 🔬</h2><div class='methbox'>"
            "<p>Your match is computed with the classical <b>Ashtakoota</b> (eight-fold) system of Vedic "
            "astrology — the same method a family astrologer uses — but from precise, <b>NASA-grade planetary "
            "positions</b> and the standard <b>Lahiri ayanamsa</b>. Same inputs, same score, every time — "
            "consistent and verifiable, not mood-of-the-day.</p>"
            f"<p>Here's exactly what we read from your birth details:</p>{table}"
            f"<p class='methsub'>{m['time_note']}</p></div>"
            "<h3 class='glossh'>The 8 factors, in plain English</h3><ul class='gloss'>" + gloss + "</ul>")


def _tldr_html(p: dict) -> str:
    """Scannable, low-text summary shown directly under the hero. Answers the three
    questions a reader actually has — what's good, what to watch, what to do — before
    any long-form detail. Built entirely from existing payload fields, so it renders
    for older stored reports too (render-time only, no payload-shape dependency)."""
    ts = _theme_scores(p["kootas"])
    strong = [t for t in ts if t["pct"] >= 60]
    weak = [t for t in ts if t["pct"] < 45]

    # --- what's working ---
    if strong:
        good_chips = "".join(f"<span class='sx-chip good'>{t['theme']['emoji']} {t['theme']['name']}</span>" for t in strong)
        good_note = f"{len(strong)} of 5 big areas — naturally strong."
    else:
        good_chips = "<span class='sx-chip good'>💚 A workable, balanced match</span>"
        good_note = "Steady across the board — no runaway strengths, no big gaps."

    # --- what to watch ---
    cancelled = {c.get("koota") for c in (p.get("cancellations") or [])}
    weak_cancelled = any(k["name"] in cancelled for k in p["kootas"]
                         if k["max"] and k["score"] / k["max"] < 0.5)
    if weak:
        watch_chips = "".join(f"<span class='sx-chip warn'>{t['theme']['emoji']} {t['theme']['name']}</span>" for t in weak)
        watch_note = ("A classical flaw shows up here — <b>and it's cancelled for you</b>. "
                      "Fixable with habits, not luck." if weak_cancelled
                      else "Not a dealbreaker — just the area to be a little intentional about.")
    else:
        watch_chips = "<span class='sx-chip ok'>✅ Nothing major</span>"
        watch_note = "No weak link here worth losing sleep over."

    # --- your moves (pulled up from the weak factors' fixes; capped at 3) ---
    weak_k = sorted([k for k in p["kootas"] if k["max"] and k["score"] / k["max"] < 0.5],
                    key=lambda k: k["score"] / k["max"])
    moves = []
    for k in weak_k:
        rem = REMEDIES.get(k["name"])
        if not rem or not rem.get("work_on"):
            continue
        ui = KOOTA_UI.get(k["name"], {"emoji": "•", "label": k["name"]})
        moves.append((ui["emoji"], ui["label"], rem["work_on"]))
        if len(moves) == 3:
            break
    if moves:
        items = "".join(
            f"<li><span class='sx-n'>{i}</span><div><span class='sx-tag'>{em} {lab}</span>{txt}</div></li>"
            for i, (em, lab, txt) in enumerate(moves, 1))
        plan_h = "Your move" if len(moves) == 1 else f"Your {len(moves)} moves"
        plan_card = (f"<div class='sx-card plan'><div class='sx-h'>🎯 {plan_h}</div>"
                     f"<ul class='sx-moves'>{items}</ul></div>")
    else:
        plan_card = ("<div class='sx-card plan'><div class='sx-h'>🎯 Your move</div>"
                     "<p class='sx-note'>Nothing to fix here — just don't take a good thing for granted. "
                     "Keep making time for each other.</p></div>")

    return (
        "<div class='sx-wrap'>"
        f"<div class='sx-card good'><div class='sx-h'>💚 What's working</div>"
        f"<div class='sx-chips'>{good_chips}</div><p class='sx-note'>{good_note}</p></div>"
        f"<div class='sx-card watch'><div class='sx-h'>🚧 Watch-out{'' if len(weak) == 1 else 's'}</div>"
        f"<div class='sx-chips'>{watch_chips}</div><p class='sx-note'>{watch_note}</p></div>"
        f"{plan_card}"
        "</div>"
        "<p class='sx-cue'>That's the gist — the full breakdown is below ↓</p>")


def render_milan(p: dict) -> str:
    m = p["meta"]
    m = {**m, "p1": escape(m["p1"]), "p2": escape(m["p2"])}  # user-supplied names: escape
    theme_html = _theme_rows(p["kootas"])
    cancelled = {c.get("koota") for c in (p.get("cancellations") or [])}
    rows = ""
    for k in sorted(p["kootas"], key=lambda k: (k["score"] / k["max"]) if k["max"] else 0, reverse=True):
        pct = k["score"] / k["max"] * 100
        bar_color = "#2E7D53" if pct >= 75 else ("#E4B04A" if pct >= 40 else "#C93B2E")
        if k["name"] in cancelled and pct < 40:
            bar_color = "#E4B04A"  # softened — this dosha is cancelled for this couple
        ui = KOOTA_UI.get(k["name"], {"emoji": "•", "label": k["name"], "blurb": k.get("meaning", "")})
        score_disp = int(k["score"]) if float(k["score"]).is_integer() else k["score"]
        fix = _koota_fix_html(k, cancelled, (m['p1'], m['p2']))
        rows += f"""<div class='koota'>
<div class='ktop'><div class='klabel'><span class='kemoji'>{ui['emoji']}</span><span class='kname'><b>{ui['label']}</b><span class='ksan'>{k['name']} koota</span></span></div><span class='ks'>{score_disp}/{k['max']}</span></div>
<div class='kbar'><div style='width:{pct:.0f}%;background:{bar_color}'></div></div>
<p class='kd'>{ui['blurb']}</p>
<p class='kt'>{k.get('text','')}</p>{fix}</div>"""

    # ---------- cancellations & effective score ----------
    canc_html = ""
    if p.get("cancellations"):
        cards = "".join(
            f"<div class='canc'>✅ <b>{c['koota']} dosha cancelled</b> (+{c['restored']} restored)"
            f"<p>{c['rule']}</p></div>" for c in p["cancellations"])
        canc_html = (f"<h2>Dosha cancellation check</h2>{cards}"
                     f"<div class='effbox'>Effective score after cancellations: "
                     f"<b>{p['effective']}/36</b> — {p['effective_verdict']}</div>")
    elif any(k['name'] in ('Nadi','Bhakoot') and k['score']==0 for k in p['kootas']):
        canc_html = ("<h2>Dosha cancellation check</h2>"
                     "<div class='canc' style='border-color:#E4B04A'>For your two charts, the usual "
                     "rules that cancel this dosha don't apply — so it stays active. This isn't a verdict. "
                     "It simply marks this as an area to be intentional about; the practical steps are on "
                     "that factor's own card in the breakdown above. Decide with understanding, not fear.</div>")

    # ---------- strengths ----------
    sw_html = ""
    if p.get("strengths"):
        st = "".join(f"<li><b>{KOOTA_UI.get(s, {'label': s})['label']}</b> — {next(k['text'] for k in p['kootas'] if k['name']==s)}</li>"
                     for s in p.get("strengths", []))
        if st:
            sw_html = f"<h2>Where you're naturally strong 💚</h2><ul class='swl'>{st}</ul>"

    # ---------- element dynamic + nakshatra lines ----------
    el_html = ""
    if p.get("element"):
        el = p["element"]
        # LLM prose if present (already html-escaped in narrative.py), else the bank text.
        el_text = narr(p, "combined_energy") or el["text"]
        el_html = (f"<h2>Your combined energy</h2>"
                   f"<div class='elbox'><b>{m['p1']}: {el['p1']} · {m['p2']}: {el['p2']}</b>"
                   f"<p>{el_text}</p></div>")

    # ---------- Manglik: keep the concern and its reassurance together ----------
    mg = p["manglik"]
    if mg.get("p1") or mg.get("p2"):
        mg_extra = ("<p class='mgfix'><b>What to do:</b> this is not a curse, and in matching it is very "
                    "often mild or fully cancelled. Read the cancellation note above, and if it matters to "
                    "your families, the classical remedy is a simple Mangal / Hanuman practice on Tuesdays. "
                    "Treat it as information to understand, not a verdict to fear.</p>")
    else:
        mg_extra = ("<p class='mgfix'><b>All clear:</b> neither chart carries a Manglik placement on this "
                    "check — one less thing to worry about.</p>")
    manglik_html = f"<h2>Manglik check</h2><div class=\"mg\">{mg['note']}{mg_extra}</div>"

    # ---------- low score guidance ----------
    low_html = ""
    if p.get("effective", p["total"]) < 24:
        low_html = ("<h2>What a lower score really means</h2>"
            "<div class='lowbox'>"
            "<p><b>First:</b> guna milan is one classical input, not the whole verdict. It measures how "
            "compatible your Moon positions are — not values, maturity or commitment, which are the real "
            "pillars of any marriage.</p>"
            "<p><b>Second:</b> look at which factors scored low. A shortfall in the softer factors — "
            "temperament, mental wavelength — is improvable; those are communication patterns couples "
            "learn. A Nadi or Bhakoot dosha, if it isn't cancelled, carries more traditional weight — "
            "there, take counsel from your elders and your own judgement together.</p>"
            "<p><b>Third:</b> countless happy marriages began with a low score. Use the number as "
            "information — to see what you'll want to work on — not as a verdict.</p></div>")

    # ---------- Phase-1 expanded sections (present only on newer reports) ----------
    has_profiles = bool(p.get("profiles"))
    opening_html = _opening_note(p) if has_profiles else ""
    couple_html = ("<h2>Your couple type ✨</h2>" + _sharecard_html(p)) if has_profiles else ""
    deepdive_html = _strength_deepdive_html(p) if has_profiles else sw_html
    profiles_html = _profiles_html(p) if has_profiles else ""
    method_html = _method_html(p, m) if has_profiles else ""
    if method_html:
        method_body = method_html.replace("<h2>How we calculated this 🔬</h2>", "", 1)
        method_acc = ("<details class=\"acc\"><summary><span class=\"acc-t\">🔬 How we calculated this</span>"
                      "<span class=\"acc-x\">the method <span class=\"caret\">▾</span></span></summary>"
                      f"<div class=\"acc-body\">{method_body}</div></details>")
    else:
        method_acc = ""
    cert_html = _certificate_html(p) if has_profiles else ""
    matchpct_html = (f"<p class='matchpct'>{_match_pct(p)}% match on what matters</p>"
                     if has_profiles else "")
    # personalised share text for axShare (couple-card image download removed)
    share_js = ""
    if has_profiles:
        share_js = "<script>window.AX_SHARE_TEXT=" + json.dumps(_share_text(p)) + ";</script>"

    # bottom-sticky actions: print-to-PDF + WhatsApp share (report link via axShare)
    sticky_bar = (
        "<style>@media screen{body{padding-bottom:80px}}"
        "#ax-stickybar{position:fixed;left:0;right:0;bottom:0;z-index:9997;"
        "background:rgba(16,20,40,.96);border-top:1px solid rgba(228,176,74,.35);"
        "box-shadow:0 -6px 20px rgba(0,0,0,.28);"
        "padding:10px 12px calc(10px + env(safe-area-inset-bottom))}"
        "#ax-stickybar .inner{max-width:640px;margin:0 auto;display:flex;gap:10px}"
        "#ax-stickybar a{flex:1;text-align:center;text-decoration:none;border-radius:12px;"
        "padding:13px 10px;font:800 15px/1 'Bricolage Grotesque',system-ui,sans-serif}"
        "#ax-stickybar .pdf{background:#C93B2E;color:#fff}"
        "#ax-stickybar .wa{background:#25D366;color:#0b2f18}"
        "@media print{#ax-stickybar{display:none!important}}</style>"
        "<div id='ax-stickybar'><div class='inner'>"
        "<a class='pdf' href='#' onclick='window.print();return false;'>&#11015; Download PDF</a>"
        "<a class='wa' href='#' onclick='axShare();return false;'>Share on WhatsApp</a>"
        "</div></div>")

    notes = "".join(f"<div class='note'>{n}</div>" for n in p["notes"])
    tldr_html = _tldr_html(p)
    vcol = VERDICT_COLOR[p["verdict_key"]]
    return f"""<!DOCTYPE html><html lang="hi-IN"><head>{AX_PRE}<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{m['p1']} ✕ {m['p2']} — Kundli Milan | Axtroshastra</title>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&display=swap" rel="stylesheet">
<style>
:root{{--ink:#23253B;--midnight:#151C39;--paper:#FAF6ED;--sindoor:#C93B2E;
--haldi:#E4B04A;--muted:#6B6D82;--line:#E7E0D2;--display:'Bricolage Grotesque',sans-serif}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,'Segoe UI',sans-serif;background:var(--paper);color:var(--ink);
line-height:1.6;font-size:15.5px;max-width:640px;margin:0 auto;padding:0 20px 60px}}
.hero{{background:var(--midnight);color:#F3EFE4;margin:0 -20px;padding:36px 22px;text-align:center}}
.hero .brand{{font-family:var(--display);font-weight:800;color:var(--haldi);font-size:13px;letter-spacing:.08em}}
.hero h1{{font-family:var(--display);font-size:26px;margin-top:14px;color:#fff}}
.score{{font-family:var(--display);font-weight:800;font-size:56px;color:var(--haldi);margin:14px 0 2px}}
.score small{{font-size:22px;color:#8F92AB}}
.verdict{{display:inline-block;background:{vcol};color:#fff;font-family:var(--display);
font-weight:800;font-size:13px;border-radius:20px;padding:7px 18px;margin-top:10px}}
h2{{font-family:var(--display);font-size:21px;margin:34px 0 14px}}
.koota{{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:10px}}
.ktop{{display:flex;justify-content:space-between;align-items:center;gap:10px;font-family:var(--display)}}
.ks{{font-weight:800;flex:none;font-size:17px}}
.lead{{color:var(--muted);font-size:15px;margin:-8px 0 14px}}
.theme{{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:10px}}
.ttop{{display:flex;align-items:center;gap:9px;font-family:var(--display)}}
.temoji{{font-size:20px;line-height:1;flex:none}}
.ttop b{{font-size:16px;flex:1;min-width:0}}
.tchip{{color:#fff;font-family:var(--display);font-weight:800;font-size:11px;border-radius:20px;padding:4px 10px;white-space:nowrap;flex:none}}
.tblurb{{font-size:14px;color:#3A3C55;margin-top:9px}}
.klabel{{display:flex;align-items:center;gap:10px;min-width:0}}
.kemoji{{font-size:20px;line-height:1;flex:none}}
.kname{{display:flex;flex-direction:column;line-height:1.2;min-width:0}}
.kname b{{font-size:16px}}
.ksan{{font-size:10.5px;color:var(--muted);font-weight:700;text-transform:uppercase;margin-top:2px}}
.work{{background:#fff;border:1.5px solid var(--line);border-left:4px solid var(--sindoor);border-radius:12px;padding:14px 16px;margin-bottom:10px;font-size:15px}}
.work.good{{border-left-color:#2E7D53}}
.work.good b{{font-family:var(--display);font-size:15.5px}}.work.good p{{margin-top:7px}}
.wtop{{display:flex;align-items:center;gap:9px;font-family:var(--display)}}
.wemoji{{font-size:19px;line-height:1;flex:none}}
.wtop b{{font-size:15.5px;flex:1;min-width:0}}
.wtag{{font-family:var(--display);font-weight:800;font-size:10.5px;text-transform:uppercase;color:var(--sindoor);background:#FBE7E3;border-radius:20px;padding:3px 9px;flex:none}}
.wcanc{{display:inline-block;font-size:13.5px;color:#2E7D53;font-weight:600;margin-top:6px}}
.wdo{{margin-top:9px}}
.wrem{{margin-top:7px;color:var(--muted);font-size:14px}}
.wdo b,.wrem b{{font-family:var(--display)}}
.kbar{{height:7px;background:#EFE8D8;border-radius:4px;margin:8px 0;overflow:hidden}}
.kbar div{{height:100%;border-radius:4px}}
.kd{{font-size:14px;color:var(--muted)}}
.mg,.note{{background:#F6E7C6;border-radius:12px;padding:15px;font-size:15px;margin:10px 0}}
.note{{background:#fff;border:1.5px solid var(--haldi)}}
.tn{{font-size:13.5px;color:var(--muted);margin-top:24px}}
.kt{{font-size:15px;margin-top:8px;color:#33355000;color:#3A3C55}}
.kfix{{margin-top:12px;padding-top:12px;border-top:1px dashed var(--line)}}
.kfix .wdo{{margin-top:0}}
.mgfix{{margin-top:10px;font-size:14px}}
.mgfix b{{font-family:var(--display)}}
.canc{{background:#fff;border:2px solid #2E7D53;border-radius:12px;padding:14px 16px;margin-bottom:10px;font-size:15px}}
.canc p{{margin-top:5px}}
.effbox{{background:var(--midnight);color:#F3EFE4;border-radius:12px;padding:16px;font-size:15px;text-align:center}}
.effbox b{{color:var(--haldi);font-family:var(--display);font-size:20px}}
.swh{{font-family:var(--display);font-weight:800;font-size:14px;margin:14px 0 6px}}
.swl{{margin-left:20px}}.swl li{{font-size:15px;margin-bottom:8px}}
.elbox,.nlbox,.lowbox{{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:15px 16px;margin-bottom:10px;font-size:15px}}
.elbox b{{font-family:var(--display)}}.elbox p{{margin-top:6px}}
.lowbox p{{margin-bottom:10px}}
/* ---- Phase-1 expanded sections ---- */
.matchpct{{display:inline-block;margin-top:12px;font-family:var(--display);font-weight:800;font-size:15px;color:#151C39;background:var(--haldi);border-radius:20px;padding:7px 16px}}
.opennote{{background:#fff;border:1.5px solid var(--line);border-radius:14px;padding:18px;margin-top:22px;font-size:15px}}
.opennote p{{margin-bottom:9px}}.opennote p:last-child{{margin-bottom:0}}
.onsub{{color:var(--muted);font-size:14px;font-style:italic}}
.sharecard{{background:radial-gradient(1200px 500px at 50% -30%, #23305C, var(--midnight) 70%);color:#F3EFE4;border-radius:18px;padding:26px 22px 24px;text-align:center;box-shadow:0 14px 40px rgba(21,28,57,.28)}}
.scbrand{{font-family:var(--display);font-weight:800;color:var(--haldi);font-size:11px;letter-spacing:.14em}}
.scnames{{font-family:var(--display);font-weight:800;font-size:24px;color:#fff;margin-top:12px}}
.scnames span{{color:var(--haldi);margin:0 6px}}
.scarch{{font-family:var(--display);font-weight:700;font-size:15px;color:#E9E4D5;margin-top:6px}}
.scpct{{font-family:var(--display);font-weight:800;font-size:52px;color:var(--haldi);margin:14px 0 0;line-height:1}}
.scpct small{{display:block;font-size:12px;color:#B9BBD0;font-weight:700;margin-top:6px}}
.scchips{{display:flex;flex-wrap:wrap;gap:7px;justify-content:center;margin-top:16px}}
.scchip{{background:rgba(228,176,74,.16);border:1px solid rgba(228,176,74,.5);color:#F1E4C4;font-size:11.5px;font-weight:700;border-radius:20px;padding:5px 11px}}
.sctag{{color:#D9D4C3;font-style:italic;font-size:14px;margin-top:16px}}
.sctag2{{font-size:15px;color:#3A3C55;margin:12px 2px 0}}
.sharebtn{{display:block;width:100%;border:0;border-radius:12px;background:var(--sindoor);color:#fff;font-family:var(--display);font-weight:800;font-size:16px;padding:14px;margin-top:14px;cursor:pointer}}
.sharebtns{{display:flex;gap:10px}}.sharebtns .sharebtn{{flex:1}}
.sharebtn.ghost{{background:transparent;color:var(--sindoor);border:2px solid var(--sindoor);padding:12px}}
.cert{{background:linear-gradient(#FFFDF7,#F7EFDD);border:2px solid var(--haldi);border-radius:16px;padding:8px;box-shadow:0 12px 34px rgba(35,37,59,.12)}}
.certin{{border:1.5px dashed #CDA43E;border-radius:12px;padding:24px 18px;text-align:center}}
.certseal{{font-size:30px;color:var(--haldi);line-height:1}}
.certk{{font-family:var(--display);font-weight:700;font-size:12px;text-transform:uppercase;color:var(--muted);margin-top:8px}}
.certnames{{font-family:var(--display);font-weight:800;font-size:24px;color:var(--ink);margin-top:12px}}
.certnames span{{color:var(--haldi);margin:0 5px;font-weight:700}}
.certarch{{font-size:15px;color:#4A4C63;margin-top:10px;line-height:1.5}}
.certarch b{{font-family:var(--display);font-size:18px;color:var(--ink)}}
.certpct{{display:inline-block;font-family:var(--display);font-weight:800;font-size:14px;color:#151C39;background:var(--haldi);border-radius:20px;padding:6px 15px;margin-top:14px}}
.certfoot{{font-size:11px;color:var(--muted);margin-top:16px;line-height:1.5}}
.profwrap{{display:flex;flex-direction:column;gap:10px}}
.prof{{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:15px 16px}}
.prtop{{display:flex;align-items:center;gap:11px;margin-bottom:6px}}
.prel{{font-size:26px;line-height:1;flex:none}}
.prname{{display:flex;flex-direction:column;line-height:1.25}}
.prname b{{font-family:var(--display);font-size:17px}}
.prsign{{font-size:11px;color:var(--muted);font-weight:700;text-transform:uppercase;margin-top:3px;line-height:1.5}}
.prline{{font-size:15px;margin-top:6px}}.prline b{{font-family:var(--display)}}
@media(min-width:560px){{.profwrap{{flex-direction:row}}.prof{{flex:1}}}}
.kchartwrap{{background:var(--midnight);border-radius:12px;padding:12px 12px 8px;margin-top:12px}}
.kchart{{width:100%;max-width:290px;height:auto;display:block;margin:0 auto}}
.kcap{{color:#B9BBD0;font-size:11.5px;text-align:center;margin-top:8px;line-height:1.4}}
.klegend{{font-size:11.5px;color:var(--muted);line-height:1.6;margin:12px 2px 0;background:#fbf7ef;border:1px solid var(--line);border-radius:10px;padding:11px 13px}}
.klegend b{{color:var(--ink)}}
.deep{{background:#F3F8F3;border:1.5px solid #CDE4D3;border-radius:12px;padding:14px 16px;margin-bottom:10px}}
.dtop{{display:flex;align-items:center;gap:9px;font-family:var(--display);margin-bottom:6px}}
.dtop b{{font-size:16px}}.demoji{{font-size:19px;flex:none}}
.deep p{{font-size:15px}}
.wplan{{background:#FBF4E6;border-radius:10px;padding:11px 12px;margin-top:10px;font-size:14px}}
.wplan p{{margin:5px 0}}
.wpk{{display:inline-block;font-family:var(--display);font-weight:800;font-size:10px;text-transform:uppercase;color:#8a6a1f;background:#F6E7C6;border-radius:6px;padding:2px 7px;margin-right:6px}}
.wsplit{{background:#FBF4E6;border-radius:10px;padding:9px 12px;margin-top:9px;font-size:14px}}
.wsplit p{{margin:5px 0}}
.wtalk{{margin-top:8px;font-size:14px}}
.methbox{{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:15px 16px;font-size:15px}}
.methbox p{{margin-bottom:9px}}
.meth{{width:100%;border-collapse:collapse;margin:6px 0;font-size:14px}}
.meth th,.meth td{{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line)}}
.meth th{{font-family:var(--display);font-size:11px;text-transform:uppercase;color:var(--muted)}}
.methsub{{font-size:13.5px;color:var(--muted);margin-top:4px}}
.glossh{{font-family:var(--display);font-size:17px;margin:22px 0 10px}}
.gloss{{list-style:none}}
.gloss li{{background:#fff;border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin-bottom:7px;font-size:14px}}
.gloss b{{font-family:var(--display)}}
.gsan{{color:var(--muted);font-size:11.5px;font-weight:600}}
/* ---- scannable TL;DR summary (directly under hero) ---- */
.sx-wrap{{display:grid;gap:10px;margin-top:16px}}
@media(min-width:560px){{.sx-wrap{{grid-template-columns:1fr 1fr}}}}
.sx-card{{background:#fff;border:1.5px solid var(--line);border-radius:14px;padding:15px 16px}}
.sx-card.good{{border-top:4px solid #2E7D53}}
.sx-card.watch{{border-top:4px solid var(--sindoor)}}
.sx-card.plan{{border:1.5px solid var(--haldi);background:#FBF4E6}}
@media(min-width:560px){{.sx-card.plan{{grid-column:1/-1}}}}
.sx-h{{font-family:var(--display);font-weight:800;font-size:13px;text-transform:uppercase}}
.sx-card.good .sx-h{{color:#2E7D53}}.sx-card.watch .sx-h{{color:var(--sindoor)}}.sx-card.plan .sx-h{{color:#8A6410}}
.sx-chips{{display:flex;flex-wrap:wrap;gap:7px;margin-top:11px}}
.sx-chip{{display:inline-flex;align-items:center;gap:5px;font-family:var(--display);font-weight:700;font-size:13px;padding:6px 11px;border-radius:20px}}
.sx-chip.good,.sx-chip.ok{{background:#E3F0E8;color:#1E5A3C}}
.sx-chip.warn{{background:#FBE9E6;color:var(--sindoor-dark,#A82F24)}}
.sx-note{{margin-top:10px;font-size:13.5px;color:var(--muted)}}
.sx-note b{{color:var(--ink)}}
.sx-moves{{list-style:none;margin:11px 0 0;display:grid;gap:8px}}
.sx-moves li{{display:flex;gap:10px;align-items:flex-start;background:#fff;border-radius:10px;padding:10px 12px;font-size:14px}}
.sx-n{{font-family:var(--display);font-weight:800;color:var(--sindoor);flex:none;line-height:1.5}}
.sx-tag{{display:inline-block;font-family:var(--display);font-weight:800;font-size:10.5px;text-transform:uppercase;color:#8a6a1f;background:#F6E7C6;border-radius:6px;padding:2px 7px;margin-right:7px;white-space:nowrap}}
.sx-cue{{text-align:center;color:var(--muted);font-size:13.5px;margin-top:14px}}
/* ---- tap-to-open detail sections ---- */
details.acc{{background:#fff;border:1.5px solid var(--line);border-radius:12px;margin-bottom:10px;overflow:hidden}}
details.acc>summary{{list-style:none;cursor:pointer;display:flex;align-items:center;gap:10px;padding:15px 16px;font-family:var(--display);font-weight:800;font-size:18px}}
details.acc>summary::-webkit-details-marker{{display:none}}
.acc-t{{flex:1;min-width:0}}
.acc-x{{font-family:var(--display);font-weight:700;font-size:12px;color:var(--muted);white-space:nowrap}}
.acc-body{{padding:2px 16px 16px;border-top:1px dashed var(--line)}}
.acc-body>.lead{{margin-top:12px}}
details.acc[open]>summary .acc-x .caret{{transform:rotate(180deg)}}
.caret{{display:inline-block;transition:transform .15s;color:var(--haldi)}}
@media print{{#axlang{{display:none!important}}details.acc>*{{display:block!important}}details.acc>summary .acc-x{{display:none}}body{{max-width:100%;padding:0 10px 16px;background:#fff}}.hero{{margin:0 -10px}}
.koota,.theme,.work,.canc,.note,.mg,.effbox,.elbox,.nlbox,.lowbox,.review,.swl li,.opennote,.sharecard,.prof,.deep,.methbox,.gloss li,.wplan,.cert,.sharebtns,.sharebtn,.matchpct,.profwrap,.kchartwrap{{break-inside:avoid}}
h2,h3{{break-after:avoid}}p{{orphans:2;widows:2}}*{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}}}
</style></head><body>
<div class="hero"><p class="brand">✦ AXTROSHASTRA · KUNDLI MILAN</p>
<h1>{m['p1']} ✕ {m['p2']}</h1>
<p class="score">{p['total']}<small>/36</small></p>
<span class="verdict">{p['verdict'].upper()}</span>
{matchpct_html}
{("<p style='margin-top:10px;font-size:15px;color:#B9BBD0'>After dosha cancellation: <b style='color:#E4B04A'>" + str(p['effective']) + "/36</b></p>") if p.get('cancellations') else ""}</div>
{tldr_html}
{opening_html}
{couple_html}
{profiles_html}
<h2>Your match, in plain English 💫</h2>
<p class="lead">The five things that actually make or break a relationship — scored straight from your two charts.</p>
{theme_html}
{deepdive_html}
<details class="acc"><summary><span class="acc-t">📊 The full breakdown — all 8 factors</span><span class="acc-x">{p['total']}/36 <span class="caret">▾</span></span></summary>
<div class="acc-body"><p class="lead">This is the classical 8-part Ashtakoota system, decoded. Every score here feeds the five themes above.</p>{rows}</div></details>
{canc_html}
{el_html}
{manglik_html}
{method_acc}
{cert_html}
{('<h2>Important notes</h2>' + notes) if notes else ''}
{low_html}
<p class="tn">System: {m['system']} · {m['time_note']} · Generated {m['generated']}<br>
This compatibility score is one classical input to a marriage decision, not the whole decision.
<a href='https://wa.me/919599827297' style='color:inherit'>WhatsApp +91 95998 27297</a> · <a href="/privacy" style="color:inherit">Privacy</a> · <a href="/terms" style="color:inherit">Terms</a> · <a href="/refunds" style="color:inherit">Refund Policy</a></p>
{share_js}
<script>window.addEventListener('beforeprint',function(){{document.querySelectorAll('details.acc').forEach(function(d){{d.__wo=d.open;d.open=true;}});}});window.addEventListener('afterprint',function(){{document.querySelectorAll('details.acc').forEach(function(d){{if(d.__wo===false)d.open=false;}});}});</script>
{sticky_bar}
{MILAN_I18N}
</body></html>"""


# ============================================================ BLUEPRINT RENDERER
def render_blueprint(p: dict) -> str:
    """/jeevan — Life Blueprint report. Returns a complete <!DOCTYPE html> doc,
    reusing Vyapar's v17 page/card system (_VYAPAR_CSS, _VYAPAR_DEFS, icon set)
    verbatim -- one card per page, points not paragraphs, no new visual style.
    English-first; Hindi is a scoped fast-follow (see blueprint_report_spec.md)."""
    m = p["meta"]
    name = escape(m.get("name", ""))  # user-supplied: escape (stored-XSS guard)
    teaser = p["teaser"]
    ch = p["chart"]
    lagna_sa = ch["lagna"]
    lagna_en = VY_SIGN_EN.get(lagna_sa, lagna_sa)
    planets = ch["planets"]
    moon_sa = planets.get("Moon", {}).get("sign", "")
    moon_en = VY_SIGN_EN.get(moon_sa, moon_sa)
    persona = p["persona"]
    career = p["career"]
    wealth = p["wealth"]
    wheel = p["wheel"]
    roadmap = p["roadmap"]
    sade = p.get("sade_sati", {})
    nakp = p["nak_profile"]
    elements = p["elements"]

    cur_md = roadmap[0] if roadmap else None
    cur_lord = cur_md["lord"] if cur_md else "—"
    compact_dasha = teaser["current_dasha"].replace(" Mahadasha", "").replace(" Antardasha", " AD")

    LABEL = {"career": "Career", "money": "Money", "marriage": "Marriage",
             "children": "Children", "home": "Home", "foreign": "Foreign",
             "health": "Health", "growth": "Growth", "family": "Family",
             "timing": "Now"}
    TAG_CLASS = {"thriving": "good", "building": "", "watch": "warn"}
    TAG_LABEL = {"thriving": "Thriving", "building": "Building", "watch": "Watch"}

    by_sign = {}
    for pl, info in planets.items():
        by_sign.setdefault(info["sign"], []).append(pl)

    def house_of(sa):
        return ((SIGN_NUM[sa] - SIGN_NUM[lagna_sa]) % 12) + 1

    kundli_cells = ""
    for sa, col, row in VY_KUNDLI_LAYOUT:
        occ = by_sign.get(sa, [])
        pl_html = f'<div class="pl">{" · ".join(occ)}</div>' if occ else ""
        is_asc = (sa == lagna_sa)
        label = f'{VY_SIGN_EN.get(sa, sa)} · Asc' if is_asc else VY_SIGN_EN.get(sa, sa)
        kundli_cells += (f'<div class="kc{" asc" if is_asc else ""}" '
                         f'style="grid-column:{col};grid-row:{row}">'
                         f'<div class="sn">{label}</div>{pl_html}</div>')
    kundli_center = (f'<div class="kc center" style="grid-column:2/4;grid-row:2/4">'
                     f'<b>Life Blueprint</b><span>{lagna_en} rising</span></div>')

    planet_rows = ""
    for pl in VY_PLANET_ORDER:
        info = planets.get(pl)
        if not info: continue
        hn = house_of(info["sign"])
        role = VY_HOUSE_ROLE.get(hn, "")
        dign = f" · {info['dignity']}" if info.get("dignity") in ("exalted", "debilitated", "own") else ""
        planet_rows += (f'<tr><td>{pl}</td><td>{VY_SIGN_EN.get(info["sign"], info["sign"])}</td>'
                        f'<td>{_vy_ordinal(hn)}</td><td>{role}{dign}</td></tr>')

    # remedies: current Mahadasha lord + the lord behind the Watch-tagged area, if any
    def remedy_pt(lord):
        from jyotish_maps import REMEDY_7L, REMEDY_NODE
        r = REMEDY_7L.get(lord) or REMEDY_NODE.get(lord)
        if not r: return ""
        day, mantra, gem = r
        return (f'<div class="pt"><svg class="ic pi"><use href="#i-check"/></svg>'
                f'<div class="tx"><b>On {day}</b>Chant &ldquo;{mantra}&rdquo;. {gem}.</div></div>')
    remedy_pts = remedy_pt(cur_lord)
    watch_areas = [a for a in wheel if wheel[a] == "watch" and a != "timing"]

    roadmap_wins = ""
    for i, r in enumerate(roadmap):
        badge = ("mod", "In progress") if r["current"] else (("build", "Ahead") if i == 1 else ("hold", "Later"))
        roadmap_wins += (f'<div class="win"><div class="wt"><span class="wd">{r["lord"]} Mahadasha</span>'
                         f'<span class="wg {badge[0]}">{badge[1]}</span></div>'
                         f'<div class="wb">{r["from"]} &ndash; {r["to"]} &middot; {r["theme"]}</div></div>')

    sade_active = bool(sade.get("active"))

    strengths_pts = "".join(
        f'<div class="pt good"><svg class="ic pi"><use href="#i-check"/></svg>'
        f'<div class="tx">{escape(s)}</div></div>' for s in p.get("strengths", [])[:3])
    lessons_pts = "".join(
        f'<div class="pt warn"><svg class="ic pi"><use href="#i-alert"/></svg>'
        f'<div class="tx">{escape(s)}</div></div>' for s in p.get("lessons", [])[:2])

    # ---- bordered tag-cards for the 8 area pages (career..family) --
    # reuses wheel[]/strengths[]/lessons[] as already computed; adds no new
    # astrology, only new presentation. Reflection lines are static per-area
    # copy, not derived from the chart.
    wheel_svg = blueprint_wheel_svg(wheel, name, compact_dasha)
    AREA_ORDER = ["career", "money", "marriage", "children", "home", "foreign", "health", "family"]
    AREA_REFLECT = {
        "career": "Where in your work life are you still waiting for permission you don’t need?",
        "money": "Is your money pattern something you inherited, or something you actually chose?",
        "marriage": "What do you actually need from a partner — not what you think you should want?",
        "children": "Are you building a family on your own timeline, or someone else’s?",
        "home": "Does where you live right now feel like roots, or a rest stop?",
        "foreign": "If distance called you tomorrow, would you go — or is that hesitation, not truth?",
        "health": "What is your body already telling you that you’ve been talking over?",
        "family": "Which family tie are you keeping out of love, and which out of habit?",
    }
    strengths_list = p.get("strengths", []) or []
    lessons_list = p.get("lessons", []) or []

    def tcard(area, icon, body_html):
        tag = wheel[area]
        cls = TAG_CLASS[tag]
        idx = AREA_ORDER.index(area)
        if tag == "watch":
            favour = "Keep doing what already works here — steady effort still compounds."
            watching = (lessons_list[idx % len(lessons_list)] if lessons_list
                        else "This is the one area worth extra patience right now.")
        else:
            favour = (strengths_list[idx % len(strengths_list)] if strengths_list
                      else "Your chart backs you here — this is a place to build, not doubt.")
            watching = "Nothing flagged here — the usual care is enough."
        return (f'<div class="tcard {cls}">'
                f'<div class="verdict {cls or "gold"} sum"><svg class="ic"><use href="#{icon}"/></svg> {TAG_LABEL[tag]} right now.</div>'
                f'{body_html}'
                f'</div>'
                f'<div class="dwcard"><div class="dwrow do"><svg class="ic pi"><use href="#i-check"/></svg>'
                f'<div class="tx"><b>Favour</b>{escape(favour)}</div></div>'
                f'<div class="dwrow watch"><svg class="ic pi"><use href="#i-alert"/></svg>'
                f'<div class="tx"><b>Watching</b>{escape(watching)}</div></div></div>'
                f'<div class="reflect">&ldquo;{escape(AREA_REFLECT[area])}&rdquo;</div>')

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} &mdash; Life Blueprint | Axtroshastra</title>
<style>
{_VYAPAR_CSS}
</style></head><body>
{_VYAPAR_DEFS}

<!-- 01 COVER -->
<section class="page sand"><div class="col">
  <div class="cov-brand">Axtroshastra &middot; Life Blueprint</div>
  <svg class="constel" viewBox="0 0 230 80" fill="none" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="14,66 60,54 104,42 150,31 210,13" stroke="#5A3C14" stroke-width="1.1" stroke-dasharray="2 5" opacity=".55"/>
    <circle cx="14" cy="66" r="3" fill="#B9862E"/><circle cx="60" cy="54" r="3" fill="#B9862E"/><circle cx="104" cy="42" r="3" fill="#B9862E"/>
    <g transform="translate(150 31)" stroke="#B9862E" stroke-width="1.4"><path d="M0 -7V7M-7 0H7M-5 -5l10 10M5 -5l-10 10"/></g>
    <g transform="translate(210 13)"><path d="M0 -9V9M-9 0H9M-6 -6l12 12M6 -6l-12 12" stroke="#B9862E" stroke-width="1.6"/><circle r="3.6" fill="#E4D5BE" stroke="#B9862E" stroke-width="1.5"/></g>
  </svg>
  <div class="cov-name">{name}</div>
  <div class="cov-type"><svg class="ti" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M3 14l4-4 3 3 6-7"/><path d="M13 4h4v4"/></svg><span>{escape(persona["lagna_line"])}</span></div>
  <div class="cov-pills"><span class="cp"><span class="g">&#9790;</span> Moon in {moon_en}</span><span class="cp"><span class="g">&#9651;</span> {lagna_en} rising</span><span class="cp"><span class="g">&#9796;</span> {compact_dasha}</span></div>
  <div class="cov-comfort">One report, ten parts of your life, and one honest answer to where you actually stand.</div>
  <div class="cov-trust">Swiss Ephemeris &middot; Lahiri ayanamsa &middot; Generated {m.get("generated", "")}</div>
</div><div class="pno">01</div></section>

<!-- 02 NOTE FOR YOU -->
<section class="page note"><div class="col">
  <svg class="fan nftop" viewBox="0 0 54 30" fill="none"><rect x="6" y="13" width="42" height="20" fill="#FBF7EE"/><g stroke="currentColor" stroke-width="1" stroke-linecap="round"><path d="M27 27 L12 15M27 27 L18 12M27 27 L27 9M27 27 L36 12M27 27 L42 15"/><path d="M12 15 A19 19 0 0 1 42 15"/></g></svg>
  <div class="eyebrow">A note for you</div>
  <h2 class="head">Before you read on</h2>
  <div class="rule"></div>
  <div class="lead">Dear {name}, this report is a map, not a verdict. Ten parts of your life, each read from the same chart &mdash; where you stand right now, and what deserves your attention next.</div>
  <div class="lead">Nothing here is guessed. Every line traces back to a house, a planet, or a period in your own birth chart &mdash; and every part is honest about what it can and cannot tell you.</div>
  <div class="lead">&mdash; Your astrologer, Axtroshastra</div>
  <svg class="fan nfbot" viewBox="0 0 54 30" fill="none"><rect x="6" y="13" width="42" height="20" fill="#FBF7EE"/><g stroke="currentColor" stroke-width="1" stroke-linecap="round"><path d="M27 27 L12 15M27 27 L18 12M27 27 L27 9M27 27 L36 12M27 27 L42 15"/><path d="M12 15 A19 19 0 0 1 42 15"/></g></svg><svg class="crn ctl" viewBox="0 0 12 12"><path d="M6 .5 11.5 6 6 11.5 .5 6Z" fill="#B9862E"/></svg><svg class="crn ctr" viewBox="0 0 12 12"><path d="M6 .5 11.5 6 6 11.5 .5 6Z" fill="#B9862E"/></svg><svg class="crn cbl" viewBox="0 0 12 12"><path d="M6 .5 11.5 6 6 11.5 .5 6Z" fill="#B9862E"/></svg><svg class="crn cbr" viewBox="0 0 12 12"><path d="M6 .5 11.5 6 6 11.5 .5 6Z" fill="#B9862E"/></svg>
</div><div class="pno">02</div></section>

<!-- 03 LIFE WHEEL -->
<section class="page"><div class="col">
  <div class="eyebrow">At a glance</div>
  <h2 class="head">Your Life Wheel</h2>
  <div class="rule"></div>
  <div class="lead">All ten areas this report covers &mdash; each tag comes straight from your chart, not a guess.</div>
  {wheel_svg}
  <div class="sfoot">Thriving &middot; Building &middot; Watch &mdash; a three-way read on each area, from the same chart math behind every page in this report.</div>
</div><div class="pno">03</div></section>

<!-- 04 ABOUT YOU -->
<section class="page"><div class="col">
  <div class="eyebrow">About you</div>
  <h2 class="head">Who you are, from the chart</h2>
  <div class="rule"></div>
  <div class="verdict gold sum"><svg class="ic"><use href="#i-scales"/></svg> {escape(persona["lagna_line"])}</div>
  <div class="pts">
    <div class="pt"><svg class="ic pi"><use href="#i-scales"/></svg><div class="tx"><b>{lagna_en} rising &mdash; your outward self</b>{escape(persona["lagna_line"])}</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-moon"/></svg><div class="tx"><b>{moon_en} Moon &mdash; how you run inside</b>{escape(persona["moon_line"])}</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-book"/></svg><div class="tx"><b>{nakp["nakshatra"]} nakshatra</b>{escape(nakp["nature"])}</div></div>
  </div>
</div><div class="pno">04</div></section>

<!-- 05 CAREER -->
<section class="page"><div class="col">
  <div class="eyebrow">01 &middot; Career &amp; work direction</div>
  <h2 class="head">Where your chart points you</h2>
  <div class="rule"></div>
  {tcard("career", "i-compass",
    f'<div class="pts">'
    f'<div class="pt"><svg class="ic pi"><use href="#i-compass"/></svg><div class="tx"><b>Your natural direction</b>{career["direction"]}.</div></div>'
    f'<div class="pt"><svg class="ic pi"><use href="#i-clock"/></svg><div class="tx"><b>The moment for a bigger question</b>If switching or building feels urgent, {("your " + cur_lord + " period") if cur_md else "your current period"} is the one shaping that pull.</div></div>'
    f'</div>')}
  <a class="xlink" href="#">Time a switch precisely, with our Job Change report &rarr;</a>
</div><div class="pno">05</div></section>

<!-- 07 MONEY -->
<section class="page"><div class="col">
  <div class="eyebrow">02 &middot; Money &amp; financial pattern</div>
  <h2 class="head">How money moves for you</h2>
  <div class="rule"></div>
  {tcard("money", "i-coins",
    f'<div class="pts">'
    f'<div class="pt"><svg class="ic pi"><use href="#i-coins"/></svg><div class="tx"><b>How you earn &amp; save</b>{wealth["second"]}.</div></div>'
    f'<div class="pt"><svg class="ic pi"><use href="#i-trend"/></svg><div class="tx"><b>How gains arrive</b>{wealth["gains"]}.</div></div>'
    f'</div>')}
</div><div class="pno">06</div></section>

<!-- 09 MARRIAGE -->
<section class="page"><div class="col">
  <div class="eyebrow">03 &middot; Marriage &amp; partnership</div>
  <h2 class="head">What you need in a partner</h2>
  <div class="rule"></div>
  {tcard("marriage", "i-people",
    f'<div class="pts">'
    f'<div class="pt"><svg class="ic pi"><use href="#i-people"/></svg><div class="tx"><b>Your partnership style</b>{p["relationship"]["line"]}.</div></div>'
    f'</div>')}
  <a class="xlink" href="#">Check real compatibility, with our Milan report &rarr;</a>
</div><div class="pno">07</div></section>

<!-- 11 CHILDREN -->
<section class="page"><div class="col">
  <div class="eyebrow">04 &middot; Children &amp; family formation</div>
  <h2 class="head">Building a family, your way</h2>
  <div class="rule"></div>
  {tcard("children", "i-gem",
    f'<div class="pts">'
    f'<div class="pt"><svg class="ic pi"><use href="#i-gem"/></svg><div class="tx"><b>Your family-formation pattern</b>{p["children"]}.</div></div>'
    f'</div>')}
  <div class="note"><b>A boundary we hold:</b> this reads a tendency, never a date, and never a claim about fertility.</div>
</div><div class="pno">08</div></section>

<!-- 13 HOME -->
<section class="page"><div class="col">
  <div class="eyebrow">05 &middot; Home &amp; property</div>
  <h2 class="head">Where and how you put down roots</h2>
  <div class="rule"></div>
  {tcard("home", "i-shield",
    f'<div class="pts">'
    f'<div class="pt"><svg class="ic pi"><use href="#i-shield"/></svg><div class="tx"><b>Your property pattern</b>{p["home"]}.</div></div>'
    f'</div>')}
</div><div class="pno">09</div></section>

<!-- 15 FOREIGN -->
<section class="page"><div class="col">
  <div class="eyebrow">06 &middot; Foreign travel &amp; relocation</div>
  <h2 class="head">Whether distance suits you</h2>
  <div class="rule"></div>
  {tcard("foreign", "i-target",
    f'<div class="pts">'
    f'<div class="pt"><svg class="ic pi"><use href="#i-target"/></svg><div class="tx"><b>Your relocation pattern</b>{p["foreign"]}.</div></div>'
    f'</div>')}
</div><div class="pno">10</div></section>

<!-- 17 HEALTH -->
<section class="page"><div class="col">
  <div class="eyebrow">07 &middot; Health &amp; energy</div>
  <h2 class="head">How your body tends to run</h2>
  <div class="rule"></div>
  {tcard("health", "i-moon",
    f'<div class="pts">'
    f'<div class="pt"><svg class="ic pi"><use href="#i-moon"/></svg><div class="tx"><b>Your constitutional tendency</b>{p["health"]}.</div></div>'
    f'</div>')}
  <div class="note"><b>A boundary we hold:</b> this is a classical tendency, not a medical diagnosis.</div>
</div><div class="pno">11</div></section>

<!-- 19 GROWTH -->
<section class="page"><div class="col">
  <div class="eyebrow">08 &middot; Personal growth &amp; identity</div>
  <h2 class="head">What comes naturally, and what doesn't</h2>
  <div class="rule"></div>
  <div class="pts">
    {strengths_pts}
    {lessons_pts}
    <div class="pt"><svg class="ic pi"><use href="#i-scales"/></svg><div class="tx"><b>Your elemental balance</b>{elements["dominant"]} runs strongest in your chart{("; " + " and ".join(elements["missing"]) + " is quiet") if elements["missing"] else ""}.</div></div>
  </div>
</div><div class="pno">12</div></section>

<!-- 20 FAMILY -->
<section class="page"><div class="col">
  <div class="eyebrow">09 &middot; Family relationships</div>
  <h2 class="head">Parents, siblings, and old ties</h2>
  <div class="rule"></div>
  {tcard("family", "i-people",
    f'<div class="pts">'
    f'<div class="pt"><svg class="ic pi"><use href="#i-people"/></svg><div class="tx"><b>Your family-relationship pattern</b>{p["family"]}.</div></div>'
    f'</div>')}
</div><div class="pno">13</div></section>

<!-- 14 CURRENT PERIOD -->
<section class="page"><div class="col">
  <div class="eyebrow">10 &middot; Current period &amp; what's next</div>
  <h2 class="head">The chapter you're in</h2>
  <div class="rule"></div>
  <div class="callout"><div class="ch"><svg class="ic"><use href="#i-hourglass"/></svg> Right now</div><p>{teaser["current_dasha"]}, until {teaser["dasha_till"]}.</p></div>
  {roadmap_wins}
  <div class="note">Periods are openings, not fixed dates. They raise your odds &mdash; the effort still has to come from you.</div>
</div><div class="pno">14</div></section>

<!-- 15 CAUTION -->
<section class="page"><div class="col">
  <div class="eyebrow terra">When to play it safe</div>
  <h2 class="head">{"Your careful stretch" if sade_active else "No major caution flag right now"}</h2>
  <div class="rule"></div>
  <div class="verdict terra sum"><svg class="ic"><use href="#i-alert"/></svg> {("Sade Sati, " + sade.get("phase", "") + " &mdash; until " + sade.get("ends", "")) if sade_active else "Nothing flagged as a hard caution period at the moment."}</div>
  <div class="pts">
    <div class="pt {'warn' if sade_active else 'good'}"><svg class="ic pi"><use href="#i-hourglass"/></svg><div class="tx"><b>What it means</b>{("Saturn is transiting near your Moon &mdash; a season for patience on big decisions, not a sign anything is wrong.") if sade_active else "The usual discipline on money and big decisions is enough for now."}</div></div>
    {("<div class='pt'><svg class=\"ic pi\"><use href=\"#i-check\"/></svg><div class=\"tx\"><b>Areas worth watching</b>" + ", ".join(LABEL[a] for a in watch_areas) + ".</div></div>") if watch_areas else ""}
  </div>
</div><div class="pno">15</div></section>

<!-- 16 REMEDIES -->
<section class="page"><div class="col">
  <div class="eyebrow">Remedies &amp; your plan</div>
  <h2 class="head">What to actually do</h2>
  <div class="rule"></div>
  <div class="callout"><div class="ch"><svg class="ic"><use href="#i-check"/></svg> Simple, classical support</div><p>Offered to steady you, never to frighten you. No remedy replaces the plan on the pages before this.</p></div>
  <div class="pts">
    {remedy_pts}
  </div>
</div><div class="pno">16</div></section>

<!-- 17 KUNDLI -->
<section class="page"><div class="col">
  <div class="eyebrow">Your chart &middot; the proof</div>
  <h2 class="head">Your kundli</h2>
  <div class="rule"></div>
  <div class="kundli">
    {kundli_cells}
    {kundli_center}
  </div>
  <div class="klegend">Your birth chart, South-Indian style &middot; Ascendant marked in gold. Every reading in this report is calculated from this chart &mdash; nothing is guessed, and any astrologer can verify it.</div>
</div><div class="pno">17</div></section>

<!-- 18 PLANETS -->
<section class="page"><div class="col">
  <div class="eyebrow">Your chart &middot; the proof</div>
  <h2 class="head">Every planet, placed</h2>
  <div class="rule"></div>
  <div class="tscroll"><table class="k">
    <tr><th>Planet</th><th>Sign</th><th>House</th><th>What it means</th></tr>
    {planet_rows}
  </table></div>
</div><div class="pno">18</div></section>

<!-- 19 METHODOLOGY -->
<section class="page"><div class="col">
  <div class="eyebrow">Your chart &middot; methodology</div>
  <h2 class="head">Which house feeds which page</h2>
  <div class="rule"></div>
  <div class="lead">A handful of houses carry each area of this report. Here's the map, so nothing in it reads as a guess.</div>
  <div class="pts">
    <div class="pt"><svg class="ic pi"><use href="#i-compass"/></svg><div class="tx"><b>10th house &mdash; career</b>Work, status, and public role.</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-coins"/></svg><div class="tx"><b>2nd &amp; 11th houses &mdash; money</b>Saved wealth, and the gains that come from effort.</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-people"/></svg><div class="tx"><b>7th house &mdash; partnership</b>Marriage, and business partnership too.</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-gem"/></svg><div class="tx"><b>5th house &mdash; children</b>Creativity and family formation.</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-shield"/></svg><div class="tx"><b>4th house &mdash; home</b>Property, base, and domestic comfort.</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-target"/></svg><div class="tx"><b>12th house &mdash; foreign lands</b>Distance, relocation, and what lies beyond home.</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-moon"/></svg><div class="tx"><b>6th house &mdash; health</b>Routine, resilience, and daily friction.</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-people"/></svg><div class="tx"><b>9th house &mdash; family</b>Father, elders, and inherited belief.</div></div>
  </div>
</div><div class="pno">19</div></section>

<!-- 20 CLOSING -->
<section class="page sand"><div class="col">
  <div class="eyebrow">With gratitude</div>
  <h2 class="head">Thank you, {name}</h2>
  <div class="rule"></div>
  <div class="lead">Thank you for trusting Axtroshastra with your questions. We hope this reading gave you a little clarity &mdash; and a little calm &mdash; about the road ahead.</div>
  <div class="lead">Got a question about one part of your life in particular? These are calculated the same honest way:</div>
  <div class="pts">
    <div class="pt"><svg class="ic pi"><use href="#i-people"/></svg><div class="tx"><b>Compatibility</b>Whether two charts really move together.</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-clock"/></svg><div class="tx"><b>Job Change</b>The right window to switch, and where to go next.</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-store"/></svg><div class="tx"><b>Vyapar &mdash; Business</b>When to build, and when to hold.</div></div>
  </div>
  <div class="cov-trust">www.axtroshastra.com &middot; Swiss Ephemeris &middot; Lahiri ayanamsa</div>
</div><div class="pno">20</div></section>

<style>
#ax-stickybar{{position:fixed;left:0;right:0;bottom:0;z-index:9997;
background:linear-gradient(180deg,rgba(250,245,237,0),var(--cream) 22%);
padding:14px 16px calc(14px + env(safe-area-inset-bottom))}}
#ax-stickybar .inner{{max-width:430px;margin:0 auto;display:flex;gap:10px}}
#ax-stickybar a{{flex:1;display:flex;align-items:center;justify-content:center;gap:8px;
min-height:52px;text-align:center;text-decoration:none;border-radius:12px;padding:12px 10px;
font:700 15px/1.15 var(--sans);-webkit-tap-highlight-color:transparent}}
#ax-stickybar a:active{{transform:scale(.97);filter:brightness(1.08)}}
#ax-stickybar svg{{width:19px;height:19px;flex:none}}
#ax-stickybar .pdf{{background:var(--ink);color:#F5EEE0;box-shadow:0 6px 16px rgba(42,35,56,.28)}}
#ax-stickybar .pdf svg{{color:var(--gold2)}}
#ax-stickybar .wa{{background:var(--green);color:#fff;box-shadow:0 6px 16px rgba(62,125,90,.28)}}
@media (min-width:640px){{#ax-stickybar a{{min-height:48px;font-size:15px}}}}
@media print{{#ax-stickybar{{display:none!important}}}}</style>
<div id='ax-stickybar'><div class='inner'>
<a class='pdf' id='ax-pdf' href='#' onclick='window.print();return false;'><svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'><path d='M12 3v12'/><path d='M6 11l6 6 6-6'/><path d='M4 21h16'/></svg>Download PDF</a>
<a class='wa' href='#' onclick='axShare();return false;'><svg viewBox='0 0 24 24' fill='currentColor' aria-hidden='true'><path d='M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 2a8 8 0 1 1-4.1 14.9l-.5-.3-2.6.7.7-2.5-.3-.5A8 8 0 0 1 12 4zm-3.1 4.3c-.2 0-.5.1-.7.3-.7.7-1 1.6-.8 2.6.3 1.2 1 2.4 2.1 3.5 1.4 1.4 3 2.3 4.6 2.5.8.1 1.6-.2 2.2-.8.2-.2.3-.5.3-.8l-.1-.7c-.1-.2-.2-.4-.5-.5l-1.7-.8a.8.8 0 0 0-.9.2l-.5.5c-.1.2-.4.2-.6.1a6.7 6.7 0 0 1-2.9-2.9c-.1-.2 0-.4.1-.6l.5-.5c.2-.2.3-.6.2-.9l-.8-1.7c-.1-.2-.3-.4-.5-.4l-.5-.1z'/></svg>Share on WhatsApp</a>
</div></div>
<script>
window.axShare=function(){{var url=location.href;var t='Check out my Life Blueprint report from Axtroshastra';if(navigator.share){{navigator.share({{title:'Axtroshastra',text:t,url:url}}).catch(function(){{}});}}else{{window.open('https://wa.me/?text='+encodeURIComponent(t+' '+url),'_blank');}}}};
</script>
</body></html>"""


def render_vidyarthi(p: dict) -> str:
    """/career (formerly /padhai) — student career & academic timing report. Unified v3 layout:
    positive-first ordering (profile -> now -> near-term outlook -> strengths)
    through the middle "what needs work" section (5 factors, strongest first,
    with fix-it dropdowns) to a confidence-boosting close (honest part,
    keepsake, FAQ). Every number traces to a real chart computation — dignity
    scores for the 5 factors and 3 ranked career types, north_chart_svg for
    the kundli, _weak_periods for the hold-back window — none of it mocked."""
    m = p["meta"]
    m = {**m, "name": escape(m["name"])}  # user-supplied name: escape to prevent stored XSS
    ex = p.get("extras", {})
    five_factors = ex.get("five_factors", [])
    candidates = ex.get("career_candidates") or []
    top = candidates[0] if candidates else None
    top_arche = (top["archetype"] if top else
                ex.get("career_archetype") or {"name": "Your Path", "emoji": "✦", "tagline": "", "body": ""})
    top_score = top["score"] if top else None
    w1 = min(p["windows"], key=lambda w: w["start"]) if p["windows"] else None

    hardship_html = ""
    if ex.get("has_hardship"):
        gem_line = (f"<li><b>Gemstone:</b> {ex['gem']} — only via a qualified jeweller/astrologer trial.</li>"
                    if ex.get("gem") else f"<li><b>Gemstone:</b> {ex.get('gem_note', '')}</li>")
        hardship_html = f"""<div class='reassure honest'><b>💬 The honest part</b><p style='margin-top:6px'>{ex['line']}</p>
<p style='margin-top:8px'><b>Classical support for this period:</b></p>
<ul class='rem'><li><b>Fast day:</b> {ex.get('fast_day', '—')}</li>
<li><b>Mantra:</b> {ex.get('mantra', '—')} — 108 times, on {ex.get('fast_day', 'the fast day')}</li>
{gem_line}</ul>
<p class='soft'>The first remedy is always action — showing up in the window above. This is support, not a substitute.</p></div>"""
    else:
        hardship_html = f"<div class='reassure honest'><b>💬 The honest part</b><p style='margin-top:6px'>{ex.get('line', '')}</p></div>"

    ss = ex.get("sade_sati", {})
    if ss.get("active"):
        ss_html = (f"<div class='ssb'><b>Sade Sati — currently active:</b> {ss['phase']}, till <b>{ss['ends']}</b>. "
                  f"Classically this means discipline and restructuring — it can feel like delay, but what's "
                  f"built in this period tends to be durable. Not a warning; a work period.</div>")
    else:
        ss_html = (f"<div class='ssb'><b>Sade Sati — not currently active.</b> Next phase approx "
                  f"{ss.get('next_starts', '—')}. No Saturn pressure on this axis right now.</div>")

    field_fit_html = (f"""<div class="fieldfit">🎓 <b>{escape(ex['stage_label'])}:</b> {ex['stage_note']}</div>"""
                      if ex.get("stage_note") else "")

    kundli_svg = north_chart_svg(p)

    tagpicker_rows = _tagpicker_html(candidates)
    tag_default = (f"<span class='chip'>{top_arche['emoji']} {escape(top_arche['name'])} · {top_score}%</span>"
                  if top else "")

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{m['name']} — Career &amp; Academic Timing | Axtroshastra</title>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&display=swap" rel="stylesheet">
<style>
:root{{--ink:#23253B;--midnight:#151C39;--midnight2:#23305C;--paper:#FAF6ED;--card:#fff;
--haldi:#E4B04A;--haldi-soft:#F6E7C6;--sindoor:#C93B2E;--green:#2E7D53;--green-soft:#E6F2EA;
--rose:#C2185B;--rose-soft:#FBE7F0;--violet:#6C5CE7;--violet-soft:#EEEBFC;--muted:#6B6D82;--line:#E7E0D2;
--display:'Bricolage Grotesque',sans-serif}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,'Segoe UI',sans-serif;background:var(--paper);color:var(--ink);
line-height:1.6;font-size:15.5px;max-width:640px;margin:0 auto;padding:0 20px 60px}}
h2{{font-family:var(--display);font-size:20px;margin:32px 0 8px}}
.lead{{color:var(--muted);font-size:14px;margin:0 0 12px}}
.hero{{background:radial-gradient(1000px 460px at 50% -25%, var(--midnight2), var(--midnight) 68%);
color:#F3EFE4;margin-top:16px;padding:32px 24px 26px;text-align:center;border-radius:26px;
box-shadow:0 14px 34px rgba(21,28,57,.18)}}
.hero .brand{{font-family:var(--display);font-weight:800;color:var(--haldi);font-size:11px;letter-spacing:.14em}}
.hero h1{{font-family:var(--display);font-size:25px;color:#fff;margin-top:12px}}
.hero .meta{{color:#8F92AB;font-size:13.5px;margin-top:10px}}
.hero .fitscore{{font-family:var(--display);font-weight:800;font-size:44px;color:var(--haldi);margin-top:10px;line-height:1}}
.hero .fitscore small{{font-size:14px;color:#B9BBD0;display:block;font-weight:600;margin-top:4px}}
.hero .arche{{display:inline-block;background:rgba(228,176,74,.16);border:1px solid rgba(228,176,74,.5);
color:#F1E4C4;font-family:var(--display);font-weight:700;font-size:13px;border-radius:20px;padding:6px 16px;margin-top:12px}}
.profile{{background:var(--card);border:1.5px solid var(--line);border-radius:16px;padding:18px;margin-top:14px}}
.profile .ptop{{display:flex;align-items:center;gap:12px}}
.profile .pemoji{{font-size:28px}}
.profile .pname{{font-family:var(--display);font-weight:800;font-size:17px}}
.profile .psign{{font-size:11px;color:var(--muted);text-transform:uppercase;font-weight:700;margin-top:2px}}
.profile .pline{{font-size:14px;margin-top:10px}}
.kchart-wrap{{background:var(--midnight);border-radius:14px;padding:14px;margin-top:12px;text-align:center}}
.kchart-wrap .kcap{{font-size:11px;color:#8F92AB;text-transform:uppercase;margin-top:8px}}
.kchart{{width:100%;max-width:280px;margin:0 auto;display:block}}
.nowcard{{background:linear-gradient(180deg,#26325E,var(--midnight));color:#F3EFE4;border-radius:16px;
padding:20px;margin-top:20px;text-align:center}}
.nowcard .k{{font-family:var(--display);font-weight:800;font-size:11px;text-transform:uppercase;color:var(--haldi)}}
.nowcard .big{{font-family:var(--display);font-weight:800;font-size:18px;color:#fff;margin:8px 0 6px}}
.nowcard p{{font-size:14px;color:#CFCBBB}}
.nowcard .verdict{{display:inline-block;background:var(--green);color:#fff;font-family:var(--display);font-weight:800;
font-size:12px;border-radius:20px;padding:5px 14px;margin-top:10px}}
.near{{background:var(--card);border:1.5px solid var(--line);border-radius:16px;padding:18px;margin-top:14px}}
.near .track{{position:relative;height:38px;background:var(--haldi-soft);border-radius:8px;overflow:hidden;margin-top:12px}}
.near .fill{{position:absolute;top:0;bottom:0;border-radius:6px;display:flex;align-items:center;justify-content:center;
font:800 11px/1 var(--display);color:#fff;padding:0 6px;overflow:hidden;white-space:nowrap}}
.near .peak{{position:absolute;top:-4px;bottom:-4px;border:2px dashed rgba(255,255,255,.7);border-radius:8px}}
.near .yrs{{display:flex;justify-content:space-between;font-size:10px;color:var(--muted);margin-top:6px}}
.near .note{{font-size:13.5px;color:var(--muted);margin-top:10px;line-height:1.55}}
.near .note b{{color:var(--ink)}}
.split{{display:flex;gap:10px;margin-top:20px}}
.splitcol{{flex:1;background:var(--card);border:1.5px solid var(--line);border-radius:12px;padding:14px}}
.splitcol.good{{border-color:var(--green)}}
.splitcol.watch{{border-color:var(--rose)}}
.splitcol .st{{font-family:var(--display);font-weight:800;font-size:12px;text-transform:uppercase}}
.splitcol.good .st{{color:var(--green)}}
.splitcol.watch .st{{color:var(--rose)}}
.splitcol ul{{list-style:none;margin-top:8px}}
.splitcol li{{font-size:14px;margin-bottom:6px}}
.glossary{{background:var(--haldi-soft);border-radius:12px;padding:14px 16px;margin-top:18px;font-size:14px}}
.glossary b{{font-family:var(--display)}}
.glossary .row{{display:flex;gap:8px;margin-top:6px}}
.qa{{background:var(--card);border:1.5px solid var(--line);border-radius:14px;padding:6px 18px;margin-top:14px}}
.qa .item{{padding:14px 0;border-bottom:1px solid var(--line)}}
.qa .item:last-child{{border-bottom:0}}
.qa .q{{font-family:var(--display);font-weight:800;font-size:14.5px;display:flex;gap:8px;align-items:baseline}}
.qa .q .em{{font-size:16px}}
.qa .a{{font-size:14px;color:#3A3C55;margin-top:5px;padding-left:24px}}
.careerbar-wrap{{margin-top:14px}}
.careerrow{{display:flex;align-items:center;gap:10px;margin-bottom:12px}}
.careerrow .cr-label{{width:150px;flex:none;font-size:14px;font-weight:700;font-family:var(--display)}}
.careerrow .cr-track{{flex:1;height:20px;background:#EFE8D8;border-radius:6px;overflow:hidden}}
.careerrow .cr-fill{{height:100%;border-radius:6px;display:flex;align-items:center;justify-content:flex-end;padding-right:8px}}
.careerrow .cr-fill span{{font:800 11px/1 var(--display);color:#fff}}
.career-desc{{font-size:14px;color:var(--muted);margin:2px 0 12px 160px}}
.pair{{display:flex;gap:10px;margin-top:14px}}
.pcard{{flex:1;border-radius:14px;padding:16px;color:#fff}}
.pcard.up{{background:linear-gradient(160deg,#2E7D53,#1F5E3D)}}
.pcard.lesson{{background:linear-gradient(160deg,#C2185B,#8E1044)}}
.pcard .pk{{font-size:11px;font-weight:800;text-transform:uppercase;opacity:.85}}
.pcard .pv{{font-family:var(--display);font-weight:800;font-size:16px;margin-top:6px}}
.pcard .pd{{font-size:13.5px;margin-top:6px;opacity:.92}}
.factor{{background:var(--card);border:1.5px solid var(--line);border-radius:12px;padding:15px 16px;margin-bottom:10px}}
.factor .ftop{{display:flex;justify-content:space-between;align-items:center}}
.factor .fname{{font-family:var(--display);font-weight:800;font-size:15.5px}}
.factor .fstatus{{font-size:11px;font-weight:800;border-radius:20px;padding:3px 10px}}
.factor .fstatus.strong{{background:var(--green-soft);color:var(--green)}}
.factor .fstatus.watch{{background:var(--rose-soft);color:var(--rose)}}
.factor .meter{{height:6px;background:#EFE8D8;border-radius:4px;margin:10px 0 8px;overflow:hidden}}
.factor .meter div{{height:100%;border-radius:4px}}
.factor .fplain{{font-family:var(--display);font-weight:700;font-size:14px}}
.factor .fplain.strong{{color:var(--green)}}
.factor .fplain.watch{{color:var(--rose)}}
.factor .fexpl{{font-size:14px;color:#3A3C55;margin-top:5px}}
.factor details{{margin-top:10px;background:var(--paper);border-radius:8px;padding:2px 12px}}
.factor summary{{font-family:var(--display);font-weight:700;font-size:12.5px;color:var(--sindoor);cursor:pointer;
list-style:none;padding:9px 0}}
.factor summary::-webkit-details-marker{{display:none}}
.factor summary::before{{content:"› ";font-weight:800}}
.factor details[open] summary::before{{content:"⌄ "}}
.factor details p{{font-size:14px;color:#3A3C55;padding-bottom:10px}}
.fieldfit{{background:var(--violet-soft);border:1.5px solid var(--violet);border-radius:12px;padding:15px 16px;margin-top:14px;font-size:15px}}
.fieldfit b{{font-family:var(--display);color:var(--violet)}}
.actionbox{{background:var(--card);border:1.5px solid var(--line);border-radius:12px;padding:16px;margin-top:14px}}
.actionbox .ak{{font-family:var(--display);font-weight:800;color:var(--sindoor);font-size:12px;text-transform:uppercase}}
.actionbox ol{{margin:8px 0 0 18px;font-size:15px}}
.actionbox li{{margin-bottom:10px}}
.actionbox li b{{font-family:var(--display)}}
.hold{{background:#FFF6E9;border:1.5px solid var(--haldi);border-radius:12px;padding:15px 16px;margin-top:14px;font-size:14px}}
.hold b{{font-family:var(--display)}}
.reassure{{background:var(--green-soft);border:2px solid var(--green);border-radius:12px;padding:14px 16px;margin-top:10px;font-size:15px}}
.reassure b{{font-family:var(--display)}}
.ssb{{background:var(--haldi-soft);border-radius:12px;padding:14px 16px;font-size:14px;margin-top:12px}}
.card{{background:var(--card);border:1.5px solid var(--line);border-radius:12px;padding:16px;margin-bottom:12px}}
.cert-toggle{{display:flex;gap:8px;margin-top:6px}}
.cert-toggle button{{flex:1;padding:9px;border-radius:10px;border:1.5px solid var(--line);background:var(--card);
font:700 12.5px var(--display);cursor:pointer;color:var(--muted)}}
.cert-toggle button.active{{background:var(--midnight);color:#fff;border-color:var(--midnight)}}
.certwrap{{margin-top:14px;border-radius:24px;padding:3px;position:relative;
background:linear-gradient(135deg,#E4B04A,#F6E7C6 45%,#E4B04A);box-shadow:0 16px 40px rgba(35,37,59,.16)}}
.cert-card{{border-radius:21px;padding:26px 20px 20px;text-align:center;transition:background .2s,color .2s}}
.certwrap[data-skin="light"] .cert-card{{background:linear-gradient(175deg,#FFFDF7,#FBF1DC);color:#23253B}}
.certwrap[data-skin="dark"] .cert-card{{background:radial-gradient(600px 300px at 50% -10%,#26325E,#0F1226 72%);color:#F3EFE4}}
.cert-brand{{display:flex;align-items:center;justify-content:center;gap:6px;font-family:var(--display);
font-weight:800;font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--haldi)}}
.cert-tagline{{font-size:9.5px;color:var(--muted);text-transform:uppercase;margin-top:2px}}
.certwrap[data-skin="dark"] .cert-tagline{{color:#9C9FC4}}
.cert-inner{{border-radius:16px;padding:20px 16px;margin-top:16px}}
.cert-eyebrow{{font-family:var(--display);font-weight:700;font-size:10.5px;text-transform:uppercase;color:var(--muted)}}
.certwrap[data-skin="dark"] .cert-eyebrow{{color:#9C9FC4}}
.cert-name{{font-family:var(--display);font-weight:800;font-size:23px;margin-top:8px;
background:linear-gradient(90deg,#C9922E,#E4B04A 40%,#C9922E);-webkit-background-clip:text;background-clip:text;color:transparent}}
.certwrap[data-skin="dark"] .cert-name{{background:linear-gradient(90deg,#F6E7C6,#E4B04A 50%,#F6E7C6);-webkit-background-clip:text;background-clip:text}}
.cert-tags{{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:14px;min-height:32px}}
.chip{{display:inline-flex;align-items:center;gap:6px;font-family:var(--display);font-weight:800;font-size:12.5px;
background:var(--haldi);color:#151C39;border-radius:20px;padding:7px 13px;box-shadow:0 4px 10px rgba(228,176,74,.35)}}
.cert-footer{{margin-top:18px;padding-top:14px;border-top:1px solid rgba(228,176,74,.35);
display:flex;justify-content:space-between;align-items:center;font-size:10.5px;color:var(--muted)}}
.certwrap[data-skin="dark"] .cert-footer{{color:#8F92AB}}
.cert-footer b{{color:var(--haldi);font-family:var(--display)}}
.cert-warn{{font-size:11.5px;color:var(--sindoor);margin-top:8px;text-align:center;display:none}}
.cert-warn.show{{display:block}}
.tagpicker{{background:var(--card);border:1.5px solid var(--line);border-radius:12px;padding:6px 14px;margin-top:12px}}
.tp-row{{display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--line)}}
.tp-row:last-child{{border-bottom:0}}
.tp-check{{display:flex;align-items:center;gap:8px;font-size:14px;font-weight:600;cursor:pointer}}
.tp-check input{{width:16px;height:16px;accent-color:var(--sindoor)}}
.tp-pct{{font-family:var(--display);font-weight:800;font-size:11.5px;border-radius:20px;padding:5px 11px;cursor:pointer;
border:1.5px solid var(--haldi);background:var(--haldi-soft);color:#8A6413}}
.tp-pct.off{{background:transparent;border-color:var(--line);color:var(--muted)}}
.certactions{{display:flex;gap:10px;margin-top:12px}}
.certbtn{{flex:1;text-align:center;font-family:var(--display);font-weight:800;font-size:14px;padding:11px 10px;
border-radius:11px;border:1.5px solid var(--line);background:var(--card);cursor:pointer;display:flex;
align-items:center;justify-content:center;gap:6px;color:var(--ink)}}
.certbtn.primary{{background:var(--midnight);color:#fff;border-color:var(--midnight)}}
.share{{background:#fff;border:2px dashed var(--haldi);border-radius:14px;padding:16px 18px;margin-top:14px;font-size:15px}}
.stillconfused{{background:var(--card);border:1.5px solid var(--line);border-radius:12px;padding:6px 16px;margin-top:14px}}
.stillconfused details{{padding:12px 0;border-bottom:1px solid var(--line)}}
.stillconfused details:last-child{{border-bottom:0}}
.stillconfused summary{{font-family:var(--display);font-weight:700;font-size:14px;cursor:pointer;list-style:none}}
.stillconfused summary::-webkit-details-marker{{display:none}}
.stillconfused summary::before{{content:"› ";color:var(--sindoor)}}
.stillconfused p{{font-size:14px;color:#3A3C55;margin-top:8px;padding-left:14px}}
.method{{background:var(--card);border:1.5px solid var(--line);border-radius:12px;padding:15px 16px;font-size:14px;margin-top:14px}}
.method table{{width:100%;border-collapse:collapse;margin-top:8px;font-size:13.5px}}
.method th,.method td{{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)}}
.method th{{font-family:var(--display);font-size:10.5px;text-transform:uppercase;color:var(--muted)}}
.sectionnote{{background:#F3ECDD;border-left:3px solid var(--violet);padding:8px 12px;border-radius:6px;font-size:11.5px;color:var(--muted);margin-top:8px}}
.gloss{{list-style:none;margin-top:8px}}
.gloss li{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin-bottom:7px;font-size:14px}}
.gloss b{{font-family:var(--display)}}
.actions{{display:flex;gap:10px;margin-top:24px}}
.btn{{flex:1;text-align:center;font-family:var(--display);font-weight:800;font-size:15px;padding:12px 10px;
border-radius:12px;border:0;text-decoration:none;display:flex;align-items:center;justify-content:center;gap:7px;cursor:pointer}}
.btn.pdf{{background:var(--midnight);color:#fff}}
.btn.share{{background:#25D366;color:#fff}}
.tn{{font-size:11.5px;color:var(--muted);margin-top:22px;line-height:1.6}}
@media print{{#ax-pdf,.btn.share,.certbtn,.cert-toggle,.tagpicker{{display:none!important}}body{{background:#fff}}
.factor,.hold,.reassure,.certwrap,.near{{break-inside:avoid}}h2{{break-after:avoid}}
*{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}}}
</style></head><body>

<header class="hero">
<p class="brand">✦ AXTROSHASTRA · CAREER &amp; ACADEMIC TIMING</p>
<h1>{m['name']}</h1>
{f"<p class='fitscore'>{top_score}%<small>match with your strongest career direction</small></p>" if top_score is not None else ""}
<span class="arche">{top_arche['emoji']} {escape(top_arche['name'])}</span>
</header>

<h2>Your profile</h2>
<p class="lead">The base your whole report is calculated from — not guesswork, your actual birth chart.</p>
<div class="profile">
<div class="ptop"><span class="pemoji">🌙</span><div><p class="pname">Moon in {p['teaser']['moon_sign']}</p>
<p class="psign">{p['teaser']['nakshatra']} · pada {p['teaser']['pada']} · Lagna {p['chart']['lagna']}</p></div></div>
<p class="pline"><b>How you learn:</b> {ex.get('study_strength', '')}.</p>
{f"<p class='pline'><b>What comes naturally:</b> {ex['natural_gift']}.</p>" if ex.get('natural_gift') else ''}
<div class="kchart-wrap">{kundli_svg}<p class="kcap">Your birth chart · North Indian style · the same one from your form</p></div>
</div>

{_nowcard_html(p)}

{_nearterm_html(p)}

{_split_html(five_factors)}

<div class="glossary">
<b>What do "Strong" and "Building" actually mean?</b>
<div class="row">💪 <span><b>Strong</b> = this is genuinely your best shot — act on it.</span></div>
<div class="row">🌤️ <span><b>Moderate</b> = still good, keep showing up, don't force it.</span></div>
<div class="row">🌱 <span><b>Building</b> = preparation phase — the payoff comes later, not now.</span></div>
</div>

{_qa_html(p, ex, w1)}

{_career_html(candidates)}

<h2>Your superpower &amp; your one lesson</h2>
<div class="pair">
<div class="pcard up"><p class="pk">💎 Superpower</p><p class="pv">{ex.get('natural_gift') or '—'}</p>
<p class="pd">Well-placed in your chart — this is a real strength to lean on.</p></div>
<div class="pcard lesson"><p class="pk">📈 Growth edge</p><p class="pv">{ex.get('growth_lesson') or '—'}</p>
<p class="pd">Naming this early is most of the fix.</p></div>
</div>

<h2>Your five core factors</h2>
<p class="lead">Strongest first, so you see what's already working before what needs work.</p>
{_factor_cards_html(five_factors)}

{field_fit_html}

{_do_next_html(ex, w1)}

{_holdback_html(p)}

{hardship_html}
{ss_html}

<h2>Your keepsake ✦</h2>
<p class="lead">Shareable, and yours to personalise — choose a skin, pick which of your computed types to show.</p>
<div class="cert-toggle">
<button type="button" id="skinLightBtn" class="active" onclick="axSetSkin('light')">☀️ Light</button>
<button type="button" id="skinDarkBtn" onclick="axSetSkin('dark')">🌙 Dark</button>
</div>
<div class="certwrap" id="certWrap" data-skin="light">
<div class="cert-card" id="certCard">
<p class="cert-brand">✦ Axtroshastra</p>
<p class="cert-tagline">Career &amp; Academic Timing</p>
<div class="cert-inner">
<p class="cert-eyebrow">Certificate of Career Direction</p>
<p class="cert-name">{m['name']}</p>
<div class="cert-tags" id="certTags">{tag_default}</div>
</div>
<div class="cert-footer"><span>axtroshastra.com</span><span><b>Issued</b> {m['generated']}</span></div>
</div>
</div>
<div class="tagpicker">{tagpicker_rows}<p class="cert-warn" id="certWarn">Keep at least one tag — pick another before removing this one.</p></div>
<div class="certactions">
<button type="button" class="certbtn" onclick="axDownloadCard()">⬇️ Download this card</button>
<button type="button" class="certbtn primary" onclick="axShareCard()">📲 Share this card</button>
</div>
<div class="share">📲 <b>Show this to a parent, teacher, or mentor</b> and ask: "does this sound like me?" People who know your habits give the best gut-check.</div>

<h2>Still a little confused?</h2>
<div class="stillconfused">
<details><summary>Does "Strong" mean I'll definitely succeed?</summary><p>No — it means the timing helps you, like a tailwind. You still have to run. A strong window with no effort beats nothing; effort in a strong window beats everything.</p></details>
<details><summary>What if I don't like the direction it gives me?</summary><p>It's a lean, not a life sentence. The chart shows what comes <i>easiest</i> — you're free to go elsewhere, it'll just ask more effort. Use it as information, not a cage.</p></details>
<details><summary>Why only a couple years, not the full picture?</summary><p>Because a wall of decade-long dates creates anxiety, not clarity. We show you the nearest window that applies, and expand further out only if nothing's close.</p></details>
</div>

<div class="actions">
<a class="btn pdf" id="ax-pdf" href="#" onclick="window.print();return false;">⬇️ Download PDF</a>
<a class="btn share" href="#" onclick="axShare();return false;">📲 Share on WhatsApp</a>
</div>

<h2>How we calculated this</h2>
<div class="method">
<p>Classical Vimshottari dasha + transit system, computed from precise NASA-grade planetary positions and standard Lahiri ayanamsa. Same inputs, same result, every time — not mood-of-the-day.</p>
<table><tr><th>Field</th><th>Value</th></tr>
<tr><td>Moon sign</td><td>{p['teaser']['moon_sign']}</td></tr>
<tr><td>Nakshatra</td><td>{p['teaser']['nakshatra']} · pada {p['teaser']['pada']}</td></tr>
<tr><td>Lagna</td><td>{p['chart']['lagna']}</td></tr>
</table>
<p class="sectionnote">The 5 factor scores and career-type percentages come from Uccha Bala — each house's ruling planet is scored by its exact degree-distance from its classical exaltation point (highest) to its debilitation point (lowest), so no two birth charts land on the same numbers by coincidence. The near-term outlook checks 2 years first, then 5, then 10, only expanding until it finds your nearest genuine window.</p>
</div>

<h2>What each factor means</h2>
<ul class="gloss">
<li><b>Study Habits</b> — your 4th house: the environment and discipline that shapes how you actually learn.</li>
<li><b>Exam &amp; Performance</b> — your 5th house: intelligence, memory, and how you perform under pressure.</li>
<li><b>Higher Education Luck</b> — your 9th house: fortune, scholarships, and guru-grace in advanced study.</li>
<li><b>Career Direction</b> — your 10th house: the classic career house — status, structure, public role.</li>
<li><b>Follow-Through</b> — Saturn's own placement: discipline, delay, and hard-won (but durable) success.</li>
</ul>

<p class="tn">System: {'Chandra Lagna' if m['system']=='chandra_lagna' else 'Lagna-based'} ·
Lahiri ayanamsa · Indications, not fate — the chart shows direction, the effort is yours.<br>
<a href='https://wa.me/919599827297' style='color:inherit'>WhatsApp +91 95998 27297</a> · <a href="/privacy" style="color:inherit">Privacy</a> · <a href="/terms" style="color:inherit">Terms</a> · <a href="/refunds" style="color:inherit">Refund Policy</a></p>

<script>
window.axShare=function(){{var url=location.href;var t=(window.__axlang==='en'?'Check out my career timing report from Axtroshastra':'Meri career timing report Axtroshastra se');if(navigator.share){{navigator.share({{title:'Axtroshastra',text:t,url:url}}).catch(function(){{}});}}else{{window.open('https://wa.me/?text='+encodeURIComponent(t+' '+url),'_blank');}}}};
function axSetSkin(skin){{var wrap=document.getElementById('certWrap');if(!wrap)return;wrap.dataset.skin=skin;
document.getElementById('skinLightBtn').classList.toggle('active',skin==='light');
document.getElementById('skinDarkBtn').classList.toggle('active',skin==='dark');}}
function axCheckboxChanged(cb){{var anyChecked=Array.prototype.some.call(document.querySelectorAll('.tp-row input[type=checkbox]'),function(i){{return i.checked;}});
var warn=document.getElementById('certWarn');
if(!anyChecked){{cb.checked=true;warn.classList.add('show');setTimeout(function(){{warn.classList.remove('show');}},2200);}}
axRenderTags();}}
function axTogglePctBtn(btn){{btn.classList.toggle('off');axRenderTags();}}
function axRenderTags(){{var rows=document.querySelectorAll('.tp-row');var container=document.getElementById('certTags');container.innerHTML='';
rows.forEach(function(row){{var checked=row.querySelector('input[type=checkbox]').checked;if(!checked)return;
var name=row.dataset.name;var pctBtn=row.querySelector('.tp-pct');var showPct=!pctBtn.classList.contains('off');
var text=name+(showPct?' · '+row.dataset.pct+'%':'');var span=document.createElement('span');span.className='chip';
span.textContent=text;container.appendChild(span);}});}}
function axDownloadCard(){{window.print();}}
function axShareCard(){{var container=document.getElementById('certTags');if(!container.children.length){{alert('Add at least one tag to your card before sharing.');return;}}
var url=location.href;var t='My Axtroshastra career type — check it out';
if(navigator.share){{navigator.share({{title:'Axtroshastra',text:t,url:url}}).catch(function(){{}});}}else{{window.open('https://wa.me/?text='+encodeURIComponent(t+' '+url),'_blank');}}}}
if(document.querySelectorAll('.tp-row').length)axRenderTags();
</script>
</body></html>"""


# ============================================================ VYAPAR ASSETS
# v17 design, verbatim. Kept as plain (non-f-string) constants so the CSS and
# the giant data-URI backgrounds stay byte-identical and need no brace-escaping;
# render_vyapar interpolates them into <head>/<body>, exactly as render_milan
# interpolates its AX_PRE / MILAN_I18N constants.
_VYAPAR_CSS = r''':root{
  --sand:#E1D1B9; --sand2:#E4D5BE; --cream:#FAF5ED; --card:#FFFFFF;
  --gold-callout:#FBF4E7; --peach:#FBEFE3; --track:#ECE3D3;
  --ink:#2A2338; --body:#3D352B; --muted:#4A4459; --mauve:#8A8199; --faint:#B9AE96;
  --gold:#B9862E; --gold2:#C9A34E; --brown:#5A3C14; --green:#3E7D5A; --green-bg:#E7F1EA;
  --terra:#B4572B; --terra-bg:#F7E6DC; --line:#E9E1D0; --box-line:#EFE7D6; --gutter:#CBBDA1;
  --serif:'Fraunces','Cormorant Garamond','Playfair Display',Georgia,'Times New Roman',serif;
  --sans:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Noto Sans',sans-serif;
  color-scheme:light;
}
*{box-sizing:border-box;margin:0;padding:0;-webkit-print-color-adjust:exact;print-color-adjust:exact}
html{scroll-behavior:smooth;background:var(--gutter)}
body{background:var(--gutter);color:var(--body);font-family:var(--sans);font-size:15px;line-height:1.58;-webkit-font-smoothing:antialiased;padding:22px 0 34px}
.page{width:min(430px,92vw);margin:0 auto 24px;min-height:min(830px,192vw);display:flex;flex-direction:column;align-items:center;justify-content:center;padding:clamp(30px,6.5vw,40px) clamp(22px,5.5vw,30px);position:relative;text-align:center;background:var(--cream);border-radius:22px;box-shadow:0 14px 38px rgba(48,34,14,.18);overflow:hidden}
.page.sand{background:linear-gradient(165deg,var(--sand),var(--sand2))}
.col{width:100%;max-width:100%;display:flex;flex-direction:column;align-items:center;position:relative;z-index:1}
.pno{z-index:2;position:absolute;bottom:16px;left:0;right:0;text-align:center;font-family:var(--sans);font-size:11px;color:var(--faint);font-variant-numeric:tabular-nums}
/* background: corner planet + one big constellation */





.eyebrow{font-family:var(--sans);font-weight:700;font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--gold)}
.eyebrow.terra{color:var(--terra)}
h2.head{font-family:var(--serif);font-weight:600;font-size:clamp(25px,6vw,30px);line-height:1.1;color:var(--ink);letter-spacing:-.01em;text-wrap:balance;margin:8px 0 0}
.rule{width:40px;height:2px;background:var(--gold);opacity:.6;border-radius:2px;margin:12px 0 2px}
.lead{width:100%;text-align:left;font-family:var(--serif);font-size:16px;color:var(--body);margin-top:14px;line-height:1.5}
.lead b{color:var(--ink)}

/* flowing text points (icon + serif subhead + paragraph, NO box) */
.pts{width:100%;text-align:left;margin-top:18px;display:flex;flex-direction:column;gap:22px}
.pt{display:flex;gap:13px;align-items:flex-start}
.pt .pi{flex:0 0 auto;width:23px;height:23px;color:var(--gold);margin-top:2px}
.pt.warn .pi{color:var(--terra)}.pt.good .pi{color:var(--green)}
.pt .tx{font-family:var(--sans);font-size:13.8px;color:var(--muted);line-height:1.62}
.pt .tx b{font-family:var(--serif);font-weight:600;font-size:15.5px;color:var(--ink);display:block;margin-bottom:2px;line-height:1.2}
.pt.warn .tx b{color:var(--ink)}
.ic{width:100%;height:100%;fill:none;stroke:currentColor;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round}

/* cover */
.cov-brand{font-family:var(--sans);font-weight:700;font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:var(--gold)}
.constel{width:min(210px,78%);height:auto;margin:12px auto 2px;overflow:visible;display:block}
.cov-name{font-family:var(--serif);font-weight:600;font-size:clamp(38px,11vw,54px);line-height:1;color:var(--ink);margin:4px 0 13px}
.cov-type{display:flex;gap:10px;align-items:flex-start;background:linear-gradient(150deg,rgba(185,134,46,.13),rgba(185,134,46,.05));border:1px solid rgba(185,134,46,.34);border-radius:14px;padding:12px 15px;text-align:left;font-family:var(--sans);font-size:13.5px;color:var(--muted);line-height:1.45}
.cov-type .ti{flex:0 0 auto;width:18px;height:18px;color:var(--gold);margin-top:1px}
.cov-pills{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:14px}
.cp{display:inline-flex;align-items:center;gap:6px;border:1px solid rgba(90,60,20,.3);border-radius:999px;padding:7px 13px;font-family:var(--sans);font-size:12.3px;color:var(--brown)}
.cp .g{color:var(--gold);font-size:13px}
.cov-comfort{font-family:var(--serif);font-style:italic;font-size:16px;color:var(--brown);margin-top:18px;max-width:32ch;line-height:1.45}
.cov-trust{font-family:var(--sans);font-size:10.5px;letter-spacing:.03em;color:var(--brown);opacity:.62;margin-top:14px}

/* summary grid */
.sgrid{display:grid;grid-template-columns:1fr 1fr;gap:9px;width:100%;margin-top:16px}
.scard{background:linear-gradient(162deg,#fff,#FBF5EA);border:1px solid var(--box-line);border-radius:13px;padding:14px 14px;text-align:left;box-shadow:0 3px 12px rgba(70,50,20,.04);display:flex;flex-direction:column;justify-content:center;min-height:114px}
.scard .si{width:30px;height:30px;color:var(--gold);margin-bottom:9px}
.scard .sl{font-family:var(--sans);font-weight:700;font-size:9px;letter-spacing:.06em;text-transform:uppercase;color:var(--mauve)}
.scard .sv{font-family:var(--serif);font-weight:600;font-size:15px;color:var(--ink);margin-top:2px;line-height:1.15}
.scard .ss{font-family:var(--sans);font-size:11px;color:var(--muted);margin-top:5px;line-height:1.4}
.scard.good .si{color:var(--green)}.scard.good .sv{color:var(--green)}
.scard.warn .si{color:var(--terra)}.scard.warn .sv{color:var(--terra)}
.sfoot{width:100%;text-align:left;font-family:var(--sans);font-size:12.5px;color:var(--mauve);font-style:italic;margin-top:9px;line-height:1.45}

/* callouts & accents (light, blend) */
.callout{background:linear-gradient(155deg,#FDF5E1,#F6E9CB);border-radius:13px;padding:14px 17px;margin-top:14px;text-align:left}
.callout.dk{background:linear-gradient(155deg,#3a2b1d,#241812)}
.callout .ch{font-family:var(--serif);font-weight:600;font-size:15px;color:var(--terra);display:flex;align-items:center;gap:8px}
.callout.dk .ch{color:#E4B04A}
.callout .ch .ic{width:17px;height:17px}
.callout p{font-family:var(--sans);font-size:13.3px;color:var(--muted);margin-top:6px;line-height:1.55}
.callout.dk p{color:#DBCEB2}
.verdict{display:inline-flex;align-items:center;gap:8px;font-family:var(--sans);font-weight:700;font-size:13px;color:var(--green);background:linear-gradient(90deg,rgba(62,125,90,.13),rgba(62,125,90,.03));border:1.5px solid var(--green);border-radius:999px;padding:8px 16px;margin:12px 0 2px}
.verdict .ic{width:15px;height:15px}
.verdict.gold{color:var(--gold);background:linear-gradient(90deg,rgba(185,134,46,.14),rgba(185,134,46,.03));border-color:var(--gold)}
.verdict.terra{color:var(--terra);background:linear-gradient(90deg,rgba(180,87,43,.14),rgba(180,87,43,.03));border-color:var(--terra)}
.verdict.sum{display:flex;align-items:flex-start;gap:9px;width:100%;font-size:12.5px;font-weight:600;line-height:1.36;text-align:left;border-radius:15px;padding:10px 15px;margin:12px 0 2px}
.verdict.sum .ic{width:15px;height:15px;margin-top:2px}
.herocard{width:100%;text-align:left;background:linear-gradient(150deg,#E7F1EA,#D4E6DA);border:1px solid #A8CAB5;border-radius:15px;padding:15px 17px;margin-top:8px}
.herocard .hd{font-family:var(--serif);font-weight:600;font-size:17px;color:var(--ink);display:flex;align-items:center;gap:9px;flex-wrap:wrap}
.herocard .hg{font-family:var(--sans);font-weight:700;font-size:10px;letter-spacing:.06em;color:#fff;background:linear-gradient(90deg,#3E7D5A,#5AAA7D);border-radius:999px;padding:3px 10px}
.herocard p{font-family:var(--sans);font-size:13.3px;color:var(--muted);margin-top:7px;line-height:1.55}
.note{width:100%;text-align:left;font-family:var(--sans);font-size:12px;color:var(--mauve);margin-top:13px;line-height:1.5;border-top:1px solid var(--line);padding-top:10px}
.note b{color:var(--body)}
.xlink{display:inline-flex;align-items:center;gap:7px;margin-top:16px;font-family:var(--sans);font-weight:700;font-size:12px;color:var(--gold);text-decoration:none;border-bottom:1px solid #E7D6AB;padding-bottom:2px}

.win{width:100%;text-align:left;padding:12px 0;border-bottom:1px solid var(--line)}
.win:last-of-type{border-bottom:0}
.win .wt{display:flex;justify-content:space-between;align-items:baseline;gap:10px}
.win .wd{font-family:var(--serif);font-weight:600;font-size:16px;color:var(--ink)}
.win .wg{font-family:var(--sans);font-weight:700;font-size:10px;letter-spacing:.05em;padding:4px 10px;border-radius:999px;border:1.5px solid}
.wg.mod{color:var(--gold);border-color:var(--gold)}.wg.build{color:var(--mauve);border-color:var(--mauve)}
.wg.hold{color:var(--muted);border-color:var(--line);border-style:dashed}
.win .wb{font-family:var(--sans);font-size:13px;color:var(--muted);margin-top:5px;line-height:1.5}

.tscroll{width:100%;overflow:hidden;margin-top:12px;border:1px solid var(--box-line);border-radius:12px}
table.k{width:100%;border-collapse:collapse;font-family:var(--sans);font-size:11px;text-align:left}
table.k th{font-family:var(--sans);font-weight:700;font-size:8.5px;letter-spacing:.04em;text-transform:uppercase;color:var(--mauve);padding:7px 9px;background:#FBF3E2;border-bottom:1px solid var(--box-line)}
table.k td{padding:7px 9px;border-bottom:1px solid var(--line);color:var(--muted);vertical-align:top}
table.k tr:last-child td{border-bottom:0}
table.k td:first-child{font-family:var(--serif);font-weight:600;color:var(--ink)}
table.k tr:nth-child(even) td{background:#FCF7EE}
.kundli{display:grid;grid-template-columns:repeat(4,1fr);grid-template-rows:repeat(4,1fr);gap:4px;width:100%;max-width:320px;aspect-ratio:1;margin:12px auto 4px}
.kc{background:linear-gradient(160deg,#fff,#FBF5EA);border:1px solid var(--box-line);border-radius:6px;padding:5px 6px;text-align:left;box-shadow:0 2px 8px rgba(70,50,20,.04);overflow:hidden}
.kc .sn{font-family:var(--sans);font-size:8px;letter-spacing:.03em;text-transform:uppercase;color:var(--faint)}
.kc .pl{font-family:var(--sans);font-weight:600;font-size:10px;color:var(--ink);line-height:1.3;margin-top:2px}
.kc.asc{outline:2px solid var(--gold);outline-offset:-2px}.kc.asc .sn{color:var(--gold)}
.kc.center{background:transparent;box-shadow:none;border:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
.kc.center b{font-family:var(--serif);font-weight:600;font-size:12px;color:var(--ink)}
.kc.center span{font-family:var(--sans);font-size:9px;color:var(--gold)}
.klegend{font-family:var(--sans);font-size:11px;color:var(--mauve);margin-top:8px;text-align:center;line-height:1.45}
.tl{width:100%;text-align:left;border-left:2px solid #E7D6AB;margin-top:12px;padding-left:19px;display:flex;flex-direction:column;gap:12px}
.tli{position:relative}
.tli::before{content:"";position:absolute;left:-25px;top:5px;width:9px;height:9px;border-radius:50%;background:var(--gold);border:2px solid var(--cream)}
.tli.good::before{background:var(--green)}.tli.warn::before{background:var(--terra)}.tli.now::before{background:var(--ink);box-shadow:0 0 0 3px var(--gold-callout)}
.tli .d{font-family:var(--serif);font-weight:600;font-size:14px;color:var(--ink)}
.tli .dt{font-family:var(--sans);font-size:10.5px;color:var(--mauve);font-variant-numeric:tabular-nums}
.tli .th{font-family:var(--sans);font-size:11.8px;color:var(--muted);line-height:1.45}
.tli.good .th b{color:var(--green)}.tli.warn .th b{color:var(--terra)}
.scores{width:100%;text-align:left;margin-top:12px;background:linear-gradient(162deg,#fff,#FBF5EA);border:1px solid var(--box-line);border-radius:13px;padding:6px 16px;box-shadow:0 3px 12px rgba(70,50,20,.04)}
.scores .sr{display:flex;justify-content:space-between;gap:12px;padding:9px 0;border-bottom:1px solid var(--line);font-family:var(--sans);font-size:13px;color:var(--muted)}
.scores .sr:last-child{border-bottom:0}
.scores .sr b{color:var(--ink);font-variant-numeric:tabular-nums}
.scores .sr.tot b{color:var(--green);font-family:var(--serif);font-size:16px}
.reviewbar{background:var(--ink);color:#E7D6AB;font-family:var(--sans);font-size:12px;text-align:center;padding:8px 18px}
.reviewbar b{color:var(--gold2)}

.page.note{background:linear-gradient(160deg,#FBF6EC,#F3EAD6)}.notebox{position:relative;z-index:1;background:rgba(255,253,247,.9);border:1px solid var(--box-line);border-radius:20px;padding:30px 26px;max-width:352px;box-shadow:0 18px 46px rgba(48,34,14,.17);text-align:center}.notebox .ne{font-family:var(--sans);font-weight:700;font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--gold)}.notebox .nh{font-family:var(--serif);font-weight:600;font-size:22px;color:var(--ink);margin-top:8px}.notebox p{font-family:var(--serif);font-size:16px;line-height:1.6;color:var(--ink);margin-top:13px}.notebox .sig{font-family:var(--sans);font-weight:700;font-size:12.5px;letter-spacing:.03em;color:var(--gold);margin-top:17px}
.page:nth-of-type(6n+1)::before{content:'';position:absolute;top:-96px;left:-96px;width:290px;height:290px;opacity:.28;pointer-events:none;z-index:0;background:url("data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%27-172%20-172%20344%20344%27%3E%3Cg%20fill%3D%27none%27%20stroke%3D%27%23b9862e%27%20stroke-width%3D%270.9%27%20opacity%3D%270.85%27%3E%3Ccircle%20r%3D%2716%27%2F%3E%3Ccircle%20r%3D%2726%27%2F%3E%3Ccircle%20r%3D%2748%27%2F%3E%3Ccircle%20r%3D%2788%27%2F%3E%3Ccircle%20r%3D%27120%27%2F%3E%3Ccircle%20r%3D%27150%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2830.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%2830.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2860.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%2860.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28120.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28120.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28150.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28150.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28210.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28210.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28240.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28240.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28300.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28300.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28330.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28330.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%2822.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%2822.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%2845.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%2845.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%2867.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%2867.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28112.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28112.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28135.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28135.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28157.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28157.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28202.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28202.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28225.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28225.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28247.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28247.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28292.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28292.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28315.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28315.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28337.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28337.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%2815.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%2815.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%2830.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%2830.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%2845.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%2845.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%2860.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%2860.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%2875.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%2875.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28105.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28105.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28120.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28120.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28135.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28135.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28150.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28150.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28165.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28165.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28195.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28195.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28210.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28210.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28225.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28225.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28240.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28240.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28255.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28255.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28285.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28285.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28300.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28300.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28315.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28315.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28330.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28330.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28345.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28345.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2811.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2811.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2822.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2822.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2833.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2833.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2845.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2845.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2856.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2856.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2867.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2867.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2878.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2878.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28101.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28101.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28112.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28112.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28123.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28123.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28135.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28135.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28146.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28146.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28157.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28157.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28168.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28168.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28191.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28191.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28202.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28202.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28213.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28213.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28225.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28225.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28236.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28236.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28247.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28247.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28258.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28258.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28281.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28281.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28292.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28292.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28303.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28303.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28315.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28315.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28326.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28326.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28337.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28337.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28348.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28348.8%29%27%2F%3E%3Cpath%20d%3D%27M0.0%20-158.0%20A%2019.0%2019.0%200%200%201%2010.3%20-157.7%27%2F%3E%3Cpath%20d%3D%27M20.6%20-156.6%20A%2019.0%2019.0%200%200%201%2030.8%20-155.0%27%2F%3E%3Cpath%20d%3D%27M40.9%20-152.6%20A%2019.0%2019.0%200%200%201%2050.8%20-149.6%27%2F%3E%3Cpath%20d%3D%27M60.5%20-146.0%20A%2019.0%2019.0%200%200%201%2069.9%20-141.7%27%2F%3E%3Cpath%20d%3D%27M79.0%20-136.8%20A%2019.0%2019.0%200%200%201%2087.8%20-131.4%27%2F%3E%3Cpath%20d%3D%27M96.2%20-125.3%20A%2019.0%2019.0%200%200%201%20104.2%20-118.8%27%2F%3E%3Cpath%20d%3D%27M111.7%20-111.7%20A%2019.0%2019.0%200%200%201%20118.8%20-104.2%27%2F%3E%3Cpath%20d%3D%27M125.3%20-96.2%20A%2019.0%2019.0%200%200%201%20131.4%20-87.8%27%2F%3E%3Cpath%20d%3D%27M136.8%20-79.0%20A%2019.0%2019.0%200%200%201%20141.7%20-69.9%27%2F%3E%3Cpath%20d%3D%27M146.0%20-60.5%20A%2019.0%2019.0%200%200%201%20149.6%20-50.8%27%2F%3E%3Cpath%20d%3D%27M152.6%20-40.9%20A%2019.0%2019.0%200%200%201%20155.0%20-30.8%27%2F%3E%3Cpath%20d%3D%27M156.6%20-20.6%20A%2019.0%2019.0%200%200%201%20157.7%20-10.3%27%2F%3E%3Cpath%20d%3D%27M158.0%20-0.0%20A%2019.0%2019.0%200%200%201%20157.7%2010.3%27%2F%3E%3Cpath%20d%3D%27M156.6%2020.6%20A%2019.0%2019.0%200%200%201%20155.0%2030.8%27%2F%3E%3Cpath%20d%3D%27M152.6%2040.9%20A%2019.0%2019.0%200%200%201%20149.6%2050.8%27%2F%3E%3Cpath%20d%3D%27M146.0%2060.5%20A%2019.0%2019.0%200%200%201%20141.7%2069.9%27%2F%3E%3Cpath%20d%3D%27M136.8%2079.0%20A%2019.0%2019.0%200%200%201%20131.4%2087.8%27%2F%3E%3Cpath%20d%3D%27M125.3%2096.2%20A%2019.0%2019.0%200%200%201%20118.8%20104.2%27%2F%3E%3Cpath%20d%3D%27M111.7%20111.7%20A%2019.0%2019.0%200%200%201%20104.2%20118.8%27%2F%3E%3Cpath%20d%3D%27M96.2%20125.3%20A%2019.0%2019.0%200%200%201%2087.8%20131.4%27%2F%3E%3Cpath%20d%3D%27M79.0%20136.8%20A%2019.0%2019.0%200%200%201%2069.9%20141.7%27%2F%3E%3Cpath%20d%3D%27M60.5%20146.0%20A%2019.0%2019.0%200%200%201%2050.8%20149.6%27%2F%3E%3Cpath%20d%3D%27M40.9%20152.6%20A%2019.0%2019.0%200%200%201%2030.8%20155.0%27%2F%3E%3Cpath%20d%3D%27M20.6%20156.6%20A%2019.0%2019.0%200%200%201%2010.3%20157.7%27%2F%3E%3Cpath%20d%3D%27M0.0%20158.0%20A%2019.0%2019.0%200%200%201%20-10.3%20157.7%27%2F%3E%3Cpath%20d%3D%27M-20.6%20156.6%20A%2019.0%2019.0%200%200%201%20-30.8%20155.0%27%2F%3E%3Cpath%20d%3D%27M-40.9%20152.6%20A%2019.0%2019.0%200%200%201%20-50.8%20149.6%27%2F%3E%3Cpath%20d%3D%27M-60.5%20146.0%20A%2019.0%2019.0%200%200%201%20-69.9%20141.7%27%2F%3E%3Cpath%20d%3D%27M-79.0%20136.8%20A%2019.0%2019.0%200%200%201%20-87.8%20131.4%27%2F%3E%3Cpath%20d%3D%27M-96.2%20125.3%20A%2019.0%2019.0%200%200%201%20-104.2%20118.8%27%2F%3E%3Cpath%20d%3D%27M-111.7%20111.7%20A%2019.0%2019.0%200%200%201%20-118.8%20104.2%27%2F%3E%3Cpath%20d%3D%27M-125.3%2096.2%20A%2019.0%2019.0%200%200%201%20-131.4%2087.8%27%2F%3E%3Cpath%20d%3D%27M-136.8%2079.0%20A%2019.0%2019.0%200%200%201%20-141.7%2069.9%27%2F%3E%3Cpath%20d%3D%27M-146.0%2060.5%20A%2019.0%2019.0%200%200%201%20-149.6%2050.8%27%2F%3E%3Cpath%20d%3D%27M-152.6%2040.9%20A%2019.0%2019.0%200%200%201%20-155.0%2030.8%27%2F%3E%3Cpath%20d%3D%27M-156.6%2020.6%20A%2019.0%2019.0%200%200%201%20-157.7%2010.3%27%2F%3E%3Cpath%20d%3D%27M-158.0%200.0%20A%2019.0%2019.0%200%200%201%20-157.7%20-10.3%27%2F%3E%3Cpath%20d%3D%27M-156.6%20-20.6%20A%2019.0%2019.0%200%200%201%20-155.0%20-30.8%27%2F%3E%3Cpath%20d%3D%27M-152.6%20-40.9%20A%2019.0%2019.0%200%200%201%20-149.6%20-50.8%27%2F%3E%3Cpath%20d%3D%27M-146.0%20-60.5%20A%2019.0%2019.0%200%200%201%20-141.7%20-69.9%27%2F%3E%3Cpath%20d%3D%27M-136.8%20-79.0%20A%2019.0%2019.0%200%200%201%20-131.4%20-87.8%27%2F%3E%3Cpath%20d%3D%27M-125.3%20-96.2%20A%2019.0%2019.0%200%200%201%20-118.8%20-104.2%27%2F%3E%3Cpath%20d%3D%27M-111.7%20-111.7%20A%2019.0%2019.0%200%200%201%20-104.2%20-118.8%27%2F%3E%3Cpath%20d%3D%27M-96.2%20-125.3%20A%2019.0%2019.0%200%200%201%20-87.8%20-131.4%27%2F%3E%3Cpath%20d%3D%27M-79.0%20-136.8%20A%2019.0%2019.0%200%200%201%20-69.9%20-141.7%27%2F%3E%3Cpath%20d%3D%27M-60.5%20-146.0%20A%2019.0%2019.0%200%200%201%20-50.8%20-149.6%27%2F%3E%3Cpath%20d%3D%27M-40.9%20-152.6%20A%2019.0%2019.0%200%200%201%20-30.8%20-155.0%27%2F%3E%3Cpath%20d%3D%27M-20.6%20-156.6%20A%2019.0%2019.0%200%200%201%20-10.3%20-157.7%27%2F%3E%3Cg%20fill%3D%27%23b9862e%27%20stroke%3D%27none%27%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%2830.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%2860.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28120.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28150.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28210.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28240.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28300.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28330.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%2815.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%2830.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%2845.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%2860.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%2875.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28105.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28120.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28135.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28150.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28165.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28195.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28210.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28225.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28240.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28255.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28285.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28300.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28315.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28330.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28345.0%29%27%2F%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fsvg%3E") center/contain no-repeat}.page:nth-of-type(6n+2)::before{content:'';position:absolute;top:20px;right:-34px;width:200px;height:160px;opacity:.55;pointer-events:none;z-index:0;background:url("data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20width%3D%27210%27%20height%3D%27170%27%3E%3Cg%20stroke%3D%27%23b9862e%27%20fill%3D%27%23b9862e%27%20stroke-linecap%3D%27round%27%20opacity%3D%270.9%27%3E%3Ccircle%20cx%3D%2716%27%20cy%3D%27150%27%20r%3D%272.3%27%2F%3E%3Ccircle%20cx%3D%2764%27%20cy%3D%27110%27%20r%3D%272.3%27%2F%3E%3Ccircle%20cx%3D%27110%27%20cy%3D%27132%27%20r%3D%272.3%27%2F%3E%3Ccircle%20cx%3D%27158%27%20cy%3D%2780%27%20r%3D%272.3%27%2F%3E%3Ccircle%20cx%3D%27198%27%20cy%3D%2730%27%20r%3D%272.3%27%2F%3E%3Cpath%20d%3D%27M16%20150%20L64%20110%20L110%20132%20L158%2080%20L198%2030%27%20fill%3D%27none%27%20stroke-width%3D%270.8%27%20stroke-dasharray%3D%273%205%27%2F%3E%3Cpath%20d%3D%27M158%2071v18M149%2080h18%27%20stroke-width%3D%271.3%27%2F%3E%3Cpath%20d%3D%27M198%2021v18M189%2030h18%27%20stroke-width%3D%271.3%27%2F%3E%3C%2Fg%3E%3C%2Fsvg%3E") center/contain no-repeat}.page:nth-of-type(6n+2)::after{content:'';position:absolute;bottom:34px;left:14px;width:60px;height:60px;opacity:.5;pointer-events:none;z-index:0;background:url("data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20width%3D%2760%27%20height%3D%2760%27%3E%3Cg%20fill%3D%27none%27%20stroke%3D%27%23b9862e%27%20stroke-width%3D%271.1%27%3E%3Ccircle%20cx%3D%2730%27%20cy%3D%2730%27%20r%3D%2711%27%2F%3E%3Cellipse%20cx%3D%2730%27%20cy%3D%2730%27%20rx%3D%2719%27%20ry%3D%276%27%20transform%3D%27rotate%28-18%2030%2030%29%27%2F%3E%3C%2Fg%3E%3C%2Fsvg%3E") center/contain no-repeat}.page:nth-of-type(6n+4)::before{content:'';position:absolute;bottom:-80px;right:-80px;width:250px;height:250px;opacity:.26;pointer-events:none;z-index:0;background:url("data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%27-172%20-172%20344%20344%27%3E%3Cg%20fill%3D%27none%27%20stroke%3D%27%23b9862e%27%20stroke-width%3D%270.9%27%20opacity%3D%270.85%27%3E%3Ccircle%20r%3D%2716%27%2F%3E%3Ccircle%20r%3D%2726%27%2F%3E%3Ccircle%20r%3D%2748%27%2F%3E%3Ccircle%20r%3D%2788%27%2F%3E%3Ccircle%20r%3D%27120%27%2F%3E%3Ccircle%20r%3D%27150%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2830.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%2830.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2860.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%2860.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28120.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28120.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28150.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28150.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28210.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28210.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28240.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28240.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28300.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28300.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28330.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28330.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%2822.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%2822.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%2845.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%2845.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%2867.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%2867.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28112.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28112.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28135.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28135.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28157.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28157.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28202.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28202.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28225.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28225.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28247.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28247.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28292.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28292.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28315.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28315.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28337.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28337.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%2815.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%2815.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%2830.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%2830.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%2845.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%2845.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%2860.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%2860.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%2875.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%2875.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28105.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28105.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28120.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28120.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28135.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28135.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28150.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28150.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28165.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28165.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28195.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28195.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28210.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28210.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28225.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28225.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28240.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28240.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28255.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28255.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28285.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28285.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28300.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28300.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28315.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28315.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28330.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28330.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28345.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28345.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2811.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2811.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2822.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2822.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2833.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2833.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2845.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2845.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2856.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2856.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2867.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2867.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2878.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2878.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28101.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28101.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28112.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28112.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28123.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28123.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28135.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28135.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28146.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28146.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28157.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28157.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28168.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28168.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28191.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28191.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28202.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28202.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28213.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28213.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28225.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28225.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28236.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28236.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28247.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28247.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28258.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28258.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28281.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28281.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28292.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28292.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28303.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28303.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28315.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28315.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28326.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28326.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28337.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28337.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28348.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28348.8%29%27%2F%3E%3Cpath%20d%3D%27M0.0%20-158.0%20A%2019.0%2019.0%200%200%201%2010.3%20-157.7%27%2F%3E%3Cpath%20d%3D%27M20.6%20-156.6%20A%2019.0%2019.0%200%200%201%2030.8%20-155.0%27%2F%3E%3Cpath%20d%3D%27M40.9%20-152.6%20A%2019.0%2019.0%200%200%201%2050.8%20-149.6%27%2F%3E%3Cpath%20d%3D%27M60.5%20-146.0%20A%2019.0%2019.0%200%200%201%2069.9%20-141.7%27%2F%3E%3Cpath%20d%3D%27M79.0%20-136.8%20A%2019.0%2019.0%200%200%201%2087.8%20-131.4%27%2F%3E%3Cpath%20d%3D%27M96.2%20-125.3%20A%2019.0%2019.0%200%200%201%20104.2%20-118.8%27%2F%3E%3Cpath%20d%3D%27M111.7%20-111.7%20A%2019.0%2019.0%200%200%201%20118.8%20-104.2%27%2F%3E%3Cpath%20d%3D%27M125.3%20-96.2%20A%2019.0%2019.0%200%200%201%20131.4%20-87.8%27%2F%3E%3Cpath%20d%3D%27M136.8%20-79.0%20A%2019.0%2019.0%200%200%201%20141.7%20-69.9%27%2F%3E%3Cpath%20d%3D%27M146.0%20-60.5%20A%2019.0%2019.0%200%200%201%20149.6%20-50.8%27%2F%3E%3Cpath%20d%3D%27M152.6%20-40.9%20A%2019.0%2019.0%200%200%201%20155.0%20-30.8%27%2F%3E%3Cpath%20d%3D%27M156.6%20-20.6%20A%2019.0%2019.0%200%200%201%20157.7%20-10.3%27%2F%3E%3Cpath%20d%3D%27M158.0%20-0.0%20A%2019.0%2019.0%200%200%201%20157.7%2010.3%27%2F%3E%3Cpath%20d%3D%27M156.6%2020.6%20A%2019.0%2019.0%200%200%201%20155.0%2030.8%27%2F%3E%3Cpath%20d%3D%27M152.6%2040.9%20A%2019.0%2019.0%200%200%201%20149.6%2050.8%27%2F%3E%3Cpath%20d%3D%27M146.0%2060.5%20A%2019.0%2019.0%200%200%201%20141.7%2069.9%27%2F%3E%3Cpath%20d%3D%27M136.8%2079.0%20A%2019.0%2019.0%200%200%201%20131.4%2087.8%27%2F%3E%3Cpath%20d%3D%27M125.3%2096.2%20A%2019.0%2019.0%200%200%201%20118.8%20104.2%27%2F%3E%3Cpath%20d%3D%27M111.7%20111.7%20A%2019.0%2019.0%200%200%201%20104.2%20118.8%27%2F%3E%3Cpath%20d%3D%27M96.2%20125.3%20A%2019.0%2019.0%200%200%201%2087.8%20131.4%27%2F%3E%3Cpath%20d%3D%27M79.0%20136.8%20A%2019.0%2019.0%200%200%201%2069.9%20141.7%27%2F%3E%3Cpath%20d%3D%27M60.5%20146.0%20A%2019.0%2019.0%200%200%201%2050.8%20149.6%27%2F%3E%3Cpath%20d%3D%27M40.9%20152.6%20A%2019.0%2019.0%200%200%201%2030.8%20155.0%27%2F%3E%3Cpath%20d%3D%27M20.6%20156.6%20A%2019.0%2019.0%200%200%201%2010.3%20157.7%27%2F%3E%3Cpath%20d%3D%27M0.0%20158.0%20A%2019.0%2019.0%200%200%201%20-10.3%20157.7%27%2F%3E%3Cpath%20d%3D%27M-20.6%20156.6%20A%2019.0%2019.0%200%200%201%20-30.8%20155.0%27%2F%3E%3Cpath%20d%3D%27M-40.9%20152.6%20A%2019.0%2019.0%200%200%201%20-50.8%20149.6%27%2F%3E%3Cpath%20d%3D%27M-60.5%20146.0%20A%2019.0%2019.0%200%200%201%20-69.9%20141.7%27%2F%3E%3Cpath%20d%3D%27M-79.0%20136.8%20A%2019.0%2019.0%200%200%201%20-87.8%20131.4%27%2F%3E%3Cpath%20d%3D%27M-96.2%20125.3%20A%2019.0%2019.0%200%200%201%20-104.2%20118.8%27%2F%3E%3Cpath%20d%3D%27M-111.7%20111.7%20A%2019.0%2019.0%200%200%201%20-118.8%20104.2%27%2F%3E%3Cpath%20d%3D%27M-125.3%2096.2%20A%2019.0%2019.0%200%200%201%20-131.4%2087.8%27%2F%3E%3Cpath%20d%3D%27M-136.8%2079.0%20A%2019.0%2019.0%200%200%201%20-141.7%2069.9%27%2F%3E%3Cpath%20d%3D%27M-146.0%2060.5%20A%2019.0%2019.0%200%200%201%20-149.6%2050.8%27%2F%3E%3Cpath%20d%3D%27M-152.6%2040.9%20A%2019.0%2019.0%200%200%201%20-155.0%2030.8%27%2F%3E%3Cpath%20d%3D%27M-156.6%2020.6%20A%2019.0%2019.0%200%200%201%20-157.7%2010.3%27%2F%3E%3Cpath%20d%3D%27M-158.0%200.0%20A%2019.0%2019.0%200%200%201%20-157.7%20-10.3%27%2F%3E%3Cpath%20d%3D%27M-156.6%20-20.6%20A%2019.0%2019.0%200%200%201%20-155.0%20-30.8%27%2F%3E%3Cpath%20d%3D%27M-152.6%20-40.9%20A%2019.0%2019.0%200%200%201%20-149.6%20-50.8%27%2F%3E%3Cpath%20d%3D%27M-146.0%20-60.5%20A%2019.0%2019.0%200%200%201%20-141.7%20-69.9%27%2F%3E%3Cpath%20d%3D%27M-136.8%20-79.0%20A%2019.0%2019.0%200%200%201%20-131.4%20-87.8%27%2F%3E%3Cpath%20d%3D%27M-125.3%20-96.2%20A%2019.0%2019.0%200%200%201%20-118.8%20-104.2%27%2F%3E%3Cpath%20d%3D%27M-111.7%20-111.7%20A%2019.0%2019.0%200%200%201%20-104.2%20-118.8%27%2F%3E%3Cpath%20d%3D%27M-96.2%20-125.3%20A%2019.0%2019.0%200%200%201%20-87.8%20-131.4%27%2F%3E%3Cpath%20d%3D%27M-79.0%20-136.8%20A%2019.0%2019.0%200%200%201%20-69.9%20-141.7%27%2F%3E%3Cpath%20d%3D%27M-60.5%20-146.0%20A%2019.0%2019.0%200%200%201%20-50.8%20-149.6%27%2F%3E%3Cpath%20d%3D%27M-40.9%20-152.6%20A%2019.0%2019.0%200%200%201%20-30.8%20-155.0%27%2F%3E%3Cpath%20d%3D%27M-20.6%20-156.6%20A%2019.0%2019.0%200%200%201%20-10.3%20-157.7%27%2F%3E%3Cg%20fill%3D%27%23b9862e%27%20stroke%3D%27none%27%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%2830.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%2860.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28120.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28150.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28210.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28240.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28300.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28330.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%2815.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%2830.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%2845.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%2860.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%2875.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28105.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28120.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28135.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28150.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28165.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28195.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28210.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28225.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28240.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28255.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28285.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28300.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28315.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28330.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28345.0%29%27%2F%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fsvg%3E") center/contain no-repeat}.page:nth-of-type(6n+5)::before{content:'';position:absolute;top:38%;left:-46px;width:210px;height:180px;opacity:.5;pointer-events:none;z-index:0;background:url("data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20width%3D%27200%27%20height%3D%27180%27%3E%3Cg%20stroke%3D%27%23b9862e%27%20fill%3D%27%23b9862e%27%20stroke-linecap%3D%27round%27%20opacity%3D%270.9%27%3E%3Ccircle%20cx%3D%2720%27%20cy%3D%2730%27%20r%3D%272.3%27%2F%3E%3Ccircle%20cx%3D%2770%27%20cy%3D%2770%27%20r%3D%272.3%27%2F%3E%3Ccircle%20cx%3D%2760%27%20cy%3D%27120%27%20r%3D%272.3%27%2F%3E%3Ccircle%20cx%3D%27120%27%20cy%3D%27140%27%20r%3D%272.3%27%2F%3E%3Ccircle%20cx%3D%27170%27%20cy%3D%2796%27%20r%3D%272.3%27%2F%3E%3Ccircle%20cx%3D%27196%27%20cy%3D%27150%27%20r%3D%272.3%27%2F%3E%3Cpath%20d%3D%27M20%2030%20L70%2070%20L60%20120%20L120%20140%20L170%2096%20L196%20150%27%20fill%3D%27none%27%20stroke-width%3D%270.8%27%20stroke-dasharray%3D%273%205%27%2F%3E%3Cpath%20d%3D%27M70%2061v18M61%2070h18%27%20stroke-width%3D%271.3%27%2F%3E%3Cpath%20d%3D%27M170%2087v18M161%2096h18%27%20stroke-width%3D%271.3%27%2F%3E%3C%2Fg%3E%3C%2Fsvg%3E") center/contain no-repeat}.page:nth-of-type(6n+3)::after{content:'';position:absolute;top:30px;right:26px;width:26px;height:26px;opacity:.5;pointer-events:none;z-index:0;background:url("data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20width%3D%2726%27%20height%3D%2726%27%3E%3Cpath%20d%3D%27M13%202v22M2%2013h22M6%206l14%2014M20%206L6%2020%27%20stroke%3D%27%23b9862e%27%20stroke-width%3D%271%27%2F%3E%3C%2Fsvg%3E") center/contain no-repeat}.page:nth-of-type(6n)::before{content:'';position:absolute;bottom:20px;left:50%;transform:translateX(-50%);width:230px;height:150px;opacity:.42;pointer-events:none;z-index:0;background:url("data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20width%3D%27210%27%20height%3D%27170%27%3E%3Cg%20stroke%3D%27%23b9862e%27%20fill%3D%27%23b9862e%27%20stroke-linecap%3D%27round%27%20opacity%3D%270.9%27%3E%3Ccircle%20cx%3D%2716%27%20cy%3D%27150%27%20r%3D%272.3%27%2F%3E%3Ccircle%20cx%3D%2764%27%20cy%3D%27110%27%20r%3D%272.3%27%2F%3E%3Ccircle%20cx%3D%27110%27%20cy%3D%27132%27%20r%3D%272.3%27%2F%3E%3Ccircle%20cx%3D%27158%27%20cy%3D%2780%27%20r%3D%272.3%27%2F%3E%3Ccircle%20cx%3D%27198%27%20cy%3D%2730%27%20r%3D%272.3%27%2F%3E%3Cpath%20d%3D%27M16%20150%20L64%20110%20L110%20132%20L158%2080%20L198%2030%27%20fill%3D%27none%27%20stroke-width%3D%270.8%27%20stroke-dasharray%3D%273%205%27%2F%3E%3Cpath%20d%3D%27M158%2071v18M149%2080h18%27%20stroke-width%3D%271.3%27%2F%3E%3Cpath%20d%3D%27M198%2021v18M189%2030h18%27%20stroke-width%3D%271.3%27%2F%3E%3C%2Fg%3E%3C%2Fsvg%3E") bottom center/contain no-repeat}.page.note::before{content:none}.page.note::after{content:none}.page.end::before{content:'';position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:346px;height:346px;opacity:.24;pointer-events:none;z-index:0;background:url("data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%27-172%20-172%20344%20344%27%3E%3Cg%20fill%3D%27none%27%20stroke%3D%27%23b9862e%27%20stroke-width%3D%270.9%27%20opacity%3D%270.85%27%3E%3Ccircle%20r%3D%2716%27%2F%3E%3Ccircle%20r%3D%2726%27%2F%3E%3Ccircle%20r%3D%2748%27%2F%3E%3Ccircle%20r%3D%2788%27%2F%3E%3Ccircle%20r%3D%27120%27%2F%3E%3Ccircle%20r%3D%27150%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2830.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%2830.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2860.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%2860.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28120.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28120.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28150.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28150.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28210.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28210.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28240.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28240.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28300.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28300.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-37.0%20-7.0%20-41.0%200%20-48.0%20C%207.0%20-41.0%207.0%20-37.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28330.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-30.0%20C%20-3.5%20-37.2%20-3.5%20-41.0%200%20-44.5%20C%203.5%20-41.0%203.5%20-37.2%200%20-30.0%20Z%27%20transform%3D%27rotate%28330.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%2822.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%2822.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%2845.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%2845.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%2867.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%2867.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28112.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28112.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28135.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28135.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28157.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28157.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28202.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28202.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28225.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28225.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28247.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28247.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28292.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28292.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28315.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28315.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-48.0%20C%20-9.0%20-68.0%20-9.0%20-79.0%200%20-88.0%20C%209.0%20-79.0%209.0%20-68.0%200%20-48.0%20Z%27%20transform%3D%27rotate%28337.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-55.2%20C%20-4.5%20-68.4%20-4.5%20-77.1%200%20-81.6%20C%204.5%20-77.1%204.5%20-68.4%200%20-55.2%20Z%27%20transform%3D%27rotate%28337.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%2815.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%2815.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%2830.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%2830.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%2845.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%2845.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%2860.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%2860.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%2875.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%2875.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28105.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28105.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28120.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28120.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28135.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28135.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28150.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28150.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28165.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28165.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28195.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28195.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28210.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28210.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28225.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28225.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28240.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28240.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28255.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28255.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28285.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28285.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28300.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28300.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28315.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28315.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28330.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28330.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-88.0%20C%20-8.0%20-104.0%20-8.0%20-112.0%200%20-120.0%20C%208.0%20-112.0%208.0%20-104.0%200%20-88.0%20Z%27%20transform%3D%27rotate%28345.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-93.8%20C%20-4.0%20-104.3%20-4.0%20-110.9%200%20-114.9%20C%204.0%20-110.9%204.0%20-104.3%200%20-93.8%20Z%27%20transform%3D%27rotate%28345.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2811.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2811.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2822.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2822.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2833.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2833.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2845.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2845.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2856.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2856.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2867.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2867.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2878.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2878.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28101.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28101.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28112.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28112.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28123.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28123.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28135.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28135.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28146.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28146.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28157.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28157.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28168.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28168.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28191.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28191.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28202.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28202.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28213.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28213.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28225.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28225.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28236.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28236.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28247.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28247.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28258.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28258.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28281.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28281.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28292.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28292.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28303.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28303.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28315.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28315.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28326.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28326.2%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28337.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28337.5%29%27%2F%3E%3Cpath%20d%3D%27M0%20-120.0%20C%20-6.0%20-135.0%20-6.0%20-144.0%200%20-150.0%20C%206.0%20-144.0%206.0%20-135.0%200%20-120.0%20Z%27%20transform%3D%27rotate%28348.8%29%27%2F%3E%3Cpath%20d%3D%27M0%20-125.4%20C%20-3.0%20-135.3%20-3.0%20-142.2%200%20-145.2%20C%203.0%20-142.2%203.0%20-135.3%200%20-125.4%20Z%27%20transform%3D%27rotate%28348.8%29%27%2F%3E%3Cpath%20d%3D%27M0.0%20-158.0%20A%2019.0%2019.0%200%200%201%2010.3%20-157.7%27%2F%3E%3Cpath%20d%3D%27M20.6%20-156.6%20A%2019.0%2019.0%200%200%201%2030.8%20-155.0%27%2F%3E%3Cpath%20d%3D%27M40.9%20-152.6%20A%2019.0%2019.0%200%200%201%2050.8%20-149.6%27%2F%3E%3Cpath%20d%3D%27M60.5%20-146.0%20A%2019.0%2019.0%200%200%201%2069.9%20-141.7%27%2F%3E%3Cpath%20d%3D%27M79.0%20-136.8%20A%2019.0%2019.0%200%200%201%2087.8%20-131.4%27%2F%3E%3Cpath%20d%3D%27M96.2%20-125.3%20A%2019.0%2019.0%200%200%201%20104.2%20-118.8%27%2F%3E%3Cpath%20d%3D%27M111.7%20-111.7%20A%2019.0%2019.0%200%200%201%20118.8%20-104.2%27%2F%3E%3Cpath%20d%3D%27M125.3%20-96.2%20A%2019.0%2019.0%200%200%201%20131.4%20-87.8%27%2F%3E%3Cpath%20d%3D%27M136.8%20-79.0%20A%2019.0%2019.0%200%200%201%20141.7%20-69.9%27%2F%3E%3Cpath%20d%3D%27M146.0%20-60.5%20A%2019.0%2019.0%200%200%201%20149.6%20-50.8%27%2F%3E%3Cpath%20d%3D%27M152.6%20-40.9%20A%2019.0%2019.0%200%200%201%20155.0%20-30.8%27%2F%3E%3Cpath%20d%3D%27M156.6%20-20.6%20A%2019.0%2019.0%200%200%201%20157.7%20-10.3%27%2F%3E%3Cpath%20d%3D%27M158.0%20-0.0%20A%2019.0%2019.0%200%200%201%20157.7%2010.3%27%2F%3E%3Cpath%20d%3D%27M156.6%2020.6%20A%2019.0%2019.0%200%200%201%20155.0%2030.8%27%2F%3E%3Cpath%20d%3D%27M152.6%2040.9%20A%2019.0%2019.0%200%200%201%20149.6%2050.8%27%2F%3E%3Cpath%20d%3D%27M146.0%2060.5%20A%2019.0%2019.0%200%200%201%20141.7%2069.9%27%2F%3E%3Cpath%20d%3D%27M136.8%2079.0%20A%2019.0%2019.0%200%200%201%20131.4%2087.8%27%2F%3E%3Cpath%20d%3D%27M125.3%2096.2%20A%2019.0%2019.0%200%200%201%20118.8%20104.2%27%2F%3E%3Cpath%20d%3D%27M111.7%20111.7%20A%2019.0%2019.0%200%200%201%20104.2%20118.8%27%2F%3E%3Cpath%20d%3D%27M96.2%20125.3%20A%2019.0%2019.0%200%200%201%2087.8%20131.4%27%2F%3E%3Cpath%20d%3D%27M79.0%20136.8%20A%2019.0%2019.0%200%200%201%2069.9%20141.7%27%2F%3E%3Cpath%20d%3D%27M60.5%20146.0%20A%2019.0%2019.0%200%200%201%2050.8%20149.6%27%2F%3E%3Cpath%20d%3D%27M40.9%20152.6%20A%2019.0%2019.0%200%200%201%2030.8%20155.0%27%2F%3E%3Cpath%20d%3D%27M20.6%20156.6%20A%2019.0%2019.0%200%200%201%2010.3%20157.7%27%2F%3E%3Cpath%20d%3D%27M0.0%20158.0%20A%2019.0%2019.0%200%200%201%20-10.3%20157.7%27%2F%3E%3Cpath%20d%3D%27M-20.6%20156.6%20A%2019.0%2019.0%200%200%201%20-30.8%20155.0%27%2F%3E%3Cpath%20d%3D%27M-40.9%20152.6%20A%2019.0%2019.0%200%200%201%20-50.8%20149.6%27%2F%3E%3Cpath%20d%3D%27M-60.5%20146.0%20A%2019.0%2019.0%200%200%201%20-69.9%20141.7%27%2F%3E%3Cpath%20d%3D%27M-79.0%20136.8%20A%2019.0%2019.0%200%200%201%20-87.8%20131.4%27%2F%3E%3Cpath%20d%3D%27M-96.2%20125.3%20A%2019.0%2019.0%200%200%201%20-104.2%20118.8%27%2F%3E%3Cpath%20d%3D%27M-111.7%20111.7%20A%2019.0%2019.0%200%200%201%20-118.8%20104.2%27%2F%3E%3Cpath%20d%3D%27M-125.3%2096.2%20A%2019.0%2019.0%200%200%201%20-131.4%2087.8%27%2F%3E%3Cpath%20d%3D%27M-136.8%2079.0%20A%2019.0%2019.0%200%200%201%20-141.7%2069.9%27%2F%3E%3Cpath%20d%3D%27M-146.0%2060.5%20A%2019.0%2019.0%200%200%201%20-149.6%2050.8%27%2F%3E%3Cpath%20d%3D%27M-152.6%2040.9%20A%2019.0%2019.0%200%200%201%20-155.0%2030.8%27%2F%3E%3Cpath%20d%3D%27M-156.6%2020.6%20A%2019.0%2019.0%200%200%201%20-157.7%2010.3%27%2F%3E%3Cpath%20d%3D%27M-158.0%200.0%20A%2019.0%2019.0%200%200%201%20-157.7%20-10.3%27%2F%3E%3Cpath%20d%3D%27M-156.6%20-20.6%20A%2019.0%2019.0%200%200%201%20-155.0%20-30.8%27%2F%3E%3Cpath%20d%3D%27M-152.6%20-40.9%20A%2019.0%2019.0%200%200%201%20-149.6%20-50.8%27%2F%3E%3Cpath%20d%3D%27M-146.0%20-60.5%20A%2019.0%2019.0%200%200%201%20-141.7%20-69.9%27%2F%3E%3Cpath%20d%3D%27M-136.8%20-79.0%20A%2019.0%2019.0%200%200%201%20-131.4%20-87.8%27%2F%3E%3Cpath%20d%3D%27M-125.3%20-96.2%20A%2019.0%2019.0%200%200%201%20-118.8%20-104.2%27%2F%3E%3Cpath%20d%3D%27M-111.7%20-111.7%20A%2019.0%2019.0%200%200%201%20-104.2%20-118.8%27%2F%3E%3Cpath%20d%3D%27M-96.2%20-125.3%20A%2019.0%2019.0%200%200%201%20-87.8%20-131.4%27%2F%3E%3Cpath%20d%3D%27M-79.0%20-136.8%20A%2019.0%2019.0%200%200%201%20-69.9%20-141.7%27%2F%3E%3Cpath%20d%3D%27M-60.5%20-146.0%20A%2019.0%2019.0%200%200%201%20-50.8%20-149.6%27%2F%3E%3Cpath%20d%3D%27M-40.9%20-152.6%20A%2019.0%2019.0%200%200%201%20-30.8%20-155.0%27%2F%3E%3Cpath%20d%3D%27M-20.6%20-156.6%20A%2019.0%2019.0%200%200%201%20-10.3%20-157.7%27%2F%3E%3Cg%20fill%3D%27%23b9862e%27%20stroke%3D%27none%27%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%2830.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%2860.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28120.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28150.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28210.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28240.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28300.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-36%27%20r%3D%271.8%27%20transform%3D%27rotate%28330.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%2815.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%2830.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%2845.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%2860.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%2875.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28105.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28120.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28135.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28150.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28165.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28195.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28210.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28225.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28240.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28255.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28285.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28300.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28315.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28330.0%29%27%2F%3E%3Ccircle%20cx%3D%270%27%20cy%3D%27-104%27%20r%3D%271.8%27%20transform%3D%27rotate%28345.0%29%27%2F%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fsvg%3E") center/contain no-repeat}.page.end::after{content:'';position:absolute;bottom:26px;right:24px;width:150px;height:120px;opacity:.5;pointer-events:none;z-index:0;background:url("data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20width%3D%27210%27%20height%3D%27170%27%3E%3Cg%20stroke%3D%27%23b9862e%27%20fill%3D%27%23b9862e%27%20stroke-linecap%3D%27round%27%20opacity%3D%270.9%27%3E%3Ccircle%20cx%3D%2716%27%20cy%3D%27150%27%20r%3D%272.3%27%2F%3E%3Ccircle%20cx%3D%2764%27%20cy%3D%27110%27%20r%3D%272.3%27%2F%3E%3Ccircle%20cx%3D%27110%27%20cy%3D%27132%27%20r%3D%272.3%27%2F%3E%3Ccircle%20cx%3D%27158%27%20cy%3D%2780%27%20r%3D%272.3%27%2F%3E%3Ccircle%20cx%3D%27198%27%20cy%3D%2730%27%20r%3D%272.3%27%2F%3E%3Cpath%20d%3D%27M16%20150%20L64%20110%20L110%20132%20L158%2080%20L198%2030%27%20fill%3D%27none%27%20stroke-width%3D%270.8%27%20stroke-dasharray%3D%273%205%27%2F%3E%3Cpath%20d%3D%27M158%2071v18M149%2080h18%27%20stroke-width%3D%271.3%27%2F%3E%3Cpath%20d%3D%27M198%2021v18M189%2030h18%27%20stroke-width%3D%271.3%27%2F%3E%3C%2Fg%3E%3C%2Fsvg%3E") bottom right/contain no-repeat}
.svc{width:100%;text-align:left;margin-top:16px;display:flex;flex-direction:column;gap:13px}.svc .s{display:flex;gap:12px;align-items:flex-start}.svc .s .si{flex:0 0 auto;width:22px;height:22px;color:var(--gold);margin-top:1px}.svc .s .st{font-family:var(--sans);font-size:13px;color:var(--muted);line-height:1.45}.svc .s .st b{font-family:var(--serif);font-weight:600;font-size:14.5px;color:var(--ink);display:block}.endbrand{font-family:var(--serif);font-style:italic;font-size:15px;color:var(--brown);margin-top:20px;line-height:1.5}
.page.note{background:url("data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20width%3D%27224%27%20height%3D%27224%27%20viewBox%3D%270%200%20224%20224%27%3E%3Cg%20transform%3D%27translate%28112.0%20112.0%29%27%3E%3Cg%20fill%3D%27none%27%20stroke%3D%27%23b78a2e%27%20stroke-width%3D%271.1%27%20opacity%3D%270.3%27%3E%3Ccircle%20r%3D%2714%27%2F%3E%3Ccircle%20r%3D%2726%27%2F%3E%3Ccircle%20r%3D%2754%27%2F%3E%3Ccircle%20r%3D%2792%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2830.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2860.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28120.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28150.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28210.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28240.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28300.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28330.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2818.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2836.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2854.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2872.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28108.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28126.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28144.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28162.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28198.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28216.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28234.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28252.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28288.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28306.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28324.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28342.0%29%27%2F%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20transform%3D%27translate%280%200%29%27%3E%3Cg%20fill%3D%27none%27%20stroke%3D%27%23b78a2e%27%20stroke-width%3D%271.1%27%20opacity%3D%270.3%27%3E%3Ccircle%20r%3D%2714%27%2F%3E%3Ccircle%20r%3D%2726%27%2F%3E%3Ccircle%20r%3D%2754%27%2F%3E%3Ccircle%20r%3D%2792%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2830.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2860.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28120.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28150.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28210.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28240.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28300.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28330.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2818.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2836.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2854.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2872.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28108.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28126.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28144.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28162.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28198.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28216.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28234.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28252.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28288.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28306.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28324.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28342.0%29%27%2F%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20transform%3D%27translate%28224%200%29%27%3E%3Cg%20fill%3D%27none%27%20stroke%3D%27%23b78a2e%27%20stroke-width%3D%271.1%27%20opacity%3D%270.3%27%3E%3Ccircle%20r%3D%2714%27%2F%3E%3Ccircle%20r%3D%2726%27%2F%3E%3Ccircle%20r%3D%2754%27%2F%3E%3Ccircle%20r%3D%2792%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2830.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2860.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28120.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28150.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28210.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28240.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28300.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28330.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2818.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2836.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2854.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2872.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28108.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28126.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28144.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28162.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28198.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28216.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28234.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28252.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28288.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28306.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28324.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28342.0%29%27%2F%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20transform%3D%27translate%280%20224%29%27%3E%3Cg%20fill%3D%27none%27%20stroke%3D%27%23b78a2e%27%20stroke-width%3D%271.1%27%20opacity%3D%270.3%27%3E%3Ccircle%20r%3D%2714%27%2F%3E%3Ccircle%20r%3D%2726%27%2F%3E%3Ccircle%20r%3D%2754%27%2F%3E%3Ccircle%20r%3D%2792%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2830.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2860.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28120.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28150.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28210.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28240.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28300.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28330.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2818.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2836.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2854.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2872.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28108.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28126.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28144.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28162.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28198.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28216.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28234.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28252.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28288.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28306.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28324.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28342.0%29%27%2F%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20transform%3D%27translate%28224%20224%29%27%3E%3Cg%20fill%3D%27none%27%20stroke%3D%27%23b78a2e%27%20stroke-width%3D%271.1%27%20opacity%3D%270.3%27%3E%3Ccircle%20r%3D%2714%27%2F%3E%3Ccircle%20r%3D%2726%27%2F%3E%3Ccircle%20r%3D%2754%27%2F%3E%3Ccircle%20r%3D%2792%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2830.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2860.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28120.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28150.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28210.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28240.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28300.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-26.0%20C%20-7.0%20-40.0%20-7.0%20-47.0%200%20-54.0%20C%207.0%20-47.0%207.0%20-40.0%200%20-26.0%20Z%27%20transform%3D%27rotate%28330.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%280.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2818.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2836.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2854.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2872.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%2890.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28108.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28126.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28144.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28162.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28180.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28198.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28216.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28234.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28252.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28270.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28288.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28306.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28324.0%29%27%2F%3E%3Cpath%20d%3D%27M0%20-54.0%20C%20-7.0%20-73.0%20-7.0%20-85.0%200%20-92.0%20C%207.0%20-85.0%207.0%20-73.0%200%20-54.0%20Z%27%20transform%3D%27rotate%28342.0%29%27%2F%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fsvg%3E") repeat center/224px 224px,linear-gradient(160deg,#FBF6EC,#F4EBD7)}.noteframe{position:relative;z-index:2;background:rgba(251,247,238,.94);border:2px solid var(--gold);padding:38px 26px 34px;max-width:330px;box-shadow:0 0 0 6px rgba(251,247,238,.94),0 16px 42px rgba(48,34,14,.15);text-align:center}.noteframe::before{content:'';position:absolute;inset:7px;border:1px solid var(--gold);opacity:.55;pointer-events:none}.noteframe .fan{position:absolute;left:50%;transform:translateX(-50%);width:52px;height:28px;z-index:1;color:var(--gold)}.noteframe .fan.nftop{top:-15px}.noteframe .fan.nfbot{bottom:-15px;transform:translateX(-50%) rotate(180deg)}.noteframe .crn{position:absolute;width:14px;height:14px;z-index:7;pointer-events:none;display:block;overflow:visible}.noteframe .crn.ctl{top:0;left:0;transform:translate(-50%,-50%)}.noteframe .crn.ctr{top:0;right:0;transform:translate(50%,-50%)}.noteframe .crn.cbl{bottom:0;left:0;transform:translate(-50%,50%)}.noteframe .crn.cbr{bottom:0;right:0;transform:translate(50%,50%)}.noteframe .ne{font-family:var(--sans);font-weight:700;font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--gold)}.noteframe .nh{font-family:var(--serif);font-weight:600;font-size:21px;color:var(--ink);margin-top:6px}.noteframe p{font-family:var(--serif);font-size:15px;line-height:1.55;color:var(--ink);margin-top:12px}.noteframe .sig{font-family:var(--sans);font-weight:700;font-size:12px;letter-spacing:.03em;color:var(--gold);margin-top:15px}
@media print{
  @page{size:430px 830px;margin:0}
  html,body{background:#fff!important;padding:0!important;margin:0}
  .reviewbar{display:none!important}
  .page{width:430px!important;max-width:none!important;min-height:830px;height:830px;margin:0!important;border-radius:0!important;box-shadow:none!important;overflow:hidden;break-inside:avoid;break-after:page;page-break-inside:avoid;page-break-after:always}
  .page:last-of-type{break-after:auto;page-break-after:avoid}
}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
/* Devanagari word-gap fix: zero letter-spacing on every letter-spaced label in the Hindi render (guarded by lang="hi"; English unaffected) */
html[lang="hi"] .eyebrow,html[lang="hi"] h2.head,html[lang="hi"] .cov-brand,html[lang="hi"] .cov-trust,html[lang="hi"] .sl,html[lang="hi"] .hg,html[lang="hi"] .wg,html[lang="hi"] table.k th,html[lang="hi"] .sn,html[lang="hi"] .ne,html[lang="hi"] .sig,html[lang="hi"] .reviewbar,html[lang="hi"] #ax-stickybar a{letter-spacing:0}
/* Life Blueprint wheel + tag-cards -- additive only, new class names, never
   redefines .pt/.scard/.callout/.verdict (render_vyapar shares those). */
.wheelchart{width:100%;max-width:270px;margin:10px auto 2px;display:block}
.tcard{width:100%;text-align:left;background:#fff;border:1.5px solid var(--box-line);
  border-left:5px solid var(--gold);border-radius:12px;padding:15px 16px;margin-top:16px}
.tcard.good{border-left-color:var(--green)}
.tcard.warn{border-left-color:var(--terra)}
.tcard .verdict{margin-top:0}
.tcard .pts{margin-top:14px;gap:14px}
.dwcard{width:100%;text-align:left;background:var(--gold-callout);border-radius:12px;
  padding:12px 14px;margin-top:10px;display:flex;flex-direction:column;gap:10px}
.dwrow{display:flex;gap:10px;align-items:flex-start;font-size:13.5px}
.dwrow .tx b{display:block;font-family:var(--sans);font-weight:700;font-size:11px;
  letter-spacing:.04em;text-transform:uppercase;margin-bottom:2px}
.dwrow.do .pi{color:var(--green)}.dwrow.do .tx b{color:var(--green)}
.dwrow.watch .pi{color:var(--terra)}.dwrow.watch .tx b{color:var(--terra)}
.reflect{width:100%;text-align:left;font-family:var(--serif);font-style:italic;
  font-size:14.5px;color:var(--body);line-height:1.5;margin-top:12px;
  border-top:1px solid var(--line);padding-top:11px}'''

_VYAPAR_DEFS = r'''<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
<symbol id="i-scales" viewBox="0 0 24 24"><path d="M12 3v18M6 21h12M5 6h14M5 6l-2.5 6a2.7 2.7 0 0 0 5 0zM19 6l2.5 6a2.7 2.7 0 0 1-5 0z"/></symbol>
<symbol id="i-store" viewBox="0 0 24 24"><path d="M4 9l1.2-4h13.6L20 9M4 9h16v10H4zM9 19v-5h6v5"/><path d="M4 9a2 2 0 0 0 4 0 2 2 0 0 0 4 0 2 2 0 0 0 4 0 2 2 0 0 0 4 0"/></symbol>
<symbol id="i-people" viewBox="0 0 24 24"><circle cx="9" cy="9" r="3"/><circle cx="16" cy="10" r="2.5"/><path d="M3.5 19a5.5 5.5 0 0 1 11 0M14.5 19a4.5 4.5 0 0 1 6 0"/></symbol>
<symbol id="i-clock" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/></symbol>
<symbol id="i-hourglass" viewBox="0 0 24 24"><path d="M6 3h12M6 21h12M8 3v3l4 5 4-5V3M8 21v-3l4-5 4 5v3"/></symbol>
<symbol id="i-trend" viewBox="0 0 24 24"><path d="M3 17l6-6 4 4 8-8M15 7h6v6"/></symbol>
<symbol id="i-coins" viewBox="0 0 24 24"><ellipse cx="8" cy="7" rx="5" ry="2.5"/><path d="M3 7v4c0 1.4 2.2 2.5 5 2.5s5-1.1 5-2.5V7"/><ellipse cx="16" cy="15" rx="5" ry="2.5"/><path d="M11 15v4c0 1.4 2.2 2.5 5 2.5s5-1.1 5-2.5v-4"/></symbol>
<symbol id="i-target" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none"/></symbol>
<symbol id="i-alert" viewBox="0 0 24 24"><path d="M12 4l8.5 15h-17z"/><path d="M12 10v4M12 17h.01"/></symbol>
<symbol id="i-moon" viewBox="0 0 24 24"><path d="M20 14.5A8 8 0 1 1 11 3.2 6.3 6.3 0 0 0 20 14.5z"/></symbol>
<symbol id="i-saturn" viewBox="0 0 24 24"><circle cx="12" cy="12" r="5.5"/><ellipse cx="12" cy="12" rx="10.5" ry="3.6" transform="rotate(-20 12 12)"/></symbol>
<symbol id="i-shield" viewBox="0 0 24 24"><path d="M12 3l8 3v5.5c0 5-3.6 7.8-8 9-4.4-1.2-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/></symbol>
<symbol id="i-gem" viewBox="0 0 24 24"><path d="M6 3h12l3 5-9 12L3 8z"/><path d="M3 8h18M9 3l3 5 3-5M12 8v12"/></symbol>
<symbol id="i-check" viewBox="0 0 24 24"><path d="M4 12l5 5 11-11"/></symbol>
<symbol id="i-book" viewBox="0 0 24 24"><path d="M4 5a2 2 0 0 1 2-2h6v16H6a2 2 0 0 0-2 2zM20 5a2 2 0 0 0-2-2h-6v16h6a2 2 0 0 1 2 2z"/></symbol>
<symbol id="i-compass" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M15.5 8.5l-2 5-5 2 2-5z"/></symbol>
</defs></svg>'''


# ============================================================ VYAPAR RENDERER
# Business-growth report (/vyapar). 29-page "card per page" portrait layout
# (design ratified as vyapar-v17). The CSS/@page/SVG-defs blocks above
# (_VYAPAR_CSS, _VYAPAR_DEFS) are the v17 design verbatim; this renderer fills
# every data slot from compute_vyapar()'s payload. LLM narrative prose is used
# where present, with the deterministic compute copy as the fallback — the same
# `narr(p, key) or <bank text>` mechanism render_milan uses (report_view.py:1573,
#   el_text = narr(p, "combined_energy") or el["text"]).
VY_SIGN_EN = {"Mesha": "Aries", "Vrishabha": "Taurus", "Mithuna": "Gemini",
              "Karka": "Cancer", "Simha": "Leo", "Kanya": "Virgo",
              "Tula": "Libra", "Vrishchika": "Scorpio", "Dhanu": "Sagittarius",
              "Makara": "Capricorn", "Kumbha": "Aquarius", "Meena": "Pisces"}
VY_TONE_CLASS = {"good": "good", "warn": "warn", "neutral": ""}
VY_TLI = {"good": "good", "warn": "warn", "neutral": ""}
VY_SUMMARY_ICON = {"Your type": "i-scales", "Best-fit line": "i-store",
                   "Solo or partner": "i-people", "Last 3 years": "i-clock",
                   "Right now": "i-hourglass", "When it turns": "i-trend",
                   "Money": "i-coins", "Be careful": "i-alert"}
VY_FIT_ICON = ["i-store", "i-gem", "i-book"]
VY_WIN = {"good": ("Favourable", "mod"), "neutral": ("Steady", "build"),
          "warn": ("Careful", "hold")}
VY_HOUSE_ROLE = {1: "self & trade sense", 2: "savings & money", 3: "drive & courage",
                 4: "base & assets", 5: "ideas & risk", 6: "effort & competition",
                 7: "partners & deals", 8: "upheaval & change", 9: "fortune & mentors",
                 10: "work & status", 11: "gains & income", 12: "outflow & distance"}
VY_HOUSE_TITLE = {2: "Savings", 7: "Partners & trade", 10: "Work & status",
                  11: "Gains & income"}
VY_HOUSE_ICON = {2: "i-shield", 7: "i-people", 10: "i-compass", 11: "i-trend"}
# South-Indian kundli fixed layout: (sign_sanskrit, grid-column, grid-row)
VY_KUNDLI_LAYOUT = [("Meena", 1, 1), ("Mesha", 2, 1), ("Vrishabha", 3, 1),
                    ("Mithuna", 4, 1), ("Kumbha", 1, 2), ("Karka", 4, 2),
                    ("Makara", 1, 3), ("Simha", 4, 3), ("Dhanu", 1, 4),
                    ("Vrishchika", 2, 4), ("Tula", 3, 4), ("Kanya", 4, 4)]
VY_PLANET_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
                   "Saturn", "Rahu", "Ketu"]


def _vy_ordinal(n: int) -> str:
    suf = "th" if 11 <= (n % 100) <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def render_vyapar(p: dict) -> str:
    """/vyapar — business growth report. Returns a complete <!DOCTYPE html> doc:
    the v17 29-page design, every value from compute_vyapar()'s payload."""
    m = p["meta"]
    hi = (p.get("meta") or {}).get("lang") == "hi"   # Devanagari twins for /hi funnel
    name = escape(m.get("name", ""))            # user-supplied: escape (stored-XSS guard)
    first = name.split(" ")[0] if name else "there"
    ch = p["chart"]
    lagna_sa = ch["lagna"]
    lagna_en = VY_SIGN_EN.get(lagna_sa, lagna_sa)
    planets = ch["planets"]
    sade = p.get("sade_sati", {}) or {}
    sade_active = bool(sade.get("active"))
    sade_ends = sade.get("ends", "—")
    sade_phase = sade.get("phase", "current phase")
    roadmap = p.get("roadmap", []) or []
    cur_md = next((r for r in roadmap if r.get("current")), roadmap[0] if roadmap else
                  {"lord": "—", "to": "—", "theme": ""})
    S = {s["label"]: s for s in p.get("summary", [])}
    sw = p.get("strong_window", {}) or {}
    window_label = sw.get("label", p.get("teaser", {}).get("window_label", "—"))
    window_sub = p.get("teaser", {}).get("window_sub", "")
    # v17 note reframe: first 4-digit year in the growth-window label (start year)
    _wl_year = str(p.get("teaser", {}).get("window_label", "") or window_label or "")
    growth_year, _run = "", ""
    for _c in _wl_year:
        if _c.isdigit():
            _run += _c
            if len(_run) == 4:
                growth_year = _run
                break
        else:
            _run = ""
    when_sub = (S.get("When it turns", {}) or {}).get("sub", "")
    window_lord = when_sub.split(" ")[0] if when_sub else (
        sw.get("body", "").split(" ")[0] or "Venus")

    # ---- window-clarity: two different clocks (Saturn transit vs personal dasha) ----
    # Sade Sati is a TRANSIT (where Saturn sits now); the growth window is a DASHA
    # (the person's own sub-period). They can overlap — real, not a contradiction.
    # Decide overlap by comparing the growth-window START vs the Sade Sati END.
    from datetime import datetime as _dt

    def _parse_my(s):
        try:
            return _dt.strptime(str(s).strip(), "%b %Y")
        except Exception:
            return None
    _win_start = _parse_my((window_label or "").split("–")[0].split("-")[0])
    _sade_end_dt = _parse_my(sade_ends)
    # overlap = the growth window opens while Sade Sati is still on
    win_sade_overlap = bool(sade_active and _win_start and _sade_end_dt
                            and _win_start < _sade_end_dt)

    def sign_en(sa):
        return VY_SIGN_EN.get(sa, sa)

    def house_of(sa):
        return ((SIGN_NUM[sa] - SIGN_NUM[lagna_sa]) % 12) + 1

    # LLM prose with deterministic fallback — same as render_milan (line 1573).
    def prose(key, fallback):
        return narr(p, key) or fallback

    # ---- occupancy indexes (chart-derived, for the proof pages) ----
    by_sign, by_house = {}, {}
    for pl, info in planets.items():
        by_sign.setdefault(info["sign"], []).append(pl)
        by_house.setdefault(house_of(info["sign"]), []).append(pl)
    asc_occ = by_house.get(1, [])
    loaded_h = max(by_house, key=lambda h: len(by_house[h])) if by_house else 12
    rahu_h = house_of(planets["Rahu"]["sign"]) if "Rahu" in planets else 0
    ketu_h = house_of(planets["Ketu"]["sign"]) if "Ketu" in planets else 0

    # ============================================================ HINDI PATH
    # When meta.lang == "hi" the whole report renders in Devanagari at compose
    # time (no LLM needed): fields read their _hi twin from compute_vyapar, and
    # every fixed sentence has a Devanagari bank here. Mirrors report_view_v2's
    # hi handling. The English return below is left byte-identical.
    if hi:
        import re as _re
        GRAHA_HI = {"Sun": "सूर्य", "Moon": "चंद्र", "Mars": "मंगल", "Mercury": "बुध",
                    "Jupiter": "गुरु", "Venus": "शुक्र", "Saturn": "शनि",
                    "Rahu": "राहु", "Ketu": "केतु"}
        SIGN_HI = {"Mesha": "मेष", "Vrishabha": "वृषभ", "Mithuna": "मिथुन",
                   "Karka": "कर्क", "Simha": "सिंह", "Kanya": "कन्या", "Tula": "तुला",
                   "Vrishchika": "वृश्चिक", "Dhanu": "धनु", "Makara": "मकर",
                   "Kumbha": "कुंभ", "Meena": "मीन"}
        MON_HI = {"Jan": "जनवरी", "Feb": "फ़रवरी", "Mar": "मार्च", "Apr": "अप्रैल",
                  "May": "मई", "Jun": "जून", "Jul": "जुलाई", "Aug": "अगस्त",
                  "Sep": "सितंबर", "Oct": "अक्टूबर", "Nov": "नवंबर", "Dec": "दिसंबर"}
        ORD_HI = {1: "पहले", 2: "दूसरे", 3: "तीसरे", 4: "चौथे", 5: "पाँचवें",
                  6: "छठे", 7: "सातवें", 8: "आठवें", 9: "नौवें", 10: "दसवें",
                  11: "ग्यारहवें", 12: "बारहवें"}
        WIN_HI = {"good": ("अनुकूल", "mod"), "neutral": ("स्थिर", "build"),
                  "warn": ("सावधानी", "hold")}
        HOUSE_ROLE_HI = {1: "स्वयं और व्यापार-समझ", 2: "बचत और पैसा", 3: "जोश और साहस",
                         4: "आधार और संपत्ति", 5: "विचार और जोखिम", 6: "मेहनत और मुक़ाबला",
                         7: "साझेदार और सौदे", 8: "उथल-पुथल और बदलाव", 9: "भाग्य और मार्गदर्शक",
                         10: "काम और रुतबा", 11: "लाभ और आमदनी", 12: "ख़र्च और दूरी"}
        HOUSE_TITLE_HI = {2: "बचत", 7: "साझेदार और व्यापार", 10: "काम और रुतबा",
                          11: "लाभ और आमदनी"}
        FLAG_HI = {"own": "स्वगृही", "exalted": "उच्च", "debilitated": "नीच",
                   "combust": "अस्त", "retro": "वक्री"}
        DIG_HI = {"own": "स्वगृही", "exalted": "उच्च"}
        SUMMARY_LABEL_HI = {"Your type": "आपका स्वभाव", "Best-fit line": "सबसे अनुकूल क्षेत्र",
                            "Solo or partner": "अकेले या साझेदारी", "Last 3 years": "पिछले 3 साल",
                            "Right now": "अभी", "When it turns": "कब मोड़ आएगा", "Money": "धन",
                            "Be careful": "सावधान रहें"}
        SADE_PHASE_HI = {"rising phase": "उठान का चरण", "peak phase": "चरम चरण",
                         "setting phase": "उतार का चरण"}

        def dhi(s):
            return _re.sub(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b",
                           lambda mm: MON_HI[mm.group(1)], str(s))

        def sgn(sa):
            return SIGN_HI.get(sa, VY_SIGN_EN.get(sa, sa))

        def gr(pl):
            return GRAHA_HI.get(pl, pl)

        def ordh(n):
            return ORD_HI.get(n, f"{n}वें")

        def fh(d, k):
            v = (d or {}).get(k + "_hi")
            return v if v not in (None, "") else (d or {}).get(k, "")

        lagna_hi = sgn(lagna_sa)
        moon_hi = sgn(planets.get("Moon", {}).get("sign", "")) if "Moon" in planets else "—"
        window_lord_hi = gr(window_lord)
        window_label_hi = dhi(window_label)
        sade_ends_hi = dhi(sade_ends)
        sade_phase_hi = SADE_PHASE_HI.get(sade_phase, sade_phase)
        cur_lord_hi = gr(cur_md["lord"])

        # window-clarity copy (Devanagari): two different clocks
        if win_sade_overlap:
            clarity_hi = (f"ये दो अलग-अलग घड़ियाँ हैं। साढ़े साती शनि का गोचर है — बाहरी "
                          f"दबाव, जो {sade_ends_hi} तक हल्का हो रहा है — और आपका मज़बूत दौर "
                          f"({window_label_hi}) आपकी अपनी दशा है। यह दौर दबाव के पूरी तरह हटने "
                          f"से पहले ही खुल जाता है, इसलिए मौक़ा आ चुका है — धीरे-धीरे बढ़ाइए और "
                          f"{sade_ends_hi} तक थोड़ा पैसा बचाकर रखिए।")
        else:
            _clr_lead_hi = (f"यह कठिन दौर {sade_ends_hi} के आसपास आपके मौक़े के खुलने से पहले "
                            "ही ख़त्म हो जाता है, इसलिए" if sade_active else
                            "साढ़े साती अभी आप पर नहीं चल रही, इसलिए")
            clarity_hi = (f"ये दो अलग-अलग घड़ियाँ हैं। साढ़े साती शनि का गोचर है — बाहरी दबाव — "
                          f"और आपका मज़बूत दौर ({window_label_hi}) आपकी अपनी दशा है। "
                          f"{_clr_lead_hi} आपका दौर एक साफ़, खुला रास्ता है — साथ में कोई "
                          "दबाव सँभालने की ज़रूरत नहीं।")

        nature = p.get("nature", {})
        part = p.get("partnership", {})
        money = p.get("money", {})
        dy = p.get("dhana_yoga", {})
        dy_present = bool(dy.get("present"))
        dy_line = fh(dy, "line")
        rn = S.get("Right now", {}) or {}

        lead_nature = narr(p, "nature") or ("कारोबार में आप लोगों और रिश्तों के ज़रिए अगुआई करते हैं। "
            "यहाँ बताया गया है कि आपकी जन्म-कुंडली आपके स्वाभाविक काम करने के ढंग को कैसे गढ़ती है — "
            "और वह एक आदत जो सबसे ज़्यादा बदलेगी।")
        lead_fit = narr(p, "fit") or (f'आपका चार्ट साफ़ तौर पर '
            f'{p.get("teaser", {}).get("fit_label_hi", "आपके सबसे अनुकूल क्षेत्र")} की ओर इशारा करता है — '
            "जहाँ मशीनों से ज़्यादा रिश्ते, समझ और अभिरुचि मायने रखते हैं। ये क्षेत्र आपको सबसे अच्छे बैठते हैं।")
        lead_partnership = narr(p, "partnership") or ((fh(part, "verdict") or "साझेदारी आपको रास आती है")
            + " — सही व्यक्ति के साथ, और शर्तें काग़ज़ पर साफ़ रखते हुए।")
        lead_last3 = narr(p, "last3") or fh(p.get("last3", {}), "lead")
        lead_windows = narr(p, "windows") or ("सबसे मज़बूत दौर के आगे भी, आने वाले दौर हल्की लहरों में "
            "देते रहते हैं। यहाँ बताया गया है कि आगे क्या आता है।")
        lead_money = narr(p, "money") or ("आपके चार्ट के धन-भाव यह कहानी कहते हैं कि पैसा कैसे आता है, "
            "कैसे बढ़ता है, और कहाँ जाता है।")
        rem_note = narr(p, "remedies") or ("सरल, शास्त्रीय सहारा — आपको स्थिर करने के लिए दिया गया, "
            "डराने के लिए नहीं। कोई उपाय नीचे दी योजना की जगह नहीं लेता।")

        # 03 summary cards
        summary_cards = "".join(
            f'<div class="scard {VY_TONE_CLASS.get(s.get("tone"), "")}">'
            f'<svg class="ic si"><use href="#{VY_SUMMARY_ICON.get(s["label"], "i-scales")}"/></svg>'
            f'<div class="sl">{SUMMARY_LABEL_HI.get(s["label"], s["label"])}</div>'
            f'<div class="sv">{fh(s, "value")}</div>'
            f'<div class="ss">{fh(s, "sub")}</div></div>'
            for s in p.get("summary", []))

        # 06 fit families + what to avoid
        fit_types = p.get("fit", {}).get("types_hi") or p.get("fit", {}).get("types", [])
        fit_pts = "".join(
            f'<div class="pt"><svg class="ic pi"><use href="#{VY_FIT_ICON[i % len(VY_FIT_ICON)]}"/></svg>'
            f'<div class="tx"><b>{i + 1}. {t["title"]}</b>{t["body"]}</div></div>'
            for i, t in enumerate(fit_types))
        _avoid_hi = p.get("fit", {}).get("avoid_hi") or p.get("fit", {}).get("avoid", "संदिग्ध, कोना-काटने वाले सौदे")
        fit_pts += ('<div class="pt warn"><svg class="ic pi"><use href="#i-alert"/></svg>'
                    f'<div class="tx"><b>किससे बचें</b>{_avoid_hi} से बचें। यह आपको उन लोगों और उस अभिरुचि से '
                    'दूर रखता है जिन पर आपका जन्म-चार्ट टिका है।</div></div>')

        # 11 years after
        years_wins = "".join(
            f'<div class="win"><div class="wt"><span class="wd">{y["range"]}</span>'
            f'<span class="wg {WIN_HI.get(y.get("tone"), WIN_HI["neutral"])[1]}">'
            f'{WIN_HI.get(y.get("tone"), WIN_HI["neutral"])[0]}</span></div>'
            f'<div class="wb">{fh(y, "body")}</div></div>'
            for y in p.get("years_after", []))

        # 12 careful stretches
        careful_pts = "".join(
            f'<div class="pt warn"><svg class="ic pi"><use href="#i-hourglass"/></svg>'
            f'<div class="tx"><b>{fh(c, "range")}</b>{fh(c, "body")}</div></div>'
            for c in p.get("careful", [])[:3])
        careful_pts += ('<div class="pt good"><svg class="ic pi"><use href="#i-shield"/></svg>'
                        '<div class="tx"><b>इस पन्ने का मक़सद</b>पहले से चेताया, पहले से तैयार। इन तारीख़ों को '
                        'पहले से जानना उन्हें बुरे झटकों से बदलकर सरल, सँभालने लायक योजना बना देता है।</div></div>')

        # 16 remedies
        rem_pts = "".join(
            f'<div class="pt"><svg class="ic pi"><use href="#i-check"/></svg>'
            f'<div class="tx"><b>{fh(r, "obstacle")}</b>{fh(r, "remedy")}</div></div>'
            for r in p.get("remedies", []))

        # 17 kundli cells
        kundli_cells = ""
        for sa, col, row in VY_KUNDLI_LAYOUT:
            occ = by_sign.get(sa, [])
            pl_html = f'<div class="pl">{" · ".join(gr(x) for x in occ)}</div>' if occ else ""
            is_asc = (sa == lagna_sa)
            label = f'{sgn(sa)} · लग्न' if is_asc else sgn(sa)
            kundli_cells += (f'<div class="kc{" asc" if is_asc else ""}" '
                             f'style="grid-column:{col};grid-row:{row}">'
                             f'<div class="sn">{label}</div>{pl_html}</div>')
        kundli_center = ('<div class="kc center" style="grid-column:2/4;grid-row:2/4">'
                         f'<b>व्यापार कुंडली</b><span>{lagna_hi} लग्न</span></div>')

        # 18 planets table
        planet_rows = ""
        for pl in VY_PLANET_ORDER:
            info = planets.get(pl)
            if not info:
                continue
            h = house_of(info["sign"])
            flags = []
            dig = info.get("dignity")
            if dig in ("own", "exalted", "debilitated"):
                flags.append(FLAG_HI[dig])
            if info.get("combust"):
                flags.append(FLAG_HI["combust"])
            if info.get("retro"):
                flags.append(FLAG_HI["retro"])
            if pl == "Moon" and sade_active:
                flags.append("अभी साढ़े साती")
            note = HOUSE_ROLE_HI.get(h, "")
            if flags:
                note += " · " + ", ".join(flags)
            planet_rows += (f'<tr><td>{gr(pl)}</td><td>{sgn(info["sign"])}</td>'
                            f'<td>{h}</td><td>{note}</td></tr>')

        _asc_occ_hi = ", ".join(gr(x) for x in asc_occ)
        asc_pt = ('<div class="pt good"><svg class="ic pi"><use href="#i-check"/></svg>'
                  f'<div class="tx"><b>आपका पहला भाव</b>'
                  + (f'{_asc_occ_hi} आपके लग्न ({lagna_hi}) पर बैठे हैं — {HOUSE_ROLE_HI[1]}। '
                     'किसी भी कारोबार के लिए एक भरोसेमंद, मिलनसार छवि सचमुच अच्छी शुरुआत है।'
                     if asc_occ else
                     f'आपका {lagna_hi} लग्न एक निष्पक्ष, आसानी से निभने वाला कारोबारी चेहरा गढ़ता है — '
                     'लोग आप पर जल्दी भरोसा करते हैं।')
                  + '</div></div>')
        _loaded_occ_hi = ", ".join(gr(x) for x in by_house.get(loaded_h, []))
        loaded_pt = ('<div class="pt warn"><svg class="ic pi"><use href="#i-coins"/></svg>'
                     f'<div class="tx"><b>आपका {ordh(loaded_h)} भाव भरा हुआ है</b>'
                     f'{_loaded_occ_hi} यहाँ बैठे हैं — {HOUSE_ROLE_HI.get(loaded_h, "")}। '
                     'आपके चार्ट का सबसे भीड़भाड़ वाला कोना, और इसके मिज़ाज का सबसे साफ़ चालक।</div></div>')

        # 19 / 20 business houses
        H = {h["house"]: h for h in p.get("houses", [])}

        def house_pt(hn):
            h = H.get(hn)
            if not h:
                return ""
            return (f'<div class="pt"><svg class="ic pi"><use href="#{VY_HOUSE_ICON.get(hn, "i-compass")}"/></svg>'
                    f'<div class="tx"><b>{ordh(hn)} भाव — {HOUSE_TITLE_HI.get(hn, "")}</b>'
                    f'{sgn(h["sign"])}, इसका स्वामी {gr(h["lord"])} {ordh(h["lord_house"])} भाव में बैठा है। '
                    f'{fh(h, "note")}।</div></div>')

        houses_pts_1 = house_pt(7) + house_pt(10) + house_pt(2)
        houses_pts_2 = house_pt(11) + loaded_pt + asc_pt

        # 08 last-3-years points
        _last_icons = ["i-alert", "i-clock", "i-hourglass"]
        _points_hi = p.get("last3", {}).get("points_hi") or p.get("last3", {}).get("points", [])
        last_pts = "".join(
            f'<div class="pt{" warn" if i == 0 else ""}">'
            f'<svg class="ic pi"><use href="#{_last_icons[i % len(_last_icons)]}"/></svg>'
            f'<div class="tx"><b>{pt.split(" — ")[0]}</b>'
            f'{pt.split(" — ", 1)[1] if " — " in pt else pt}</div></div>'
            for i, pt in enumerate(_points_hi[:3]))

        # 21 recent sub-periods timeline
        last_tl = "".join(f'<div class="tli"><div class="th">{pt}</div></div>' for pt in _points_hi)
        last_tl += (f'<div class="tli now"><div class="d">अभी</div>'
                    f'<div class="dt">{fh(rn, "value") or "मौजूदा दौर"}</div>'
                    f'<div class="th">{fh(rn, "sub")}</div></div>')

        # 22 upcoming mahadashas timeline
        road_tl = "".join(
            f'<div class="tli {"now" if r.get("current") else VY_TLI.get(r.get("tone"), "")}">'
            f'<div class="d">{gr(r["lord"])} दौर{" · अभी" if r.get("current") else ""}</div>'
            f'<div class="dt">{r["from"]} – {r["to"]}</div>'
            f'<div class="th">{fh(r, "theme")}</div></div>'
            for r in roadmap)

        # 23 why the strong window scores "strong"
        wlord_dig = planets.get(window_lord, {}).get("dignity", "neutral")
        _wsub_hi = p.get("teaser", {}).get("window_sub_hi") or window_sub
        strong_pts = ('<div class="pt good"><svg class="ic pi"><use href="#i-check"/></svg>'
                      f'<div class="tx"><b>{window_lord_hi} इस दौर को चलाता है</b>'
                      f'{_wsub_hi if _wsub_hi else "यह मुख्य उप-दौर बन जाता है"}। जब कोई सहायक ग्रह दौर का '
                      'अगुआ हो, तो उसका मिज़ाज सीधे अवसर में बदल जाता है।</div></div>')
        if wlord_dig in ("own", "exalted"):
            strong_pts += ('<div class="pt good"><svg class="ic pi"><use href="#i-gem"/></svg>'
                           f'<div class="tx"><b>{window_lord_hi} अपनी {DIG_HI.get(wlord_dig, wlord_dig)} राशि में है</b>'
                           'किसी चालक ग्रह की सबसे मज़बूत स्थितियों में से एक — इसका मतलब यह दौर सिर्फ़ एक '
                           'उम्मीद-भरा नाम नहीं, बल्कि सचमुच वज़न रखता है।</div></div>')
        if sade_active:
            strong_pts += ('<div class="pt"><svg class="ic pi"><use href="#i-hourglass"/></svg>'
                           f'<div class="tx"><b>दबाव भी इसी के साथ हल्का होता है</b>'
                           f'साढ़े साती {sade_ends_hi} तक हल्की पड़ जाती है — लगभग तभी जब यह दौर चलता है, '
                           'इसलिए बोझ ठीक उसी समय उतरता है जब गति बनती है।</div></div>')

        # 24 the other windows
        other_pts = "".join(
            f'<div class="pt"><svg class="ic pi"><use href="#i-trend"/></svg>'
            f'<div class="tx"><b>{y["range"]}</b>{fh(y, "body")}</div></div>'
            for y in p.get("years_after", [])[1:])
        _c0 = (p.get("careful", []) or [{}])[0]
        other_pts += ('<div class="pt warn"><svg class="ic pi"><use href="#i-alert"/></svg>'
                      f'<div class="tx"><b>सावधानी का दौर</b>{fh(_c0, "range")} — '
                      f'{fh(_c0, "body") or "धक्का देने के बजाय रुककर चलने का समय।"}</div></div>')

        # 28 year-by-year timeline
        yby_tl = "".join(
            f'<div class="tli {VY_TLI.get(y.get("tone"), "")}"><div class="d">{y["year"]}</div>'
            f'<div class="th">{fh(y, "outlook")}</div></div>'
            for y in p.get("year_by_year", []))

        # strong window card
        sw_do = sw.get("do_hi") or sw.get("do", [])
        sw_dont = sw.get("dont_hi") or sw.get("dont", [])
        sw_body = fh(sw, "body")

        # cover pills
        rn_val = fh(rn, "value")
        compact = (rn_val.replace(" महादशा", "").replace(" अंतर्दशा", "").replace(" — ", "–")
                   ) if rn_val and rn_val != "—" else cur_lord_hi
        cov_sub = fh(nature, "lagna_line") or "आप लोगों के ज़रिए कारोबार करते हैं — भरोसा और रिश्ते ही आपकी असली ताक़त हैं।"

    else:
        # -------------------------------------------------- fragment builders
        # 03 summary cards
        summary_cards = "".join(
            f'<div class="scard {VY_TONE_CLASS.get(s.get("tone"), "")}">'
            f'<svg class="ic si"><use href="#{VY_SUMMARY_ICON.get(s["label"], "i-scales")}"/></svg>'
            f'<div class="sl">{s["label"]}</div><div class="sv">{s["value"]}</div>'
            f'<div class="ss">{s["sub"]}</div></div>'
            for s in p.get("summary", []))

        # 06 fit families + what to avoid
        fit_pts = "".join(
            f'<div class="pt"><svg class="ic pi"><use href="#{VY_FIT_ICON[i % len(VY_FIT_ICON)]}"/></svg>'
            f'<div class="tx"><b>{i + 1}. {t["title"]}</b>{t["body"]}</div></div>'
            for i, t in enumerate(p.get("fit", {}).get("types", [])))
        fit_pts += ('<div class="pt warn"><svg class="ic pi"><use href="#i-alert"/></svg>'
                    f'<div class="tx"><b>What to avoid</b>Avoid {p.get("fit", {}).get("avoid", "grey-area, cut-corner trades")}. '
                    'It keeps you away from the people and taste your chart runs on.</div></div>')

        # 11 years after (the softer waves)
        years_wins = "".join(
            f'<div class="win"><div class="wt"><span class="wd">{y["range"]}</span>'
            f'<span class="wg {VY_WIN.get(y.get("tone"), VY_WIN["neutral"])[1]}">'
            f'{VY_WIN.get(y.get("tone"), VY_WIN["neutral"])[0]}</span></div>'
            f'<div class="wb">{y["body"]}</div></div>'
            for y in p.get("years_after", []))

        # 12 careful stretches
        careful_pts = "".join(
            f'<div class="pt warn"><svg class="ic pi"><use href="#i-hourglass"/></svg>'
            f'<div class="tx"><b>{c["range"]}</b>{c["body"]}</div></div>'
            for c in p.get("careful", [])[:3])
        careful_pts += ('<div class="pt good"><svg class="ic pi"><use href="#i-shield"/></svg>'
                        '<div class="tx"><b>The point of this page</b>Forewarned is forearmed. '
                        'Knowing these dates in advance turns them from nasty surprises into simple, '
                        'manageable planning.</div></div>')

        # 16 remedies -> action points
        rem_pts = "".join(
            f'<div class="pt"><svg class="ic pi"><use href="#i-check"/></svg>'
            f'<div class="tx"><b>{r["obstacle"]}</b>{r["remedy"]}</div></div>'
            for r in p.get("remedies", []))

        # 17 kundli cells (South-Indian, ascendant marked)
        kundli_cells = ""
        for sa, col, row in VY_KUNDLI_LAYOUT:
            occ = by_sign.get(sa, [])
            pl_html = f'<div class="pl">{" · ".join(occ)}</div>' if occ else ""
            is_asc = (sa == lagna_sa)
            label = f'{sign_en(sa)} · Asc' if is_asc else sign_en(sa)
            kundli_cells += (f'<div class="kc{" asc" if is_asc else ""}" '
                             f'style="grid-column:{col};grid-row:{row}">'
                             f'<div class="sn">{label}</div>{pl_html}</div>')
        kundli_center = ('<div class="kc center" style="grid-column:2/4;grid-row:2/4">'
                         f'<b>Vyapar Kundli</b><span>{lagna_en} Ascendant</span></div>')

        # 18 planets table
        planet_rows = ""
        for pl in VY_PLANET_ORDER:
            info = planets.get(pl)
            if not info:
                continue
            h = house_of(info["sign"])
            flags = []
            dig = info.get("dignity")
            if dig in ("own", "exalted", "debilitated"):
                flags.append(dig)
            if info.get("combust"):
                flags.append("combust")
            if info.get("retro"):
                flags.append("retro")
            if pl == "Moon" and sade_active:
                flags.append("Sade Sati now")
            note = VY_HOUSE_ROLE.get(h, "")
            if flags:
                note += " · " + ", ".join(flags)
            planet_rows += (f'<tr><td>{pl}</td><td>{sign_en(info["sign"])}</td>'
                            f'<td>{h}</td><td>{note}</td></tr>')

        asc_pt = ('<div class="pt good"><svg class="ic pi"><use href="#i-check"/></svg>'
                  f'<div class="tx"><b>Your 1st house</b>'
                  + (f'{", ".join(asc_occ)} sit on your ascendant ({lagna_en}) — {VY_HOUSE_ROLE[1]}. '
                     'A personable, trusted presence is a genuinely good start for any business.'
                     if asc_occ else
                     f'Your {lagna_en} ascendant sets a fair, easy-to-deal-with business face — '
                     'people trust you quickly.')
                  + '</div></div>')
        loaded_pt = ('<div class="pt warn"><svg class="ic pi"><use href="#i-coins"/></svg>'
                     f'<div class="tx"><b>Your {_vy_ordinal(loaded_h)} house is loaded</b>'
                     f'{", ".join(by_house.get(loaded_h, []))} sit here — {VY_HOUSE_ROLE.get(loaded_h, "")}. '
                     'The most crowded corner of your chart, and the clearest driver of its theme.</div></div>')

        # 19 / 20 business houses (from payload.houses: 2, 7, 10, 11)
        H = {h["house"]: h for h in p.get("houses", [])}

        def house_pt(hn):
            h = H.get(hn)
            if not h:
                return ""
            return (f'<div class="pt"><svg class="ic pi"><use href="#{VY_HOUSE_ICON.get(hn, "i-compass")}"/></svg>'
                    f'<div class="tx"><b>{_vy_ordinal(hn)} — {VY_HOUSE_TITLE.get(hn, "")}</b>'
                    f'{sign_en(h["sign"])}, its lord {h["lord"]} sits in the {_vy_ordinal(h["lord_house"])} house. '
                    f'{h["note"]}.</div></div>')

        houses_pts_1 = house_pt(7) + house_pt(10) + house_pt(2)
        houses_pts_2 = house_pt(11) + loaded_pt + asc_pt

        # 08 last-3-years -> flowing points (first testing one flagged 'warn')
        _last_icons = ["i-alert", "i-clock", "i-hourglass"]
        last_pts = "".join(
            f'<div class="pt{" warn" if i == 0 else ""}">'
            f'<svg class="ic pi"><use href="#{_last_icons[i % len(_last_icons)]}"/></svg>'
            f'<div class="tx"><b>{pt.split(" — ")[0]}</b>'
            f'{pt.split(" — ", 1)[1] if " — " in pt else pt}</div></div>'
            for i, pt in enumerate(p.get("last3", {}).get("points", [])[:3]))

        # 21 recent sub-periods timeline (last3) + "now" node
        last_tl = "".join(f'<div class="tli"><div class="th">{pt}</div></div>'
                          for pt in p.get("last3", {}).get("points", []))
        rn = S.get("Right now", {}) or {}
        last_tl += (f'<div class="tli now"><div class="d">Now</div>'
                    f'<div class="dt">{rn.get("value", "current period")}</div>'
                    f'<div class="th">{rn.get("sub", "")}</div></div>')

        # 22 upcoming mahadashas timeline (roadmap)
        road_tl = "".join(
            f'<div class="tli {"now" if r.get("current") else VY_TLI.get(r.get("tone"), "")}">'
            f'<div class="d">{r["lord"]} period{" · now" if r.get("current") else ""}</div>'
            f'<div class="dt">{r["from"]} – {r["to"]}</div>'
            f'<div class="th">{r["theme"]}</div></div>'
            for r in roadmap)

        # 23 why the strong window scores "strong" (chart-derived, qualitative)
        wlord_dig = planets.get(window_lord, {}).get("dignity", "neutral")
        strong_pts = ('<div class="pt good"><svg class="ic pi"><use href="#i-check"/></svg>'
                      f'<div class="tx"><b>{window_lord} drives this window</b>'
                      f'{window_sub.capitalize() if window_sub else "It takes over as the driving sub-period."}. '
                      'When a helpful planet leads the period, its theme turns straight into opportunity.</div></div>')
        if wlord_dig in ("own", "exalted"):
            strong_pts += ('<div class="pt good"><svg class="ic pi"><use href="#i-gem"/></svg>'
                           f'<div class="tx"><b>{window_lord} is in its {wlord_dig} sign</b>'
                           'One of the strongest placements a driving planet can have — it means this '
                           'window carries real weight, not just a hopeful label.</div></div>')
        if sade_active:
            strong_pts += ('<div class="pt"><svg class="ic pi"><use href="#i-hourglass"/></svg>'
                           f'<div class="tx"><b>The pressure lifts alongside it</b>'
                           f'Sade Sati eases by {sade_ends} — close to when this window runs, so the '
                           'weight comes off at roughly the moment momentum builds.</div></div>')

        # 24 the other windows (years_after tail + first careful stretch)
        other_pts = "".join(
            f'<div class="pt"><svg class="ic pi"><use href="#i-trend"/></svg>'
            f'<div class="tx"><b>{y["range"]}</b>{y["body"]}</div></div>'
            for y in p.get("years_after", [])[1:])
        _c0 = (p.get("careful", []) or [{}])[0]
        other_pts += ('<div class="pt warn"><svg class="ic pi"><use href="#i-alert"/></svg>'
                      f'<div class="tx"><b>The careful stretch</b>{_c0.get("range", "")} — '
                      f'{_c0.get("body", "a time to hold back rather than push.")}</div></div>')

        # window-clarity copy (English): two different clocks
        if win_sade_overlap:
            clarity_en = (f"These are two different clocks. Sade Sati is Saturn's transit — outside "
                          f"pressure that is easing until {sade_ends} — while your growth window "
                          f"({window_label}) is your own personal dasha period. It opens before that "
                          f"pressure fully lifts, so the opportunity is already arriving: grow steadily "
                          f"and keep a cash reserve until {sade_ends}, then push harder.")
        else:
            _clr_lead_en = (f"That hard phase clears around {sade_ends}, before your window opens, so"
                            if sade_active else "Sade Sati isn't pressing on you now, so")
            clarity_en = (f"These are two different clocks. Sade Sati is Saturn's transit — the hard "
                          f"outside phase — and your growth window ({window_label}) is your own "
                          f"personal dasha period. {_clr_lead_en} your window is a clean, open road "
                          f"with no overlapping pressure to manage.")

        # 28 year-by-year timeline
        yby_tl = "".join(
            f'<div class="tli {VY_TLI.get(y.get("tone"), "")}"><div class="d">{y["year"]}</div>'
            f'<div class="th">{y["outlook"]}</div></div>'
            for y in p.get("year_by_year", []))

        # ---- narrative-or-bank leads (LLM prose when present, else compute copy) ----
        nature = p.get("nature", {})
        lead_nature = prose("nature", "In business you lead through people and relationships. "
                            "Here is how your birth chart shapes the way you naturally work — "
                            "and the one habit that will change the most.")
        lead_fit = prose("fit", f'Your chart points clearly toward {p.get("teaser", {}).get("fit_label", "your best-fit line")} '
                         '— where relationships, judgement and taste matter more than machinery. '
                         'These families fit you best.')
        lead_partnership = prose("partnership", p.get("partnership", {}).get("verdict", "")
                                 + " — with the right person, and clear terms on paper.")
        lead_last3 = prose("last3", p.get("last3", {}).get("lead", ""))
        lead_windows = prose("windows", "Beyond the strongest window, the upcoming periods keep "
                             "giving in gentler waves. Here is what follows.")
        lead_money = prose("money", "The money houses in your chart tell the story of how wealth "
                           "comes in, how it grows, and where it goes.")
        rem_note = prose("remedies", "Simple, classical support — offered to steady you, never to "
                         "frighten you. No remedy replaces the plan below.")

        part = p.get("partnership", {})
        money = p.get("money", {})
        dy = p.get("dhana_yoga", {})
        dy_present = bool(dy.get("present"))
        dy_line = dy.get("line", "")

        # cover pills
        moon_en = sign_en(planets.get("Moon", {}).get("sign", "")) if "Moon" in planets else "—"
        rn_val = rn.get("value", "")
        compact = (rn_val.replace(" Mahadasha", "").replace(" Antardasha", "")
                   .replace(" — ", "–")) if rn_val and rn_val != "—" else f'{cur_md["lord"]}'
        cov_sub = nature.get("lagna_line", "You do business through people — trust and relationships are your real strength.")
        cov_sub = cov_sub[0].upper() + cov_sub[1:] if cov_sub else cov_sub
    return f"""<!DOCTYPE html>{(f'''<html lang="hi">''' if hi else f'''<html lang="en">''')}<head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{(f'''{name} — व्यापार व्यवसाय रिपोर्ट | Axtroshastra''' if hi else f'''{name} — Vyapar Business Report | Axtroshastra''')}</title>
<style>
{_VYAPAR_CSS}
</style></head><body>
{_VYAPAR_DEFS}

<!-- 01 COVER -->
<section class="page sand"><div class="col">
  <div class="cov-brand">{(f'''AxtroShastra · व्यापार — व्यवसाय वृद्धि''' if hi else f'''AxtroShastra · Vyapar — Business Growth''')}</div>
  <svg class="constel" viewBox="0 0 230 80" fill="none" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="14,66 60,54 104,42 150,31 210,13" stroke="#5A3C14" stroke-width="1.1" stroke-dasharray="2 5" opacity=".55"/>
    <circle cx="14" cy="66" r="3" fill="#B9862E"/><circle cx="60" cy="54" r="3" fill="#B9862E"/><circle cx="104" cy="42" r="3" fill="#B9862E"/>
    <g transform="translate(150 31)" stroke="#B9862E" stroke-width="1.4"><path d="M0 -7V7M-7 0H7M-5 -5l10 10M5 -5l-10 10"/></g>
    <g transform="translate(210 13)"><path d="M0 -9V9M-9 0H9M-6 -6l12 12M6 -6l-12 12" stroke="#B9862E" stroke-width="1.6"/><circle r="3.6" fill="#E4D5BE" stroke="#B9862E" stroke-width="1.5"/></g>
  </svg>
  <div class="cov-name">{name}</div>
  <div class="cov-type"><svg class="ti" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M3 14l4-4 3 3 6-7"/><path d="M13 4h4v4"/></svg><span>{(f'''{cov_sub}।''' if hi else f'''{cov_sub}.''')}</span></div>
  <div class="cov-pills"><span class="cp"><span class="g">☾</span>{(f''' {moon_hi} में चंद्र''' if hi else f''' Moon in {moon_en}''')}</span><span class="cp"><span class="g">△</span>{(f''' {lagna_hi} लग्न''' if hi else f''' {lagna_en} rising''')}</span><span class="cp"><span class="g">♄</span>{(f''' {compact} दौर''' if hi else f''' {compact} period''')}</span></div>
  <div class="cov-comfort">{(f'''दिक़्क़त कभी आपकी मेहनत नहीं थी। वह समय था — और समय बदलता है।''' if hi else f'''The problem was never your effort. It was the timing — and timing changes.''')}</div>
  <div class="cov-trust">{(f'''Swiss Ephemeris · लाहिरी अयनांश · तैयार {m.get("generated", "")}''' if hi else f'''Swiss Ephemeris · Lahiri ayanamsa · Generated {m.get("generated", "")}''')}</div>
</div><div class="pno">01</div></section>

<!-- 02 NOTE FOR YOU -->
<section class="page note"><div class="col">
  <div class="noteframe">
    <svg class="fan nftop" viewBox="0 0 54 30" fill="none"><rect x="6" y="13" width="42" height="20" fill="#FBF7EE"/><g stroke="currentColor" stroke-width="1" stroke-linecap="round"><path d="M27 27 L12 15M27 27 L18 12M27 27 L27 9M27 27 L36 12M27 27 L42 15"/><path d="M12 15 A19 19 0 0 1 42 15"/></g></svg>
    <div class="ne">{(f'''आपके लिए एक बात''' if hi else f'''A note for you''')}</div>
    <div class="nh">{(f'''आगे पढ़ने से पहले''' if hi else f'''Before you read on''')}</div>
    <p>{(f'''प्रिय {first}, इन बीते सालों ने आपसे बहुत माँगा &mdash; और आप डटे रहे। {cur_lord_hi} के दौर में यही लगन असल में जुड़ती जाती है।''' if hi else f'''Dear {first}, the last few years asked a lot of you &mdash; and you kept going. In a {cur_md['lord']} phase, that persistence is exactly what compounds.''')}</p>
    <p>{(f'''यह रिपोर्ट किसी टूटे कारोबार की नहीं है। यह बताती है कि एक कठिन दौर के बाद अच्छा समय आ रहा है। जब {growth_year} में आपका दौर खुले तब क़दम बढ़ाइए &mdash; और पीछे मुड़कर यह मोड़ ऐसा लगेगा जैसे आपने ख़ुद बनाया हो।''' if hi else f'''This report doesn't show a broken business. It shows good timing arriving after a hard test. Move when your window opens in {growth_year}, and the turn will look, in hindsight, like something you built.''')}</p>
    <div class="sig">{(f'''&mdash; आपके ज्योतिषी, AxtroShastra''' if hi else f'''&mdash; Your astrologer, AxtroShastra''')}</div>
    <svg class="fan nfbot" viewBox="0 0 54 30" fill="none"><rect x="6" y="13" width="42" height="20" fill="#FBF7EE"/><g stroke="currentColor" stroke-width="1" stroke-linecap="round"><path d="M27 27 L12 15M27 27 L18 12M27 27 L27 9M27 27 L36 12M27 27 L42 15"/><path d="M12 15 A19 19 0 0 1 42 15"/></g></svg><svg class="crn ctl" viewBox="0 0 12 12"><path d="M6 .5 11.5 6 6 11.5 .5 6Z" fill="#B9862E"/></svg><svg class="crn ctr" viewBox="0 0 12 12"><path d="M6 .5 11.5 6 6 11.5 .5 6Z" fill="#B9862E"/></svg><svg class="crn cbl" viewBox="0 0 12 12"><path d="M6 .5 11.5 6 6 11.5 .5 6Z" fill="#B9862E"/></svg><svg class="crn cbr" viewBox="0 0 12 12"><path d="M6 .5 11.5 6 6 11.5 .5 6Z" fill="#B9862E"/></svg>
  </div>
</div><div class="pno">02</div></section>

<!-- 03 SUMMARY -->
<section class="page"><div class="col">
  <div class="eyebrow">{(f'''एक नज़र में''' if hi else f'''In one look''')}</div>
  <h2 class="head">{(f'''आपका कारोबार, एक नज़र में''' if hi else f'''Your business, in one look''')}</h2>
  <div class="rule"></div>
  <div class="sgrid">
    {summary_cards}
  </div>
  <div style="display:flex;gap:9px;align-items:flex-start;background:#E7F1EA;border:1px solid rgba(46,125,83,.3);border-radius:12px;padding:10px 13px;margin-top:11px;text-align:left"><svg viewBox="0 0 24 24" fill="none" stroke="#2E7D53" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="flex:none;width:16px;height:16px;margin-top:1px"><circle cx="12" cy="12" r="9"/><path d="M12 8v4l2.5 1.5"/></svg>{(f'''<div style="font-family:var(--sans);font-size:12px;line-height:1.55;color:var(--ink)">''' if hi else f'''<div style="font-family:var(--sans);font-size:12px;line-height:1.5;color:var(--ink)">''')}<b style="color:#2E7D53">{(f'''दो घड़ियाँ:''' if hi else f'''Two clocks:''')}</b>{(f''' आपका मज़बूत दौर (आपकी अपनी दशा) साढ़े साती (बाहरी दबाव) के ख़त्म होने से पहले खुल सकता है — इसलिए तारीख़ें साथ आती हैं। धीरे बढ़ाइए, दबाव हटते ही ज़ोर लगाइए।''' if hi else f''' your best window (your own timing) can open before Sade Sati (outside pressure) ends — so they overlap. Grow steadily, then push once it lifts.''')}</div></div>
</div><div class="pno">03</div></section>

<!-- 04 HOW YOU WORK -->
<section class="page"><div class="col">
  <div class="eyebrow">{(f'''आपका कारोबारी स्वभाव''' if hi else f'''Your business nature''')}</div>
  <h2 class="head">{(f'''आप कैसे काम करते हैं''' if hi else f'''How you work''')}</h2>
  <div class="rule"></div>
  <div class="verdict gold sum"><svg class="ic"><use href="#i-scales"/></svg>{(f''' आप स्वाभाविक रूप से कैसे काम करते हैं — आपकी ताक़त भरोसा है, और आपकी बढ़त थोड़ा जल्दी फ़ैसला लेने में है।''' if hi else f''' How you naturally work — your strength is trust, and your growth is deciding a little faster.''')}</div>
  <div class="lead">{lead_nature}</div>
  <div class="pts">
    <div class="pt"><svg class="ic pi"><use href="#i-scales"/></svg><div class="tx"><b>{(f'''{lagna_hi} लग्न — आपका कारोबारी चेहरा''' if hi else f'''{lagna_en} rising — your business face''')}</b>{(f'''{fh(nature, "lagna_line")}।''' if hi else f'''{nature.get("lagna_line", "")}.''')}</div></div>
    <div class="pt warn"><svg class="ic pi"><use href="#i-alert"/></svg><div class="tx"><b>{(f'''आपकी कमज़ोरी''' if hi else f'''Your weak spot''')}</b>{(f'''{fh(nature, "weak_spot")}।''' if hi else f'''{nature.get("weak_spot", "")}.''')}</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-moon"/></svg><div class="tx"><b>{(f'''{moon_hi} चंद्र — आप चीज़ें कैसे चलाते हैं''' if hi else f'''{moon_en} Moon — how you run things''')}</b>{(f'''{fh(nature, "moon_line")}।''' if hi else f'''{nature.get("moon_line", "")}.''')}</div></div>
  </div>
  <a class="xlink" href="#p16">{(f'''अपना चार्ट देखें (पृ. 17) →''' if hi else f'''See your chart (p.17) →''')}</a>
</div><div class="pno">04</div></section>

<!-- 05 INSTINCT & PRESSURE -->
<section class="page"><div class="col">
  <div class="eyebrow">{(f'''आपका कारोबारी स्वभाव''' if hi else f'''Your business nature''')}</div>
  <h2 class="head">{(f'''आपकी सहज-समझ और आप दबाव कैसे झेलते हैं''' if hi else f'''Your instinct &amp; how you take pressure''')}</h2>
  <div class="rule"></div>
  <div class="verdict sum"><svg class="ic"><use href="#i-shield"/></svg>{(f''' आप कठिन समय कैसे सँभालते हैं — आप स्थिर रहते हैं, और अभी का भारी दौर गुज़र जाएगा।''' if hi else f''' How you handle hard times — you stay steady, and the heavy phase now will pass.''')}</div>
  <div class="lead">{(f'''दो बातें तय करती हैं कि कोई कारोबारी कठिन साल पार करता है या नहीं: धीरज, और वह दबाव कैसे उठाता है।''' if hi else f'''Two things decide whether a business owner survives the hard years: patience, and how they carry pressure.''')}</div>
  <div class="pts">
    <div class="pt"><svg class="ic pi"><use href="#i-shield"/></svg><div class="tx"><b>{(f'''एक धीरजवाला निर्माता''' if hi else f'''A patient builder''')}</b>{(f'''आप कुछ ठोस को समय के साथ बनाने में अपना सबसे अच्छा काम करते हैं, न कि जल्दी और चमकदार जीत के पीछे भागकर। आपकी ताक़त लंबी दौड़ में दिखती है — बस सावधानी को इतना न बढ़ने दें कि आप कभी हिलें ही नहीं।''' if hi else f'''You do your best work building something solid over time, not chasing quick, flashy wins. Your strength shows up in the long run — just don't let caution tip over into never moving at all.''')}</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-moon"/></svg><div class="tx"><b>{(f'''आपका मन पैसे को कैसे पढ़ता है''' if hi else f'''How your mind reads money''')}</b>{(f'''{fh(nature, "moon_line")}। इस ढंग को जानना उसे सँभालने का आधा काम है।''' if hi else f'''{nature.get("moon_line", "")}. Knowing this pattern is half of managing it.''')}</div></div>
    <div class="pt {"warn" if sade_active else ""}"><svg class="ic pi"><use href="#i-hourglass"/></svg><div class="tx"><b>{(f'''अभी का बोझ असली है''' if hi else f'''The weight now is real''')}</b>{(f'''{("जो भारीपन आप महसूस करते हैं वह साढ़े साती है — एक कठिन शनि दौर जो आपके मन पर दबाव डालता है। इसे इस दौर का मौसम समझें, अपनी कोई कमी नहीं। इसकी एक तय समाप्ति-तिथि है, लगभग " + sade_ends_hi + " के आसपास।") if sade_active else "शनि अभी आपके लिए अपने सबसे भारी दौर में नहीं है — नक़दी और ज़िम्मेदारियों पर सामान्य अनुशासन ही काफ़ी है।"}''' if hi else f'''{("The heaviness you feel is Sade Sati — a hard Saturn phase pressing on your mind. Read it as the weather of this stretch, not a flaw in you. It has a fixed end date around " + sade_ends + ".") if sade_active else ("Saturn is not in its heaviest phase for you right now — the usual discipline on cash and commitments is enough.")}''')}</div></div>
  </div>{(f'''
  {('<div class="note"><b>ध्यान दें:</b> आपका जन्म-समय अनुमानित है, इसलिए यह पठन व्यक्तित्व के लिए चंद्र-चार्ट (शास्त्रीय चंद्र लग्न विधि) का उपयोग करता है।</div>') if nature.get("note_chandra") else ''}
  ''' if hi else f'''
  {('<div class="note"><b>Note:</b> your birth time is approximate, so this reading uses the Moon chart (the classical Chandra Lagna method) for personality.</div>') if nature.get("note_chandra") else ''}
  ''')}<a class="xlink" href="#p16">{(f'''अपना चार्ट देखें (पृ. 17) →''' if hi else f'''See your chart (p.17) →''')}</a>
</div><div class="pno">05</div></section>

<!-- 06 THE WORK THAT FITS -->
<section class="page"><div class="col">
  <div class="eyebrow">{(f'''आपके लिए कौन-सा कारोबार''' if hi else f'''What business suits you''')}</div>
  <h2 class="head">{(f'''वह काम जो आपको जँचता है''' if hi else f'''The work that fits you''')}</h2>
  <div class="rule"></div>
  <div class="verdict gold sum"><svg class="ic"><use href="#i-compass"/></svg>{(f''' वह काम जो आपको जँचता है — {p.get("teaser", {}).get("fit_label_hi", "आपका सबसे अनुकूल क्षेत्र")}।''' if hi else f''' The work that suits you — {p.get("teaser", {}).get("fit_label", "your best-fit line").lower()}.''')}</div>
  <div class="lead">{lead_fit}</div>
  <div class="pts">
    {fit_pts}
  </div>
</div><div class="pno">06</div></section>

<!-- 07 PARTNERSHIP -->
<section class="page"><div class="col">
  <div class="eyebrow">{(f'''अकेले या साझेदार''' if hi else f'''Solo or partner''')}</div>
  <h2 class="head">{(f'''क्या आपको अकेले चलना चाहिए?''' if hi else f'''Should you go alone?''')}</h2>
  <div class="rule"></div>
  <div class="verdict"><svg class="ic"><use href="#i-check"/></svg>{(f''' {fh(part, "verdict") or "साझेदारी आपको रास आती है"}''' if hi else f''' {part.get("verdict", "A partner suits you")}''')}</div>
  <div class="lead">{lead_partnership}</div>
  <div class="pts">
    <div class="pt good"><svg class="ic pi"><use href="#i-people"/></svg><div class="tx"><b>{(f'''वरदान''' if hi else f'''The blessing''')}</b>{(f'''{fh(part, "blessing")}।''' if hi else f'''{part.get("blessing", "")}.''')}</div></div>
    <div class="pt warn"><svg class="ic pi"><use href="#i-alert"/></svg><div class="tx"><b>{(f'''पर सोच-समझकर चुनें''' if hi else f'''But choose carefully''')}</b>{(f'''{fh(part, "caution")}।''' if hi else f'''{part.get("caution", "")}.''')}</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-check"/></svg><div class="tx"><b>{(f'''किसे चुनें''' if hi else f'''Who to pick''')}</b>{(f'''{fh(part, "who")}। सौदा हमेशा लिखित में रखें, और पहले दिन से पैसे को पारदर्शी रखें।''' if hi else f'''{part.get("who", "")}. Always put the deal in writing, and keep money transparent from day one.''')}</div></div>
  </div>
  <a class="xlink" href="#p18">{(f'''भाव देखें (पृ. 19) →''' if hi else f'''See the houses (p.19) →''')}</a>
</div><div class="pno">07</div></section>

<!-- 08 LAST 3 YEARS 1 -->
<section class="page"><div class="col">
  <div class="eyebrow terra">{(f'''पिछले तीन साल''' if hi else f'''The last three years''')}</div>
  <h2 class="head">{(f'''यह इतना कठिन क्यों लगा''' if hi else f'''Why it felt so hard''')}</h2>
  <div class="rule"></div>
  <div class="verdict terra sum"><svg class="ic"><use href="#i-hourglass"/></svg>{(f''' पिछले तीन साल जैसे रहे वैसे क्यों रहे — चक्र, आपकी मेहनत नहीं।''' if hi else f''' Why the last three years were the way they were — the cycle, not your effort.''')}</div>
  <div class="lead">{lead_last3}</div>
  <div class="pts">
    {last_pts}
  </div>
  <a class="xlink" href="#p20">{(f'''समय-रेखा देखें (पृ. 21) →''' if hi else f'''See the timeline (p.21) →''')}</a>
</div><div class="pno">08</div></section>

<!-- 09 LAST 3 YEARS 2 -->
<section class="page"><div class="col">
  <div class="eyebrow terra">{(f'''पिछले तीन साल''' if hi else f'''The last three years''')}</div>
  <h2 class="head">{(f'''ढंग — और उसका मतलब''' if hi else f'''The pattern — and what it means''')}</h2>
  <div class="rule"></div>
  <div class="callout dk"><div class="ch"><svg class="ic"><use href="#i-clock"/></svg>{(f''' पूरा दौर, एक पंक्ति में''' if hi else f''' The whole stretch, in one line''')}</div><p>{(f'''{fh(p.get("last3", {}), "lead")}''' if hi else f'''{p.get("last3", {}).get("lead", "")}''')}</p></div>
  <div class="pts">
    <div class="pt good"><svg class="ic pi"><use href="#i-trend"/></svg><div class="tx"><b>{(f'''यह अब हल्का हो रहा है''' if hi else f'''It is lifting now''')}</b>{(f'''मौजूदा {cur_lord_hi} दौर {cur_md["to"]} तक चलता है{(", और साढ़े साती " + sade_ends_hi + " तक पूरी तरह हट जाती है") if sade_active else ""}। ख़ास बात — आपका मज़बूत दौर, {window_label_hi}, ठीक तभी खुलता है जब यह दबाव हल्का होता है।''' if hi else f'''The current {cur_md["lord"]} period runs to {cur_md["to"]}{(", and Sade Sati fully lifts by " + sade_ends) if sade_active else ""}. Crucially, your strong window — {window_label} — opens as that pressure eases.''')}</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-compass"/></svg><div class="tx"><b>{(f'''यह क्यों मायने रखता है''' if hi else f'''Why this matters''')}</b>{(f'''जिस चार्ट ने कठिन सालों को समझाया, वही अच्छे साल भी थामे हुए है। आप जो महसूस कर रहे हैं वह एक चक्र का मोड़ है, आपके पूरे कारोबारी जीवन का आकार नहीं।''' if hi else f'''The same chart that explained the hard years also holds the good ones. What you're feeling is the turning point of a cycle, not the shape of your whole business life.''')}</div></div>
  </div>
  <a class="xlink" href="#p20">{(f'''समय-रेखा देखें (पृ. 21) →''' if hi else f'''See the timeline (p.21) →''')}</a>
</div><div class="pno">09</div></section>

<!-- 10 STRONG WINDOW 1 -->
<section class="page"><div class="col">
  <div class="eyebrow">{(f'''जब रास्ता खुलता है''' if hi else f'''When the road opens''')}</div>
  <h2 class="head">{(f'''आपका सबसे मज़बूत दौर''' if hi else f'''Your strongest window''')}</h2>
  <div class="rule"></div>
  <div class="herocard"><div class="hd">{(f'''{window_label_hi} ''' if hi else f'''{window_label} ''')}<span class="hg">{(f'''मज़बूत''' if hi else f'''STRONG''')}</span></div>
    <p>{(f'''{sw_body}''' if hi else f'''{sw.get("body", "")}''')}</p></div>
  <div class="pts">
    <div class="pt good"><svg class="ic pi"><use href="#i-check"/></svg><div class="tx"><b>{(f'''क्या करें''' if hi else f'''What to do''')}</b>{(f'''{" ".join(sw_do)}''' if hi else f'''{" ".join(sw.get("do", []))}''')}</div></div>
    <div class="pt warn"><svg class="ic pi"><use href="#i-alert"/></svg><div class="tx"><b>{(f'''क्या न करें''' if hi else f'''What not to do''')}</b>{(f'''{" ".join(sw_dont)}''' if hi else f'''{" ".join(sw.get("dont", []))}''')}</div></div>
  </div>
  <a class="xlink" href="#p22">{(f'''यह कैसे आँका गया (पृ. 23) →''' if hi else f'''How this was scored (p.23) →''')}</a>
</div><div class="pno">10</div></section>

<!-- 11 STRONG WINDOW 2 -->
<section class="page"><div class="col">
  <div class="eyebrow">{(f'''जब रास्ता खुलता है''' if hi else f'''When the road opens''')}</div>
  <h2 class="head">{(f'''उसके बाद के साल''' if hi else f'''The years after''')}</h2>
  <div class="rule"></div>
  <div class="lead">{lead_windows}</div>
  {years_wins}
  <div class="note">{(f'''दौर आपकी संभावना बढ़ाते हैं — मेहनत ख़त्म नहीं करते। एक मज़बूत दौर भी आपके लगाए श्रम को ही फल देता है।''' if hi else f'''Windows raise your odds — they don't remove the effort. Even a strong window still rewards the work you put in.''')}</div>
  <a class="xlink" href="#p22">{(f'''यह कैसे आँका गया (पृ. 23) →''' if hi else f'''How this was scored (p.23) →''')}</a>
</div><div class="pno">11</div></section>

<!-- 12 RISK -->
<section class="page"><div class="col">
  <div class="eyebrow terra">{(f'''सावधानी के दौर''' if hi else f'''Careful stretches''')}</div>
  <h2 class="head">{(f'''कब रुककर चलें''' if hi else f'''When to hold back''')}</h2>
  <div class="rule"></div>
  <div class="verdict terra sum"><svg class="ic"><use href="#i-alert"/></svg>{(f''' कब सँभलकर चलें — नीचे दिए सावधानी के दौरों में नक़दी हाथ में रखें और बड़े जोखिम से बचें।''' if hi else f''' When to play it safe — keep cash in hand and avoid big risks in the careful stretches below.''')}</div>
  <div class="lead">{(f'''सावधानी का दौर यह नहीं कहता कि सब कुछ ग़लत होगा — इसका मतलब है कि यहाँ सँभलकर चलना ही समझदारी है। जो कारोबारी जानता है कि नक़दी तंग रहेगी, वह पहले से उसकी योजना बना लेता है।''' if hi else f'''A caution window doesn't mean everything goes wrong — it means being careful here is the smart play. The owner who knows cash will be tight simply plans for it in advance.''')}</div>
  <div class="pts">
    {careful_pts}
  </div>
  <a class="xlink" href="#p24">{(f'''कारण देखें (पृ. 25) →''' if hi else f'''See why (p.25) →''')}</a>
</div><div class="pno">12</div></section>

<!-- 13 MONEY 1 -->
<section class="page"><div class="col">
  <div class="eyebrow">{(f'''पैसा और नक़दी-प्रवाह''' if hi else f'''Money &amp; cash flow''')}</div>
  <h2 class="head">{(f'''पैसा आपके लिए कैसे चलता है''' if hi else f'''How money moves for you''')}</h2>
  <div class="rule"></div>
  <div class="verdict gold sum"><svg class="ic"><use href="#i-coins"/></svg>{(f''' पैसा कैसे आता और जाता है — कमाई, बढ़ोतरी, और कहाँ रिसता है।''' if hi else f''' How money comes and goes — the earning, the growing, and where it leaks.''')}</div>
  <div class="lead">{lead_money}</div>
  <div class="pts">
    <div class="pt"><svg class="ic pi"><use href="#i-coins"/></svg><div class="tx"><b>{(f'''आप कैसे कमाते हैं''' if hi else f'''How you earn''')}</b>{(f'''{fh(money, "earn_leak")}।''' if hi else f'''{money.get("earn_leak", "")}.''')}</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-trend"/></svg><div class="tx"><b>{(f'''लाभ कैसे आता है''' if hi else f'''How gains arrive''')}</b>{(f'''{fh(money, "gains")}।''' if hi else f'''{money.get("gains", "")}.''')}</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-shield"/></svg><div class="tx"><b>{(f'''एक भंडार रखें''' if hi else f'''Keep a reserve''')}</b>{(f'''{fh(money, "reserve")}''' if hi else f'''{money.get("reserve", "")}''')}</div></div>
  </div>
  <a class="xlink" href="#p26">{(f'''धन-जाँच देखें (पृ. 27) →''' if hi else f'''See the wealth check (p.27) →''')}</a>
</div><div class="pno">13</div></section>

<!-- 14 MONEY 2 -->
<section class="page"><div class="col">
  <div class="eyebrow">{(f'''पैसा और नक़दी-प्रवाह''' if hi else f'''Money &amp; cash flow''')}</div>
  <h2 class="head">{(f'''आपकी धन-क्षमता''' if hi else f'''Your wealth potential''')}</h2>
  <div class="rule"></div>
  <div class="callout"><div class="ch"><svg class="ic"><use href="#i-gem"/></svg>{(f''' {"आपके पास एक धन-संयोग है" if dy_present else "मेहनत से बना धन"}''' if hi else f''' {"You have a wealth combination" if dy_present else "Wealth built by effort"}''')}</div><p>{dy_line}</p></div>
  <div class="pts">
    <div class="pt"><svg class="ic pi"><use href="#i-coins"/></svg><div class="tx"><b>{(f'''आपका धन असल में कैसे बढ़ता है''' if hi else f'''How your wealth actually grows''')}</b>{(f'''{fh(money, "earn_leak")}, इसलिए थामे रखना ही असली काम है — और {fh(money, "gains")}।''' if hi else f'''{money.get("earn_leak", "")}, so holding on is the real work — and {money.get("gains", "")}.''')}</div></div>
    <div class="pt good"><svg class="ic pi"><use href="#i-trend"/></svg><div class="tx"><b>{(f'''आपके मज़बूत दौर के सबसे अच्छे धन-वर्ष''' if hi else f'''Best money years from your strong window''')}</b>{(f'''जैसे-जैसे {window_lord_hi} दौर जमता है ({window_label_hi}), आपका धन-ढंग सचमुच जीवंत हो उठता है। धन बनाने के आपके सबसे मज़बूत साल अब भी आपके आगे हैं।''' if hi else f'''As the {window_lord} period settles in ({window_label}), your wealth pattern truly comes alive. Your strongest years for building money are still ahead of you.''')}</div></div>
  </div>
</div><div class="pno">14</div></section>

<!-- 15 OBSTRUCTION -->
<section class="page"><div class="col">
  <div class="eyebrow terra">{(f'''क्या आपको रोक रहा है''' if hi else f'''What's holding you''')}</div>
  <h2 class="head">{(f'''रुकावटें, ईमानदारी से''' if hi else f'''The blocks, honestly''')}</h2>
  <div class="rule"></div>
  <div class="callout dk"><div class="ch"><svg class="ic"><use href="#i-hourglass"/></svg>{(f''' {("साढ़े साती (" + sade_phase_hi + ") — " + sade_ends_hi + " तक") if sade_active else "मौजूदा परखने वाला दौर"}''' if hi else f''' {("Sade Sati (" + sade_phase + ") — until " + sade_ends) if sade_active else "The current testing phase"}''')}</div><p>{(f'''{("शनि आपके चंद्र पर बैठा है, इस चक्र का सबसे भारी मौसम। यह देरी, कम आत्मविश्वास और पैसे की चिंता लाता है — पर यह एक तय समाप्ति-तिथि वाली परीक्षा है, और जो अनुशासन से इसे पार करते हैं वे और मज़बूत होकर निकलते हैं।") if sade_active else "मौजूदा उप-दौर विस्तार से ज़्यादा धीरज माँगता है। यह गुज़र जाता है — और आगे का नक़्शा ठीक-ठीक दिखाता है कि कब।"}''' if hi else f'''{("Saturn is sitting on your Moon, the heaviest weather of this cycle. It brings delays, low confidence, and money worry — but it is a test with a fixed end date, and those who ride it out with discipline come out stronger.") if sade_active else ("The current sub-period asks for patience more than expansion. It passes — and the roadmap ahead shows exactly when.")}''')}</p></div>
  <div class="pts">
    <div class="pt warn"><svg class="ic pi"><use href="#i-moon"/></svg><div class="tx"><b>{(f'''छाया ग्रह''' if hi else f'''The shadow planets''')}</b>{(f'''राहु आपके {ordh(rahu_h)} भाव में और केतु आपके {ordh(ketu_h)} भाव में बैठा है — मिलकर ये ध्यान बिखेरते हैं और बेचैनी व अति-सोच जोड़ते हैं। यह हल्की रुकावट {cur_lord_hi} दौर के बंद होते ही ({cur_md["to"]}) हल्की पड़ जाती है।''' if hi else f'''Rahu sits in your {_vy_ordinal(rahu_h)} house and Ketu in your {_vy_ordinal(ketu_h)} — together they scatter focus and add restlessness and over-thinking. This lighter block eases as the {cur_md["lord"]} period closes ({cur_md["to"]}).''')}</div></div>
    <div class="pt good"><svg class="ic pi"><use href="#i-check"/></svg><div class="tx"><b>{(f'''इनमें से कुछ भी स्थायी नहीं''' if hi else f'''None of it is permanent''')}</b>{(f'''दोनों रुकावटें गुज़रने वाले चक्र हैं, आपके चार्ट का आकार नहीं। इन्हें नाम देना ही इन्हें सँभालने का पहला क़दम है।''' if hi else f'''Both blocks are passing cycles, not the shape of your chart. Naming them is the first step to managing them.''')}</div></div>
  </div>
  <a class="xlink" href="#p24">{(f'''विवरण देखें (पृ. 25) →''' if hi else f'''See the detail (p.25) →''')}</a>
</div><div class="pno">15</div></section>

<!-- 16 REMEDIES -->
<section class="page"><div class="col">
  <div class="eyebrow">{(f'''उपाय और आपकी योजना''' if hi else f'''Remedies &amp; your plan''')}</div>
  <h2 class="head">{(f'''असल में क्या करें''' if hi else f'''What to actually do''')}</h2>
  <div class="rule"></div>
  <div class="callout"><div class="ch"><svg class="ic"><use href="#i-check"/></svg>{(f''' सरल, शास्त्रीय उपाय''' if hi else f''' Simple, classical remedies''')}</div><p>{rem_note}</p></div>
  <div class="pts">
    {rem_pts}
  </div>
</div><div class="pno">16</div></section>

<!-- 17 KUNDLI -->
<section class="page" id="p16"><div class="col">
  <div class="eyebrow">{(f'''आपका चार्ट · प्रमाण''' if hi else f'''Your chart · the proof''')}</div>
  <h2 class="head">{(f'''आपकी कुंडली''' if hi else f'''Your kundli''')}</h2>
  <div class="rule"></div>
  <div class="kundli">
    {kundli_cells}
    {kundli_center}
  </div>
  <div class="klegend">{(f'''आपकी जन्म-कुंडली, दक्षिण-भारतीय शैली में · लग्न सुनहरे में चिह्नित। इस रिपोर्ट का हर पठन इसी चार्ट से गणना किया गया है — कुछ भी अनुमान से नहीं, और कोई भी ज्योतिषी इसे जाँच सकता है।''' if hi else f'''Your birth chart, South-Indian style · Ascendant marked in gold. Every reading in this report is calculated from this chart — nothing is guessed, and any astrologer can verify it.''')}</div>
</div><div class="pno">17</div></section>

<!-- 18 PLANETS -->
<section class="page"><div class="col">
  <div class="eyebrow">{(f'''आपका चार्ट · प्रमाण''' if hi else f'''Your chart · the proof''')}</div>
  <h2 class="head">{(f'''हर ग्रह, अपनी जगह''' if hi else f'''Every planet, placed''')}</h2>
  <div class="rule"></div>
  <div class="tscroll"><table class="k">
    <tr><th>{(f'''ग्रह''' if hi else f'''Planet''')}</th><th>{(f'''राशि''' if hi else f'''Sign''')}</th><th>{(f'''भाव''' if hi else f'''House''')}</th><th>{(f'''इसका मतलब''' if hi else f'''What it means''')}</th></tr>
    {planet_rows}
  </table></div>
  <div class="pts" style="margin-top:14px">
    {asc_pt}
    {loaded_pt}
  </div>
</div><div class="pno">18</div></section>

<!-- 19 HOUSES 1 -->
<section class="page" id="p18"><div class="col">
  <div class="eyebrow">{(f'''आपका चार्ट · कारोबारी भाव''' if hi else f'''Your chart · business houses''')}</div>
  <h2 class="head">{(f'''वे भाव जो मायने रखते हैं''' if hi else f'''The houses that matter''')}</h2>
  <div class="rule"></div>
  <div class="lead">{(f'''कुछ ही भाव किसी कारोबार को चलाते हैं। ये वे हैं जिन्हें आपका चार्ट सबसे आगे रखता है।''' if hi else f'''A handful of houses run a business. Here are the ones your chart puts front and centre.''')}</div>
  <div class="pts">
    {houses_pts_1}
  </div>
</div><div class="pno">19</div></section>

<!-- 20 HOUSES 2 -->
<section class="page"><div class="col">
  <div class="eyebrow">{(f'''आपका चार्ट · कारोबारी भाव''' if hi else f'''Your chart · business houses''')}</div>
  <h2 class="head">{(f'''लाभ, मज़बूती और भरा हुआ कोना''' if hi else f'''Gains, strength &amp; the loaded corner''')}</h2>
  <div class="rule"></div>
  <div class="pts">
    {houses_pts_2}
  </div>
</div><div class="pno">20</div></section>

<!-- 21 DASHA 1 -->
<section class="page" id="p20"><div class="col">
  <div class="eyebrow">{(f'''आपका चार्ट · समय-रेखा''' if hi else f'''Your chart · timeline''')}</div>
  <h2 class="head">{(f'''आपकी समय-रेखा — हाल का दौर''' if hi else f'''Your timeline — the recent stretch''')}</h2>
  <div class="rule"></div>
  <div class="lead">{(f'''आपका जीवन ग्रहों के दौरों में चलता है, जिन्हें दशा कहते हैं। ये हाल के उप-दौर हैं — और ये आपके पीछे के दौर को समझाते हैं।''' if hi else f'''Your life runs in planetary periods, called dashas. These are the recent sub-periods — and they explain the stretch behind you.''')}</div>
  <div class="tl">
    {last_tl}
  </div>
</div><div class="pno">21</div></section>

<!-- 22 DASHA 2 -->
<section class="page"><div class="col">
  <div class="eyebrow">{(f'''आपका चार्ट · समय-रेखा''' if hi else f'''Your chart · timeline''')}</div>
  <h2 class="head">{(f'''आपकी समय-रेखा — आगे के साल''' if hi else f'''Your timeline — the years ahead''')}</h2>
  <div class="rule"></div>
  <div class="lead">{(f'''और ये वे दौर हैं जो आगे चलते हैं — आपके सामने के रास्ते का आकार।''' if hi else f'''And these are the periods that take over next — the shape of the road in front of you.''')}</div>
  <div class="tl">
    {road_tl}
  </div>
</div><div class="pno">22</div></section>

<!-- 23 SCORING 1 -->
<section class="page" id="p22"><div class="col">
  <div class="eyebrow">{(f'''आपका चार्ट · दौर की आँकड़-गणना''' if hi else f'''Your chart · window scoring''')}</div>
  <h2 class="head">{(f'''&ldquo;मज़बूत&rdquo; क्यों — दिखाया गया''' if hi else f'''Why "Strong" — shown''')}</h2>
  <div class="rule"></div>
  <div class="lead">{(f'''इस रिपोर्ट में कुछ भी अनुमान से नहीं है। आपका सबसे मज़बूत दौर अपनी श्रेणी आपके चार्ट के साफ़ तथ्यों से कमाता है। यहाँ बताया गया है कि {window_lord_hi} का दौर क्यों अलग दिखता है।''' if hi else f'''Nothing in this report is guessed. Your strongest window earns its grade from clear facts in your chart. Here is why {window_lord}'s window stands out.''')}</div>
  <div class="pts">
    {strong_pts}
  </div>
</div><div class="pno">23</div></section>

<!-- 24 SCORING 2 -->
<section class="page"><div class="col">
  <div class="eyebrow">{(f'''आपका चार्ट · दौर की आँकड़-गणना''' if hi else f'''Your chart · window scoring''')}</div>
  <h2 class="head">{(f'''बाक़ी दौर''' if hi else f'''The other windows''')}</h2>
  <div class="rule"></div>
  <div class="pts">
    {other_pts}
  </div>
  <div class="note"><b>{(f'''दौर मौक़े हैं, तय तारीख़ें नहीं।''' if hi else f'''Windows are chances, not fixed dates.''')}</b>{(f''' ये आपकी संभावना बढ़ाते हैं; मेहनत फिर भी आपको ही लानी है।''' if hi else f''' They raise your odds; the effort is still yours to bring.''')}</div>
</div><div class="pno">24</div></section>

<!-- 25 SADE SATI 1 -->
<section class="page" id="p24"><div class="col">
  <div class="eyebrow">{(f'''आपका चार्ट · साढ़े साती''' if hi else f'''Your chart · Sade Sati''')}</div>
  <h2 class="head">{(f'''साढ़े साती, समझाई गई''' if hi else f'''Sade Sati, explained''')}</h2>
  <div class="rule"></div>
  <div class="pts">
    <div class="pt"><svg class="ic pi"><use href="#i-saturn"/></svg><div class="tx"><b>{(f'''यह क्या है''' if hi else f'''What it is''')}</b>{(f'''{("शनि आपके चंद्र के ऊपर से गुज़र रहा है — साढ़े सात साल की साढ़े साती का " + sade_phase_hi + "। यह " + sade_ends_hi + " के आसपास ख़त्म होता है।") if sade_active else "साढ़े साती अभी आपके चंद्र पर नहीं चल रही — शनि का सबसे भारी चक्र इस दौर की कहानी नहीं है।"}''' if hi else f'''{("Saturn is passing over your Moon — the " + sade_phase + " of the seven-and-a-half-year Sade Sati. It ends around " + sade_ends + ".") if sade_active else "Sade Sati is not running on your Moon right now — Saturn's heaviest cycle is not the story of this phase for you."}''')}</div></div>
    <div class="pt warn"><svg class="ic pi"><use href="#i-alert"/></svg><div class="tx"><b>{(f'''आप क्या महसूस करते हैं''' if hi else f'''What you feel''')}</b>{(f'''देरी, भारी फ़ैसले, और पैसे को लेकर एक टिकी हुई चिंता। यह असली है, और — ख़ास बात — यह अस्थायी है।''' if hi else f'''Delays, heavier decisions, and a steadier worry about money. It's real, and — importantly — it's temporary.''')}</div></div>
    <div class="pt good"><svg class="ic pi"><use href="#i-check"/></svg><div class="tx"><b>{(f'''अच्छी ख़बर''' if hi else f'''The good news''')}</b>{(f'''{("इसका अंत (" + sade_ends_hi + ") आपके मज़बूत " + window_label_hi + " दौर के पास पड़ता है — इसलिए बोझ लगभग तभी उतरता है जब आपके सबसे अच्छे साल शुरू होते हैं।") if sade_active else ("आपका सबसे मज़बूत दौर — " + window_label_hi + " — रास्ते का वह हिस्सा है जिसके इर्द-गिर्द योजना बनानी है।")}''' if hi else f'''{("Its end (" + sade_ends + ") falls near your strong " + window_label + " window — so the weight lifts close to when your best years get going.") if sade_active else ("Your strongest window — " + window_label + " — is the part of the road to plan around.")}''')}</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-clock"/></svg><div class="tx"><b>{(f'''दो अलग-अलग घड़ियाँ''' if hi else f'''Two different clocks''')}</b>{(f'''{clarity_hi}''' if hi else f'''{clarity_en}''')}</div></div>
  </div>
</div><div class="pno">25</div></section>

<!-- 26 SADE SATI 2 -->
<section class="page"><div class="col">
  <div class="eyebrow">{(f'''आपका चार्ट · छाया ग्रह''' if hi else f'''Your chart · the shadow planets''')}</div>
  <h2 class="head">{(f'''राहु, केतु और छायाएँ''' if hi else f'''Rahu, Ketu &amp; the shadows''')}</h2>
  <div class="rule"></div>
  <div class="pts">
    <div class="pt warn"><svg class="ic pi"><use href="#i-moon"/></svg><div class="tx"><b>{(f'''राहु आपके {ordh(rahu_h)} भाव में''' if hi else f'''Rahu in your {_vy_ordinal(rahu_h)} house''')}</b>{(f'''मौजूदा दौर में चिंता, बेचैनी और अति-सोच जोड़ता है — वही रोज़मर्रा का तनाव जो आप महसूस करते रहे हैं।''' if hi else f'''Adds worry, restlessness and over-thinking to the current stretch — the day-to-day strain you've been feeling.''')}</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-coins"/></svg><div class="tx"><b>{(f'''केतु आपके {ordh(ketu_h)} भाव में''' if hi else f'''Ketu in your {_vy_ordinal(ketu_h)} house''')}</b>{(f'''आपको छोड़ने की ओर खींचता है — यही एक वजह है कि अभी ध्यान और, कभी-कभी, पैसा इतनी आसानी से फिसल जाता है।''' if hi else f'''Pulls you toward letting-go — part of why focus and, at times, money slip away so easily right now.''')}</div></div>
    <div class="pt good"><svg class="ic pi"><use href="#i-check"/></svg><div class="tx"><b>{(f'''ये {cur_lord_hi} दौर के साथ हल्के पड़ते हैं''' if hi else f'''They fade with the {cur_md["lord"]} period''')}</b>{(f'''जैसे ही यह बंद होता है ({cur_md["to"]}), ये छाया प्रभाव अपनी पकड़ ढीली कर देते हैं। ये गुज़रने वाले गोचर हैं, आपके चार्ट की स्थायी बनावट नहीं।''' if hi else f'''As it closes ({cur_md["to"]}), these shadow influences loosen their grip. They are passing transits, not permanent features of your chart.''')}</div></div>
  </div>
</div><div class="pno">26</div></section>

<!-- 27 DHANA -->
<section class="page" id="p26"><div class="col">
  <div class="eyebrow">{(f'''आपका चार्ट · धन''' if hi else f'''Your chart · wealth''')}</div>
  <h2 class="head">{(f'''धन-संयोग''' if hi else f'''Wealth combinations''')}</h2>
  <div class="rule"></div>
  <div class="lead">{(f'''हमने आपके चार्ट में शास्त्रीय धन-संयोगों (धन योग) की जाँच की। यहाँ बताया गया है कि हमें क्या मिला।''' if hi else f'''We checked your chart for the classical wealth combinations (Dhana Yogas). Here is what we found.''')}</div>
  <div class="pts">
    <div class="pt {"good" if dy_present else ""}"><svg class="ic pi"><use href="#i-gem"/></svg><div class="tx"><b>{(f'''{"आपके पास एक धन योग है" if dy_present else "सोचे-समझे प्रयास से धन"}''' if hi else f'''{"You have a wealth yoga" if dy_present else "Wealth by deliberate effort"}''')}</b>{dy_line}</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-trend"/></svg><div class="tx"><b>{(f'''लाभ कहाँ से आता है''' if hi else f'''Where gains come from''')}</b>{(f'''{fh(money, "gains")}।''' if hi else f'''{money.get("gains", "")}.''')}</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-shield"/></svg><div class="tx"><b>{(f'''नक़दी पर पकड़ बनाए रखें''' if hi else f'''Hold the line on cash''')}</b>{(f'''{fh(money, "reserve")}''' if hi else f'''{money.get("reserve", "")}''')}</div></div>
  </div>
</div><div class="pno">27</div></section>

<!-- 28 YEAR BY YEAR -->
<section class="page"><div class="col">
  <div class="eyebrow">{(f'''आपका चार्ट · साल-दर-साल''' if hi else f'''Your chart · year by year''')}</div>
  <h2 class="head">{(f'''आने वाले साल''' if hi else f'''The next years''')}</h2>
  <div class="rule"></div>
  <div class="lead">{(f'''एक झटपट साल-दर-साल नज़र, ताकि आप आने वाले का आकार थामे रह सकें।''' if hi else f'''A quick year-by-year view, so you can hold the shape of what's coming.''')}</div>
  <div class="tl">
    {yby_tl}
  </div>
  <div class="note" style="text-align:center;border:0">{(f'''मार्गदर्शन, कोई गारंटी नहीं। समय-दौर मौक़े हैं, तय तारीख़ें नहीं। यह क़ानूनी या वित्तीय सलाह नहीं है।''' if hi else f'''Guidance, not a guarantee. Timing windows are chances, not fixed dates. This is not legal or financial advice.''')}</div>
</div><div class="pno">28</div></section>

<!-- 29 ENDING -->
<section class="page end"><div class="col">
  <div class="eyebrow">{(f'''आभार के साथ''' if hi else f'''With gratitude''')}</div>
  <h2 class="head">{(f'''धन्यवाद, {first}''' if hi else f'''Thank you, {first}''')}</h2>
  <div class="rule"></div>
  <div class="lead" style="text-align:center;max-width:34ch">{(f'''अपने कारोबारी सवालों के लिए AxtroShastra पर भरोसा करने के लिए धन्यवाद। हमें उम्मीद है कि यह पठन आपको आगे के रास्ते के बारे में स्पष्टता — और थोड़ी शांति — देगा।''' if hi else f'''Thank you for trusting AxtroShastra with your business questions. We hope this reading brings you clarity — and a little calm — about the road ahead.''')}</div>
  <div class="intro" style="text-align:center;margin-top:14px">{(f'''अपने जीवन के बारे में कोई और सवाल? इनमें से हर एक हमारी साइट पर है, उसी ईमानदार तरीक़े से गणना किया हुआ:''' if hi else f'''Have another question about your life? Each of these is on our site, computed the same honest way:''')}</div>
  <div class="svc">
    <div class="s"><svg class="ic si"><use href="#i-people"/></svg><div class="st"><b>{(f'''अनुकूलता''' if hi else f'''Compatibility''')}</b>{(f'''क्या दो चार्ट सचमुच साथ चलते हैं।''' if hi else f'''Whether two charts truly work together.''')}</div></div>
    <div class="s"><svg class="ic si"><use href="#i-check"/></svg><div class="st"><b>{(f'''विवाह का समय''' if hi else f'''Marriage Timing''')}</b>{(f'''विवाह कब सबसे संभव है, और किसके साथ।''' if hi else f'''When marriage is most likely, and with whom.''')}</div></div>
    <div class="s"><svg class="ic si"><use href="#i-compass"/></svg><div class="st"><b>{(f'''नौकरी बदलना''' if hi else f'''Job Change''')}</b>{(f'''नौकरी बदलने का सही समय — और आगे कहाँ जाएँ।''' if hi else f'''The right time to switch jobs — and where to go next.''')}</div></div>
    <div class="s"><svg class="ic si"><use href="#i-trend"/></svg><div class="st"><b>{(f'''व्यापार — कारोबार''' if hi else f'''Vyapar — Business''')}</b>{(f'''यही रिपोर्ट: कब बनाएँ, कब रुकें।''' if hi else f'''This report: when to build, when to hold.''')}</div></div>
  </div>
  <div class="endbrand">{(f'''हर AxtroShastra रिपोर्ट आपके असली जन्म-चार्ट से गणना की जाती है &mdash; कभी अनुमान से नहीं। यही हमारा वादा है।''' if hi else f'''Every AxtroShastra report is computed from your real birth chart &mdash; never guessed. That is our promise.''')}</div>
  <div class="cov-trust" style="opacity:.8">{(f'''www.axtroshastra.com &middot; Swiss Ephemeris &middot; लाहिरी अयनांश''' if hi else f'''www.axtroshastra.com &middot; Swiss Ephemeris &middot; Lahiri ayanamsa''')}</div>
</div><div class="pno">29</div></section>

<style>@media screen{{body{{padding-bottom:92px}}}}
#ax-stickybar{{position:fixed;left:0;right:0;bottom:0;z-index:9997;
background:rgba(250,245,237,.97);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);
border-top:1px solid rgba(185,134,46,.35);box-shadow:0 -8px 24px rgba(48,34,14,.16);
padding:10px 14px calc(10px + env(safe-area-inset-bottom))}}
#ax-stickybar .inner{{max-width:430px;margin:0 auto;display:flex;gap:10px}}
#ax-stickybar a{{flex:1;display:flex;align-items:center;justify-content:center;gap:8px;
min-height:52px;text-align:center;text-decoration:none;border-radius:14px;padding:12px 10px;
font:700 16px/1.15 var(--sans);letter-spacing:.01em;
-webkit-tap-highlight-color:transparent;transition:transform .08s ease,filter .15s ease}}
#ax-stickybar a:active{{transform:scale(.97);filter:brightness(1.08)}}
#ax-stickybar svg{{width:19px;height:19px;flex:none}}
#ax-stickybar .pdf{{background:var(--ink);color:#F5EEE0;box-shadow:0 6px 16px rgba(42,35,56,.28)}}
#ax-stickybar .pdf svg{{color:var(--gold2)}}
#ax-stickybar .wa{{background:var(--green);color:#fff;box-shadow:0 6px 16px rgba(62,125,90,.28)}}
@media (min-width:640px){{#ax-stickybar a{{min-height:48px;font-size:15px}}}}
@media print{{#ax-stickybar{{display:none!important}}}}</style>
<div id='ax-stickybar'><div class='inner'>
<a class='pdf' id='ax-pdf' href='#' onclick='window.print();return false;'><svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'><path d='M12 3v12'/><path d='M6 11l6 6 6-6'/><path d='M4 21h16'/></svg>{(f'''PDF डाउनलोड करें''' if hi else f'''Download PDF''')}</a>
<a class='wa' href='#' onclick='axShare();return false;'><svg viewBox='0 0 24 24' fill='currentColor' aria-hidden='true'><path d='M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 2a8 8 0 1 1-4.1 14.9l-.5-.3-2.6.7.7-2.5-.3-.5A8 8 0 0 1 12 4zm-3.1 4.3c-.2 0-.5.1-.7.3-.7.7-1 1.6-.8 2.6.3 1.2 1 2.4 2.1 3.5 1.4 1.4 3 2.3 4.6 2.5.8.1 1.6-.2 2.2-.8.2-.2.3-.5.3-.8l-.1-.7c-.1-.2-.2-.4-.5-.5l-1.7-.8a.8.8 0 0 0-.9.2l-.5.5c-.1.2-.4.2-.6.1a6.7 6.7 0 0 1-2.9-2.9c-.1-.2 0-.4.1-.6l.5-.5c.2-.2.3-.6.2-.9l-.8-1.7c-.1-.2-.3-.4-.5-.4l-.5-.1z'/></svg>{(f'''WhatsApp पर साझा करें''' if hi else f'''Share on WhatsApp''')}</a>
</div></div>
<script>{(f'''
window.axShare=function(){{var url=location.href;var t='AxtroShastra से मेरी व्यवसाय वृद्धि रिपोर्ट देखें';if(navigator.share){{navigator.share({{title:'AxtroShastra',text:t,url:url}}).catch(function(){{}});}}else{{window.open('https://wa.me/?text='+encodeURIComponent(t+' '+url),'_blank');}}}};
''' if hi else f'''
window.axShare=function(){{var url=location.href;var t='Check out my business growth report from AxtroShastra';if(navigator.share){{navigator.share({{title:'AxtroShastra',text:t,url:url}}).catch(function(){{}});}}else{{window.open('https://wa.me/?text='+encodeURIComponent(t+' '+url),'_blank');}}}};
''')}</script>
</body></html>"""
