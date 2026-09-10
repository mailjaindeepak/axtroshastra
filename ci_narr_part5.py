"""Career Intelligence — narrative personalization layer, Part V (Money & Success).

Personalizes the five prose/exhibit pages of "Part IV — Money & Professional
Success" so no page ships the mock persona's chart-derived claims to another
buyer (brief Rule 2). Same contract as ci_narrative.py: each builder returns
list[(old, new)] of exact string replacements against career_intelligence_assets
.CI_BODY; `new` keeps the SAME HTML structure and SVG `<use href="#i-..."/>`
icons as `old`, only the human-readable text/number changes. Calm analyst voice;
em-dashes are house style in report prose (Rule 4). Helpers copied (not imported)
to keep this module independent.

Pages (by heading):
  P35 "Your relationship with money"  — ddims stability/risk/entrepreneurial + Venus/Jupiter dscore
  P36 "Two routes to the same goal"   — naukri lean (job vs enterprise)
  P37 "Career vs enterprise" (bars)   — ddims + naukri lean; bar widths are real functions of ddims
  P38 "When to expand, when to hold"  — three_year peak_year + best_window
  P39 "Visibility & authority ahead"  — Sun dscore, leadership ddim, Saturn dscore

NOTE on the naukri lean sign: the engine (_naukri_apnakaam_meter) defines
positive lean = Naukri/job-leaning, negative = Apnakaam/enterprise-leaning. The
brief's parenthetical had this inverted; we branch on the engine's own `label`
field ("Naukri-leaning"/"Apnakaam-leaning"/"Balanced") so the prose is correct
for a real chart, not the mock.
"""


def _cap(s):
    return s[:1].upper() + s[1:]


def _ranked(ddims):
    return sorted(ddims, key=ddims.get, reverse=True)


def _lvl(v):
    return "high" if v >= 76 else "mod" if v >= 62 else "low"


def _dscore(payload, planet):
    return payload["chart"]["planets"].get(planet, {}).get("dscore", 50)


def _lean(payload):
    """career | enterprise | balanced, from the engine's own naukri label."""
    label = payload["entrepreneurial"]["label"]
    if label == "Naukri-leaning":
        return "career"
    if label == "Apnakaam-leaning":
        return "enterprise"
    return "balanced"


def _clamp(v):
    return max(12, min(96, round(v)))


# ---------------------------------------------------------------- Part V -------
def _p35_money(payload, ddims):
    """Your relationship with money — Orientation / Risk / Stability cards."""
    st, en, rk = ddims["stability"], ddims["entrepreneurial"], ddims["risk"]
    fin = round((_dscore(payload, "Venus") + _dscore(payload, "Jupiter")) / 2)

    orientation = ("You build wealth steadily — accumulation through consistency, not speculation."
                   if st >= en else
                   "You build wealth by backing your own bets — upside you create and own, not just salary set aside.")
    rlvl = _lvl(rk)
    risk = {"high": "Comfortable with calculated risk — you will take a bigger, considered swing when the odds read right.",
            "mod": "Considered, not conservative. You take the risk you understand; dislike it when imposed.",
            "low": "Conservative by default — you protect the base first and add risk only once it is well understood."}[rlvl]
    stability = ("A secure base is the platform every larger bet stands on — and your money indicators back a steady, compounding one."
                 if fin >= 62 else
                 "A base of security is the platform from which you take the bigger bet — build it first, then stretch.")

    return [
        ('<div class="pt"><svg class="pi"><use href="#i-coins"/></svg><div class="tx"><b>Orientation</b><span>You build wealth steadily — accumulation through consistency, not speculation.</span></div></div>',
         f'<div class="pt"><svg class="pi"><use href="#i-coins"/></svg><div class="tx"><b>Orientation</b><span>{orientation}</span></div></div>'),
        ('<div class="pt"><svg class="pi"><use href="#i-alert"/></svg><div class="tx"><b>Risk</b><span>Considered, not conservative. You take risk you understand; dislike it when imposed.</span></div></div>',
         f'<div class="pt"><svg class="pi"><use href="#i-alert"/></svg><div class="tx"><b>Risk</b><span>{risk}</span></div></div>'),
        ('<div class="pt"><svg class="pi"><use href="#i-shield"/></svg><div class="tx"><b>Stability</b><span>A base of security is the platform from which you take the bigger bet.</span></div></div>',
         f'<div class="pt"><svg class="pi"><use href="#i-shield"/></svg><div class="tx"><b>Stability</b><span>{stability}</span></div></div>'),
    ]


