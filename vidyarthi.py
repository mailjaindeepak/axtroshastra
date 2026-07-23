"""
Axtroshastra Student Career & Academic Timing Engine (/padhai)
================================================================
Deterministic Jyotish computation. No LLM anywhere in this file.
Mirrors engine.py's marriage-timing pipeline exactly, swapping the 7th house
(marriage) for the classical education/career houses: 4th (foundation in
study), 5th (intelligence, exam success), 9th (higher education, luck/guru),
10th (career rise). Karakas are Mercury (intellect), Jupiter (wisdom), and
Saturn (discipline, hard-won success — included deliberately, not as a pure
malefic, so the report can be honest about hardship while framing it as
correctable through effort).

Pipeline: compute_vidyarthi_report(input) -> full JSON
  1. chart()                  reused as-is from engine.py
  2. vimshottari()            reused as-is from engine.py
  3. student_significators()  4th/5th/9th/10th lords, karakas
  4. windows()                score every AD in horizon, transit gate, grade
  5. assemble JSON with time_quality tier handling (T0/T1/T2/T3)

NOTE for review: the RULES_STUDY point values below are a first,
classically-grounded draft (the four houses used are the standard, uncontested
Jyotish houses for education/career). Like engine.py's own RULES table, the
exact weights benefit from a domain review/tuning pass before being fully
trusted as a paid product feature.
"""
import swisseph as swe
from datetime import datetime, timedelta

from engine import (
    compute_chart, vimshottari_tree, houses_from, aspects_house,
    sidereal_lon, sign_of, jd, SIGN_LORD, SIGNS, SIGNS_EN, NAKSHATRAS,
    DASHA_SEQ, DASHA_YRS, grade, _sade_sati,
)
from jyotish_maps import REMEDY_7L
from products import CAREER_HOUSE, CAREER_ARCHETYPE, PLANET_GIFT, PLANET_LESSON
from vidyarthi_maps import (STUDY_HOUSE, EXAM_HOUSE, HIGHERED_HOUSE, HARDSHIP_LINE,
                            STAGE_LABEL, FIELD_NOTE, FOLLOWTHROUGH_TEXT, FACTOR_ADVICE)

# Uccha Bala (a real Shadbala sub-component): continuous 0-100 strength from
# the planet's EXACT degree-distance to its classical exaltation point (100)
# vs. its debilitation point, exactly 180 degrees opposite (0). Values below
# are the standard classical exaltation degrees, expressed as absolute
# ecliptic longitude (sign_index*30 + degree-in-sign, SIGNS order Mesha=0):
# Sun 10 Mesha, Moon 3 Vrishabha, Mars 28 Makara, Mercury 15 Kanya,
# Jupiter 5 Karka, Venus 27 Meena, Saturn 20 Tula.
#
# This replaces an earlier version that scored off engine.py's `dignity`
# flag (own/exalted/debilitated/neutral -- 4 buckets total). That collapsed
# every "neutral" placement -- roughly two-thirds of all possible sign
# placements for any given planet -- onto one identical score, so most
# factors converged on the same number across different people's charts
# (a real, confirmed bug: 15/25 random test charts shared a duplicate
# 5-factor score profile). Uccha Bala is degree-based, so it varies
# continuously and is effectively unique per birth moment.
EXALT_DEG = {"Sun": 10.0, "Moon": 33.0, "Mars": 298.0, "Mercury": 165.0,
            "Jupiter": 95.0, "Venus": 357.0, "Saturn": 200.0}
DIGNITY_SCORE_FALLBACK = {"exalted": 92, "own": 82, "neutral": 68, "debilitated": 30}  # Rahu/Ketu safety net
COMBUST_PENALTY = 15
WATCH_THRESHOLD = 50

KEY_HOUSES = (4, 5, 9, 10)          # used for the DESCRIPTIVE reads (study/exam/higher-ed/career text)
TIMING_HOUSES = (10, 11)            # used for WINDOW TIMING only — career rise + gains, the direct
                                     # analogue of marriage's single-house (7th) focus. Scoring against
                                     # all 4 KEY_HOUSES made almost every antardasha "qualify" (they
                                     # overlap too much), producing windows that merged into one
                                     # multi-decade span instead of a real, narrow breakthrough window.


