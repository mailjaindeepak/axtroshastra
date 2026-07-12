"""
AstroShastra Marriage Timing Engine
====================================
Deterministic Jyotish computation. No LLM anywhere in this file.
Astronomy: pyswisseph (Moshier model — no ephemeris files needed, arc-second accuracy).
Zodiac: sidereal, Lahiri ayanamsa. Houses: whole sign from lagna.

Pipeline: compute_report(input) -> full JSON
  1. chart()          planets, lagna, nakshatras
  2. vimshottari()    MD/AD tree from Moon nakshatra balance
  3. significators()  7th lord, Venus/Jupiter, darakaraka, nodes
  4. windows()        score every AD in horizon, transit gate, grade
  5. manglik()        status + cancellations
  6. assemble JSON with time_quality tier handling (T0/T1/T2/T3)
"""

import swisseph as swe
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
import json

swe.set_sid_mode(swe.SIDM_LAHIRI)

# ---------------------------------------------------------------- constants
SIGNS = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
         "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena"]
SIGNS_EN = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
              "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
              "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha",
              "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha",
              "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
              "Uttara Bhadrapada", "Revati"]

# Vimshottari: lord sequence and years
DASHA_SEQ = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
DASHA_YRS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
             "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}
TOTAL_YRS = 120.0

# Rahu/Ketu node model. "mean" = smoothed node (classical default, used here);
# swe.TRUE_NODE = osculating node (common on Lahiri panchangs). They differ by up
# to ~2 deg, which flips Rahu's sign ~3% and its nakshatra ~7% of the time. This is
# a deliberate, documented convention -- set NODE_MODE = swe.TRUE_NODE to switch.
NODE_MODE = swe.MEAN_NODE

PLANETS = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS,
           "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, "Venus": swe.VENUS,
           "Saturn": swe.SATURN, "Rahu": NODE_MODE}  # Ketu = Rahu + 180

OWN = {"Sun": [4], "Moon": [3], "Mars": [0, 7], "Mercury": [2, 5],
       "Jupiter": [8, 11], "Venus": [1, 6], "Saturn": [9, 10]}
EXALT = {"Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5, "Jupiter": 3, "Venus": 11, "Saturn": 6}
DEBIL = {p: (s + 6) % 12 for p, s in EXALT.items()}
SIGN_LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
             "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
# Combustion orbs (degrees from the Sun). The Moon is intentionally excluded: a
# "combust Moon" (near new moon) is not used as a weakness/dignity signal here and
# only produced confusing output. Retro-specific orbs are not modelled (minor).
COMBUST_ORB = {"Mars": 17, "Mercury": 13, "Jupiter": 11, "Venus": 9, "Saturn": 15}

# Full special aspects (graha drishti), by house-count from planet
ASPECTS = {"Mars": [4, 7, 8], "Jupiter": [5, 7, 9], "Saturn": [3, 7, 10],
           "Rahu": [5, 7, 9], "Ketu": [5, 7, 9]}
DEFAULT_ASPECT = [7]

DAY_MS = 86400000.0


# ---------------------------------------------------------------- helpers
def jd(dt_utc: datetime) -> float:
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day,
                      dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600)


def sidereal_lon(planet_id: int, j: float) -> tuple:
    """Returns (longitude 0-360, speed deg/day) in sidereal zodiac."""
    pos, _ = swe.calc_ut(j, planet_id, swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED)
    return pos[0] % 360.0, pos[3]


