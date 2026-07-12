"""
Report add-on sections for the Axtroshastra marriage report.
Pure render helpers — each returns an HTML string built only from the payload,
so report_view.py just drops the calls into its existing f-string.

Sections:
  d9_section_html(p)        Navamsa (D9) chart + vargottama + marriage-promise strength
  occupants_html(p)         planets sitting in the 7th house (was computed, never shown)
  planet_table_html(p)      full verifiable planet placement table (brand: any astrologer can check)
  scoring_box_html(p)       the exact rule table + points behind the top window (transparency)

No LLM. Same chart, same output.
"""

SIGNS = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
         "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena"]
SIGN_NUM = {s: i for i, s in enumerate(SIGNS)}

PLANET_ABBR = {"Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me",
               "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa",
               "Rahu": "Ra", "Ketu": "Ke"}
PLANET_HI = {"Sun": "Surya", "Moon": "Chandra", "Mars": "Mangal", "Mercury": "Budh",
             "Jupiter": "Guru", "Venus": "Shukra", "Saturn": "Shani",
             "Rahu": "Rahu", "Ketu": "Ketu"}

HOUSE_POS = {1: (200, 105), 2: (105, 58), 3: (55, 105), 4: (105, 200),
             5: (55, 295), 6: (105, 345), 7: (200, 295), 8: (295, 345),
             9: (345, 295), 10: (295, 200), 11: (345, 105), 12: (295, 58)}

