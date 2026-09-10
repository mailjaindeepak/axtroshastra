"""Career Intelligence — narrative personalization, Part V (roadmap/action pages).

Personalizes the Part-V action pages of the 57-card body so no page ships the
mock persona's ("Rajesh Menon") chart-derived roadmap to another buyer (Rule 2).
Same contract/voice as ci_narrative.py: each builder returns (old, new) exact
string replacements; `new` keeps the SAME HTML structure and SAME SVG icons as
`old`, only the human-readable text changes. Every claim traces to computed data
(display dims `ddims`, phase md-lord, three-year peak window, naukri lean).

Pages (career_intelligence_assets.CI_BODY):
  44 Lean toward these        — from top dims + naukri lean
  45 Steer clear of these     — from the person's live mismatches
  46 Questions worth sitting  — top-vs-bottom gap, phase, three-year window
  47 Stop / Start / Continue  — blind spot / positioning bet / strongest edge
  48 12 months in three moves — mirrors 47 (must agree)
  49 From insight to motion   — 30/90/365, specialism -> decision-room -> window
  50 12-month plan (timeline) — mirrors 49 (must agree)

Built from the person's TOP strength (specialism), bottom dim (blind spot),
delegation edge (leadership high), and phase / three-year window.
"""

# --- copied verbatim from ci_narrative (keep this module independent) ----------
_DIM_WORD = {"leadership": "leadership", "strategic": "strategy",
             "independence": "independence", "entrepreneurial": "enterprise",
             "risk": "risk-taking", "stability": "stability"}
_DIM_BAR_LABEL = {"leadership": "Leadership", "strategic": "Strategic thinking",
                  "independence": "Independence", "entrepreneurial": "Enterprise drive",
                  "risk": "Bold, timely moves", "stability": "Long-horizon patience"}


def _cap(s):
    return s[:1].upper() + s[1:]


def _ranked(ddims):
    return sorted(ddims, key=ddims.get, reverse=True)


def _lvl(v):
    return "high" if v >= 76 else "mod" if v >= 62 else "low"


# --- Part-V content maps, keyed by dimension -----------------------------------
# a named specialism, from the person's TOP strength (page 44/47/48/49/50)
_SPECIALISM = {
    "leadership": "the one who owns the hard call",
    "strategic": "the strategist for the problem no one else can structure",
    "independence": "the owner who takes an outcome end to end",
    "entrepreneurial": "the builder who owns what they make",
    "risk": "the one who moves the moment the window opens",
    "stability": "the one who compounds the long bet others quit early",
}
# what to STOP, when this dimension is the person's weakest (page 47/48)
_STOP_BY_WEAK = {
    "leadership": ("Deferring the call when it is yours to make",
                   "It leaves your own judgement on the table."),
    "strategic": ("Reacting move-to-move without the map",
                  "It costs you the structure you think best inside."),
    "independence": ("Waiting on a sign-off you do not actually need",
                     "It hands your sharpest judgement to someone else."),
    "entrepreneurial": ("Building only ever inside someone else's play",
                        "It caps how much of the upside is yours."),
    "risk": ("Waiting for full certainty before you move",
             "The window usually shuts before certainty arrives."),
    "stability": ("Jumping to the next thing before the last compounds",
                  "You forfeit the gains only time pays out."),
}
# the delegation-edge Stop, when leadership is high (mirrors the leadership pages)
_STOP_DELEGATION = ("Absorbing work that others should own",
                    "It costs the room your judgement needs.")
# what to CONTINUE — the person's strongest trait as an edge (page 47/48)
_CONT_BY_TOP = {
    "leadership": ("Setting the standard and holding it",
                   "People follow your read; that trust is the edge."),
    "strategic": ("Solving from the structure, not the symptom",
                  "Seeing the shape first is your durable edge."),
    "independence": ("Owning outcomes end to end",
                     "Your judgement is sharpest when it is yours to carry."),
    "entrepreneurial": ("Building things that are yours to own",
                        "The builder's instinct is your edge — keep feeding it."),
    "risk": ("Moving the moment the window opens",
             "Decisiveness is an edge; protect it from second-guessing."),
    "stability": ("Playing the long, compounding game",
                  "Your patience is an edge, not a delay."),
}
# mahadasha lords whose phase is a reinventing one (else: consolidating)
_REINVENT_LORDS = {"Rahu", "Ketu", "Moon", "Mercury"}


