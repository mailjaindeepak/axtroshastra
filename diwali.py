"""Diwali Wealth & Prosperity Report engine (product "diwali").

Deterministic astrology only, no LLM. Every chart fact comes from the shared
engine (engine.compute_report / compute_chart / vimshottari_tree / sidereal_lon,
CLAUDE.md §21); this module only maps those facts onto the Diwali payload
contract in docs/diwali/BUILD-BRIEF.md (spec §7 E1-E10, E12).

All timing is pinned to `as_of` (default Diwali day 2026-11-08), never the
clock, so the same input always gives the same payload (E1).

Month sampling: each month is read at 12:00 UTC on the 15th (the same sampling
as docs/diwali/mock/persona.json). A planet that changes sign late in a month
shows from the next month.
"""
from datetime import datetime, timedelta, date

import swisseph as swe

import engine
from engine import (PLANETS, SIGN_LORD, ASPECTS, DEFAULT_ASPECT, NAKSHATRAS,
                    sidereal_lon, sign_of, houses_from, jd, vimshottari_tree)
from jyotish_maps import REMEDY_7L, REMEDY_NODE
from divisional import bhinnashtakavarga

# ----------------------------------------------------------------- constants
# English sign names, but "Karka" for the 4th sign (R3: never the word "Cancer").
SIGN_NAMES = ["Aries", "Taurus", "Gemini", "Karka", "Leo", "Virgo",
              "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
# Fixed plain names for the houses (TIMING.md round 2). Used in "why" facts.
HOUSE_NAME = {1: "the part for yourself", 2: "the money part", 3: "the effort and courage part",
              4: "the home part", 5: "the children and planning part",
              6: "the loans and competition part", 7: "the partner part",
              8: "the shared-money part", 9: "the luck part", 10: "the work part",
              11: "the gains part", 12: "the spending part"}
ABBR = {"Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me", "Jupiter": "Ju",
        "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke"}
PLANET_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
TRANSIT_PLANETS = ["Sun", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

AREAS = ["money", "career", "business", "family", "marriage"]
AREA_LABEL = {"money": "Money", "career": "Career", "business": "Business",
              "family": "Family & children", "marriage": "Marriage", "luck": "Better luck"}
# Spec §5 "Area order" rule 4.
AREA_HOUSES = {"money": (2, 11), "career": (10, 6), "business": (7, 10, 11),
               "family": (4, 5), "marriage": (7,)}
# Spec §5 "Area order" rule 2 (situation table). No life-stage rule (dropped 26 Oct).
SITUATION_ORDER = {
    "student": ["career", "money", "marriage", "family", "business"],
    "job": ["career", "money", "family", "marriage", "business"],
    "business": ["business", "money", "career", "family", "marriage"],
    "home": ["family", "money", "marriage", "career", "business"],
}
WORK_TYPES = tuple(SITUATION_ORDER)
STEERING = ("money", "career", "business", "family", "marriage", "luck")

# Spec §6 topic lists; key = "<area>.t<n>" in this order. Career/Business slots keep
# the same keys for every work type; the wording per work type belongs to the bank.
TOPICS = {
    "money": ["better after Diwali", "next good money time", "saving vs larger spending",
              "clearing loans", "recovery after a loss", "where money comes from",
              "wealth combination"],
    "career": ["next big break", "switch or stay", "asking for a raise",
               "after a job loss", "work that suits you", "work travel or abroad"],
    "business": ["business or job leaning", "start or expand", "partner or alone",
                 "deals, hiring and new account books", "go slow on new spending"],
    "family": ["home life", "family events", "house move or property", "moving city or abroad",
               "happy news"],   # 5 topics = the bank's FAMILY list and Mock 3C v2 (happy news = Q4, owner 26 Oct)
    "marriage": ["relationship tone", "important relationship decisions",
                 "care in conversations", "partnership traits", "Manglik facts"],
}

# Spec §6a, word fixes O-32 applied.
QUESTIONS = {
    "money": ["Will your financial fortunes improve after this Diwali?",
              "When could your next period of financial growth begin?",
              "Does your birth chart suggest stronger wealth-building opportunities from this Diwali to the next?",
              "Which months may call for more care with spending?",
              "Which months may be favourable for buying gold or property?"],
    "career": ["Could a career breakthrough come from this Diwali to the next?",
               "Which periods may be more favourable for professional growth?",
               "When could a good time for a job change begin?",
               "Which months may favour asking for a raise or promotion?",
               "Which months may call for steady effort, not sudden moves?"],
    "business": ["Could new growth come for your business from this Diwali to the next?",
                 "When could your next period of business profit begin?",
                 "Which months may be favourable for launching or expanding?",
                 "What does your birth chart suggest about partnerships?",
                 "Which months may call for more care with loans and credit?"],
    "family": ["Could more harmony come to your home from this Diwali to the next?",
               "Which months may suit family functions and celebrations?",
               "When could a good period for buying or moving home begin?",
               "Which months may bring happy news in your family?",
               "Which months may call for more care in family conversations?"],
    "marriage": ["Could more warmth come to your relationships from this Diwali to the next?",
                 "Which months may be favourable for important relationship decisions?",
                 "Which months may call for more care in talks with the people closest to you?",
                 "What does your birth chart suggest about partnership in your life?",
                 "Does your birth chart show Manglik, and does it matter?"],
    "luck": ["Is the period after Diwali a potential turning point in your life?",
             "Which months appear relatively favourable in your outlook?",
             "When could a fresh chapter begin for you after this Diwali?",
             "Which personal strengths could shape your next life phase?",
             "Which small habits may support your fresh start after this Diwali?"],
}
# Locked-answer teaser lines on the free preview (no month, no date, no year).
TEASERS = {
    "money": ["Your chart gives a one-word answer, what it means for you, and what to do.",
              "There is a named month when this starts for you.",
              "The planets that decide this are named in your report.",
              "Your careful months are marked, with what to hold back on.",
              "Your best months for gold, plus the Lakshmi Puja times for your city."],
    "career": ["Your chart gives a one-word answer, what it means for you, and what to do.",
               "Your good times for growth are marked month by month.",
               "There is a named month when a move suits you best.",
               "The months to ask are marked, with how to ask.",
               "Your steady-effort months are marked, with what to avoid."],
    "business": ["Your chart gives a one-word answer, what it means for you, and what to do.",
                 "There is a named month when profit may start to build.",
                 "Your months for launching or expanding are marked.",
                 "Your chart's partner part gives a clear leaning.",
                 "Your careful months for loans and credit are marked."],
    "family": ["Your chart gives a one-word answer, what it means for you, and what to do.",
               "Your best months for family functions are marked.",
               "There is a named month when a home move suits you.",
               "The months that may bring happy family news are marked.",
               "Your careful months for family talks are marked, with what helps."],
    "marriage": ["Your chart gives a one-word answer, what it means for you, and what to do.",
                 "Your good months for important decisions are marked.",
                 "Your careful months for talks are marked, with what helps.",
                 "Your partner part shows a clear tendency.",
                 "A plain facts box: the rule, and whether it applies to you."],
    "luck": ["Your turning points are named in your report.",
             "Your brightest months are marked month by month.",
             "There is a named month when a fresh chapter may begin.",
             "Your 3 strengths are named, each with one thing to do.",
             "Small habits picked for your chart, nothing to buy."],
}

DHANA_RULE = ("Our rule: a wealth combination is present when the planets that rule the part "
              "for yourself, the money part, the children and planning part, the luck part or "
              "the gains part are linked: one planet rules two of them, two of them sit in one "
              "sign, swap signs, or one looks at the other.")
GOLD_RULE = ("Our method: a month is marked when Venus or Jupiter passes the money part or the "
             "gains part of your chart, or when your current sub-period planet rules those parts.")

# Diwali 2026 (spec §5 "Diwali across India", README key dates, Drik Panchang; dates for New Delhi).
DIWALI_DAYS = [
    {"name": "Dhanteras", "date": "2026-11-06"},
    {"name": "Kali Chaudas & Tamil Deepavali", "date": "2026-11-07"},
    {"name": "Lakshmi Puja & Chopda Pujan", "date": "2026-11-08"},
    {"name": "Govardhan, Gujarati New Year & Padwa", "date": "2026-11-10"},
    {"name": "Bhai Dooj", "date": "2026-11-11"},
]
# Lakshmi Puja on Sun 8 Nov 2026 = the Vrishabha (Taurus) sthir lagna after sunset
# (Drik method). Start times for the first 6 cities: README "Key dates (Drik Panchang)";
# end times for those 6: Mock 3C table ("Times from Drik Panchang"). The last 3 are
# COMPUTED here with swisseph (sidereal ascendant 30-60 deg, Lahiri, floored to the
# minute) and are NOT hand-checked: our computation runs about 1 minute later than
# Drik on the checked cities. A human must check every row against Drik Panchang.
_DRIK = "Drik Panchang"
_COMPUTED = "computed: Vrishabha lagna after sunset, Drik method, not yet hand-checked"
PUJA_TIMES = [
    {"city": "Delhi", "start": "17:54", "end": "19:50", "source": _DRIK},
    {"city": "Mumbai", "start": "18:27", "end": "20:27", "source": _DRIK},
    {"city": "Bengaluru", "start": "18:17", "end": "20:20", "source": _DRIK},
    {"city": "Chennai", "start": "18:06", "end": "20:09", "source": _DRIK},
    {"city": "Ahmedabad", "start": "18:22", "end": "20:20", "source": _DRIK},
    {"city": "Kolkata", "start": "17:20", "end": "19:18", "source": _DRIK},
    {"city": "Pune", "start": "18:24", "end": "20:25", "source": _COMPUTED},
    {"city": "Hyderabad", "start": "18:08", "end": "20:08", "source": _COMPUTED},
    {"city": "Jaipur", "start": "18:03", "end": "20:00", "source": _COMPUTED},
]
PUJA_CITY_COORDS = {"Delhi": (28.6139, 77.2090), "Mumbai": (19.0760, 72.8777),
                    "Bengaluru": (12.9716, 77.5946), "Chennai": (13.0827, 80.2707),
                    "Ahmedabad": (23.0225, 72.5714), "Kolkata": (22.5726, 88.3639),
                    "Pune": (18.5204, 73.8567), "Hyderabad": (17.3850, 78.4867),
                    "Jaipur": (26.9124, 75.7873)}

CANCEL_PLAIN = {"Mars in own or exalted sign": "Mars sits in its own or exalted sign",
                "Jupiter conjunct Mars": "Jupiter sits with Mars",
                "Jupiter aspects Mars": "Jupiter looks at Mars"}
DIGNITY_RANK = {"exalted": 4, "own": 3, "friendly": 2, "neutral": 1, "enemy": 0.5,
                "debilitated": 0}
FRIENDS = {"Sun": {"Moon", "Mars", "Jupiter"}, "Moon": {"Sun", "Mercury"},
           "Mars": {"Sun", "Moon", "Jupiter"}, "Mercury": {"Sun", "Venus"},
           "Jupiter": {"Sun", "Moon", "Mars"}, "Venus": {"Mercury", "Saturn"},
           "Saturn": {"Mercury", "Venus"}}
ENEMIES = {"Sun": {"Venus", "Saturn"}, "Moon": set(), "Mars": {"Mercury"},
           "Mercury": {"Moon"}, "Jupiter": {"Mercury", "Venus"},
           "Venus": {"Sun", "Moon"}, "Saturn": {"Sun", "Moon", "Mars"}}

# Month scoring ("our method", spec §7 E2). Houses are counted from the basis sign
# and, with an exact time, also from the Moon (the shared engine's convention:
# compute_report uses [lagna, moon] for transits on T0/T1, Moon only on T2/T3).
BENEFIC_GOOD, BENEFIC_BAD = {1, 2, 4, 5, 7, 9, 10, 11}, {6, 8, 12}
MALEFIC_GOOD, MALEFIC_BAD = {3, 6, 11}, {8, 12}
WEIGHT = {"Jupiter": 2, "Saturn": 2, "Venus": 1, "Mars": 1, "Sun": 1, "Rahu": 1}
GOOD_AT, CAREFUL_AT, BEST_AT = 2, -3, 6     # score thresholds for month tones


# ----------------------------------------------------------------- helpers
def _ym(y, m):
    return f"{y:04d}-{m:02d}"


def _add_months(y, m, k):
    t = (y * 12 + (m - 1)) + k
    return t // 12, t % 12 + 1


def _ym_label(ym):
    y, m = int(ym[:4]), int(ym[5:])
    return f"{MONTHS[m - 1]} {y}"


def _span_len(a, b):
    return (int(b[:4]) * 12 + int(b[5:])) - (int(a[:4]) * 12 + int(a[5:])) + 1


def _range_label(yms):
    """'Jun–Jul 2027', 'Nov 2026', 'Dec 2026–Jan 2027' for a list of yms (first..last)."""
    if not yms:
        return ""
    a, b = yms[0], yms[-1]
    if a == b:
        return _ym_label(a)
    if a[:4] == b[:4]:
        return f"{MONTHS[int(a[5:]) - 1]}–{_ym_label(b)}"
    return f"{_ym_label(a)}–{_ym_label(b)}"


def _months_label(yms):
    """Label each run of consecutive months separately: 'Dec 2026–Jan 2027, Jul–Aug 2027'."""
    out = []
    for y in sorted(yms):
        n = int(y[:4]) * 12 + int(y[5:])
        if out and n == out[-1][1] + 1:
            out[-1][0].append(y)
        else:
            out.append([[y], n])
        out[-1][1] = n
    return ", ".join(_range_label(r) for r, _ in out)


def _runs(yms, ordered):
    """Split yms into runs of consecutive months following `ordered`."""
    idx = {y: i for i, y in enumerate(ordered)}
    out = []
    for y in sorted(yms, key=idx.get):
        if out and idx[y] == idx[out[-1][-1]] + 1:
            out[-1].append(y)
        else:
            out.append([y])
    return out


def _short_runs(yms, span):
    """Picture month lines in the mock's style, one per run, 2-digit year of the run's last
    month ('Nov–Dec 26', 'Dec–Jan 27', 'Jul 27'), each <= 12 chars. At most 3 lines: with
    more than 3 runs, the 2 longest (earliest on a tie) stay, in time order, + 'and more'."""
    runs = _runs(yms, span)
    if len(runs) > 3:
        runs = sorted(sorted(runs, key=lambda r: -len(r))[:2], key=lambda r: span.index(r[0]))
    out = [f"{MONTHS[int(r[0][5:]) - 1]}{'–' + MONTHS[int(r[-1][5:]) - 1] if len(r) > 1 else ''} {r[-1][2:4]}"
           for r in runs]
    return out + (["and more"] if len(_runs(yms, span)) > 3 else [])


def _easier_from(care, span):
    after = [y for y in span if y > care[-1]]
    return [f"easier from {MONTHS[int(after[0][5:]) - 1]}"] if after else []


def _strand(label, state, yms, span, caption=()):
    """One garland strand: months_label = short month lines (list), months_text = prose form,
    caption = extra short words under the months (e.g. 'talk slowly', 'easier from Jun')."""
    return {"label": label, "state": state, "months_label": _short_runs(yms, span),
            "months_text": _months_label(yms), "caption": list(caption)}


FAMILY_STRAND = ["Home life", "Family events", "House or property", "Moving or abroad", "Happy news"]


def _family_picture(tp, careful, span):
    """Mock 3C v2 family garland: one strand per topic with months, then 'Family talks' when careful."""
    pic = []
    for t, label in zip(tp, FAMILY_STRAND):
        if t["months"]:
            st = t["when"] if t["when"] in ("best", "good", "careful") else "good"
            pic.append(_strand(label, st, t["months"], span))
    if careful:
        run = _runs(careful, span)[0]
        pic.append(_strand("Family talks", "careful", run, span, _easier_from(run, span)))
    return pic


_MARRIAGE_CAPTION = {"best": ["best for", "decisions"], "good": ["plan together"], "careful": ["talk slowly"]}


def _marriage_picture(tone, span, cap=5):
    """Mock 3C v2 marriage garland: one strand per run of best/good/careful months, in time order."""
    runs = []
    for y in span:
        t = tone[y] if tone[y] in ("best", "good", "careful") else None
        if t and runs and runs[-1][0] == t and span.index(y) == span.index(runs[-1][1][-1]) + 1:
            runs[-1][1].append(y)
        elif t:
            runs.append((t, [y]))
    if len(runs) > cap:   # keep the longest runs, still in time order
        keep = sorted(sorted(range(len(runs)), key=lambda i: -len(runs[i][1]))[:cap])
        runs = [runs[i] for i in keep]
    pic = []
    for i, (t, r) in enumerate(runs):
        label = ("First months" if i == 0 else "Later months" if i == len(runs) - 1 else
                 "Next" if i == 1 else _SEASON[int(r[0][5:])].capitalize())
        pic.append(_strand(label, t, r, span,
                           _MARRIAGE_CAPTION[t] + (_easier_from(r, span) if t == "careful" else [])))
    return pic


def _positions(t):
    """Sidereal sign + retro for every transit planet at datetime t (UTC)."""
    j = jd(t)
    out = {}
    for name, pid in PLANETS.items():
        if name == "Moon":
            continue
        lon, speed = sidereal_lon(pid, j)
        out[name] = (sign_of(lon), speed < 0)
    out["Ketu"] = ((out["Rahu"][0] + 6) % 12, True)
    return out


def _aspects(planet, from_house, target_house):
    for a in ASPECTS.get(planet, DEFAULT_ASPECT):
        if ((from_house - 1 + (a - 1)) % 12) + 1 == target_house:
            return True
    return False


def _relation(planet, sign):
    lord = SIGN_LORD[sign]
    if planet not in FRIENDS or lord == planet:
        return "neutral"
    if lord in FRIENDS[planet]:
        return "friendly"
    if lord in ENEMIES[planet]:
        return "enemy"
    return "neutral"


def _age_band(age):
    return "u25" if age < 25 else "25_40" if age < 40 else "40_60" if age < 60 else "60p"


# ----------------------------------------------------------------- month scoring (E2)
def _base_score(pos, refs, basis_sign, moon_sign):
    """Returns (score, parts, reactions_flag). parts = [(points, planet, house, kind)],
    kind in in|looks|retro|sadesati."""
    parts = []
    scale = 2 if len(refs) == 1 else 1           # Moon-only reading counts once, so double it
    for p, w in WEIGHT.items():
        sign, _ = pos[p]
        pts = 0
        for ref in refs:
            h = houses_from(ref, sign)
            if p in ("Jupiter", "Venus"):
                pts += w if h in BENEFIC_GOOD else -w if h in BENEFIC_BAD else 0
            else:
                pts += w if h in MALEFIC_GOOD else -w if h in MALEFIC_BAD else 0
        parts.append((pts * scale, p, houses_from(basis_sign, sign), "in"))
    if (pos["Saturn"][0] - moon_sign) % 12 in (11, 0, 1):          # Sade Sati
        parts.append((-1, "Saturn", None, "sadesati"))
    mars_sign, mars_retro = pos["Mars"]
    reactions = mars_retro and houses_from(basis_sign, mars_sign) in (1, 7)
    if reactions:
        parts.append((-1, "Mars", houses_from(basis_sign, mars_sign), "retro"))
    return sum(x[0] for x in parts), parts, reactions


def _area_term(pos, basis_sign, area, female):
    """Area-specific transit points over that area's houses (from the basis sign)."""
    hs = AREA_HOUSES[area]
    parts = []
    for p in ("Jupiter", "Venus", "Mercury", "Saturn", "Mars", "Rahu", "Ketu", "Sun"):
        sign, retro = pos[p]
        h = houses_from(basis_sign, sign)
        pts, kind, at = 0, "in", h
        if p == "Jupiter":
            if h in hs:
                pts = 2
            else:
                hit = [x for x in hs if _aspects("Jupiter", h, x)]
                if hit:
                    pts, kind, at = 2, "looks", hit[0]
        elif h in hs:
            if p in ("Venus", "Mercury"):
                pts = 1
            elif p == "Sun":
                pts = 1 if h in (6, 10, 11) else 0
            elif p == "Mars":
                pts = 1 if h in (6, 11) else (-1 if retro else 0)
            else:                                       # Saturn, Rahu, Ketu
                pts = 1 if h in (6, 11) else -1
        if pts:
            parts.append((pts, p, at, kind))
    if area == "marriage":                               # gender branch (engine karakas)
        for k in (["Venus", "Jupiter"] if female else ["Venus"]):
            h = houses_from(basis_sign, pos[k][0])
            if h in (1, 7):
                parts.append((1, k, h, "in"))
    return sum(x[0] for x in parts), parts


def _tones(scores, flags, capped):
    """Map scores to best|good|steady|careful. Best = the top month (score >= BEST_AT)
    plus any neighbour within 1 point that also clears BEST_AT. Capped (T2/T3) -> no best."""
    tones = []
    for s, f in zip(scores, flags):
        tones.append("careful" if (f or s <= CAREFUL_AT) else "good" if s >= GOOD_AT else "steady")
    top = max(range(len(scores)), key=lambda i: (scores[i], -i))
    if not capped and scores[top] >= BEST_AT and tones[top] != "careful":
        tones[top] = "best"
        for d in (-1, 1):
            i = top + d
            while 0 <= i < len(scores) and scores[i] >= max(BEST_AT, scores[top] - 1) \
                    and tones[i] != "careful":
                tones[i] = "best"
                i += d
    return tones


def _fact(part):
    pts, planet, h, kind = part
    if kind == "sadesati":
        return "Saturn passes close to your Moon sign."
    if kind == "retro":
        return f"Mars moves backward in {HOUSE_NAME[h]}."
    if kind == "looks":
        return f"{planet} looks at {HOUSE_NAME[h]}."
    return f"{planet} passes {HOUSE_NAME[h]}."


def _why(parts, careful=False):
    """One plain 'why' fact (no brackets, no numbers): the strongest positive part,
    or for a careful topic the strongest negative part. Area parts come first."""
    pick = [p for p in parts if (p[0] < 0 if careful else p[0] > 0)]
    if not pick:
        return "No slow planet presses hard on this part of your chart."
    return _fact(max(pick, key=lambda x: abs(x[0])))


# ----------------------------------------------------------------- Sade Sati (E3)
def _sade_sati(moon_sign, as_of, span_end_ym):
    """Monthly 2-way scan: the start of a running phase (back up to 8 years), every
    phase and pause from there across the span, plus a return that begins within
    6 months after the span (Saturn's move back, e.g. 2027)."""
    y0, m0 = _add_months(as_of.year, as_of.month, -96)
    rows = []
    for k in range(96 + 36):
        y, m = _add_months(y0, m0, k)
        s = sign_of(sidereal_lon(swe.SATURN, jd(datetime(y, m, 15, 12)))[0])
        rel = (s - moon_sign) % 12
        rows.append((_ym(y, m), {11: "rising", 0: "peak", 1: "setting"}.get(rel)))
    runs = []
    for ym, ph in rows:
        if runs and runs[-1]["phase"] == ph:
            runs[-1]["to"] = ym
        else:
            runs.append({"phase": ph, "from": ym, "to": ym})
    now = _ym(as_of.year, as_of.month)
    cur = next(r for r in runs if r["from"] <= now <= r["to"])
    limit = _ym(*_add_months(int(span_end_ym[:4]), int(span_end_ym[5:]), 6))
    phases = []
    for r in runs:
        if r["to"] < now and r is not cur:
            continue
        if r["from"] > limit:
            break
        if r["phase"] is None:
            # a gap is a "pause" only if Sade Sati comes back soon after it
            nxt = runs[runs.index(r) + 1] if runs.index(r) + 1 < len(runs) else None
            if phases and nxt and nxt["phase"] and nxt["from"] <= limit:
                phases.append({"phase": "pause", "from": r["from"], "to": r["to"]})
            continue
        phases.append(dict(r))
    return {"active": cur["phase"] is not None, "phase": cur["phase"], "phases": phases}


# ----------------------------------------------------------------- main
def compute_diwali(name, dob, tob, tz, lat, lon, *, gender, work_type, steering,
                   time_quality="T0", gift_on=False, giver_name="", gift_message="",
                   place="", as_of="2026-11-08"):
    if gender not in ("male", "female"):
        raise ValueError("gender must be 'male' or 'female'")
    if work_type not in WORK_TYPES:
        raise ValueError(f"work_type must be one of {WORK_TYPES}")
    if steering is not None and steering not in STEERING:
        raise ValueError(f"steering must be one of {STEERING} or None")
    if time_quality not in ("T0", "T1", "T2", "T3"):
        raise ValueError("time_quality must be T0..T3")
    female = gender == "female"
    as_of_dt = datetime.fromisoformat(as_of) if isinstance(as_of, str) else as_of
    as_of_s = as_of_dt.strftime("%Y-%m-%d")

    # ---- shared engine: tier logic (T1 stability, T2/T3 Moon chart), manglik, period
    rep = engine.compute_report(name, dob, tob, tz, lat, lon, female=female,
                                time_quality=time_quality, as_of=as_of_dt, place=place)
    dt_utc = datetime.fromisoformat(f"{dob}T{tob}:00") - timedelta(hours=tz)
    ch = engine.compute_chart(dt_utc, lat, lon)
    g = ch["grahas"]
    moon = g["Moon"]
    use_moon = rep["meta"]["system"] == "chandra_lagna"
    basis = "moon" if use_moon else "lagna"
    ref = moon.sign if use_moon else ch["lagna_sign"]
    refs = [ref] if use_moon else [ch["lagna_sign"], moon.sign]
    capped = time_quality in ("T2", "T3")              # engine grade cap -> no "best"

    def H(sign):
        return houses_from(ref, sign)

    def lord(h):
        return SIGN_LORD[(ref + h - 1) % 12]

    # ---- meta
    b = date.fromisoformat(dob)
    age = as_of_dt.year - b.year - ((as_of_dt.month, as_of_dt.day) < (b.month, b.day))
    sy, sm = as_of_dt.year, as_of_dt.month
    span = [_ym(*_add_months(sy, sm, k)) for k in range(12)]
    ey, em = int(span[-1][:4]), int(span[-1][5:])
    meta = {"name": name, "first_name": (name or "").strip().split(" ")[0], "dob": dob,
            "tob": tob, "place": place, "gender": gender, "work_type": work_type,
            "steering": steering, "time_quality": time_quality, "basis": basis,
            "lang": "en", "variant": "/en/diwali", "age": age, "age_band": _age_band(age),
            "as_of": as_of_s, "span": f"{MONTHS[sm - 1]} {sy} – {MONTHS[em - 1]} {ey}",
            "two_timelines": rep["meta"]["two_timelines_detected"],
            "gift": {"on": bool(gift_on), "giver_name": (giver_name or "").strip() if gift_on else "",
                     "message": (gift_message or "").strip() if gift_on else ""}}

    # ---- chart
    planets = [{"name": p, "sign": SIGN_NAMES[g[p].sign], "house": H(g[p].sign),
                "dignity": g[p].dignity, "retro": g[p].retro, "nakshatra": NAKSHATRAS[g[p].nak]}
               for p in PLANET_ORDER]
    chart = {"lagna": {"sign": SIGN_NAMES[ch["lagna_sign"]]},
             "moon": {"sign": SIGN_NAMES[moon.sign], "nakshatra": NAKSHATRAS[moon.nak],
                      "pada": moon.pada},
             "planets": planets,
             "houses": {str(h): {"sign": SIGN_NAMES[(ref + h - 1) % 12], "lord": lord(h)}
                        for h in range(1, 13)}}

    # ---- period + turning points
    tree = vimshottari_tree(moon.lon, dt_utc, as_of_dt + timedelta(days=4 * 365))
    md = next(m for m in tree if m["start"] <= as_of_dt <= m["end"])
    ad = next(a for a in md["ads"] if a["start"] <= as_of_dt <= a["end"])
    all_ads = [(m["lord"], a) for m in tree for a in m["ads"]]
    i_ad = next(i for i, (_, a) in enumerate(all_ads) if a is ad)
    nxt = all_ads[i_ad + 1] if i_ad + 1 < len(all_ads) else None
    span_end_dt = datetime(*_add_months(ey, em, 1), 1)
    turning = []
    for mlord, a in all_ads:
        if as_of_dt < a["start"] < span_end_dt:
            kind = "main_period" if a["lord"] == mlord else "sub_period"
            turning.append({"ym": a["start"].strftime("%Y-%m"), "kind": kind,
                            "planet": a["lord"]})

    # ---- 12 months (+ the month before, to see sign changes)
    pyb, pmb = _add_months(sy, sm, -1)
    prev = _positions(datetime(pyb, pmb, 15, 12))
    months, pos_by_ym = [], {}
    for ym in span:
        y, m = int(ym[:4]), int(ym[5:])
        pos = _positions(datetime(y, m, 15, 12))
        pos_by_ym[ym] = pos
        for p in ("Jupiter", "Saturn"):
            if pos[p][0] != prev[p][0]:
                turning.append({"ym": ym, "kind": p.lower() + "_moves", "planet": p,
                                "house": H(pos[p][0])})
        prev = pos
    turning.sort(key=lambda t: t["ym"])

    base = {ym: _base_score(pos_by_ym[ym], refs, ref, moon.sign) for ym in span}
    tones = _tones([base[ym][0] for ym in span], [base[ym][2] for ym in span], capped)
    tone_of = dict(zip(span, tones))

    # E7 gold months + loan months
    ad_rules_money = ad["lord"] in (lord(2), lord(11))
    gold, loans, loan_why = [], [], {}
    for k, ym in enumerate(span):
        pos = pos_by_ym[ym]
        hit = any(H(pos[p][0]) in (2, 11) for p in ("Venus", "Jupiter")) or ad_rules_money
        if hit:                                  # exactly GOLD_RULE (E7 / O-5), no extra filter
            gold.append(ym)
        mars_h = H(pos["Mars"][0])
        prev_pos = pos_by_ym[span[k - 1]] if k else _positions(datetime(pyb, pmb, 15, 12))
        prev2 = pos_by_ym[span[k - 2]] if k > 1 else None
        entered6 = any(H(pos[p][0]) == 6 and (H(prev_pos[p][0]) != 6 or
                                              (prev2 is not None and H(prev2[p][0]) != 6))
                       for p in ("Rahu", "Saturn"))
        if (mars_h in (2, 6, 11) or entered6) and tone_of[ym] != "careful":   # "good months to clear loans"
            loans.append(ym)
            loan_why.setdefault(ym, f"Mars passes {HOUSE_NAME[mars_h]}." if mars_h in (2, 6, 11)
                                else f"A slow planet enters {HOUSE_NAME[6]}.")

    for ym in span:
        pos = pos_by_ym[ym]
        y, m = int(ym[:4]), int(ym[5:])
        tone = tone_of[ym]
        hs = {p: H(pos[p][0]) for p in TRANSIT_PLANETS}
        care = None
        if tone == "careful":
            twelfth = any(hs[p] == 12 for p in ("Jupiter", "Mars", "Venus", "Saturn"))
            care = "reactions" if (base[ym][2] and not twelfth) else "spending"
        tags = []
        if ym in gold: tags.append("gold")
        if ym in loans: tags.append("loans")
        if tone in ("best", "good") and any(hs[p] in (2, 7, 10, 11) for p in ("Venus", "Mercury")):
            tags.append("deals")
        if tone != "careful" and any(hs["Venus"] == h or hs["Jupiter"] == h
                                      or _aspects("Jupiter", hs["Jupiter"], h)
                                      for h in AREA_HOUSES["family"]):
            tags.append("family")
        if tone != "careful" and any(hs[p] in (9, 12) for p in ("Jupiter", "Venus", "Rahu")):
            tags.append("travel")
        if tone in ("best", "good") and (hs["Sun"] in (10, 11) or hs["Jupiter"] == 10):
            tags.append("work")
        months.append({"ym": ym, "label": MONTHS[m - 1], "year": y, "tone": tone,
                       "care_reason": care,
                       "transits": {p: {"sign": SIGN_NAMES[pos[p][0]], "house": hs[p],
                                        "retro": pos[p][1]} for p in TRANSIT_PLANETS},
                       "tags": tags, "score": base[ym][0]})

    # ---- areas: month tones per area
    area_tone, area_parts = {}, {}
    for a in AREAS:
        sc, fl = [], []
        for ym in span:
            t, parts = _area_term(pos_by_ym[ym], ref, a, female)
            area_parts[(a, ym)] = parts + base[ym][1]
            sc.append(base[ym][0] + 2 * t)
            fl.append(base[ym][2])
        # A month the 12 months call careful is never a best/good month for any area (it drops to
        # steady), so no picture, topic or answer can put a careful month in a "best/good time".
        area_tone[a] = {y: "steady" if tone_of[y] == "careful" and t in ("best", "good") else t
                        for y, t in zip(span, _tones(sc, fl, capped))}

    # ---- rule B fine-tune scores (spec §5 "Area order" rule 4)
    # Signal 3 uses the sign(s) Jupiter holds for most of the span (>= 6 of 12 months);
    # a short retrograde dip back into the previous sign is not counted. This is the
    # reading that matches the spec's worked example (Vikram: Career 0).
    from collections import Counter
    jup_count = Counter(pos_by_ym[ym]["Jupiter"][0] for ym in span)
    jup_main = [s for s, n in jup_count.items() if n >= 6] or [jup_count.most_common(1)[0][0]]

    def rules_or_sits(planet, hs):
        sits = planet in g and H(g[planet].sign) in hs
        return sits or any(lord(h) == planet for h in hs)

    scores = {}
    for a in AREAS:
        hs = AREA_HOUSES[a]
        jup = any(H(s) in hs or any(_aspects("Jupiter", H(s), x) for x in hs) for s in jup_main)
        scores[a] = int(rules_or_sits(md["lord"], hs)) + int(rules_or_sits(ad["lord"], hs)) + int(jup)

    # ---- area order (E4)
    order, first_reason = area_order(work_type, steering, scores)

    # ---- area detail
    def windows(a):
        t = area_tone[a]
        return {"best": [y for y in span if t[y] == "best"],
                "good": [y for y in span if t[y] == "good"],
                "careful": [y for y in span if t[y] == "careful"]}

    def when_of(a, yms):
        ts = {area_tone[a][y] for y in yms}
        return "best" if "best" in ts else "good" if "good" in ts else \
            "careful" if ts == {"careful"} else "steady"

    def topic(a, n, state, yms, why, when=None):
        return {"key": f"{a}.t{n}", "state": state, "when": when or (when_of(a, yms) if yms else "steady"),
                "months": list(yms), "why": why}

    def area_state(w):
        nb, ng, nc = len(w["best"]), len(w["good"]), len(w["careful"])
        if nc >= 6 and nb == 0:
            return "careful"
        if (nb >= 1 and nb + ng >= 4) or (nb + ng >= 6 and nb + ng > nc):
            return "good"
        return "steady"

    def first_run(yms):
        r = _runs(yms, span)
        return r[0] if r else []

    def best_or_good(a):
        # All positive months in time order: the best months must not hide earlier good ones.
        return [y for y in span if area_tone[a][y] in ("best", "good")]

    def why_for(a, yms, careful=False):
        return _why(area_parts[(a, yms[0])], careful) if yms else _why([])

    sev_lord = lord(7)
    dy = _dhana_yoga(g, ref)
    mg = rep["manglik"]
    manglik = {"lagna_rule": None if use_moon else mg["from_lagna"], "moon_rule": mg["from_moon"],
               "cancelled": False, "reason": None}
    if mg["status"] == "manglik_cancelled" and (manglik["moon_rule"] or manglik["lagna_rule"]):
        manglik["cancelled"], manglik["reason"] = True, mg["cancellations"][0]
    manglik_on = (manglik["moon_rule"] or bool(manglik["lagna_rule"])) and not manglik["cancelled"]
    spend_care = [m["ym"] for m in months if m["care_reason"] == "spending"]
    react_care = [m["ym"] for m in months if m["care_reason"] == "reactions"]
    all_care = [m["ym"] for m in months if m["tone"] == "careful"]

    areas = {}
    for a in AREAS:
        w = windows(a)
        st = area_state(w)
        bg = best_or_good(a)
        tp = []
        if a == "money":
            early = [y for y in span[:3] if area_tone[a][y] in ("best", "good")]
            tp.append(topic(a, 1, st if early or st != "careful" else "careful", early or span[:1],
                            why_for(a, early or span[:1])))
            tp.append(topic(a, 2, "good" if bg else "steady", first_run(bg), why_for(a, first_run(bg))))
            tp.append(topic(a, 3, "careful" if spend_care else "steady", spend_care,
                            why_for(a, spend_care, True), when="careful" if spend_care else "steady"))
            ln = [y for y in loans if area_tone[a][y] != "careful"]
            tp.append(topic(a, 4, "good" if ln else "steady", ln,
                            loan_why[ln[0]] if ln else "No month stands out for loans; pay down steadily."))
            after = [y for y in span if all_care and y > all_care[-1] and area_tone[a][y] != "careful"]
            rec = first_run([y for y in span if area_tone[a][y] in ("best", "good")]) or after[:1]
            tp.append(topic(a, 5, "good" if rec else "steady", rec, why_for(a, rec)))
            src = (f"{lord(2)} rules both the money part and the gains part" if lord(2) == lord(11) else
                   f"{lord(2)} rules the money part and {lord(11)} the gains part")
            tp.append(topic(a, 6, st, [], f"{src}; {lord(2)} sits in {HOUSE_NAME[H(g[lord(2)].sign)]}."))
            tp.append(topic(a, 7, "good" if dy["present"] else "steady", [],
                            dy["fact"]))
        elif a == "career":
            tp.append(topic(a, 1, "good" if w["best"] else st, w["best"] or first_run(w["good"]),
                            why_for(a, w["best"] or first_run(w["good"]))))
            tp.append(topic(a, 2, "good" if bg else "steady", bg, why_for(a, bg)))
            raise_m = [y for y in span if area_tone[a][y] in ("best", "good") and
                       any(H(pos_by_ym[y][p][0]) in (10, 11) for p in ("Sun", "Venus", "Jupiter", "Mercury"))]
            tp.append(topic(a, 3, "good" if raise_m else "steady", raise_m, why_for(a, raise_m)))
            rec = first_run(bg)
            tp.append(topic(a, 4, "good" if rec else "steady", rec, why_for(a, rec)))
            tl = lord(10)
            tp.append(topic(a, 5, st, [], f"The work part is ruled by {tl}, which sits in "
                                          f"{HOUSE_NAME[H(g[tl].sign)]}."))
            trav = [y for y in span if "careful" not in (area_tone[a][y], tone_of[y]) and
                    any(H(pos_by_ym[y][p][0]) in (9, 12) for p in ("Jupiter", "Venus", "Rahu"))]
            tp.append(topic(a, 6, "good" if trav else "steady", trav, why_for(a, trav)))
        elif a == "business":
            signs_ = [g[lord(7)].dignity in ("own", "exalted"), H(g["Mercury"].sign) in (1, 7, 10, 11),
                      H(g[lord(10)].sign) in (7, 11)]
            lean = "business" if any(signs_) else "job"
            tp.append(topic(a, 1, "good" if lean == "business" else "steady", [],
                            f"The partner part is ruled by {lord(7)} and the work part by {lord(10)}; "
                            f"your chart leans to {'business' if lean == 'business' else 'a job with side income'}."))
            tp.append(topic(a, 2, "good" if bg else "steady", bg, why_for(a, bg)))
            solo = g[lord(7)].dignity in ("debilitated",) or g[lord(7)].combust
            # Mock 3C v2 a-business: two dials, value 0 (left) .. 1 (right), from the same facts as topics 1 and 3.
            # Job↔Business rule: count 3 business signs (partner-part ruler in own/exalted sign; Mercury in the
            # 1st/7th/10th/11th; work-part ruler in the 7th/11th): 0 -> .25, 1 -> .55, 2 -> .70, 3 -> .85.
            # Alone↔Partner rule: partner-part ruler weak (debilitated or combust) -> .30; in own/exalted -> .75;
            # otherwise .55.
            k = sum(signs_)
            l7 = lord(7)
            biz_why = [w for w, on in zip(
                (f"{l7}, ruler of the partner part, sits in its own or exalted sign.",
                 f"Mercury sits in {HOUSE_NAME[H(g['Mercury'].sign)]}.",
                 f"{lord(10)}, ruler of the work part, sits in {HOUSE_NAME[H(g[lord(10)].sign)]}."), signs_) if on]
            dials = [
                {"left": "Job", "right": "Business", "value": 0.25 if not k else round(0.55 + 0.15 * (k - 1), 2),
                 "why": " ".join(biz_why) or f"{lord(10)} rules the work part and leans to steady work for others."},
                {"left": "Alone", "right": "Partner",
                 "value": 0.30 if solo else 0.75 if g[l7].dignity in ("own", "exalted") else 0.55,
                 "why": (f"{l7}, ruler of the partner part, is weak in your chart." if solo else
                         f"{l7}, ruler of the partner part, is strong in its own or exalted sign."
                         if g[l7].dignity in ("own", "exalted") else
                         f"{l7} rules the partner part and sits in {HOUSE_NAME[H(g[l7].sign)]}.")}]
            tp.append(topic(a, 3, "steady" if solo else "good", [],
                            f"{lord(7)} rules the partner part and sits in {HOUSE_NAME[H(g[lord(7)].sign)]}."))
            deals = [m["ym"] for m in months if "deals" in m["tags"]]
            tp.append(topic(a, 4, "good" if deals else "steady", deals, why_for(a, deals)))
            tp.append(topic(a, 5, "careful" if all_care else "steady", all_care, why_for(a, all_care, True),
                            when="careful" if all_care else "steady"))
        elif a == "family":
            tp.append(topic(a, 1, st, bg[:1], why_for(a, bg[:1])))
            fam = [m["ym"] for m in months if "family" in m["tags"] and area_tone[a][m["ym"]] != "careful"] or bg
            tp.append(topic(a, 2, "good" if fam else "steady", fam, why_for(a, fam)))
            prop = [y for y in gold if area_tone[a][y] in ("best", "good")]   # large-buy months
            tp.append(topic(a, 3, "good" if prop else "steady", prop, why_for(a, prop)))
            mv = [y for y in span if area_tone[a][y] in ("best", "good") and
                  any(H(pos_by_ym[y][p][0]) in (4, 9, 12) for p in ("Jupiter", "Venus", "Rahu", "Saturn"))]
            tp.append(topic(a, 4, "good" if mv else "steady", mv, why_for(a, mv)))
            happy = [y for y in span if area_tone[a][y] in ("best", "good") and
                     (H(pos_by_ym[y]["Jupiter"][0]) == 5 or _aspects("Jupiter", H(pos_by_ym[y]["Jupiter"][0]), 5)
                      or H(pos_by_ym[y]["Venus"][0]) == 5)]
            tp.append(topic(a, 5, "good" if happy else "steady", happy, why_for(a, happy)))
        else:  # marriage
            tp.append(topic(a, 1, st, bg, why_for(a, bg)))
            dec = [y for y in span if area_tone[a][y] in ("best", "good") and
                   (_aspects("Jupiter", H(pos_by_ym[y]["Jupiter"][0]), 7) or
                    H(pos_by_ym[y]["Jupiter"][0]) == 7 or H(pos_by_ym[y]["Venus"][0]) in (1, 7))]
            tp.append(topic(a, 2, "good" if dec else "steady", dec or bg[:2], why_for(a, dec or bg[:2])))
            talk = [y for y in span if area_tone[a][y] == "careful" and
                    (H(pos_by_ym[y]["Mars"][0]) in (1, 7) or _aspects("Mars", H(pos_by_ym[y]["Mars"][0]), 7)
                     or pos_by_ym[y]["Mars"][1])] or w["careful"]
            mars_neg = [x for x in area_parts[(a, talk[0])] if x[1] == "Mars" and x[0] < 0] if talk else []
            tp.append(topic(a, 3, "careful" if talk else "steady", talk,
                            _fact(mars_neg[0]) if mars_neg else why_for(a, talk, True),
                            when="careful" if talk else "steady"))
            tp.append(topic(a, 4, "good" if g[sev_lord].dignity in ("own", "exalted") else "steady", [],
                            f"The partner part is in {SIGN_NAMES[(ref + 6) % 12]}, ruled by {sev_lord}."))
            tp.append(topic(a, 5, "steady" if manglik_on else "good", [],
                            "Manglik by the classical rule, with no cancelling factor." if manglik_on else
                            ("Mars meets the Manglik rule, but it is cancelled: " + CANCEL_PLAIN.get(manglik["reason"], manglik["reason"]) + "."
                             if manglik["cancelled"] else "Mars does not meet the Manglik rule.")))
        if a == "family":
            picture = _family_picture(tp, w["careful"], span)
        elif a == "marriage":
            picture = _marriage_picture(area_tone[a], span)
        else:
            picture = [_strand(TOPICS[a][int(t["key"].split(".t")[1]) - 1],
                               t["when"] if t["when"] in ("best", "good", "careful") else "good",
                               t["months"], span)
                       for t in tp if t["months"]]
        areas[a] = {"state": st, "windows": w, "topics": tp, "picture": picture}
        if a == "business":
            areas[a]["dials"] = dials

    # ---- money / marriage extras
    sp_windows = [x for x in rep["windows"] if x["end"] >= span[0] and x["start"] <= span[-1]]
    money_extra = {"dhana_yoga": {"present": dy["present"], "rule_text": DHANA_RULE,
                                  "lords": dy["lords"], "links": dy["links"]},
                   "gold_months": gold, "loan_months": loans, "gold_rule": GOLD_RULE,
                   "sub_period_rule_fired": ad_rules_money}
    marriage_extra = {"manglik": manglik,
                      "seventh": {"sign": SIGN_NAMES[(ref + 6) % 12], "lord": sev_lord,
                                  "lord_dignity": g[sev_lord].dignity},
                      "karakas": ["Venus", "Jupiter"] if female else ["Venus"],
                      # E9: the engine lifts weak periods to "Building" when nothing is strong
                      "building_only": bool(sp_windows) and all(x["grade"] == "Building" for x in sp_windows)}

    # ---- strengths (E5): always 3
    def str_key(p):
        gg = g[p]
        dig = gg.dignity if gg.dignity != "neutral" else _relation(p, gg.sign)
        h = H(gg.sign)
        hb = 1 if h in (1, 4, 5, 7, 9, 10) else -1 if h in (6, 8, 12) else 0
        bav = bhinnashtakavarga(ch, p)[gg.sign]
        return (DIGNITY_RANK[dig] - (0.5 if gg.combust else 0), hb, bav, -PLANET_ORDER.index(p)), dig
    seven = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
    ranked = sorted(seven, key=lambda p: str_key(p)[0], reverse=True)[:3]
    strengths = [{"planet": p, "sign": SIGN_NAMES[g[p].sign], "house": H(g[p].sign),
                  "dignity": str_key(p)[1]} for p in ranked]

    # ---- look-back (E8): Diwali 2025 -> 2026
    lb_good, lb_hard = [], []
    lb = [_ym(*_add_months(sy, sm, k)) for k in range(-12, 0)]
    lb_sc, lb_fl = [], []
    for ym in lb:
        s, _, f = _base_score(_positions(datetime(int(ym[:4]), int(ym[5:]), 15, 12)), refs, ref, moon.sign)
        lb_sc.append(s); lb_fl.append(f)
    for ym, t in zip(lb, _tones(lb_sc, lb_fl, True)):
        if t in ("good", "best"): lb_good.append(ym)
        elif t == "careful": lb_hard.append(ym)

    # ---- best time + summary (the one source for overall best/careful)
    best_m = [y for y in span if tone_of[y] == "best"]
    if best_m:
        bt = _runs(best_m, span)[0]
    else:                                              # capped / no best: top good run by score
        good_runs = _runs([y for y in span if tone_of[y] == "good"], span)
        bt = max(good_runs, key=lambda r: sum(base[y][0] for y in r)) if good_runs else \
            [max(span, key=lambda y: base[y][0])]
        bt = bt[:3]
    best_time = {"from": bt[0], "to": bt[-1]}
    summary = _summary(months, span, best_time)

    # ---- timeline: 4 parts cut from summary
    segs = _segments(months, span, summary)
    timeline = []
    # a second segment with the same tone gets the next theme, so no legend line repeats (spec §9)
    alts = {"careful": ["Slow down and save", "Go slow and think twice", "Spend with care"],
            "best": ["Your best time", "Your best time goes on", "The turning point"],
            "good": ["Growth with a steady hand", "Keep building", "Steady gains"],
            "steady": ["Hold steady and plan", "A quieter, steady time", "Keep a steady pace"]}
    for k, (yms, tone, ts, core) in enumerate(segs):
        care_r = [m["care_reason"] for m in months if m["ym"] in yms and m["care_reason"]]
        if tone == "careful":
            theme = "Spend with care" if "spending" in care_r else "Go slow and think twice"
        elif tone == "best":
            theme = "The turning point" if k and segs[k - 1][1] in ("careful", "steady") else "Your best time"
        elif k == 0:
            theme = "A steady new start"
        elif tone == "good":
            theme = "Growth with a steady hand"
        else:
            theme = "Hold steady and plan"
        used = {s["theme"] for s in timeline}
        theme = next((t for t in [theme] + alts[tone] if t not in used), theme)
        timeline.append({"from": yms[0], "to": yms[-1], "tone": tone, "theme": theme, "core": core})

    # ---- strongest area, luck
    def strength(a):
        w = areas[a]["windows"]
        return scores[a] * 2 + 2 * len(w["best"]) + len(w["good"]) - len(w["careful"])
    strongest = max(AREAS, key=lambda a: (strength(a), -AREAS.index(a)))
    luck = {"bright_spots": [{"area": a, "fact": next(
                (t["why"] for t in areas[a]["topics"] if t["state"] == "good" and t["months"]),
                areas[a]["topics"][0]["why"])} for a in order],
            "ninth": {"sign": SIGN_NAMES[(ref + 8) % 12], "lord": lord(9)}}

    # ---- answers (E12): 5 for the first area, or Better luck when picked
    emphasis = "luck" if steering == "luck" else order[0]
    answers = [{"q": q, "state": s} for q, s in zip(QUESTIONS[emphasis],
                                                     _answer_states(emphasis, areas, months, manglik_on,
                                                                    turning, best_m, gold))]

    # ---- practices (E10: no gemstones, no health fasting)
    practices, seen = [], set()
    for role, p in (("money", lord(2)), ("gains", lord(11)), ("luck", lord(9)),
                    ("period", ad["lord"]), ("period", md["lord"]), ("self", lord(1))):
        if p in seen:
            continue
        seen.add(p)
        day, mantra = (REMEDY_7L.get(p) or REMEDY_NODE[p])[:2]
        practices.append({"planet": p, "role": role, "day": day, "mantra": mantra})
        if len(practices) == 3:
            break

    # ---- Wrapped card + teaser
    wrapped = _wrapped(strongest, summary, order[0], ad["lord"], md["lord"], not capped)
    wrapped["lead_area"] = order[0]
    wrapped["same"] = strongest == order[0]
    sade = _sade_sati(moon.sign, as_of_dt, span[-1])
    kundli = {}
    for p in PLANET_ORDER:
        kundli.setdefault(SIGN_NAMES[g[p].sign], []).append(ABBR[p])
    if not use_moon:
        kundli.setdefault(SIGN_NAMES[ch["lagna_sign"]], []).insert(0, "La")
    teaser = {"name": name, "moon_sign": SIGN_NAMES[moon.sign], "nakshatra": NAKSHATRAS[moon.nak],
              "lagna_sign": SIGN_NAMES[ch["lagna_sign"]], "basis": basis,
              "period": f"{md['lord']} – {ad['lord']}",
              "sade_sati": {"active": sade["active"], "phase": sade["phase"]},
              "planets": [{"name": p["name"], "sign": p["sign"], "dignity": p["dignity"]} for p in planets],
              "kundli": kundli, "strongest_area": strongest, "move": wrapped["move"],
              "words": [{"word": w["word"], "line_masked": w["line_masked"]} for w in wrapped["words"]],
              "emphasis_area": emphasis, "questions": list(QUESTIONS[emphasis]),
              "teasers": _teasers(emphasis, capped)}
    wrapped_out = {k: v for k, v in wrapped.items() if k != "words"}
    wrapped_out["words"] = [{"word": w["word"], "line": w["line"]} for w in wrapped["words"]]

    return {
        "product": "diwali", "meta": meta, "chart": chart,
        "period": {"md": md["lord"], "ad": ad["lord"], "ad_end": ad["end"].strftime("%Y-%m"),
                   "next_ad": {"lord": nxt[1]["lord"], "from": nxt[1]["start"].strftime("%Y-%m")} if nxt else None,
                   "turning_points": turning},
        "sade_sati": sade, "months": months,
        "area_order": order, "first_reason": first_reason, "scores": scores,
        "areas": areas, "money_extra": money_extra, "marriage_extra": marriage_extra,
        "strengths": strengths, "lookback": {"good": lb_good, "hard": lb_hard},
        "luck": luck, "timeline": timeline, "best_time": best_time, "summary": summary,
        "diwali": {"days": [dict(d) for d in DIWALI_DAYS], "puja_times": [dict(p) for p in PUJA_TIMES]},
        "answers": answers, "practices": practices,
        "wrapped": wrapped_out, "teaser": teaser,
    }


# ----------------------------------------------------------------- pieces
def area_order(work_type, steering, scores):
    """E4 / spec §5 "Area order": chosen area first (pinned), else the situation order
    (its first area pinned); Better luck picked -> the areas as if skipped. Then rule B:
    one top-down pass, swap two unpinned neighbours only on a 2+ point gap."""
    sit = list(SITUATION_ORDER[work_type])
    if steering in AREAS:
        order, first_reason = [steering] + [x for x in sit if x != steering], "picked"
    else:
        order, first_reason = sit, "situation"
    for i in range(1, len(order) - 1):
        if scores[order[i + 1]] - scores[order[i]] >= 2:
            order[i], order[i + 1] = order[i + 1], order[i]
    return order, first_reason


def _dhana_yoga(g, ref):
    """E6 (O-5): a link between the lords of houses 1, 2, 5, 9, 11 — one planet ruling
    two of them, conjunction (same sign), exchange, or graha drishti."""
    houses = (1, 2, 5, 9, 11)
    lords = {h: SIGN_LORD[(ref + h - 1) % 12] for h in houses}
    links = []
    by_planet = {}
    for h, p in lords.items():
        by_planet.setdefault(p, []).append(h)
    for p, hs in by_planet.items():
        if len(hs) > 1:
            links.append({"kind": "one planet rules two", "planets": [p], "houses": hs})
    uniq = list(by_planet)
    for i in range(len(uniq)):
        for j in range(i + 1, len(uniq)):
            a, b = uniq[i], uniq[j]
            sa, sb = g[a].sign, g[b].sign
            kind = None
            if sa == sb:
                kind = "same sign"
            elif SIGN_LORD[sa] == b and SIGN_LORD[sb] == a:
                kind = "exchange"
            elif _aspects(a, houses_from(sa, sa), houses_from(sa, sb)) or \
                    _aspects(b, houses_from(sb, sb), houses_from(sb, sa)):
                kind = "aspect"
            if kind:
                links.append({"kind": kind, "planets": [a, b],
                              "houses": sorted(by_planet[a] + by_planet[b])})
    present = bool(links)
    if present:
        l0 = links[0]
        if l0["kind"] == "one planet rules two":
            fact = f"{l0['planets'][0]} rules both {HOUSE_NAME[l0['houses'][0]]} and {HOUSE_NAME[l0['houses'][1]]}."
        else:
            verb = {"same sign": "sit together", "exchange": "swap signs", "aspect": "look at each other"}[l0["kind"]]
            fact = f"{l0['planets'][0]} and {l0['planets'][1]} {verb}, linking your wealth parts."
    else:
        fact = "The planets of your wealth parts do not link directly; money builds through steady effort."
    return {"present": present, "lords": sorted(set(lords.values()), key=PLANET_ORDER.index),
            "links": links, "fact": fact}


def _answer_states(area, areas, months, manglik_on, turning, best_m, gold):
    """E12: one word per §6a question (good|steady|careful)."""
    def ts(a, n):
        return areas[a]["topics"][n - 1]["state"]
    care = [m for m in months if m["tone"] == "careful"]
    spend = [m for m in care if m["care_reason"] == "spending"]
    if area == "money":
        return [ts("money", 1), ts("money", 2), ts("money", 7),
                "careful" if spend else "steady", "good" if gold else "steady"]
    if area == "career":
        return [ts("career", 1), ts("career", 2), ts("career", 2), ts("career", 3),
                "careful" if areas["career"]["windows"]["careful"] else "steady"]
    if area == "business":
        return [areas["business"]["state"], ts("business", 2), ts("business", 2), ts("business", 3),
                "careful" if care else "steady"]
    if area == "family":
        return [ts("family", 1), ts("family", 2), ts("family", 3), ts("family", 5),
                "careful" if areas["family"]["windows"]["careful"] else "steady"]
    if area == "marriage":
        return [ts("marriage", 1), ts("marriage", 2), ts("marriage", 3), ts("marriage", 4),
                "steady" if manglik_on else "good"]
    # luck: positives only, never careful
    goodish = [m for m in months if m["tone"] in ("best", "good")]
    return ["good" if turning else "steady", "good" if goodish else "steady",
            "good" if (best_m or goodish) else "steady", "good", "good"]


_SEASON = {11: "winter", 12: "winter", 1: "winter", 2: "spring", 3: "spring", 4: "spring",
           5: "summer", 6: "summer", 7: "summer", 8: "autumn", 9: "autumn", 10: "autumn"}
_STRONG_WORD = {"money": ("STEADY", "Your money grows slowly but surely."),
                "career": ("RISING", "Your work and name tend to grow step by step."),
                "business": ("BUILDER", "Your business has room to grow."),
                "family": ("ROOTED", "Home and family give you your footing."),
                "marriage": ("WARM", "The people closest to you matter most now.")}
_BEST_THING = {"money": "Your money moves best", "career": "Your work and name shine most",
               "business": "Your business grows best", "family": "Home life glows most",
               "marriage": "Warmth with the people closest to you peaks"}
MASK = "●●●–●●●"


def _summary(months, span, best_time):
    """THE one source for the overall best and careful times, built only from the month tones.
    careful = every run of consecutive careful months; its reason is the run's most common
    care_reason ("spending" on a tie). best = best_time (the first best run, or for capped
    charts the top good run). Wrapped, timeline headline, tally and prose all read this."""
    from collections import Counter
    careful = []
    for r in _runs([m["ym"] for m in months if m["tone"] == "careful"], span):
        c = Counter(m["care_reason"] for m in months if m["ym"] in r)
        reason = "spending" if c["spending"] >= c["reactions"] else "reactions"
        careful.append({"from": r[0], "to": r[-1], "reason": reason, "label": _range_label(r)})
    return {"best": {"from": best_time["from"], "to": best_time["to"],
                     "label": _range_label([best_time["from"], best_time["to"]])},
            "careful": careful,
            "good_label": _months_label([m["ym"] for m in months if m["tone"] == "good"]),
            "steady_label": _months_label([m["ym"] for m in months if m["tone"] == "steady"])}


def _segments(months, span, summary):
    """The 4 timeline parts, cut so every summary.careful run and the summary.best run stay whole.
    Each month has a kind: "c" (in a careful run), "b" (in the best run) or "o" (other). Blocks
    start as the runs of one kind. Rules, so the timeline can never contradict the month tones
    or summary:
      * a careful month only ever sits in a careful part, and a careful part is always tone careful;
      * a part's kind is derived from what it holds: any "c" month -> careful, else any "b" month
        -> best (good when the best run has no best month, capped charts), else other. So a
        "best" part always holds a summary.best month, and a careful part a careful run;
      * "c" and "b" months never share a part.
    Over 4: the shortest "o" block is absorbed into a neighbour: the best run if next to it, else
    both careful neighbours (bridging two careful runs into one part), else its careful neighbour
    (ties: that order, then earliest). Under 4: a block is cut in two, at the most even point that
    cuts no careful run (then no best run); blocks with such a point first, then longest
    (o, then b, then c). o tone = good when half or more is good/best, else steady.
    core = the summary runs the part holds, as a list of {from, to}: every careful run in a
    careful part, the best months in a best part, the part itself otherwise.
    Returns [(yms, tone, month_tones, core)]."""
    tone = {m["ym"]: m["tone"] for m in months}
    runs = [span[span.index(c["from"]):span.index(c["to"]) + 1] for c in summary["careful"]]
    best = span[span.index(summary["best"]["from"]):span.index(summary["best"]["to"]) + 1]
    mk = {y: "c" for r in runs for y in r}
    mk.update({y: "b" for y in best})
    mk = {y: mk.get(y, "o") for y in span}

    def kind(yms):
        return "c" if any(mk[y] == "c" for y in yms) else "b" if any(mk[y] == "b" for y in yms) else "o"

    blocks = []                                        # [kind, yms]
    for y in span:
        if blocks and blocks[-1][0] == mk[y]:          # careful runs are maximal, so never adjacent
            blocks[-1][1].append(y)
        else:
            blocks.append([mk[y], [y]])
    while len(blocks) > 4:
        def cand(i):
            nb = [blocks[j][0] for j in (i - 1, i + 1) if 0 <= j < len(blocks)]
            how = 0 if "b" in nb else 1 if nb.count("c") == 2 else 2
            return (len(blocks[i][1]), how, i)
        i = min((k for k in range(len(blocks)) if blocks[k][0] == "o"), key=cand)
        nb = [j for j in (i - 1, i + 1) if 0 <= j < len(blocks)]
        if any(blocks[j][0] == "b" for j in nb):
            nb = [j for j in nb if blocks[j][0] == "b"]
        lo, hi = min(nb + [i]), max(nb + [i])
        yms = [y for b_ in blocks[lo:hi + 1] for y in b_[1]]
        blocks[lo:hi + 1] = [[kind(yms), yms]]

    def cut(yms):                                      # (cuts careful run, cuts best run, unevenness, -h, h)
        n = len(yms)
        return min(((mk[yms[h - 1]] == mk[yms[h]] == "c", mk[yms[h - 1]] == mk[yms[h]] == "b",
                     abs(2 * h - n), -h, h) for h in range(1, n)), default=None)
    while len(blocks) < 4:
        i = max((k for k in range(len(blocks)) if len(blocks[k][1]) > 1),
                key=lambda k: (not cut(blocks[k][1])[0], -"obc".index(blocks[k][0]), len(blocks[k][1]), -k))
        yms, h = blocks[i][1], cut(blocks[i][1])[-1]
        blocks[i:i + 1] = [[kind(yms[:h]), yms[:h]], [kind(yms[h:]), yms[h:]]]
    out = []
    for k, yms in blocks:
        ts = [tone[y] for y in yms]
        if k == "c":
            t, core = "careful", [r for r in _runs([y for y in yms if mk[y] == "c"], span)]
        elif k == "b":
            t = "best" if any(tone[y] == "best" for y in best) else "good"
            core = [[y for y in yms if mk[y] == "b"]]
        else:
            t = "good" if (ts.count("good") + ts.count("best")) * 2 >= len(ts) else "steady"
            core = [yms]
        out.append((yms, t, ts, [{"from": r[0], "to": r[-1]} for r in core]))
    return out


def _teasers(emphasis, capped):
    if not capped:
        return list(TEASERS[emphasis])
    from diwali_bank import no_best_text
    return [no_best_text(t) for t in TEASERS[emphasis]]


def _wrapped(strongest, summary, lead="", ad_lord="", md_lord="", has_best=True):
    """Wrapped card: best = summary.best; careful = the longest careful run in summary
    (earliest on a tie), so the card can never disagree with the 12 months."""
    best = summary["best"]
    w1 = _STRONG_WORD[strongest]
    words = [{"word": w1[0], "line": w1[1], "line_masked": w1[1]}]
    bm = int(best["from"][5:])
    cr = max(summary["careful"], key=lambda c: _span_len(c["from"], c["to"]), default=None)
    if cr:
        reason = cr["reason"]
        n = _span_len(cr["from"], cr["to"])
        cm = int(_ym(*_add_months(int(cr["from"][:4]), int(cr["from"][5:]), n // 2))[5:])  # middle month
        short = cr["label"] if n == 1 else f"{MONTHS[int(cr['from'][5:]) - 1]}–{MONTHS[int(cr['to'][5:]) - 1]}"
        tmpl = "{M} is for planning, not spending." if reason == "spending" else \
            "{M} asks you to pause before you reply."
        words.append({"word": "PREPARED" if reason == "spending" else "THOUGHTFUL",
                      "line": tmpl.replace("{M}", short), "line_masked": tmpl.replace("{M}", MASK)})
        verb = "Save" if reason == "spending" else "Pause"
        move = f"{verb} in {_SEASON[cm]}. Act in {_SEASON[bm]}." if _SEASON[cm] != _SEASON[bm] else \
            f"{verb} first. Then act in {_SEASON[bm]}."
        careful = dict(cr)
    else:
        words.append({"word": "GROUNDED", "line": "No long careful time; keep a steady pace.",
                      "line_masked": "No long careful time; keep a steady pace."})
        words[-1]["line"] = words[-1]["line_masked"] = "No long careful time; keep a steady pace."
        move = f"Plan now. Act in {_SEASON[bm]}."
        careful = None
    word3 = "RISING" if w1[0] != "RISING" else "BRIGHT"
    tmpl = _BEST_THING[strongest] + " in {M}."
    words.append({"word": word3, "line": tmpl.replace("{M}", best["label"]),
                  "line_masked": tmpl.replace("{M}", MASK)})
    words[0]["line"] = words[0]["line_masked"] = w1[1]
    if not has_best:
        from diwali_bank import no_best_text
        for w in words:
            w["line"], w["line_masked"] = no_best_text(w["line"]), no_best_text(w["line_masked"])
    return {"strongest_area": strongest, "best": dict(best), "careful": careful,
            "move": move, "words": words}
