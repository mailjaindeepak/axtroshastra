"""Career Intelligence — narrative personalization, Part 3.

The career-arc + three-year-window prose pages (14, 15, 25, 26, 27, 28 of the
57-card body). Same contract/voice as ci_narrative.py: each builder returns
(old, new) exact-replacement pairs; `new` keeps the SAME HTML structure and the
SAME SVG `<use href="#i-..."/>` icons as `old` — only human-readable prose
changes. Every claim is traceable to computed data:

  * pages 14/15 key off p['phase']['md_lord'] (which dasha lord rules now),
    NOT the phase name string (the renderer replaces that).
  * pages 25/26/27/28 key off p['three_year']['peak_year'] (1|2|3 = which of the
    next three years the strongest window lands) and ['best_window'].

An (old, new) pair is emitted only when the personalized text actually differs
from the mock, so a persona whose chart matches the mock is left untouched.
Independent module — no import from ci_narrative.
"""


def _bucket(md_lord):
    """Which arc stage the current dasha lord reads as (per the brief)."""
    if md_lord in ("Rahu", "Ketu", "Mars"):
        return "reinvent"          # breakout / expand
    if md_lord in ("Sun", "Jupiter"):
        return "growth"            # visible growth
    return "consolidate"           # Saturn / Mercury / Venus / Moon / default


# ------------------------------------------------ page 14: shape of the journey
# The three timeline stages, verbatim from career_intelligence_assets.py.
_P14_BUILD = ('<div class="tli"><div class="dt">Build</div><div class="th">The foundation years</div>'
              '<div class="td">Went deep, earned credibility, built real expertise rather than chasing titles early.</div></div>')
_P14_CONSOL = ('<div class="tli"><div class="dt">Consolidate</div><div class="th">Where you are now</div>'
               '<div class="td">Converting depth into leverage — the person others rely on for judgement.</div></div>')
_P14_REINV = ('<div class="tli"><div class="dt">Reinvent</div><div class="th">The chapter ahead</div>'
              '<div class="td">Applying everything you have built in a more self-directed form.</div></div>')

_P14_TH = {
    0: {"past": "The foundation years", "cur": "Where you are now"},
    1: {"past": "The years just behind you", "cur": "Where you are now", "fut": "The chapter ahead"},
    2: {"cur": "Where you are now", "fut": "The chapter ahead"},
}
_P14_TD = {
    0: {"past": "Went deep, earned credibility, built real expertise rather than chasing titles early.",
        "cur": "Going deep now — earning credibility and building real expertise rather than chasing titles early."},
    1: {"past": "Turned depth into leverage — became the person others rely on for judgement.",
        "fut": "Converting depth into leverage — the person others rely on for judgement."},
    2: {"fut": "Applying everything you have built in a more self-directed form."},
}
# description of whichever stage is CURRENT, by bucket
_P14_CUR_DESC = {
    "consolidate": "Converting depth into leverage — the person others rely on for judgement.",
    "growth": "In a visible, expanding phase — the depth you banked is compounding into wider reach and recognition now.",
    "reinvent": "Reshaping your role now — everything you have built, in a freer and more self-directed form.",
}
_P14_DT = ["Build", "Consolidate", "Reinvent"]


def _page14_shape(p, dd):
    b = _bucket((p.get("phase") or {}).get("md_lord"))
    cur = 2 if b == "reinvent" else 1
    old = [_P14_BUILD, _P14_CONSOL, _P14_REINV]
    out = []
    for i in range(3):
        role = "cur" if i == cur else ("past" if i < cur else "fut")
        th = _P14_TH[i][role]
        td = _P14_CUR_DESC[b] if role == "cur" else _P14_TD[i][role]
        new = (f'<div class="tli"><div class="dt">{_P14_DT[i]}</div>'
               f'<div class="th">{th}</div><div class="td">{td}</div></div>')
        if new != old[i]:
            out.append((old[i], new))
    return out


# ------------------------------------------------------- page 15: journey arc
_P15_HINGE_OLD = '<h2 class="action">You are at the hinge between consolidating and reinventing.</h2>'
_P15_LEGCON_OLD = '<b>Consolidate</b> — turning that depth into leverage now.'
_P15_LEGREI_OLD = '<b>Reinvent</b> — the same skill, in a freer form.'
_P15_READ_OLD = ('<div class="take"><b>The read</b>The build is done. The next move is not more of the same '
                 '— it is a change of form.</div>')