def _p36_two_routes(payload, ddims):
    """Two routes to the same goal — the read for you, from the naukri lean."""
    read = {
        "career": "Slightly favours wealth <b>through senior career and advisory work</b>, with enterprise strong as a combined second.",
        "enterprise": "Leans toward wealth <b>through ownership and building your own venture</b>, with a structured senior role as the dependable base.",
        "balanced": "Reads close to even — wealth <b>through senior career or through ownership</b> can both work, and the combined play is the sweet spot.",
    }[_lean(payload)]
    return [
        ('<div class="callout"><div class="ch">The read for you</div><p>Slightly favours wealth <b>through senior career and advisory work</b>, with enterprise strong as a combined second.</p></div>',
         f'<div class="callout"><div class="ch">The read for you</div><p>{read}</p></div>'),
    ]


def _p37_bars(payload, ddims):
    """Career vs enterprise exhibit — 4 bars + 3 legend bullets + read.
    Bar widths are real functions of ddims (owner decision, per brief)."""
    reliability = _clamp(ddims["stability"])
    autonomy = _clamp(ddims["independence"])
    downside = _clamp((ddims["stability"] + (100 - ddims["entrepreneurial"])) / 2)
    upside = _clamp((ddims["entrepreneurial"] + ddims["risk"]) / 2)
    lean = _lean(payload)

    combined = {
        "career": "The steady route leads for you — ownership can layer in on top of it.",
        "enterprise": "Ownership leads for you — a structured base is what keeps the bigger swings safe.",
        "balanced": "Ownership inside structure captures both — your strongest path.",
    }[lean]
    read = {
        "career": "The steady route leads — and ownership inside a structured setting is the natural second act.",
        "enterprise": "Ownership leads — build the structured base first, and the bigger swings become yours to take.",
        "balanced": "Ownership inside a structured setting captures both — your strongest financial path.",
    }[lean]

    return [
        ('<div class="bx g"><div class="bl">Fit with your reliability <span>Career 85</span></div><div class="bt"><i style="width:85%"></i></div></div>',
         f'<div class="bx g"><div class="bl">Fit with your reliability <span>Career {reliability}</span></div><div class="bt"><i style="width:{reliability}%"></i></div></div>'),
        ('<div class="bx"><div class="bl">Fit with your autonomy <span>Enterprise 78</span></div><div class="bt"><i style="width:78%"></i></div></div>',
         f'<div class="bx"><div class="bl">Fit with your autonomy <span>Enterprise {autonomy}</span></div><div class="bt"><i style="width:{autonomy}%"></i></div></div>'),
        ('<div class="bx g"><div class="bl">Downside protection <span>Career 88</span></div><div class="bt"><i style="width:88%"></i></div></div>',
         f'<div class="bx g"><div class="bl">Downside protection <span>Career {downside}</span></div><div class="bt"><i style="width:{downside}%"></i></div></div>'),
        ('<div class="bx"><div class="bl">Upside ceiling <span>Enterprise 82</span></div><div class="bt"><i style="width:82%"></i></div></div>',
         f'<div class="bx"><div class="bl">Upside ceiling <span>Enterprise {upside}</span></div><div class="bt"><i style="width:{upside}%"></i></div></div>'),
        ('<div class="lr"><span class="dot" style="background:#B9862E"></span><span class="lt"><b>Career strengths.</b> Reliability fit (85) and downside protection (88) favour the steady route.</span></div>',
         f'<div class="lr"><span class="dot" style="background:#B9862E"></span><span class="lt"><b>Career strengths.</b> Reliability fit ({reliability}) and downside protection ({downside}) favour the steady route.</span></div>'),
        ('<div class="lr"><span class="dot" style="background:#C9A34E"></span><span class="lt"><b>Enterprise edge.</b> Autonomy fit (78) and upside ceiling (82) reward ownership.</span></div>',
         f'<div class="lr"><span class="dot" style="background:#C9A34E"></span><span class="lt"><b>Enterprise edge.</b> Autonomy fit ({autonomy}) and upside ceiling ({upside}) reward ownership.</span></div>'),
        ('<div class="lr"><span class="dot" style="background:#C9BFA6"></span><span class="lt"><b>Combined play.</b> Ownership inside structure captures both — your strongest path.</span></div>',
         f'<div class="lr"><span class="dot" style="background:#C9BFA6"></span><span class="lt"><b>Combined play.</b> {combined}</span></div>'),
        ('<div class="take"><b>The read</b>Ownership inside a structured setting captures both — your strongest financial path.</div>',
         f'<div class="take"><b>The read</b>{read}</div>'),
    ]


