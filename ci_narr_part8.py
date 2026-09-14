"""Career Intelligence — narrative personalization, Part 8.

The two new verdict pages inserted after the cover:
  V1 — "Your 9 career questions, answered" (verdict dashboard)
  V2 — "Your career timeline" (timeline exhibit)

Same contract as all other ci_narr_part* modules: each builder returns
(old, new) exact-replacement pairs; `new` keeps the same HTML structure,
only human-readable prose changes. Every claim traces to computed data.
Independent module — no import from ci_narrative.
"""


def _v(p):
    """Extract verdicts dict from payload, with safe fallback."""
    return p.get("verdicts") or {}


# -------------------------------------------------------- V1: verdict dashboard

_VD_OUTLOOK_OLD = 'YES — Stronger career growth lies ahead.'
_VD_STAYSWITCH_OLD = ('Prepare — your chart favours preparing before '
                      'making the bigger move.')
_VD_WINDOW_OLD = ('Year 3 — the strongest career-movement opening '
                  'falls in Year 3 of the next three.')
_VD_PROMOTION_OLD = ('Visibility rising — growth is more likely through '
                     'promotion into a named authority role.')
_VD_INCOME_OLD = ('Steady compounding — your chart indicates a '
                  'compounding financial trajectory.')
_VD_BUSINESS_OLD = ('Career-leaning — your chart leans toward senior '
                    'career and advisory work.')
_VD_3YEAR_OLD = ('Position &rarr; Build momentum &rarr; The window.')
_VD_ROLE_OLD = ('Roles built around authority and decision-making '
                'responsibility.')
_VD_12MONTH_OLD = ('Invest in deepening expertise. Avoid forcing a '
                   'career move before Year 3.')


def _verdict_dashboard(p, dd):
    v = _v(p)
    pairs = []

    outlook = v.get("outlook") or {}
    if outlook.get("verdict"):
        new = outlook["verdict"]
        if new != _VD_OUTLOOK_OLD:
            pairs.append((_VD_OUTLOOK_OLD, new))

    ss = v.get("stay_switch") or {}
    if ss.get("verdict"):
        new = f'{ss["verdict"]} — {ss.get("tag", "")}'.rstrip(' — ')
        if new != _VD_STAYSWITCH_OLD:
            pairs.append((_VD_STAYSWITCH_OLD, new))

    win = v.get("window") or {}
    peak = win.get("year")
    if win.get("has_window") and peak:
        new = (f'Year {peak} — the strongest career-movement opening '
               f'falls in Year {peak} of the next three.')
    elif win.get("has_window") is False:
        new = win.get("signal", "No strong job-change window in the next three years.")
    else:
        new = None
    if new and new != _VD_WINDOW_OLD:
        pairs.append((_VD_WINDOW_OLD, new))

    promo = v.get("promotion") or {}
    if promo.get("visibility"):
        vis_label = "Visibility rising" if promo["visibility"] == "rising" else "Visibility emerging"
        route = promo.get("route", "promotion")
        if route == "promotion":
            route_txt = "promotion into a named authority role"
        elif route == "bigger mandate":
            route_txt = "a larger responsibility or mandate"
        else:
            route_txt = "a role change or external move"
        new = f'{vis_label} — growth is more likely through {route_txt}.'
        if new != _VD_PROMOTION_OLD:
            pairs.append((_VD_PROMOTION_OLD, new))

    inc = v.get("income") or {}
    if inc.get("shape"):
        shape_label = {"steady-compound": "Steady compounding",
                       "step-up": "Step-up growth",
                       "gradual": "Gradual trajectory"}.get(inc["shape"], "Steady compounding")
        shape_detail = {"steady-compound": "your chart indicates a compounding financial trajectory",
                        "step-up": "your chart indicates income growth in steps — periods of plateau, then a step up",
                        "gradual": "your chart indicates a gradual but dependable earning trajectory"
                        }.get(inc["shape"], "")
        new = f'{shape_label} — {shape_detail}.'
        if new != _VD_INCOME_OLD:
            pairs.append((_VD_INCOME_OLD, new))

    biz = v.get("business") or {}
    if biz.get("verdict"):
        biz_label = biz["verdict"]
        biz_detail = {"Career-leaning": "your chart leans toward senior career and advisory work",
                      "Business-leaning": "your chart leans toward building through ownership and enterprise",
                      "Balanced": "both career and enterprise paths show potential"
                      }.get(biz_label, "")
        new = f'{biz_label} — {biz_detail}.'
        if new != _VD_BUSINESS_OLD:
            pairs.append((_VD_BUSINESS_OLD, new))

    ty = v.get("three_year") or {}
    yp = ty.get("year_phases")
    if yp and len(yp) == 3:
        new = f'{yp[0]} &rarr; {yp[1]} &rarr; {yp[2]}.'
        if new != _VD_3YEAR_OLD:
            pairs.append((_VD_3YEAR_OLD, new))

    role = v.get("role") or {}
    if role.get("signal"):
        new = role["signal"]
        if new != _VD_ROLE_OLD:
            pairs.append((_VD_ROLE_OLD, new))

    tm = v.get("twelve_month") or {}
    if tm.get("do") and tm.get("avoid"):
        new = f'{tm["do"]}. Avoid: {tm["avoid"].lower() if tm["avoid"][0].isupper() else tm["avoid"]}.'
        if '— ' in new:
            new = new.replace('— ', '— ').rstrip('.')  + '.'
        if new != _VD_12MONTH_OLD:
            pairs.append((_VD_12MONTH_OLD, new))

    return pairs


