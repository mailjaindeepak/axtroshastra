"""
Report add-on sections for the Axtroshastra marriage report.
Pure render helpers — each returns an HTML string built only from the payload.

Sections:
  d9_section_html(p, lang)   Navamsa (D9) chart + vargottama + marriage-promise strength
  occupants_html(p, lang)    planets sitting in the 7th house
  planet_table_html(p, lang) full verifiable planet placement table
  scoring_box_html(p, lang)  the exact rule table + points behind the top window

Language-aware (v2): lang="en" (default) emits English; lang="hi" emits Devanagari
for the prose/labels here, while data tokens (signs, dignities, months) are left for
the shaadi_hi localizer's TOK/GRADE/DIGNITY maps to finish. Deterministic — no LLM.
"""

import re

SIGNS = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
         "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena"]
SIGN_NUM = {s: i for i, s in enumerate(SIGNS)}

PLANET_HI = {"Sun": "सूर्य", "Moon": "चंद्र", "Mars": "मंगल", "Mercury": "बुध",
             "Jupiter": "गुरु", "Venus": "शुक्र", "Saturn": "शनि", "Rahu": "राहु", "Ketu": "केतु"}


def _dasha_disp(dasha: str, lang: str) -> str:
    """MD/AD -> full words, and (for hi) planet names + period words to Devanagari,
    so the dasha reads cleanly when embedded inside a Hindi sentence."""
    dasha = (dasha or "").replace(" MD ", " Mahadasha ").replace(" AD", " Antardasha")
    if lang == "hi":
        for en, hin in PLANET_HI.items():
            dasha = re.sub(r"\b" + en + r"\b", hin, dasha)
        dasha = dasha.replace("Mahadasha", "महादशा").replace("Antardasha", "अंतर्दशा")
    return dasha

PLANET_ABBR = {"Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me",
               "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa",
               "Rahu": "Ra", "Ketu": "Ke"}

HOUSE_POS = {1: (200, 105), 2: (105, 58), 3: (55, 105), 4: (105, 200),
             5: (55, 295), 6: (105, 345), 7: (200, 295), 8: (295, 345),
             9: (345, 295), 10: (295, 200), 11: (345, 105), 12: (295, 58)}


def _t(en: str, hi: str, lang: str) -> str:
    return hi if lang == "hi" else en


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
PLANET_IN_7TH_HI = {
    "Sun": "स्वाभिमानी, दृढ़-इच्छाशक्ति वाला साथी — व्यक्तित्व बंधन का केंद्र है; एक-दूसरे के अहं को जगह देना फ़ायदेमंद",
    "Moon": "भावनात्मक रूप से जुड़ा, ख़याल रखने वाला साथी — घर और गर्माहट केंद्र में; मूड को समझना साझा ज़िम्मेदारी",
    "Mars": "ऊर्जावान, जोशीला बंधन — कभी तेज़-मिज़ाज भी (ऊपर मांगलिक जाँच देखें); झगड़े जल्दी सुलझाना इसे मज़बूत करता है",
    "Mercury": "युवा-मन, बातूनी साथी — बातचीत ही असली जोड़ है; अक्सर साथी उम्र में कमतर या कम आयु-अंतर",
    "Jupiter": "समझदार, उसूलों वाला, अक्सर पारंपरिक-मूल्यों वाला साथी — शास्त्र 7वें में गुरु को शुभ मानते हैं; परिवार-स्वीकृत मेल",
    "Venus": "स्नेही, सामंजस्य-प्रेमी साथी — रोमांस और सुकून सहज; विवाह कारक अपने ही क्षेत्र में, अच्छी स्थिति",
    "Saturn": "परिपक्व, प्रतिबद्ध, शायद उम्र में बड़ा या गंभीर साथी — बंधन धीरे बनता पर टिकाऊ; शुरुआती धीरज बाद में फल देता है",
    "Rahu": "अपरंपरागत आकर्षण — साथी अलग पृष्ठभूमि, समुदाय या देश से हो सकता है; शुरुआत अचानक या तीव्र",
    "Ketu": "गहरा पर थोड़ा अलिप्त बंधन — साथी आध्यात्मिक झुकाव वाला हो सकता है; ज़्यादा विश्लेषण से नहीं, दिल से जुड़ें",
}

