"""
Axtroshastra Career Report engine + renderer ("/career-growth" product,
internal product id "career_growth").

compute_career_growth() -- deterministic Jyotish computation, no LLM. Reuses
the same real engines every other product on this site uses:
  - engine.compute_chart() / vimshottari_tree() / _sade_sati() / grade()
  - vidyarthi.py's 10th/11th-house significators + compute_vidyarthi_report()
    (horizon_years=3) for the Switch Windows timing -- the exact same career-
    timing engine the shipping /career (vidyarthi) product uses.
  - products.py's LAGNA_PERSONA / PLANET_GIFT / PLANET_LESSON / CAREER_ARCHETYPE
    and jyotish_maps.py's WEALTH_2L / GAINS_11L / REMEDY_7L text banks.
Three scoring functions (_workplace_archetype, _foreign_potential,
_naukri_apnakaam_meter) are simplified rule engines built from real computed
planetary-dignity scores (Uccha Bala, via vidyarthi._dignity_score) -- ported
from the samples/naukri_engine.py prototype, same TEMP status documented
there: real numbers, simplified rules, pending a dedicated house-based engine.

render_career_growth(payload) -- ports the finalized Career Report HTML
design (built and hand-refined this session) into a template function,
interpolating every value from compute_career_growth()'s output. Uses forced
per-section page breaks (not the fragile dynamic natural-flow packing the
original design prototype used) since pdfgen.py's single-shot
`chrome --print-to-pdf` has no measurement pass and real user content length
varies -- see the PRINT_CSS block below for the full rationale.

Employment-situation / experience (collected on the landing form) are
personalization-only inputs here -- they never affect scoring, windows, or
verdicts (decision confirmed with the product owner).
"""
import os
from datetime import datetime, timedelta
from html import escape

from engine import (
    compute_chart, vimshottari_tree, houses_from, sign_of, SIGN_LORD, SIGNS, SIGNS_EN,
    _sade_sati, grade,
)
from vidyarthi import (
    student_significators, _career_candidates, _dignity_score, compute_vidyarthi_report,
)
from products import LAGNA_PERSONA, PLANET_GIFT, PLANET_LESSON, MD_PHASE
from jyotish_maps import WEALTH_2L, GAINS_11L, REMEDY_7L, REMEDY_NODE
from vidyarthi_maps import HIGHERED_HOUSE

# ---------------------------------------------------------------------------
# Reused/ported field-family taxonomy (10th-lord house placement - 1), same
# table as samples/naukri_engine.py on feature/naukri-switch-report.
FIELD_FAMILIES = [
    ["Technology & Engineering", "Product Management", "Data & Analytics"],
    ["Finance & Banking", "Operations", "Consulting"],
    ["Sales & Business Development", "Marketing & Brand", "Client Relations"],
    ["Real Estate & Assets", "Manufacturing", "Supply Chain"],
    ["Education & Training", "Content & Media", "Design"],
    ["Public Administration", "HR & People", "Legal & Compliance"],
    ["Startups & New Ventures", "Product Management", "Growth & Strategy"],
    ["Research & Analysis", "Finance & Banking", "Consulting"],
    ["Consulting", "Higher Education", "Cross-Border Roles"],
    ["General Management", "Operations", "Technology & Engineering"],
    ["Sales & Business Development", "Marketing & Brand", "Public Relations"],
    ["Design", "Content & Media", "Non-Profit / Social Impact"],
]
FIELD_ANTIFIT_NOTE = [
    "highly repetitive back-office roles with little variety",
    "rigid, low-autonomy operational roles",
    "purely solitary, low-interaction technical roles",
    "fast-pivoting, low-structure environments",
    "high-conflict, adversarial environments",
    "loosely-structured, ambiguity-heavy roles",
    "slow-moving, hierarchy-heavy organisations",
    "purely people-facing, low-analysis roles",
    "narrow, single-skill execution roles",
    "chaotic, undefined early-stage environments",
    "isolated, low-visibility back-end roles",
    "rigid, metrics-only, low-creativity roles",
]

# "About You" — new text bank (indexed by lagna sign, same order as
# LAGNA_PERSONA/SIGNS_EN: Aries..Pisces). No source existed for this section
# in the reused engines; authored fresh in the same voice as LAGNA_PERSONA.
ABOUT_YOU_TRAITS = [
    {"work_ethic": "Fast-starting — you'd rather act than overplan.",
     "approach": "Direct — you say what needs saying, early and plainly.",
     "attitude": "Bold and competitive — you want to win on merit, not politics.",
     "strength": "A natural first-mover with real initiative."},
    {"work_ethic": "Hardworking — you finish what you start.",
     "approach": "Reliable — people count on your follow-through.",
     "attitude": "Ambitious, but deliberate — not impulsive.",
     "strength": "A steady hand others build on."},
    {"work_ethic": "Quick-adapting — you pick up new work fast.",
     "approach": "Communicative — you think out loud and in writing.",
     "attitude": "Curious and versatile — variety keeps you sharp.",
     "strength": "A clear, persuasive communicator."},
    {"work_ethic": "Committed — you care about the outcome, not just the task.",
     "approach": "Protective — you look out for your team as much as the work.",
     "attitude": "Intuitive, loyalty-driven — you read situations before they're said.",
     "strength": "A trusted, steady presence under pressure."},
    {"work_ethic": "Driven — you want your work to actually matter.",
     "approach": "Visible — you lead from the front, not the sidelines.",
     "attitude": "Confident and generous — you build others up while building yourself.",
     "strength": "A natural, credible leader."},
    {"work_ethic": "Precise — details matter to you more than most.",
     "approach": "Improving — you can't leave a process alone if it's inefficient.",
     "attitude": "Analytical and service-minded — competence over showmanship.",
     "strength": "A dependable problem-solver."},
    {"work_ethic": "Balanced — you pace yourself for the long run.",
     "approach": "Collaborative — you work best alongside people, not around them.",
     "attitude": "Diplomatic and fair — you weigh both sides before deciding.",
     "strength": "A natural relationship-builder."},
    {"work_ethic": "Intense — once committed, you go deep.",
     "approach": "Private, strategic — you play the long game quietly.",
     "attitude": "Transformative — you'd rather rebuild than patch.",
     "strength": "Genuine strategic depth."},
    {"work_ethic": "Expansive — you're motivated by meaning, not just tasks.",
     "approach": "Principled — you say what you believe, even when inconvenient.",
     "attitude": "Optimistic and freedom-loving — you need room to grow.",
     "strength": "A big-picture thinker who inspires others."},
    {"work_ethic": "Structured — you climb in decades, not days.",
     "approach": "Enduring — you outlast problems others give up on.",
     "attitude": "Ambitious and patient — status earned the hard way, not shortcut.",
     "strength": "Genuine staying power."},
    {"work_ethic": "Independent — you work best on your own terms.",
     "approach": "Systemic — you think in structures, not just tasks.",
     "attitude": "Humanitarian and forward-looking — you build for more than yourself.",
     "strength": "An original, future-facing thinker."},
    {"work_ethic": "Fluid — you adapt your effort to what the moment needs.",
     "approach": "Empathetic — you sense what a room needs before it's said.",
     "attitude": "Imaginative and absorbing — you dissolve boundaries between roles.",
     "strength": "A genuinely creative problem-solver."},
]

# Workplace archetype copy — 3 variants, same TEMP status as the scoring
# function below (ported from samples/naukri_engine.py's _workplace_archetype).
WORKPLACE_TEXT = {
    "Diplomat": {
        "para1": "You resolve friction by finding the middle ground, not by pushing harder or "
                 "waiting it out. This reads as a genuine strength in cross-functional or "
                 "client-facing roles — less so in environments that reward blunt confrontation.",
        "para2": "Competition doesn't energise you the way collaboration does — you'll do "
                 "your best work where success is measured in outcomes, not internal rivalry.",
        "best_fit": "Clear goals, light oversight", "team_size": "Small, trusted teams",
        "burnout": "High-pressure, fast-scaling settings — without deliberate pacing",
    },
    "Confronter": {
        "para1": "You resolve friction head-on — direct, fast, and comfortable naming the "
                 "problem rather than working around it. This reads as a genuine strength in "
                 "fast-moving, high-stakes environments — less so in cultures that prize "
                 "consensus over speed.",
        "para2": "Competition energises you rather than draining you — you tend to do your "
                 "best work when there's a clear target to hit or beat.",
        "best_fit": "Clear targets, fast decisions", "team_size": "Lean, high-ownership teams",
        "burnout": "Slow-moving, consensus-heavy organisations",
    },
    "Outlaster": {
        "para1": "You resolve friction by holding steady — outlasting pressure rather than "
                 "reacting to it. This reads as a genuine strength in long-cycle, high-stakes "
                 "work — less so in fast-pivoting environments that reward quick improvisation.",
        "para2": "Competition doesn't rattle you; sustained effort does more for you than short "
                 "bursts of intensity — you're built for the long haul, not the sprint.",
        "best_fit": "Defined processes, long time-horizons", "team_size": "Stable, low-churn teams",
        "burnout": "Chaotic, constantly-shifting priorities without a settled process",
    },
}

