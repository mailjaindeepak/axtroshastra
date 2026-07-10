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

# Vashya group by moon sign: Q quadruped, M human, J water, V wild, K insect
VASHYA = {0:"Q",1:"Q",2:"M",3:"J",4:"V",5:"M",6:"M",7:"K",8:"M",9:"J",10:"M",11:"J"}
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

# Gana by nakshatra: D deva, M manushya, R rakshasa
GANA = "DMRMDMDDRRMMDRDRDRRMMDRRMMD"
GANA_NAME = {"D":"Deva","M":"Manushya","R":"Rakshasa"}
GANA_SCORE = {("D","D"):6,("M","M"):6,("R","R"):6,("D","M"):5,("M","D"):5,
              ("D","R"):1,("R","D"):1,("M","R"):0,("R","M"):0}

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


# ============================================================ KUNDLI MILAN
def compute_milan(p1: dict, p2: dict) -> dict:
    """p = {name, dob 'YYYY-MM-DD', tob 'HH:MM', tz, lat, lon, time_known bool}.
    p1 = groom/partner 1, p2 = bride/partner 2 (classical direction matters
    for Varna/Tara counting; UI labels them Partner 1/Partner 2)."""
    charts, moons = [], []
    for p in (p1, p2):
        dt = datetime.fromisoformat(f"{p['dob']}T{p.get('tob') or '12:00'}:00") \
             - timedelta(hours=p["tz"])
        ch = compute_chart(dt, p["lat"], p["lon"])
        charts.append(ch)
        m = ch["grahas"]["Moon"]
        moons.append({"sign": m.sign, "nak": m.nak, "pada": m.pada})

    g, b = moons[0], moons[1]
    kootas = []

    v1, v2 = VARNA[g["sign"]], VARNA[b["sign"]]
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
    s = 4 if y1 == y2 else (0 if frozenset((y1, y2)) in YONI_ENEMY else 2)
    kootas.append({"name": "Yoni", "max": 4, "score": s,
                   "detail": f"{y1} – {y2}", "meaning": "physical and instinctive harmony"})

    l1, l2 = SIGN_LORD[g["sign"]], SIGN_LORD[b["sign"]]
    s = 5 if l1 == l2 else MAITRI_SCORE[(_relation(l1, l2), _relation(l2, l1))]
    kootas.append({"name": "Graha Maitri", "max": 5, "score": s,
                   "detail": f"{l1} – {l2}", "meaning": "mental wavelength and friendship"})

    g1, g2 = GANA[g["nak"]], GANA[b["nak"]]
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
    if m1 and m2: manglik_note = ("Dono charts mein manglik placement hai — classical "
                                  "rule mein manglik-manglik pairing neutral ho jaati hai. Not an obstacle.")
    elif m1 or m2: manglik_note = ("Ek chart mein manglik placement hai (Moon-based check). "
                                   "Cancellation rules aksar apply hote hain — full lagna-based "
                                   "check ke liye exact birth times chahiye.")
    else: manglik_note = "Kisi bhi chart mein manglik dosha nahi hai (Moon-based check). ✅"

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
            "gana_preview": f"Gana: {GANA_NAME[g1]} – {GANA_NAME[g2]}",
            "score_locked": True},
        "kootas": kootas, "total": total, "max_total": 36,
        "verdict": verdict, "verdict_key": vkey,
        "cancellations": cancellations, "effective": effective,
        "effective_verdict": eff_verdict,
        "strengths": [k["name"] for k in strengths],
        "watchouts": [k["name"] for k in watchouts],
        "element": element, "nak_lines": nak_lines,
        "padas": {"p1": g["pada"], "p2": b["pada"]},
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
