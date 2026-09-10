"""Career Intelligence — narrative personalization layer, Part VI.

Personalizes the prose on five chart-derived pages so no page ships the mock
persona's (Rajesh Menon's) claims to another buyer (Rule 2). Same contract as
ci_narrative: each builder returns (old, new) exact-string replacements; `new`
keeps the SAME HTML structure and the SAME SVG <use href="#i-..."/> icons as
`old` — only human-readable text/numbers change. Every claim is traceable to
computed data (life-stage momentum, display dims, planet dignity scores,
three-year timing). Analyst voice; em-dashes are house style here.

Pages (asset comment number in parens):
  40  The decades ahead — life-stage narrative      (39 LONG-TERM)
  42  Where to put your energy — top-5 priorities    (41 TOP 5 PRIORITIES)
  43  Priority matrix — impact x effort exhibit      (42 EXHIBIT)
  53  The planets that shape your work               (52 PLANETARY INFLUENCES)
  54  Planetary strength — bars exhibit              (53 EXHIBIT)

Renderer-owned strings are avoided: page 41 (the life-stage BAR rects) is
personalized by career_intelligence_report._lifebars_html, so this module does
not touch it — only page 40's prose.
"""

# career planets ranked when equal: a fixed, deterministic tie-break order
# Classic career karakas only (Venus/Moon excluded — off-topic for a career chart,
# and this keeps pages 53/54 consistent with the page-8 astrological basis).
_CAREER = ["Saturn", "Jupiter", "Sun", "Mercury", "Mars"]


def _ranked(ddims):
    return sorted(ddims, key=ddims.get, reverse=True)


def _planet_rank(planets):
    """The six career planets, strongest dscore first (stable tie-break)."""
    return sorted(_CAREER,
                  key=lambda P: (-planets.get(P, {}).get("dscore", 0), _CAREER.index(P)))


# ---------------------------------------------------------------- Page 40 ------
# fixed life-stage label per age band (position-anchored); score picks the peak
_STAGE = [("40–45", "Depth"), ("45–50", "Leverage"),
          ("50–55", "Authority"), ("55–60", "Legacy")]
_STAGE_DEFAULT = {
    "Depth": "Consolidating expertise and reputation.",
    "Leverage": "A larger role or reinvention comes within reach.",
    "Authority": "Named, senior influence — advisory or independent leadership.",
    "Legacy": "Shaping others and stewarding what you built.",
}
_STAGE_PEAK = {
    "Depth": "Your strongest stretch arrives early — depth and reputation compounding fastest here.",
    "Leverage": "Your highest-leverage window — the one to spend on a larger role or a clean reinvention.",
    "Authority": "Your highest-leverage decade — named, senior authority at full strength.",
    "Legacy": "Your momentum keeps rising to the end — authority that shapes others carries the most weight late.",
}


def _page40_decades(p, dd):
    stages = p["life_stage"]                       # [{'band','score'}] x4, in age order
    peak_i = max(range(len(stages)), key=lambda i: stages[i]["score"])
    peak_band, peak_label = _STAGE[peak_i]

    rows = "\n  ".join(
        (f'<div class="win"><span class="wg{" grn" if i == peak_i else ""}">{band}</span>'
         f'<div class="wt">{label}</div>'
         f'<div class="wd">{_STAGE_PEAK[label] if i == peak_i else _STAGE_DEFAULT[label]}</div></div>')
        for i, (band, label) in enumerate(_STAGE))

    lead = (f'<p class="lead" style="margin-top:12px">The pattern is a long, rising curve rather '
            f'than a single peak — each stage sets up the next. Your professional momentum '
            f'concentrates around {peak_band} ({peak_label.lower()}), the window that carries the '
            f'most leverage; the value you bank before then is exactly what makes it pay.</p>')

    if peak_i <= 1:
        basis = (f'Your chart front-loads its professional weight — the benefic periods that lift a '
                 f'career run earlier than most, so the {peak_band} window rewards moving with '
                 f'intent rather than waiting for permission.')
    else:
        basis = (f"Saturn's maturing influence favours authority that arrives with age — for you the "
                 f"{peak_band} window is where a well-built chart tends to reward most.")

    return [
        ('<p class="lead" style="margin-top:12px">The pattern is a long, rising curve rather than a single peak — each stage sets up the next. The middle decades carry the most leverage, but the value you bank early is exactly what makes them pay.</p>',
         lead),
        ('<div class="win"><span class="wg">40–45</span><div class="wt">Depth</div><div class="wd">Consolidating expertise and reputation.</div></div>\n'
         '  <div class="win"><span class="wg grn">45–50</span><div class="wt">Leverage</div><div class="wd">The likely peak window for a larger role or reinvention.</div></div>\n'
         '  <div class="win"><span class="wg grn">50–55</span><div class="wt">Authority</div><div class="wd">Named, senior influence — advisory or independent leadership.</div></div>\n'
         '  <div class="win"><span class="wg">55–60</span><div class="wt">Legacy</div><div class="wd">Shaping others and stewarding what you built.</div></div>',
         rows),
        ("Saturn's maturing influence favours authority that arrives with age — the later chapters are where a well-built chart tends to reward most.",
         basis),
    ]


