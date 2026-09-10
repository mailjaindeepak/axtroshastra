"""Career Intelligence — narrative personalization, Part II (pages 16-21).

Personalizes the prose/exhibit pages that state a chart-derived finding, so no
page ships the mock persona's ("Rajesh Menon") claims to another buyer (Rule 2).
Same contract as ci_narrative: each builder returns [(old, new), ...] of exact
string replacements against career_intelligence_assets.CI_BODY. `new` keeps the
SAME HTML structure and the SAME SVG <use href="#i-..."/> icons as `old`; only
the human-readable text/number changes. Every shown value/width/percentage is a
real function of the buyer's `ddims` or a planet dscore — no invented numbers.
Analyst voice, em-dashes allowed (report prose, not testimonials).

Helpers (_cap/_ranked/_lvl) are copied from ci_narrative so this module stays
independent; cir._disp is imported for the Status motivator (Sun dscore display).
"""

import math
import career_intelligence_report as cir

_DIM_BAR_LABEL = {"leadership": "Leadership", "strategic": "Strategic thinking",
                  "independence": "Independence", "entrepreneurial": "Enterprise drive",
                  "risk": "Bold, timely moves", "stability": "Long-horizon patience"}


def _cap(s):
    return s[:1].upper() + s[1:]


def _ranked(ddims):
    return sorted(ddims, key=ddims.get, reverse=True)


def _lvl(v):
    return "high" if v >= 76 else "mod" if v >= 62 else "low"


def _round100(vals):
    """Round floats (summing ~100) to ints summing exactly 100 (largest remainder)."""
    fl = [int(v) for v in vals]
    rem = 100 - sum(fl)
    order = sorted(range(len(vals)), key=lambda i: vals[i] - fl[i], reverse=True)
    for i in range(rem):
        fl[order[i]] += 1
    return fl


# ---- the five work-motivators, mapped to the buyer's computed dims -----------
# Purpose&mastery<-strategic, Autonomy&freedom<-independence, Impact&legacy<-leadership,
# Security&stability<-stability, Status&recognition<-cir._disp(Sun dscore)
_MOT_LABEL = {"strategic": "Purpose &amp; mastery", "independence": "Autonomy &amp; freedom",
              "leadership": "Impact &amp; legacy", "stability": "Security &amp; stability",
              "status": "Status &amp; recognition"}
_MOT_SHORT = {"strategic": "Purpose &amp; mastery", "independence": "Autonomy",
              "leadership": "Impact", "stability": "Security", "status": "Status"}
_MOT_CENTER = {"strategic": "Purpose", "independence": "Autonomy",
               "leadership": "Impact", "stability": "Security", "status": "Status"}
_MOT_WORD = {"strategic": "meaning", "independence": "autonomy", "leadership": "impact",
             "stability": "security", "status": "status"}
_MOT_PHRASE = {"strategic": "the problem itself and mastering it",
               "independence": "the freedom to solve it your own way",
               "leadership": "the mark your work leaves",
               "stability": "a secure, stable base",
               "status": "recognition and standing"}


def _motivators(payload, ddims):
    """The five motivator scores, all traceable to computed data."""
    sun = payload["chart"]["planets"].get("Sun", {}).get("dscore", 50)
    return {"strategic": ddims["strategic"], "independence": ddims["independence"],
            "leadership": ddims["leadership"], "stability": ddims["stability"],
            "status": cir._disp(sun)}


