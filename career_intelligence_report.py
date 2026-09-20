"""
Axtroshastra Career Intelligence Report — engine (compute) + renderer.
Internal product id: "career_intelligence".  Route: /en/career-intelligence.
English-only for now (Hindi twin on hold — see docs/career-intelligence-report-spec.md).

Premium LinkedIn-audience product (₹1,999 / ₹999 founding price). Same funnel as
career-growth; a NEW, separate report. Visual design = the approved LIGHT
(Business-Growth `_VYAPAR_CSS`) 55-card mock (content card → McKinsey exhibit card).

compute_career_intelligence() — deterministic Jyotish only, no LLM. Reuses the same
real engines every product uses (engine.compute_chart / vimshottari_tree, vidyarthi
significators + windows, _dignity_score) and career_growth_report.py's proven
rule-based scorers. Produces the payload the renderer + narrative layer read.

Scoring note (TEMP, same status as career_growth's scorers): the six dimensions,
archetype affinity, decision-style and entrepreneurial score are simplified rule
engines built from REAL computed Uccha-Bala dignity scores (vidyarthi._dignity_score).
Real numbers, simplified rules — tunable, pending a dedicated house-based engine.
The chart→score mappings are the "open engine-design questions" in the spec, answered
here with classical karaka choices and marked for later calibration.
"""
import os
import re
from datetime import datetime, timedelta

from engine import (
    compute_chart, vimshottari_tree, houses_from, SIGN_LORD, SIGNS, SIGNS_EN, _sade_sati,
)
from vidyarthi import (
    student_significators, _dignity_score, compute_vidyarthi_report,
)
from products import LAGNA_PERSONA, PLANET_GIFT, PLANET_LESSON
# Reuse career_growth's proven scorers/prose so the two career products stay aligned.
from career_growth_report import (
    _naukri_apnakaam_meter, _strength_bucket, ABOUT_YOU_TRAITS, _fmt_range,
)
import ci_narrative
from ci_narr_part4 import NEED_BY_DIM   # dimension -> "environment that trait needs" (teaser reuse)


def _d(g, planet):
    """Real Uccha-Bala dignity score 0..100 for a planet (via vidyarthi._dignity_score)."""
    s, _ = _dignity_score(g[planet])
    return int(s)


def _avg(*vals):
    return round(sum(vals) / len(vals))


def _disp(v: int) -> int:
    """Calibrate a raw 0..100 dignity dimension into the report's DISPLAY band
    (~42..96). Raw Uccha-Bala dignity scores cluster low, so an un-calibrated
    radar can show an alarming near-zero ("Strategic 8") on what is a premium
    strengths report — no serious strengths assessment shows a catastrophic low.
    Monotonic, so it preserves the radar's shape and every relative ranking; the
    ARCHETYPE is chosen from the RAW dims (in compute_*), never from these, so
    calibration changes the shown numbers only, not which archetype a person is.
    Band is intentionally easy to tune."""
    return round(42 + max(0, min(100, v)) * 0.54)


# --- the six Executive-Snapshot dimensions --------------------------------------
# Each = average of the real dignity scores of its classical karaka(s). TEMP mapping.
def _dimensions(g) -> dict:
    leadership    = _avg(_d(g, "Sun"), _d(g, "Mars"))                 # authority + drive
    strategic     = _avg(_d(g, "Mercury"), _d(g, "Saturn"), _d(g, "Jupiter"))  # intellect+structure+wisdom
    independence  = _avg(_d(g, "Mars"), _d(g, "Sun"), _d(g, "Rahu"))  # self-drive + unconventional
    entrepreneur  = _avg(_d(g, "Mars"), _d(g, "Rahu"))                # risk + independence (== apnakaam karakas)
    risk          = _avg(_d(g, "Mars"), _d(g, "Rahu"), _d(g, "Ketu")) # boldness / detachment from safety
    stability     = _avg(_d(g, "Saturn"), _d(g, "Venus"), _d(g, "Moon"))  # endurance + comfort + security
    return {"leadership": leadership, "strategic": strategic, "independence": independence,
            "entrepreneurial": entrepreneur, "risk": risk, "stability": stability}


# --- the seven Career Archetypes ------------------------------------------------
# Affinity = weighted blend of the six dimensions; highest wins. TEMP weights.
ARCHETYPES = {
    "The Strategic Builder":   {"strategic": 1.0, "stability": 0.7, "leadership": 0.4, "risk": -0.3},
    "The Independent Leader":  {"leadership": 1.0, "independence": 0.8, "strategic": 0.3},
    "The Visionary":           {"strategic": 0.8, "risk": 0.8, "independence": 0.5, "stability": -0.4},
    "The Specialist":          {"strategic": 1.0, "stability": 0.5, "leadership": -0.4, "independence": -0.3},
    "The Entrepreneurial Mind":{"entrepreneurial": 1.0, "risk": 0.7, "independence": 0.6, "stability": -0.5},
    "The Consolidator":        {"stability": 1.0, "strategic": 0.4, "risk": -0.6, "entrepreneurial": -0.4},
    "The Reinventor":          {"risk": 0.9, "independence": 0.8, "entrepreneurial": 0.5, "stability": -0.3},
}
ARCHETYPE_BLURB = {
    "The Strategic Builder":   "You create lasting structures rather than chase quick wins — strongest with complexity, ownership and time.",
    "The Independent Leader":  "You lead best on your own terms — clear authority, your own standard, your own call.",
    "The Visionary":           "You see further than the room and move toward it — patterns and possibility over routine.",
    "The Specialist":          "You go deep, not wide — the trusted authority on the one thing that matters.",
    "The Entrepreneurial Mind":"You are built to own the outcome — autonomy, risk and building are where you come alive.",
    "The Consolidator":        "You turn what exists into something durable — steadiness others build on.",
    "The Reinventor":          "You reshape rather than repeat — every few years you change the game, not just play it.",
}


def _archetype(dims: dict) -> dict:
    def aff(weights):
        return sum(dims[k] * w for k, w in weights.items())
    ranked = sorted(ARCHETYPES.items(), key=lambda kv: -aff(kv[1]))
    top = ranked[0][0]
    return {"name": top, "blurb": ARCHETYPE_BLURB[top], "runner_up": ranked[1][0]}


