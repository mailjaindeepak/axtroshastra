"""
Report add-on sections for the Axtroshastra marriage report.
Pure render helpers — each returns an HTML string built only from the payload,
so report_view.py just drops the calls into its existing f-string.

Sections:
  d9_section_html(p)        Navamsa (D9) chart + vargottama + marriage-promise strength
  occupants_html(p)         planets sitting in the 7th house (was computed, never shown)
  planet_table_html(p)      full verifiable planet placement table (brand: any astrologer can check)
  scoring_box_html(p)       the exact rule table + points behind the top window (transparency)

English base text (v2). Deterministic — same chart, same output. No LLM. The Hindi
report is produced by translating these labels via the shaadi_hi localizer.
"""

SIGNS = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
         "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena"]
SIGN_NUM = {s: i for i, s in enumerate(SIGNS)}

PLANET_ABBR = {"Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me",
               "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa",
               "Rahu": "Ra", "Ketu": "Ke"}

HOUSE_POS = {1: (200, 105), 2: (105, 58), 3: (55, 105), 4: (105, 200),
             5: (55, 295), 6: (105, 345), 7: (200, 295), 8: (295, 345),
             9: (345, 295), 10: (295, 200), 11: (345, 105), 12: (295, 58)}

# ---- planet-in-7th meanings (classical, bounded, marriage lens) ----
PLANET_IN_7TH = {
    "Sun": "a self-respecting, strong-willed partner — individuality is central to the bond; giving each other's ego room pays off",
    "Moon": "an emotionally attuned, caring partner — home and warmth sit at the centre; tuning into each other's moods is a shared job",
    "Mars": "an energetic, passionate bond — sometimes fiery too (see the Manglik check above); resolving conflict quickly makes it stronger",
    "Mercury": "a youthful, communicative partner — conversation is your real glue; often a younger-feeling partner or a small age gap",
    "Jupiter": "a wise, principled, often traditional-values partner — classical texts consider Jupiter in the 7th auspicious; a family-approved match",
    "Venus": "an affectionate, harmony-loving partner — romance and comfort come easily; the marriage karaka in its own domain, a good placement",
    "Saturn": "a mature, committed, possibly older or serious-minded partner — the bond builds slowly but lasts; early patience is rewarded later",
    "Rahu": "an unconventional attraction — the partner may come from a different background, community or country; the start can be sudden or intense",
    "Ketu": "a deep but slightly detached bond — the partner may be spiritually inclined; connect from the heart rather than over-analysing",
}

# ---- scoring rule table (mirrors engine.RULES so no engine edit is needed) ----
RULE_PTS = {
    "AD_IS_7L": 3.0, "MD_IS_7L": 2.0, "AD_IS_KARAKA": 2.0, "AD_IN_7TH": 2.0,
    "AD_WITH_7L": 2.0, "AD_IS_DK": 1.5, "AD_NODE_7AX": 1.5, "MD_7CONNECT": 1.0,
    "AD_WEAK": -1.5, "AD_DRY": -1.0,
    "TR_JUP_TRIG": 2.0, "TR_JUP_ON_7L": 1.0, "TR_SAT_HEAVY": -1.0,
}
RULE_DESC = {
    "AD_IS_7L": "Antardasha lord is the 7th lord",
    "MD_IS_7L": "Mahadasha lord is the 7th lord",
    "AD_IS_KARAKA": "AD lord is Venus/Jupiter (marriage karaka)",
    "AD_IN_7TH": "AD lord occupies or aspects the 7th house",
    "AD_WITH_7L": "AD lord conjunct the 7th lord",
    "AD_IS_DK": "AD lord is the darakaraka",
    "AD_NODE_7AX": "Node on 7th axis and AD lord is that node",
    "MD_7CONNECT": "MD lord has a 7th-house connection",
    "AD_WEAK": "AD lord debilitated or combust",
    "AD_DRY": "AD is Saturn/Ketu with no 7th connection",
    "TR_JUP_TRIG": "Jupiter transits 7/1/2/11 in the window",
    "TR_JUP_ON_7L": "Jupiter transits over your natal 7th lord",
    "TR_SAT_HEAVY": "Saturn sits on the 7th axis for most of the window",
}

_GOLD = "#E4B04A"


def _houses_from(ref: int, target: int) -> int:
    return ((target - ref) % 12) + 1