# ---------------------------------------------------------------- significators
def student_significators(chart: dict, ref_sign: int) -> dict:
    """ref_sign = lagna sign (T0/T1) or Moon sign (Chandra lagna, T2/T3)."""
    g = chart["grahas"]
    house_sign = {h: (ref_sign + h - 1) % 12 for h in KEY_HOUSES + (11,)}
    house_lord = {h: SIGN_LORD[house_sign[h]] for h in KEY_HOUSES + (11,)}
    key_lords = list(dict.fromkeys(house_lord[h] for h in KEY_HOUSES))       # descriptive reads
    timing_lords = list(dict.fromkeys(house_lord[h] for h in TIMING_HOUSES))  # window timing only
    karakas = ["Mercury", "Jupiter", "Saturn"]
    return {
        "ref_sign": ref_sign,
        "fourth_sign": house_sign[4], "fourth_lord": house_lord[4],
        "fifth_sign": house_sign[5], "fifth_lord": house_lord[5],
        "ninth_sign": house_sign[9], "ninth_lord": house_lord[9],
        "tenth_sign": house_sign[10], "tenth_lord": house_lord[10],
        "eleventh_sign": house_sign[11], "eleventh_lord": house_lord[11],
        "key_lords": key_lords, "timing_lords": timing_lords, "karakas": karakas,
        "fourth_lord_house": houses_from(ref_sign, g[house_lord[4]].sign),
        "fifth_lord_house": houses_from(ref_sign, g[house_lord[5]].sign),
        "ninth_lord_house": houses_from(ref_sign, g[house_lord[9]].sign),
        "tenth_lord_house": houses_from(ref_sign, g[house_lord[10]].sign),
    }


# ---------------------------------------------------------------- scoring
# NOTE: these fire against TIMING_HOUSES (10th/11th) only — the descriptive
# reads (study/exam/higher-ed) use the broader KEY_HOUSES but don't need a
# score, since they're not timed.
RULES_STUDY = [  # (rule_id, points, description)
    ("AD_IS_KEY_LORD",    2.5, "Antardasha lord rules the 10th/11th house"),
    ("MD_IS_KEY_LORD",    2.0, "Mahadasha lord rules the 10th/11th house"),
    ("AD_IS_KARAKA",      2.0, "Antardasha lord is Mercury/Jupiter/Saturn (study-career karaka)"),
    ("AD_IN_KEY_HOUSE",   2.0, "AD lord occupies or aspects the 10th/11th house"),
    ("AD_WITH_KEY_LORD",  1.5, "AD lord conjunct the 10th/11th lord"),
    ("MD_KEY_CONNECT",    1.0, "MD lord has a 10th/11th-house connection"),
    ("AD_WEAK",          -1.5, "AD lord debilitated or combust"),
    ("AD_DRY",           -1.0, "AD is Saturn/Ketu with no career-house connection"),
    ("TR_JUP_TRIG",       2.0, "Jupiter transits 1/10/11 from lagna or Moon in window"),
    ("TR_JUP_ON_10L",     1.0, "Jupiter transits over the natal 10th lord (career)"),
    ("TR_SAT_DISCIPLINE",-0.5, "Saturn sits on the 1st/10th axis for most of the window — "
                               "harder-won, not necessarily worse (see report note)"),
]
RULE_PTS = {r[0]: r[1] for r in RULES_STUDY}
RULE_DESC = {r[0]: r[2] for r in RULES_STUDY}

# Marriage timing's qualifying bar is "any grade at all" (score >= 3, engine.py's
# grade()) because scoring against one house (7th) already makes qualification
# rare. Three of the nine Vimshottari lords (Mercury/Jupiter/Saturn) are ALSO
# this engine's karakas, so AD_IS_KARAKA + MD_KEY_CONNECT alone can cross that
# bar for a third of all periods -- verified this produced a single window
# spanning nearly an entire Mahadasha (contiguous "qualifying" antardashas all
# merge). Requiring >=5 (marriage's "Moderate" tier) breaks that contiguity so
# real, narrower windows surface instead of one multi-decade span.
MIN_QUALIFY_SCORE = 5.0