# --- decision-making style (speed × basis) --------------------------------------
def _decision_style(g) -> dict:
    deliberate = _d(g, "Saturn") >= _d(g, "Mars")      # Saturn=deliberate, Mars=fast
    evidence   = _d(g, "Mercury") >= _d(g, "Moon")     # Mercury=evidence, Moon=instinct
    if deliberate and evidence:   name = "The Analyst"
    elif not deliberate and evidence: name = "The Fast Analyst"
    elif not deliberate and not evidence: name = "The Instinctive Decision Maker"
    else: name = "The Conservative Builder"
    # x,y in 0..1 for the 2x2 dot (x: instinct→evidence, y: fast(top)→deliberate(bottom))
    total = _d(g, "Mercury") + _d(g, "Moon") or 1
    x = _d(g, "Mercury") / total
    dtot = _d(g, "Saturn") + _d(g, "Mars") or 1
    y = _d(g, "Saturn") / dtot   # higher = more deliberate = lower on the matrix
    return {"name": name, "deliberate": deliberate, "evidence": evidence,
            "x": round(x, 2), "y": round(y, 2)}


# --- current career phase (from the running mahadasha lord) ---------------------
MD_TO_PHASE = {
    "Sun": "Recognition & Authority", "Moon": "Reflection & Repositioning",
    "Mars": "Drive & Expansion", "Mercury": "Repositioning & Sharpening",
    "Jupiter": "Growth & Expansion", "Venus": "Consolidation & Comfort",
    "Saturn": "Consolidation & Repositioning", "Rahu": "Reinvention & Breakout",
    "Ketu": "Detachment & Refocusing",
}
MD_PHASE_BASIS = {
    "Sun": "a Sun-ruled period — visibility, authority and being seen for your work",
    "Moon": "a Moon-ruled period — an inward, repositioning phase rather than outward push",
    "Mars": "a Mars-ruled period — energy, initiative and forward drive",
    "Mercury": "a Mercury-ruled period — sharpening, communicating and repositioning",
    "Jupiter": "a Jupiter-ruled period — classically the most expansive, growth-favouring phase",
    "Venus": "a Venus-ruled period — comfort, consolidation and relationships",
    "Saturn": "a Saturn-ruled period — restructuring and building on foundations already laid",
    "Rahu": "a Rahu-ruled period — unconventional moves, breakout and reinvention",
    "Ketu": "a Ketu-ruled period — letting go of the old and refocusing",
}

# --- phase-based growth direction (used by Q1 outlook + Q2 stay/switch) ----------
_GROWTH_LORDS = {"Sun", "Jupiter", "Mars", "Rahu"}       # lords whose MD reads as forward/up
_CONSOLIDATION_LORDS = {"Saturn", "Venus", "Moon", "Mercury", "Ketu"}


# ============================================================ VERDICT FUNCTIONS
# Package existing engine data into direct-answer objects for the 9 career
# questions. Every claim traces to computed chart data — no LLM, no guessing.
# Non-deterministic language per spec ("your chart indicates", "may favour").

def _career_outlook_verdict(phase, windows, peak_year, life_stage):
    """Q1: Will my career improve from here?"""
    md_lord = phase["md_lord"]
    has_windows = bool(windows)
    if md_lord in _GROWTH_LORDS and has_windows:
        direction = "improving"
        verdict = "YES — Stronger career growth lies ahead."
        detail = (f"You are currently in a {phase['name'].lower()} phase. Your chart indicates "
                  f"that the stronger professional period is still ahead of you.")
    elif md_lord in _GROWTH_LORDS:
        direction = "improving"
        verdict = "YES — Your current phase favours forward movement."
        detail = (f"You are in a {phase['name'].lower()} phase — a period that tends to "
                  f"reward initiative and expansion.")
    elif has_windows:
        direction = "building"
        verdict = "YES — After a repositioning phase, growth lies ahead."
        detail = (f"You are currently in a {phase['name'].lower()} phase. Your chart indicates "
                  f"that the stronger professional period is still ahead of you.")
    else:
        direction = "preparing"
        verdict = "YES — A transition period that opens into stronger ground."
        detail = (f"You are currently in a {phase['name'].lower()} phase. The chart favours "
                  f"using this period to prepare — the returns come once the ground is set.")
    return {"direction": direction, "verdict": verdict, "detail": detail}


def _stay_switch_verdict(phase, windows, peak_year, dims):
    """Q2: Should I stay in my current job or switch?
    4-way classification: Switch / Explore / Prepare / Stay."""
    md_lord = phase["md_lord"]
    has_windows = bool(windows)
    best_score = max((w["score"] for w in windows), default=0)

    if peak_year == 1 and md_lord in _GROWTH_LORDS and best_score >= 6.0:
        verdict = "Switch Jobs"
        tag = "Your chart favours making the move now — your current dasha supports forward action."
        detail = ("The strongest career-movement window of the next three years is open now, and "
                  "your current phase supports forward action.")
    elif peak_year <= 2 and has_windows and md_lord in _GROWTH_LORDS:
        verdict = "Start Exploring Options"
        tag = "Your chart favours exploring options — your current dasha supports initiative."
        detail = ("A career-movement window is approaching, and your current phase supports "
                  "initiative — this is a time to position and be ready.")
    elif has_windows and peak_year >= 2:
        verdict = "Prepare"
        tag = "Your chart favours preparing before making the bigger move."
        detail = ("A stronger window is ahead. The current phase is better "
                  "suited to groundwork than to the move itself.")
    else:
        verdict = "Not right time to switch"
        tag = "Your chart favours consolidating where you are for now."
        detail = ("The current phase reads as a consolidation period — strengthen your position "
                  "rather than chase a new one.")
    return {"verdict": verdict, "tag": tag, "detail": detail}


def _best_window_verdict(windows, peak_year, three_year):
    """Q3: When is the best time to change jobs?"""
    bwr = three_year.get("best_window")
    if not windows:
        return {"has_window": False, "year": None, "best_window_range": None,
                "signal": "No strong job-change window in the next three years — a steadier period.",
                "detail": "Your chart does not show a qualifying career-movement window in the near term. "
                          "This favours deepening where you are over seeking a move."}
    return {"has_window": True, "year": peak_year,
            "best_window_range": bwr,
            "signal": f"Around {bwr} — the strongest career-movement opening in the next three years." if bwr else "We've identified a stronger window for career movement.",
            "detail": f"The strongest career-movement opening falls around {bwr}." if bwr else f"The strongest career-movement opening falls in Year {peak_year} of the next three."}


def _promotion_outlook(g, dims, windows, peak_year):
    """Q4: When will I get my next promotion or major career breakthrough?"""
    sun = _d(g, "Sun")
    saturn = _d(g, "Saturn")
    leadership = dims["leadership"]

    if sun >= 62:
        visibility = "rising"
        how = "through growing professional visibility and recognition"
    else:
        visibility = "emerging"
        how = "through consistent delivery rather than sudden recognition"

    if saturn >= 62 and leadership >= 70:
        route = "promotion"
        route_detail = "promotion into a named authority role or a significantly bigger mandate"
    elif leadership >= 70:
        route = "bigger mandate"
        route_detail = "a larger responsibility or mandate — possibly through an external move"
    else:
        route = "external move"
        route_detail = "a role change or external move rather than promotion within the current structure"

    signal = f"Your chart shows {visibility} professional visibility and authority ahead."
    detail = f"Growth is more likely through {route_detail}."
    return {"visibility": visibility, "route": route, "how": how,
            "signal": signal, "detail": detail, "year": peak_year}