# ============================================================ Navamsa (D9)
def _d9_chart_svg(nav: dict) -> str:
    lagna = nav["d9_lagna_idx"]
    by_house = {h: [] for h in range(1, 13)}
    for pname, pd in nav["planets"].items():
        h = _houses_from(lagna, pd["sign_idx"])
        tag = PLANET_ABBR[pname] + ("*" if pd["vargottama"] else "")
        by_house[h].append(tag)
    cells = []
    for h, (cx, cy) in HOUSE_POS.items():
        sign_num = ((lagna + h - 1) % 12) + 1
        cells.append(f"<text x='{cx}' y='{cy-16}' class='sn9'>{sign_num}</text>")
        if by_house[h]:
            cells.append(f"<text x='{cx}' y='{cy+6}' class='pl9'>{' '.join(by_house[h][:4])}</text>")
            if len(by_house[h]) > 4:
                cells.append(f"<text x='{cx}' y='{cy+24}' class='pl9'>{' '.join(by_house[h][4:])}</text>")
    return f"""<svg viewBox="0 0 400 400" class="kchart" role="img" aria-label="Navamsa D9 chart">
<rect x="8" y="8" width="384" height="384" fill="none" stroke="{_GOLD}" stroke-width="2"/>
<path d="M8 8 L392 392 M392 8 L8 392" stroke="{_GOLD}" stroke-width="1.5" fill="none"/>
<path d="M200 8 L392 200 L200 392 L8 200 Z" stroke="{_GOLD}" stroke-width="2" fill="none"/>
<style>.sn9{{font:600 13px sans-serif;fill:#A8977F;text-anchor:middle}}
.pl9{{font:800 15px sans-serif;fill:#F3EFE4;text-anchor:middle}}</style>
{''.join(cells)}</svg>"""


def d9_section_html(p: dict) -> str:
    nav = p.get("navamsa")
    if not nav:
        return ""
    vgt = nav["vargottama_planets"]
    vgt_line = ("Vargottama (same sign in D1 and D9 — extra strong): <b>"
                + ", ".join(vgt) + "</b>."
                if vgt else "No planet is vargottama in this chart — that's normal; "
                            "most charts have 0–2.")
    band_color = {"strong": "#2E7D53", "steady": _GOLD, "tender": "#C93B2E"}[nav["strength"]]
    reasons = "".join(f"<li>{r}</li>" for r in nav["reasons"])
    return f"""
<section class="pg"><p class="plabel">Navamsa · D9</p>
<h2>The Navamsa (D9) — marriage's truest mirror</h2>
<p>The Rashi chart (D1) shows <b>when</b>; the Navamsa (D9) shows <b>how solid</b> and
<b>how it will feel</b>. That is why, in classical Jyotish, D9 is the single most important
divisional chart for marriage. Your D9 Lagna is <b>{nav['d9_lagna']}</b>.</p>
<div class="tl" style="padding:14px"><div style="text-align:center">{_d9_chart_svg(nav)}</div>
<p style="color:#A8977F;font-size:12.5px;text-align:center;margin-top:6px">
D9 chart · <b style="color:{_GOLD}">*</b> = vargottama · sign numbers inside the houses</p></div>
<div class="facts" style="margin-top:6px">
<div class="row"><span class="k">D9 Lagna</span><span class="v">{nav['d9_lagna']}</span></div>
<div class="row"><span class="k">D9 7th house</span><span class="v">{nav['d9_seventh_sign']}</span></div>
<div class="row"><span class="k">D9 7th lord</span><span class="v">{nav['d9_seventh_lord']} — {nav['d9_seventh_lord_dignity']}</span></div>
<div class="row"><span class="k">Venus in D9</span><span class="v">{nav['venus_d9_sign']}{' (vargottama)' if nav['venus_vargottama'] else ''}</span></div>
</div>
<p style="margin-top:12px">{vgt_line}</p>
<div class="mgcard" style="background:#F6E7C6;margin-top:14px">
<b class="h" style="color:{band_color}">Navamsa marriage-promise: {nav['strength'].upper()}</b>
<p>{nav['strength_note']}</p>
<ul class="wwhy" style="margin-top:10px">{reasons}</ul></div>
<p class="soft">D9 speaks to the promise, not the timing — the windows above give the timing.
Together, they form the full picture.</p></section>"""