# Additional safety net, independent of the scoring calibration above: even
# after narrowing to 10th/11th and raising the bar, TR_JUP_TRIG alone (Jupiter
# transiting 1/10/11 from lagna OR Moon at ANY point in a multi-year window)
# turned out to fire for almost any span, since a slow-moving Jupiter cycles
# through all houses over ~12 years -- checked against two reference points,
# it's rare for a multi-year window to NOT catch it once. Rather than keep
# re-tuning individual rule weights against one test chart, cap how long a
# single reported window is allowed to be: a "breakthrough window" a student
# can actually plan around should be a few years, not a decade-plus span.
MAX_WINDOW_DAYS = 365 * 3


def score_ad_student(chart, sig, md_lord, ad_lord, ref_sign) -> tuple:
    g = chart["grahas"]
    timing_lords = sig["timing_lords"]

    def has_timing_connection(p):
        return (p in timing_lords or
                houses_from(ref_sign, g[p].sign) in TIMING_HOUSES or
                any(aspects_house(chart, p, ref_sign, h) for h in TIMING_HOUSES))

    fired = []
    if ad_lord in timing_lords: fired.append("AD_IS_KEY_LORD")
    if md_lord in timing_lords: fired.append("MD_IS_KEY_LORD")
    if ad_lord in sig["karakas"]: fired.append("AD_IS_KARAKA")
    if houses_from(ref_sign, g[ad_lord].sign) in TIMING_HOUSES or \
       any(aspects_house(chart, ad_lord, ref_sign, h) for h in TIMING_HOUSES):
        fired.append("AD_IN_KEY_HOUSE")
    if ad_lord not in timing_lords and any(g[ad_lord].sign == g[tl].sign for tl in timing_lords):
        fired.append("AD_WITH_KEY_LORD")
    if md_lord not in timing_lords and has_timing_connection(md_lord):
        fired.append("MD_KEY_CONNECT")
    if g[ad_lord].dignity == "debilitated" or g[ad_lord].combust:
        fired.append("AD_WEAK")
    if ad_lord in ("Saturn", "Ketu") and not has_timing_connection(ad_lord):
        fired.append("AD_DRY")
    return sum(RULE_PTS[f] for f in fired), fired


def transit_gate_student(chart, sig, ref_signs, start: datetime, end: datetime) -> tuple:
    """Monthly-sampled Jupiter/Saturn transit checks over the window."""
    fired, months = [], []
    g10l = chart["grahas"][sig["tenth_lord"]]
    t, jup_hit, jup_on_10l, sat_heavy_n, n = start, False, False, 0, 0
    while t <= end:
        j = jd(t)
        jlon, _ = sidereal_lon(swe.JUPITER, j)
        slon, _ = sidereal_lon(swe.SATURN, j)
        n += 1
        for ref in ref_signs:                                # lagna and/or moon
            h = houses_from(ref, sign_of(jlon))
            if h in (1, 10, 11):
                jup_hit = True
                months.append(t.strftime("%b %Y"))
        if abs((jlon - g10l.lon + 180) % 360 - 180) < 8.0:
            jup_on_10l = True
        sat_h = houses_from(ref_signs[0], sign_of(slon))
        if sat_h in (1, 10):
            sat_heavy_n += 1
        t += timedelta(days=30)
    if jup_hit: fired.append("TR_JUP_TRIG")
    if jup_on_10l: fired.append("TR_JUP_ON_10L")
    if n and sat_heavy_n / n > 0.5: fired.append("TR_SAT_DISCIPLINE")
    return fired, months[:4]