def _income_periods(dims, life_stage, g):
    """Q5: When will my income and career growth improve?"""
    venus = _d(g, "Venus")
    jupiter = _d(g, "Jupiter")
    fin_strength = _avg(venus, jupiter)
    stability = dims["stability"]
    entrepreneurial = dims["entrepreneurial"]

    if fin_strength >= 62 and stability >= 60:
        shape = "steady-compound"
        signal = "Your chart indicates a compounding financial trajectory — each phase builds on the last."
    elif entrepreneurial >= 65:
        shape = "step-up"
        signal = "Your chart indicates income growth in steps — periods of plateau, then a step up."
    else:
        shape = "gradual"
        signal = "Your chart indicates a gradual but dependable earning trajectory."

    peak_band = max(life_stage, key=lambda b: b["score"])
    return {"shape": shape, "signal": signal,
            "peak_band": peak_band["band"],
            "peak_band_label": f"ages {peak_band['band']}",
            "financial_strength": fin_strength}


def _business_verdict(naukri):
    """Q6: Should I stay in a job or start my own business?"""
    label = naukri["label"]
    lean = naukri["lean"]
    score = naukri["apnakaam_score"]

    if label == "Naukri-leaning":
        verdict = "Career-leaning"
        signal = "One path shows stronger long-term potential for you."
        detail = ("Your chart leans toward building wealth through a senior career "
                  "or advisory role, with enterprise as a strong secondary option.")
    elif label == "Apnakaam-leaning":
        verdict = "Business-leaning"
        signal = "One path shows stronger long-term potential for you."
        detail = ("Your chart leans toward building through ownership and enterprise, "
                  "with a structured career as the dependable base.")
    else:
        verdict = "Balanced"
        signal = "Both paths show potential — the combined play may be your strongest."
        detail = ("Your chart reads close to even between career and enterprise. "
                  "A hybrid approach — ownership within a structured setting — may suit you best.")
    return {"verdict": verdict, "signal": signal, "detail": detail,
            "score": round(score), "lean": lean}


def _three_year_phases(phase, peak_year, three_year, today=None):
    """Q7: What will the next 3 years of my career look like?"""
    PHASE_MAP = {
        1: ["The window — make the move", "Build on the move", "Consolidate the gain"],
        2: ["Position and prepare", "The window — make the move", "Consolidate the gain"],
        3: ["Position and prepare", "Build momentum", "The window — make the move"],
    }
    phases = PHASE_MAP.get(peak_year, PHASE_MAP[2])
    yr = today.year if today else datetime.utcnow().year
    year_labels = [str(yr), str(yr + 1), str(yr + 2)]
    return {"year_phases": phases, "peak_year": peak_year,
            "best_window": three_year.get("best_window"),
            "year_labels": year_labels}


def _best_role(archetype, dims, top_dim):
    """Q8: What kind of role/work will bring me the most success?"""
    DIM_ENVIRONMENT = {
        "leadership": "authority and decision-making responsibility",
        "strategic": "complexity, long-horizon planning and analytical depth",
        "independence": "autonomy and self-direction",
        "entrepreneurial": "ownership and a stake in the outcome",
        "risk": "calculated bets and fast-moving opportunities",
        "stability": "structure, reliability and long-term commitment",
    }
    ranked = sorted(dims, key=dims.get, reverse=True)
    top2 = [ranked[0], ranked[1]]
    environment = DIM_ENVIRONMENT.get(top_dim, "room to use your strongest traits")
    return {"archetype": archetype["name"], "top_traits": top2,
            "environment": environment,
            "signal": f"Roles built around {environment}."}


def _twelve_month_focus(phase, peak_year, dims, year_labels=None):
    """Q9: What should I do — and what should I avoid — over the next 12 months?"""
    md_lord = phase["md_lord"]
    ranked = sorted(dims, key=dims.get, reverse=True)
    top = ranked[0]
    bottom = ranked[-1]

    peak_yr = year_labels[peak_year - 1] if year_labels else str(peak_year)

    DIM_LABEL = {"leadership": "leadership visibility", "strategic": "strategic depth",
                 "independence": "independent positioning", "entrepreneurial": "entrepreneurial bets",
                 "risk": "high-stakes opportunities", "stability": "structural foundations"}
    top_action = DIM_LABEL.get(top, "your strongest trait")

    if peak_year == 1:
        do_focus = f"Act on career opportunities now — lean into {top_action}"
        avoid = "Overthinking the timing — your chart says move"
    elif peak_year == 2:
        do_focus = f"Build relationships and visibility — position for {peak_yr}"
        avoid = "Making a premature move before the groundwork is set"
    else:
        do_focus = f"Invest in {top_action} — strengthen your base before {peak_yr}"
        avoid = "Forcing a career move in a preparation phase"

    return {"do": do_focus, "avoid": avoid,
            "signal": f"A concrete plan for what to pursue and what to hold off on."}