# ---- scoring rule table (mirrors engine.RULES) ----
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
RULE_DESC_HI = {
    "AD_IS_7L": "अंतर्दशा स्वामी ही 7वें भाव का स्वामी है",
    "MD_IS_7L": "महादशा स्वामी ही 7वें भाव का स्वामी है",
    "AD_IS_KARAKA": "अंतर्दशा स्वामी शुक्र/गुरु है (विवाह कारक)",
    "AD_IN_7TH": "अंतर्दशा स्वामी 7वें भाव में है या उस पर दृष्टि है",
    "AD_WITH_7L": "अंतर्दशा स्वामी 7वें भाव के स्वामी के साथ है",
    "AD_IS_DK": "अंतर्दशा स्वामी दारकारक है",
    "AD_NODE_7AX": "राहु/केतु 7वें अक्ष पर और अंतर्दशा स्वामी वही नोड है",
    "MD_7CONNECT": "महादशा स्वामी का 7वें भाव से संबंध है",
    "AD_WEAK": "अंतर्दशा स्वामी नीच या अस्त है",
    "AD_DRY": "अंतर्दशा शनि/केतु की है, 7वें भाव से कोई संबंध नहीं",
    "TR_JUP_TRIG": "गुरु का विंडो में 7/1/2/11 पर गोचर",
    "TR_JUP_ON_7L": "गुरु का आपके जन्म-कुंडली के 7वें स्वामी पर गोचर",
    "TR_SAT_HEAVY": "शनि विंडो के अधिकांश समय 7वें अक्ष पर बैठा है",
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


def d9_section_html(p: dict, lang: str = "en") -> str:
    nav = p.get("navamsa")
    if not nav:
        return ""
    vgt = nav["vargottama_planets"]
    if vgt:
        vgt_line = (_t("Vargottama (same sign in D1 and D9 — extra strong): <b>",
                       "वर्गोत्तम (D1 और D9 में एक ही राशि — अतिरिक्त मज़बूत): <b>", lang)
                    + ", ".join(vgt) + "</b>.")
    else:
        vgt_line = _t("No planet is vargottama in this chart — that's normal; most charts have 0–2.",
                      "इस कुंडली में कोई ग्रह वर्गोत्तम नहीं — यह सामान्य है; ज़्यादातर कुंडलियों में 0–2 होते हैं।", lang)
    band_color = {"strong": "#2E7D53", "steady": _GOLD, "tender": "#C93B2E"}[nav["strength"]]
    reasons = "".join(f"<li>{r}</li>" for r in nav["reasons"])
    h2 = _t("The Navamsa (D9) — marriage's truest mirror",
            "नवमांश (D9) — विवाह का सच्चा दर्पण", lang)
    intro = _t(
        "The Rashi chart (D1) shows <b>when</b>; the Navamsa (D9) shows <b>how solid</b> and "
        "<b>how it will feel</b>. That is why, in classical Jyotish, D9 is the single most important "
        f"divisional chart for marriage. Your D9 Lagna is <b>{nav['d9_lagna']}</b>.",
        "राशि कुंडली (D1) बताती है <b>कब</b>; नवमांश (D9) बताता है <b>कितना पक्का</b> और "
        "<b>कैसा निभेगा</b>। इसीलिए शास्त्रीय ज्योतिष में विवाह के लिए D9 सबसे अहम विभाजन-कुंडली है। "
        f"आपका D9 लग्न <b>{nav['d9_lagna']}</b> है।", lang)
    caption = _t("D9 chart · <b style=\"color:%s\">*</b> = vargottama · sign numbers inside the houses" % _GOLD,
                 "D9 चार्ट · <b style=\"color:%s\">*</b> = वर्गोत्तम · भावों के अंदर राशि-संख्याएँ" % _GOLD, lang)
    band = _t(f"Navamsa marriage-promise: {nav['strength'].upper()}",
              f"नवमांश विवाह-वादा: {nav['strength'].upper()}", lang)
    soft = _t("D9 speaks to the promise, not the timing — the windows above give the timing. Together, they form the full picture.",
              "D9 वादे की बात करता है, समय की नहीं — समय ऊपर की विंडोज़ बताती हैं। दोनों मिलकर पूरी तस्वीर बनाते हैं।", lang)
    r_lagna = _t("D9 Lagna", "D9 लग्न", lang)
    r_seventh = _t("D9 7th house", "D9 7वाँ भाव", lang)
    r_lord = _t("D9 7th lord", "D9 7वें भाव का स्वामी", lang)
    r_venus = _t("Venus in D9", "D9 में शुक्र", lang)
    vgt_tag = _t(" (vargottama)", " (वर्गोत्तम)", lang) if nav['venus_vargottama'] else ""
    return f"""
<section class="pg"><p class="plabel">Navamsa · D9</p>
<h2>{h2}</h2>
<p>{intro}</p>
<div class="tl" style="padding:14px"><div style="text-align:center">{_d9_chart_svg(nav)}</div>
<p style="color:#A8977F;font-size:11.5px;text-align:center;margin-top:6px">{caption}</p></div>
<div class="facts" style="margin-top:6px">
<div class="row"><span class="k">{r_lagna}</span><span class="v">{nav['d9_lagna']}</span></div>
<div class="row"><span class="k">{r_seventh}</span><span class="v">{nav['d9_seventh_sign']}</span></div>
<div class="row"><span class="k">{r_lord}</span><span class="v">{nav['d9_seventh_lord']} — {nav['d9_seventh_lord_dignity']}</span></div>
<div class="row"><span class="k">{r_venus}</span><span class="v">{nav['venus_d9_sign']}{vgt_tag}</span></div>
</div>
<p style="margin-top:12px">{vgt_line}</p>
<div class="mgcard" style="background:#F1E4C8;margin-top:14px">
<b class="h" style="color:{band_color}">{band}</b>
<p>{nav['strength_note']}</p>
<ul class="wwhy" style="margin-top:10px">{reasons}</ul></div>
<p class="soft">{soft}</p></section>"""


# ============================================================ 7th-house occupants
def occupants_html(p: dict, lang: str = "en") -> str:
    occ = p.get("significators", {}).get("seventh_occupants") or []
    meanings = PLANET_IN_7TH_HI if lang == "hi" else PLANET_IN_7TH
    if not occ:
        return "<p style='margin-top:14px'>" + _t(
            "<b>Your 7th house is empty</b> — no planet sits in it. This is normal and often "
            "considered favourable: the partner pattern is read from the <i>lord</i> of the 7th and "
            "the karaka (given above), not from a planet sitting there.",
            "<b>आपका 7वाँ भाव ख़ाली है</b> — इसमें कोई ग्रह नहीं बैठा। यह सामान्य और अक्सर शुभ माना जाता है: "
            "साथी का स्वरूप 7वें भाव के <i>स्वामी</i> और कारक (ऊपर दिया) से पढ़ा जाता है, किसी बैठे ग्रह से नहीं।",
            lang) + "</p>"
    rows = "".join(
        f"<div class='act'><b>{x}{_t(' in the 7th house', ' 7वें भाव में', lang)}</b><p>{meanings.get(x, '')}</p></div>"
        for x in occ)
    header = _t("<b>Planets in your 7th house:</b> %s — these shape the colour of the partnership most directly:" % ', '.join(occ),
                "<b>आपके 7वें भाव में ग्रह:</b> %s — ये साझेदारी के रंग को सबसे सीधे आकार देते हैं:" % ', '.join(occ), lang)
    return f"<p style=\"margin-top:14px\">{header}</p>\n{rows}"


# ============================================================ full planet table
def planet_table_html(p: dict, lang: str = "en") -> str:
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
    plabel = _t("Full chart", "पूरी कुंडली", lang)
    h2 = _t("Your full chart — verify it yourself", "आपकी पूरी कुंडली — ख़ुद जाँचें", lang)
    intro = _t("We hide nothing. Below are the exact positions of all nine planets — any astrologer can "
               "check them against their own panchang. That transparency is the point.",
               "हम कुछ नहीं छिपाते। नीचे सभी नौ ग्रहों की सटीक स्थितियाँ हैं — कोई भी ज्योतिषी इन्हें अपने पंचांग "
               "से मिला सकता है। यही पारदर्शिता असल बात है।", lang)
    th0 = _t("Planet", "ग्रह", lang); th1 = _t("Sign", "राशि", lang); th2 = _t("Nakshatra", "नक्षत्र", lang)
    th3 = _t("House", "भाव", lang); th4 = _t("State", "स्थिति", lang)
    soft = _t("House counted from the Lagna · Lahiri ayanamsa · whole-sign houses.",
              "भाव लग्न से गिना गया · लाहिरी अयनांश · पूर्ण-राशि भाव।", lang)
    return f"""
<section class="pg"><p class="plabel">{plabel}</p>
<h2>{h2}</h2>
<p>{intro}</p>
<table style="width:100%;border-collapse:collapse;margin-top:12px;font-size:13.5px;background:#fff;
border:1.5px solid #E7DDC9;border-radius:12px;overflow:hidden">
<thead><tr style="background:#4A3A2A;color:#F3EFE4;font-family:'Bricolage Grotesque',sans-serif">
<th style="text-align:left;padding:9px 10px">{th0}</th><th style="text-align:left;padding:9px 10px">{th1}</th>
<th style="text-align:left;padding:9px 10px">{th2}</th><th style="padding:9px 10px">{th3}</th>
<th style="text-align:left;padding:9px 10px">{th4}</th></tr></thead>
<tbody>{rows}</tbody></table>
<p class="soft">{soft}</p></section>"""


# ============================================================ scoring transparency
def scoring_box_html(p: dict, lang: str = "en") -> str:
    ws = p.get("windows") or []
    if not ws:
        return ""
    desc = RULE_DESC_HI if lang == "hi" else RULE_DESC
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
        return (f"<tr><td style='padding:7px 10px'>{desc.get(rid, rid)}</td>"
                f"<td style='padding:7px 10px;text-align:right;font-weight:800;color:{col}'>{sign}{pts:g}</td></tr>")
    body = "".join(row(r, pt) for r, pt in pos) + "".join(row(r, pt) for r, pt in neg)
    dasha = _dasha_disp(w.get('dasha', ''), lang)
    plabel = _t("Under the hood", "पर्दे के पीछे", lang)
    h2 = _t("Your top window's scorecard", "आपकी टॉप विंडो का स्कोरकार्ड", lang)
    intro = _t(f"We gave this window ({dasha}) <b>{w.get('score', 0):g} points</b>, which is why it "
               f"graded <b>{w['grade']}</b>. Every point traces back to a classical rule — here's the exact breakdown:",
               f"हमने इस विंडो ({dasha}) को <b>{w.get('score', 0):g} अंक</b> दिए, इसीलिए इसे "
               f"<b>{w['grade']}</b> ग्रेड मिला। हर अंक के पीछे एक शास्त्रीय नियम है — नीचे सटीक ब्योरा:", lang)
    total = _t("Total", "कुल", lang)
    soft = _t("Grade bands: Strong ≥ 8 · Moderate ≥ 5 · Building ≥ 3. Any astrologer can verify "
              "these rules by hand — because this is calculation, not opinion.",
              "ग्रेड बैंड: Strong ≥ 8 · Moderate ≥ 5 · Building ≥ 3। कोई भी ज्योतिषी इन नियमों को हाथ से "
              "जाँच सकता है — क्योंकि यह राय नहीं, गणना है।", lang)
    return f"""
<section class="pg"><p class="plabel">{plabel}</p>
<h2>{h2}</h2>
<p>{intro}</p>
<table style="width:100%;border-collapse:collapse;margin-top:12px;font-size:14px;background:#fff;
border:1.5px solid #E7DDC9;border-radius:12px;overflow:hidden">
<tbody>{body}
<tr style="background:#F1E4C8"><td style="padding:9px 10px;font-weight:800">{total}</td>
<td style="padding:9px 10px;text-align:right;font-weight:800">{w.get('score', 0):g}</td></tr></tbody></table>
<p class="soft">{soft}</p></section>"""