# ---------------------------------------------------------------- extras
def _hardship_and_remedy(chart, sig):
    """Identify the weakest of the 4 key lords and pair it with a remedy —
    honest about the hardship, framed as correctable through discipline."""
    g = chart["grahas"]
    weakest = None
    for lord in sig["key_lords"]:
        p = g[lord]
        if p.dignity == "debilitated" or p.combust:
            weakest = lord
            break
    if weakest is None:
        return {"has_hardship": False, "line": HARDSHIP_LINE.get("_none")}
    fast, mantra, gem = REMEDY_7L.get(weakest, REMEDY_7L["Jupiter"])
    gem_ok = g[weakest].dignity != "debilitated" and not g[weakest].combust
    return {
        "has_hardship": True, "lord": weakest,
        "line": HARDSHIP_LINE.get(weakest, HARDSHIP_LINE["_none"]),
        "fast_day": fast, "mantra": mantra,
        "gem": gem if gem_ok else None,
        "gem_note": None if gem_ok else
            f"{weakest} ki current condition mein gemstone recommend nahi karte — "
            f"mantra aur fast se discipline build hoti hai, yehi sabse durable remedy hai.",
    }


def _study_career_reads(chart, sig):
    g = chart["grahas"]
    return {
        "study_strength": STUDY_HOUSE[sig["fourth_lord_house"] - 1],
        "exam_strength": EXAM_HOUSE[sig["fifth_lord_house"] - 1],
        "higher_education": HIGHERED_HOUSE[sig["ninth_lord_house"] - 1],
        "career_direction": CAREER_HOUSE[sig["tenth_lord_house"] - 1],
        "career_archetype": CAREER_ARCHETYPE[sig["tenth_lord_house"] - 1],
        "natural_gift": next((f"{p.name} — {PLANET_GIFT[p.name]}"
                              for p in g.values()
                              if p.dignity in ("own", "exalted") and p.name in PLANET_GIFT), None),
        "growth_lesson": next((f"{p.name} — {PLANET_LESSON[p.name]}"
                               for p in g.values()
                               if p.dignity == "debilitated" and p.name in PLANET_LESSON), None),
    }


def _dignity_score(planet) -> tuple:
    """Continuous 0-100 strength score (Uccha Bala: degree-distance from the
    planet's exact debilitation point -> 0, to its exact exaltation point ->
    100), minus a combustion penalty. Feeds the 5-factor and career-ranking
    percentages so every number on the report traces back to a real,
    per-degree chart placement -- not a coarse dignity bucket."""
    exalt = EXALT_DEG.get(planet.name)
    if exalt is None:  # Rahu/Ketu have no classical exaltation degree in this system
        score = float(DIGNITY_SCORE_FALLBACK[planet.dignity])
    else:
        debil = (exalt + 180) % 360
        score = abs((planet.lon - debil + 180) % 360 - 180) / 180 * 100
    if planet.combust:
        score = max(5, score - COMBUST_PENALTY)
    score = round(score)
    status = "strong" if score >= WATCH_THRESHOLD else "watch"
    return score, status


def _five_factors(chart, sig) -> list:
    """The report's 5 core factors, strongest-first. Each is scored from the
    dignity of the classical house-lord that governs it (Saturn's own dignity
    for Follow-Through, since that factor isn't house-lord dependent)."""
    g = chart["grahas"]
    items = []
    for key, emoji, label, lord, house, expl in (
        ("study", "🧠", "Study Habits", sig["fourth_lord"], sig["fourth_lord_house"],
         STUDY_HOUSE[sig["fourth_lord_house"] - 1]),
        ("exam", "🎯", "Exam & Performance", sig["fifth_lord"], sig["fifth_lord_house"],
         EXAM_HOUSE[sig["fifth_lord_house"] - 1]),
        ("highered", "🎓", "Higher Education Luck", sig["ninth_lord"], sig["ninth_lord_house"],
         HIGHERED_HOUSE[sig["ninth_lord_house"] - 1]),
        ("career", "🧭", "Career Direction", sig["tenth_lord"], sig["tenth_lord_house"],
         CAREER_HOUSE[sig["tenth_lord_house"] - 1]),
    ):
        score, status = _dignity_score(g[lord])
        items.append({"key": key, "emoji": emoji, "label": label, "lord": lord, "house": house,
                     "score": score, "status": status, "explanation": expl,
                     "advice": FACTOR_ADVICE[key] if status == "watch" else None})
    sat_score, sat_status = _dignity_score(g["Saturn"])
    items.append({"key": "followthrough", "emoji": "💪", "label": "Follow-Through", "lord": "Saturn",
                 "house": None, "score": sat_score, "status": sat_status,
                 "explanation": FOLLOWTHROUGH_TEXT[g["Saturn"].dignity],
                 "advice": FACTOR_ADVICE["followthrough"] if sat_status == "watch" else None})
    items.sort(key=lambda f: -f["score"])
    return items