# ---------------------------------------------------------------- PAGE 16 ------
def _page16_recurring_themes(payload, ddims):
    """Themes that keep returning — pick the 4 themes that fit THIS chart.
    Keeps the four icon slots (i-gem, i-shield, i-trend, i-alert/warn); swaps the
    b/span text. Each candidate theme is scored from ddims / planet dscores."""
    planets = payload["chart"]["planets"]
    sun = planets.get("Sun", {}).get("dscore", 50)
    sat = planets.get("Saturn", {}).get("dscore", 50)
    arch = (payload.get("archetype") or {}).get("name", "")
    reinvent_boost = 12 if any(w in arch for w in ("Reinvent", "Visionary")) else 0

    pool = [
        ((100 - sun) + sat * 0.5, "Delayed recognition",
         "Your value has often landed later than it was delivered — the credit tends to trail the contribution."),
        (ddims["leadership"], "Rising responsibility",
         "Responsibility keeps finding you — you are handed the things that actually matter."),
        ((ddims["risk"] + ddims["independence"]) / 2 + reinvent_boost, "Periodic reinvention",
         "Every few years you reshape your role rather than simply continue it."),
        (ddims["independence"], "Friction with rigid hierarchy",
         "You respect earned rank, not positional rank — a title alone does not move you."),
        (ddims["stability"], "Quiet compounding",
         "Your gains arrive by accumulation, not sudden breaks — the long line trends up."),
        (ddims["entrepreneurial"], "Drawn to owning the outcome",
         "You keep drifting toward work that is yours to own, not someone else's play to run."),
        (ddims["strategic"], "Depth before breadth",
         "You go deep before you go wide — one hard thing mastered over many held loosely."),
    ]
    top4 = sorted(pool, key=lambda t: t[0], reverse=True)[:4]
    icons = ["i-gem", "i-shield", "i-trend", "i-alert"]
    cls = ["pt", "pt", "pt", "pt warn"]
    new = "\n".join(
        f'    <div class="{cls[i]}"><svg class="pi"><use href="#{icons[i]}"/></svg>'
        f'<div class="tx"><b>{top4[i][1]}</b><span>{top4[i][2]}</span></div></div>'
        for i in range(4))

    old = (
        '    <div class="pt"><svg class="pi"><use href="#i-gem"/></svg><div class="tx"><b>Delayed recognition</b><span>Your value has often been acknowledged later than it was delivered.</span></div></div>\n'
        '    <div class="pt"><svg class="pi"><use href="#i-shield"/></svg><div class="tx"><b>Rising responsibility</b><span>Responsibility finds you — you are handed the things that matter.</span></div></div>\n'
        '    <div class="pt"><svg class="pi"><use href="#i-trend"/></svg><div class="tx"><b>Periodic reinvention</b><span>Every few years, you reshape your role rather than simply continue it.</span></div></div>\n'
        '    <div class="pt warn"><svg class="pi"><use href="#i-alert"/></svg><div class="tx"><b>Friction with rigid hierarchy</b><span>You respect earned rank, not positional rank.</span></div></div>')
    return [(old, new)]


# ---------------------------------------------------------------- PAGE 17 ------
def _page17_motivates(payload, ddims):
    """What actually motivates you — 5 motivators ranked by value; Primary/Strong/
    Moderate/Secondary tags + bar widths from the ranking; summary + 'what this
    means' rewritten from the top two."""
    mot = _motivators(payload, ddims)
    order = sorted(mot, key=mot.get, reverse=True)
    tags = ["Primary", "Strong", "Strong", "Moderate", "Secondary"]

    rows = "\n".join(
        f'    <div class="rr"><div class="rl">{_MOT_LABEL[k]} <span>{tags[i]}</span></div>'
        f'<div class="bar"><i style="width:{min(mot[k], 98)}%"></i></div></div>'
        for i, k in enumerate(order))
    old_rows = (
        '    <div class="rr"><div class="rl">Purpose &amp; mastery <span>Primary</span></div><div class="bar"><i style="width:90%"></i></div></div>\n'
        '    <div class="rr"><div class="rl">Autonomy &amp; freedom <span>Strong</span></div><div class="bar"><i style="width:82%"></i></div></div>\n'
        '    <div class="rr"><div class="rl">Impact &amp; legacy <span>Strong</span></div><div class="bar"><i style="width:74%"></i></div></div>\n'
        '    <div class="rr"><div class="rl">Security &amp; stability <span>Moderate</span></div><div class="bar"><i style="width:52%"></i></div></div>\n'
        '    <div class="rr"><div class="rl">Status &amp; recognition <span>Secondary</span></div><div class="bar"><i style="width:40%"></i></div></div>')

    top1, top2, last = order[0], order[1], order[-1]
    lead = (f'What pulls you hardest is {_MOT_PHRASE[top1]} and {_MOT_PHRASE[top2]}. '
            f'{_cap(_MOT_WORD[last])} still matters, but it follows the work rather than leads it.')
    means = (f'You are moved most by {_MOT_WORD[top1]} and {_MOT_WORD[top2]}. Design the next '
             f'role around those two, and the rest tends to follow rather than lead.')

    return [
        (old_rows, rows),
        ('<p class="lead" style="margin-top:14px">Notice the gap between the top three and the bottom two: what pulls you is internal — the problem itself, the freedom to solve it your way, the mark it leaves. Pay and title still matter, but they follow the work rather than lead it.</p>',
         f'<p class="lead" style="margin-top:14px">{lead}</p>'),
        ('<div class="callout"><div class="ch">What this means</div><p>You are moved by meaning and ownership more than title or money. Autonomy holds you longer than a raise.</p></div>',
         f'<div class="callout"><div class="ch">What this means</div><p>{means}</p></div>'),
    ]


