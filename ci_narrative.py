"""Career Intelligence — narrative personalization layer.

The 57-card body (career_intelligence_assets.CI_BODY) was authored for one mock
persona ("Rajesh Menon"). render_career_intelligence() personalizes the data
exhibits; THIS module personalizes the prose pages that state a chart-derived
finding, so no page ships the mock persona's claims to another buyer (Rule 2).

Contract: narrative_replacements(payload, ddims) -> list[(old, new)] of exact
string replacements applied to the body. Every claim is traceable to computed
data (display dims `ddims`, planet dignity scores, phase, naukri meter, etc.);
we never invent numbers that look computed. House style in report prose: em-dash
allowed (this is analyst voice, not a testimonial).

Each page builder returns its own (old, new) pairs; add builders batch by batch.
"""

_DIM_WORD = {"leadership": "leadership", "strategic": "strategy",
             "independence": "independence", "entrepreneurial": "enterprise",
             "risk": "risk-taking", "stability": "stability"}
_DIM_BAR_LABEL = {"leadership": "Leadership", "strategic": "Strategic thinking",
                  "independence": "Independence", "entrepreneurial": "Enterprise drive",
                  "risk": "Bold, timely moves", "stability": "Long-horizon patience"}
_DIM_ICON = {"leadership": "i-shield", "strategic": "i-compass",
             "independence": "i-scales", "entrepreneurial": "i-gem",
             "risk": "i-moon", "stability": "i-hourglass"}
# description of a dimension when it is one of the person's TOP strengths (page 8)
_DIM_STRENGTH_DESC = {
    "leadership": "You take charge naturally — when the call has to be made, people look to you to make it.",
    "strategic": "You perform best on a complex, open problem — you find the structure underneath before others see it.",
    "independence": "You do your strongest work when the outcome is yours to own, not handed up for approval.",
    "entrepreneurial": "You are wired to build and own outcomes, not just run someone else's play.",
    "risk": "You move when the window is open — decisive where others stall waiting for certainty.",
    "stability": "Your gains arrive through sustained effort, not sudden breaks. You are built for compounding.",
}


def _cap(s):
    return s[:1].upper() + s[1:]


def _ranked(ddims):
    return sorted(ddims, key=ddims.get, reverse=True)


def _lvl(v):
    return "high" if v >= 76 else "mod" if v >= 62 else "low"


# ---------------------------------------------------------------- Part I -------
def _page7_who_you_are(payload, ddims):
    """Who you are at work — summary line + 4 personality facets."""
    r = _ranked(ddims)
    top = r[0]
    ds = payload["decision_style"]
    sun = payload["chart"]["planets"].get("Sun", {}).get("dscore", 50)
    ld, ind = ddims["leadership"], ddims["independence"]

    summary = {
        "leadership": "At your best when you set the direction and own the call.",
        "strategic": "At your best on a hard, open problem others cannot yet see through.",
        "independence": "At your best when the outcome rests on your own judgement.",
        "entrepreneurial": "At your best when you are building something that is yours to own.",
        "risk": "At your best when a decisive move is needed and the window is short.",
        "stability": "At your best over the long game — steady where others burn out.",
    }[top]

    responsibility = ("You gravitate toward ownership — most engaged when the outcome rests on your judgement."
                      if ind >= 68 or top in ("independence", "leadership", "entrepreneurial")
                      else "You do your steadiest work inside a clear remit, with the mandate spelled out.")
    high_stakes = ("You grow steadier, not louder, as stakes rise — a settling presence when others escalate."
                   if ds["deliberate"]
                   else "You come alive when the pressure is on — quick and decisive when the window is short.")
    recognition = ("You are comfortable being visible, and recognition tends to find you."
                   if sun >= 62
                   else "You value being respected for judgement over being seen. Substance over spotlight.")
    authority = ("You hold authority with ease and compete against the problem, not the person."
                 if ld >= 68
                 else "You respect earned authority and prefer to let the work make your case.")

    return [
        ('<span>At your best when the outcome rests on your own judgement.</span>',
         f'<span>{summary}</span>'),
        ('<b>Responsibility</b><span>You gravitate toward ownership — most engaged when the outcome rests on your judgement.</span>',
         f'<b>Responsibility</b><span>{responsibility}</span>'),
        ('<b>High-stakes moments</b><span>You grow steadier, not louder, as stakes rise — a settling presence when others escalate.</span>',
         f'<b>High-stakes moments</b><span>{high_stakes}</span>'),
        ('<b>Recognition</b><span>You value being respected for judgement over being visible. Substance over spotlight.</span>',
         f'<b>Recognition</b><span>{recognition}</span>'),
        ('<b>Authority &amp; competition</b><span>You compete against the problem, not the person — at ease with authority when it is earned.</span>',
         f'<b>Authority &amp; competition</b><span>{authority}</span>'),
    ]