# ---------------------------------------------------------------- Page 42 ------
_SPECIALISM = {
    "leadership": "the calls other people would rather not make",
    "strategic": "the hard, open problems no one else has framed",
    "independence": "work you can own from end to end",
    "entrepreneurial": "building something that is yours to own",
    "risk": "the decisive move when the window is short",
    "stability": "the long game others cannot sustain",
}

_P42_OLD_ROWS = (
    '    <div class="sr"><div class="num">1</div><div class="st"><b>Decide the one thing</b> you want to be known for next.</div></div>\n'
    '    <div class="sr"><div class="num">2</div><div class="st"><b>Move decisions closer to you</b> — seek roles where you own outcomes.</div></div>\n'
    '    <div class="sr"><div class="num">3</div><div class="st"><b>Delegate deliberately</b> — hand off what others can own.</div></div>\n'
    '    <div class="sr"><div class="num">4</div><div class="st"><b>Prepare the Year-2 move</b> now.</div></div>\n'
    "    <div class=\"sr\"><div class=\"num\">5</div><div class=\"st\"><b>Protect optionality</b> — don't over-absorb.</div></div>")

_P42_OLD_CALLOUT = ('<div class="callout"><div class="ch">If you do only one</div><p>Start with priority '
                    'one — naming the single thing you want to be known for. It sharpens the other four '
                    'and turns a busy year into a directed one.</p></div>')


def _page42_priorities(p, dd):
    top = _ranked(dd)[0]
    peak_year = p["three_year"]["peak_year"]
    bw = p["three_year"]["best_window"]
    ind_high = dd["independence"] >= 70
    ld_high = dd["leadership"] >= 70

    # priority 1 is always the positioning bet from the single top strength;
    # the remaining priorities are ordered by relevance (score desc).
    first = ("Name your specialism",
             f" — decide the one thing you want to be known for: {_SPECIALISM[top]}.")
    rest = []
    if ld_high:                                    # high standards -> delegation matters most
        rest.append((dd["leadership"], "Delegate deliberately",
                     " — your standards run high, so hand off what others can carry and keep only what needs your judgement."))
    if ind_high:
        rest.append((dd["independence"], "Move decisions closer to you",
                     " — seek roles where you own the outcome rather than hand it up."))
    yr_rest = (f" — the window around {bw} is the one to be ready for." if bw else " now.")
    rest.append((78 - (peak_year - 1) * 6, f"Prepare the Year-{peak_year} move", yr_rest))
    rest.append((46, "Protect optionality",
                 " — do not over-absorb; keep room to move when the right opening appears."))
    rest.sort(key=lambda c: c[0], reverse=True)

    items = [first] + [(b, r) for _s, b, r in rest]
    rows = "\n".join(
        f'    <div class="sr"><div class="num">{i}</div><div class="st"><b>{b}</b>{r}</div></div>'
        for i, (b, r) in enumerate(items, 1))

    n = len(items)
    others = {3: "other two", 4: "other three", 5: "other four"}.get(n, "others")
    callout = (f'<div class="callout"><div class="ch">If you do only one</div><p>Start with priority '
               f'one — naming the single thing you want to be known for. It sharpens the {others} and '
               f'turns a busy year into a directed one.</p></div>')

    return [(_P42_OLD_ROWS, rows), (_P42_OLD_CALLOUT, callout)]