def _p38_expand_hold(payload, ddims):
    """When to expand, when to hold — from three_year peak_year + best_window."""
    pk = payload["three_year"]["peak_year"]
    bw = payload["three_year"]["best_window"]
    window = bw if bw else ("the year-2 window ahead" if pk == 2 else "the window ahead")

    if pk <= 1:  # window is now/near -> lean expand
        exp_t, exp_d = f"The {window} window", "The stronger window is close — this is the time to lean into a larger, considered commitment."
        con_t, con_d = "Right after", "Once you have moved, tighten the base around the bigger commitment."
        lead = "For you the window is close — line up the groundwork now so you can move the moment it opens."
    elif pk >= 3:  # window is later -> lean consolidate/prepare
        exp_t, exp_d = f"The {window} window", "The larger commitment reads better later — prepare for it rather than forcing it now."
        con_t, con_d = "The stretch ahead", "Best spent strengthening the base and the runway, not stretching it early."
        lead = "For you the stronger window sits further out — consolidate now so it pays when it arrives."
    else:  # pk == 2, middle
        exp_t, exp_d = f"The {window} window", "May reward a larger, considered commitment — the time to lean in."
        con_t, con_d = "The current phase", "Better suited to strengthening the base than stretching it."
        lead = "For you, timing matters more than appetite — expand when the groundwork is genuinely set."

    return [
        ('<div class="win"><span class="wg grn">Expand</span><div class="wt">The Year-2 window ahead</div><div class="wd">May reward a larger, considered commitment — the time to lean in.</div></div>',
         f'<div class="win"><span class="wg grn">Expand</span><div class="wt">{exp_t}</div><div class="wd">{exp_d}</div></div>'),
        ('<div class="win"><span class="wg mod">Consolidate</span><div class="wt">The current phase</div><div class="wd">Better suited to strengthening the base than stretching it.</div></div>',
         f'<div class="win"><span class="wg mod">Consolidate</span><div class="wt">{con_t}</div><div class="wd">{con_d}</div></div>'),
        ('<p class="lead">For you, timing matters more than appetite — expand when the groundwork is genuinely set.</p>',
         f'<p class="lead">{lead}</p>'),
    ]


def _p39_recognition(payload, ddims):
    """Visibility & authority ahead — Recognition / Authority / Scope cards."""
    sun = _dscore(payload, "Sun")
    sat = _dscore(payload, "Saturn")
    ld = ddims["leadership"]

    if sun >= 62:
        rec_dt, rec_th, rec_td = "Rising", "Visibility rising to match your work", "Periods ahead are likely to put your contribution in front of the people who decide."
    else:
        rec_dt, rec_th, rec_td = "Emerging", "Recognition catching up to contribution", "Periods ahead may surface value you have quietly delivered."

    if sat >= 62 or ld >= 76:
        auth_th, auth_td = "A shift toward named authority", "Being known for one specific thing is favoured — let that define you."
    else:
        auth_th, auth_td = "Authority earned step by step", "Authority here is built by consistency; each delivered result compounds into standing."

    if ld >= 70:
        scope_th, scope_td = "Larger mandates may arrive", "Bigger remits will come your way — be deliberate about which you accept."
    else:
        scope_th, scope_td = "Scope widening gradually", "Scope grows as trust does — take the mandates that build the record you want."

    return [
        ('<div class="tli"><div class="dt">Emerging</div><div class="th">Recognition catching up to contribution</div><div class="td">Periods ahead may surface value you quietly delivered.</div></div>',
         f'<div class="tli"><div class="dt">{rec_dt}</div><div class="th">{rec_th}</div><div class="td">{rec_td}</div></div>'),
        ('<div class="tli"><div class="dt">Authority</div><div class="th">A shift toward named authority</div><div class="td">Being known for a specific thing is favoured now.</div></div>',
         f'<div class="tli"><div class="dt">Authority</div><div class="th">{auth_th}</div><div class="td">{auth_td}</div></div>'),
        ('<div class="tli"><div class="dt">Scope</div><div class="th">Larger mandates may arrive</div><div class="td">Be deliberate about which you accept.</div></div>',
         f'<div class="tli"><div class="dt">Scope</div><div class="th">{scope_th}</div><div class="td">{scope_td}</div></div>'),
    ]


BUILDERS = [
    _p35_money,
    _p36_two_routes,
    _p37_bars,
    _p38_expand_hold,
    _p39_recognition,
]