def _page8_strengths(payload, ddims):
    """What you do better than most — top-3 dims as strength cards + basis."""
    r = _ranked(ddims)
    top3 = r[:3]
    cards = "\n    ".join(
        f'<div class="pt"><svg class="pi"><use href="#{_DIM_ICON[k]}"/></svg><div class="tx">'
        f'<b>{_DIM_BAR_LABEL[k]}</b><span>{_DIM_STRENGTH_DESC[k]}</span></div></div>'
        for k in top3)

    # astrological basis: name the 1-2 strongest career planets by dignity score
    planets = payload["chart"]["planets"]
    career = sorted(("Saturn", "Jupiter", "Sun", "Mercury", "Mars"),
                    key=lambda p: planets.get(p, {}).get("dscore", 0), reverse=True)
    p1, p2 = career[0], career[1]
    _GIFT = {"Saturn": "discipline and staying power", "Jupiter": "judgement and expansion",
             "Sun": "authority and visibility", "Mercury": "sharp thinking and communication",
             "Mars": "drive and decisiveness"}
    basis = (f'{p1} sits well on your career indicators, supported by {p2} — '
             f'{_GIFT[p1]}, backed by {_GIFT[p2]}.')

    old_cards = ('<div class="pt"><svg class="pi"><use href="#i-compass"/></svg><div class="tx"><b>Strategic thinking</b><span>You perform best given a complex, open problem — you find the structure underneath.</span></div></div>\n'
                 '    <div class="pt"><svg class="pi"><use href="#i-hourglass"/></svg><div class="tx"><b>Long-horizon patience</b><span>Your gains arrive after sustained effort, not sudden breaks. Built for compounding.</span></div></div>\n'
                 '    <div class="pt"><svg class="pi"><use href="#i-scales"/></svg><div class="tx"><b>Quiet authority</b><span>You earn influence through consistency and judgement — people defer to your read.</span></div></div>')
    return [
        (old_cards, cards),
        ('A well-placed Saturn on the career indicators, supported by Jupiter — persistence and structure over quick wins.',
         basis),
    ]


def _page10_how_you_lead(payload, ddims):
    """How you lead — summary + Style / Influence / growth-edge."""
    ld = ddims["leadership"]
    strat, risk = ddims["strategic"], ddims["risk"]
    reasoning = strat >= risk  # reasoning-led vs force/drive-led
    delegates = ddims["independence"] >= 70 and ld < 80  # trusts others vs holds on

    if ld >= 76:
        summary = "You lead from the front — clear standards, and the room follows your call."
    elif ld >= 62:
        summary = "You lead by credibility — people follow your judgement more than your title."
    else:
        summary = "You lead quietly — through the work and the standard you hold, not volume."

    style = ("Directive on the destination, flexible on the route. Set the standard, trust people to reach it."
             if ld >= 68 else
             "You lead by example first — you set the bar by meeting it, then others rise to match.")
    influence = ("You persuade with reasoning, not force. Credibility-based authority ages well."
                 if reasoning else
                 "You persuade through conviction and momentum — you move first, and people follow the energy.")
    if delegates:
        edge = ('<div class="pt"><svg class="pi"><use href="#i-scales"/></svg><div class="tx">'
                '<b>Trust — well placed</b><span>You hand off the route and keep the destination. Guard against spreading yourself too thin as scope grows.</span></div></div>')
    else:
        edge = ('<div class="pt warn"><svg class="pi"><use href="#i-alert"/></svg><div class="tx">'
                '<b>Delegation — the growth edge</b><span>High standards make handing off hard. The next level asks you to let others carry more.</span></div></div>')

    return [
        ('<span>You lead through standards and reasoning — delegation is the growth edge.</span>',
         f'<span>{summary}</span>'),
        ('<b>Style</b><span>Directive on the destination, flexible on the route. Set the standard, trust people to reach it.</span>',
         f'<b>Style</b><span>{style}</span>'),
        ('<b>Influence</b><span>You persuade with reasoning, not force. Credibility-based authority ages well.</span>',
         f'<b>Influence</b><span>{influence}</span>'),
        ('<div class="pt warn"><svg class="pi"><use href="#i-alert"/></svg><div class="tx"><b>Delegation — the growth edge</b><span>High standards make handing off hard. The next level asks you to let others carry more.</span></div></div>',
         edge),
    ]