def _profile(payload, ddims):
    """The few computed signals every Part-V page shares."""
    r = _ranked(ddims)
    top, bottom = r[0], r[-1]
    ld = ddims["leadership"]
    ind = ddims["independence"]
    delegates_edge = ld >= 76  # leadership high -> delegation is the growth lever
    lean = payload.get("entrepreneurial", {}).get("lean", 0)  # +ve = job, -ve = enterprise
    enterprise_lean = lean < 0 or top == "entrepreneurial" or ddims["entrepreneurial"] >= 70
    md_lord = payload.get("phase", {}).get("md_lord", "Saturn")
    reinventing = md_lord in _REINVENT_LORDS
    ty = payload.get("three_year", {}) or {}
    peak_year = ty.get("peak_year", 2)
    best_window = ty.get("best_window")
    return dict(top=top, bottom=bottom, ld=ld, ind=ind,
                specialism=_SPECIALISM[top], delegates_edge=delegates_edge,
                enterprise_lean=enterprise_lean, reinventing=reinventing,
                peak_year=peak_year, best_window=best_window)


# ---------------------------------------------------------------- Page 44 ------
def _page44_pursue(payload, ddims):
    """Lean toward these — 3 pursue cards + the test, from top dims + naukri lean."""
    pr = _profile(payload, ddims)
    topw = _DIM_WORD[pr["top"]]
    botw = _DIM_WORD[pr["bottom"]]
    spec = pr["specialism"]

    lead = (f'Each of these plays to the same core: your {topw} is the asset, so put it where '
            f'it decides the outcome. The closer a role sits to all three, the more it feels like '
            f'the work you were built for.')

    c1 = ('Roles where the outcome rests on your own judgement, not a sign-off.'
          if pr["ind"] >= 68 or pr["delegates_edge"] or pr["top"] in ("independence", "leadership", "entrepreneurial")
          else 'Roles with a clear remit that is genuinely yours to own.')
    c2 = f'Become {spec} — one clear thing you are the person for.'
    if pr["enterprise_lean"]:
        c3_h, c3_s = ('A complementary partnership',
                      'If you build your own thing, pair your judgement with structure and capital.')
    else:
        c3_h, c3_s = ('A complementary partnership',
                      f'Pair with someone strong on {botw}, so your {topw} is free to lead.')

    the_test = (f'Before you say yes to a role, ask whether it hands you ownership, room to be {spec}, '
                f'or the right people beside you. The best ones offer all three.')

    return [
        ('<p class="lead" style="margin-top:12px">Each of these plays to the same core: your judgement is the asset, so put it where it decides the outcome. The closer a role sits to all three, the more it feels like the work you were built for.</p>',
         f'<p class="lead" style="margin-top:12px">{lead}</p>'),
        ('<b>High-ownership roles</b><span>Where the outcome rests on your judgement.</span>',
         f'<b>High-ownership roles</b><span>{c1}</span>'),
        ('<b>A named specialism</b><span>Be the person for one clear thing.</span>',
         f'<b>A named specialism</b><span>{c2}</span>'),
        ('<b>A complementary partnership</b><span>If you move to enterprise, pair with structure and capital.</span>',
         f'<b>{c3_h}</b><span>{c3_s}</span>'),
        ('<div class="callout"><div class="ch">The test</div><p>Before you say yes to a role, ask whether it hands you ownership, a clear specialism, or the right people. The best ones offer all three.</p></div>',
         f'<div class="callout"><div class="ch">The test</div><p>{the_test}</p></div>'),
    ]


# ---------------------------------------------------------------- Page 45 ------
def _page45_avoid(payload, ddims):
    """Steer clear of these — pick the 3 mismatches that fit this chart + the tell."""
    pr = _profile(payload, ddims)
    ld, ind = pr["ld"], ddims["independence"]
    stab, risk, entre = ddims["stability"], ddims["risk"], ddims["entrepreneurial"]

    # candidate avoidances, each weighted by how strongly this chart earns it
    cands = [
        (ld, 'Responsibility without authority', "Accountable for outcomes you don't get to decide."),
        (stab + (100 - risk), 'Staying on purely for comfort', 'Safe long past the point it still grows you.'),
        (entre - stab + (30 if pr["enterprise_lean"] else 0), 'The solo leap without a base',
         'Full independence with nothing solid under it.'),
        (ind, 'Boxed in with no autonomy', 'A role that dictates the how, not just the what.'),
    ]
    top3 = [c for c in sorted(cands, key=lambda c: c[0], reverse=True)[:3]]
    (h1, s1), (h2, s2), (h3, s3) = [(h, s) for _, h, s in top3]

    lead = ('The through-line in all three is a mismatch between what you carry and what you '
            'control. You can shoulder a great deal — but only when the authority and the ground '
            'beneath it are real.')
    tell = (f'If a move offers a bigger title but a smaller say, or comfort in place of growth, '
            f'read that as the signal to pause — not to accept. Watch the first of the three hardest.')

    return [
        ('<p class="lead" style="margin-top:12px">The through-line in all three is a mismatch between what you carry and what you control. You can shoulder enormous responsibility — but only when the authority and the ground beneath it are real.</p>',
         f'<p class="lead" style="margin-top:12px">{lead}</p>'),
        ('<b>Responsibility without authority</b><span>Accountable for outcomes you can\'t decide.</span>',
         f'<b>{h1}</b><span>{s1}</span>'),
        ('<b>Staying purely for comfort</b><span>Safe past the point it grows you.</span>',
         f'<b>{h2}</b><span>{s2}</span>'),
        ('<b>The solo leap without a base</b><span>Full independence with no structure under it.</span>',
         f'<b>{h3}</b><span>{s3}</span>'),
        ('<div class="callout terra"><div class="ch">The tell</div><p>If a move offers a bigger title but a smaller say, or comfort in place of growth, read that as the signal to pause — not to accept.</p></div>',
         f'<div class="callout terra"><div class="ch">The tell</div><p>{tell}</p></div>'),
    ]


