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
_VD_STAYSWITCH_OLD = ('Prepare — your chart favours preparing before making '
                      'the bigger move.')
_VD_WINDOW_OLD = ('Around Apr – Sep 2029 — the strongest career-movement '
                  'opening in the next three years.')
_VD_PROMOTION_OLD = ('Visibility rising — growth is more likely through '
                     'promotion into a named authority role.')
_VD_INCOME_OLD = ('Steady compounding — your chart indicates a compounding '
                  'financial trajectory, peaking around ages 45–50.')
_VD_BUSINESS_OLD = ('Career-leaning — your chart leans toward senior '
                    'career and advisory work.')
_VD_3YEAR_OLD = ('2027: Position &rarr; 2028: Build momentum '
                 '&rarr; 2029: The window.')
_VD_ROLE_OLD = ('Roles built around authority and decision-making '
                'responsibility.')
_VD_12MONTH_OLD = ('Invest in leadership visibility — strengthen your '
                   'base before 2029. Avoid: forcing a career move '
                   'in a preparation phase.')


def _verdict_dashboard(p, dd):
    v = _v(p)
    pairs = []

    outlook = v.get("outlook") or {}
    if outlook.get("verdict"):
        new = outlook["verdict"]
        if new != _VD_OUTLOOK_OLD:
            pairs.append((_VD_OUTLOOK_OLD, new))

    ss = v.get("stay_switch") or {}
    if ss.get("tag"):
        new = f'{ss["verdict"]} — {ss["tag"]}'
        if new != _VD_STAYSWITCH_OLD:
            pairs.append((_VD_STAYSWITCH_OLD, new))

    win = v.get("window") or {}
    bwr = win.get("best_window_range")
    if win.get("has_window") and bwr:
        new = f'Around {bwr} — the strongest career-movement opening in the next three years.'
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
                        "step-up": "your chart indicates income growth in steps, then a significant jump",
                        "gradual": "your chart indicates a gradual but dependable earning trajectory"
                        }.get(inc["shape"], "")
        peak_band = inc.get("peak_band_label", "")
        peak_txt = f", peaking around {peak_band}" if peak_band else ""
        new = f'{shape_label} — {shape_detail}{peak_txt}.'
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
    yl = ty.get("year_labels")
    if yp and len(yp) == 3 and yl and len(yl) == 3:
        new = f'{yl[0]}: {yp[0]} &rarr; {yl[1]}: {yp[1]} &rarr; {yl[2]}: {yp[2]}.'
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
        if new != _VD_12MONTH_OLD:
            pairs.append((_VD_12MONTH_OLD, new))

    return pairs


# -------------------------------------------------------- V2: career timeline

_TL_HEAD_OLD = ('Your best window for a career move is around '
                'Apr – Sep 2029 — position for it now.')

_TL3_OLD = (
    '<div class="tl3" id="vd-timeline">\n'
    '    <div class="tly"><div class="tlyh">2027</div>'
    '<div class="tlyphase ph-pos">Positioning</div>'
    '<div class="tlyp">Sharpen focus. Build relationships. Invisible groundwork.</div></div>\n'
    '    <div class="tly"><div class="tlyh">2028</div>'
    '<div class="tlyphase ph-exp">Building</div>'
    '<div class="tlyp">Wider scope. Doors opening. Momentum compounding.</div></div>\n'
    '    <div class="tly pk"><div class="tlyh">2029</div>'
    '<div class="tlyphase ph-win">The window</div>'
    '<div class="tlyp">The strongest opening. Make the move here.</div>'
    '<div class="tlypeak" id="vd-peak">Peak: around Apr – Sep 2029</div></div>\n'
    '  </div>'
)

_SC_OLD = [
    ('<b>2027 — Groundwork</b>', 'Not visible moves. Name it, seed relationships.'),
    ('<b>2028 — Build momentum</b>', 'The connective year. Scope widens.'),
    ('<b>2029 — The window</b>', 'Strongest opening. The move belongs here.'),
]

_TL_READ_OLD = ('Lay the groundwork through 2027 and 2028 so the '
                'larger move around Apr – Sep 2029 lands with full force.')


def _tl3_block(pk, descs, labels, peak_txt, year_labels):
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
            f'    <div class="{cls}"><div class="tlyh">{year_labels[i]}</div>'
            f'<div class="tlyphase {css[i]}">{labels[i]}</div>'
            f'<div class="tlyp">{descs[i]}</div>{peak_div}</div>'
        )
    return '<div class="tl3" id="vd-timeline">\n' + '\n'.join(rows) + '\n  </div>'


def _career_timeline(p, dd):
    v = _v(p)
    ty = v.get("three_year") or {}
    pk = ty.get("peak_year")
    yp = ty.get("year_phases")
    yl = ty.get("year_labels")
    win = v.get("window") or {}
    best_window = ty.get("best_window") or win.get("best_window_range")

    if not pk or not yp or len(yp) != 3 or not yl or len(yl) != 3:
        return []

    pairs = []

    if best_window:
        head = f"Your best window for a career move is around {best_window} — {'act on it' if pk == 1 else 'position for it now'}."
    else:
        head = {
            1: "Your best window for a career move is right now — act on it.",
            2: "Your best window for a career move is in the next two years — position for it now.",
            3: "Your best window for a career move is ahead — position for it now.",
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

    tl3_new = _tl3_block(pk, descs, labels, peak_txt, yl)
    if tl3_new != _TL3_OLD:
        pairs.append((_TL3_OLD, tl3_new))

    # scores section — uses <b> tags so replacements are unique
    _SC_NEW_LABELS = {
        1: [(f'<b>{yl[0]} — The window</b>', 'The strongest opening. Make the move now.'),
            (f'<b>{yl[1]} — Build on the move</b>', 'The connective year. Scope widens.'),
            (f'<b>{yl[2]} — Consolidate</b>', 'Settle into the new ground.')],
        2: [(f'<b>{yl[0]} — Groundwork</b>', 'Not visible moves. Name it, seed relationships.'),
            (f'<b>{yl[1]} — The window</b>', 'The strongest opening. Make the move here.'),
            (f'<b>{yl[2]} — Consolidate</b>', 'Settle into the new ground.')],
        3: [(f'<b>{yl[0]} — Groundwork</b>', 'Not visible moves. Name it, seed relationships.'),
            (f'<b>{yl[1]} — Build momentum</b>', 'The connective year. Scope widens.'),
            (f'<b>{yl[2]} — The window</b>', 'Strongest opening. The move belongs here.')],
    }
    sc = _SC_NEW_LABELS.get(pk, _SC_NEW_LABELS[3])
    for i in range(3):
        if _SC_OLD[i][0] != sc[i][0]:
            pairs.append((_SC_OLD[i][0], sc[i][0]))
        if _SC_OLD[i][1] != sc[i][1]:
            pairs.append((_SC_OLD[i][1], sc[i][1]))

    peak_yr_label = yl[pk - 1]
    if pk == 1:
        read = f"The window is open now — act in {yl[0]}, then spend {yl[1]} and {yl[2]} compounding it."
    elif pk == 2:
        bw = f" around {best_window}" if best_window else ""
        read = f"Prepare in {yl[0]} so you can act decisively{bw} in {yl[1]}."
    else:
        bw = f" around {best_window}" if best_window else ""
        read = f"Lay the groundwork through {yl[0]} and {yl[1]} so the larger move{bw} in {yl[2]} lands with full force."
    if read != _TL_READ_OLD:
        pairs.append((_TL_READ_OLD, read))

    return pairs


BUILDERS = [
    _verdict_dashboard,
    _career_timeline,
]