# ---- planet-in-7th meanings (classical, bounded, marriage lens) ----
PLANET_IN_7TH = {
    "Sun": "self-respecting, strong-willed partner — individuality rishtey mein central; ek dusre ke ego ko space dena seekhna faydemand",
    "Moon": "emotionally attuned, caring partner — ghar-parivar ka warmth bond ka kendra; mood-tuning dono ki saanjhi zimmedari",
    "Mars": "energetic, passionate bond — kabhi tez-mizaji bhi (Manglik check upar dekhiye); jhagdon ko jaldi suljhana rishtey ko majboot karta hai",
    "Mercury": "youthful, communicative partner — baat-cheet aapka asli gum hai; aksar partner young-natured ya age-gap kam",
    "Jupiter": "wise, principled, often traditional-values partner — 7th house mein Guru ko classical texts shubh maante hain; family-approved yog",
    "Venus": "affectionate, harmony-loving partner — romance aur comfort sahaj; marriage karaka apni hi jagah, isliye achha placement",
    "Saturn": "mature, committed, possibly older ya seriously-minded partner — bond dheere banta hai par tikau; shuruaati sabr baad mein rang laata hai",
    "Rahu": "unconventional attraction — partner alag background/community/desh se ho sakta hai; shuruaat sudden ya intense",
    "Ketu": "gehra par thoda detached bond — partner spiritually-inclined ho sakta hai; over-analysis se bachna, dil se judna",
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
<style>.sn9{{font:600 13px sans-serif;fill:#8F92AB;text-anchor:middle}}
.pl9{{font:800 15px sans-serif;fill:#F3EFE4;text-anchor:middle}}</style>
{''.join(cells)}</svg>"""


def d9_section_html(p: dict) -> str:
    nav = p.get("navamsa")
    if not nav:
        return ""
    vgt = nav["vargottama_planets"]
    vgt_line = ("Vargottama (D1 aur D9 mein ek hi rashi — extra strong): <b>"
                + ", ".join(PLANET_HI[x] for x in vgt) + "</b>."
                if vgt else "Is chart mein koi graha vargottama nahi — normal hai, "
                            "zyaadatar charts mein 0–2 hote hain.")
    band_color = {"strong": "#2E7D53", "steady": _GOLD, "tender": "#C93B2E"}[nav["strength"]]
    reasons = "".join(f"<li>{r}</li>" for r in nav["reasons"])
    return f"""
<section class="pg"><p class="plabel">Navamsa · D9</p>
<h2>Navamsa (D9) — shaadi ka asli sheesha</h2>
<p>Rashi chart (D1) <b>kab</b> batata hai; Navamsa (D9) <b>kitna pakka</b> aur <b>kaisa</b>
nibhega — isiliye classical Jyotish mein shaadi ke liye D9 sabse zaroori divisional chart hai.
Aapka D9 lagna <b>{nav['d9_lagna']}</b> hai.</p>
<div class="tl" style="padding:14px"><div style="text-align:center">{_d9_chart_svg(nav)}</div>
<p style="color:#8F92AB;font-size:11.5px;text-align:center;margin-top:6px">
D9 chart · <b style="color:{_GOLD}">*</b> = vargottama · sign-numbers houses ke andar</p></div>
<div class="facts" style="margin-top:6px">
<div class="row"><span class="k">D9 lagna</span><span class="v">{nav['d9_lagna']}</span></div>
<div class="row"><span class="k">D9 7th house</span><span class="v">{nav['d9_seventh_sign']}</span></div>
<div class="row"><span class="k">D9 7th lord</span><span class="v">{nav['d9_seventh_lord']} — {nav['d9_seventh_lord_dignity']}</span></div>
<div class="row"><span class="k">Venus in D9</span><span class="v">{nav['venus_d9_sign']}{' (vargottama)' if nav['venus_vargottama'] else ''}</span></div>
</div>
<p style="margin-top:12px">{vgt_line}</p>
<div class="mgcard" style="background:#F6E7C6;margin-top:14px">
<b class="h" style="color:{band_color}">Navamsa marriage-promise: {nav['strength'].upper()}</b>
<p>{nav['strength_note']}</p>
<ul class="wwhy" style="margin-top:10px">{reasons}</ul></div>
<p class="soft">D9 promise ki baat hai, timing ki nahi — timing upar ke windows batate hain.
Dono milkar poori tasveer dete hain.</p></section>"""


# ============================================================ 7th-house occupants
def occupants_html(p: dict) -> str:
    occ = p.get("significators", {}).get("seventh_occupants") or []
    if not occ:
        return ("<p style='margin-top:14px'><b>7th house khaali hai</b> — koi graha 7th mein nahi. "
                "Yeh normal aur aksar shubh maana jaata hai: partner ka pattern 7th ke "
                "<i>lord</i> aur karaka se padha jaata hai (upar diya hai), naa ki kisi baithe graha se.</p>")
    rows = "".join(
        f"<div class='act'><b>{PLANET_HI.get(x, x)} 7th house mein</b><p>{PLANET_IN_7TH.get(x, '')}</p></div>"
        for x in occ)
    return f"""<p style="margin-top:14px"><b>Aapke 7th house mein baithe graha:</b>
{', '.join(PLANET_HI.get(x, x) for x in occ)} — yeh partnership ke rang ko sabse seedha shape dete hain:</p>
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
        rows += (f"<tr><td style='font-weight:700'>{PLANET_HI.get(name, name)}</td>"
                 f"<td>{d['sign']}</td><td>{d['nakshatra']}</td>"
                 f"<td style='text-align:center'>{house}</td>"
                 f"<td style='color:#6B6D82'>{state_txt}</td></tr>")
    return f"""
<section class="pg"><p class="plabel">Full chart</p>
<h2>Aapka poora chart — verify kijiye</h2>
<p>Hum kuch chhupate nahi. Neeche aapke saare 9 grahon ki exact position hai —
koi bhi astrologer ise apni panchang se milaa sakta hai. Yahi hamari transparency hai.</p>
<table style="width:100%;border-collapse:collapse;margin-top:12px;font-size:13.5px;background:#fff;
border:1.5px solid #E7E0D2;border-radius:12px;overflow:hidden">
<thead><tr style="background:#151C39;color:#F3EFE4;font-family:'Bricolage Grotesque',sans-serif">
<th style="text-align:left;padding:9px 10px">Graha</th><th style="text-align:left;padding:9px 10px">Rashi</th>
<th style="text-align:left;padding:9px 10px">Nakshatra</th><th style="padding:9px 10px">Bhaav</th>
<th style="text-align:left;padding:9px 10px">Sthiti</th></tr></thead>
<tbody>{rows}</tbody></table>
<p class="soft">Bhaav (house) lagna se gina gaya hai · Lahiri ayanamsa · whole-sign houses.</p></section>"""


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
    return f"""
<section class="pg"><p class="plabel">Under the hood</p>
<h2>Aapke top window ka scorecard</h2>
<p>Yeh window ({w['dasha']}) ko humne <b>{w.get('score', 0):g} points</b> diye, isliye grade
<b>{w['grade']}</b> mila. Har point ke peeche ek classical rule hai — neeche exact breakdown:</p>
<table style="width:100%;border-collapse:collapse;margin-top:12px;font-size:14px;background:#fff;
border:1.5px solid #E7E0D2;border-radius:12px;overflow:hidden">
<tbody>{body}
<tr style="background:#F6E7C6"><td style="padding:9px 10px;font-weight:800">Total</td>
<td style="padding:9px 10px;text-align:right;font-weight:800">{w.get('score', 0):g}</td></tr></tbody></table>
<p class="soft">Grade bands: Strong ≥ 8 · Moderate ≥ 5 · Building ≥ 3. Koi astrologer chaahe toh
in rules ko apne haath se verify kar sakta hai — kyunki yeh judgement nahi, calculation hai.</p></section>"""
