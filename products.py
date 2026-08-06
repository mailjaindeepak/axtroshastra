"""
AstroShastra product engines: Kundli Milan (Ashtakoota) + Life Blueprint.
Deterministic classical tables only. Reuses chart computation from engine.py.
"""
from datetime import datetime, timedelta
from engine import (compute_chart, nak_of, vimshottari_tree, SIGNS, SIGNS_EN,
                    NAKSHATRAS, SIGN_LORD, DASHA_SEQ, DASHA_YRS, _sade_sati)
from jyotish_maps import (NAK_PROFILE, SIGN_ELEMENT, ELEMENT_PAIR, ELEMENT_HI,
                          KOOTA_TEXT, WEALTH_2L, GAINS_11L, HEALTH_6, MD_LORD_HI)

# ============================================================ ASHTAKOOTA TABLES
# Varna by moon sign (0=Shudra..3=Brahmin for hierarchy compare)
VARNA = {3:3, 7:3, 11:3,  0:2, 4:2, 8:2,  1:1, 5:1, 9:1,  2:0, 6:0, 10:0}
VARNA_NAME = {3:"Brahmin", 2:"Kshatriya", 1:"Vaishya", 0:"Shudra"}

# Vashya group by moon sign: Q quadruped, M human, J water, V wild, K insect.
# Sagittarius(8) and Capricorn(9) are classical SPLIT signs — their group
# depends on which half of the sign (0-15 deg vs 15-30 deg) the Moon falls in,
# not the sign alone. The two entries below are the front-half (0-15 deg)
# defaults; _vashya_group() overrides them for the back half. Verified against
# AstroSage's Kundli Milan (Capricorn back-half -> Chatushpad/Q), 2026-08-06.
VASHYA = {0:"Q",1:"Q",2:"M",3:"J",4:"V",5:"M",6:"M",7:"K",8:"M",9:"J",10:"M",11:"J"}


def _vashya_group(sign: int, deg_in_sign: float) -> str:
    """Vashya group for a moon sign+degree, handling the two classical split
    signs. Sagittarius: front half (0-15) Manav/human, back half (15-30)
    Chatushpad/quadruped. Capricorn: front half (0-15) Chatushpad/quadruped,
    back half (15-30) Jalachar/water — empirically matched against AstroSage's
    Kundli Milan (a Capricorn moon at 5.7 deg read as Chatushpad there),
    2026-08-06; this is the reverse of the naive "goat head is Jalachar"
    assumption. Every other sign is a single fixed group (VASHYA table)."""
    if sign == 8:
        return "M" if deg_in_sign < 15 else "Q"
    if sign == 9:
        return "Q" if deg_in_sign < 15 else "J"
    return VASHYA[sign]
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
# Standard symmetric classical Gana table (same score regardless of groom/bride
# direction): Deva-Manushya=5, Deva-Rakshasa=0, Manushya-Rakshasa=0. Verified
# against AstroSage's Kundli Milan on 3 independent real pairs (accuracy test,
# 2026-08-06) — a prior asymmetric variant here scored (M,D)=6 and (D,R)=1,
# both of which disagreed with AstroSage.
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
        moons.append({"sign": m.sign, "nak": m.nak, "pada": m.pada, "deg": m.lon % 30})

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

    vg, vb = _vashya_group(g["sign"], g["deg"]), _vashya_group(b["sign"], b["deg"])
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
                   "chapters": 6},
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
    }
