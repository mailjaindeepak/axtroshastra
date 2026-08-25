"""
AstroShastra product engines: Kundli Milan (Ashtakoota) + Life Blueprint.
Deterministic classical tables only. Reuses chart computation from engine.py.
"""
from datetime import datetime, timedelta
from engine import (compute_chart, nak_of, vimshottari_tree, SIGNS, SIGNS_EN,
                    NAKSHATRAS, SIGN_LORD, DASHA_SEQ, DASHA_YRS, _sade_sati)
from jyotish_maps import (NAK_PROFILE, SIGN_ELEMENT, ELEMENT_PAIR, ELEMENT_HI,
                          KOOTA_TEXT, WEALTH_2L, GAINS_11L, HEALTH_6, MD_LORD_HI,
                          HOME_4, CHILDREN_5, FOREIGN_12, FAMILY_9,
                          REMEDY_7L, REMEDY_NODE, BIZ_TEMPERAMENT, BIZ_SECTOR_10L,
                          BIZ_PARTNERSHIP_7L, BIZ_OBSTACLE, BIZ_DASHA, BENEFIC_BIZ,
                          STRONG_WINDOW_DO, STRONG_WINDOW_DONT,
                          BIZ_TEMPERAMENT_HI, BIZ_SECTOR_10L_HI, BIZ_DASHA_HI)

# Devanagari helpers for the Vyapar /hi/ teaser (mirrors milan's authored _hi
# fields — no runtime translation, no LLM). Planet names + month abbreviations
# to Devanagari; the phrase content comes from the BIZ_*_HI tables above.
_GRAHA_HI = {"Sun": "सूर्य", "Moon": "चंद्र", "Mars": "मंगल", "Mercury": "बुध",
             "Jupiter": "गुरु", "Venus": "शुक्र", "Saturn": "शनि", "Rahu": "राहु", "Ketu": "केतु"}
_MON_HI = {"Jan": "जनवरी", "Feb": "फ़रवरी", "Mar": "मार्च", "Apr": "अप्रैल", "May": "मई",
           "Jun": "जून", "Jul": "जुलाई", "Aug": "अगस्त", "Sep": "सितंबर", "Oct": "अक्टूबर",
           "Nov": "नवंबर", "Dec": "दिसंबर"}
def _date_hi(s):
    import re
    return re.sub(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b",
                  lambda m: _MON_HI[m.group(1)], str(s))

# ============================================================ ASHTAKOOTA TABLES
# Varna by moon sign (0=Shudra..3=Brahmin for hierarchy compare)
VARNA = {3:3, 7:3, 11:3,  0:2, 4:2, 8:2,  1:1, 5:1, 9:1,  2:0, 6:0, 10:0}
VARNA_NAME = {3:"Brahmin", 2:"Kshatriya", 1:"Vaishya", 0:"Shudra"}

# Vashya group by moon sign: Q quadruped, M human, J water, V wild, K insect
# Vashya class per sign. Capricorn (9) is classically split (Chatushpada first
# half / Jalachar second); AstroSage — the reference our users compare against —
# treats it as Chatushpada, so we map it to "Q" to match (verified against the
# AstroSage MatchMaking reports in tests/test_milan_accuracy.py).
VASHYA = {0:"Q",1:"Q",2:"M",3:"J",4:"V",5:"M",6:"M",7:"K",8:"M",9:"Q",10:"M",11:"J"}
VASHYA_SCORE = {("Q","Q"):2,("Q","M"):1,("Q","J"):1,("Q","V"):0,("Q","K"):1,
                ("M","Q"):1,("M","M"):2,("M","J"):.5,("M","V"):0,("M","K"):1,
                ("J","Q"):1,("J","M"):.5,("J","J"):2,("J","V"):1,("J","K"):1,
                ("V","Q"):0,("V","M"):0,("V","J"):1,("V","V"):2,("V","K"):0,
                ("K","Q"):1,("K","M"):1,("K","J"):1,("K","V"):0,("K","K"):2}

# Yoni animal by nakshatra index 0-26
YONI = ["Horse","Elephant","Sheep","Serpent","Serpent","Dog","Cat","Sheep","Cat",
        "Rat","Rat","Cow","Buffalo","Tiger","Buffalo","Tiger","Deer","Deer","Dog",
        "Monkey","Mongoose","Monkey","Lion","Horse","Lion","Cow","Elephant"]
YONI_ENEMY = {frozenset(p) for p in [("Cow","Tiger"),("Elephant","Lion"),
              ("Horse","Buffalo"),("Dog","Deer"),("Serpent","Mongoose"),
              ("Monkey","Sheep"),("Cat","Rat")]}
# Full classical 5-tier Yoni scoring (same 4 / friendly 3 / neutral 2 / unfriendly 1
# / mortal-enemy 0), replacing the earlier flat same/enemy/else-neutral scheme.
# Friendly + unfriendly sets derived from the classical animal-relationship tables
# (mutually-agreed pairs; conflicting/asymmetric entries default to neutral).
YONI_FRIEND = {frozenset(p) for p in [
    ("Horse","Serpent"),("Horse","Monkey"),("Elephant","Sheep"),
    ("Elephant","Serpent"),("Elephant","Buffalo"),("Elephant","Monkey"),
    ("Sheep","Cow"),("Sheep","Buffalo"),("Sheep","Mongoose"),
    ("Cat","Deer"),("Cat","Monkey"),("Cow","Buffalo"),("Cow","Deer"),
    ("Monkey","Mongoose")]}
YONI_UNFRIEND = {frozenset(p) for p in [
    ("Horse","Cow"),("Horse","Tiger"),("Horse","Lion"),("Elephant","Tiger"),
    ("Sheep","Dog"),("Sheep","Rat"),("Sheep","Tiger"),("Sheep","Lion"),
    ("Serpent","Cat"),("Serpent","Rat"),("Serpent","Cow"),("Serpent","Buffalo"),
    ("Dog","Rat"),("Dog","Tiger"),("Dog","Mongoose"),("Dog","Lion"),
    ("Cat","Tiger"),("Cat","Mongoose"),("Cat","Lion"),("Rat","Mongoose"),
    ("Cow","Lion"),("Buffalo","Tiger"),("Buffalo","Lion"),("Tiger","Deer"),
    ("Tiger","Monkey"),("Tiger","Lion"),("Deer","Lion")]}


def _yoni_score(y1: str, y2: str) -> float:
    if y1 == y2:
        return 4
    pair = frozenset((y1, y2))
    if pair in YONI_ENEMY:
        return 0
    if pair in YONI_FRIEND:
        return 3
    if pair in YONI_UNFRIEND:
        return 1
    return 2

# Gana by nakshatra: D deva, M manushya, R rakshasa
GANA = "DMRMDMDDRRMMDRDRDRRMMDRRMMD"
GANA_NAME = {"D":"Deva","M":"Manushya","R":"Rakshasa"}
# Direction-dependent (groom, bride) classical Gana table. Key order is
# (groom_gana, bride_gana): a Manushya groom with a Deva bride scores 6, but a
# Deva groom with a Manushya bride scores 5; a Rakshasa groom with a Deva/Manushya
# bride scores 0. (Earlier table was symmetric and over-scored these cases.)
# Gana koota — aligned to AstroSage's table (the reference our users compare
# against): Manushya(groom)-Deva(bride) scores 5 (not 6), and Deva(groom)-
# Rakshasa(bride) scores 0 (not 1). Verified against 5 AstroSage MatchMaking
# reports (see tests/test_milan_accuracy.py).
GANA_SCORE = {("D","D"):6,("M","M"):6,("R","R"):6,
              ("D","M"):5,("M","D"):5,
              ("D","R"):0,("R","D"):0,
              ("M","R"):0,("R","M"):0}

# Nadi by nakshatra: A adi, M madhya, N antya (cycle A M N N M A A M N ...)
NADI = "AMNNMAAMNNMAAMNNMAAMNNMAAMN"
NADI_NAME = {"A":"Adi","M":"Madhya","N":"Antya"}

# Graha maitri: natural friendships of sign lords
FRIENDS = {"Sun":{"Moon","Mars","Jupiter"}, "Moon":{"Sun","Mercury"},
           "Mars":{"Sun","Moon","Jupiter"}, "Mercury":{"Sun","Venus"},
           "Jupiter":{"Sun","Moon","Mars"}, "Venus":{"Mercury","Saturn"},
           "Saturn":{"Mercury","Venus"}}
ENEMIES = {"Sun":{"Venus","Saturn"}, "Moon":set(), "Mars":{"Mercury"},
           "Mercury":{"Moon"}, "Jupiter":{"Mercury","Venus"},
           "Venus":{"Sun","Moon"}, "Saturn":{"Sun","Moon","Mars"}}

MANGLIK_HOUSES = {1, 2, 4, 7, 8, 12}


def _relation(a, b):
    if b in FRIENDS[a]: return "F"
    if b in ENEMIES[a]: return "E"
    return "N"

MAITRI_SCORE = {("F","F"):5,("F","N"):4,("N","F"):4,("N","N"):3,
                ("F","E"):1,("E","F"):1,("N","E"):.5,("E","N"):.5,("E","E"):0}


def _tara_ok(from_nak, to_nak):
    t = (((to_nak - from_nak) % 27) + 1) % 9
    t = 9 if t == 0 else t
    return t not in (3, 5, 7)


def _moon_manglik(chart):
    moon_sign = chart["grahas"]["Moon"].sign
    mars_sign = chart["grahas"]["Mars"].sign
    return ((mars_sign - moon_sign) % 12) + 1 in MANGLIK_HOUSES


def _western_sun(dob):
    """Western (tropical) Sun sign from the birth DATE only — the sign users know
    from horoscope apps. No birth time needed. Returns None on a bad date."""
    if not dob:
        return None
    try:
        m, d = int(dob[5:7]), int(dob[8:10])
    except Exception:
        return None
    cuts = [(1, 20, "Aquarius"), (2, 19, "Pisces"), (3, 21, "Aries"),
            (4, 20, "Taurus"), (5, 21, "Gemini"), (6, 21, "Cancer"),
            (7, 23, "Leo"), (8, 23, "Virgo"), (9, 23, "Libra"),
            (10, 23, "Scorpio"), (11, 22, "Sagittarius"), (12, 22, "Capricorn")]
    sign = "Capricorn"                       # Jan 1-19 wraps to Capricorn
    for sm, sd, nm in cuts:
        if (m, d) >= (sm, sd):
            sign = nm
    return sign