# ---------------------------------------------------------------- Page 46 ------
def _page46_questions(payload, ddims):
    """Questions worth sitting with — top-vs-bottom gap, phase, three-year window."""
    pr = _profile(payload, ddims)
    topw, botw = _DIM_WORD[pr["top"]], _DIM_WORD[pr["bottom"]]

    q_autonomy = (f'Your {topw} runs well ahead of your {botw}. Is your current role using the '
                  f'first, or quietly taxing the second?')
    q_direction = ('You are in a reinventing phase. Are you actually letting the old shape go, or '
                   'holding it out of habit?'
                   if pr["reinventing"] else
                   'You are in a consolidating phase. Are you building on what is laid down on '
                   'purpose, or staying because leaving feels like effort?')
    if pr["best_window"]:
        q_legacy = (f'Your strongest window lands around {pr["best_window"]}. What do you want that '
                    f'opening to build that the last ten years did not?')
    else:
        q_legacy = (f'Your strongest window lands in Year {pr["peak_year"]}. What do you want that '
                    f'opening to build that the last ten years did not?')

    return [
        ('<b>Autonomy</b><span>Is your role giving you enough real decision-making, or just more responsibility?</span>',
         f'<b>Autonomy</b><span>{q_autonomy}</span>'),
        ('<b>Direction</b><span>Are you consolidating on purpose, or staying because leaving feels like effort?</span>',
         f'<b>Direction</b><span>{q_direction}</span>'),
        ('<b>Legacy</b><span>What should the next ten years build that the last ten did not?</span>',
         f'<b>Legacy</b><span>{q_legacy}</span>'),
    ]


# --- shared Stop/Start/Continue content for pages 47 + 48 (must agree) ---------
def _ssc(pr):
    stop_h, stop_s = (_STOP_DELEGATION if pr["delegates_edge"] else _STOP_BY_WEAK[pr["bottom"]])
    cont_h, cont_s = _CONT_BY_TOP[pr["top"]]
    return stop_h, stop_s, pr["specialism"], cont_h, cont_s


# ---------------------------------------------------------------- Page 47 ------
def _page47_stop_start_continue(payload, ddims):
    """Stop / Start / Continue — blind spot, positioning bet, strongest edge."""
    pr = _profile(payload, ddims)
    stop_h, stop_s, spec, cont_h, cont_s = _ssc(pr)
    return [
        ('<div class="th">Absorbing work others should own</div><div class="td">It costs the strategic room you need.</div>',
         f'<div class="th">{stop_h}</div><div class="td">{stop_s}</div>'),
        ('<div class="th">Making one clear positioning bet</div><div class="td">Choose what you want to be known for.</div>',
         f'<div class="th">Making one clear positioning bet</div><div class="td">Choose to be known as {spec}.</div>'),
        ('<div class="th">Playing the long game</div><div class="td">Your patience is an edge, not a delay.</div>',
         f'<div class="th">{cont_h}</div><div class="td">{cont_s}</div>'),
    ]


