"""
Deeper astrology: divisional charts, yogas, ashtakavarga. (#8)

Pure calculation on top of a D1 chart dict from engine.compute_chart:
    chart = {"grahas": {name: Graha(lon, sign, ...)}, "lagna_lon", "lagna_sign"}

Provides:
  navamsa_sign(lon)        -> D9 sign index (0..11)
  dasamsa_sign(lon)        -> D10 sign index
  divisional(chart)        -> D9/D10 sign of lagna + each graha
  yogas(chart)             -> list of detected classical yogas
  bhinnashtakavarga(chart, planet) -> 12-length bindu array for one planet
  sarvashtakavarga(chart)  -> 12-length combined array (grand total 337)
  analyze(chart)           -> everything above, as a JSON-friendly dict

No LLM, no randomness — consistent with the engine's determinism guarantee.
"""

SIGNS = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
         "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena"]

SIGN_LORD = {0: "Mars", 1: "Venus", 2: "Mercury", 3: "Moon", 4: "Sun", 5: "Mercury",
             6: "Venus", 7: "Mars", 8: "Jupiter", 9: "Saturn", 10: "Saturn", 11: "Jupiter"}

KENDRAS = {1, 4, 7, 10}
GRAHAS7 = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]


def _house(from_sign: int, to_sign: int) -> int:
    """House number (1..12) of to_sign counted from from_sign."""
    return ((to_sign - from_sign) % 12) + 1