# -------------------------------------------------------- V2: career timeline

_TL_HEAD_OLD = ('Your best window for a career move is in Year 3 '
                '— position for it now.')
_TL_SUB_OLD = 'Your next three years at a glance'

_TL_Y1_PHASE_OLD = 'Positioning'
_TL_Y1_DESC_OLD = 'Sharpen focus. Build relationships. Invisible groundwork.'
_TL_Y2_PHASE_OLD = 'Building'
_TL_Y2_DESC_OLD = 'Wider scope. Doors opening. Momentum compounding.'
_TL_Y3_PHASE_OLD = 'The window'
_TL_Y3_DESC_OLD = 'The strongest opening. Make the move here.'
_TL_PEAK_OLD = 'Peak: the strongest stretch of the three years'

_TL_READ_OLD = ('Lay the groundwork through Years 1 and 2 so the '
                'larger move in Year 3 lands with full force.')

# The entire 3-year timeline block (mock = peak at Year 3)
_TL3_OLD = (
    '<div class="tl3" id="vd-timeline">\n'
    '    <div class="tly"><div class="tlyh">Year 1</div>'
    '<div class="tlyphase ph-pos">Positioning</div>'
    '<div class="tlyp">Sharpen focus. Build relationships. Invisible groundwork.</div></div>\n'
    '    <div class="tly"><div class="tlyh">Year 2</div>'
    '<div class="tlyphase ph-exp">Building</div>'
    '<div class="tlyp">Wider scope. Doors opening. Momentum compounding.</div></div>\n'
    '    <div class="tly pk"><div class="tlyh">Year 3</div>'
    '<div class="tlyphase ph-win">The window</div>'
    '<div class="tlyp">The strongest opening. Make the move here.</div>'
    '<div class="tlypeak" id="vd-peak">Peak: the strongest stretch of the three years</div></div>\n'
    '  </div>'
)


def _tl3_block(pk, descs, labels, peak_txt):
    """Build the entire timeline block with .pk on the correct year."""
    CSS_MAP = {
        1: ["ph-win", "ph-exp", "ph-pos"],
        2: ["ph-pos", "ph-win", "ph-exp"],
        3: ["ph-pos", "ph-exp", "ph-win"],
    }
    css = CSS_MAP.get(pk, CSS_MAP[3])
    rows = []
    for i in range(3):
        cls = "tly pk" if (i + 1) == pk else "tly"
        peak_div = (f'<div class="tlypeak" id="vd-peak">{peak_txt}</div>'
                    if (i + 1) == pk else '')
        rows.append(
            f'    <div class="{cls}"><div class="tlyh">Year {i+1}</div>'
            f'<div class="tlyphase {css[i]}">{labels[i]}</div>'
            f'<div class="tlyp">{descs[i]}</div>{peak_div}</div>'
        )
    return '<div class="tl3" id="vd-timeline">\n' + '\n'.join(rows) + '\n  </div>'