DAY_OF_WEEK = {"Sun": "Sunday", "Moon": "Monday", "Mars": "Tuesday", "Mercury": "Wednesday",
               "Jupiter": "Thursday", "Venus": "Friday", "Saturn": "Saturday"}


def _strength_bucket(score: int) -> str:
    if score >= 70:
        return "Strong"
    if score >= 45:
        return "Moderate"
    return "Low"


def _workplace_archetype(g: dict) -> dict:
    """TEMP — no dedicated 6th-house workplace-conflict engine exists yet.
    Built from real Uccha-Bala dignity scores of three relevant karakas: Mars
    (Confronter), Saturn (Outlaster), Mercury (Diplomat). Highest wins. Ported
    from samples/naukri_engine.py; replace when a dedicated engine ships."""
    mars, _ = _dignity_score(g["Mars"])
    sat, _ = _dignity_score(g["Saturn"])
    merc, _ = _dignity_score(g["Mercury"])
    ranked = sorted([("Confronter", mars), ("Outlaster", sat), ("Diplomat", merc)],
                     key=lambda x: -x[1])
    return {"archetype": ranked[0][0], "scores": dict(ranked), "runner_up": ranked[1][0]}


def _foreign_potential(chart: dict, ref_sign: int) -> dict:
    """TEMP — no dedicated 12th-house foreign-potential engine exists yet.
    12th lord's house placement + real dignity score. Ported from
    samples/naukri_engine.py; replace when a dedicated engine ships."""
    g = chart["grahas"]
    twelfth_sign = (ref_sign + 11) % 12
    twelfth_lord = SIGN_LORD[twelfth_sign]
    tl_house = houses_from(ref_sign, g[twelfth_lord].sign)
    score, _ = _dignity_score(g[twelfth_lord])
    rahu_score, _ = _dignity_score(g["Rahu"])
    combined = round((score + rahu_score) / 2)
    return {"level": _strength_bucket(combined), "score": combined,
            "twelfth_lord": twelfth_lord, "twelfth_lord_house": tl_house}


def _naukri_apnakaam_meter(g: dict) -> dict:
    """TEMP — no dedicated Naukri-vs-Apna-Kaam engine exists yet. Saturn
    dignity (structure/employment) vs avg(Mars, Rahu) dignity (independence/
    risk-taking). lean -100..+100, positive = Naukri (job). Ported from
    samples/naukri_engine.py; replace when a dedicated engine ships."""
    sat, _ = _dignity_score(g["Saturn"])
    mars, _ = _dignity_score(g["Mars"])
    rahu, _ = _dignity_score(g["Rahu"])
    apna = round((mars + rahu) / 2)
    lean = sat - apna
    if lean >= 20:
        label = "Naukri-leaning"
    elif lean <= -20:
        label = "Apnakaam-leaning"
    else:
        label = "Balanced"
    return {"lean": lean, "label": label, "naukri_score": sat, "apnakaam_score": apna}


def _phase_label(windows, today) -> str:
    for w in windows:
        s = datetime.strptime(w["start"], "%Y-%m")
        e = datetime.strptime(w["end"], "%Y-%m")
        if s <= today <= e and w["grade"] in ("Strong", "Moderate"):
            return "Move Now"
    return "Wait & Prepare"


def _quiet_stretch(windows, today, horizon_years=3):
    """No 'actively bad, don't resign here' signal exists in the reused
    engine (vidyarthi.grade() only ever returns Strong/Moderate/Building) --
    per the product decision, this reports the largest gap between windows
    (real data: an absence of a qualifying signal) rather than inventing a
    negative verdict. Returns None if no gap is wide enough to be worth
    flagging (< 120 days, matching the engine's own window-merge threshold)."""
    horizon_end = today + timedelta(days=horizon_years * 365.25)
    spans = sorted([(datetime.strptime(w["start"], "%Y-%m"),
                     datetime.strptime(w["end"], "%Y-%m")) for w in windows])
    cursor, best = today, None
    for s, e in spans:
        if s > cursor:
            gap = (s - cursor).days
            if best is None or gap > best[2]:
                best = (cursor, s, gap)
        cursor = max(cursor, e)
    if horizon_end > cursor:
        gap = (horizon_end - cursor).days
        if best is None or gap > best[2]:
            best = (cursor, horizon_end, gap)
    if not best or best[2] < 120:
        return None
    return {"start": best[0].strftime("%Y-%m"), "end": best[1].strftime("%Y-%m")}


def _mon(ym: str) -> str:
    return datetime.strptime(ym, "%Y-%m").strftime("%b")


def _fmt_range(start: str, end: str) -> str:
    if start[:4] == end[:4]:
        return f"{_mon(start)} – {_mon(end)} {end[:4]}"
    return f"{_mon(start)} {start[:4]} – {_mon(end)} {end[:4]}"


def _fmt_date_long(dt: datetime) -> str:
    return f"{dt.day} {dt.strftime('%B %Y')}"


def _verdict_text(naukri_meter: dict) -> dict:
    """Job-vs-Own-Business verdict copy, shared by the teaser (POST /api/kundli
    response) and the full report (render_career_growth) so both always agree —
    single source of truth instead of two independent copies drifting apart."""
    label = naukri_meter.get("label", "Balanced")
    if label == "Naukri-leaning":
        return {"h3": "Job, not Own Business — for now",
                "p": ("Your strengths compound faster inside a team than solo, so structured "
                      "employment reads stronger than independent business right now.")}
    if label == "Apnakaam-leaning":
        return {"h3": "Own Business, Over a Job — worth exploring",
                "p": ("Your strengths read as more self-directed than team-dependent — building "
                      "something of your own reads stronger here than structured employment.")}
    return {"h3": "Balanced — Either Path Can Work",
            "p": ("Your chart doesn't lean hard either way — both structured employment and "
                  "independent business are genuinely open paths; the choice comes down to "
                  "opportunity and personal preference more than chart pressure.")}


def _do_by_month(best_window: dict | None) -> str:
    if not best_window:
        return "soon"
    return (datetime.strptime(best_window["start"], "%Y-%m") - timedelta(days=45)).strftime("%B")