def compute_career_intelligence(name: str, dob: str, tob: str, tz: float, lat: float, lon: float,
                                gender: str = "male", place: str = "",
                                employment_situation: str | None = None,
                                experience: str | None = None, time_quality: str = "T0",
                                as_of: datetime = None) -> dict:
    """dob 'YYYY-MM-DD', tob 'HH:MM' local. employment_situation/experience are
    personalization-only (never affect scoring) — same decision as career_growth."""
    local_dt = datetime.fromisoformat(f"{dob}T{tob}:00")
    dt_utc = local_dt - timedelta(hours=tz)
    today = as_of or datetime.utcnow()

    chart = compute_chart(dt_utc, lat, lon)
    g = chart["grahas"]
    ref_sign = chart["lagna_sign"]
    horizon_end = today + timedelta(days=10 * 365.25)
    tree = vimshottari_tree(g["Moon"].lon, dt_utc, horizon_end)
    sig = student_significators(chart, ref_sign)

    dims = _dimensions(g)
    archetype = _archetype(dims)
    decision = _decision_style(g)
    naukri = _naukri_apnakaam_meter(g)
    entre_10 = max(1, min(10, round(naukri["apnakaam_score"] / 10)))  # 1..10

    current_md = next((md for md in tree if md["start"] <= today <= md["end"]), tree[0])
    md_lord = current_md["lord"]
    phase = {"name": MD_TO_PHASE.get(md_lord, "Consolidation & Repositioning"),
             "basis": MD_PHASE_BASIS.get(md_lord, MD_PHASE_BASIS["Saturn"]),
             "md_lord": md_lord, "ends": current_md["end"].strftime("%Y")}

    # 3-year outlook — reuse the shipping vidyarthi window engine (horizon 3y)
    vidy = compute_vidyarthi_report(name, dob, tob, tz, lat, lon, female=(gender == "female"),
                                    time_quality=time_quality, horizon_years=3, as_of=today)
    windows = vidy["windows"]
    best_window = max(windows, key=lambda w: w["score"]) if windows else None
    # which of the next 3 years does the best window land in -> "expansion" year
    peak_year = 2
    if best_window:
        wy = datetime.strptime(best_window["start"], "%Y-%m").year - today.year
        peak_year = max(1, min(3, wy + 1))
    three_year = {"peak_year": peak_year,
                  "best_window": _fmt_range(best_window["start"], best_window["end"]) if best_window else None}

    # life-stage momentum (ages 40-60), from the favourability of the dasha in each band
    age = (today - local_dt).days / 365.25
    life_stage = _life_stage_bands(tree, local_dt)

    persona_line = LAGNA_PERSONA[ref_sign]
    about_you = ABOUT_YOU_TRAITS[ref_sign]
    strengths = [{"planet": pl.name, "gift": PLANET_GIFT[pl.name]} for pl in g.values()
                 if pl.dignity in ("own", "exalted") and pl.name in PLANET_GIFT]
    lessons = [{"planet": pl.name, "lesson": PLANET_LESSON[pl.name]} for pl in g.values()
               if (pl.dignity == "debilitated" or pl.combust) and pl.name in PLANET_LESSON]

    top_dim = max(dims, key=dims.get)

    # --- 9-question verdicts (NEW) -------------------------------------------
    bwr = three_year.get("best_window")
    v_outlook = _career_outlook_verdict(phase, windows, peak_year, life_stage)
    v_stay_switch = _stay_switch_verdict(phase, windows, peak_year, dims)
    v_window = _best_window_verdict(windows, peak_year, three_year)
    v_promotion = _promotion_outlook(g, dims, windows, peak_year)
    v_income = _income_periods(dims, life_stage, g)
    v_business = _business_verdict(naukri)
    v_3year = _three_year_phases(phase, peak_year, three_year, today=today)
    v_role = _best_role(archetype, dims, top_dim)
    v_12month = _twelve_month_focus(phase, peak_year, dims, year_labels=v_3year["year_labels"])

    verdicts = {
        "outlook": v_outlook,           # Q1
        "stay_switch": v_stay_switch,   # Q2
        "window": v_window,             # Q3
        "promotion": v_promotion,       # Q4
        "income": v_income,             # Q5
        "business": v_business,         # Q6
        "three_year": v_3year,          # Q7
        "role": v_role,                 # Q8
        "twelve_month": v_12month,      # Q9
    }

    teaser = {
        "name": name,
        "dob": dob,
        "tob": tob,
        "place": place,
        "archetype": archetype["name"],
        "archetype_blurb": archetype["blurb"],
        "top_dimension": top_dim,
        "phase": phase["name"],
        "entrepreneurial_10": entre_10,
        "quote": about_you.get("strength") or persona_line,
        "best_environment": NEED_BY_DIM.get(top_dim, "room to do your best work"),
        "dimensions": {k: _disp(v) for k, v in dims.items()},
        "about_you": about_you,
        "decision_style": decision["name"],
        "current_md": md_lord,
        "md_ends": phase["ends"],
        "chart": {
            "lagna_en": SIGNS_EN[ref_sign],
            "ref_sign": ref_sign,
            "planets": {p.name: {"sign_en": SIGNS_EN[p.sign], "sign": p.sign,
                                  "dignity": p.dignity, "retro": p.retro}
                        for p in g.values()},
        },
    }

    return {
        "product": "career_intelligence",
        "meta": {"name": name, "generated": today.strftime("%Y-%m-%d"), "lang": "en"},
        "teaser": teaser,
        "person": {"name": name, "gender": gender, "dob": dob, "tob": tob, "place": place,
                   "employment_situation": employment_situation, "experience": experience},
        "chart": {"lagna": SIGNS[ref_sign], "lagna_en": SIGNS_EN[ref_sign],
                  "planets": {p.name: {"sign": SIGNS[p.sign], "sign_en": SIGNS_EN[p.sign],
                                       "dignity": p.dignity, "retro": p.retro,
                                       "combust": p.combust, "dscore": _d(g, p.name)} for p in g.values()}},
        "ref_sign": ref_sign, "persona_line": persona_line, "about_you": about_you,
        "dimensions": dims, "archetype": archetype, "decision_style": decision,
        "entrepreneurial": {"score_10": entre_10, "lean": naukri["lean"], "label": naukri["label"]},
        "phase": phase, "three_year": three_year, "life_stage": life_stage,
        "windows": windows, "best_window": best_window,
        "verdicts": verdicts,
        "strengths": strengths, "lessons": lessons,
        "sade_sati": _sade_sati(g["Moon"].sign, today),
        "current_md": md_lord,
    }


def _life_stage_bands(tree, birth_dt):
    """Momentum 0..100 for each of ages 40-45/45-50/50-55/55-60, from the natural
    benefic/malefic weight of the mahadasha(s) running in that band. TEMP heuristic."""
    WEIGHT = {"Jupiter": 90, "Venus": 78, "Mercury": 74, "Sun": 68, "Moon": 62,
              "Rahu": 66, "Mars": 60, "Saturn": 64, "Ketu": 50}
    bands = [(40, 45), (45, 50), (50, 55), (55, 60)]
    out = []
    for a0, a1 in bands:
        b_start = birth_dt + timedelta(days=a0 * 365.25)
        b_end = birth_dt + timedelta(days=a1 * 365.25)
        # weighted by how much of the band each MD covers
        acc, span = 0.0, (b_end - b_start).days or 1
        for md in tree:
            ov = (min(md["end"], b_end) - max(md["start"], b_start)).days
            if ov > 0:
                acc += WEIGHT.get(md["lord"], 60) * ov
        out.append({"band": f"{a0}–{a1}", "score": round(acc / span) if acc else 60})
    return out


