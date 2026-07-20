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
from products import CAREER_HOUSE, PLANET_GIFT, PLANET_LESSON
from vidyarthi_maps import STUDY_HOUSE, EXAM_HOUSE, HIGHERED_HOUSE, HARDSHIP_LINE

KEY_HOUSES = (4, 5, 9, 10)


# ---------------------------------------------------------------- significators
def student_significators(chart: dict, ref_sign: int) -> dict:
    """ref_sign = lagna sign (T0/T1) or Moon sign (Chandra lagna, T2/T3)."""
    g = chart["grahas"]
    house_sign = {h: (ref_sign + h - 1) % 12 for h in KEY_HOUSES}
    house_lord = {h: SIGN_LORD[house_sign[h]] for h in KEY_HOUSES}
    key_lords = list(dict.fromkeys(house_lord.values()))  # dedupe, keep order
    karakas = ["Mercury", "Jupiter", "Saturn"]
    return {
        "ref_sign": ref_sign,
        "fourth_sign": house_sign[4], "fourth_lord": house_lord[4],
        "fifth_sign": house_sign[5], "fifth_lord": house_lord[5],
        "ninth_sign": house_sign[9], "ninth_lord": house_lord[9],
        "tenth_sign": house_sign[10], "tenth_lord": house_lord[10],
        "key_lords": key_lords, "karakas": karakas,
        "fourth_lord_house": houses_from(ref_sign, g[house_lord[4]].sign),
        "fifth_lord_house": houses_from(ref_sign, g[house_lord[5]].sign),
        "ninth_lord_house": houses_from(ref_sign, g[house_lord[9]].sign),
        "tenth_lord_house": houses_from(ref_sign, g[house_lord[10]].sign),
    }


# ---------------------------------------------------------------- scoring
RULES_STUDY = [  # (rule_id, points, description)
    ("AD_IS_KEY_LORD",    2.5, "Antardasha lord rules the 4th/5th/9th/10th house"),
    ("MD_IS_KEY_LORD",    2.0, "Mahadasha lord rules the 4th/5th/9th/10th house"),
    ("AD_IS_KARAKA",      2.0, "Antardasha lord is Mercury/Jupiter/Saturn (study-career karaka)"),
    ("AD_IN_KEY_HOUSE",   2.0, "AD lord occupies or aspects a 4th/5th/9th/10th house"),
    ("AD_WITH_KEY_LORD",  1.5, "AD lord conjunct a 4th/5th/9th/10th lord"),
    ("MD_KEY_CONNECT",    1.0, "MD lord has a 4th/5th/9th/10th-house connection"),
    ("AD_WEAK",          -1.5, "AD lord debilitated or combust"),
    ("AD_DRY",           -1.0, "AD is Saturn/Ketu with no study/career-house connection"),
    ("TR_JUP_TRIG",       2.0, "Jupiter transits 1/5/9/10/11 from lagna or Moon in window"),
    ("TR_JUP_ON_10L",     1.0, "Jupiter transits over the natal 10th lord (career)"),
    ("TR_SAT_DISCIPLINE",-0.5, "Saturn sits on the 1st/10th axis for most of the window — "
                               "harder-won, not necessarily worse (see report note)"),
]
RULE_PTS = {r[0]: r[1] for r in RULES_STUDY}
RULE_DESC = {r[0]: r[2] for r in RULES_STUDY}