def compute_career_growth(name: str, dob: str, tob: str, tz: float, lat: float, lon: float,
                          gender: str = "male", place: str = "", employment_situation: str | None = None,
                          experience: str | None = None, time_quality: str = "T0",
                          as_of: datetime = None) -> dict:
    """dob 'YYYY-MM-DD', tob 'HH:MM' local. employment_situation/experience are
    personalization-only (never affect scoring/windows/verdicts) -- confirmed
    product decision. Mirrors compute_vidyarthi_report's signature shape for
    consistency with create_kundli's existing product dispatch."""
    local_dt = datetime.fromisoformat(f"{dob}T{tob}:00")
    dt_utc = local_dt - timedelta(hours=tz)
    today = as_of or datetime.utcnow()

    chart = compute_chart(dt_utc, lat, lon)
    g = chart["grahas"]
    ref_sign = chart["lagna_sign"]
    horizon_end = today + timedelta(days=10 * 365.25)

    sig = student_significators(chart, ref_sign)
    tree = vimshottari_tree(g["Moon"].lon, dt_utc, horizon_end)

    persona_line = LAGNA_PERSONA[chart["lagna_sign"]]
    about_you = ABOUT_YOU_TRAITS[chart["lagna_sign"]]
    strengths = [f"{pl.name} — {PLANET_GIFT[pl.name]}" for pl in g.values()
                 if pl.dignity in ("own", "exalted") and pl.name in PLANET_GIFT]
    lessons = [f"{pl.name} — {PLANET_LESSON[pl.name]}" for pl in g.values()
               if (pl.dignity == "debilitated" or pl.combust) and pl.name in PLANET_LESSON]

    tenth_lord_house = sig["tenth_lord_house"]
    field_families = FIELD_FAMILIES[tenth_lord_house - 1]
    field_antifit = FIELD_ANTIFIT_NOTE[tenth_lord_house - 1]
    naukri_meter = _naukri_apnakaam_meter(g)

    sade = _sade_sati(g["Moon"].sign, today)
    current_md = next((md for md in tree if md["start"] <= today <= md["end"]), tree[0])
    current_ad = next((ad for ad in current_md["ads"] if ad["start"] <= today <= ad["end"]),
                      current_md["ads"][0])

    vidy = compute_vidyarthi_report(name, dob, tob, tz, lat, lon, female=(gender == "female"),
                                    time_quality=time_quality, horizon_years=3, as_of=today)
    windows = vidy["windows"]
    quiet_stretch = _quiet_stretch(windows, today, horizon_years=3)

    second_lord = SIGN_LORD[(ref_sign + 1) % 12]
    eleventh_lord = SIGN_LORD[(ref_sign + 10) % 12]
    second_house = houses_from(ref_sign, g[second_lord].sign)
    eleventh_house = houses_from(ref_sign, g[eleventh_lord].sign)
    second_score, _ = _dignity_score(g[second_lord])
    eleventh_score, _ = _dignity_score(g[eleventh_lord])
    wealth = {"second_lord": second_lord, "second_house": second_house,
              "second_text": WEALTH_2L[second_house - 1],
              "eleventh_lord": eleventh_lord, "eleventh_house": eleventh_house,
              "eleventh_text": GAINS_11L[eleventh_house - 1],
              "stability": _strength_bucket(second_score),
              "upside": _strength_bucket(eleventh_score)}

    workplace = _workplace_archetype(g)
    foreign = _foreign_potential(chart, ref_sign)
    ninth_lord = SIGN_LORD[(ref_sign + 8) % 12]
    ninth_house_note = HIGHERED_HOUSE[houses_from(ref_sign, g[ninth_lord].sign) - 1]

    best_window = max(windows, key=lambda w: w["score"]) if windows else None
    switch_outlook = "Favorable" if best_window and best_window["grade"] in ("Strong", "Moderate") \
        else "Building"
    growth_pattern = "Steady & Self-directed" if naukri_meter["label"] == "Apnakaam-leaning" \
        else "Jump-led"
    phase = _phase_label(windows, today)

    if current_md["lord"] in REMEDY_7L:
        remedy_day, remedy_mantra, _gem = REMEDY_7L[current_md["lord"]]
    else:
        remedy_day, remedy_mantra, _gem = REMEDY_NODE.get(current_md["lord"], REMEDY_7L["Saturn"])
    comm_day = DAY_OF_WEEK.get(sig["tenth_lord"], "Wednesday")

    tenth_lord = sig["tenth_lord"]
    strongest_support = next((s for s in strengths if not s.startswith(current_md["lord"])
                              and not s.startswith(tenth_lord)), None)

    verdict = _verdict_text(naukri_meter)
    do_by = _do_by_month(best_window)
    teaser_quote = about_you.get("strength") or persona_line

    teaser = {
        "name": name,
        "switch_outlook": switch_outlook,
        "phase": phase,
        "field_top": field_families[0],
        "windows_count": len(windows),
        "best_window_range": _fmt_range(best_window["start"], best_window["end"]) if best_window else "—",
        "quote": teaser_quote,
        "do_by": do_by,
        "has_quiet_stretch": quiet_stretch is not None,
        "verdict_h3": verdict["h3"],
        "verdict_h3_blurred": "Job, not Own Business" if naukri_meter["label"] != "Apnakaam-leaning"
                              else "Own Business, not a Job",
    }

    return {
        "product": "career_growth",
        "meta": {"name": name, "generated": today.strftime("%Y-%m-%d")},
        "teaser": teaser,
        "verdict": verdict,
        "do_by": do_by,
        "person": {"name": name, "gender": gender, "dob": dob, "tob": tob, "place": place,
                   "employment_situation": employment_situation, "experience": experience},
        "chart": {"lagna": SIGNS[chart["lagna_sign"]],
                  "planets": {p.name: {"sign": SIGNS[p.sign], "nakshatra": None,
                                       "dignity": p.dignity, "retro": p.retro,
                                       "combust": p.combust} for p in g.values()}},
        "sig": sig, "ref_sign": ref_sign,
        "persona_line": persona_line, "about_you": about_you,
        "strengths": strengths, "lessons": lessons,
        "strongest_support": strongest_support,
        "field_families": field_families, "field_antifit": field_antifit,
        "naukri_meter": naukri_meter,
        "sade_sati": sade,
        "current_md": current_md["lord"], "current_ad": current_ad["lord"],
        "windows": windows, "best_window": best_window, "quiet_stretch": quiet_stretch,
        "wealth": wealth,
        "workplace": workplace,
        "foreign": foreign, "ninth_house_note": ninth_house_note,
        "tenth_lord": tenth_lord, "tenth_lord_house": tenth_lord_house,
        "switch_outlook": switch_outlook, "growth_pattern": growth_pattern, "phase": phase,
        "remedy_day": remedy_day, "remedy_mantra": remedy_mantra, "comm_day": comm_day,
    }


# ---------------------------------------------------------------------------
# render_career_growth() -- ports the finalized Career Report HTML design
# (built and hand-refined earlier this session as a standalone prototype)
# into a real template function. Same component CSS/theme as
# pages/marriage.html's .premium-sample block (Fraunces serif, cream/gold),
# every value interpolated from compute_career_growth()'s payload.
#
# PAGINATION: the original design prototype used a two-pass Playwright
# measure-then-inject-forced-breaks algorithm to pack multiple short sections
# per physical page. That pass requires browser scripting (page.evaluate())
# and cannot run inside pdfgen.py's single-shot `chrome --print-to-pdf`
# subprocess call -- and real user content length varies (window count,
# name length, etc.), so the original hand-tuned packing can't be reused
# as-is. Instead: force `page-break-before: always` on every `.rpage`
# section (one-section-per-page), the same reliable approach an earlier
# iteration of the design already validated -- Chrome's print engine does
# not reliably honor soft `page-break-inside: avoid` hints on decorated/
# gradient boxes (a dark card can paint on the wrong page before moving),
# which is exactly why the original design needed forced breaks in the
# first place. Trade-off: page count isn't fixed, but nothing is ever
# clipped. `page-break-inside: avoid` stays on atomic card classes as a
# second line of defense for the rare section too long for one page.
PRINT_CSS = """
@page { size: 210mm 297mm; margin: 14mm; }
* { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.rpage { page-break-before: always; page-break-inside: avoid; break-inside: avoid-page; }
.rpage:first-of-type { page-break-before: auto; }
.house-card, .pair-card, .phase-card, .dodont .card, .tl-row, .stat-row,
.hero-chip, .verdict, .quote, .note { page-break-inside: avoid; break-inside: avoid-page; }
.rpage-kicker { display: none; }
"""


def _window_row_html(w: dict, is_best: bool) -> str:
    dot_cls = "" if w["grade"] == "Strong" else "soft"
    if is_best:
        blurb = "the strongest window — see next page."
    elif w["grade"] == "Strong":
        blurb = "a strong window, worth planning around."
    elif w["grade"] == "Moderate":
        blurb = "a second, meaningful opening."
    else:
        blurb = "early signals, worth watching quietly."
    return (f'<div class="tl-row"><div class="yr-line"><div class="dot {dot_cls}"></div>'
            f'<div class="yr">{escape(_fmt_range(w["start"], w["end"]))}</div></div>'
            f'<div class="d"><b>{escape(w["grade"])}</b> &middot; {blurb}</div></div>')


def _quiet_row_html(qs: dict) -> str:
    return (f'<div class="tl-row"><div class="yr-line"><div class="dot warn"></div>'
            f'<div class="yr">{escape(_fmt_range(qs["start"], qs["end"]))}</div></div>'
            f'<div class="d"><b>Quiet stretch</b> &middot; no strong signal here — '
            f'evaluate opportunities carefully rather than forcing a move.</div></div>')


def _rules_prose(w: dict) -> str:
    whys = [r["why"] for r in w.get("rules_fired", []) if r.get("why")][:2]
    if not whys:
        return ("This window is worth planning around: your current dasha and the transits "
                "moving through it align in its favour.")
    if len(whys) == 1:
        return f"This window is strong because of one clear signal: {whys[0]}."
    return f"This window is strong for two connected reasons: {whys[0]}; and {whys[1]}."