# ---------------------------------------------------------------- PAGE 18 ------
def _page18_drivers_donut(payload, ddims):
    """What drives you (donut) — normalize the 5 motivator scores to % summing 100,
    collapse the two lowest into one slice; recompute the donut arc dasharrays;
    rewrite labels, action line, design note, read and centre word."""
    mot = _motivators(payload, ddims)
    order = sorted(mot, key=mot.get, reverse=True)
    top4 = order[:4]                                    # 4 wedges = the 4 strongest drivers
    sub = sum(mot[k] for k in top4) or 1                # the 5th (lowest) "barely registers"
    slice_pct = _round100([mot[k] / sub * 100 for k in top4])
    top1, top2, top3 = order[0], order[1], order[2]
    labels = [_MOT_SHORT[k] for k in top4]
    colors = ["#B9862E", "#C9A34E", "#A6791E", "#C9BFA6"]

    # --- arcs: circumference of r=70; each arc = pct/100 * C; offsets stack ----
    C = 2 * math.pi * 70
    arcs, cum = [], 0.0
    for i, pct in enumerate(slice_pct):
        L = pct / 100 * C
        da = f'{round(L)} {round(C - L)}'
        off = '' if i == 0 else f' stroke-dashoffset="{-round(cum)}"'
        arcs.append(f'    <circle cx="100" cy="100" r="70" fill="none" stroke="{colors[i]}" '
                    f'stroke-width="26" stroke-dasharray="{da}"{off} transform="rotate(-90 100 100)"/>')
        cum += L
    new_arcs = "\n".join(arcs)
    old_arcs = (
        '    <circle cx="100" cy="100" r="70" fill="none" stroke="#B9862E" stroke-width="26" stroke-dasharray="145 295" transform="rotate(-90 100 100)"/>\n'
        '    <circle cx="100" cy="100" r="70" fill="none" stroke="#C9A34E" stroke-width="26" stroke-dasharray="110 330" stroke-dashoffset="-145" transform="rotate(-90 100 100)"/>\n'
        '    <circle cx="100" cy="100" r="70" fill="none" stroke="#A6791E" stroke-width="26" stroke-dasharray="92 348" stroke-dashoffset="-255" transform="rotate(-90 100 100)"/>\n'
        '    <circle cx="100" cy="100" r="70" fill="none" stroke="#C9BFA6" stroke-width="26" stroke-dasharray="92 348" stroke-dashoffset="-347" transform="rotate(-90 100 100)"/>')

    new_leg = "\n".join(
        f'    <div class="lr"><span class="dot" style="background:{colors[i]}"></span>'
        f'<span class="lt"><b>{labels[i]}</b> — {slice_pct[i]}%</span></div>'
        for i in range(4))
    old_leg = (
        '    <div class="lr"><span class="dot" style="background:#B9862E"></span><span class="lt"><b>Purpose &amp; mastery</b> — 33%</span></div>\n'
        '    <div class="lr"><span class="dot" style="background:#C9A34E"></span><span class="lt"><b>Autonomy</b> — 25%</span></div>\n'
        '    <div class="lr"><span class="dot" style="background:#A6791E"></span><span class="lt"><b>Impact</b> — 21%</span></div>\n'
        '    <div class="lr"><span class="dot" style="background:#C9BFA6"></span><span class="lt"><b>Security / status</b> — 21%</span></div>')

    top2sum = slice_pct[0] + slice_pct[1]
    action = (f'{_cap(_MOT_WORD[top1])} and {_MOT_WORD[top2]} dominate what drives you; '
              f'{_MOT_WORD[order[-1]]} barely registers.')
    note = (f'Roughly {top2sum}% of your drive is {_MOT_WORD[top1]} and {_MOT_WORD[top2]}. A role '
            f'that maxes the pay band but caps either one tends to feel thin within a year.')
    read = f'Design the next role around {_MOT_WORD[top1]} and {_MOT_WORD[top2]} — not the pay band.'

    return [
        ('<h2 class="action">Meaning and autonomy dominate; status barely registers.</h2>',
         f'<h2 class="action">{action}</h2>'),
        (old_arcs, new_arcs),
        ('font-weight="600">Purpose</text>', f'font-weight="600">{_MOT_CENTER[top1]}</text>'),
        (old_leg, new_leg),
        ('<div class="callout" style="margin-top:12px"><div class="ch">Design note</div><p>Roughly two-thirds of your drive is meaning and control. A role that maxes the pay band but caps either one tends to feel thin within a year.</p></div>',
         f'<div class="callout" style="margin-top:12px"><div class="ch">Design note</div><p>{note}</p></div>'),
        ('<div class="take"><b>The read</b>Design the next role around meaning and control — not the pay band.</div>',
         f'<div class="take"><b>The read</b>{read}</div>'),
    ]