def score_ad_student(chart, sig, md_lord, ad_lord, ref_sign) -> tuple:
    g = chart["grahas"]
    key_lords = sig["key_lords"]

    def has_key_connection(p):
        return (p in key_lords or
                houses_from(ref_sign, g[p].sign) in KEY_HOUSES or
                any(aspects_house(chart, p, ref_sign, h) for h in KEY_HOUSES))

    fired = []
    if ad_lord in key_lords: fired.append("AD_IS_KEY_LORD")
    if md_lord in key_lords: fired.append("MD_IS_KEY_LORD")
    if ad_lord in sig["karakas"]: fired.append("AD_IS_KARAKA")
    if houses_from(ref_sign, g[ad_lord].sign) in KEY_HOUSES or \
       any(aspects_house(chart, ad_lord, ref_sign, h) for h in KEY_HOUSES):
        fired.append("AD_IN_KEY_HOUSE")
    if ad_lord not in key_lords and any(g[ad_lord].sign == g[kl].sign for kl in key_lords):
        fired.append("AD_WITH_KEY_LORD")
    if md_lord not in key_lords and has_key_connection(md_lord):
        fired.append("MD_KEY_CONNECT")
    if g[ad_lord].dignity == "debilitated" or g[ad_lord].combust:
        fired.append("AD_WEAK")
    if ad_lord in ("Saturn", "Ketu") and not has_key_connection(ad_lord):
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
            if h in (1, 5, 9, 10, 11):
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
        "natural_gift": next((f"{p.name} — {PLANET_GIFT[p.name]}"
                              for p in g.values()
                              if p.dignity in ("own", "exalted") and p.name in PLANET_GIFT), None),
        "growth_lesson": next((f"{p.name} — {PLANET_LESSON[p.name]}"
                               for p in g.values()
                               if p.dignity == "debilitated" and p.name in PLANET_LESSON), None),
    }


def vidyarthi_extras(chart, sig, today):
    g = chart["grahas"]; moon = g["Moon"]
    extras = {"sade_sati": _sade_sati(moon.sign, today)}
    extras.update(_hardship_and_remedy(chart, sig))
    extras.update(_study_career_reads(chart, sig))
    return extras


# ---------------------------------------------------------------- main pipeline
def compute_vidyarthi_report(name: str, dob: str, tob: str, tz_offset_hours: float,
                             lat: float, lon_geo: float, female: bool = False,
                             time_quality: str = "T0", horizon_years: int = 10,
                             min_age: int = 10, as_of: datetime = None) -> dict:
    """
    dob 'YYYY-MM-DD', tob 'HH:MM' local (for T2/T3 pass band midpoint / 12:00).
    time_quality: T0 exact | T1 approx +-45m | T2 band +-3h | T3 unknown.
    min_age is lower than marriage's default (10 vs 21) because academic/exam
    breakthrough windows meaningfully start in the teenage years.
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

    qualifying = sorted([c for c in candidates if grade(c["score"])],
                        key=lambda c: c["start"])
    if not qualifying:
        best = sorted(candidates, key=lambda c: -c["score"])[:2]
        for b in best: b["score"] = max(b["score"], 3.0)
        qualifying = sorted(best, key=lambda c: c["start"])
    merged = []
    for c in qualifying:
        if merged and (c["start"] - merged[-1]["end"]).days < 120:
            m = merged[-1]
            m["end"] = c["end"]; m["score"] = max(m["score"], c["score"])
            m["rules"] = list(dict.fromkeys(m["rules"] + c["rules"]))
            m["peak_months"] += c["peak_months"]
            m["ad"] += f" + {c['ad']}"
        else:
            merged.append(dict(c))
    windows = sorted(merged, key=lambda c: -c["score"])[:3]
    windows = sorted(windows, key=lambda c: c["start"])

    grade_cap = "Moderate" if time_quality in ("T2", "T3") else "Strong"
    out_windows = []
    for w in windows:
        g_ = grade(w["score"]) or "Building"
        if grade_cap == "Moderate" and g_ == "Strong": g_ = "Moderate"
        out_windows.append({
            "start": (w["start"] - timedelta(days=pad_days)).strftime("%Y-%m"),
            "end": (w["end"] + timedelta(days=pad_days)).strftime("%Y-%m"),
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

    extras = vidyarthi_extras(chart, sig, today)

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
                                                 "ninth_sign", "tenth_sign") else v)
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