# ============================================================ KUNDLI MILAN
def compute_milan(p1: dict, p2: dict) -> dict:
    """p = {name, dob 'YYYY-MM-DD', tob 'HH:MM', tz, lat, lon, gender?}.
    Two kootas are direction-sensitive (Varna, Gana): they depend on which
    partner is the groom (boy) vs bride (girl). If a `gender` is supplied on
    either person we order those roles correctly regardless of input order;
    otherwise we fall back to the classical default of p1 = groom. The other
    six kootas are symmetric, so input order never affects them. UI labels the
    two people Partner 1 / Partner 2."""
    charts, moons = [], []
    for p in (p1, p2):
        dt = datetime.fromisoformat(f"{p['dob']}T{p.get('tob') or '12:00'}:00") \
             - timedelta(hours=p["tz"])
        ch = compute_chart(dt, p["lat"], p["lon"])
        charts.append(ch)
        m = ch["grahas"]["Moon"]
        moons.append({"sign": m.sign, "nak": m.nak, "pada": m.pada})

    g, b = moons[0], moons[1]
    # Order the groom (boy) and bride (girl) for the direction-sensitive kootas
    # (Varna, Gana). Default keeps the old behaviour (p1 = groom) so callers
    # that don't pass gender are unaffected; when gender is given the roles are
    # correct no matter who was entered first. Symmetric kootas keep g/b order.
    def _female(p): return (p.get("gender") or "").strip().lower() in ("female", "f", "bride", "girl", "woman")
    def _male(p):   return (p.get("gender") or "").strip().lower() in ("male", "m", "groom", "boy", "man")
    groom, bride = (moons[1], moons[0]) if (_male(p2) or _female(p1)) else (moons[0], moons[1])
    kootas = []

    v1, v2 = VARNA[groom["sign"]], VARNA[bride["sign"]]
    s = 1 if v1 >= v2 else 0
    kootas.append({"name": "Varna", "max": 1, "score": s,
                   "detail": f"{VARNA_NAME[v1]} – {VARNA_NAME[v2]}",
                   "meaning": "work-ego compatibility"})

    vg, vb = VASHYA[g["sign"]], VASHYA[b["sign"]]
    kootas.append({"name": "Vashya", "max": 2, "score": VASHYA_SCORE[(vg, vb)],
                   "detail": f"{g and SIGNS[g['sign']]} – {SIGNS[b['sign']]}",
                   "meaning": "mutual influence and pull"})

    s = (1.5 if _tara_ok(b["nak"], g["nak"]) else 0) + \
        (1.5 if _tara_ok(g["nak"], b["nak"]) else 0)
    kootas.append({"name": "Tara", "max": 3, "score": s,
                   "detail": f"{NAKSHATRAS[g['nak']]} – {NAKSHATRAS[b['nak']]}",
                   "meaning": "health and wellbeing of the bond"})

    y1, y2 = YONI[g["nak"]], YONI[b["nak"]]
    s = _yoni_score(y1, y2)
    kootas.append({"name": "Yoni", "max": 4, "score": s,
                   "detail": f"{y1} – {y2}", "meaning": "physical and instinctive harmony"})

    l1, l2 = SIGN_LORD[g["sign"]], SIGN_LORD[b["sign"]]
    s = 5 if l1 == l2 else MAITRI_SCORE[(_relation(l1, l2), _relation(l2, l1))]
    kootas.append({"name": "Graha Maitri", "max": 5, "score": s,
                   "detail": f"{l1} – {l2}", "meaning": "mental wavelength and friendship"})

    g1, g2 = GANA[groom["nak"]], GANA[bride["nak"]]
    kootas.append({"name": "Gana", "max": 6, "score": GANA_SCORE[(g1, g2)],
                   "detail": f"{GANA_NAME[g1]} – {GANA_NAME[g2]}",
                   "meaning": "temperament match"})

    dist = (b["sign"] - g["sign"]) % 12 + 1
    rev = (g["sign"] - b["sign"]) % 12 + 1
    bhakoot_bad = {dist, rev} & {(2, 12) and 2, 12, 5, 9, 6, 8} and \
                  ({dist, rev} in [{2, 12}, {5, 9}, {6, 8}])
    # Bhakoot cancellation: same sign-lord, or lords in mutual friendship
    from jyotish_maps import MD_LORD_HI as _unused  # keep import graph simple
    bl1, bl2 = SIGN_LORD[g["sign"]], SIGN_LORD[b["sign"]]
    bhakoot_cancel = None
    if bhakoot_bad:
        if bl1 == bl2:
            bhakoot_cancel = f"Dono rashiyon ka lord ek hi hai ({bl1}) — Bhakoot dosha cancelled."
        elif _relation(bl1, bl2) == "F" and _relation(bl2, bl1) == "F":
            bhakoot_cancel = f"Rashi lords ({bl1}–{bl2}) mutual friends hain — Bhakoot dosha cancelled."
    s = 0 if bhakoot_bad else 7
    kootas.append({"name": "Bhakoot", "max": 7, "score": s,
                   "detail": f"{SIGNS[g['sign']]} – {SIGNS[b['sign']]} ({min(dist,rev)}/{max(dist,rev)})",
                   "meaning": "emotional bond, family growth"})

    n1, n2 = NADI[g["nak"]], NADI[b["nak"]]
    nadi_dosha = n1 == n2
    # classical Nadi cancellation: same nadi cancelled if rashis differ,
    # or same nakshatra with different padas
    nadi_cancel = None
    if nadi_dosha:
        if g["nak"] == b["nak"] and g["pada"] != b["pada"]:
            nadi_cancel = "Same nakshatra, alag pada — classical rule mein Nadi dosha cancelled."
        elif g["sign"] != b["sign"]:
            nadi_cancel = "Moon rashi alag hai — widely-followed classical rule mein Nadi dosha cancelled."
    kootas.append({"name": "Nadi", "max": 8, "score": 0 if nadi_dosha else 8,
                   "detail": f"{NADI_NAME[n1]} – {NADI_NAME[n2]}",
                   "meaning": "health of progeny, vitality"})

    total = round(sum(k["score"] for k in kootas), 1)
    if total >= 32: verdict, vkey = "Excellent match", "excellent"
    elif total >= 25: verdict, vkey = "Very good match", "verygood"
    elif total >= 18: verdict, vkey = "Acceptable match", "ok"
    else: verdict, vkey = "Below threshold — needs careful consideration", "weak"

    m1, m2 = _moon_manglik(charts[0]), _moon_manglik(charts[1])
    if m1 and m2: manglik_note = ("Both charts carry a Manglik placement — and in the classical rule a "
                                  "Manglik–Manglik pairing cancels out. Not an obstacle.")
    elif m1 or m2: manglik_note = ("One chart carries a Manglik placement (Moon-based check). "
                                   "Cancellation rules usually apply — a full lagna-based check needs "
                                   "exact birth times for both.")
    else: manglik_note = "Neither chart carries a Manglik placement (Moon-based check). ✅"

    notes = []
    if nadi_dosha:
        notes.append("Nadi dosha present — traditionally the most weighted dosha. "
                     "Note: cancellation applies if moon signs differ or nakshatra "
                     "padas differ; a detailed pada-level check is recommended.")
    if s == 0 and not nadi_dosha:
        pass
    if not bhakoot_bad and total < 18:
        notes.append("Low score is spread across kootas rather than one dosha — "
                     "often improvable factors (understanding, timing) rather than structural.")

    # ---- per-koota couple-voiced interpretation (high/mid/low bands) ----
    for k in kootas:
        pct = k["score"] / k["max"]
        hi, mid, lo = KOOTA_TEXT[k["name"]]
        k["text"] = hi if pct >= 0.75 else (lo if pct < 0.4 or not mid else mid)
        if not k["text"]: k["text"] = lo if pct < 0.75 else hi

    # ---- cancellations -> effective score ----
    cancellations = []
    effective = total
    if nadi_dosha and nadi_cancel:
        cancellations.append({"koota": "Nadi", "rule": nadi_cancel, "restored": 8})
        effective += 8
    if bhakoot_bad and bhakoot_cancel:
        cancellations.append({"koota": "Bhakoot", "rule": bhakoot_cancel, "restored": 7})
        effective += 7
    effective = round(min(effective, 36.0), 1)
    eff_verdict = ("Excellent match" if effective >= 32 else
                   "Very good match" if effective >= 25 else
                   "Acceptable match" if effective >= 18 else
                   "Below threshold — needs careful consideration")

    # ---- strengths & watch-outs ----
    ranked = sorted(kootas, key=lambda k: k["score"] / k["max"], reverse=True)
    strengths = [k for k in ranked if k["score"] / k["max"] >= 0.75][:3]
    watchouts = [k for k in ranked[::-1] if k["score"] / k["max"] < 0.5][:2]

    # ---- element dynamic ----
    e1, e2 = SIGN_ELEMENT[g["sign"]], SIGN_ELEMENT[b["sign"]]
    element = {"p1": ELEMENT_HI[e1], "p2": ELEMENT_HI[e2],
               "text": ELEMENT_PAIR[frozenset([e1, e2])]}

    # ---- nakshatra one-liners for each ----
    nak_lines = {"p1": NAK_PROFILE[g["nak"]][2], "p2": NAK_PROFILE[b["nak"]][2]}

    # ---- full birth charts for the kundli diagrams (both partners) ----
    # Planet positions by sign are stable through the day; the Lagna (ascendant)
    # needs the exact birth time. When no time is given we fall back to a Moon
    # chart (Chandra lagna), which is honest and stable and matches the Moon-based
    # Ashtakoota method used here.
    def _chart_payload(ch, tob):
        return {"lagna": SIGNS[ch["lagna_sign"]],
                "moon_sign": SIGNS[ch["grahas"]["Moon"].sign],
                "time_known": bool(tob),
                "planets": {gp.name: {"sign": SIGNS[gp.sign], "retro": gp.retro}
                            for gp in ch["grahas"].values()}}
    chart_p1 = _chart_payload(charts[0], p1.get("tob"))
    chart_p2 = _chart_payload(charts[1], p2.get("tob"))

    # ---- per-person profile facts (for the expanded report sections) ----
    # sun_western = the Western/tropical Sun sign (the one users recognise from
    # horoscope apps), from the birth DATE only. Shown alongside the Vedic Moon
    # sign so the report can bridge "you know your Sun sign; we read your Moon".
    profiles = {
        "p1": {"name": p1["name"], "sign": SIGNS_EN[g["sign"]], "nak": NAKSHATRAS[g["nak"]],
               "pada": g["pada"], "element": e1, "lord": SIGN_LORD[g["sign"]],
               "sun_western": _western_sun(p1.get("dob")),
               "symbol": NAK_PROFILE[g["nak"]][0], "persona": NAK_PROFILE[g["nak"]][1],
               "love": NAK_PROFILE[g["nak"]][2], "chart": chart_p1},
        "p2": {"name": p2["name"], "sign": SIGNS_EN[b["sign"]], "nak": NAKSHATRAS[b["nak"]],
               "pada": b["pada"], "element": e2, "lord": SIGN_LORD[b["sign"]],
               "sun_western": _western_sun(p2.get("dob")),
               "symbol": NAK_PROFILE[b["nak"]][0], "persona": NAK_PROFILE[b["nak"]][1],
               "love": NAK_PROFILE[b["nak"]][2], "chart": chart_p2},
    }
    match_pct = int(round(effective / 36 * 100))

    # ---- premium free-teaser preview (a real GLIMPSE of the paid report) ----
    # The verdict word + the one-breath summary come straight from the report's
    # own helpers so the preview reads as a genuine slice of what's bought.
    # We reveal the SCORE, 2-3 theme cards and the one-line summary; the deeper
    # koota-by-koota detail, doshas and action plan stay locked behind paywall.
    from report_view import (_theme_scores as _ts, milan_one_breath as _one_breath,
                             milan_one_breath_hi as _one_breath_hi)
    from milan_v2 import _verdict_word as _vword
    # Devanagari lookups for the Hindi funnel page (milan.hi.html): reuse the
    # report localiser's proper-noun tokens (signs, nakshatras, planets, elements)
    # and its verdict-word dictionary rather than duplicating those tables here.
    from milan_hi import TOK as _HI_TOK, HI as _HI_TEXT
    from jyotish_maps import NAK_PROFILE_HI
    _dev = lambda s: _HI_TOK.get(s, s)
    _bands = lambda pc: "strong" if pc >= 75 else ("solid" if pc >= 45 else "grow")
    _tscores = _ts(kootas)
    teaser_themes = [{"name": t["theme"]["name"], "emoji": t["theme"]["emoji"],
                      "pct": int(round(t["pct"])), "blurb": t["theme"]["blurb"],
                      "band": _bands(t["pct"])} for t in _tscores[:3]]
    strongest = _tscores[0]["theme"]["name"] if _tscores else ""

    return {
        "product": "milan",
        "meta": {"p1": p1["name"], "p2": p2["name"],
                 "generated": datetime.utcnow().strftime("%Y-%m-%d"),
                 "system": "Ashtakoota (Moon-based)", "ayanamsa": "Lahiri",
                 "time_note": ("Exact birth times used." if p1.get("tob") and p2.get("tob")
                               else "Moon-based matching is largely stable across the day; "
                                    "exact times refine pada-level checks.")},
        "teaser": {
            "p1_moon": SIGNS[g["sign"]], "p1_nak": NAKSHATRAS[g["nak"]],
            "p2_moon": SIGNS[b["sign"]], "p2_nak": NAKSHATRAS[b["nak"]],
            # Per-person facts for the warm-cream preview UI (same lookups as
            # `profiles` below — English sign names, nakshatra persona/love
            # one-liners, element + ruling lord for the trait-box pills).
            "p1_name": p1["name"], "p2_name": p2["name"],
            "p1_moon_en": SIGNS_EN[g["sign"]], "p2_moon_en": SIGNS_EN[b["sign"]],
            "p1_persona": NAK_PROFILE[g["nak"]][1], "p1_love": NAK_PROFILE[g["nak"]][2],
            "p2_persona": NAK_PROFILE[b["nak"]][1], "p2_love": NAK_PROFILE[b["nak"]][2],
            "p1_element": e1.capitalize(), "p2_element": e2.capitalize(),
            "p1_lord": SIGN_LORD[g["sign"]], "p2_lord": SIGN_LORD[b["sign"]],
            "gana_preview": f"Gana: {GANA_NAME[g1]} – {GANA_NAME[g2]}",
            # Revealed in the premium preview (the hook):
            "score_locked": False,
            "match_pct": match_pct,
            "verdict": _vword(match_pct),
            "one_breath": _one_breath(kootas),
            "themes": teaser_themes,
            "strongest": strongest,
            # ---- Devanagari (_hi) variants for the Hindi funnel teaser ----
            # Additive only: the English fields above are the contract for
            # milan.html AND the fallback for milan.hi.html when a cached teaser
            # predates these fields. Authored static tables — no runtime
            # translation, no LLM.
            "p1_moon_hi": _dev(SIGNS[g["sign"]]), "p2_moon_hi": _dev(SIGNS[b["sign"]]),
            "p1_nak_hi": _dev(NAKSHATRAS[g["nak"]]), "p2_nak_hi": _dev(NAKSHATRAS[b["nak"]]),
            "p1_persona_hi": NAK_PROFILE_HI[g["nak"]][0], "p1_love_hi": NAK_PROFILE_HI[g["nak"]][1],
            "p2_persona_hi": NAK_PROFILE_HI[b["nak"]][0], "p2_love_hi": NAK_PROFILE_HI[b["nak"]][1],
            "p1_element_hi": _dev(e1.capitalize()), "p2_element_hi": _dev(e2.capitalize()),
            "p1_lord_hi": _dev(SIGN_LORD[g["sign"]]), "p2_lord_hi": _dev(SIGN_LORD[b["sign"]]),
            "verdict_hi": _HI_TEXT.get(_vword(match_pct), _vword(match_pct)),
            "one_breath_hi": _one_breath_hi(kootas)},
        "kootas": kootas, "total": total, "max_total": 36,
        "verdict": verdict, "verdict_key": vkey,
        "cancellations": cancellations, "effective": effective,
        "effective_verdict": eff_verdict,
        "strengths": [k["name"] for k in strengths],
        "watchouts": [k["name"] for k in watchouts],
        "element": element, "nak_lines": nak_lines,
        "padas": {"p1": g["pada"], "p2": b["pada"]},
        "profiles": profiles, "match_pct": match_pct,
        "manglik": {"p1": m1, "p2": m2, "note": manglik_note},
        "notes": notes,
    }