def _career_candidates(chart, sig) -> list:
    """Up to 3 distinct career archetypes, ranked by the dignity-strength of
    the significator that points to each -- 10th lord (career action), 11th
    lord (gains/network), Sun (authority/soul-purpose), with 5th/4th lord as
    fallback significators if those three collide on the same house. Same
    CAREER_ARCHETYPE table as the single-archetype read, just scored and
    ranked instead of only taking the top one."""
    g = chart["grahas"]
    ref = sig["ref_sign"]
    raw = [
        (sig["tenth_lord"], sig["tenth_lord_house"]),
        (sig["eleventh_lord"], houses_from(ref, g[sig["eleventh_lord"]].sign)),
        ("Sun", houses_from(ref, g["Sun"].sign)),
        (sig["fifth_lord"], sig["fifth_lord_house"]),
        (sig["fourth_lord"], sig["fourth_lord_house"]),
    ]
    seen, out = set(), []
    for lord, house in raw:
        if house in seen:
            continue
        seen.add(house)
        score, _ = _dignity_score(g[lord])
        out.append({"archetype": CAREER_ARCHETYPE[house - 1], "lord": lord, "house": house, "score": score})
    out.sort(key=lambda c: -c["score"])
    return out[:3]


def _stage_field_note(stage, field, career_direction):
    """Students still DECIDING (10th/12th) get general direction only -- no
    named fields, per design decision. Students already committed (college/
    postgrad) get a short field-specific note if they picked a field."""
    if stage in ("10th", "12th"):
        return ("At your stage the useful signal is direction, not a named field yet: "
                f"{career_direction}.")
    if stage in ("college", "postgrad") and field:
        return FIELD_NOTE.get(field, FIELD_NOTE["Other"])
    return None


def vidyarthi_extras(chart, sig, today, stage=None, field=None):
    g = chart["grahas"]; moon = g["Moon"]
    extras = {"sade_sati": _sade_sati(moon.sign, today)}
    extras.update(_hardship_and_remedy(chart, sig))
    extras.update(_study_career_reads(chart, sig))
    extras["five_factors"] = _five_factors(chart, sig)
    extras["career_candidates"] = _career_candidates(chart, sig)
    extras["stage"] = stage
    extras["stage_label"] = STAGE_LABEL.get(stage)
    extras["field"] = field
    extras["stage_note"] = _stage_field_note(stage, field, extras["career_direction"])
    return extras