def _page15_arc(p, dd):
    b = _bucket((p.get("phase") or {}).get("md_lord"))
    hinge = {
        "consolidate": "You are at the hinge between consolidating and reinventing.",
        "growth": "You are past consolidation and into a phase of visible growth.",
        "reinvent": "You are already reinventing — the build and the consolidation sit behind you.",
    }[b]
    legcon = {
        "consolidate": "<b>Consolidate</b> — turning that depth into leverage now.",
        "growth": "<b>Consolidate</b> — that depth is compounding into reach now.",
        "reinvent": "<b>Consolidate</b> — done; that leverage is yours to spend.",
    }[b]
    legrei = {
        "consolidate": "<b>Reinvent</b> — the same skill, in a freer form.",
        "growth": "<b>Reinvent</b> — the same skill, in a more visible form ahead.",
        "reinvent": "<b>Reinvent</b> — the freer form you are moving into now.",
    }[b]
    read = {
        "consolidate": "The build is done. The next move is not more of the same — it is a change of form.",
        "growth": "The build is banked. You are on the rise now — the lever is reach and visibility, not more effort.",
        "reinvent": "The consolidation is done. You are already changing form — the task now is to commit to it fully.",
    }[b]
    pairs = [
        (_P15_HINGE_OLD, f'<h2 class="action">{hinge}</h2>'),
        (_P15_LEGCON_OLD, legcon),
        (_P15_LEGREI_OLD, legrei),
        (_P15_READ_OLD, f'<div class="take"><b>The read</b>{read}</div>'),
    ]
    return [(o, n) for o, n in pairs if o != n]


# ----------------------------------------- pages 25/26/27: the three-year window
def _peak(p):
    ty = p.get("three_year") or {}
    return int(ty.get("peak_year") or 2), ty.get("best_window")


def _win_txt(win):
    return f" The strongest stretch reads around {win}." if win else ""


_P25_INTRO_OLD = ('<p class="lead">A year to sharpen focus and become known for one thing. The work is often '
                  'invisible — groundwork, relationships, the story you tell about yourself.</p>')
_P25_BASIS_OLD = ('<div class="callout"><div class="ch">Astrological basis</div><p>An antardasha emphasising '
                  'preparation and internal restructuring over outward expansion.</p></div>')


def _page25_year1(p, dd):
    peak, win = _peak(p)
    if peak == 1:
        intro = ("This is your window. The strongest opening of the three years is now — this year positioning "
                 "is not preparation, it is the move itself.")
        basis = ("Your major and sub-period line up now — the antardasha opens the clearest window of the three "
                 "years." + _win_txt(win))
    elif peak == 2:
        intro = ("A year to sharpen focus and become known for one thing. The work is often invisible — "
                 "groundwork, relationships, the story you tell about yourself. It sets up the larger move in Year 2.")
        basis = None
    else:
        intro = ("A year to sharpen focus and become known for one thing. The real opening lands further out, in "
                 "Year 3 — so this year is patient groundwork, not a push.")
        basis = None
    out = [(_P25_INTRO_OLD, f'<p class="lead">{intro}</p>')]
    if basis:
        out.append((_P25_BASIS_OLD,
                    f'<div class="callout"><div class="ch">Astrological basis</div><p>{basis}</p></div>'))
    return [(o, n) for o, n in out if o != n]


_P26_INTRO_OLD = ('<p class="lead">The period that may most reward a considered, larger move — a role, mandate, '
                  'or venture that uses everything built in Year 1. If a bigger step is coming, this is its window.</p>')
_P26_BASIS_OLD = ('<div class="callout"><div class="ch">Astrological basis</div><p>A more expansive sub-period, '
                  'supportive of growth, visibility and new undertakings.</p></div>')


def _page26_year2(p, dd):
    peak, win = _peak(p)
    if peak == 2:
        intro = ("The period that may most reward a considered, larger move — a role, mandate, or venture that "
                 "uses everything built in Year 1. This is your window: if a bigger step is coming, this is when "
                 "to make it.")
        basis = ("A more expansive sub-period, supportive of growth, visibility and new undertakings — the "
                 "strongest of the three years." + _win_txt(win))
    elif peak == 1:
        intro = ("A year to build on a move already made. Your strongest window was Year 1 — here you expand and "
                 "stabilise what you have already set in motion.")
        basis = None
    else:
        intro = ("A steadying year between positioning and the larger move. Your strongest window is Year 3, so "
                 "this year keeps momentum without forcing the big step early.")
        basis = None
    out = [(_P26_INTRO_OLD, f'<p class="lead">{intro}</p>')]
    if basis:
        out.append((_P26_BASIS_OLD,
                    f'<div class="callout"><div class="ch">Astrological basis</div><p>{basis}</p></div>'))
    return [(o, n) for o, n in out if o != n]