def _page11_leadership_dials(payload, ddims):
    """Leadership dials — 4 dial positions + legend + take, from dims/planets."""
    ld, strat, risk, ind = ddims["leadership"], ddims["strategic"], ddims["risk"], ddims["independence"]
    sun = payload["chart"]["planets"].get("Sun", {}).get("dscore", 50)
    direction = ld                        # hands-off -> directive
    influence = round(100 * strat / (strat + risk)) if (strat + risk) else 50  # force -> reasoning
    delegation = max(12, min(88, 100 - ld + (ind - 60)))  # holds on -> lets go
    visibility = max(12, min(88, round((sun * 0.54 + 42 + ld) / 2)))  # quiet -> front-facing

    reasoning = strat >= risk
    heading = (f"You lead through {'reasoning' if reasoning else 'drive'} and standards"
               f" — {'light on delegation' if delegation < 50 else 'and you let others carry'}.")
    leg1 = (f'<b>{"Directive plus reasoning" if reasoning else "Direct and driven"}</b> — '
            f'{"you set the bar, then win the room with the argument" if reasoning else "you set the pace and pull people with your momentum"}.')
    leg2 = (f'<b>Delegation is the lever</b> — hand off the route, keep the destination.'
            if delegation < 55 else
            f'<b>Reach is your lever</b> — you already delegate; the next step is choosing where to be seen.')
    take = (f"A credible, standard-setting leader. The single dial to move is "
            f"{'delegation' if delegation < 55 else 'visibility'}.")

    return [
        ('<h2 class="action">You lead through standards and reasoning — light on delegation.</h2>',
         f'<h2 class="action">{heading}</h2>'),
        ('<div class="spt">Direction</div><div class="spl"><span>Hands-off</span><span>Directive</span></div><div class="spline"><span class="spd" style="left:72%"></span></div>',
         f'<div class="spt">Direction</div><div class="spl"><span>Hands-off</span><span>Directive</span></div><div class="spline"><span class="spd" style="left:{direction}%"></span></div>'),
        ('<div class="spt">Influence</div><div class="spl"><span>Force</span><span>Reasoning</span></div><div class="spline"><span class="spd" style="left:85%"></span></div>',
         f'<div class="spt">Influence</div><div class="spl"><span>Force</span><span>Reasoning</span></div><div class="spline"><span class="spd" style="left:{influence}%"></span></div>'),
        ('<div class="spt">Delegation</div><div class="spl"><span>Holds on</span><span>Lets go</span></div><div class="spline"><span class="spd" style="left:35%"></span></div>',
         f'<div class="spt">Delegation</div><div class="spl"><span>Holds on</span><span>Lets go</span></div><div class="spline"><span class="spd" style="left:{delegation}%"></span></div>'),
        ('<div class="spt">Visibility</div><div class="spl"><span>Quiet</span><span>Front-facing</span></div><div class="spline"><span class="spd" style="left:40%"></span></div>',
         f'<div class="spt">Visibility</div><div class="spl"><span>Quiet</span><span>Front-facing</span></div><div class="spline"><span class="spd" style="left:{visibility}%"></span></div>'),
        ('<b>Directive plus reasoning</b> — you set the bar, then win the room with the argument.', leg1),
        ('<b>Delegation is the lever</b> — hand off the route, keep the destination.', leg2),
        ('<div class="take"><b>The read</b>A credible, standard-setting leader. The single dial to move is delegation.</div>',
         f'<div class="take"><b>The read</b>{take}</div>'),
    ]


_BUILDERS = [
    _page7_who_you_are,
    _page8_strengths,
    _page10_how_you_lead,
    _page11_leadership_dials,
]


def _part_builders():
    """Batch-2..7 live in ci_narr_part2..7 modules (one per page group), each
    exposing BUILDERS. Picked up automatically once present."""
    import importlib
    extra = []
    for n in range(2, 9):
        try:
            mod = importlib.import_module(f"ci_narr_part{n}")
        except ModuleNotFoundError:
            continue
        extra.extend(getattr(mod, "BUILDERS", []))
    return extra


def narrative_replacements(payload, ddims):
    out = []
    for b in _BUILDERS + _part_builders():
        out.extend(b(payload, ddims))
    return out