# ---------------------------------------------------------------- Page 48 ------
def _page48_three_moves(payload, ddims):
    """12 months in three moves — same Stop/Start/Continue as page 47, + the read."""
    pr = _profile(payload, ddims)
    stop_h, stop_s, spec, cont_h, cont_s = _ssc(pr)
    return [
        ('<div class="blk stop"><div class="bh">Stop</div><div class="bb">Absorbing work that others should own.</div></div>',
         f'<div class="blk stop"><div class="bh">Stop</div><div class="bb">{stop_h}.</div></div>'),
        ('<div class="blk start"><div class="bh">Start</div><div class="bb">Making one clear positioning bet — your "known for".</div></div>',
         f'<div class="blk start"><div class="bh">Start</div><div class="bb">Making one clear positioning bet — {spec}.</div></div>'),
        ('<div class="blk cont"><div class="bh">Continue</div><div class="bb">Playing the long, compounding game. Trust the patience.</div></div>',
         f'<div class="blk cont"><div class="bh">Continue</div><div class="bb">{cont_h}. {cont_s}</div></div>'),
        ('<div class="lr"><span class="dot" style="background:#B9862E"></span><span class="lt"><b>Stop and start.</b> Drop absorbed work; begin one clear positioning bet.</span></div>',
         f'<div class="lr"><span class="dot" style="background:#B9862E"></span><span class="lt"><b>Stop and start.</b> Stop {stop_h.lower()}; begin one clear positioning bet.</span></div>'),
        ('<div class="lr"><span class="dot" style="background:#C9A34E"></span><span class="lt"><b>Continue.</b> Keep playing the long, compounding game — patience is the edge.</span></div>',
         f'<div class="lr"><span class="dot" style="background:#C9A34E"></span><span class="lt"><b>Continue.</b> Keep {cont_h.lower()} — that is the edge.</span></div>'),
        ('<div class="take"><b>The read</b>If you do only one: start the positioning bet. It unlocks the other two.</div>',
         f'<div class="take"><b>The read</b>If you do only one: make the positioning bet — {spec}. It unlocks the other two.</div>'),
    ]


# --- shared 30/90/365 content for pages 49 + 50 (must agree) -------------------
def _horizons(pr):
    d90 = ('Hand off two responsibilities; use the freed time to prepare the Year-{y} move.'.format(y=pr["peak_year"])
           if pr["delegates_edge"] else
           'Build the evidence and the case that make your Year-{y} move undeniable.'.format(y=pr["peak_year"]))
    d90_short = ('Delegate two things to open real decision-room.'
                 if pr["delegates_edge"] else
                 'Build the case and evidence for your next move.')
    return pr["specialism"], d90, d90_short


# ---------------------------------------------------------------- Page 49 ------
def _page49_insight_to_motion(payload, ddims):
    """From insight to motion — 30 name it / 90 decision-room / 365 the window."""
    pr = _profile(payload, ddims)
    spec, d90, _ = _horizons(pr)
    return [
        ('<div class="dt">Next 30 days</div><div class="th">Name your one thing</div><div class="td">Write the sentence you want associated with you. Test it on three people.</div>',
         f'<div class="dt">Next 30 days</div><div class="th">Name your specialism</div><div class="td">Write the sentence that makes you {spec}. Test it on three people.</div>'),
        ('<div class="dt">Next 90 days</div><div class="th">Create decision-room</div><div class="td">Hand off two responsibilities; use the time to prepare the Year-2 move.</div>',
         f'<div class="dt">Next 90 days</div><div class="th">Create decision-room</div><div class="td">{d90}</div>'),
        ('<div class="dt">Next 12 months</div><div class="th">Position for the window</div><div class="td">Have the case and relationships ready so you can act when it opens.</div>',
         f'<div class="dt">Next 12 months</div><div class="th">Position for the window</div><div class="td">Have the case and relationships ready for the Year-{pr["peak_year"]} window, so you can act when it opens.</div>'),
    ]


# ---------------------------------------------------------------- Page 50 ------
def _page50_plan_timeline(payload, ddims):
    """12-month plan (timeline exhibit) — mirrors page 49, + prose and the read."""
    pr = _profile(payload, ddims)
    spec, _, d90_short = _horizons(pr)
    free_verb = 'free your time' if pr["delegates_edge"] else 'build your case'
    heading = f'Name it, {free_verb}, then position for Year {pr["peak_year"]}.'
    return [
        ('<h2 class="action">Name it, free your time, then position for Year 2.</h2>',
         f'<h2 class="action">{heading}</h2>'),
        ('<span class="lt"><b>30 days — Name it.</b> Commit to one positioning line and test it on three people.</span>',
         f'<span class="lt"><b>30 days — Name it.</b> Commit to being {spec}, and test the line on three people.</span>'),
        ('<span class="lt"><b>90 days — Free time.</b> Delegate two things to open real decision-room.</span>',
         f'<span class="lt"><b>90 days — Free time.</b> {d90_short}</span>'),
        ('<span class="lt"><b>12 months — Position.</b> Have the case and the relationships ready for the window.</span>',
         f'<span class="lt"><b>12 months — Position.</b> Have the case and relationships ready for the Year-{pr["peak_year"]} window.</span>'),
        ('<div class="take"><b>The read</b>Each step buys the next. Start in the first 30 days or the year drifts.</div>',
         f'<div class="take"><b>The read</b>Each step buys the next. Name your specialism in the first 30 days or the year drifts.</div>'),
    ]


BUILDERS = [
    _page44_pursue,
    _page45_avoid,
    _page46_questions,
    _page47_stop_start_continue,
    _page48_three_moves,
    _page49_insight_to_motion,
    _page50_plan_timeline,
]