_P27_INTRO_OLD = ('<p class="lead">A phase where a meaningful shift becomes natural — consolidating the Year-2 '
                  'gain, or stepping into a different kind of leadership. Change here feels like evolution, not '
                  'rupture.</p>')
_P27_BASIS_OLD = ('<div class="callout"><div class="ch">Astrological basis</div><p>A junction between '
                  'major/sub-periods — a natural moment to settle into a new form of your role.</p></div>')


def _page27_year3(p, dd):
    peak, win = _peak(p)
    if peak == 3:
        intro = ("This is your window. The strongest opening lands in Year 3 — the larger move belongs here, not "
                 "earlier; the first two years are its run-up.")
        basis = ("The sub-period peaks here — a junction that opens the clearest window of the three years."
                 + _win_txt(win))
    elif peak == 2:
        intro = ("A phase where a meaningful shift becomes natural — consolidating the Year-2 gain, or stepping "
                 "into a different kind of leadership. Change here feels like evolution, not rupture.")
        basis = None
    else:
        intro = ("A phase to consolidate. With your strongest window back in Year 1, this year settles and "
                 "compounds the gain rather than chasing a new one.")
        basis = None
    out = [(_P27_INTRO_OLD, f'<p class="lead">{intro}</p>')]
    if basis:
        out.append((_P27_BASIS_OLD,
                    f'<div class="callout"><div class="ch">Astrological basis</div><p>{basis}</p></div>'))
    return [(o, n) for o, n in out if o != n]


# ---------------------------------------------- page 28: three-year roadmap exhibit
_P28_H2_OLD = '<h2 class="action">Position now, expand in Year 2, settle in Year 3.</h2>'
_P28_SUB_OLD = '<div class="subtit">Your window for the larger move is the middle year</div>'
_P28_LEG1_OLD = '<b>Year 1 — Positioning.</b> Groundwork, not visible moves.'
_P28_LEG2_OLD = '<b>Year 2 — Expansion.</b> The move most rewarded.'
_P28_LEG3_OLD = '<b>Year 3 — Transition.</b> Consolidate the gain.'
_P28_READ_OLD = '<div class="take"><b>The read</b>Prepare in Year 1 so you can act decisively in Year 2.</div>'


def _page28_roadmap(p, dd):
    peak, win = _peak(p)
    h2 = {
        1: "The window is now — move in Year 1, then build and settle across Years 2 and 3.",
        2: "Position now, expand in Year 2, settle in Year 3.",
        3: "Position and build first; the larger move belongs in Year 3.",
    }[peak]
    sub = {1: "Your window for the larger move is the first year",
           2: "Your window for the larger move is the middle year",
           3: "Your window for the larger move is the third year"}[peak]
    read = {
        1: "The window is open now — act in Year 1, then spend Years 2 and 3 compounding it.",
        2: "Prepare in Year 1 so you can act decisively in Year 2.",
        3: "Lay the groundwork through Years 1 and 2 so the larger move in Year 3 lands with full force.",
    }[peak]
    leg1 = ("<b>Year 1 — Positioning.</b> The move most rewarded — the window is now." if peak == 1
            else "<b>Year 1 — Positioning.</b> Groundwork, not visible moves.")
    leg2 = ("<b>Year 2 — Expansion.</b> The move most rewarded." if peak == 2
            else "<b>Year 2 — Expansion.</b> The connective year between positioning and the move.")
    leg3 = ("<b>Year 3 — Transition.</b> The move most rewarded — the window lands here." if peak == 3
            else "<b>Year 3 — Transition.</b> Consolidate the gain.")
    pairs = [
        (_P28_H2_OLD, f'<h2 class="action">{h2}</h2>'),
        (_P28_SUB_OLD, f'<div class="subtit">{sub}</div>'),
        (_P28_LEG1_OLD, leg1),
        (_P28_LEG2_OLD, leg2),
        (_P28_LEG3_OLD, leg3),
        (_P28_READ_OLD, f'<div class="take"><b>The read</b>{read}</div>'),
    ]
    return [(o, n) for o, n in pairs if o != n]


BUILDERS = [
    _page14_shape,
    _page15_arc,
    _page25_year1,
    _page26_year2,
    _page27_year3,
    _page28_roadmap,
]