# ============================================================ LIFE BLUEPRINT
LAGNA_PERSONA = [
    "direct, self-starting, competitive — you move first and think on your feet",
    "steady, sensory, patient — you build slowly and hold what you build",
    "curious, verbal, versatile — you live through ideas and exchange",
    "protective, intuitive, memory-driven — you lead with feeling",
    "dignified, expressive, generous — you need a stage and a cause",
    "precise, analytical, service-minded — you improve everything you touch",
    "balancing, relational, aesthetic — you think in partnerships",
    "intense, private, strategic — you transform rather than adjust",
    "expansive, principled, freedom-loving — you follow meaning",
    "structured, ambitious, enduring — you climb in decades, not days",
    "independent, systemic, humanitarian — you belong to the future",
    "fluid, empathetic, imaginative — you absorb and dissolve boundaries"]

MD_PHASE = {
    "Sun": "authority, visibility, father-figures — a phase of standing in your own name",
    "Moon": "emotional recalibration, home, public connect — inner life leads outer",
    "Mars": "drive, conflict-and-conquest, property, siblings — energy seeks a battlefield",
    "Rahu": "ambition, unconventional rise, foreign elements — rapid but restless growth",
    "Jupiter": "wisdom, expansion, children, teachers — doors open through knowledge and faith",
    "Saturn": "discipline, karma-settlement, slow durable gains — what you build now stays",
    "Mercury": "commerce, communication, learning — intellect becomes income",
    "Ketu": "detachment, spiritual sharpening, endings that liberate — less becomes more",
    "Venus": "relationships, comfort, creativity, wealth-enjoyment — life softens and sweetens"}

CAREER_HOUSE = [
    "self-driven work — entrepreneurship, independent practice, your name on the door",
    "wealth-handling fields — finance, food, family business, voice-related work",
    "communication and courage — media, sales, writing, hands-on skill",
    "home-linked work — real estate, vehicles, education, working close to your base",
    "creative-speculative fields — teaching, entertainment, markets, working with young people",
    "service and problem-solving — healthcare, law, operations, competitive fields",
    "partnership-driven work — consulting, client business, trade, public dealing",
    "research and transformation — depth fields, insurance, occult, others' resources",
    "knowledge and distance — higher education, publishing, foreign connections, dharma-fields",
    "classic career house — status roles, government, corporate ladder, public responsibility",
    "network-scale work — large organisations, communities, gains through circles",
    "behind-the-scenes or beyond-borders — foreign lands, institutions, imaginative fields"]