# ---------------------------------------------------------------- PAGE 19 ------
def _page19_blind_spots(payload, ddims):
    """Your potential blind spots — pick the 3 that fit from bottom-2 dims,
    debilitated/combust lessons, and decision style. All keep the i-alert/warn slot."""
    ld, strat, ind = ddims["leadership"], ddims["strategic"], ddims["independence"]
    risk, stab = ddims["risk"], ddims["stability"]
    ds = payload.get("decision_style") or {}
    deliberate = ds.get("deliberate", False)
    lessons = payload.get("lessons") or []

    pool = [
        (stab, "Staying too long in the familiar",
         "Patience can tip into inertia — remaining past the point it still grows you."),
        (96 - stab, "Moving on before the base is set",
         "Restlessness can pull you to the next thing before the current one has had time to compound."),
        (strat + (10 if deliberate else -25), "Over-analysis on reversible calls",
         "You weigh small, undoable decisions as carefully as the large ones. Some deserve a faster yes."),
        ((ld + (96 - ind)) / 2, "Difficulty delegating fully",
         "High standards can mean carrying work others could own — capping both of you."),
        (96 - ind, "Over-reliance on structure",
         "You do your steadiest work inside a clear remit — worth trusting your own read on the open calls."),
        (risk, "Acting before the groundwork can carry it",
         "You move when the window opens, sometimes ahead of the base that has to support the move."),
    ]
    if lessons:
        les = lessons[0]
        pool.append((80, _cap(les["lesson"]),
                     f'Your chart flags this as a recurring pull — {les["planet"]} asks you to keep it in check as scope grows.'))

    # de-dupe by title, keep highest score, take top 3
    seen, ranked = {}, sorted(pool, key=lambda t: t[0], reverse=True)
    picks = []
    for sc, title, span in ranked:
        if title in seen:
            continue
        seen[title] = 1
        picks.append((title, span))
        if len(picks) == 3:
            break

    new = "\n".join(
        f'    <div class="pt warn"><svg class="pi"><use href="#i-alert"/></svg>'
        f'<div class="tx"><b>{t}</b><span>{s}</span></div></div>'
        for t, s in picks)
    old = (
        '    <div class="pt warn"><svg class="pi"><use href="#i-alert"/></svg><div class="tx"><b>Staying too long in the familiar</b><span>Patience can tip into inertia — remaining past the point it still grows you.</span></div></div>\n'
        '    <div class="pt warn"><svg class="pi"><use href="#i-alert"/></svg><div class="tx"><b>Excessive caution on reversible bets</b><span>You weigh small decisions as carefully as big ones. Some deserve a faster yes.</span></div></div>\n'
        '    <div class="pt warn"><svg class="pi"><use href="#i-alert"/></svg><div class="tx"><b>Difficulty delegating fully</b><span>High standards can mean carrying work others could own — capping both of you.</span></div></div>')
    return [(old, new)]


# ---------------------------------------------------------------- PAGE 20 ------
_SHADOW_TABLE = {"leadership": "Can dominate or over-own the outcome",
                 "strategic": "Over-analysis on small calls",
                 "independence": "Impatience with rigid hierarchy",
                 "stability": "Staying too long in the familiar",
                 "risk": "Acting before the base is set",
                 "entrepreneurial": "Spreading yourself too thin"}


def _page20_shadow_table(payload, ddims):
    """Every strength has a shadow (table) — one row per TOP-3 dim, each paired
    with its shadow. The 'why this matters' note names no traits, so it stays."""
    top3 = _ranked(ddims)[:3]
    new = "\n".join(f'    <tr><td>{_DIM_BAR_LABEL[k]}</td><td>{_SHADOW_TABLE[k]}</td></tr>'
                    for k in top3)
    old = (
        '    <tr><td>Strategic thinking</td><td>Over-analysis on small calls</td></tr>\n'
        '    <tr><td>Long-horizon patience</td><td>Staying too long in the familiar</td></tr>\n'
        '    <tr><td>Strong ownership</td><td>Difficulty delegating fully</td></tr>\n'
        '    <tr><td>Independent judgement</td><td>Impatience with hierarchy</td></tr>\n'
        '    <tr><td>High standards</td><td>Taking on too much yourself</td></tr>')
    return [(old, new)]


