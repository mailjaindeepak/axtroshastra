"""Career Intelligence — narrative personalization, Part IV (Opportunities & Fit).

Same contract/voice as ci_narrative.py: each builder returns (old, new) exact
string replacements against career_intelligence_assets.CI_BODY. `new` keeps the
SAME HTML structure and the SAME SVG icons/circles as `old` — only the
human-readable text changes, and every claim is a function of the buyer's
computed data (`ddims`, phase md_lord, planet dscores, naukri lean). Modules are
independent, so the shared helpers are copied in rather than imported.

Pages owned (report card / assets comment):
  29 "Where the doors may open"      role-fit cards, ranked from top ddims + lean
  31 "The rooms you belong in"       rooms from top-3 ddims + 10th-house/planet basis
  32 "Is this a phase for reinvention?"  verdict from phase md_lord + risk/indep + archetype
  33 "Where you thrive"              conditions from top-3 ddims
  34 "Your sweet spot" (venn)        3 circles relabelled to top-3 ddim themes
"""


def _ranked(ddims):
    return sorted(ddims, key=ddims.get, reverse=True)


# dimension -> venn/circle theme (page 34 labels)
_THEME = {"leadership": "Authority", "strategic": "Strategy", "independence": "Autonomy",
          "entrepreneurial": "Ownership", "stability": "Continuity", "risk": "Bold moves"}
# dimension -> mid-sentence noun for the sweet-spot verdict (page 33)
_SPOT_WORD = {"leadership": "decision-making", "strategic": "strategy", "independence": "autonomy",
              "entrepreneurial": "building", "risk": "timely calls", "stability": "the long game"}
# dimension -> the environment that trait needs (page 33 lead + conditions).
# Public so the landing-page teaser (career_intelligence_report.compute_*) can reuse the
# SAME phrasing for its "you may perform best where …" line — keeps teaser and report
# consistent (CLAUDE.md §8 anti-drift). `_NEED` stays as a back-compat alias.
NEED_BY_DIM = {"leadership": "real authority over the call", "strategic": "a genuinely hard problem",
               "independence": "room to own the outcome", "entrepreneurial": "something to build",
               "risk": "freedom to move early", "stability": "a long-enough horizon"}
_NEED = NEED_BY_DIM
_COND = {
    "leadership": ("Real authority over the call",
                   "The decision is genuinely yours, not recommended upward for someone else to make."),
    "strategic": ("A problem worth solving",
                  "Complex and open-ended, with real consequences riding on the answer."),
    "independence": ("Room to own the outcome",
                     "A remit you run on your own judgement, and are measured on the result."),
    "entrepreneurial": ("Something of your own to build",
                        "Space to create the thing, not just maintain what already runs."),
    "risk": ("Freedom to move early",
             "Permission to act when the window opens instead of waiting for full certainty."),
    "stability": ("A long-enough horizon",
                  "Time for steady effort to compound, not judgement quarter to quarter."),
}
# dimension -> a "room" you belong in (page 31), keeps the #i-check icon
_ROOM = {
    "leadership": ("Rooms where you hold the mandate",
                   "Authority that matches the accountability — you own the call, not only the result."),
    "strategic": ("Complex, open problems",
                  "Where the answer must be found, not followed — your read is the value you add."),
    "independence": ("Roles you run on your own standard",
                     "A remit that is yours to shape, and yours to be judged on."),
    "entrepreneurial": ("Building and owning outcomes",
                        "Where you create the thing, not just administer what already exists."),
    "risk": ("Calls with a live clock",
             "Rooms that reward moving when the window is open, not waiting for certainty."),
    "stability": ("Long-horizon senior roles",
                  "Where structure and time are an asset, not a constraint."),
}
_THREAD = {
    "leadership": "authority that matches the accountability — rooms where you own the decision, not only the result",
    "strategic": "a problem hard enough to need your judgement — rooms where your read is what moves things",
    "independence": "a remit that is genuinely yours — rooms where the outcome rests on your own standard",
    "entrepreneurial": "ownership of the outcome — rooms where you build the thing, not run someone else's play",
    "risk": "freedom to move when the window opens — rooms that reward a timely call over a safe wait",
    "stability": "structure and a long horizon — rooms where steady effort compounds into standing",
}
# strongest career planet -> 10th-house basis (page 31 callout)
_TENTH = {
    "Saturn": "A Saturn-strong 10th house favours earned, structural authority over borrowed or purely positional rank.",
    "Jupiter": "A Jupiter-supported 10th house favours authority built on judgement and trust rather than title.",
    "Sun": "A Sun-supported 10th house favours visible, front-of-room authority you carry in your own name.",
    "Mercury": "A Mercury-supported 10th house favours authority earned through sharp thinking and clear communication.",
    "Mars": "A Mars-supported 10th house favours authority won by decisive action, not by waiting your turn.",
}