# Career archetype, same index as CAREER_HOUSE (tenth_lord_house - 1). Mirrors
# milan's ARCHETYPE shape (name/emoji/tagline/body) for a consistent voice
# across products -- a real, deterministic label from the chart, not a mockup.
CAREER_ARCHETYPE = [
    {"name": "The Founder", "emoji": "🚀", "tagline": "Building something with your name on it",
     "body": "You're wired for independence — work fits you best when you're shaping the role, not just filling it."},
    {"name": "The Steward", "emoji": "💰", "tagline": "Steady hands with resources",
     "body": "Money, assets, family enterprise — you have a natural instinct for managing and growing what's already there."},
    {"name": "The Communicator", "emoji": "🎤", "tagline": "Your words do the heavy lifting",
     "body": "Media, sales, writing, thinking fast on your feet — your career runs on courage and clear communication."},
    {"name": "The Anchor", "emoji": "🏡", "tagline": "Strong roots, strong results",
     "body": "You do your best work close to a steady base — property, education, or anything that needs strong foundations."},
    {"name": "The Creative", "emoji": "🎨", "tagline": "Original ideas, playful execution",
     "body": "Teaching, entertainment, working with young people — you're built for fields that reward imagination over routine."},
    {"name": "The Fixer", "emoji": "🛠️", "tagline": "You solve what others avoid",
     "body": "Healthcare, law, operations — competitive, service-driven fields where your problem-solving instinct is the whole point."},
    {"name": "The Connector", "emoji": "🤝", "tagline": "Better work happens with people",
     "body": "Consulting, client relationships, trade — you're built for partnership-driven work, not solo grind."},
    {"name": "The Investigator", "emoji": "🔍", "tagline": "You go where others stop looking",
     "body": "Research and depth-fields, working with what's hidden or complex — patience with complexity is your edge."},
    {"name": "The Scholar", "emoji": "📚", "tagline": "Knowledge is your currency",
     "body": "Higher education, publishing, foreign connections — your fortune grows the further you're willing to learn and travel."},
    {"name": "The Builder", "emoji": "🏛️", "tagline": "Status earned the structured way",
     "body": "Government, corporate ladders, public responsibility — you're built for roles where the position carries real weight."},
    {"name": "The Networker", "emoji": "🌐", "tagline": "Your circle multiplies your wins",
     "body": "Large organisations, communities, collective effort — the bigger the network, the bigger your gains tend to be."},
    {"name": "The Explorer", "emoji": "🧭", "tagline": "Your path looks different, on purpose",
     "body": "Foreign lands, institutions, imaginative fields — success for you often comes through the unconventional route."},
]

PLANET_GIFT = {"Sun": "natural authority", "Moon": "emotional intelligence",
               "Mars": "courage and stamina", "Mercury": "sharp communication",
               "Jupiter": "wisdom and luck-expansion", "Venus": "charm and aesthetic sense",
               "Saturn": "endurance and discipline"}
PLANET_LESSON = {"Sun": "ego and recognition", "Moon": "emotional steadiness",
                 "Mars": "anger and impulse", "Mercury": "scattered focus",
                 "Jupiter": "over-optimism", "Venus": "indulgence",
                 "Saturn": "delay and self-doubt"}

# Blueprint's Life Wheel: a 3-way bucket (thriving/building/watch) derived
# entirely from a house lord's already-computed dignity -- no new scoring.
# Dusthanas (6/8/12) invert the reading: a weak lord there is classically a
# relief (less of that house's difficulty), a strong one keeps it active.
_DUSTHANA_HOUSES = (6, 8, 12)


def _wheel_tag(dignity: str, house_num: int) -> str:
    strong = dignity in ("exalted", "own")
    weak = dignity == "debilitated"
    if house_num in _DUSTHANA_HOUSES:
        if weak: return "thriving"
        if strong: return "watch"
    else:
        if strong: return "thriving"
        if weak: return "watch"
    return "building"


def compute_blueprint(name, dob, tob, tz, lat, lon, time_quality="T0") -> dict:
    dt = datetime.fromisoformat(f"{dob}T{tob}:00") - timedelta(hours=tz)
    ch = compute_chart(dt, lat, lon)
    g = ch["grahas"]
    moon = g["Moon"]
    today = datetime.utcnow()
    use_chandra = time_quality in ("T2", "T3")
    ref = moon.sign if use_chandra else ch["lagna_sign"]

    # career: 10th lord's house from ref
    tenth_sign = (ref + 9) % 12
    tenth_lord = SIGN_LORD[tenth_sign]
    tl_house = ((g[tenth_lord].sign - ref) % 12)  # 0-indexed
    career = CAREER_HOUSE[tl_house]

    strengths = [f"{p.name} — {PLANET_GIFT[p.name]} ({'exalted' if p.dignity=='exalted' else 'own sign'})"
                 for p in g.values() if p.dignity in ("own", "exalted") and p.name in PLANET_GIFT]
    lessons = [f"{p.name} — {PLANET_LESSON[p.name]}"
               for p in g.values() if (p.dignity == "debilitated" or p.combust)
               and p.name in PLANET_LESSON]

    # life roadmap: current + next 2 mahadashas
    tree = vimshottari_tree(moon.lon, dt, today + timedelta(days=40 * 365.25))

    roadmap, started = [], False
    for md in tree:
        if md["end"] < today: continue
        roadmap.append({"lord": md["lord"],
                        "from": max(md["start"], today).strftime("%Y"),
                        "to": md["end"].strftime("%Y"),
                        "theme": MD_PHASE[md["lord"]],
                        "current": md["start"] <= today <= md["end"]})
        if len(roadmap) == 3: break

    active_md = next((m for m in tree if m["start"] <= today <= m["end"]), None)
    active_ad = next((a for a in active_md["ads"] if a["start"] <= today <= a["end"]),
                     None) if active_md else None

    # ---- new depth: sade sati, nakshatra profile, elements, wealth, health, relationship ----
    sade = _sade_sati(moon.sign, today)
    nakp = NAK_PROFILE[moon.nak]
    from collections import Counter
    elem_count = Counter(SIGN_ELEMENT[p.sign] for p in g.values())
    dominant = elem_count.most_common(1)[0]
    missing = [e for e in ("fire", "earth", "air", "water") if elem_count.get(e, 0) == 0]
    second_lord = SIGN_LORD[(ref + 1) % 12]
    eleventh_lord = SIGN_LORD[(ref + 10) % 12]
    wealth = {"second": WEALTH_2L[((g[second_lord].sign - ref) % 12)],
              "gains": GAINS_11L[((g[eleventh_lord].sign - ref) % 12)]}
    health = HEALTH_6[(ref + 5) % 12]
    from report_view import SIGN_PARTNER
    seventh_sign_b = (ref + 6) % 12
    relationship = {"seventh": SIGNS[seventh_sign_b], "line": SIGN_PARTNER[SIGNS[seventh_sign_b]]}
    # year ahead: current AD + next AD + Jupiter/Saturn from moon
    import swisseph as swe_
    from engine import sidereal_lon, jd, sign_of, houses_from
    jl, _ = sidereal_lon(swe_.JUPITER, jd(today))
    sl, _ = sidereal_lon(swe_.SATURN, jd(today))
    jup_h = houses_from(moon.sign, sign_of(jl))
    sat_h = houses_from(moon.sign, sign_of(sl))
    next_ad = None
    if active_md:
        ads = active_md["ads"]
        for i, a in enumerate(ads):
            if a is active_ad and i + 1 < len(ads):
                next_ad = ads[i + 1]; break
        if next_ad is None:
            nmd = next((m for m in tree if m["start"] > today), None)
            if nmd and nmd["ads"]: next_ad = nmd["ads"][0]
    year_ahead = {"jup_house": jup_h, "jup_good": jup_h in (1, 2, 5, 7, 9, 11),
                  "sat_house": sat_h,
                  "next_ad": {"lord": next_ad["lord"],
                              "from": next_ad["start"].strftime("%b %Y")} if next_ad else None}

    # ---- the three genuinely new life areas + a small parents/siblings note ----
    home = HOME_4[(ref + 3) % 12]
    children = CHILDREN_5[(ref + 4) % 12]
    foreign = FOREIGN_12[(ref + 11) % 12]
    family = FAMILY_9[(ref + 8) % 12]

    # ---- Life Wheel: one 3-way tag per area, from each house lord's dignity ----
    lagna_lord = SIGN_LORD[ref]
    seventh_lord = SIGN_LORD[(ref + 6) % 12]
    fifth_lord = SIGN_LORD[(ref + 4) % 12]
    fourth_lord = SIGN_LORD[(ref + 3) % 12]
    twelfth_lord = SIGN_LORD[(ref + 11) % 12]
    sixth_lord = SIGN_LORD[(ref + 5) % 12]
    ninth_lord = SIGN_LORD[(ref + 8) % 12]
    wheel = {
        "career": _wheel_tag(g[tenth_lord].dignity, 10),
        "money": _wheel_tag(g[second_lord].dignity, 2),
        "marriage": _wheel_tag(g[seventh_lord].dignity, 7),
        "children": _wheel_tag(g[fifth_lord].dignity, 5),
        "home": _wheel_tag(g[fourth_lord].dignity, 4),
        "foreign": _wheel_tag(g[twelfth_lord].dignity, 12),
        "health": _wheel_tag(g[sixth_lord].dignity, 6),
        "growth": _wheel_tag(g[lagna_lord].dignity, 1),
        "family": _wheel_tag(g[ninth_lord].dignity, 9),
        "timing": "watch" if sade["active"] else _wheel_tag(g[active_md["lord"]].dignity, 1),
    }

    return {
        "product": "blueprint",
        "meta": {"name": name, "generated": today.strftime("%Y-%m-%d"),
                 "system": "chandra_lagna" if use_chandra else "lagna",
                 "time_quality": time_quality, "ayanamsa": "Lahiri"},
        "teaser": {"moon_sign": SIGNS[moon.sign], "moon_sign_en": SIGNS_EN[moon.sign],
                   "nakshatra": NAKSHATRAS[moon.nak], "pada": moon.pada,
                   "current_dasha": f"{active_md['lord']} Mahadasha — {active_ad['lord']} Antardasha"
                                    if active_ad else "—",
                   "dasha_till": active_ad["end"].strftime("%b %Y") if active_ad else "—",
                   "lagna_en": SIGNS_EN[ch["lagna_sign"]],
                   "cur_ad_lord": active_ad["lord"] if active_ad else None,
                   # Free-preview Life Wheel (landing-page teaser only): the same
                   # real, already-computed 10-area Thriving/Building/Watch verdict
                   # shown in the full report -- read-only copy of the `wheel` dict
                   # above, no new calculation.
                   "wheel": wheel},
        "chart": {"lagna": SIGNS[ch["lagna_sign"]],
                  "planets": {p.name: {"sign": SIGNS[p.sign], "nakshatra": NAKSHATRAS[p.nak],
                                       "dignity": p.dignity, "retro": p.retro,
                                       "combust": p.combust} for p in g.values()}},
        "persona": {"lagna_line": LAGNA_PERSONA[ch["lagna_sign"]],
                    "moon_line": LAGNA_PERSONA[moon.sign],
                    "note_chandra": use_chandra},
        "career": {"tenth_sign": SIGNS[tenth_sign], "tenth_lord": tenth_lord,
                   "direction": career},
        "strengths": strengths or ["A balanced chart — no single dominant planet; "
                                   "versatility is itself the gift"],
        "lessons": lessons or ["No major debilitations — your challenges are "
                               "situational, not structural"],
        "roadmap": roadmap,
        "sade_sati": sade,
        "nak_profile": {"nakshatra": NAKSHATRAS[moon.nak], "symbol": nakp[0],
                        "nature": nakp[1], "relationship": nakp[2]},
        "elements": {"dominant": ELEMENT_HI[dominant[0]], "dominant_n": dominant[1],
                     "missing": [ELEMENT_HI[m] for m in missing]},
        "wealth": wealth, "health": health, "relationship": relationship,
        "year_ahead": year_ahead,
        "home": home, "children": children, "foreign": foreign, "family": family,
        "wheel": wheel,
    }