if __name__ == "__main__":  # ponytail: one runnable self-check
    r = compute_career_intelligence("Rajesh Menon", "1972-03-14", "10:30", 5.5,
                                    12.9716, 77.5946, place="Bengaluru",
                                    as_of=datetime(2026, 8, 28))
    d = r["dimensions"]
    print("archetype :", r["archetype"]["name"], "| runner-up:", r["archetype"]["runner_up"])
    print("dimensions:", d)
    print("decision  :", r["decision_style"]["name"])
    print("phase     :", r["phase"]["name"], "(", r["current_md"], "MD )")
    print("entre /10 :", r["entrepreneurial"]["score_10"], "| lean", r["entrepreneurial"]["lean"])
    print("3-year    : peak year", r["three_year"]["peak_year"], "| best", r["three_year"]["best_window"])
    print("life-stage:", [(b["band"], b["score"]) for b in r["life_stage"]])
    # invariants
    assert all(0 <= v <= 100 for v in d.values()), "dimension out of range"
    assert 1 <= r["entrepreneurial"]["score_10"] <= 10
    assert r["archetype"]["name"] in ARCHETYPES
    assert len(r["life_stage"]) == 4 and all(0 <= b["score"] <= 100 for b in r["life_stage"])
    print("OK — all invariants hold")


# ============================================================ RENDERER
# render_career_intelligence(payload) reproduces the APPROVED 55-card light-theme
# report (career-intelligence report - v5.pdf) per person. It wraps the approved
# card body (career_intelligence_assets.CI_BODY, captured verbatim from the signed-
# off mock) and swaps in each person's identity + the chart-driven exhibits:
# the six Executive-Snapshot dimensions (tiles + radar), archetype, entrepreneurial
# gauge, current phase, life-stage momentum bars, and the real birth chart.
# Secondary illustrative exhibits (2x2 dots, donut, journey/roadmap arcs, priority
# matrix, strength/comparison/planet bars, leadership dials) keep the approved
# design for now and are a tracked follow-up to data-drive.  Same @page/print
# recipe as every card-per-page product -> production pdfgen renders 55 pages.
import math as _math
from html import escape as _esc
from engine import SIGNS_EN as _SIGNS_EN
from career_intelligence_assets import CI_CSS, CI_DEFS, CI_BODY

_MONTHS = ["January","February","March","April","May","June","July","August",
           "September","October","November","December"]
_PL_ABBR = {"Sun":"Su","Moon":"Mo","Mars":"Ma","Mercury":"Me","Jupiter":"Ju",
            "Venus":"Ve","Saturn":"Sa","Rahu":"Ra","Ketu":"Ke"}
# South-Indian fixed grid, DOM order matching the mock (Pis,Ari,Tau,Gem / Aqu,·,Can / Cap,Leo / Sag,Sco,Lib,Vir)
_KUNDLI_CELLS = [("Pis",11),("Ari",0),("Tau",1),("Gem",2),
                 ("Aqu",10),("__CENTER__",-1),("Can",3),
                 ("Cap",9),("Leo",4),
                 ("Sag",8),("Sco",7),("Lib",6),("Vir",5)]
_DIM_WORD = {"leadership":"leadership","strategic":"strategy","independence":"independence",
             "entrepreneurial":"enterprise","risk":"risk-taking","stability":"stability"}
# radar axes clockwise from top, matching the mock's label layout
_RADAR_AXES = [("leadership",-90),("strategic",-30),("independence",30),
               ("stability",90),("risk",150),("entrepreneurial",210)]


def _dim_label(v: int) -> str:
    return "High" if v >= 78 else "Mod–High" if v >= 62 else "Moderate" if v >= 45 else "Low"


def _fmt_dob(dob: str) -> str:
    y, m, d = dob.split("-")
    return f"{int(d)} {_MONTHS[int(m)-1]} {y}"


def _fmt_gen(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{int(d)} {_MONTHS[int(m)-1]} {y}"


def _radar_bits(dims: dict):
    pts, circ = [], []
    for key, ang in _RADAR_AXES:
        v = max(0.0, min(1.0, dims[key] / 100))
        x = round(150 + 100 * v * _math.cos(_math.radians(ang)), 1)
        y = round(145 + 100 * v * _math.sin(_math.radians(ang)), 1)
        pts.append(f"{x},{y}")
        circ.append(f'<circle cx="{x}" cy="{y}" r="3"/>')
    labels = (f'<text x="150" y="36" text-anchor="middle">LEADERSHIP {dims["leadership"]}</text>'
              f'<text x="248" y="94" text-anchor="start">STRAT. {dims["strategic"]}</text>\n'
              f'      <text x="248" y="198" text-anchor="start">INDEP. {dims["independence"]}</text>'
              f'<text x="150" y="262" text-anchor="middle">STABILITY {dims["stability"]}</text>\n'
              f'      <text x="52" y="198" text-anchor="end">RISK {dims["risk"]}</text>'
              f'<text x="52" y="94" text-anchor="end">ENTREP. {dims["entrepreneurial"]}</text>')
    new = (f'<polygon points="{" ".join(pts)}" fill="rgba(201,163,78,.22)" stroke="#B9862E" stroke-width="2"/>\n'
           f'    <g fill="#B9862E">{"".join(circ)}</g>\n'
           f'    <g font-family="Inter,sans-serif" font-size="9.5" fill="#8A8199" font-weight="600">\n'
           f'      {labels}</g>')
    return new


def _snapshot_html(dims: dict) -> str:
    rows = [("Leadership", "leadership"), ("Strategic thinking", "strategic"),
            ("Independence", "independence"), ("Entrepreneurial", "entrepreneurial"),
            ("Risk appetite", "risk"), ("Stability orient.", "stability")]
    tiles = "\n    ".join(
        f'<div class="scard"><div class="sl">{lab}</div><div class="sv">{_dim_label(dims[k])}</div>'
        f'<div class="bar"><i style="width:{dims[k]}%"></i></div></div>'
        for lab, k in rows)
    return f'<div class="sgrid">\n    {tiles}\n  </div>\n  <div class="herocard">'


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:]


# "What this shows" take, keyed by the person's TOP display dimension. Keeps the
# page-5 conclusion true for every profile (the mock's was shaper-specific).
_TAKE_BY_TOP = {
    "leadership": "You are wired to lead and set direction. Roles that keep you executing someone else's plan will underuse you.",
    "strategic": "You are wired to think ahead and plan the play. Roles that reward routine over judgement will underuse you.",
    "independence": "You are wired to run your own track. Roles that box you into rigid structure will underuse you.",
    "entrepreneurial": "You are wired to build and own the outcome. Roles with no stake in the upside will underuse you.",
    "risk": "You are wired to move on opportunity. Roles that punish bold, timely calls will underuse you.",
    "stability": "You are wired to steady and sustain. Roles built on constant churn will wear you down.",
}