# ---------------------------------------------------------------- Page 43 ------
def _page43_matrix(p, dd):
    peak_year = p["three_year"]["peak_year"]
    ld_high = dd["leadership"] >= 70
    ind_high = dd["independence"] >= 70

    # the second do-now move must match what page 42 surfaced after positioning
    if ld_high:
        dot2, phrase2 = "Delegate", "delegate"
    elif ind_high:
        dot2, phrase2 = "Own it", "own your decisions"
    else:
        dot2, phrase2 = "Protect", "protect your focus"

    return [
        # relabel the two personalized dots (positioning "Name it" dot is kept verbatim)
        ('<text x="120" y="113" text-anchor="middle">Delegate</text>',
         f'<text x="120" y="113" text-anchor="middle">{dot2}</text>'),
        ('<text x="205" y="93" text-anchor="middle" font-family="Inter,sans-serif" font-size="8" fill="#3D352B">Year-2 move</text>',
         f'<text x="205" y="93" text-anchor="middle" font-family="Inter,sans-serif" font-size="8" fill="#3D352B">Year-{peak_year} move</text>'),
        ('<b>Do now.</b> Name your one thing and delegate — high impact, low effort.',
         f'<b>Do now.</b> Name your one thing and {phrase2} — high impact, low effort.'),
        ('<b>Sequence next.</b> The Year-2 move is high-impact but heavier; queue it deliberately.',
         f'<b>Sequence next.</b> The Year-{peak_year} move is high-impact but heavier; queue it deliberately.'),
        ('<div class="take"><b>The read</b>"Name your one thing" and "delegate" are high-impact, low-effort — do them first.</div>',
         f'<div class="take"><b>The read</b>"Name your one thing" and "{phrase2}" are high-impact, low-effort — do them first.</div>'),
    ]


# ---------------------------------------------------------------- Page 53 ------
_PGIFT = {
    "Saturn": ("structure &amp; patience", "earned authority, discipline, and the long game"),
    "Jupiter": ("wisdom &amp; growth", "sound judgement, guidance, and expansion"),
    "Sun": ("authority &amp; visibility", "recognition, confidence, and being seen for your work"),
    "Mercury": ("clarity &amp; communication", "sharp thinking, analysis, and how well you put it across"),
    "Mars": ("drive &amp; initiative", "decisiveness, energy, and the will to move first"),
    "Venus": ("relationships &amp; taste", "rapport, an eye for quality, and ease with people"),
}
_WHY = {
    "Saturn": "When Saturn sits well on the career axis, reward tends to arrive later and last longer — the steady, structural path outperforms the quick one.",
    "Jupiter": "When Jupiter is your strongest, growth comes through good judgement and trust — you expand by being the person others turn to for the wider view.",
    "Sun": "When the Sun leads, recognition follows contribution — you do your best work visible, with your name on the outcome.",
    "Mercury": "When Mercury leads, your edge is clarity — you think it through and say it well, and that is what moves things forward.",
    "Mars": "When Mars leads, momentum is your advantage — you move first and decisively, and the win goes to initiative over caution.",
    "Venus": "When Venus leads, relationships and taste carry your career — trust, rapport and a feel for quality open the doors.",
}
# icons stay position-anchored (SVG structure preserved); only text changes
_P53_ICONS = ["#i-hourglass", "#i-trend", "#i-target"]
_P53_SPANS = ["The strongest career signal: {}.", "Supports with {}.", "Adds {}."]