# ------------------------------------------------------------------ D9 / D10
def navamsa_sign(lon: float) -> int:
    sign = int(lon // 30) % 12
    deg = lon % 30
    n = int(deg / (30 / 9))              # 0..8
    modality = sign % 3                  # 0 movable, 1 fixed, 2 dual
    start = sign if modality == 0 else ((sign + 8) % 12 if modality == 1 else (sign + 4) % 12)
    return (start + n) % 12


def dasamsa_sign(lon: float) -> int:
    sign = int(lon // 30) % 12
    deg = lon % 30
    num = int(deg / 3)                   # 0..9
    start = sign if sign % 2 == 0 else (sign + 8) % 12  # odd sign -> same, even -> 9th
    return (start + num) % 12


def divisional(chart: dict) -> dict:
    out = {"D9": {"lagna": SIGNS[navamsa_sign(chart["lagna_lon"])]},
           "D10": {"lagna": SIGNS[dasamsa_sign(chart["lagna_lon"])]}}
    for name, g in chart["grahas"].items():
        out["D9"][name] = SIGNS[navamsa_sign(g.lon)]
        out["D10"][name] = SIGNS[dasamsa_sign(g.lon)]
    return out


# ------------------------------------------------------------------ yogas
def yogas(chart: dict) -> list:
    g = chart["grahas"]
    lagna = chart["lagna_sign"]
    found = []

    def house_from_lagna(planet):
        return _house(lagna, g[planet].sign)

    # Gajakesari: Jupiter in a kendra from the Moon
    if _house(g["Moon"].sign, g["Jupiter"].sign) in KENDRAS:
        found.append({"name": "Gajakesari Yoga",
                      "detail": "Jupiter in a kendra from the Moon",
                      "effect": "Wisdom, reputation, steady rise."})

    # Budha-Aditya: Sun + Mercury in the same sign
    if g["Sun"].sign == g["Mercury"].sign:
        found.append({"name": "Budha-Aditya Yoga",
                      "detail": "Sun and Mercury conjunct",
                      "effect": "Sharp intellect, communication, analytical work."})

    # Chandra-Mangala: Moon + Mars conjunct
    if g["Moon"].sign == g["Mars"].sign:
        found.append({"name": "Chandra-Mangala Yoga",
                      "detail": "Moon and Mars conjunct",
                      "effect": "Drive and resourcefulness, earning capacity."})

    # Pancha Mahapurusha yogas: planet in own/exalted AND in a kendra from lagna
    mahapurusha = {"Mars": "Ruchaka", "Mercury": "Bhadra", "Jupiter": "Hamsa",
                   "Venus": "Malavya", "Saturn": "Sasa"}
    for planet, yname in mahapurusha.items():
        if g[planet].dignity in ("own", "exalted") and house_from_lagna(planet) in KENDRAS:
            found.append({"name": f"{yname} Yoga (Pancha Mahapurusha)",
                          "detail": f"{planet} strong ({g[planet].dignity}) in a kendra",
                          "effect": "A defining strength of personality and success."})

    # Neecha Bhanga (basic): debilitated planet whose dispositor sits in a kendra from lagna
    for planet in GRAHAS7:
        if g[planet].dignity == "debilitated":
            lord = SIGN_LORD[g[planet].sign]
            if _house(lagna, g[lord].sign) in KENDRAS:
                found.append({"name": "Neecha Bhanga Raja Yoga (indication)",
                              "detail": f"{planet} debilitated but dispositor {lord} in a kendra",
                              "effect": "Early struggle turning into notable success."})

    # Dharma-Karmadhipati: lords of the 9th and 10th associated (same sign)
    lord9 = SIGN_LORD[(lagna + 8) % 12]
    lord10 = SIGN_LORD[(lagna + 9) % 12]
    if lord9 != lord10 and g[lord9].sign == g[lord10].sign:
        found.append({"name": "Dharma-Karmadhipati Raja Yoga",
                      "detail": f"9th lord ({lord9}) and 10th lord ({lord10}) conjunct",
                      "effect": "Strong career–fortune link; leadership potential."})

    return found


# ------------------------------------------------------------ ashtakavarga
# Houses (from each reference) that grant a bindu. Classical Parashari tables.
# Per-planet totals: Sun 48, Moon 49, Mars 39, Mercury 54, Jupiter 56, Venus 52,
# Saturn 39  ->  Sarvashtakavarga grand total = 337.
_AV = {
    "Sun": {
        "Sun": [1, 2, 4, 7, 8, 9, 10, 11], "Moon": [3, 6, 10, 11],
        "Mars": [1, 2, 4, 7, 8, 9, 10, 11], "Mercury": [3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [5, 6, 9, 11], "Venus": [6, 7, 12],
        "Saturn": [1, 2, 4, 7, 8, 9, 10, 11], "Lagna": [3, 4, 6, 10, 11, 12]},
    "Moon": {
        "Sun": [3, 6, 7, 8, 10, 11], "Moon": [1, 3, 6, 7, 10, 11],
        "Mars": [2, 3, 5, 6, 9, 10, 11], "Mercury": [1, 3, 4, 5, 7, 8, 10, 11],
        "Jupiter": [1, 4, 7, 8, 10, 11, 12], "Venus": [3, 4, 5, 7, 9, 10, 11],
        "Saturn": [3, 5, 6, 11], "Lagna": [3, 6, 10, 11]},
    "Mars": {
        "Sun": [3, 5, 6, 10, 11], "Moon": [3, 6, 11],
        "Mars": [1, 2, 4, 7, 8, 10, 11], "Mercury": [3, 5, 6, 11],
        "Jupiter": [6, 10, 11, 12], "Venus": [6, 8, 11, 12],
        "Saturn": [1, 4, 7, 8, 9, 10, 11], "Lagna": [1, 3, 6, 10, 11]},
    "Mercury": {
        "Sun": [5, 6, 9, 11, 12], "Moon": [2, 4, 6, 8, 10, 11],
        "Mars": [1, 2, 4, 7, 8, 9, 10, 11], "Mercury": [1, 3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [6, 8, 11, 12], "Venus": [1, 2, 3, 4, 5, 8, 9, 11],
        "Saturn": [1, 2, 4, 7, 8, 9, 10, 11], "Lagna": [1, 2, 4, 6, 8, 10, 11]},
    "Jupiter": {
        "Sun": [1, 2, 3, 4, 7, 8, 9, 10, 11], "Moon": [2, 5, 7, 9, 11],
        "Mars": [1, 2, 4, 7, 8, 10, 11], "Mercury": [1, 2, 4, 5, 6, 9, 10, 11],
        "Jupiter": [1, 2, 3, 4, 7, 8, 10, 11], "Venus": [2, 5, 6, 9, 10, 11],
        "Saturn": [3, 5, 6, 12], "Lagna": [1, 2, 4, 5, 6, 7, 9, 10, 11]},
    "Venus": {
        "Sun": [8, 11, 12], "Moon": [1, 2, 3, 4, 5, 8, 9, 11, 12],
        "Mars": [3, 5, 6, 9, 11, 12], "Mercury": [3, 5, 6, 9, 11],
        "Jupiter": [5, 8, 9, 10, 11], "Venus": [1, 2, 3, 4, 5, 8, 9, 10, 11],
        "Saturn": [3, 4, 5, 8, 9, 10, 11], "Lagna": [1, 2, 3, 4, 5, 8, 9, 11]},
    "Saturn": {
        "Sun": [1, 2, 4, 7, 8, 10, 11], "Moon": [3, 6, 11],
        "Mars": [3, 5, 6, 10, 11, 12], "Mercury": [6, 8, 9, 10, 11, 12],
        "Jupiter": [5, 6, 11, 12], "Venus": [6, 11, 12],
        "Saturn": [3, 5, 6, 11], "Lagna": [1, 3, 4, 6, 10, 11]},
}


def _ref_signs(chart):
    signs = {name: chart["grahas"][name].sign for name in GRAHAS7}
    signs["Lagna"] = chart["lagna_sign"]
    return signs


def bhinnashtakavarga(chart: dict, planet: str) -> list:
    """12-length bindu array (indexed by sign 0..11) for one planet."""
    counts = [0] * 12
    ref_signs = _ref_signs(chart)
    for ref, houses in _AV[planet].items():
        s = ref_signs[ref]
        for h in houses:
            counts[(s + h - 1) % 12] += 1
    return counts


def sarvashtakavarga(chart: dict) -> list:
    """Combined 12-length bindu array across the seven grahas (grand total 337)."""
    total = [0] * 12
    for p in GRAHAS7:
        b = bhinnashtakavarga(chart, p)
        total = [total[i] + b[i] for i in range(12)]
    return total


def analyze(chart: dict) -> dict:
    """Everything in one JSON-friendly payload for reports/APIs."""
    sav = sarvashtakavarga(chart)
    lagna = chart["lagna_sign"]
    return {
        "divisional": divisional(chart),
        "yogas": yogas(chart),
        "sarvashtakavarga": {SIGNS[i]: sav[i] for i in range(12)},
        "sav_total": sum(sav),
        "lagna_sav_bindus": sav[lagna],
        "bhinnashtakavarga": {p: bhinnashtakavarga(chart, p) for p in GRAHAS7},
    }