def render_career_growth(payload: dict) -> str:
    p = payload
    person = p.get("person", {})
    name = escape(person.get("name") or "there")
    dob_dt = datetime.strptime(person["dob"], "%Y-%m-%d") if person.get("dob") else None
    born_line = f"Born {escape(_fmt_date_long(dob_dt))}" if dob_dt else ""
    place = escape(person.get("place") or "")
    generated = p.get("meta", {}).get("generated")
    generated_line = _fmt_date_long(datetime.strptime(generated, "%Y-%m-%d")) if generated else ""

    about = p.get("about_you", {})
    windows = p.get("windows", [])
    best_window = p.get("best_window")
    quiet = p.get("quiet_stretch")

    field_families = p.get("field_families", ["—", "—", "—"])
    while len(field_families) < 3:
        field_families = field_families + ["Adjacent, related fields"]

    naukri_meter = p.get("naukri_meter", {"lean": 0, "label": "Balanced"})
    job_fill_pct = max(6, min(100, round((naukri_meter.get("lean", 0) + 100) / 2)))
    verdict = p.get("verdict") or _verdict_text(naukri_meter)
    verdict_h3, verdict_p = verdict["h3"], verdict["p"]

    workplace = p.get("workplace", {"archetype": "Diplomat"})
    wtext = WORKPLACE_TEXT.get(workplace.get("archetype", "Diplomat"), WORKPLACE_TEXT["Diplomat"])

    foreign = p.get("foreign", {"level": "Moderate"})
    foreign_display = {"Strong": "High", "Moderate": "Moderate", "Low": "Limited"}.get(
        foreign.get("level", "Moderate"), "Moderate")
    foreign_go = ' go' if foreign.get("level") == "Strong" else ""

    wealth = p.get("wealth", {})
    stability_go = ' go' if wealth.get("stability") == "Strong" else ""
    upside_go = ' go' if wealth.get("upside") == "Strong" else ""

    switch_outlook = p.get("switch_outlook", "Building")
    outlook_go = ' go' if switch_outlook == "Favorable" else ""

    tenth_lord = p.get("tenth_lord", "the 10th lord")
    current_md = p.get("current_md", "your Mahadasha lord")
    current_ad = p.get("current_ad", "your Antardasha lord")
    md_phase_text = MD_PHASE.get(current_md, "structure and steady effort")

    strongest_support = p.get("strongest_support") or f"{tenth_lord} — {PLANET_GIFT.get(tenth_lord, 'a real strength in this chart')}"
    support_name, _, support_text = strongest_support.partition(" — ")

    window_rows = "".join(_window_row_html(w, is_best=(best_window is not None and w is best_window))
                          for w in windows)
    if quiet:
        window_rows += _quiet_row_html(quiet)

    best_range = _fmt_range(best_window["start"], best_window["end"]) if best_window else "the window above"
    best_rules_prose = _rules_prose(best_window) if best_window else ""

    if len(windows) > 1:
        second = sorted([w for w in windows if w is not best_window], key=lambda w: -w["score"])[0]
        second_para = (f'<p style="font-size:12.5px;line-height:1.65"><b>{escape(_fmt_range(second["start"], second["end"]))}, '
                       f'{escape(second["grade"])}</b> &mdash; a second window worth watching if the '
                       f'{escape(best_range)} window doesn\'t convert, not a reason to wait for it instead.</p>')
    else:
        second_para = ""
    if quiet:
        quiet_para = (f'<p style="font-size:12.5px;line-height:1.65;margin-top:10px"><b>{escape(_fmt_range(quiet["start"], quiet["end"]))}, '
                     f'quiet stretch</b> &mdash; no strong signal in this period. Evaluate opportunities '
                     f'carefully here rather than avoiding action altogether; just don\'t rush anything final.</p>')
    else:
        quiet_para = ('<p style="font-size:12.5px;line-height:1.65;margin-top:10px">No notable quiet '
                     'stretch shows up in the next three years — the windows above are the main '
                     'shape of your timing.</p>')

    do_by = p.get("do_by") or _do_by_month(best_window)

    phase = p.get("phase", "Wait & Prepare")

    fields_p7 = ", ".join(field_families[:3])
    fields_link_p17 = " and ".join(field_families[:2])

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Career Report — {name}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;1,9..144,400&family=Jost:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box}}
body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Noto Sans',sans-serif}}
.premium-sample{{
  --disp:'Fraunces',Georgia,serif;
  --bg:#E9E1D3;--panel:#FBF7EF;--pline:#E7DCC6;--pshadow:rgba(90,60,20,.10);
  --pink:#2A2015;--phead:#3a2c18;--pmuted:#8A8199;--pgold:#C9A34E;--pgold-lt:#E7CE8F;
  --pglow:rgba(201,163,78,.26);
  --tbox:linear-gradient(150deg,#3a2c18,#211509);--tbox-glow:rgba(201,163,78,.30);
  --pcta:#B4674A;--pcta-h:#9A4E35;
  --go:#4F7A5C;--go-soft:#E7EEE3;
  --body:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Noto Sans',sans-serif;
  background:var(--bg);color:var(--pink);font-family:var(--body);line-height:1.6}}

.rbook{{padding:26px 12px 90px}}
.rpage{{max-width:600px;margin:0 auto 22px;background:var(--panel);border:1px solid var(--pline);
  border-radius:20px;box-shadow:0 14px 34px var(--pshadow);overflow:hidden;position:relative}}
.rpage-top{{padding:22px 26px 0}}
.rpage-kicker{{display:flex;justify-content:space-between;align-items:center;font-size:8.5px;
  letter-spacing:.12em;text-transform:uppercase;color:var(--pgold);font-weight:700}}
.rpage-title{{font-family:var(--disp);font-weight:500;font-size:24px;color:var(--phead);margin:8px 0 5px;text-wrap:balance}}
.rpage-sub{{font-size:13px;color:var(--pmuted);margin:0 0 16px;line-height:1.45}}
.rpage-body{{padding:0 26px 26px}}
.rpage-foot{{padding:12px 26px;border-top:1px solid var(--pline);font-size:9px;color:var(--pmuted);
  display:flex;justify-content:space-between}}

.rpage.dark{{background:var(--tbox);color:#F5EEE0}}

.pair-cards{{display:flex;flex-direction:column;gap:12px}}
.pair-card{{background:var(--panel);border:1px solid var(--pline);border-radius:14px;padding:16px 18px;box-shadow:0 5px 14px var(--pshadow)}}
.pair-card h4{{font-family:var(--disp);font-weight:600;font-size:15px;color:var(--phead);margin:0 0 9px}}
.pair-card .row{{padding:8px 0}}
.pair-card .row + .row{{border-top:1px solid var(--pline)}}
.pair-card .k{{font-size:10px;font-weight:700;color:var(--pmuted);text-transform:uppercase;letter-spacing:.04em;display:block;margin-bottom:2px}}
.pair-card .v{{font-size:13px;color:var(--pink);line-height:1.4}}

.phase-card{{background:var(--panel);border:1px solid var(--pline);border-radius:14px;padding:16px 18px;box-shadow:0 5px 14px var(--pshadow)}}
.phase-card + .phase-card{{margin-top:12px}}
.phase-card .ph{{font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--pgold);font-weight:700}}
.phase-card h4{{font-family:var(--disp);font-weight:600;font-size:17px;color:var(--phead);margin:5px 0 10px}}
.phase-card .lbl{{font-size:10px;font-weight:700;color:var(--pmuted);text-transform:uppercase;letter-spacing:.03em;margin:10px 0 3px}}
.phase-card .lbl:first-of-type{{margin-top:0}}
.phase-card p{{font-size:12.5px;color:var(--pink);line-height:1.5;margin:0}}
.phase-card ul{{font-size:12.5px;color:var(--pink);line-height:1.5;margin:2px 0 0;padding-left:16px}}
.phase-card li{{margin-bottom:2px}}
.phase-card .link{{font-size:11.5px;color:var(--pmuted);font-style:italic;line-height:1.5;margin:10px 0 0;padding-top:10px;border-top:1px solid var(--pline)}}

.dodont{{display:flex;flex-direction:column;gap:12px}}
.dodont .card{{border-radius:14px;padding:16px 18px;display:flex;gap:14px;align-items:flex-start}}
.dodont .mark{{flex:0 0 auto;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-family:var(--disp);font-size:15px;font-weight:700}}
.dodont .lbl{{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin-bottom:3px}}
.dodont .card p{{font-size:14px;color:var(--pink);line-height:1.45;margin:0;font-weight:500}}
.dodont .do{{background:var(--go-soft);border:1px solid #CFDFC9}}
.dodont .do .mark{{background:var(--go);color:#fff}}
.dodont .do .lbl{{color:var(--go)}}
.dodont .avoid{{background:rgba(178,58,46,.07);border:1px solid rgba(178,58,46,.25)}}
.dodont .avoid .mark{{background:#B23A2E;color:#fff}}
.dodont .avoid .lbl{{color:#B23A2E}}

.stat-strip{{display:flex;flex-direction:column;border:1px solid var(--pline);border-radius:13px;overflow:hidden}}
.stat-row{{display:flex;flex-direction:column;gap:2px;padding:12px 16px;background:var(--panel);border-top:1px solid var(--pline)}}
.stat-row:first-child{{border-top:0}}
.stat-row .k{{font-size:11px;font-weight:700;color:var(--pmuted);text-transform:uppercase;letter-spacing:.03em}}
.stat-row .v{{font-family:var(--disp);font-size:16px;color:var(--phead)}}
.stat-row .v.go{{color:var(--go)}}

.verdict{{background:var(--tbox);border-radius:16px;padding:22px 22px 20px;color:#F5EEE0;position:relative;overflow:hidden}}
.verdict .eb{{color:var(--pgold-lt);position:relative;font-size:10px;letter-spacing:.12em;text-transform:uppercase;font-weight:700}}
.verdict h3{{font-family:var(--disp);font-weight:500;font-size:23px;margin:8px 0 8px;position:relative}}
.verdict p{{font-size:13.5px;color:rgba(240,232,218,.86);position:relative;margin:0;line-height:1.55}}

.hero-chip{{background:var(--tbox);border-radius:16px;padding:20px 22px;color:#F5EEE0;text-align:center;position:relative;overflow:hidden}}
.hero-chip .eb{{position:relative;color:var(--pgold-lt);font-size:10px;letter-spacing:.14em;text-transform:uppercase;font-weight:700}}
.hero-chip .rng{{position:relative;font-family:var(--disp);font-weight:600;font-size:26px;margin-top:7px}}

.meter{{margin-top:16px}}
.meter-track{{height:8px;border-radius:8px;background:var(--pline);position:relative;overflow:hidden}}
.meter-fill{{position:absolute;left:0;top:0;bottom:0;background:linear-gradient(90deg,var(--pgold-lt),var(--pgold));border-radius:8px}}
.meter-labels{{display:flex;justify-content:space-between;font-size:10px;color:var(--pmuted);margin-top:7px;font-weight:600}}

.tl-col{{display:flex;flex-direction:column;gap:9px}}
.tl-row{{display:flex;flex-direction:column;gap:3px;background:var(--panel);border:1px solid var(--pline);border-radius:12px;padding:13px 16px}}
.tl-row .yr-line{{display:flex;align-items:center;gap:10px}}
.tl-row .dot{{width:10px;height:10px;border-radius:50%;background:var(--pgold);flex:0 0 auto}}
.tl-row .dot.soft{{background:var(--pline);border:2px solid var(--pgold)}}
.tl-row .dot.warn{{background:#B23A2E}}
.tl-row .yr{{font-family:var(--disp);font-weight:500;font-size:15.5px;color:var(--phead)}}
.tl-row .d{{font-size:12.5px;color:var(--pmuted);line-height:1.45;padding-left:20px}}
.tl-row .d b{{color:var(--pink);font-weight:600}}

.checklist{{display:flex;flex-direction:column;gap:9px}}
.chk{{display:flex;gap:10px;align-items:flex-start;font-size:13px;color:var(--pink);line-height:1.45}}
.chk .box{{width:15px;height:15px;border:1.5px solid var(--pgold);border-radius:4px;flex:0 0 auto;margin-top:1px}}

.house-card{{display:flex;gap:12px;align-items:flex-start;background:var(--panel);border:1px solid var(--pline);border-radius:14px;padding:16px}}
.house-card .badge{{flex:0 0 auto;width:38px;height:38px;border-radius:50%;background:var(--tbox);color:var(--pgold-lt);
  display:flex;align-items:center;justify-content:center;font-family:var(--disp);font-size:14px}}
.house-card h4{{font-family:var(--disp);font-weight:600;font-size:15px;color:var(--phead);margin:0 0 5px}}
.house-card p{{font-size:12.5px;color:var(--pmuted);margin:0;line-height:1.5}}
.house-card p b{{color:var(--pink)}}

.quote{{font-family:var(--disp);font-style:italic;font-size:16px;color:var(--phead);text-align:center;
  padding:16px 10px;border-top:1px solid var(--pline);border-bottom:1px solid var(--pline);margin:16px 0;line-height:1.4}}
.note{{font-size:11.5px;color:#8A6B2E;background:#F8F1DE;border:1px solid var(--pgold-lt);border-radius:9px;padding:11px 13px;font-style:italic;line-height:1.4}}

.cover-hero{{text-align:center}}
.cover-hero svg{{width:32px;height:32px;margin-bottom:13px}}
.cover-brand{{font-size:14px;letter-spacing:.18em;text-transform:uppercase;color:var(--pgold-lt)}}
.cover-title{{font-family:var(--disp);font-weight:500;font-size:38px;color:#fff;margin:15px 0 8px;line-height:1.15}}
.cover-subtitle{{font-size:16px;color:rgba(240,232,218,.8)}}
.cover-meta{{font-size:13.5px;color:rgba(240,232,218,.75);line-height:1.75;margin-top:18px}}
.cover-rule{{width:56px;height:2px;background:var(--pgold-lt);margin:30px auto;border-radius:2px;opacity:.55}}
.cover-inside{{text-align:center}}
.cover-inside .rpage-title{{font-size:26px;line-height:1.2;margin:0 0 20px;color:#fff}}
.cover-inside-grid{{display:grid;grid-template-columns:1fr 1fr;gap:13px;text-align:left}}
.cover-inside-full{{grid-column:1 / -1}}
.cover-inside .house-card{{background:rgba(255,255,255,.055);border:1px solid rgba(228,176,74,.3);box-shadow:none;padding:14px}}
.cover-inside .house-card .badge{{width:30px;height:30px;font-size:13px;background:rgba(228,176,74,.16);color:var(--pgold-lt);border:1px solid rgba(228,176,74,.4)}}
.cover-inside .house-card h4{{font-size:14.5px;color:#fff}}
.cover-inside .house-card p{{font-size:12.3px;color:rgba(240,232,218,.6)}}
.cover-inside-closing{{font-size:13px;line-height:1.55;color:rgba(240,232,218,.55);margin:18px 0 0}}

{PRINT_CSS}
</style>
</head>
<body>
<div class="premium-sample">
<div class="rbook">

  <section class="rpage dark" id="p1">
    <div class="rpage-body cover-merged" style="padding-top:36px;padding-bottom:30px">
      <div class="cover-hero">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M12 2 L14.5 9.5 L22 12 L14.5 14.5 L12 22 L9.5 14.5 L2 12 L9.5 9.5 Z" fill="#E4B04A"/></svg>
        <div class="cover-brand">Axtroshastra</div>
        <h1 class="cover-title">Career Report</h1>
        <div class="cover-subtitle">Career Timing &amp; Decision Analysis</div>
        <div class="cover-meta">
          Prepared for <b style="color:#fff">{name}</b><br>
          {born_line}{" &middot; " + place if born_line and place else place}<br>
          Report generated {escape(generated_line)}
        </div>
      </div>
      <div class="cover-rule"></div>
      <div class="cover-inside">
        <div class="rpage-title">What's Inside Your Report</div>
        <div class="cover-inside-grid">
          <div class="house-card"><div class="badge">1</div><div><h4>Who You Are</h4><p>Your natural work style, decision-making, strengths and growth edge &mdash; how you're wired to operate.</p></div></div>
          <div class="house-card"><div class="badge">2</div><div><h4>Where You're Headed</h4><p>Which fields fit you best, and whether this chart favours a job or your own venture.</p></div></div>
          <div class="house-card"><div class="badge">3</div><div><h4>Your Timing</h4><p>The hero of this report: your current phase, and the exact windows ahead &mdash; graded Strong, Moderate or a quieter stretch.</p></div></div>
          <div class="house-card"><div class="badge">4</div><div><h4>Life Beyond the Move</h4><p>How your income tends to grow, your workplace style, and your relocation potential.</p></div></div>
          <div class="house-card cover-inside-full"><div class="badge">5</div><div><h4>Your Plan</h4><p>A 90-day roadmap, light remedies, and a one-page summary of everything above.</p></div></div>
        </div>
        <p class="cover-inside-closing">The closing pages explain the astrology behind every insight above &mdash; houses, planets, dashas and transits, connected step by step.</p>
      </div>
    </div>
  </section>

  <section class="rpage" id="p3">
    <div class="rpage-top">
      <div class="rpage-title">About You</div>
      <div class="rpage-sub">A quick read on your career personality, before the analysis begins.</div>
    </div>
    <div class="rpage-body">
      <div class="pair-cards">
        <div class="pair-card">
          <h4>How You Work</h4>
          <div class="row"><span class="k">Work Ethic</span><span class="v">{escape(about.get("work_ethic",""))}</span></div>
          <div class="row"><span class="k">Approach to Work</span><span class="v">{escape(about.get("approach",""))}</span></div>
        </div>
        <div class="pair-card">
          <h4>Your Professional Edge</h4>
          <div class="row"><span class="k">Career Attitude</span><span class="v">{escape(about.get("attitude",""))}</span></div>
          <div class="row"><span class="k">Professional Strength</span><span class="v">{escape(about.get("strength",""))}</span></div>
        </div>
      </div>
    </div>
  </section>

  <section class="rpage" id="p4">
    <div class="rpage-top">
      <div class="rpage-title">Summary</div>
      <div class="rpage-sub">The whole report, at a glance &mdash; every row is explained in the pages that follow.</div>
    </div>
    <div class="rpage-body">
      <div class="hero-chip">
        <div class="eb">Next Strong Window</div>
        <div class="rng">{escape(best_range)}</div>
      </div>
      <div class="stat-strip" style="margin-top:14px">
        <div class="stat-row"><span class="k">Switch Outlook</span><span class="v{outlook_go}">{escape(switch_outlook)}</span></div>
        <div class="stat-row"><span class="k">Current Phase</span><span class="v">{escape(phase)}</span></div>
        <div class="stat-row"><span class="k">Career Direction</span><span class="v">{escape(field_families[0])}</span></div>
        <div class="stat-row"><span class="k">Growth Pattern</span><span class="v">{escape(p.get("growth_pattern","Jump-led"))}</span></div>
        <div class="stat-row"><span class="k">Foreign Potential</span><span class="v{foreign_go}">{escape(foreign_display)}</span></div>
      </div>
    </div>
  </section>

  <section class="rpage" id="p5">
    <div class="rpage-top"><div class="rpage-title">Who You Are at Work</div></div>
    <div class="rpage-body">
      <p style="font-size:14px;line-height:1.65">{escape(p.get("persona_line","").capitalize())}. Decisions come easily when you can talk them through out loud; you're slower and more cautious when working in isolation.</p>
      <p style="font-size:14px;line-height:1.65;margin-top:10px">As a leader, you guide more than you command &mdash; people tend to follow because they trust your read of a situation, not because of hierarchy.</p>
      <div class="quote">{escape(about.get("strength","You build trust through how you work."))}</div>
    </div>
  </section>

  <section class="rpage" id="p6">
    <div class="rpage-top"><div class="rpage-title">Strength &amp; Growth Edge</div></div>
    <div class="rpage-body">
      <p style="font-size:14px;line-height:1.65"><b>Core strength:</b> {escape(support_text or "steady follow-through")}. Once committed, you see things to completion &mdash; steady effort over flashes of intensity, which reads well in senior roles.</p>
      <p style="font-size:14px;line-height:1.65;margin-top:10px"><b>Under pressure:</b> you slow down and reason it out rather than react &mdash; an asset in negotiation, a liability if it tips into over-deliberation.</p>
      <p style="font-size:14px;line-height:1.65;margin-top:10px"><b>Growth edge:</b> {escape(p.get("lessons", [f"{tenth_lord} — a lesson worth naming in advance"])[0].split(" — ",1)[-1] if p.get("lessons") else "restlessness during quiet periods can push toward premature moves")}. Naming it in advance makes it easier to sit with.</p>
    </div>
  </section>

  <section class="rpage" id="p7">
    <div class="rpage-top"><div class="rpage-title">Where Your Chart Points</div></div>
    <div class="rpage-body">
      <div class="stat-strip">
        <div class="stat-row"><span class="k">1. Strongest fit</span><span class="v">{escape(field_families[0])}</span></div>
        <div class="stat-row"><span class="k">2. Also favorable</span><span class="v">{escape(field_families[1])}</span></div>
        <div class="stat-row"><span class="k">3. Also favorable</span><span class="v">{escape(field_families[2])}</span></div>
      </div>
      <p style="font-size:13px;color:var(--pmuted);margin-top:14px">Less natural fit: {escape(p.get("field_antifit","highly repetitive, solo-execution roles with little client or team contact"))} &mdash; not closed to you, just a harder climb.</p>
    </div>
  </section>

  <section class="rpage" id="p8">
    <div class="rpage-top"><div class="rpage-title">Job or Own Business?</div></div>
    <div class="rpage-body">
      <div class="verdict" style="margin-bottom:16px">
        <div class="eb">Main takeaway</div>
        <h3>{escape(verdict_h3)}</h3>
        <p>{escape(verdict_p)}</p>
      </div>
      <div class="meter">
        <div class="meter-track"><div class="meter-fill" style="width:{job_fill_pct}%"></div></div>
        <div class="meter-labels"><span>Own Business</span><span></span><span>Job</span></div>
      </div>
      <p class="note" style="margin-top:16px">This isn't about "AI-proof" or "AI-safe" work &mdash; it's about durable strengths: judgement, relationship-building and follow-through are hard to automate regardless of role or field.</p>
    </div>
  </section>

  <section class="rpage" id="p9">
    <div class="rpage-top"><div class="rpage-title">Your Current Period</div></div>
    <div class="rpage-body">
      <p style="font-size:14px;line-height:1.65">You're inside a {escape(current_md)} Mahadasha, {escape(current_ad)} Antardasha &mdash; a period defined by {escape(md_phase_text)}.{" No Sade Sati is active right now." if not p.get("sade_sati",{}).get("active") else " Saturn's Sade Sati is also active right now, adding extra weight to this period."}</p>
      <div class="verdict" style="margin-top:16px">
        <div class="eb">Current phase</div>
        <h3>{escape(phase)}</h3>
        <p>The next section shows exactly how long, and what changes.</p>
      </div>
    </div>
  </section>

  <section class="rpage" id="p10">
    <div class="rpage-top"><div class="rpage-title">Your Switch Windows</div></div>
    <div class="rpage-body">
      <div class="tl-col">{window_rows}</div>
    </div>
  </section>

  <section class="rpage" id="p11">
    <div class="rpage-top">
      <div class="rpage-title">Your Strongest Window</div>
      <div class="rpage-sub">{escape(best_range)}</div>
    </div>
    <div class="rpage-body">
      <div class="dodont">
        <div class="card do"><div class="mark">&#10003;</div><div><div class="lbl">Do</div><p>Start exploring by {escape(do_by)}, and treat the window as one arc.</p></div></div>
        <div class="card avoid"><div class="mark">&#33;</div><div><div class="lbl">Avoid</div><p>Rushing a decision before you've actually explored your options.</p></div></div>
      </div>
      <p style="font-size:13px;color:var(--pmuted);line-height:1.55;margin-top:16px">{escape(best_rules_prose)}</p>
      <p class="note" style="margin-top:14px">A favorable window improves timing &mdash; the offer still comes from your skills, preparation and market opportunities.</p>
    </div>
  </section>

  <section class="rpage" id="p12">
    <div class="rpage-top"><div class="rpage-title">Other Windows to Watch</div></div>
    <div class="rpage-body">
      {second_para}
      {quiet_para}
    </div>
  </section>

  <section class="rpage" id="p13">
    <div class="rpage-top"><div class="rpage-title">How Your Income Tends to Grow</div></div>
    <div class="rpage-body">
      <p style="font-size:14px;line-height:1.65">{escape(wealth.get("second_text","").capitalize())}. {escape(wealth.get("eleventh_text","").capitalize())}.</p>
      <div class="stat-strip" style="margin-top:14px">
        <div class="stat-row"><span class="k">Stability</span><span class="v{stability_go}">{escape(wealth.get("stability","Moderate"))}</span></div>
        <div class="stat-row"><span class="k">Upside via switching</span><span class="v{upside_go}">{escape(wealth.get("upside","Moderate"))}</span></div>
      </div>
    </div>
  </section>

  <section class="rpage" id="p14">
    <div class="rpage-top"><div class="rpage-title">Your Workplace Archetype: {escape(workplace.get("archetype","Diplomat"))}</div></div>
    <div class="rpage-body">
      <p style="font-size:14px;line-height:1.65">{escape(wtext["para1"])}</p>
      <p style="font-size:14px;line-height:1.65;margin-top:10px">{escape(wtext["para2"])}</p>
    </div>
  </section>

  <section class="rpage" id="p15">
    <div class="rpage-top"><div class="rpage-title">Environment That Suits You</div></div>
    <div class="rpage-body">
      <div class="stat-strip">
        <div class="stat-row"><span class="k">Best-fit structure</span><span class="v">{escape(wtext["best_fit"])}</span></div>
        <div class="stat-row"><span class="k">Team size</span><span class="v">{escape(wtext["team_size"])}</span></div>
        <div class="stat-row"><span class="k">Burnout risk</span><span class="v">{escape(wtext["burnout"])}</span></div>
      </div>
    </div>
  </section>

  <section class="rpage" id="p16">
    <div class="rpage-top"><div class="rpage-title">Relocation &amp; Foreign Potential</div></div>
    <div class="rpage-body">
      <div class="stat-strip">
        <div class="stat-row"><span class="k">Foreign potential</span><span class="v{foreign_go}">{escape(foreign_display)}</span></div>
        <div class="stat-row"><span class="k">Best-supported form</span><span class="v">Major career hub, international clients</span></div>
      </div>
      <p style="font-size:13.5px;line-height:1.65;margin-top:14px">{escape(p.get("ninth_house_note","").capitalize())}. No specific country is indicated; treat any interest in a hub or global-facing role as worth pursuing.</p>
    </div>
  </section>

  <section class="rpage" id="p17">
    <div class="rpage-top">
      <div class="rpage-title">Your 90-Day Plan</div>
      <div class="rpage-sub">Not the window itself &mdash; the groundwork that makes it land well when it arrives.</div>
    </div>
    <div class="rpage-body">
      <p style="font-size:13px;color:var(--pmuted);line-height:1.6;margin-bottom:14px">Your strongest window is {escape(best_range)} &mdash; still worth building toward. These 90 days turn patience into a genuinely ready profile, not a rushed one.</p>
      <div class="phase-card">
        <div class="ph">Days 1&ndash;30</div><h4>Settle &amp; Audit</h4>
        <div class="lbl">Focus</div><p>Get honest about where you stand, while signals are still just building.</p>
        <div class="lbl">Do</div>
        <ul>
          <li>Update your resume and portfolio around your top direction &mdash; {escape(fields_link_p17)}.</li>
          <li>Reconnect quietly with 3&ndash;5 people in your network &mdash; conversation, not cold outreach.</li>
        </ul>
        <div class="lbl">Avoid</div><p>Applying anywhere yet, or reading early interest as the window itself.</p>
      </div>
      <div class="phase-card">
        <div class="ph">Days 31&ndash;60</div><h4>Deepen &amp; Test</h4>
        <div class="lbl">Focus</div><p>Sharpen your direction without committing to anything.</p>
        <div class="lbl">Do</div>
        <ul>
          <li>Have a few honest, informal conversations in your target fields &mdash; testing fit, not applying.</li>
          <li>Notice what energises you vs. drains you in these conversations.</li>
        </ul>
        <div class="lbl">Avoid</div><p>Mistaking a good conversation for an offer, or applying too early out of restlessness.</p>
      </div>
    </div>
  </section>

  <section class="rpage" id="p18">
    <div class="rpage-top">
      <div class="rpage-title">Your 90-Day Plan, Continued</div>
      <div class="rpage-sub">Days 61&ndash;90.</div>
    </div>
    <div class="rpage-body">
      <div class="phase-card">
        <div class="ph">Days 61&ndash;90</div><h4>Consolidate</h4>
        <div class="lbl">Focus</div><p>Close the quarter with a genuinely ready profile, not a rushed one.</p>
        <div class="lbl">Do</div>
        <ul>
          <li>Finalise a resume and portfolio version you'd be proud to send without editing.</li>
          <li>Keep the network warm with light, periodic check-ins &mdash; not a hard push.</li>
        </ul>
        <div class="lbl">Avoid</div><p>Forcing a decision before the real window opens.</p>
      </div>
      <p class="note" style="margin-top:16px">The offer still comes from your skills, preparation and market opportunities &mdash; these 90 days are what make sure you're ready to meet it.</p>
    </div>
  </section>

  <section class="rpage" id="p19">
    <div class="rpage-top"><div class="rpage-title">Light Remedies</div></div>
    <div class="rpage-body">
      <div class="checklist">
        <div class="chk"><span class="box"></span>Keep {escape(p.get("remedy_day","Saturday"))}s for {escape(current_md)}-linked discipline &mdash; a simple steadying practice for your current Mahadasha.</div>
        <div class="chk"><span class="box"></span>Keep {escape(p.get("comm_day","Wednesday"))}s for important conversations &mdash; your career-lord's day suits your communication strength.</div>
        <div class="chk"><span class="box"></span>{"Avoid starting anything irreversible during the quiet stretch identified on page 12." if quiet else "No notable hold period ahead &mdash; pace yourself by the windows above instead."}</div>
      </div>
    </div>
  </section>

  <section class="rpage" id="p20">
    <div class="rpage-top">
      <div class="rpage-title">The Chain, at a Glance</div>
      <div class="rpage-sub">Eight links connect your birth chart to your career recommendations.</div>
    </div>
    <div class="rpage-body">
      <div class="tl-col">
        <div class="tl-row"><div class="yr-line"><div class="dot soft"></div><div class="yr">1. Birth Chart</div></div><div class="d">Lagna sets your baseline.</div></div>
        <div class="tl-row"><div class="yr-line"><div class="dot soft"></div><div class="yr">2. Career Houses</div></div><div class="d">10th, 6th, 2nd, 11th, 9th &amp; 12th mark the terrain.</div></div>
        <div class="tl-row"><div class="yr-line"><div class="dot soft"></div><div class="yr">3. Planetary Strengths</div></div><div class="d">Which planets are well-placed, which aren't.</div></div>
        <div class="tl-row"><div class="yr-line"><div class="dot soft"></div><div class="yr">4. Dasha &amp; Antardasha</div></div><div class="d">Your current chapter, and its theme.</div></div>
        <div class="tl-row"><div class="yr-line"><div class="dot soft"></div><div class="yr">5. Transits</div></div><div class="d">What's moving right now &mdash; especially Jupiter and Saturn.</div></div>
        <div class="tl-row"><div class="yr-line"><div class="dot soft"></div><div class="yr">6. Career Themes</div></div><div class="d">Direction, workplace style, income pattern, foreign potential.</div></div>
        <div class="tl-row"><div class="yr-line"><div class="dot soft"></div><div class="yr">7. Job-Change Windows</div></div><div class="d">When enough of the above align to act.</div></div>
        <div class="tl-row"><div class="yr-line"><div class="dot"></div><div class="yr">8. Recommendation</div></div><div class="d">What to actually do, and when.</div></div>
      </div>
    </div>
  </section>

  <section class="rpage" id="p21">
    <div class="rpage-top">
      <div class="rpage-title">Your Birth Chart: Lagna</div>
      <div class="rpage-sub">Everything on pages 5&ndash;6 starts here.</div>
    </div>
    <div class="rpage-body">
      <div class="house-card">
        <div class="badge">LG</div>
        <div><h4>Lagna &mdash; how you show up</h4><p>{escape(p.get("persona_line","").capitalize())} (p.5) &mdash; this is the outward professional self your chart sets at birth.</p></div>
      </div>
    </div>
  </section>

  <section class="rpage" id="p22">
    <div class="rpage-top">
      <div class="rpage-title">The Career Houses</div>
      <div class="rpage-sub">10th, 6th, 2nd &amp; 11th &mdash; the terrain behind pages 7, 13&ndash;14.</div>
    </div>
    <div class="rpage-body">
      <div class="house-card" style="margin-bottom:10px"><div class="badge">10</div><div><h4>Direction</h4><p>Points toward {escape(fields_p7)} (p.7).</p></div></div>
      <div class="house-card" style="margin-bottom:10px"><div class="badge">6</div><div><h4>Workplace conduct</h4><p>Behind your {escape(workplace.get("archetype","Diplomat"))} archetype (p.14).</p></div></div>
      <div class="house-card" style="margin-bottom:10px"><div class="badge">2</div><div><h4>Stability</h4><p>Behind the {escape(wealth.get("stability","Moderate"))} stability rating in your income pattern (p.13).</p></div></div>
      <div class="house-card"><div class="badge">11</div><div><h4>Gains &amp; networks</h4><p>Behind your {escape(p.get("growth_pattern","Jump-led"))} growth pattern (p.13).</p></div></div>
    </div>
  </section>

  <section class="rpage" id="p23">
    <div class="rpage-top">
      <div class="rpage-title">9th &amp; 12th Houses, and Rahu</div>
      <div class="rpage-sub">Behind the Relocation &amp; Overseas Opportunities chapter, page 16.</div>
    </div>
    <div class="rpage-body">
      <p style="font-size:14px;line-height:1.65">{escape(p.get("ninth_house_note","").capitalize())}. <b style="color:var(--pink)">Rahu</b> adds the pull toward the unfamiliar &mdash; part of why relocation reads as worth actively exploring, not something to force.</p>
    </div>
  </section>

  <section class="rpage" id="p24">
    <div class="rpage-top">
      <div class="rpage-title">Planetary Strengths</div>
      <div class="rpage-sub">Which planets are carrying the most weight right now.</div>
    </div>
    <div class="rpage-body">
      <div class="pair-cards">
        <div class="pair-card">
          <h4>Structure &amp; Timing</h4>
          <div class="row"><span class="k">{escape(current_md)}</span><span class="v">{escape(PLANET_GIFT.get(current_md, "steady effort").capitalize())} &mdash; your current Mahadasha lord (p.9).</span></div>
          <div class="row"><span class="k">{escape(tenth_lord)}</span><span class="v">Your 10th lord &mdash; behind your career direction (p.7).</span></div>
        </div>
        <div class="pair-card">
          <h4>Growth &amp; Drive</h4>
          <div class="row"><span class="k">Jupiter</span><span class="v">The planet most linked to expansion &mdash; watch its transits for your switch windows (p.10&ndash;11).</span></div>
          <div class="row"><span class="k">{escape(support_name or "Additional strengths")}</span><span class="v">{escape(support_text.capitalize() + " — an additional real strength in this chart." if support_text else "A further real strength in this chart.")}</span></div>
        </div>
      </div>
    </div>
  </section>

  <section class="rpage" id="p25">
    <div class="rpage-top">
      <div class="rpage-title">Dasha &amp; Antardasha</div>
      <div class="rpage-sub">Your timeline engine &mdash; the theme, and the current chapter within it.</div>
    </div>
    <div class="rpage-body">
      <div class="tl-col">
        <div class="tl-row"><div class="yr-line"><div class="dot"></div><div class="yr">Mahadasha &mdash; {escape(current_md)}</div></div><div class="d">{escape(md_phase_text.capitalize())}.</div></div>
        <div class="tl-row"><div class="yr-line"><div class="dot soft"></div><div class="yr">Antardasha &mdash; {escape(current_ad)}</div></div><div class="d">The current flavour layered on top of the Mahadasha theme.</div></div>
      </div>
      <p style="font-size:13px;line-height:1.6;margin-top:14px">This exact combination is why right now specifically reads as {escape(phase)} (p.9).</p>
    </div>
  </section>

  <section class="rpage" id="p26">
    <div class="rpage-top">
      <div class="rpage-title">Transits: Why {escape(best_range)}</div>
      <div class="rpage-sub">The moving parts, layered on top of the dasha backdrop.</div>
    </div>
    <div class="rpage-body">
      <p style="font-size:13.5px;line-height:1.65">A dasha sets the stage; a transit raises the curtain. {escape(best_rules_prose)}</p>
    </div>
  </section>

  <section class="rpage" id="p27">
    <div class="rpage-top"><div class="rpage-title">How It All Adds Up</div></div>
    <div class="rpage-body">
      <div class="tl-col">
        <div class="tl-row"><div class="yr-line"><div class="dot soft"></div><div class="yr">Birth Chart</div></div><div class="d">{escape(p.get("persona_line","").capitalize())}.</div></div>
        <div class="tl-row"><div class="yr-line"><div class="dot soft"></div><div class="yr">Houses</div></div><div class="d">10th &rarr; {escape(field_families[0])} &middot; 6th &rarr; {escape(workplace.get("archetype","Diplomat"))} &middot; 9th/12th &rarr; {escape(foreign_display)} foreign potential.</div></div>
        <div class="tl-row"><div class="yr-line"><div class="dot soft"></div><div class="yr">Planetary Strengths</div></div><div class="d">{escape(current_md)} and {escape(tenth_lord)} lead.</div></div>
        <div class="tl-row"><div class="yr-line"><div class="dot soft"></div><div class="yr">Dasha</div></div><div class="d">{escape(current_md)} MD, {escape(current_ad)} AD &rarr; {escape(phase)}.</div></div>
        <div class="tl-row"><div class="yr-line"><div class="dot"></div><div class="yr">Transit</div></div><div class="d">Activates {escape(best_range)}.</div></div>
      </div>
      <div class="quote">Prepare now. Move in the window.</div>
      <div class="note" style="margin-top:9px">Computed from classical Vedic principles, applied consistently &mdash; probabilities and tendencies, not guarantees.</div>
    </div>
  </section>

  <section class="rpage dark" id="p28">
    <div class="rpage-body" style="padding-top:32px;padding-bottom:32px;text-align:center">
      <p class="note" style="text-align:left;margin:0 0 34px;background:rgba(255,255,255,.06);border-color:rgba(228,176,74,.3);color:rgba(240,232,218,.75)">
        <b style="color:#fff">Disclaimer:</b> This report is computed from classical Vedic Jyotish (dasha&ndash;transit) principles &mdash; for guidance, not a guarantee. Timing windows are probabilities, not fixed dates. This is not legal, medical or financial advice &mdash; please make your own decisions using your own judgement.
      </p>
      <div style="width:48px;height:2px;background:var(--pgold);margin:0 auto 34px;border-radius:2px"></div>
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" style="margin:0 auto 14px"><path d="M12 2 L14.5 9.5 L22 12 L14.5 14.5 L12 22 L9.5 14.5 L2 12 L9.5 9.5 Z" fill="#E4B04A"/></svg>
      <div style="font-family:var(--disp);font-weight:600;font-size:28px;color:#fff;margin-bottom:14px">Axtroshastra</div>
      <p style="font-size:13.5px;color:rgba(240,232,218,.75);line-height:1.65">Made with Axtroshastra &mdash; get your own report:<br><a href="https://www.axtroshastra.com" style="color:#E4B04A;font-weight:700;text-decoration:none">axtroshastra.com</a></p>
      <p style="font-size:11.5px;color:rgba(240,232,218,.55);line-height:1.7;max-width:34ch;margin:28px auto 0">Windows are probability estimates from classical dasha&ndash;transit principles, not guarantees. <a href="https://wa.me/919599827297" style="color:rgba(240,232,218,.55);text-decoration:underline">WhatsApp +91 95998 27297</a> &middot; <a href="mailto:support@axtroshastra.com" style="color:rgba(240,232,218,.55);text-decoration:none">support@axtroshastra.com</a></p>
      <p style="font-size:11.5px;color:rgba(240,232,218,.55);line-height:1.7;max-width:36ch;margin:12px auto 0">Axtroshastra &middot; Computational Vedic Astrology &middot; by Cultnuts &middot; <a href="https://www.axtroshastra.com/privacy" style="color:rgba(240,232,218,.55);text-decoration:underline">Privacy</a> &middot; <a href="https://www.axtroshastra.com/terms" style="color:rgba(240,232,218,.55);text-decoration:underline">Terms</a> &middot; <a href="https://www.axtroshastra.com/refund" style="color:rgba(240,232,218,.55);text-decoration:underline">Refund Policy</a></p>
    </div>
  </section>

</div>
</div>

<style>@media screen{{body{{padding-bottom:92px}}}}
#ax-stickybar{{position:fixed;left:0;right:0;bottom:0;z-index:9997;
background:rgba(251,247,239,.97);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);
border-top:1px solid rgba(201,163,78,.4);box-shadow:0 -8px 24px rgba(58,44,24,.16);
padding:10px 14px calc(10px + env(safe-area-inset-bottom))}}
#ax-stickybar .inner{{max-width:520px;margin:0 auto;display:flex;gap:10px}}
#ax-stickybar a{{flex:1;display:flex;align-items:center;justify-content:center;gap:8px;
min-height:52px;text-align:center;text-decoration:none;border-radius:14px;padding:12px 10px;
font:700 16px/1.15 system-ui,sans-serif;letter-spacing:.01em;
-webkit-tap-highlight-color:transparent;transition:transform .08s ease}}
#ax-stickybar a:active{{transform:scale(.97)}}
#ax-stickybar svg{{width:19px;height:19px;flex:none}}
#ax-stickybar .pdf{{background:#B4674A;color:#fff;box-shadow:0 6px 16px rgba(180,103,74,.3)}}
#ax-stickybar .wa{{background:#4F7A5C;color:#fff;box-shadow:0 6px 16px rgba(79,122,92,.3)}}
@media (min-width:640px){{#ax-stickybar a{{min-height:48px;font-size:15px}}}}
@media print{{#ax-stickybar{{display:none!important}}}}</style>
<div id='ax-stickybar'><div class='inner'>
<a class='pdf' id='ax-pdf' href='#' onclick='window.print();return false;'><svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'><path d='M12 3v12'/><path d='M6 11l6 6 6-6'/><path d='M4 21h16'/></svg>Download PDF</a>
<a class='wa' href='#' onclick='axShare();return false;'><svg viewBox='0 0 24 24' fill='currentColor' aria-hidden='true'><path d='M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 2a8 8 0 1 1-4.1 14.9l-.5-.3-2.6.7.7-2.5-.3-.5A8 8 0 0 1 12 4zm-3.1 4.3c-.2 0-.5.1-.7.3-.7.7-1 1.6-.8 2.6.3 1.2 1 2.4 2.1 3.5 1.4 1.4 3 2.3 4.6 2.5.8.1 1.6-.2 2.2-.8.2-.2.3-.5.3-.8l-.1-.7c-.1-.2-.2-.4-.5-.5l-1.7-.8a.8.8 0 0 0-.9.2l-.5.5c-.1.2-.4.2-.6.1a6.7 6.7 0 0 1-2.9-2.9c-.1-.2 0-.4.1-.6l.5-.5c.2-.2.3-.6.2-.9l-.8-1.7c-.1-.2-.3-.4-.5-.4l-.5-.1z'/></svg>Share on WhatsApp</a>
</div></div>
<script>
window.axShare=function(){{var url=location.href;var t='Check out my career report from Axtroshastra';if(navigator.share){{navigator.share({{title:'Axtroshastra',text:t,url:url}}).catch(function(){{}});}}else{{window.open('https://wa.me/?text='+encodeURIComponent(t+' '+url),'_blank');}}}};
</script>
</body>
</html>
"""


if __name__ == "__main__":
    import json
    r = compute_career_growth("Test Person", "1996-06-14", "10:30", 5.5, 12.97, 77.59,
                              gender="male", place="Bengaluru, India",
                              employment_situation="changing-job",
                              experience="5-10")
    print(json.dumps({k: v for k, v in r.items() if k not in ("chart", "sig")},
                      indent=2, default=str))
    html = render_career_growth(r)
    out_path = os.path.join(os.path.dirname(__file__), "_career_growth_test.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", out_path, len(html), "bytes")