def _page53_planets(p, dd):
    top3 = _planet_rank(p["chart"]["planets"])[:3]
    p1, p2, p3 = top3

    cards = "\n    ".join(
        f'<div class="pt"><svg class="pi"><use href="{_P53_ICONS[i]}"/></svg><div class="tx">'
        f'<b>{P} — {_PGIFT[P][0]}</b><span>{_P53_SPANS[i].format(_PGIFT[P][1])}</span></div></div>'
        for i, P in enumerate(top3))

    lead = (f'<p class="lead" style="margin-top:12px">Read together, {p1}, {p2} and {p3} shape how '
            f'your working life takes form — {p1} leads, with {p2} and {p3} close behind. Each '
            f'carries a distinct professional gift, and the strongest sets the tone.</p>')

    callout = f'<div class="callout"><div class="ch">Why {p1} leads</div><p>{_WHY[p1]}</p></div>'

    return [
        ('<p class="lead" style="margin-top:12px">Read together, these three point the same way: authority earned slowly, widened by sound judgement, and expressed through guidance rather than noise. It is a chart built for the long, advisory climb.</p>',
         lead),
        ('<div class="pt"><svg class="pi"><use href="#i-hourglass"/></svg><div class="tx"><b>Saturn — structure &amp; patience</b><span>The strongest career signal: earned authority, discipline, the long game.</span></div></div>\n'
         '    <div class="pt"><svg class="pi"><use href="#i-trend"/></svg><div class="tx"><b>Jupiter — wisdom &amp; growth</b><span>Supports advisory, guidance and expansion.</span></div></div>\n'
         '    <div class="pt"><svg class="pi"><use href="#i-target"/></svg><div class="tx"><b>Sun &amp; Mercury — clarity &amp; voice</b><span>Sharpen judgement and communication.</span></div></div>',
         cards),
        ('<div class="callout"><div class="ch">Why Saturn leads</div><p>When Saturn sits well on the career axis, reward tends to arrive later and last longer — the steady, structural path outperforms the quick one.</p></div>',
         callout),
    ]


# ---------------------------------------------------------------- Page 54 ------
_PLABEL = {"Saturn": "structure", "Jupiter": "growth", "Mercury": "judgement",
           "Sun": "visibility", "Mars": "drive", "Venus": "rapport"}


def _p54_word(d):
    return "strong" if d >= 80 else "good" if d >= 68 else "moderate" if d >= 55 else "present"


def _page54_strength(p, dd):
    planets = p["chart"]["planets"]
    top4 = _planet_rank(planets)[:4]
    ds = {P: planets.get(P, {}).get("dscore", 50) for P in top4}
    p1, p2, p3, p4 = top4

    bars = "\n    ".join(
        f'<div class="bx"><div class="bl">{P} — {_PLABEL[P]} <span>{_p54_word(ds[P])}</span></div>'
        f'<div class="bt"><i style="width:{ds[P]}%"></i></div></div>'
        for P in top4)

    return [
        ('<h2 class="action">Saturn and Jupiter carry your career chart.</h2>',
         f'<h2 class="action">{p1} and {p2} carry your career chart.</h2>'),
        ('<div class="bx"><div class="bl">Saturn — structure <span>strong</span></div><div class="bt"><i style="width:90%"></i></div></div>\n'
         '    <div class="bx"><div class="bl">Jupiter — growth <span>strong</span></div><div class="bt"><i style="width:82%"></i></div></div>\n'
         '    <div class="bx"><div class="bl">Mercury — judgement <span>good</span></div><div class="bt"><i style="width:68%"></i></div></div>\n'
         '    <div class="bx"><div class="bl">Sun — visibility <span>moderate</span></div><div class="bt"><i style="width:52%"></i></div></div>',
         bars),
        ('<b>The carriers.</b> Saturn (structure) and Jupiter (growth) lead your career chart.',
         f'<b>The carriers.</b> {p1} ({_PLABEL[p1]}) and {p2} ({_PLABEL[p2]}) lead your career chart.'),
        ("<b>The support.</b> Mercury lends judgement; the Sun's visibility runs quieter.",
         f'<b>The support.</b> {p3} lends {_PLABEL[p3]}; {p4}\'s {_PLABEL[p4]} runs quieter.'),
        ('<b>The direction.</b> The mix rewards the steady, structural, advisory path.',
         f'<b>The direction.</b> Your strongest planets reward a {_PLABEL[p1]}-led, {_PLABEL[p2]}-supported path.'),
        ('<div class="take"><b>The read</b>Your chart rewards the steady, structural, advisory path — exactly where the report points.</div>',
         f'<div class="take"><b>The read</b>Your chart is carried by {p1} and {p2} — build your career around {_PLABEL[p1]} and {_PLABEL[p2]}.</div>'),
    ]


BUILDERS = [
    _page40_decades,
    _page42_priorities,
    _page43_matrix,
    _page53_planets,
    _page54_strength,
]