# ============================================================ 7th-house occupants
def occupants_html(p: dict) -> str:
    occ = p.get("significators", {}).get("seventh_occupants") or []
    if not occ:
        return ("<p style='margin-top:14px'><b>Your 7th house is empty</b> — no planet sits in it. "
                "This is normal and often considered favourable: the partner pattern is read from the "
                "<i>lord</i> of the 7th and the karaka (given above), not from a planet sitting there.</p>")
    rows = "".join(
        f"<div class='act'><b>{x} in the 7th house</b><p>{PLANET_IN_7TH.get(x, '')}</p></div>"
        for x in occ)
    return f"""<p style="margin-top:14px"><b>Planets in your 7th house:</b>
{', '.join(occ)} — these shape the colour of the partnership most directly:</p>
{rows}"""


# ============================================================ full planet table
def planet_table_html(p: dict) -> str:
    lagna_idx = SIGN_NUM.get(p["chart"]["lagna"], 0)
    rows = ""
    order = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    planets = p["chart"]["planets"]
    for name in order:
        d = planets.get(name)
        if not d:
            continue
        house = _houses_from(lagna_idx, SIGN_NUM.get(d["sign"], 0))
        state = []
        if d.get("dignity") and d["dignity"] != "neutral":
            state.append(d["dignity"])
        if d.get("retro"):
            state.append("retro")
        if d.get("combust"):
            state.append("combust")
        state_txt = ", ".join(state) if state else "—"
        rows += (f"<tr><td style='font-weight:700'>{name}</td>"
                 f"<td>{d['sign']}</td><td>{d['nakshatra']}</td>"
                 f"<td style='text-align:center'>{house}</td>"
                 f"<td style='color:#6B6D82'>{state_txt}</td></tr>")
    return f"""
<section class="pg"><p class="plabel">Full chart</p>
<h2>Your full chart — verify it yourself</h2>
<p>We hide nothing. Below are the exact positions of all nine planets — any astrologer can
check them against their own panchang. That transparency is the point.</p>
<table style="width:100%;border-collapse:collapse;margin-top:12px;font-size:14.5px;background:#fff;
border:1.5px solid #E7E0D2;border-radius:12px;overflow:hidden">
<thead><tr style="background:#4A3A2A;color:#F3EFE4;font-family:'Bricolage Grotesque',sans-serif">
<th style="text-align:left;padding:9px 10px">Planet</th><th style="text-align:left;padding:9px 10px">Sign</th>
<th style="text-align:left;padding:9px 10px">Nakshatra</th><th style="padding:9px 10px">House</th>
<th style="text-align:left;padding:9px 10px">State</th></tr></thead>
<tbody>{rows}</tbody></table>
<p class="soft">House counted from the Lagna · Lahiri ayanamsa · whole-sign houses.</p></section>"""


# ============================================================ scoring transparency
def scoring_box_html(p: dict) -> str:
    ws = p.get("windows") or []
    if not ws:
        return ""
    w = ws[0]
    fired = [r["id"] for r in w.get("rules_fired", [])]
    pos, neg = [], []
    for rid in fired:
        pts = RULE_PTS.get(rid)
        if pts is None:
            continue
        (pos if pts > 0 else neg).append((rid, pts))
    def row(rid, pts):
        col = "#2E7D53" if pts > 0 else "#C93B2E"
        sign = "+" if pts > 0 else ""
        return (f"<tr><td style='padding:7px 10px'>{RULE_DESC.get(rid, rid)}</td>"
                f"<td style='padding:7px 10px;text-align:right;font-weight:800;color:{col}'>{sign}{pts:g}</td></tr>")
    body = "".join(row(r, pt) for r, pt in pos) + "".join(row(r, pt) for r, pt in neg)
    dasha = (w.get('dasha', '') or '').replace(' MD ', ' Mahadasha ').replace(' AD', ' Antardasha')
    return f"""
<section class="pg"><p class="plabel">Under the hood</p>
<h2>Your top window's scorecard</h2>
<p>We gave this window ({dasha}) <b>{w.get('score', 0):g} points</b>, which is why it
graded <b>{w['grade']}</b>. Every point traces back to a classical rule — here's the exact breakdown:</p>
<table style="width:100%;border-collapse:collapse;margin-top:12px;font-size:15.5px;background:#fff;
border:1.5px solid #E7E0D2;border-radius:12px;overflow:hidden">
<tbody>{body}
<tr style="background:#F6E7C6"><td style="padding:9px 10px;font-weight:800">Total</td>
<td style="padding:9px 10px;text-align:right;font-weight:800">{w.get('score', 0):g}</td></tr></tbody></table>
<p class="soft">Grade bands: Strong ≥ 8 · Moderate ≥ 5 · Building ≥ 3. Any astrologer can verify
these rules by hand — because this is calculation, not opinion.</p></section>"""