def _page5_prose(ddims: dict) -> dict:
    """Callout / signal-peaks / deliberate-floors / take for the radar page, built
    from the person's DISPLAY dims so the text matches the numbers on the radar.
    (_disp is monotonic, so this ranking equals the raw-dims ranking used for the
    page heading — the page stays internally consistent.)"""
    ranked = sorted(ddims, key=ddims.get, reverse=True)
    W = _DIM_WORD
    t0, t1, t2 = ranked[0], ranked[1], ranked[2]
    lo0, lo1 = ranked[-1], ranked[-2]  # lowest, then second-lowest
    return {
        "callout": (f'{_cap(W[t0])}, {W[t1]} and {W[t2]} are your load-bearing traits, '
                    f'the ones a role should be built around. {_cap(W[lo0])} and {W[lo1]} '
                    f'sit lower by design, not deficit.'),
        "peaks": (f'<b>Signal peaks.</b> {_cap(W[t0])} ({ddims[t0]}) and {W[t1]} '
                  f'({ddims[t1]}) are your load-bearing dimensions.'),
        "floors": (f'<b>Deliberate floors.</b> {_cap(W[lo0])} ({ddims[lo0]}) and {W[lo1]} '
                   f'({ddims[lo1]}) sit low by design, not deficit.'),
        "take": _TAKE_BY_TOP[ranked[0]],
    }


# page-8 "Strengths, ranked" — the mock's five invented traits are replaced with the
# person's own six dimensions ranked, so the bars agree with the radar on page 5.
_DIM_BAR_LABEL = {"leadership": "Leadership", "strategic": "Strategic thinking",
                  "independence": "Independence", "entrepreneurial": "Enterprise drive",
                  "risk": "Risk appetite", "stability": "Stability & follow-through"}


def _ranked_bars_html(ddims: dict) -> str:
    order = sorted(ddims, key=ddims.get, reverse=True)
    return "\n    ".join(
        f'<div class="bx"><div class="bl">{_DIM_BAR_LABEL[k]} <span>{ddims[k]}</span></div>'
        f'<div class="bt"><i style="width:{ddims[k]}%"></i></div></div>'
        for k in order)


def _page8_prose(ddims: dict) -> dict:
    ranked = sorted(ddims, key=ddims.get, reverse=True)
    W = _DIM_WORD
    t0, t1, t2, lo = ranked[0], ranked[1], ranked[2], ranked[-1]
    return {
        "heading": f"{_cap(W[t0])} and {W[t1]} lead; {W[lo]} trails.",
        "bars": _ranked_bars_html(ddims),
        "leg1": (f'<b>Your top band.</b> {_cap(W[t0])}, {W[t1]} and {W[t2]} are the '
                 f'traits to build a role around.'),
        "leg2": (f'<b>{_cap(W[lo])} sits lower.</b> A preference, not a gap; you let '
                 f'your strongest traits carry the load.'),
        "take": (f'Your edge is in {W[t0]} and {W[t1]}, not {W[lo]}. Position where your '
                 f'strongest traits are the product.'),
    }


def _lifebars_html(bands: list) -> str:
    xs = [50, 108, 166, 224]
    peak = max(range(4), key=lambda i: bands[i]["score"])
    rects = []
    for i, bd in enumerate(bands):
        h = round(30 + bd["score"] * 0.95)          # 30..~125 px
        y = 165 - h
        fill = "#B9862E" if i == peak else "#C9A34E" if bd["score"] >= 68 else "#A6791E"
        rects.append(f'<rect x="{xs[i]}" y="{y}" width="42" height="{h}" rx="4" fill="{fill}"/>')
    return "<g>\n      " + "\n      ".join(rects) + "\n    </g>"


def _kundli_html(payload: dict) -> str:
    planets = payload["chart"]["planets"]
    by_sign = {}
    for pname, info in planets.items():
        idx = _SIGNS_EN.index(info["sign_en"]) if info["sign_en"] in _SIGNS_EN else None
        if idx is not None:
            by_sign.setdefault(idx, []).append(_PL_ABBR.get(pname, pname[:2]))
    first = _esc(payload["person"]["name"].split()[0]) if payload["person"]["name"].strip() else "You"
    cells = []
    for lab, sidx in _KUNDLI_CELLS:
        if lab == "__CENTER__":
            cells.append(f'<div class="kc center"><b>{first}</b><span>D-1 · Lahiri</span></div>')
            continue
        occ = by_sign.get(sidx)
        pl = f'<span class="pl">{" ".join(occ)}</span>' if occ else ""
        cells.append(f'<div class="kc">{lab}{pl}</div>')
    # rebuild with the mock's row grouping (line breaks are cosmetic)
    body = (f'{cells[0]}{cells[1]}{cells[2]}{cells[3]}\n    '
            f'{cells[4]}{cells[5]}{cells[6]}\n    '
            f'{cells[7]}{cells[8]}\n    '
            f'{cells[9]}{cells[10]}{cells[11]}{cells[12]}')
    return f'<div class="kundli">\n    {body}\n  </div>'


# --- decision-making style: per-style copy + which 2x2 cell lights up -----------
# keyed by (deliberate, evidence) — the booleans _decision_style() returns. The p13
# 2x2 axes are top=FAST / bottom=DELIBERATE, left=INSTINCT / right=EVIDENCE, so each
# (deliberate, evidence) pair maps to exactly one quadrant. `cell` = (label, tint_x,
# tint_y, label_x, label_y, dot_x, dot_y). Copy is non-deterministic and Meta-safe.
_DECISION_CONTENT = {
    (True, True): {                                    # deliberate + evidence -> BR
        "verdict": "The Analyst — you gather, weigh, then commit firmly",
        "lead": "You slow down before large decisions and speed up once you have decided. This serves you well on consequential, hard-to-reverse choices.",
        "watch": "The same care can become over-analysis on smaller, reversible calls. Not every decision deserves the full process.",
        "heading": 'Deliberate and <span style="white-space:nowrap">evidence-led</span> — an Analyst.',
        "cell": ("The Analyst", 155, 135, 210, 190, 210, 206)},
    (False, True): {                                   # fast + evidence -> TR
        "verdict": "The Fast Analyst — you read the evidence quickly, then move",
        "lead": "You move quickly, but on evidence rather than impulse. You are comfortable deciding once the signal is clear, without waiting for full certainty.",
        "watch": "Fast and evidence-led is a strong mix — just be sure the signal is really there before you call it.",
        "heading": 'Fast but <span style="white-space:nowrap">evidence-led</span> — a Fast Analyst.',
        "cell": ("Fast Analyst", 155, 30, 210, 86, 210, 104)},
    (True, False): {                                   # deliberate + instinct -> BL
        "verdict": "The Conservative — you move deliberately, on trusted judgement",
        "lead": "You take your time and lean on what has worked before. This gives you steadiness on decisions others tend to rush.",
        "watch": "Deliberate and proven is safe, but can hold you back when a situation genuinely calls for a new approach.",
        "heading": 'Deliberate and <span style="white-space:nowrap">judgement-led</span> — a Conservative.',
        "cell": ("Conservative", 45, 135, 100, 193, 100, 209)},
    (False, False): {                                  # fast + instinct -> TL
        "verdict": "The Risk Taker — you decide fast and back your read",
        "lead": "You decide quickly and trust your read of a situation. This serves you well when speed matters and the window is short.",
        "watch": "The same speed can skip useful evidence on big, one-way calls. Slow down where a decision is hard to reverse.",
        "heading": 'Fast and <span style="white-space:nowrap">instinct-led</span> — a Risk Taker.',
        "cell": ("Risk Taker", 45, 30, 100, 86, 100, 104)},
}
_DEC_MUTED = {"Risk Taker": (100, 86), "Fast Analyst": (210, 86),
              "Conservative": (100, 193), "The Analyst": (210, 190)}