# ---------------------------------------------------------------- PAGE 21 ------
_SHADOW_SHORT = {"leadership": "Over-owning", "strategic": "Over-analysis",
                 "independence": "Impatience with hierarchy", "stability": "Staying too long",
                 "risk": "Acting too early", "entrepreneurial": "Spreading thin"}


def _page21_shadow_bars(payload, ddims):
    """Strength & its shadow (bars) — TOP-2 dims as strength bars (widths = their
    ddim values), each with a shadow bar (~0.62x, derived). Legend + read rewritten."""
    r = _ranked(ddims)
    k1, k2 = r[0], r[1]
    v1, v2 = min(ddims[k1], 98), min(ddims[k2], 98)
    sw1, sw2 = round(v1 * 0.62), round(v2 * 0.62)
    l1, l2 = _DIM_BAR_LABEL[k1], _DIM_BAR_LABEL[k2]
    s1, s2 = _SHADOW_SHORT[k1], _SHADOW_SHORT[k2]

    new_bars = (
        f'    <div class="bx"><div class="bl">{l1} <span>strength</span></div><div class="bt"><i style="width:{v1}%"></i></div></div>\n'
        f'    <div class="bx"><div class="bl" style="color:var(--terra)">↳ {s1} <span style="color:var(--terra)">watch</span></div><div class="bt"><i style="width:{sw1}%;background:linear-gradient(90deg,#E7B48F,var(--terra))"></i></div></div>\n'
        f'    <div class="bx"><div class="bl">{l2} <span>strength</span></div><div class="bt"><i style="width:{v2}%"></i></div></div>\n'
        f'    <div class="bx"><div class="bl" style="color:var(--terra)">↳ {s2} <span style="color:var(--terra)">watch</span></div><div class="bt"><i style="width:{sw2}%;background:linear-gradient(90deg,#E7B48F,var(--terra))"></i></div></div>')
    old_bars = (
        '    <div class="bx"><div class="bl">Strategic thinking <span>strength</span></div><div class="bt"><i style="width:92%"></i></div></div>\n'
        '    <div class="bx"><div class="bl" style="color:var(--terra)">↳ Over-analysis <span style="color:var(--terra)">watch</span></div><div class="bt"><i style="width:55%;background:linear-gradient(90deg,#E7B48F,var(--terra))"></i></div></div>\n'
        '    <div class="bx"><div class="bl">Ownership <span>strength</span></div><div class="bt"><i style="width:86%"></i></div></div>\n'
        '    <div class="bx"><div class="bl" style="color:var(--terra)">↳ Won\'t delegate <span style="color:var(--terra)">watch</span></div><div class="bt"><i style="width:62%;background:linear-gradient(90deg,#E7B48F,var(--terra))"></i></div></div>')

    leg1 = f'<b>Strength bars.</b> {l1} and {l2} run high — your core assets.'
    leg2 = f'<b>Shadow bars.</b> Unmanaged, the same two strengths tip into {s1.lower()} and {s2.lower()}.'
    take = f'Don\'t blunt {l1} or {l2} — manage the shadow each one casts. That is the lever.'

    return [
        (old_bars, new_bars),
        ('<div class="lr"><span class="dot" style="background:#B9862E"></span><span class="lt"><b>Strength bars.</b> Strategic thinking and ownership run high — your core assets.</span></div>',
         f'<div class="lr"><span class="dot" style="background:#B9862E"></span><span class="lt">{leg1}</span></div>'),
        ('<div class="lr"><span class="dot" style="background:#C9A34E"></span><span class="lt"><b>Shadow bars.</b> Unmanaged, the same traits tip into over-analysis and holding on.</span></div>',
         f'<div class="lr"><span class="dot" style="background:#C9A34E"></span><span class="lt">{leg2}</span></div>'),
        ('<div class="take"><b>The read</b>Don\'t blunt the strengths — manage their shadow. The lever is delegation and faster small calls.</div>',
         f'<div class="take"><b>The read</b>{take}</div>'),
    ]


BUILDERS = [
    _page16_recurring_themes,
    _page17_motivates,
    _page18_drivers_donut,
    _page19_blind_spots,
    _page20_shadow_table,
    _page21_shadow_bars,
]