def _page29_doors(p, dd):
    """Where the doors may open — 3 role-fit cards ranked from top ddims + naukri lean."""
    lean = p["entrepreneurial"]["lean"]  # engine: POSITIVE = job/career-leaning, negative = enterprise
    # candidate roles, each scored off the dimension that drives its fit
    cands = [
        (dd["leadership"], "Senior leadership &amp; ownership",
         "Roles where the strategy and the outcome are yours to shape."),
        (dd["strategic"], "Advisory &amp; consulting",
         "Selling judgement rather than hours — your experience becomes the product."),
        (max(dd["entrepreneurial"], dd["risk"]) + (8 if lean < 0 else -8),
         "Independent practice / venture",
         "A capital-light path to autonomy — ideally with a partner for structure."),
        (dd["stability"] + (8 if lean > 0 else 0), "Structured senior roles",
         "Scope and a long horizon, where steadiness compounds into standing."),
    ]
    top3 = sorted(cands, key=lambda c: c[0], reverse=True)[:3]

    def card(rank, score, title, desc):
        strong = rank == 0 or score >= 74   # the best fit is always a Strong fit
        cls, tag = ("wg grn", "Strong fit") if strong else ("wg", "Explore")
        return (f'<div class="win"><span class="{cls}">{tag}</span>'
                f'<div class="wt">{title}</div><div class="wd">{desc}</div></div>')

    # the 3 mock cards are 3 distinct one-liners; replace each slot with the ranked fit
    olds = [
        '<div class="win"><span class="wg grn">Strong fit</span><div class="wt">Senior leadership &amp; ownership</div><div class="wd">Roles where the strategy and the outcome are yours to shape.</div></div>',
        '<div class="win"><span class="wg grn">Strong fit</span><div class="wt">Advisory &amp; consulting</div><div class="wd">Selling judgement rather than hours — your two decades become the product.</div></div>',
        '<div class="win"><span class="wg">Explore</span><div class="wt">Independent practice / venture</div><div class="wd">A structured, capital-light path to autonomy — ideally with a partner.</div></div>',
    ]
    return [(olds[i], card(i, *top3[i])) for i in range(3)]


def _page31_rooms(p, dd):
    """The rooms you belong in — 3 rooms from top-3 ddims + common thread + 10th-house basis."""
    top3 = _ranked(dd)[:3]
    top = top3[0]

    def room(k):
        b, s = _ROOM[k]
        return (f'<div class="pt good"><svg class="pi"><use href="#i-check"/></svg>'
                f'<div class="tx"><b>{b}</b><span>{s}</span></div></div>')

    planets = p["chart"]["planets"]
    cp = max(("Saturn", "Jupiter", "Sun", "Mercury", "Mars"),
             key=lambda x: planets.get(x, {}).get("dscore", 0))

    thread = (f'The common thread is {_THREAD[top]}. Where that holds you do your best work; '
              f'where it is missing, even a senior title feels hollow.')

    return [
        ('<div class="pt good"><svg class="pi"><use href="#i-check"/></svg><div class="tx"><b>Senior management &amp; ownership</b><span>Where structure and long horizons are an asset, not a constraint.</span></div></div>',
         room(top3[0])),
        ('<div class="pt good"><svg class="pi"><use href="#i-check"/></svg><div class="tx"><b>Advisory &amp; board roles</b><span>Judgement without day-to-day execution suits this stage well.</span></div></div>',
         room(top3[1])),
        ('<div class="pt good"><svg class="pi"><use href="#i-check"/></svg><div class="tx"><b>Independent leadership</b><span>A team you shape around your own standard.</span></div></div>',
         room(top3[2])),
        ('The common thread is authority that matches the accountability — rooms where you own the decision, not only the result. Where those two line up you do your best work; where they split, even a senior title feels hollow.',
         thread),
        ('A Saturn-strong 10th house favours earned, structural authority over borrowed or purely positional rank.',
         _TENTH[cp]),
    ]