def _decision_svg(deliberate: bool, evidence: bool) -> str:
    """The p13 decision 2×2 with the person's quadrant highlighted (tint + gold label + dot)."""
    win, tx, ty, lx, ly, dx, dy = _DECISION_CONTENT[(deliberate, evidence)]["cell"]
    muted = "".join(f'<text x="{x}" y="{y}">{lab}</text>'
                    for lab, (x, y) in _DEC_MUTED.items() if lab != win)
    return (
        '<svg viewBox="0 0 300 278" width="100%" style="max-width:322px;margin-top:10px" role="img" aria-label="Decision style 2 by 2">\n'
        f'    <rect x="{tx}" y="{ty}" width="110" height="105" fill="rgba(201,163,78,.13)"/>\n'
        '    <rect x="45" y="30" width="220" height="210" fill="none" stroke="#DCCFB2"/>\n'
        '    <line x1="155" y1="30" x2="155" y2="240" stroke="#DCCFB2"/><line x1="45" y1="135" x2="265" y2="135" stroke="#DCCFB2"/>\n'
        '    <g font-family="Inter,sans-serif" font-size="9" fill="#8A8199" font-weight="600">\n'
        '      <text x="155" y="20" text-anchor="middle">FAST</text><text x="155" y="260" text-anchor="middle">DELIBERATE</text>\n'
        '      <text x="34" y="135" text-anchor="middle" transform="rotate(-90 34 135)">INSTINCT</text><text x="281" y="135" text-anchor="middle" transform="rotate(90 281 135)">EVIDENCE</text></g>\n'
        f'    <g font-family="Inter,sans-serif" font-size="10" fill="#A79A7E" text-anchor="middle">{muted}</g>\n'
        f'    <text x="{lx}" y="{ly}" text-anchor="middle" font-family="Fraunces,Georgia,serif" font-size="13" fill="#B9862E" font-weight="600">{win}</text>\n'
        f'    <circle cx="{dx}" cy="{dy}" r="3.2" fill="#B9862E"/>\n'
        '  </svg>')