def _career_timeline(p, dd):
    v = _v(p)
    ty = v.get("three_year") or {}
    pk = ty.get("peak_year")
    yp = ty.get("year_phases")
    win = v.get("window") or {}
    best_window = ty.get("best_window") or win.get("best_window_range")

    if not pk or not yp or len(yp) != 3:
        return []

    pairs = []

    head = {
        1: "Your best window for a career move is right now — act on it.",
        2: "Your best window for a career move is in Year 2 — position for it now.",
        3: "Your best window for a career move is in Year 3 — position for it now.",
    }[pk]
    if head != _TL_HEAD_OLD:
        pairs.append((_TL_HEAD_OLD, head))

    PHASE_LABELS = {
        1: ["The window", "Building on the move", "Consolidating"],
        2: ["Positioning", "The window", "Consolidating"],
        3: ["Positioning", "Building", "The window"],
    }
    YEAR_DESC = {
        1: [
            "The strongest opening. Make the move now.",
            "Build on what you set in motion. Wider scope.",
            "Settle into the new ground. Consolidate the gain.",
        ],
        2: [
            "Sharpen focus. Build relationships. Invisible groundwork.",
            "The strongest opening. Make the move here.",
            "Settle into the new ground. Consolidate the gain.",
        ],
        3: [
            "Sharpen focus. Build relationships. Invisible groundwork.",
            "Wider scope. Doors opening. Momentum compounding.",
            "The strongest opening. Make the move here.",
        ],
    }

    labels = PHASE_LABELS[pk]
    descs = YEAR_DESC[pk]
    peak_txt = f'Peak: around {best_window}' if best_window else 'Peak: the strongest stretch of the three years'

    tl3_new = _tl3_block(pk, descs, labels, peak_txt)
    if tl3_new != _TL3_OLD:
        pairs.append((_TL3_OLD, tl3_new))

    # scores section — uses <b> tags so replacements are unique
    _SC_OLD = [
        ('<b>Year 1 — Groundwork</b>', 'Not visible moves. Name it, seed relationships.'),
        ('<b>Year 2 — Build momentum</b>', 'The connective year. Scope widens.'),
        ('<b>Year 3 — The window</b>', 'Strongest opening. The move belongs here.'),
    ]
    _SC_NEW = {
        1: [('<b>Year 1 — The window</b>', 'The strongest opening. Make the move now.'),
            ('<b>Year 2 — Build on the move</b>', 'The connective year. Scope widens.'),
            ('<b>Year 3 — Consolidate</b>', 'Settle into the new ground.')],
        2: [('<b>Year 1 — Groundwork</b>', 'Not visible moves. Name it, seed relationships.'),
            ('<b>Year 2 — The window</b>', 'The strongest opening. Make the move here.'),
            ('<b>Year 3 — Consolidate</b>', 'Settle into the new ground.')],
        3: _SC_OLD,
    }
    sc = _SC_NEW.get(pk, _SC_OLD)
    for i in range(3):
        if _SC_OLD[i][0] != sc[i][0]:
            pairs.append((_SC_OLD[i][0], sc[i][0]))
        if _SC_OLD[i][1] != sc[i][1]:
            pairs.append((_SC_OLD[i][1], sc[i][1]))

    read = {
        1: "The window is open now — act in Year 1, then spend Years 2 and 3 compounding it.",
        2: "Prepare in Year 1 so you can act decisively in Year 2.",
        3: "Lay the groundwork through Years 1 and 2 so the larger move in Year 3 lands with full force.",
    }[pk]
    if read != _TL_READ_OLD:
        pairs.append((_TL_READ_OLD, read))

    return pairs


BUILDERS = [
    _verdict_dashboard,
    _career_timeline,
]