# ============================================================ VYAPAR (business)
_TONE_LABEL = {"good": "Supportive", "warn": "Hard", "neutral": "Mixed"}
_DIG_RANK = {"exalted": 3, "own": 2, "neutral": 1, "debilitated": 0}


def _ordinal(n: int) -> str:
    return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def _biz_planet_power(p) -> int:
    """Coarse strength of a planet for business ranking: dignity minus a
    combustion penalty. Deterministic, no degree math needed here."""
    return _DIG_RANK.get(p.dignity, 1) - (1 if p.combust else 0)


def _biz_remedy_line(planet) -> str:
    """Agency-first remedy string for an obstructing planet (7 classical +
    the two nodes), reusing the shared REMEDY tables."""
    if planet in REMEDY_7L:
        fast, mantra, gem = REMEDY_7L[planet]
        return (f"{fast}: keep it a light, disciplined day and chant "
                f"“{mantra}”. Consider {gem.split(' — ')[0]} only after an expert trial.")
    if planet in REMEDY_NODE:
        fast, mantra, note = REMEDY_NODE[planet]
        return f"{fast}: chant “{mantra}”. {note}"
    return "Keep routines steady and decisions unhurried; discipline is the durable remedy."


def compute_vyapar(name, dob, tob, tz, lat, lon, time_quality="T0") -> dict:
    """Business-growth report engine (/vyapar). Reuses compute_blueprint's
    classical derivations (chart, house lords, Vimshottari dasha, Sade Sati,
    Jupiter/Saturn transits) and maps them to BUSINESS verdicts via the
    authored BIZ_* tables in jyotish_maps. Deterministic, no LLM, never raises
    on valid input. `tz` may be a numeric UTC-offset in hours (like
    compute_blueprint) or an IANA zone name such as 'Asia/Kolkata'."""
    if isinstance(tz, str):                                  # accept a zone name too
        try:
            from zoneinfo import ZoneInfo
            _naive = datetime.fromisoformat(f"{dob}T{tob}:00")
            _off = ZoneInfo(tz).utcoffset(_naive)
            tz = _off.total_seconds() / 3600 if _off else 0.0
        except Exception:
            tz = 5.5                                         # sensible IST fallback
    dt = datetime.fromisoformat(f"{dob}T{tob}:00") - timedelta(hours=tz)
    ch = compute_chart(dt, lat, lon)
    g = ch["grahas"]
    moon = g["Moon"]
    today = datetime.utcnow()
    use_chandra = time_quality in ("T2", "T3")
    ref = moon.sign if use_chandra else ch["lagna_sign"]

    # ---- business significators (whole-sign house lords from ref) ----
    def _hsign(h):  # 1-indexed house -> sign
        return (ref + h - 1) % 12

    def _hlord(h):
        return SIGN_LORD[_hsign(h)]

    def _lord_house(lord):  # 1-12 house occupied by a lord (from ref)
        return ((g[lord].sign - ref) % 12) + 1

    tenth_sign = _hsign(10)
    tenth_lord = _hlord(10)
    tl_house = (g[tenth_lord].sign - ref) % 12               # 0-indexed
    second_lord = _hlord(2)
    eleventh_lord = _hlord(11)
    seventh_lord = _hlord(7)
    sec_house = _lord_house(second_lord)                     # 1-12
    ele_house = _lord_house(eleventh_lord)

    temperament = BIZ_TEMPERAMENT[ref]
    sector = BIZ_SECTOR_10L[tenth_lord]
    partnership_map = BIZ_PARTNERSHIP_7L[seventh_lord]

    # ---- Devanagari resources for the /hi/business-growth report (additive).
    # English fields below are the contract and never change; these feed the
    # parallel *_hi twins the Hindi renderer reads. Same meaning, no LLM. ----
    from jyotish_maps import BIZ_PARTNERSHIP_7L_HI, BIZ_OBSTACLE_HI
    temperament_hi = BIZ_TEMPERAMENT_HI[ref]
    sector_hi = BIZ_SECTOR_10L_HI[tenth_lord]
    partnership_map_hi = BIZ_PARTNERSHIP_7L_HI[seventh_lord]
    _SADE_PHASE_HI = {"rising phase": "उठान का चरण", "peak phase": "चरम चरण",
                      "setting phase": "उतार का चरण"}
    _TONE_LABEL_HI = {"good": "सहायक", "warn": "कठिन", "neutral": "मिला-जुला"}
    _H_ORD_HI = {1: "पहले", 2: "दूसरे", 3: "तीसरे", 4: "चौथे", 5: "पाँचवें",
                 6: "छठे", 7: "सातवें", 8: "आठवें", 9: "नौवें", 10: "दसवें",
                 11: "ग्यारहवें", 12: "बारहवें"}
    WEALTH_2L_HI = [
        "अपने बल की कमाई — आमदनी सीधे आपकी अपनी मेहनत और नाम से जुड़ी",
        "मज़बूत संचय-प्रवृत्ति — पैसा तब बढ़ता है जब पास रखा और ख़ुद सँभाला जाए",
        "हुनर, संचार या साहस से कमाई — आमदनी पहल के पीछे आती है",
        "संपत्ति बनाने का ढंग — ज़मीन-जायदाद, वाहन और घर से जुड़ा धन आपको रास आता है",
        "रचनात्मकता, सट्टे या शिक्षण से लाभ — सोच-समझकर लिया जोखिम फल दे सकता है",
        "सेवा और समस्या-समाधान से कमाई — स्थिर पर मुक़ाबले वाले क्षेत्र",
        "साझेदारी से धन — कारोबारी साझेदार और जीवनसाथी का भाग्य दोनों मायने रखते हैं",
        "अचानक लाभ और दूसरों के संसाधन — बीमा, विरासत और बदलाव से जुड़ा धन",
        "ज्ञान, दूरी या धर्म से भाग्य — घर से दूर कमाई बढ़ती है",
        "करियर से जुड़ा धन — पद और रुतबा सीधे आमदनी चलाते हैं",
        "नेटवर्क के पैमाने का लाभ — दायरा जितना बड़ा, कमाई उतनी बड़ी",
        "ख़र्च के साथ कमाई — पैसा आता-जाता रहता है; विदेशी या संस्थागत संबंध उसे थामने में मदद करते हैं"]
    GAINS_11L_HI = [
        "लाभ अपनी पहल से आता है — आपको माँगना, आवेदन करना, शुरू करना होगा",
        "लाभ बचत और पारिवारिक संसाधनों से मज़बूत होता है",
        "भाई-बहन, मीडिया, लेखन या छोटे उद्यमों से लाभ",
        "संपत्ति, मातृभूमि और भावनात्मक स्थिरता से लाभ",
        "संतान, विद्यार्थियों, रचनात्मकता या बाज़ारों से लाभ",
        "मेहनत और मुक़ाबले के बाद लाभ — कमाया हुआ, कभी उपहार में नहीं",
        "साझेदारियों और जन-व्यवहार से लाभ",
        "गहरी शोध, दूसरों के पैसे या अचानक मोड़ से लाभ",
        "गुरुओं, उच्च शिक्षा और लंबी यात्राओं से लाभ",
        "करियर की उत्कृष्टता से लाभ — साख इनाम में बदलती है",
        "लाभ की मज़बूत छाप — नेटवर्क आपकी बनाई हर चीज़ को कई गुना करते हैं",
        "ऐसा लाभ जो कहीं और की वृद्धि को सींचता है — रिसाव पर नज़र रखें, इसे निवेश में लगाएँ"]
    # short, plain one-liners for the page-3 summary capsule (detail keeps GAINS_11L_HI)
    GAINS_11L_SHORT_HI = [
        "लाभ आपकी अपनी पहल से आता है।",
        "लाभ बचत और परिवार के सहारे से आता है।",
        "भाई-बहन, मीडिया या छोटे काम से लाभ।",
        "संपत्ति और घर-ज़मीन से लाभ।",
        "संतान, रचनात्मकता या बाज़ार से लाभ।",
        "मेहनत और मुक़ाबले के बाद लाभ मिलता है।",
        "साझेदारी और जन-व्यवहार से लाभ।",
        "शोध, दूसरों के पैसे या अचानक मोड़ से लाभ।",
        "गुरु, उच्च शिक्षा और लंबी यात्रा से लाभ।",
        "करियर और साख से लाभ मिलता है।",
        "नेटवर्क आपकी हर मेहनत को कई गुना करते हैं।",
        "कमाई अच्छी, पर बचत कमज़ोर — पैसा टिकाना सीखें।"]
    # short, plain one-liners for the page-3 summary capsule (detail keeps GAINS_11L)
    GAINS_11L_SHORT = [
        "Gains come from your own initiative.",
        "Gains come from savings and family.",
        "Gains through siblings, media or small ventures.",
        "Gains through property and home base.",
        "Gains through children, creativity or markets.",
        "Gains come after effort — earned, never gifted.",
        "Gains through partnerships and public dealing.",
        "Gains through research, others' money or sudden turns.",
        "Gains through higher learning and long journeys.",
        "Gains through career — reputation becomes reward.",
        "Networks multiply whatever you build.",
        "You earn well, but it leaks — invest it."]
    STRONG_WINDOW_DO_HI = [
        "इस दौर में शुरुआत करें, फैलाएँ या पूँजी जुटाएँ — हवा आपके पक्ष में है।",
        "जब भरोसा ऊँचा है तभी अपने सबसे अच्छे ग्राहक और लंबे अनुबंध पक्के कर लें।",
        "शुरुआती लाभ को ख़र्च करने के बजाय कारोबार में दोबारा लगाएँ।"]
    STRONG_WINDOW_DONT_HI = [
        "सही मौक़े का इंतज़ार करते हुए बैठे न रहें — यह दौर निर्णायक क़दम को फल देता है।",
        "उम्मीद में हद से ज़्यादा क़र्ज़ न लें; हमेशा एक कामकाजी भंडार रखें।"]
    REMEDY_LINE_HI = {
        "Sun": "रविवार को: दिन को हल्का और अनुशासित रखें और “ॐ घृणि सूर्याय नमः” का जप करें। माणिक केवल विशेषज्ञ की सलाह के बाद ही विचारें।",
        "Moon": "सोमवार को: दिन को हल्का और अनुशासित रखें और “ॐ सोम सोमाय नमः” का जप करें। मोती केवल विशेषज्ञ की सलाह के बाद ही विचारें।",
        "Mars": "मंगलवार को: दिन को हल्का और अनुशासित रखें और “ॐ अं अंगारकाय नमः” का जप करें। मूँगा केवल विशेषज्ञ की सलाह के बाद ही विचारें।",
        "Mercury": "बुधवार को: दिन को हल्का और अनुशासित रखें और “ॐ बुं बुधाय नमः” का जप करें। पन्ना केवल विशेषज्ञ की सलाह के बाद ही विचारें।",
        "Jupiter": "गुरुवार को: दिन को हल्का और अनुशासित रखें और “ॐ ब्रीं बृहस्पतये नमः” का जप करें। पुखराज केवल विशेषज्ञ की सलाह के बाद ही विचारें।",
        "Venus": "शुक्रवार को: दिन को हल्का और अनुशासित रखें और “ॐ शुं शुक्राय नमः” का जप करें। हीरा केवल विशेषज्ञ की सलाह के बाद ही विचारें।",
        "Saturn": "शनिवार को: दिन को हल्का और अनुशासित रखें और “ॐ शं शनैश्चराय नमः” का जप करें। नीलम केवल विशेषज्ञ की सलाह के बाद ही विचारें।",
        "Rahu": "शनिवार को: “ॐ रां राहवे नमः” का जप करें। राहु के दौर में कोई रत्न नहीं — दिनचर्या स्थिर रखें और फ़ैसले जल्दबाज़ी में न लें।",
        "Ketu": "मंगलवार को: “ॐ कें केतवे नमः” का जप करें। केतु के दौर में कोई रत्न नहीं — स्पष्टता, समापन और सरल आदतों को तरजीह दें।"}
    _REMEDY_LINE_HI_DEFAULT = "दिनचर्या स्थिर और फ़ैसले धीरज से रखें; अनुशासन ही टिकाऊ उपाय है।"

    # ---- fit: sector by 10th lord, tilted by the stronger of Venus / Mercury ----
    tilt = ""
    vp, mp = _biz_planet_power(g["Venus"]), _biz_planet_power(g["Mercury"])
    if vp > mp and tenth_lord != "Venus":
        tilt = (" A well-placed Venus adds a creative or lifestyle edge — "
                "lean where taste and design decide the sale.")
    elif mp > vp and tenth_lord != "Mercury":
        tilt = (" A strong Mercury favours trade and quick turns — "
                "keep the deal-cycle short and the inventory moving.")
    fit_label = sector["label"]
    fit_sub = sector["sub"] + ("." + tilt if tilt else "")
    tilt_hi = ""
    if vp > mp and tenth_lord != "Venus":
        tilt_hi = (" अच्छी स्थिति में शुक्र एक रचनात्मक या लाइफ़स्टाइल बढ़त देता है — "
                   "वहाँ झुकें जहाँ पसंद और डिज़ाइन बिक्री तय करते हैं।")
    elif mp > vp and tenth_lord != "Mercury":
        tilt_hi = (" मज़बूत बुध व्यापार और तेज़ लेन-देन के हक़ में है — "
                   "सौदे का चक्र छोटा और माल चलता हुआ रखें।")
    fit_sub_hi = sector_hi["sub"] + ("." + tilt_hi if tilt_hi else "")

    # ---- full dasha tree, current period, roadmap (blueprint idioms) ----
    tree = vimshottari_tree(moon.lon, dt, today + timedelta(days=40 * 365.25))
    roadmap, active_md, active_ad, next_ad = [], None, None, None
    for md in tree:
        if md["end"] >= today and len(roadmap) < 3:
            roadmap.append({"lord": md["lord"],
                            "from": max(md["start"], today).strftime("%Y"),
                            "to": md["end"].strftime("%Y"),
                            "theme": BIZ_DASHA[md["lord"]]["body"],
                            "theme_hi": BIZ_DASHA_HI[md["lord"]]["body"],
                            "tone": BIZ_DASHA[md["lord"]]["tone"],
                            "current": md["start"] <= today <= md["end"]})
    active_md = next((m for m in tree if m["start"] <= today <= m["end"]), None)
    if active_md:
        active_ad = next((a for a in active_md["ads"] if a["start"] <= today <= a["end"]), None)
        ads = active_md["ads"]
        for i, a in enumerate(ads):
            if a is active_ad and i + 1 < len(ads):
                next_ad = ads[i + 1]
                break
        if next_ad is None:
            nmd = next((m for m in tree if m["start"] > today), None)
            if nmd and nmd["ads"]:
                next_ad = nmd["ads"][0]

    # ---- strong window: next strongly-benefic antardasha after today ----
    def _fmt_window(a):
        s, e = a["start"], a["end"]
        left = s.strftime("%b %Y")
        right = e.strftime("%b %Y") if s.year == e.year else e.strftime("%Y")
        return f"{left} – {right}"

    strong_ad = None
    future_ads = [a for m in tree for a in m["ads"] if a["end"] > today]
    future_ads.sort(key=lambda a: a["start"])
    # prefer the earliest AD (not the currently-running one) whose lord is a
    # strong business benefic; fall back to any benefic, then to the next AD.
    for a in future_ads:
        if a["start"] > today and a["lord"] in BENEFIC_BIZ:
            strong_ad = a
            break
    if strong_ad is None:
        for a in future_ads:
            if a["lord"] in BENEFIC_BIZ:
                strong_ad = a
                break
    if strong_ad is None:
        strong_ad = next_ad or (future_ads[0] if future_ads else None)
    if strong_ad is None:                                    # extreme safety net
        strong_ad = {"lord": active_md["lord"] if active_md else "Jupiter",
                     "start": today, "end": today + timedelta(days=365)}
    window_label = _fmt_window(strong_ad)
    window_lord = strong_ad["lord"]
    window_sub = BIZ_DASHA[window_lord]["body"]
    window_sub_short = BIZ_DASHA[window_lord]["body_short"]
    window_sub_hi = BIZ_DASHA_HI[window_lord]["body"]
    window_sub_short_hi = BIZ_DASHA_HI[window_lord]["body_short_hi"]

    # ---- sade sati + Jupiter/Saturn transits from Moon (blueprint idioms) ----
    sade = _sade_sati(moon.sign, today)
    import swisseph as swe_
    from engine import sidereal_lon, jd, sign_of, houses_from
    jl, _ = sidereal_lon(swe_.JUPITER, jd(today))
    sl, _ = sidereal_lon(swe_.SATURN, jd(today))
    jup_h = houses_from(moon.sign, sign_of(jl))
    sat_h = houses_from(moon.sign, sign_of(sl))
    year_ahead = {"jup_house": jup_h, "jup_good": jup_h in (1, 2, 5, 7, 9, 11),
                  "sat_house": sat_h,
                  "next_ad": {"lord": next_ad["lord"],
                              "from": next_ad["start"].strftime("%b %Y")} if next_ad else None}

    # ---- when the current hard phase lifts ----
    if sade.get("active"):
        hard_ends = sade["ends"]
    elif active_ad and BIZ_DASHA[active_ad["lord"]]["tone"] == "warn":
        hard_ends = active_ad["end"].strftime("%b %Y")
    elif active_md and BIZ_DASHA[active_md["lord"]]["tone"] == "warn":
        hard_ends = active_md["end"].strftime("%b %Y")
    else:
        hard_ends = active_ad["end"].strftime("%b %Y") if active_ad else "—"

    # ---- last ~3 years: backward read of the recent dasha ----
    frm = today - timedelta(days=int(3 * 365.25))
    last_points, last_points_hi, hard_n, seen = [], [], 0, set()
    for md in tree:
        for ad in md["ads"]:
            if ad["end"] < frm or ad["start"] > today:
                continue
            key = (md["lord"], ad["lord"])
            if key in seen:
                continue
            seen.add(key)
            d = BIZ_DASHA[ad["lord"]]
            if d["tone"] == "warn":
                hard_n += 1
            last_points.append(f"{ad['lord']} sub-period — {d['body']}.")
            last_points_hi.append(f"{_GRAHA_HI.get(ad['lord'], ad['lord'])} का उप-दौर — "
                                  f"{BIZ_DASHA_HI[ad['lord']]['body']}।")
    if hard_n >= 2:
        last_lead = ("The last three years leaned hard — the dasha sub-periods pulled "
                     "toward friction and slow cash rather than easy expansion.")
        last_lead_hi = ("पिछले तीन साल भारी रहे — दशा के उप-दौर आसान विस्तार के बजाय "
                        "रुकावट और धीमी नक़दी की ओर खींचते रहे।")
        last_lead_short = "A rough stretch pulled focus from growth."
        last_lead_short_hi = "पिछले तीन साल भारी रहे — रुकावट और धीमी नक़दी।"
    elif hard_n == 1:
        last_lead = ("The last three years were mixed — one testing sub-period sat "
                     "beside steadier ones, so momentum came in stops and starts.")
        last_lead_hi = ("पिछले तीन साल मिले-जुले रहे — एक परखने वाला उप-दौर कुछ स्थिर "
                        "दौरों के साथ रहा, इसलिए गति रुक-रुककर आई।")
        last_lead_short = "A mixed stretch — momentum came in fits."
        last_lead_short_hi = "पिछले तीन साल मिले-जुले रहे — गति रुक-रुककर आई।"
    else:
        last_lead = ("The last three years were broadly supportive — the sub-periods "
                     "favoured trade and connection more than obstruction.")
        last_lead_hi = ("पिछले तीन साल कुल मिलाकर सहायक रहे — उप-दौरों ने रुकावट से "
                        "ज़्यादा व्यापार और जुड़ाव का साथ दिया।")
        last_lead_short = "A broadly supportive few years."
        last_lead_short_hi = "पिछले तीन साल कुल मिलाकर सहायक रहे।"
    last3 = {"lead": last_lead, "lead_hi": last_lead_hi,
             "points": last_points[:4] or
             ["A quiet stretch — no single dominant sub-period drove the last three years."],
             "points_hi": last_points_hi[:4] or
             ["एक शांत दौर — पिछले तीन सालों को किसी एक प्रमुख उप-दौर ने नहीं चलाया।"]}

    # ---- years after: the upcoming mahadashas, business-framed ----
    years_after = [{"range": f"{r['from']}–{r['to']}", "tone": r["tone"],
                    "body": f"{r['lord']} Mahadasha — {r['theme']}.",
                    "body_hi": f"{_GRAHA_HI.get(r['lord'], r['lord'])} महादशा — {r['theme_hi']}।"}
                   for r in roadmap]

    # ---- careful phases: upcoming warn sub-periods (next ~5y) + sade sati ----
    careful = []
    horizon5 = today + timedelta(days=int(5 * 365.25))
    for md in tree:
        for ad in md["ads"]:
            if ad["end"] < today or ad["start"] > horizon5:
                continue
            if BIZ_DASHA[ad["lord"]]["tone"] == "warn" and ad["end"] > today:
                rng = f"{max(ad['start'], today).strftime('%b %Y')} – {ad['end'].strftime('%b %Y')}"
                careful.append({"range": rng, "range_hi": _date_hi(rng),
                                "body": f"{ad['lord']} sub-period — {BIZ_DASHA[ad['lord']]['body']}. "
                                        "Hold reserves, avoid big new leverage.",
                                "body_short": f"{ad['lord']} phase — keep reserves, avoid new debt.",
                                "body_hi": f"{_GRAHA_HI.get(ad['lord'], ad['lord'])} का उप-दौर — "
                                           f"{BIZ_DASHA_HI[ad['lord']]['body']}। भंडार बचाकर रखें, "
                                           "बड़ा नया क़र्ज़ न लें।",
                                "body_short_hi": f"{_GRAHA_HI.get(ad['lord'], ad['lord'])} का "
                                                 "दौर — बचत रखें, नया क़र्ज़ न लें।"})
    if sade.get("active"):
        careful.insert(0, {"range": f"through {sade['ends']}",
                           "range_hi": f"{_date_hi(sade['ends'])} तक",
                           "body": f"Sade Sati {sade['phase']} — Saturn is pressing your Moon. "
                                   "Consolidate, cut waste and delay the biggest bets until it lifts.",
                           "body_short": "Sade Sati — delay big bets, cut spending.",
                           "body_hi": f"साढ़े साती {_SADE_PHASE_HI.get(sade['phase'], sade['phase'])} — "
                                      "शनि आपके चंद्र पर दबाव डाल रहा है। खपत घटाएँ, फ़िज़ूलख़र्ची काटें "
                                      "और सबसे बड़े दांव तब तक टालें जब तक यह हल्का न पड़े।",
                           "body_short_hi": "साढ़े साती — बड़े दांव टालें, ख़र्च घटाएँ।"})
    careful = careful[:4] or [{"range": "next 5 years", "range_hi": "अगले 5 साल",
                               "body": "No sharply hard sub-period stands out — "
                                       "the usual discipline on cash and leverage is enough.",
                               "body_short": "No big risk — the usual cash discipline is enough.",
                               "body_hi": "कोई तीखा कठिन उप-दौर सामने नहीं है — नक़दी और "
                                          "क़र्ज़ पर सामान्य अनुशासन ही काफ़ी है।",
                               "body_short_hi": "कोई बड़ा जोखिम नहीं — बचत का सामान्य ध्यान काफ़ी।"}]

    # ---- money: earning pattern, gains pattern, reserve caution ----
    money = {
        "earn_leak": WEALTH_2L[sec_house - 1],
        "earn_leak_hi": WEALTH_2L_HI[sec_house - 1],
        "gains": GAINS_11L[ele_house - 1],
        "gains_hi": GAINS_11L_HI[ele_house - 1],
        "reserve": (f"Saturn currently transits your {sat_h}{_ordinal(sat_h)} house from the Moon — "
                    "keep a working cash reserve and avoid over-leverage until it moves on."
                    if sat_h in (1, 2, 8, 12) else
                    "Cash discipline is your steadier lever than any single big bet — "
                    "reserve first, then expand."),
        "reserve_hi": (f"शनि अभी आपके चंद्र से {_H_ORD_HI.get(sat_h, str(sat_h))} भाव में गोचर कर रहा है — "
                       "जब तक यह आगे न बढ़े, एक कामकाजी नक़दी-भंडार रखें और हद से ज़्यादा क़र्ज़ से बचें।"
                       if sat_h in (1, 2, 8, 12) else
                       "किसी एक बड़े दांव से ज़्यादा भरोसेमंद लीवर आपका नक़दी-अनुशासन है — "
                       "पहले भंडार, फिर विस्तार।")}

    # ---- remedies: obstructing planets among the business significators ----
    biz_lords = list(dict.fromkeys([tenth_lord, second_lord, eleventh_lord, seventh_lord]))
    afflicted = [lord for lord in biz_lords
                 if g[lord].dignity == "debilitated" or g[lord].combust]
    if not afflicted:
        # weakest business significator by coarse power, so the section is never empty
        afflicted = [min(biz_lords, key=lambda l: _biz_planet_power(g[l]))]
    remedies = []
    for lord in afflicted[:3]:
        remedies.append({"obstacle": BIZ_OBSTACLE.get(lord, "friction that slows the business"),
                         "obstacle_hi": BIZ_OBSTACLE_HI.get(lord, "ऐसी रुकावट जो कारोबार को धीमा करती है"),
                         "remedy": _biz_remedy_line(lord),
                         "remedy_hi": REMEDY_LINE_HI.get(lord, _REMEDY_LINE_HI_DEFAULT)})
    # add the current dasha lord's obstacle if it's a hard period and not already covered
    if active_md and BIZ_DASHA[active_md["lord"]]["tone"] == "warn" \
            and active_md["lord"] not in afflicted:
        remedies.append({"obstacle": BIZ_OBSTACLE.get(active_md["lord"], "a demanding phase"),
                         "obstacle_hi": BIZ_OBSTACLE_HI.get(active_md["lord"], "एक माँग भरा दौर"),
                         "remedy": _biz_remedy_line(active_md["lord"]),
                         "remedy_hi": REMEDY_LINE_HI.get(active_md["lord"], _REMEDY_LINE_HI_DEFAULT)})
    remedies = remedies[:3]

    # ---- year-by-year outlook for the next ~5 years ----
    year_by_year = []
    for yr in range(today.year, today.year + 5):
        probe = datetime(yr, 7, 1)
        if probe < today:
            probe = today
        ad_lord = None
        for md in tree:
            if md["start"] <= probe <= md["end"]:
                a = next((x for x in md["ads"] if x["start"] <= probe <= x["end"]), None)
                ad_lord = a["lord"] if a else md["lord"]
                break
        if ad_lord is None:
            ad_lord = active_md["lord"] if active_md else "Jupiter"
        d = BIZ_DASHA[ad_lord]
        year_by_year.append({"year": yr, "tone": d["tone"],
                             "outlook": f"{ad_lord} sub-period — {d['body']}.",
                             "outlook_hi": f"{_GRAHA_HI.get(ad_lord, ad_lord)} का उप-दौर — "
                                           f"{BIZ_DASHA_HI[ad_lord]['body']}।"})

    # ---- houses table: 2nd / 7th / 10th / 11th business houses ----
    house_notes = {2: WEALTH_2L[sec_house - 1], 7: partnership_map["verdict"],
                   10: sector["label"], 11: GAINS_11L[ele_house - 1]}
    house_notes_hi = {2: WEALTH_2L_HI[sec_house - 1], 7: partnership_map_hi["verdict"],
                      10: sector_hi["label"], 11: GAINS_11L_HI[ele_house - 1]}
    houses = []
    for h in (2, 7, 10, 11):
        lord = _hlord(h)
        houses.append({"house": h, "sign": SIGNS[_hsign(h)], "lord": lord,
                       "lord_house": _lord_house(lord), "note": house_notes[h],
                       "note_hi": house_notes_hi[h]})

    # ---- dhana yoga: do the 2nd & 11th lords combine? ----
    dy_present, dy_line, dy_line_hi = False, "", ""
    _sl_hi = _GRAHA_HI.get(second_lord, second_lord)
    _el_hi = _GRAHA_HI.get(eleventh_lord, eleventh_lord)
    if second_lord == eleventh_lord:
        dy_present = True
        dy_line = (f"One planet ({second_lord}) rules both your wealth (2nd) and gains (11th) "
                   "houses — a natural Dhana (wealth) yoga: earning and profit pull the same way.")
        dy_line_hi = (f"एक ही ग्रह ({_sl_hi}) आपके धन (द्वितीय) और लाभ (एकादश) दोनों भावों का "
                      "स्वामी है — एक स्वाभाविक धन योग: कमाई और मुनाफ़ा एक ही दिशा में खींचते हैं।")
    elif g[second_lord].sign == g[eleventh_lord].sign:
        dy_present = True
        dy_line = (f"Your 2nd lord ({second_lord}) and 11th lord ({eleventh_lord}) sit together "
                   "in one sign — a Dhana yoga where income and gains reinforce each other.")
        dy_line_hi = (f"आपका द्वितीय स्वामी ({_sl_hi}) और एकादश स्वामी ({_el_hi}) एक ही राशि में "
                      "साथ बैठे हैं — एक धन योग जहाँ आमदनी और लाभ एक-दूसरे को मज़बूत करते हैं।")
    elif g[second_lord].sign == _hsign(11) and g[eleventh_lord].sign == _hsign(2):
        dy_present = True
        dy_line = (f"Your 2nd and 11th lords ({second_lord}, {eleventh_lord}) exchange houses "
                   "(Parivartana) — a strong classical wealth combination.")
        dy_line_hi = (f"आपके द्वितीय और एकादश स्वामी ({_sl_hi}, {_el_hi}) भावों की अदला-बदली "
                      "करते हैं (परिवर्तन) — एक मज़बूत शास्त्रीय धन-संयोग।")
    else:
        dy_line = (f"Your 2nd lord ({second_lord}) and 11th lord ({eleventh_lord}) don't directly "
                   "combine — wealth builds through deliberate effort rather than an automatic yoga.")
        dy_line_hi = (f"आपका द्वितीय स्वामी ({_sl_hi}) और एकादश स्वामी ({_el_hi}) सीधे नहीं मिलते — "
                      "धन किसी स्वतः योग से नहीं, बल्कि सोचे-समझे प्रयास से बनता है।")
    dhana_yoga = {"present": dy_present, "line": dy_line, "line_hi": dy_line_hi}

    # ---- solo vs partner leaning ----
    if temperament["solo"] == "solo" and seventh_lord in ("Saturn", "Sun", "Mars"):
        solo_value = "Built to go solo"
        solo_value_hi = "अकेले चलने के लिए बना"
    elif temperament["solo"] == "partner":
        solo_value = "Better with a partner"
        solo_value_hi = "साझेदार के साथ बेहतर"
    else:
        solo_value = "Solo by nature, open to the right partner"
        solo_value_hi = "स्वभाव से अकेले, पर सही साझेदार के लिए खुले"

    # ---- current-period tone ----
    cur_lord = active_ad["lord"] if active_ad else (active_md["lord"] if active_md else "—")
    cur_tone = BIZ_DASHA.get(cur_lord, {}).get("tone", "neutral")
    cur_body = BIZ_DASHA.get(cur_lord, {}).get("body", "")
    cur_body_short = BIZ_DASHA.get(cur_lord, {}).get("body_short", "")
    cur_body_hi = BIZ_DASHA_HI.get(cur_lord, {}).get("body", "")
    cur_body_short_hi = BIZ_DASHA_HI.get(cur_lord, {}).get("body_short_hi", "")
    current_dasha = (f"{active_md['lord']} Mahadasha — {active_ad['lord']} Antardasha"
                     if active_ad else "—")
    current_dasha_hi = (f"{_GRAHA_HI.get(active_md['lord'], active_md['lord'])} महादशा — "
                        f"{_GRAHA_HI.get(active_ad['lord'], active_ad['lord'])} अंतर्दशा"
                        if active_ad else "—")

    # ---- one-breath honest paragraph ----
    hard_frame = (f"a Sade Sati squeeze that eases around {sade['ends']}"
                  if sade.get("active") else
                  f"a testing {cur_lord} phase" if cur_tone == "warn" else
                  "a steady but unspectacular stretch")
    _art = "an" if temperament["type"][:1].lower() in "aeiou" else "a"
    breath = (f"At heart you're {_art} {temperament['type'].lower()}: your money runs best through "
              f"{fit_label.lower()}, and {temperament['weak']}. "
              f"The recent road has been {hard_frame}, but {window_lord} opens a real "
              f"turning window around {strong_ad['start'].strftime('%b %Y')} — "
              "the time to build and expand, not just hold on.")

    # ---- at-a-glance summary (~8 items) ----
    last_tone = "warn" if hard_n >= 2 else ("neutral" if hard_n == 1 else "good")
    summary = [
        {"label": "Your type", "value": temperament["type"],
         "value_hi": temperament_hi["type"],
         "sub": temperament["work_short"], "sub_hi": temperament_hi["work_short_hi"], "tone": "neutral"},
        {"label": "Best-fit line", "value": fit_label, "value_hi": sector_hi["label"],
         "sub": sector["sub_short"], "sub_hi": sector_hi["sub_short_hi"], "tone": "good"},
        {"label": "Solo or partner", "value": solo_value, "value_hi": solo_value_hi,
         "sub": partnership_map["verdict_short"], "sub_hi": partnership_map_hi["verdict_short_hi"], "tone": "neutral"},
        {"label": "Last 3 years", "value": _TONE_LABEL[last_tone],
         "value_hi": _TONE_LABEL_HI[last_tone],
         "sub": last_lead_short, "sub_hi": last_lead_short_hi, "tone": last_tone},
        {"label": "Right now", "value": current_dasha, "value_hi": current_dasha_hi,
         "sub": cur_body_short or "A transitional phase.",
         "sub_hi": cur_body_short_hi or "एक बदलाव का दौर।", "tone": cur_tone},
        {"label": "When it turns", "value": window_label, "value_hi": _date_hi(window_label),
         "sub": f"{window_lord}: {window_sub_short}",
         "sub_hi": f"{_GRAHA_HI.get(window_lord, window_lord)} का उप-दौर — {window_sub_short_hi}", "tone": "good"},
        {"label": "Money", "value": ("Wealth yoga present" if dy_present else "Effort-built wealth"),
         "value_hi": ("धन योग मौजूद" if dy_present else "मेहनत से बना धन"),
         "sub": GAINS_11L_SHORT[ele_house - 1], "sub_hi": GAINS_11L_SHORT_HI[ele_house - 1], "tone": "good" if dy_present else "neutral"},
        {"label": "Be careful", "value": careful[0]["range"],
         "value_hi": careful[0]["range_hi"],
         "sub": careful[0]["body_short"], "sub_hi": careful[0]["body_short_hi"], "tone": "warn"},
    ]

    # ---- Devanagari (_hi) teaser variants for the /hi/business-growth funnel.
    # Additive: the English fields above stay the contract; business-growth.hi.html
    # reads _hi first and falls back to English. Values come from the BIZ_*_HI
    # tables; dates/planets via _date_hi/_GRAHA_HI. Same meaning, no LLM.
    # (temperament_hi/sector_hi/fit_sub_hi are computed once, higher up.) ----
    hard_frame_hi = (f"साढ़े साती का दबाव रहा जो {_date_hi(sade['ends'])} के आसपास हल्का पड़ता है"
                     if sade.get("active") else
                     f"एक कठिन {_GRAHA_HI.get(cur_lord, cur_lord)} का दौर रहा" if cur_tone == "warn"
                     else "सफ़र स्थिर पर कुछ ख़ास नहीं रहा")
    breath_hi = (f"मूल रूप से आप {temperament_hi['type']} हैं। आपका पैसा {sector_hi['label']} से "
                 f"सबसे अच्छा चलता है। हाल में {hard_frame_hi}, पर "
                 f"{_GRAHA_HI.get(window_lord, window_lord)} "
                 f"{_date_hi(strong_ad['start'].strftime('%b %Y'))} के आसपास असली मोड़ लाता है — "
                 "अब बनाने और बढ़ाने का समय है, सिर्फ़ टिके रहने का नहीं।")

    return {
        "product": "vyapar",
        "meta": {"name": name, "generated": today.strftime("%Y-%m-%d"),
                 "system": "chandra_lagna" if use_chandra else "lagna",
                 "time_quality": time_quality, "ayanamsa": "Lahiri"},
        "teaser": {
            "window_label": window_label,
            "window_sub": window_sub,
            "fit_label": fit_label,
            "fit_sub": fit_sub,
            "type_label": temperament["type"],
            "hard_ends": hard_ends,
            "breath": breath,
            # ---- Devanagari variants (Hindi funnel) ----
            "window_label_hi": _date_hi(window_label),
            "window_sub_hi": BIZ_DASHA_HI[window_lord]["body"],
            "fit_label_hi": sector_hi["label"],
            "fit_sub_hi": fit_sub_hi,
            "type_label_hi": temperament_hi["type"],
            "hard_ends_hi": _date_hi(hard_ends),
            "breath_hi": breath_hi,
        },
        "chart": {"lagna": SIGNS[ch["lagna_sign"]],
                  "planets": {p.name: {"sign": SIGNS[p.sign], "nakshatra": NAKSHATRAS[p.nak],
                                       "dignity": p.dignity, "retro": p.retro,
                                       "combust": p.combust} for p in g.values()}},
        "summary": summary,
        "nature": {"lagna_line": BIZ_TEMPERAMENT[ch["lagna_sign"]]["work"],
                   "lagna_line_hi": BIZ_TEMPERAMENT_HI[ch["lagna_sign"]]["work"],
                   "moon_line": BIZ_TEMPERAMENT[moon.sign]["gut"],
                   "moon_line_hi": BIZ_TEMPERAMENT_HI[moon.sign]["gut"],
                   "weak_spot": temperament["weak"],
                   "weak_spot_hi": temperament_hi["weak"],
                   "note_chandra": use_chandra},
        "fit": {"types": sector["types"], "types_hi": sector_hi["types"],
                "avoid": sector["avoid"], "avoid_hi": sector_hi["avoid"]},
        "partnership": {"verdict": partnership_map["verdict"],
                        "verdict_hi": partnership_map_hi["verdict"],
                        "blessing": partnership_map["blessing"],
                        "blessing_hi": partnership_map_hi["blessing"],
                        "caution": partnership_map["caution"],
                        "caution_hi": partnership_map_hi["caution"],
                        "who": partnership_map["who"],
                        "who_hi": partnership_map_hi["who"]},
        "last3": last3,
        "strong_window": {"label": window_label, "label_hi": _date_hi(window_label),
                          "body": f"{window_lord} takes over as the driving period here — "
                                  f"{window_sub}. This is your build-and-expand window.",
                          "body_hi": f"{_GRAHA_HI.get(window_lord, window_lord)} यहाँ मुख्य संचालक "
                                     f"दौर बन जाता है — {window_sub_hi}। यही आपका बनाने-और-बढ़ाने का दौर है।",
                          "do": STRONG_WINDOW_DO, "do_hi": STRONG_WINDOW_DO_HI,
                          "dont": STRONG_WINDOW_DONT, "dont_hi": STRONG_WINDOW_DONT_HI},
        "years_after": years_after,
        "careful": careful,
        "money": money,
        "remedies": remedies,
        "year_by_year": year_by_year,
        "houses": houses,
        "roadmap": roadmap,
        "sade_sati": sade,
        "year_ahead": year_ahead,
        "dhana_yoga": dhana_yoga,
    }