def render_career_intelligence(payload: dict) -> str:
    p = payload
    dims = p["dimensions"]                       # RAW — drives the title ranking (below)
    ddims = {k: _disp(v) for k, v in dims.items()}  # DISPLAY-calibrated — drives the shown charts
    person = p["person"]
    body = CI_BODY

    # --- identity (v2 cover metadata blocks; kundli centre handled separately) ---
    name = _esc(person["name"])
    place = _esc(person.get("place") or "")
    dob_line = _fmt_dob(person["dob"]) + (f" · {place}" if place else "")
    body = body.replace(">Rajesh Menon<", f">{name}<")
    body = body.replace("Thank you, Rajesh</h2>", f"Thank you, {name.split()[0]}</h2>")
    body = body.replace(">14 March 1972 · Bengaluru<", f">{dob_line}<")
    body = body.replace("Report prepared 28 August 2026",
                        f"Report prepared {_fmt_gen(p['meta']['generated'])}")

    # --- executive snapshot tiles ---
    body = body.replace(
        '<div class="sgrid">\n    <div class="scard"><div class="sl">Leadership</div><div class="sv">High</div><div class="bar"><i style="width:86%"></i></div></div>\n    <div class="scard"><div class="sl">Strategic thinking</div><div class="sv">High</div><div class="bar"><i style="width:88%"></i></div></div>\n    <div class="scard"><div class="sl">Independence</div><div class="sv">High</div><div class="bar"><i style="width:82%"></i></div></div>\n    <div class="scard"><div class="sl">Entrepreneurial</div><div class="sv">Moderate</div><div class="bar"><i style="width:58%"></i></div></div>\n    <div class="scard"><div class="sl">Risk appetite</div><div class="sv">Mod–High</div><div class="bar"><i style="width:66%"></i></div></div>\n    <div class="scard"><div class="sl">Stability orient.</div><div class="sv">Moderate</div><div class="bar"><i style="width:54%"></i></div></div>\n  </div>\n  <div class="herocard">',
        _snapshot_html(ddims))

    # --- radar polygon + labels ---
    body = body.replace(
        '<polygon points="150,59 227.4,100.3 220.7,178.2 150,201.7 92.3,177.6 100.4,114.9" fill="rgba(201,163,78,.22)" stroke="#B9862E" stroke-width="2"/>\n    <g fill="#B9862E"><circle cx="150" cy="59" r="3"/><circle cx="227.4" cy="100.3" r="3"/><circle cx="220.7" cy="178.2" r="3"/><circle cx="150" cy="201.7" r="3"/><circle cx="92.3" cy="177.6" r="3"/><circle cx="100.4" cy="114.9" r="3"/></g>\n    <g font-family="Inter,sans-serif" font-size="9.5" fill="#8A8199" font-weight="600">\n      <text x="150" y="36" text-anchor="middle">LEADERSHIP 86</text><text x="248" y="94" text-anchor="start">STRATEGIC 88</text>\n      <text x="248" y="198" text-anchor="start">INDEP. 82</text><text x="150" y="262" text-anchor="middle">STABILITY 54</text>\n      <text x="52" y="198" text-anchor="end">RISK 66</text><text x="52" y="94" text-anchor="end">ENTREP. 58</text></g>',
        _radar_bits(ddims))

    # --- radar action title (top-2 vs bottom dimension) ---
    ranked = sorted(dims, key=dims.get, reverse=True)
    top2 = f"{_DIM_WORD[ranked[0]]} and {_DIM_WORD[ranked[1]]}"
    bottom = _DIM_WORD[ranked[-1]]
    body = body.replace(
        "Your strengths cluster on strategy and independence — not stability.",
        f"Your strengths cluster on {top2} — not {bottom}.")

    # --- page-5 profile prose (callout / peaks / floors / take) kept in sync with the radar ---
    pr = _page5_prose(ddims)
    body = body.replace(
        "Leadership, strategy and independence are your load-bearing traits — the ones a role should be built around. Entrepreneurial drive and stability sit lower by design: you back the bet you understand, and you value movement over standing still.",
        pr["callout"])
    body = body.replace(
        "<b>Signal peaks.</b> Strategy (88) and leadership (86) are your load-bearing dimensions.",
        pr["peaks"])
    body = body.replace(
        "<b>Deliberate floors.</b> Stability (54) and entrepreneurial (58) sit low by design, not deficit.",
        pr["floors"])
    body = body.replace(
        "You are wired to shape and decide, not to hold steady. Roles that reward stability over judgement will underuse you.",
        pr["take"])

    # --- page-8 "Strengths, ranked" bars + prose, driven by the same six dims ---
    p8 = _page8_prose(ddims)
    body = body.replace("Judgement and structure lead; visibility trails.", p8["heading"])
    body = body.replace(
        '<div class="bx"><div class="bl">Strategic thinking <span>92</span></div><div class="bt"><i style="width:92%"></i></div></div>\n'
        '    <div class="bx"><div class="bl">Follow-through <span>88</span></div><div class="bt"><i style="width:88%"></i></div></div>\n'
        '    <div class="bx"><div class="bl">Long-horizon patience <span>85</span></div><div class="bt"><i style="width:85%"></i></div></div>\n'
        '    <div class="bx"><div class="bl">Quiet authority <span>80</span></div><div class="bt"><i style="width:80%"></i></div></div>\n'
        '    <div class="bx"><div class="bl">Public visibility <span>48</span></div><div class="bt"><i style="width:48%"></i></div></div>',
        p8["bars"])
    body = body.replace(
        '<b>The 80-plus band</b> — thinking, finishing, and holding the line over years.',
        p8["leg1"])
    body = body.replace(
        '<b>Visibility at 48</b> — a preference, not a gap; you let the work argue for you.',
        p8["leg2"])
    body = body.replace(
        "Your edge is in thinking and finishing, not in being seen. Position where judgement is the product.",
        p8["take"])

    # --- archetype name (4 spots) + blurb ---
    arch = p["archetype"]["name"]
    arch_short = arch.replace("The ", "")
    body = body.replace("The Strategic Builder", arch)
    body = body.replace("Strategic Builder", arch_short)
    body = body.replace(
        "You create lasting structures rather than chase quick wins — strongest with complexity, ownership and time.",
        _esc(p["archetype"]["blurb"]))

    # --- entrepreneurial gauge ---
    e10 = p["entrepreneurial"]["score_10"]
    body = body.replace(
        '<div class="gv">6.5<small>/10</small></div><div class="gt"><i style="width:65%"></i></div>',
        f'<div class="gv">{e10}<small>/10</small></div><div class="gt"><i style="width:{e10*10}%"></i></div>')

    # --- current phase name (2 spots) ---
    phase_name = _esc(p["phase"]["name"])
    body = body.replace("Consolidation &amp; Repositioning", phase_name)

    # --- decision-making style (p12 verdict/lead/watch + p13 heading + 2×2 cell) ---
    ds = p["decision_style"]
    dc = _DECISION_CONTENT[(ds["deliberate"], ds["evidence"])]
    body = body.replace(
        '<div class="vt">The Analyst — you gather, weigh, then commit firmly</div>',
        f'<div class="vt">{dc["verdict"]}</div>')
    body = body.replace(
        'You slow down before large decisions and speed up once you have decided. This serves you well on consequential, hard-to-reverse choices.',
        dc["lead"])
    body = body.replace(
        'The same care can become over-analysis on smaller, reversible calls. Not every decision deserves the full process.',
        dc["watch"])
    body = body.replace(
        'Deliberate and <span style="white-space:nowrap">evidence-led</span> — an Analyst.',
        dc["heading"])
    body = re.sub(r'<svg viewBox="0 0 300 278".*?</svg>',
                  lambda _m: _decision_svg(ds["deliberate"], ds["evidence"]),
                  body, count=1, flags=re.S)

    # --- life-stage bars ---
    body = body.replace(
        '<g>\n      <rect x="50" y="110" width="42" height="55" rx="4" fill="#A6791E"/>\n      <rect x="108" y="55" width="42" height="110" rx="4" fill="#C9A34E"/>\n      <rect x="166" y="45" width="42" height="120" rx="4" fill="#B9862E"/>\n      <rect x="224" y="90" width="42" height="75" rx="4" fill="#A6791E"/>\n    </g>',
        _lifebars_html(p["life_stage"]))

    # --- birth chart ---
    body = body.replace(
        '<div class="kundli">\n    <div class="kc">Pis<span class="pl">Ke</span></div><div class="kc">Ari</div><div class="kc">Tau<span class="pl">Ma</span></div><div class="kc">Gem<span class="pl">Su Me</span></div>\n    <div class="kc">Aqu<span class="pl">Sa</span></div><div class="kc center"><b>Rajesh</b><span>D-1 · Lahiri</span></div><div class="kc">Can</div>\n    <div class="kc">Cap</div><div class="kc">Leo<span class="pl">Ju</span></div>\n    <div class="kc">Sag<span class="pl">Ve</span></div><div class="kc">Sco<span class="pl">Mo</span></div><div class="kc">Lib<span class="pl">Ra</span></div><div class="kc">Vir</div>\n  </div>',
        _kundli_html(p))

    # --- narrative prose pages (Part I..VI) personalized from computed data ---
    for _old, _new in ci_narrative.narrative_replacements(p, ddims):
        assert _old in body, f"ci_narrative: stale target not found: {_old[:60]!r}"
        body = body.replace(_old, _new)

    head = ('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            '<title>Career Intelligence Report</title>\n'
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">\n'
            f'<style>{CI_CSS}</style>\n</head>\n<body>\n{CI_DEFS}\n')
    return head + body + "\n</body>\n</html>\n"


if __name__ == "__main__" and os.environ.get("CI_RENDER"):
    r = compute_career_intelligence("Rajesh Menon", "1972-03-14", "10:30", 5.5,
                                    12.9716, 77.5946, place="Bengaluru",
                                    as_of=datetime(2026, 8, 28))
    html = render_career_intelligence(r)
    assert html.count('<section class="page') == 59, "expected 59 cards (Version C: 55 + contents + thank-you + 2 verdict pages)"
    assert r["archetype"]["name"].replace("The ", "") in html
    open("/tmp/ci_render.html", "w").write(html)
    print("rendered OK ->", len(html), "chars, 59 pages; wrote /tmp/ci_render.html")
