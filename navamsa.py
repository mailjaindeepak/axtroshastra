"""
Navamsa (D9) computation for Axtroshastra marriage reports.
Deterministic Jyotish, no LLM. Standalone so engine.py needs only a single call.

The Navamsa (D9) divisional chart is the single most important varga for marriage
in classical Jyotish. This module derives, from the same sidereal longitudes the
main engine already computes:

  * each planet's D9 sign
  * vargottama status (same sign in D1 and D9 -> classically strengthened)
  * the D9 lagna, D9 7th sign and D9 7th lord (with its D9 dignity + house)
  * an honest strength band for the marriage promise, with a reason string

Every output is a pure function of the birth chart -- same chart, same answer.
"""

SIGNS = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
         "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena"]

# sign -> ruling planet (index aligns with SIGNS)
SIGN_LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
             "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]

# dignity references (sign indices), mirrored from engine.py so this file is standalone
OWN = {"Sun": [4], "Moon": [3], "Mars": [0, 7], "Mercury": [2, 5],
       "Jupiter": [8, 11], "Venus": [1, 6], "Saturn": [9, 10]}
EXALT = {"Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5, "Jupiter": 3, "Venus": 11, "Saturn": 6}
DEBIL = {p: (s + 6) % 12 for p, s in EXALT.items()}

SEVEN = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]


def navamsa_sign(lon: float) -> int:
    """D9 sign index (0-11) for a sidereal longitude 0-360.

    Continuous form of the classical rule: each 30 deg sign is split into nine
    3 deg20' padas; counting padas from Mesha 0 deg and taking mod 12 reproduces the
    movable/fixed/dual starting points exactly (movable -> same sign, fixed -> 9th,
    dual -> 5th).
    """
    return int((lon % 360.0) * 9.0 / 30.0) % 12


def _d9_dignity(planet: str, d9sign: int) -> str:
    if planet in OWN and d9sign in OWN[planet]:
        return "own"
    if planet in EXALT and d9sign == EXALT[planet]:
        return "exalted"
    if planet in DEBIL and d9sign == DEBIL[planet]:
        return "debilitated"
    return "neutral"


def _houses_from(ref: int, target: int) -> int:
    return ((target - ref) % 12) + 1


def navamsa_analysis(chart: dict, ref_sign: int, female: bool = False) -> dict:
    """Build the full D9 payload block.

    chart    : the dict returned by engine.compute_chart (grahas have .lon/.sign,
               plus 'lagna_lon' and 'lagna_sign').
    ref_sign : the D1 reference sign the main engine used (lagna sign for T0/T1,
               Moon sign for Chandra-lagna T2/T3). Used to find the D1 7th lord so
               its vargottama status can be reported.
    """
    grahas = chart["grahas"]

    # ---- D9 positions for every graha ----
    planets, vargottama = {}, []
    for name, g in grahas.items():
        d9s = navamsa_sign(g.lon)
        is_vgt = (d9s == g.sign)
        if is_vgt:
            vargottama.append(name)
        planets[name] = {
            "sign": SIGNS[d9s], "sign_idx": d9s,
            "vargottama": is_vgt,
            "dignity": _d9_dignity(name, d9s) if name in EXALT else "neutral",
        }

    # ---- D9 lagna and D9 7th ----
    d9_lagna = navamsa_sign(chart["lagna_lon"])
    d9_seventh = (d9_lagna + 6) % 12
    d9_seventh_lord = SIGN_LORD[d9_seventh]
    d9_7l_sign = planets[d9_seventh_lord]["sign_idx"]
    d9_7l_house = _houses_from(d9_lagna, d9_7l_sign)
    d9_7l_dignity = planets[d9_seventh_lord]["dignity"]

    # ---- D1 7th lord vargottama (marriage promise strengthener) ----
    d1_seventh = (ref_sign + 6) % 12
    d1_seventh_lord = SIGN_LORD[d1_seventh]
    seventh_lord_vargottama = planets[d1_seventh_lord]["vargottama"]
    venus_vargottama = planets["Venus"]["vargottama"]
    venus_d9_dignity = planets["Venus"]["dignity"]

    # ---- honest strength band (deterministic) ----
    score = 0
    reasons = []
    if seventh_lord_vargottama:
        score += 2
        reasons.append(f"aapka 7th lord ({d1_seventh_lord}) vargottama hai (D1 aur D9 mein ek hi rashi) — marriage promise strong")
    if venus_vargottama:
        score += 2
        reasons.append("Venus (marriage karaka) vargottama hai — sneh aur nibhaav ki strength")
    if d9_7l_dignity in ("own", "exalted"):
        score += 2
        reasons.append(f"D9 mein 7th lord ({d9_seventh_lord}) apni acchi dignity mein hai ({d9_7l_dignity})")
    if venus_d9_dignity in ("own", "exalted"):
        score += 1
        reasons.append(f"Venus D9 mein strong hai ({venus_d9_dignity})")
    if d9_7l_dignity == "debilitated":
        score -= 2
        reasons.append(f"D9 mein 7th lord ({d9_seventh_lord}) debilitated hai — timing par thoda extra dhyaan")
    if venus_d9_dignity == "debilitated":
        score -= 1
        reasons.append("Venus D9 mein debilitated hai — expression mein narmi ki zaroorat")

    if score >= 3:
        band, band_note = "strong", ("Navamsa marriage promise ko strongly support karta hai — "
                                     "yog pakka hai, sirf timing ki baat hai (upar windows dekhiye).")
    elif score <= -1:
        band, band_note = "tender", ("Navamsa thoda tender hai — iska matlab shaadi nahi hoti aisa "
                                     "nahi, balki partner-choice aur timing mein soch-samajh zyada zaroori hai. "
                                     "Yeh warning nahi, awareness hai.")
    else:
        band, band_note = "steady", ("Navamsa marriage promise ko steadily support karta hai — "
                                     "koi badi rukaawat nahi, D1 windows hi driver hain.")

    if not reasons:
        reasons.append("D9 mein koi strong plus ya minus signal nahi — neutral promise, timing D1 se aati hai.")

    return {
        "d9_lagna": SIGNS[d9_lagna], "d9_lagna_idx": d9_lagna,
        "d9_seventh_sign": SIGNS[d9_seventh],
        "d9_seventh_lord": d9_seventh_lord,
        "d9_seventh_lord_house": d9_7l_house,
        "d9_seventh_lord_dignity": d9_7l_dignity,
        "seventh_lord_vargottama": seventh_lord_vargottama,
        "d1_seventh_lord": d1_seventh_lord,
        "venus_vargottama": venus_vargottama,
        "venus_d9_sign": planets["Venus"]["sign"],
        "venus_d9_dignity": venus_d9_dignity,
        "vargottama_planets": vargottama,
        "planets": planets,
        "strength": band,
        "strength_note": band_note,
        "reasons": reasons,
    }