# ---------------------------------------------------------------- main pipeline
def compute_vidyarthi_report(name: str, dob: str, tob: str, tz_offset_hours: float,
                             lat: float, lon_geo: float, female: bool = False,
                             time_quality: str = "T0", horizon_years: int = 10,
                             min_age: int = 10, as_of: datetime = None,
                             stage: str = None, field: str = None) -> dict:
    """
    dob 'YYYY-MM-DD', tob 'HH:MM' local (for T2/T3 pass band midpoint / 12:00).
    time_quality: T0 exact | T1 approx +-45m | T2 band +-3h | T3 unknown.
    min_age is lower than marriage's default (10 vs 21) because academic/exam
    breakthrough windows meaningfully start in the teenage years.
    stage: "10th" | "12th" | "college" | "postgrad" (optional). field: one of
    FIELD_NOTE's keys, only meaningful when stage is "college"/"postgrad".
    """
    local = datetime.fromisoformat(f"{dob}T{tob}:00")
    dt_utc = local - timedelta(hours=tz_offset_hours)
    today = as_of or datetime.utcnow()
    horizon_end = today + timedelta(days=horizon_years * 365.25)

    chart = compute_chart(dt_utc, lat, lon_geo)
    use_chandra = time_quality in ("T2", "T3")

    if time_quality == "T1":
        for dm in (-45, 45):
            alt = compute_chart(dt_utc + timedelta(minutes=dm), lat, lon_geo)
            if alt["lagna_sign"] != chart["lagna_sign"]:
                use_chandra = True
                break

    two_timelines = False
    if time_quality == "T3":
        n0 = _moon_nak(chart, local, tz_offset_hours, lat, lon_geo, "00:00:00")
        n1 = _moon_nak(chart, local, tz_offset_hours, lat, lon_geo, "23:59:00")
        two_timelines = (n0 != n1)

    ref_sign = chart["grahas"]["Moon"].sign if use_chandra else chart["lagna_sign"]
    ref_signs_for_transit = [ref_sign] if use_chandra else \
        [chart["lagna_sign"], chart["grahas"]["Moon"].sign]

    ERR_H = {"T0": 0.25, "T1": 0.75, "T2": 3.0, "T3": 5.0}[time_quality]
    nak_idx = _nak_index(chart["grahas"]["Moon"].lon)
    birth_md_lord = DASHA_SEQ[nak_idx % 9]
    pad_days = int(ERR_H * 0.041 * DASHA_YRS[birth_md_lord] * 365.25)

    sig = student_significators(chart, ref_sign)
    tree = vimshottari_tree(chart["grahas"]["Moon"].lon, dt_utc, horizon_end)

    birth_date, candidates = local, []
    for md in tree:
        for ad in md["ads"]:
            if ad["end"] < today or ad["start"] > horizon_end:
                continue
            if (ad["end"] - birth_date).days / 365.25 < min_age:
                continue
            s, fired = score_ad_student(chart, sig, md["lord"], ad["lord"], ref_sign)
            if s >= 3:
                tf, peak = transit_gate_student(chart, sig, ref_signs_for_transit,
                                                max(ad["start"], today), ad["end"])
                s += sum(RULE_PTS[f] for f in tf)
                fired += tf
            else:
                peak = []
            candidates.append({"md": md["lord"], "ad": ad["lord"],
                               "start": ad["start"], "end": ad["end"],
                               "score": round(s, 1), "rules": fired, "peak_months": peak})

    qualifying = sorted([c for c in candidates if c["score"] >= MIN_QUALIFY_SCORE],
                        key=lambda c: c["start"])
    if not qualifying:
        best = sorted(candidates, key=lambda c: -c["score"])[:2]
        for b in best: b["score"] = max(b["score"], 3.0)
        qualifying = sorted(best, key=lambda c: c["start"])
    merged = []
    for c in qualifying:
        if merged and (c["start"] - merged[-1]["end"]).days < 120 and \
           (c["end"] - merged[-1]["start"]).days <= MAX_WINDOW_DAYS:
            m = merged[-1]
            m["end"] = c["end"]; m["score"] = max(m["score"], c["score"])
            m["rules"] = list(dict.fromkeys(m["rules"] + c["rules"]))
            m["peak_months"] += c["peak_months"]
            m["ad"] += f" + {c['ad']}"
        else:
            merged.append(dict(c))
    windows = sorted(merged, key=lambda c: -c["score"])[:3]
    windows = sorted(windows, key=lambda c: c["start"])

    # Pad each window's displayed range, then clamp so adjacent windows never
    # visually overlap -- padding is symmetric per window, but two windows
    # close together (e.g. consecutive ADs in the same MD) could otherwise
    # have window N's padded end fall after window N+1's padded start, which
    # reads as a data error to anyone looking at the dates.
    padded_start = [w["start"] - timedelta(days=pad_days) for w in windows]
    padded_end = [w["end"] + timedelta(days=pad_days) for w in windows]
    for i in range(1, len(windows)):
        if padded_start[i] < padded_end[i - 1]:
            midpoint = windows[i - 1]["end"] + (windows[i]["start"] - windows[i - 1]["end"]) / 2
            padded_end[i - 1] = min(padded_end[i - 1], midpoint)
            padded_start[i] = max(padded_start[i], midpoint)

    grade_cap = "Moderate" if time_quality in ("T2", "T3") else "Strong"
    out_windows = []
    for i, w in enumerate(windows):
        g_ = grade(w["score"]) or "Building"
        if grade_cap == "Moderate" and g_ == "Strong": g_ = "Moderate"
        out_windows.append({
            "start": padded_start[i].strftime("%Y-%m"),
            "end": padded_end[i].strftime("%Y-%m"),
            "core_start": w["start"].strftime("%Y-%m"),
            "core_end": w["end"].strftime("%Y-%m"),
            "grade": g_, "score": w["score"],
            "dasha": f"{w['md']} MD — {w['ad']} AD",
            "rules_fired": [{"id": r, "why": RULE_DESC[r]} for r in w["rules"]],
            "peak_months": list(dict.fromkeys(w["peak_months"]))[:3]})

    g = chart["grahas"]
    moon = g["Moon"]
    active_md = next((m for m in tree if m["start"] <= today <= m["end"]), None)
    active_ad = next((a for a in active_md["ads"] if a["start"] <= today <= a["end"]),
                     None) if active_md else None

    extras = vidyarthi_extras(chart, sig, today, stage=stage, field=field)

    return {
        "product": "vidyarthi",
        "extras": extras,
        "meta": {"name": name, "generated": today.strftime("%Y-%m-%d"),
                 "time_quality": time_quality, "system": "chandra_lagna" if use_chandra else "lagna",
                 "window_padding_days": pad_days, "two_timelines_detected": two_timelines,
                 "ayanamsa": "Lahiri", "houses": "whole_sign"},
        "teaser": {                                       # ONLY this goes to browser pre-payment
            "moon_sign": SIGNS[moon.sign], "moon_sign_en": SIGNS_EN[moon.sign],
            "nakshatra": NAKSHATRAS[moon.nak], "pada": moon.pada,
            "current_dasha": f"{active_md['lord']} Mahadasha — {active_ad['lord']} Antardasha"
                             if active_ad else "—",
            "dasha_till": active_ad["end"].strftime("%b %Y") if active_ad else "—",
            "windows_count": len(out_windows),
            "first_window_teaser": out_windows[0]["start"][:4] + "–" +
                                   out_windows[0]["end"][:4] if out_windows else "—",
            "timeline_hints": [
                {"left_pct": round(max(0, (datetime.strptime(w["start"], "%Y-%m")
                     - today).days / (horizon_years * 365.25)) * 100, 1),
                 "width_pct": round(min(100, max(6, (datetime.strptime(w["end"], "%Y-%m")
                     - datetime.strptime(w["start"], "%Y-%m")).days
                     / (horizon_years * 365.25) * 100)), 1)}
                for w in out_windows],
            "horizon": [today.year, today.year + horizon_years]},
        "chart": {"lagna": SIGNS[chart["lagna_sign"]],
                  "planets": {p.name: {"sign": SIGNS[p.sign], "nakshatra": NAKSHATRAS[p.nak],
                                       "dignity": p.dignity, "retro": p.retro,
                                       "combust": p.combust} for p in g.values()}},
        "significators": {k: (SIGNS[v] if k in ("ref_sign", "fourth_sign", "fifth_sign",
                                                 "ninth_sign", "tenth_sign", "eleventh_sign") else v)
                          for k, v in sig.items()},
        "windows": out_windows,
        "current_period": {"md": active_md["lord"] if active_md else None,
                           "ad": active_ad["lord"] if active_ad else None,
                           "ad_end": active_ad["end"].strftime("%Y-%m-%d") if active_ad else None},
    }


def _nak_index(lon: float) -> int:
    return int(lon // (360.0 / 27.0))


def _moon_nak(chart, local, tz_offset_hours, lat, lon_geo, time_str):
    dt = (datetime.combine(local.date(), datetime.min.time())
          + timedelta(hours=int(time_str[:2]), minutes=int(time_str[3:5]))
          - timedelta(hours=tz_offset_hours))
    return _nak_index(compute_chart(dt, lat, lon_geo)["grahas"]["Moon"].lon)


if __name__ == "__main__":
    # T0 smoke test: 15 Aug 2008, 10:30 IST, Delhi (a "student" birth year)
    import json
    r = compute_vidyarthi_report("Test Student", "2008-08-15", "10:30", 5.5,
                                 28.61, 77.21, female=False, time_quality="T0")
    print(json.dumps(r, indent=2, default=str))