def _page32_reinvention(p, dd):
    """Is this a phase for reinvention? — verdict + 3 points from phase md_lord + dims + archetype."""
    md = p["phase"]["md_lord"]
    arch = p["archetype"]["name"]
    reinventor = arch in ("The Reinventor", "The Visionary")
    bold = (dd["risk"] + dd["independence"]) / 2

    if md in ("Rahu", "Ketu", "Mars"):
        tier = "strong"
    elif md in ("Saturn", "Mercury"):
        tier = "evolution"
    else:  # Venus, Jupiter, Sun, Moon — growth-leaning
        tier = "growth"
    # the person's own appetite can lift a soft verdict one notch
    if tier == "growth" and (reinventor or bold >= 76):
        tier = "evolution"
    if tier == "evolution" and reinventor and bold >= 80:
        tier = "strong"

    CONTENT = {
        "strong": {
            "vt": "Yes — the chart favours a genuine change of direction",
            "lead": "Your chart backs a real shift now, not a cosmetic one — the appetite and the timing line up to remake the shape of your work, not just its setting.",
            "compass": ("A real change of direction", "Not a tweak — the kind of move that resets what you do, not only where you do it."),
            "hourglass": ("The window is open now", "The timing favours acting on it rather than waiting for a safer season."),
            "shield": ("Your credibility travels", "What you have already built comes with you into the new form."),
        },
        "evolution": {
            "vt": "Yes — but as evolution, not rupture",
            "lead": "Your chart supports a meaningful change of form now — not throwing away what you built, but redirecting it into a more self-directed setting.",
            "compass": ("Same craft, new container", "The expertise stays; the setting that holds it is what changes."),
            "hourglass": ("Gradual, not overnight", "A deliberate redirection over quarters — the version of change your chart rewards."),
            "shield": ("Kept, not discarded", "The credibility you have already built travels with you into the new form."),
        },
        "growth": {
            "vt": "More a season of growth than reinvention",
            "lead": "This reads less as reinvention and more as deepening — building on the path you are on rather than switching off it.",
            "compass": ("Deepen, don't switch", "The gains now come from going further on your current path, not changing it."),
            "hourglass": ("Compounding, not resetting", "Steady progress on what you already do is what the timing rewards."),
            "shield": ("Consolidate the base", "Strengthen what you have built before any larger change of form."),
        },
    }
    c = CONTENT[tier]

    def pt(icon, key):
        b, s = c[key]
        return (f'<div class="pt"><svg class="pi"><use href="#{icon}"/></svg>'
                f'<div class="tx"><b>{b}</b><span>{s}</span></div></div>')

    return [
        ('<div class="vt">Yes — but as evolution, not rupture</div>',
         f'<div class="vt">{c["vt"]}</div>'),
        ('<p class="lead">Your chart supports a meaningful change of form now — not throwing away what you built, but redirecting it into a more self-directed setting.</p>',
         f'<p class="lead">{c["lead"]}</p>'),
        ('<div class="pt"><svg class="pi"><use href="#i-compass"/></svg><div class="tx"><b>Same craft, new container</b><span>The expertise stays; the setting that holds it is what changes.</span></div></div>',
         pt("i-compass", "compass")),
        ('<div class="pt"><svg class="pi"><use href="#i-hourglass"/></svg><div class="tx"><b>Gradual, not overnight</b><span>A deliberate redirection over quarters — the version of change your chart rewards.</span></div></div>',
         pt("i-hourglass", "hourglass")),
        ('<div class="pt"><svg class="pi"><use href="#i-shield"/></svg><div class="tx"><b>Kept, not discarded</b><span>Two decades of credibility travel with you into the new form.</span></div></div>',
         pt("i-shield", "shield")),
    ]