def sign_of(lon: float) -> int:
    return int(lon // 30)


def nak_of(lon: float) -> tuple:
    """Returns (nakshatra_index 0-26, fraction_traversed 0-1, pada 1-4)."""
    span = 360.0 / 27.0
    idx = int(lon // span)
    frac = (lon % span) / span
    pada = int(frac * 4) + 1
    return idx, frac, pada


def houses_from(ref_sign: int, target_sign: int) -> int:
    """Whole-sign house count: house number of target as seen from ref (1-12)."""
    return ((target_sign - ref_sign) % 12) + 1


# ---------------------------------------------------------------- chart
@dataclass
class Graha:
    name: str
    lon: float
    sign: int
    nak: int
    pada: int
    retro: bool
    combust: bool = False
    dignity: str = "neutral"   # own / exalted / debilitated / neutral


def compute_chart(dt_utc: datetime, lat: float, lon_geo: float) -> dict:
    j = jd(dt_utc)
    grahas = {}
    for name, pid in PLANETS.items():
        lo, speed = sidereal_lon(pid, j)
        grahas[name] = Graha(name, lo, sign_of(lo), *nak_of(lo)[0:1],
                             nak_of(lo)[2], speed < 0)
    # Ketu
    klon = (grahas["Rahu"].lon + 180.0) % 360.0
    grahas["Ketu"] = Graha("Ketu", klon, sign_of(klon), nak_of(klon)[0],
                           nak_of(klon)[2], True)
    # dignity + combustion
    sun_lon = grahas["Sun"].lon
    for g in grahas.values():
        if g.name in OWN and g.sign in OWN[g.name]:
            g.dignity = "own"
        if g.name in EXALT and g.sign == EXALT[g.name]:
            g.dignity = "exalted"
        if g.name in DEBIL and g.sign == DEBIL[g.name]:
            g.dignity = "debilitated"
        if g.name in COMBUST_ORB:
            d = abs((g.lon - sun_lon + 180) % 360 - 180)
            g.combust = d <= COMBUST_ORB[g.name]

    # lagna (sidereal ascendant)
    _, ascmc = swe.houses_ex(j, lat, lon_geo, b'W', swe.FLG_SIDEREAL)
    asc = ascmc[0] % 360.0
    return {"jd": j, "grahas": grahas, "lagna_lon": asc, "lagna_sign": sign_of(asc)}


# ---------------------------------------------------------------- vimshottari
def vimshottari_tree(moon_lon: float, birth: datetime, horizon_end: datetime) -> list:
    """Full MD->AD tree from birth until horizon_end. Dates are datetimes (UTC ok)."""
    nak_idx, frac, _ = nak_of(moon_lon)
    start_lord_i = nak_idx % 9
    birth_md = DASHA_SEQ[start_lord_i]
    remaining = DASHA_YRS[birth_md] * (1.0 - frac)          # years left of birth MD

    tree, cursor = [], birth
    # first (partial) MD then cycle
    i, md_len = start_lord_i, remaining
    while cursor < horizon_end:
        md_lord = DASHA_SEQ[i % 9]
        full = DASHA_YRS[md_lord]
        md_start, md_end = cursor, cursor + timedelta(days=md_len * 365.25)
        # antardashas: proportional slices in fixed sequence starting from MD lord
        ads, ad_cursor = [], md_start
        elapsed_frac = 1.0 - (md_len / full)                # >0 only for the partial birth MD
        skip_time = elapsed_frac * full
        acc = 0.0
        for k in range(9):
            ad_lord = DASHA_SEQ[(i + k) % 9]
            ad_yrs = full * DASHA_YRS[ad_lord] / TOTAL_YRS
            if acc + ad_yrs <= skip_time + 1e-9:            # AD fully elapsed pre-birth
                acc += ad_yrs
                continue
            start_off = max(acc, skip_time)
            eff = ad_yrs - max(0.0, skip_time - acc)
            ad_start = md_start + timedelta(days=(start_off - skip_time) * 365.25)
            ad_end = ad_start + timedelta(days=eff * 365.25)
            ads.append({"lord": ad_lord, "start": ad_start, "end": ad_end})
            acc += ad_yrs
        tree.append({"lord": md_lord, "start": md_start, "end": md_end, "ads": ads,
                     "is_birth_md": (cursor == birth)})
        cursor = md_end
        i += 1
        md_len = DASHA_YRS[DASHA_SEQ[i % 9]]
    return tree


def current_period(moon_lon: float, birth_dt_utc: datetime, as_of: datetime = None) -> dict:
    """Active Mahadasha / Antardasha (and the AD end date) as of `as_of`.

    This is intentionally recomputed on demand: the current MD/AD is a moving
    target, so serving a value frozen at report-creation time goes stale. Callers
    should refresh the displayed "current period" from stored birth data each time
    a report is shown rather than trusting a stored snapshot.
    """
    today = as_of or datetime.utcnow()
    tree = vimshottari_tree(moon_lon, birth_dt_utc, today + timedelta(days=int(60 * 365.25)))
    md = next((m for m in tree if m["start"] <= today <= m["end"]), None)
    ad = next((a for a in md["ads"] if a["start"] <= today <= a["end"]), None) if md else None
    return {"md": md["lord"] if md else None,
            "ad": ad["lord"] if ad else None,
            "ad_end": ad["end"] if ad else None}


# ---------------------------------------------------------------- significators
def marriage_significators(chart: dict, ref_sign: int, female: bool) -> dict:
    """ref_sign = lagna sign (T0/T1) or Moon sign (Chandra lagna, T2/T3)."""
    g = chart["grahas"]
    seventh_sign = (ref_sign + 6) % 12
    seventh_lord = SIGN_LORD[seventh_sign]
    occupants = [p.name for p in g.values() if p.sign == seventh_sign]
    # darakaraka: lowest degree-in-sign among 7 classical planets
    seven = [g[p] for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]]
    dk = min(seven, key=lambda p: p.lon % 30).name
    karakas = ["Venus"] + (["Jupiter"] if female else [])
    return {"ref_sign": ref_sign, "seventh_sign": seventh_sign,
            "seventh_lord": seventh_lord, "seventh_occupants": occupants,
            "darakaraka": dk, "karakas": karakas,
            "node_on_7th_axis": any(g[n].sign in (seventh_sign, ref_sign) for n in ("Rahu", "Ketu")),
            "seventh_lord_dignity": g[seventh_lord].dignity,
            "seventh_lord_combust": g[seventh_lord].combust,
            "seventh_lord_house": houses_from(ref_sign, g[seventh_lord].sign)}


def aspects_house(chart: dict, planet: str, ref_sign: int, target_house: int) -> bool:
    p = chart["grahas"][planet]
    p_house = houses_from(ref_sign, p.sign)
    for a in ASPECTS.get(planet, DEFAULT_ASPECT):
        if ((p_house - 1 + (a - 1)) % 12) + 1 == target_house:
            return True
    return False


# ---------------------------------------------------------------- scoring
RULES = [  # (rule_id, points, description)
    ("AD_IS_7L",      3.0, "Antardasha lord is the 7th lord"),
    ("MD_IS_7L",      2.0, "Mahadasha lord is the 7th lord"),
    ("AD_IS_KARAKA",  2.0, "Antardasha lord is Venus/Jupiter (marriage karaka)"),
    ("AD_IN_7TH",     2.0, "AD lord occupies or aspects the 7th house"),
    ("AD_WITH_7L",    2.0, "AD lord conjunct the 7th lord"),
    ("AD_IS_DK",      1.5, "AD lord is the darakaraka"),
    ("AD_NODE_7AX",   1.5, "Node on 7th axis and AD lord is that node"),
    ("MD_7CONNECT",   1.0, "MD lord has a 7th-house connection"),
    ("AD_WEAK",      -1.5, "AD lord debilitated or combust"),
    ("AD_DRY",       -1.0, "AD is Saturn/Ketu with no 7th connection"),
    ("TR_JUP_TRIG",   2.0, "Jupiter transits 7/1/2/11 from lagna or Moon in window"),
    ("TR_JUP_ON_7L",  1.0, "Jupiter transits over natal 7th lord"),
    ("TR_SAT_HEAVY", -1.0, "Saturn sits on the 7th axis for most of the window"),
]
RULE_PTS = {r[0]: r[1] for r in RULES}
RULE_DESC = {r[0]: r[2] for r in RULES}


def score_ad(chart, sig, md_lord, ad_lord, ref_sign) -> tuple:
    g = chart["grahas"]
    fired = []
    def has_7_connection(p):
        return (p == sig["seventh_lord"] or
                houses_from(ref_sign, g[p].sign) == 7 or
                aspects_house(chart, p, ref_sign, 7) or
                g[p].sign == g[sig["seventh_lord"]].sign)
    if ad_lord == sig["seventh_lord"]: fired.append("AD_IS_7L")
    if md_lord == sig["seventh_lord"]: fired.append("MD_IS_7L")
    if ad_lord in sig["karakas"]: fired.append("AD_IS_KARAKA")
    if houses_from(ref_sign, g[ad_lord].sign) == 7 or aspects_house(chart, ad_lord, ref_sign, 7):
        fired.append("AD_IN_7TH")
    if ad_lord != sig["seventh_lord"] and g[ad_lord].sign == g[sig["seventh_lord"]].sign:
        fired.append("AD_WITH_7L")
    if ad_lord == sig["darakaraka"]: fired.append("AD_IS_DK")
    if sig["node_on_7th_axis"] and ad_lord in ("Rahu", "Ketu") and \
       g[ad_lord].sign in (sig["seventh_sign"], ref_sign):
        fired.append("AD_NODE_7AX")
    if md_lord != sig["seventh_lord"] and has_7_connection(md_lord):
        fired.append("MD_7CONNECT")
    if g[ad_lord].dignity == "debilitated" or g[ad_lord].combust:
        fired.append("AD_WEAK")
    if ad_lord in ("Saturn", "Ketu") and not has_7_connection(ad_lord):
        fired.append("AD_DRY")
    return sum(RULE_PTS[f] for f in fired), fired


def transit_gate(chart, sig, ref_signs, start: datetime, end: datetime) -> tuple:
    """Monthly-sampled Jupiter/Saturn transit checks over the window."""
    fired, months = [], []
    g7l = chart["grahas"][sig["seventh_lord"]]
    t, jup_hit, jup_on_7l, sat_heavy_n, n = start, False, False, 0, 0
    while t <= end:
        j = jd(t)
        jlon, _ = sidereal_lon(swe.JUPITER, j)
        slon, _ = sidereal_lon(swe.SATURN, j)
        n += 1
        for ref in ref_signs:                                # lagna and/or moon
            h = houses_from(ref, sign_of(jlon))
            if h in (7, 1, 2, 11):
                jup_hit = True
                months.append(t.strftime("%b %Y"))
        if abs((jlon - g7l.lon + 180) % 360 - 180) < 8.0:
            jup_on_7l = True
        sat_h = houses_from(ref_signs[0], sign_of(slon))
        if sat_h in (1, 7):
            sat_heavy_n += 1
        t += timedelta(days=30)
    if jup_hit: fired.append("TR_JUP_TRIG")
    if jup_on_7l: fired.append("TR_JUP_ON_7L")
    if n and sat_heavy_n / n > 0.5: fired.append("TR_SAT_HEAVY")
    return fired, months[:4]


# ---------------------------------------------------------------- manglik
MANGLIK_HOUSES = {1, 2, 4, 7, 8, 12}

def manglik(chart) -> dict:
    g = chart["grahas"]
    mars = g["Mars"]
    from_lagna = houses_from(chart["lagna_sign"], mars.sign) in MANGLIK_HOUSES
    from_moon = houses_from(g["Moon"].sign, mars.sign) in MANGLIK_HOUSES
    # Classical cancellations of Mangal dosha. (The earlier "Mars in Cancer/Leo"
    # rule was dropped -- it is not a standard cancellation, and Cancer is in fact
    # Mars's sign of debilitation.)
    jup = g["Jupiter"]
    cancels = []
    if mars.dignity in ("own", "exalted"):
        cancels.append("Mars in own or exalted sign")
    if jup.sign == mars.sign:
        cancels.append("Jupiter conjunct Mars")
    elif ((mars.sign - jup.sign) % 12) + 1 in (5, 7, 9):   # Jupiter's 5/7/9 drishti on Mars
        cancels.append("Jupiter aspects Mars")
    status = "manglik" if (from_lagna or from_moon) else "non_manglik"
    if status == "manglik" and cancels: status = "manglik_cancelled"
    return {"from_lagna": from_lagna, "from_moon": from_moon,
            "status": status, "cancellations": cancels}


# ---------------------------------------------------------------- main pipeline
def grade(score: float) -> str:
    if score >= 8: return "Strong"
    if score >= 5: return "Moderate"
    if score >= 3: return "Building"
    return None


def compute_report(name: str, dob: str, tob: str, tz_offset_hours: float,
                   lat: float, lon_geo: float, female: bool = False,
                   time_quality: str = "T0", horizon_years: int = 10,
                   min_age: int = 21, as_of: datetime = None) -> dict:
    """
    dob 'YYYY-MM-DD', tob 'HH:MM' local (for T2/T3 pass band midpoint / 12:00).
    time_quality: T0 exact | T1 approx ±45m | T2 band ±3h | T3 unknown.
    """
    local = datetime.fromisoformat(f"{dob}T{tob}:00")
    dt_utc = local - timedelta(hours=tz_offset_hours)
    today = as_of or datetime.utcnow()
    horizon_end = today + timedelta(days=horizon_years * 365.25)

    # ---- tier setup: which reference sign(s), window padding, D9 usage
    chart = compute_chart(dt_utc, lat, lon_geo)
    use_chandra = time_quality in ("T2", "T3")

    # T1: lagna stability check across ±45 min
    if time_quality == "T1":
        for dm in (-45, 45):
            alt = compute_chart(dt_utc + timedelta(minutes=dm), lat, lon_geo)
            if alt["lagna_sign"] != chart["lagna_sign"]:
                use_chandra = True                     # lagna unstable -> fall to Chandra
                break

    # T3: nakshatra-crossing check across the day (two-timeline case)
    two_timelines = False
    if time_quality == "T3":
        n0 = nak_of(compute_chart(datetime.combine(local.date(), datetime.min.time())
                                  - timedelta(hours=tz_offset_hours), lat, lon_geo)
                    ["grahas"]["Moon"].lon)[0]
        n1 = nak_of(compute_chart(datetime.combine(local.date(), datetime.min.time())
                                  + timedelta(hours=23, minutes=59)
                                  - timedelta(hours=tz_offset_hours), lat, lon_geo)
                    ["grahas"]["Moon"].lon)[0]
        two_timelines = (n0 != n1)

    ref_sign = chart["grahas"]["Moon"].sign if use_chandra else chart["lagna_sign"]
    ref_signs_for_transit = [ref_sign] if use_chandra else \
        [chart["lagna_sign"], chart["grahas"]["Moon"].sign]

    # window padding from dasha-shift math: err_hours * 4.1% * birth-MD years
    ERR_H = {"T0": 0.25, "T1": 0.75, "T2": 3.0, "T3": 5.0}[time_quality]
    birth_md_lord = DASHA_SEQ[nak_of(chart["grahas"]["Moon"].lon)[0] % 9]
    pad_days = int(ERR_H * 0.041 * DASHA_YRS[birth_md_lord] * 365.25)

    sig = marriage_significators(chart, ref_sign, female)
    tree = vimshottari_tree(chart["grahas"]["Moon"].lon, dt_utc, horizon_end)

    # ---- score every AD in horizon
    birth_date, candidates = local, []
    for md in tree:
        for ad in md["ads"]:
            if ad["end"] < today or ad["start"] > horizon_end:
                continue
            age_at_start = (ad["start"] - birth_date).days / 365.25
            if (ad["end"] - birth_date).days / 365.25 < min_age:
                continue                                  # age gate
            s, fired = score_ad(chart, sig, md["lord"], ad["lord"], ref_sign)
            if s >= 3:
                tf, peak = transit_gate(chart, sig, ref_signs_for_transit,
                                        max(ad["start"], today), ad["end"])
                s += sum(RULE_PTS[f] for f in tf)
                fired += tf
            else:
                peak = []
            candidates.append({"md": md["lord"], "ad": ad["lord"],
                               "start": ad["start"], "end": ad["end"],
                               "score": round(s, 1), "rules": fired, "peak_months": peak})

    # ---- select, merge adjacent (<4 months gap), never-zero fallback, cap 3
    qualifying = sorted([c for c in candidates if grade(c["score"])],
                        key=lambda c: c["start"])
    if not qualifying:                                     # never-zero rule
        best = sorted(candidates, key=lambda c: -c["score"])[:2]
        for b in best: b["score"] = max(b["score"], 3.0)   # surface as Building
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

    extras = marriage_extras(chart, sig, tree, out_windows, ref_sign,
                             ref_signs_for_transit, today)

    return {
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
            # approximate positions for the locked timeline strip (no dates/grades leak)
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
        "significators": {k: (SIGNS[v] if k in ("ref_sign", "seventh_sign") else v)
                          for k, v in sig.items()},
        "windows": out_windows,
        "manglik": manglik(chart),
        "current_period": {"md": active_md["lord"] if active_md else None,
                           "ad": active_ad["lord"] if active_ad else None,
                           "ad_end": active_ad["end"].strftime("%Y-%m-%d") if active_ad else None},
    }


if __name__ == "__main__":
    # T0 smoke test: 15 Aug 1995, 10:30 IST, Delhi
    r = compute_report("Test User", "1995-08-15", "10:30", 5.5, 28.61, 77.21,
                       female=False, time_quality="T0")
    print(json.dumps(r, indent=2, default=str))


# ================================================== REPORT EXTRAS (deterministic)
from jyotish_maps import (NAK_PROFILE, VENUS_STYLE, REMEDY_7L, SIGN_ELEMENT)

def _sade_sati(moon_sign: int, today: datetime) -> dict:
    """Saturn transit vs natal moon: 12th/1st/2nd house = rising/peak/setting."""
    sat_lon, _ = sidereal_lon(swe.SATURN, jd(today))
    rel = (sign_of(sat_lon) - moon_sign) % 12
    phase = {11: "rising (pehla charan)", 0: "peak (dusra charan)", 1: "setting (aakhri charan)"}.get(rel)
    if phase:
        t, end = today, None
        for _ in range(120):                       # sample monthly up to 10y
            t += timedelta(days=30)
            r2 = (sign_of(sidereal_lon(swe.SATURN, jd(t))[0]) - moon_sign) % 12
            if r2 not in (11, 0, 1):
                end = t; break
        return {"active": True, "phase": phase,
                "ends": end.strftime("%b %Y") if end else "beyond 10 years"}
    t, start = today, None
    for _ in range(360):
        t += timedelta(days=30)
        if (sign_of(sidereal_lon(swe.SATURN, jd(t))[0]) - moon_sign) % 12 == 11:
            start = t; break
    return {"active": False, "phase": None,
            "next_starts": start.strftime("%b %Y") if start else "beyond 30 years"}


def _past_analysis(chart, sig, tree, ref_sign, ref_signs_tr, today, years_back=3):
    """Backward dasha scoring: label each past AD active/quiet with reasons."""
    frm = today - timedelta(days=int(years_back * 365.25))
    out = []
    for md in tree:
        for ad in md["ads"]:
            s, e = max(ad["start"], frm), min(ad["end"], today)
            if s >= e: continue
            score, fired = score_ad(chart, sig, md["lord"], ad["lord"], ref_sign)
            if score >= 3:
                tf, _ = transit_gate(chart, sig, ref_signs_tr, s, e)
                score += sum(RULE_PTS[f] for f in tf); fired += tf
            label = "active" if score >= 5 else ("mild" if score >= 3 else "quiet")
            why = [RULE_DESC[f] for f in fired if RULE_PTS[f] > 0][:2] or \
                  ["No dasha connection to the 7th house in this period"]
            out.append({"from": s.strftime("%b %Y"), "to": e.strftime("%b %Y"),
                        "dasha": f"{md['lord']} MD — {ad['lord']} AD",
                        "label": label, "why": why})
    return out[-5:]


def _year_outlook(out_windows, tree, chart, ref_sign, today, n_years=3):
    """Per-calendar-year outlook with favourable months from window peaks."""
    years = []
    for k in range(n_years):
        y = today.year + k
        y0, y1 = datetime(y, 1, 1), datetime(y, 12, 31)
        # window overlap
        best = None
        for w in out_windows:
            ws = datetime.strptime(w["core_start"], "%Y-%m")
            we = datetime.strptime(w["core_end"], "%Y-%m")
            if ws <= y1 and we >= y0:
                if best is None or w["score"] > best["score"]: best = w
        # active dashas in the year
        ads = []
        for md in tree:
            for ad in md["ads"]:
                if ad["start"] <= y1 and ad["end"] >= y0:
                    ads.append(f"{md['lord']}–{ad['lord']}")
        # jupiter house mid-year (from moon)
        jl, _ = sidereal_lon(swe.JUPITER, jd(datetime(y, 7, 1)))
        jup_h = houses_from(chart["grahas"]["Moon"].sign, sign_of(jl))
        fav = [m for m in (best["peak_months"] if best else []) if str(y) in m]
        years.append({"year": y, "grade": best["grade"] if best else None,
                      "dashas": ads[:3], "jupiter_house_from_moon": jup_h,
                      "jupiter_supportive": jup_h in (1, 2, 5, 7, 9, 11),
                      "fav_months": fav[:3]})
    return years


def _three_checks(chart, sig, ref_sign):
    g = chart["grahas"]
    sat, seventh = g["Saturn"], sig["seventh_sign"] if isinstance(sig["seventh_sign"], int) else None
    seventh_sign = (ref_sign + 6) % 12
    late = (houses_from(ref_sign, sat.sign) == 7 or
            aspects_house(chart, "Saturn", ref_sign, 7) or
            SIGN_LORD[seventh_sign] == "Saturn" or
            g[SIGN_LORD[seventh_sign]].sign == sat.sign)
    fifth_lord = SIGN_LORD[(ref_sign + 4) % 12]
    seventh_lord = SIGN_LORD[seventh_sign]
    love = (g[fifth_lord].sign == g[seventh_lord].sign or
            houses_from(ref_sign, g["Venus"].sign) in (5, 7) or
            g[fifth_lord].sign == seventh_sign or g[seventh_lord].sign == (ref_sign + 4) % 12)
    foreign = (g["Rahu"].sign == seventh_sign or
               houses_from(ref_sign, g[seventh_lord].sign) == 12 or
               g[seventh_lord].sign == g["Rahu"].sign)
    return {"late_marriage_influence": late, "love_leaning": love, "foreign_or_intercommunity": foreign}


def marriage_extras(chart, sig, tree, out_windows, ref_sign, ref_signs_tr, today):
    g = chart["grahas"]; moon = g["Moon"]; venus = g["Venus"]
    seventh_lord = SIGN_LORD[(ref_sign + 6) % 12]
    fast, mantra, gem = REMEDY_7L[seventh_lord if seventh_lord in REMEDY_7L else "Venus"]
    gem_ok = g[seventh_lord].dignity not in ("debilitated",) and not g[seventh_lord].combust
    nakp = NAK_PROFILE[moon.nak]
    return {
        "past": _past_analysis(chart, sig, tree, ref_sign, ref_signs_tr, today),
        "year_outlook": _year_outlook(out_windows, tree, chart, ref_sign, today),
        "nak_profile": {"nakshatra": NAKSHATRAS[moon.nak], "symbol": nakp[0],
                        "nature": nakp[1], "relationship": nakp[2]},
        "venus_style": VENUS_STYLE[venus.sign] +
                       (" — Venus combust hai, isliye expression mein hesitation aa sakti hai; feelings genuine, awaaz dheemi." if venus.combust else
                        (" — Venus apne hi sign mein strong hai; pyaar mein aapki instinct par bharosa kiya ja sakta hai." if venus.dignity in ("own","exalted") else "")),
        "checks": _three_checks(chart, sig, ref_sign),
        "sade_sati": _sade_sati(moon.sign, today),
        "remedies": {"lord": seventh_lord, "fast_day": fast, "mantra": mantra,
                     "gem": gem if gem_ok else None,
                     "gem_note": None if gem_ok else
                     f"{seventh_lord} ki current condition mein gemstone recommend nahi karte — mantra aur fast kaafi hain."},
    }

# build-cache-bust force Railway rebuild so live matches main correct Vimshottari antardasha 2026-07-12