def _page33_thrive(p, dd):
    """Where you thrive — sweet-spot verdict + lead + 3 conditions from top-3 ddims."""
    top3 = _ranked(dd)[:3]
    a, b, c = (_SPOT_WORD[k] for k in top3)
    n1, n2, n3 = (_NEED[k] for k in top3)

    vt = f"Roles that combine {a}, {b} and {c} — with the outcome genuinely yours to own."
    lead = f"Give you {n1}, {n2} and {n3}, and you do your strongest work."

    # 3 condition slots keep their icons (compass / scales / people) in order
    icons = ["i-compass", "i-scales", "i-people"]

    def cond(i):
        ttl, desc = _COND[top3[i]]
        return (f'<div class="pt good"><svg class="pi"><use href="#{icons[i]}"/></svg>'
                f'<div class="tx"><b>{ttl}</b><span>{desc}</span></div></div>')

    return [
        ('<div class="vt">High-autonomy roles combining strategy, decision-making and people influence — where you own the outcome.</div>',
         f'<div class="vt">{vt}</div>'),
        ('<p class="lead">A complex problem, real authority over the answer, and a team to move it through — that brings out your strongest work.</p>',
         f'<p class="lead">{lead}</p>'),
        ('<div class="pt good"><svg class="pi"><use href="#i-compass"/></svg><div class="tx"><b>A problem worth solving</b><span>Complex and open-ended, with real consequences riding on the answer.</span></div></div>',
         cond(0)),
        ('<div class="pt good"><svg class="pi"><use href="#i-scales"/></svg><div class="tx"><b>Real authority over it</b><span>The call is genuinely yours — not recommended upward for someone else to make.</span></div></div>',
         cond(1)),
        ('<div class="pt good"><svg class="pi"><use href="#i-people"/></svg><div class="tx"><b>A team to move it</b><span>People to carry the execution while you hold the strategy.</span></div></div>',
         cond(2)),
    ]


def _page34_venn(p, dd):
    """Your sweet spot (venn) — relabel the 3 circles to top-3 ddim themes; keep SVG structure."""
    top3 = _ranked(dd)[:3]
    t1, t2, t3 = (_THEME[k] for k in top3)

    return [
        # action headline
        ('<h2 class="action">You thrive where strategy, authority and people meet.</h2>',
         f'<h2 class="action">You thrive where {t1.lower()}, {t2.lower()} and {t3.lower()} meet.</h2>'),
        # 3 circle labels — keep coords + fill, change only the label text
        ('<text x="72" y="70" text-anchor="middle" fill="#C9A34E">Strategy</text>',
         f'<text x="72" y="70" text-anchor="middle" fill="#C9A34E">{t1}</text>'),
        ('<text x="188" y="70" text-anchor="middle" fill="#3E7D5A">Authority</text>',
         f'<text x="188" y="70" text-anchor="middle" fill="#3E7D5A">{t2}</text>'),
        ('<text x="130" y="200" text-anchor="middle" fill="#B4572B">People</text>',
         f'<text x="130" y="200" text-anchor="middle" fill="#B4572B">{t3}</text>'),
        # legend line naming the three circles
        ('<b>The three circles.</b> Strategy, authority and people — your work needs all three.',
         f'<b>The three circles.</b> {t1}, {t2} and {t3} — your work needs all three.'),
    ]


BUILDERS = [
    _page29_doors,
    _page31_rooms,
    _page32_reinvention,
    _page33_thrive,
    _page34_venn,
]
