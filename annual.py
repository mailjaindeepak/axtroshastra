"""Annual Report engine (product "annual_report"): the production twin of diwali.compute_diwali.

Deterministic astrology only, no LLM. Every chart fact comes from the shared engine
(engine.compute_report / compute_chart / doshas / sign_change_dates / sade_sati_stages /
saturn_house_timeline, divisional.yogas, CLAUDE.md s21). Month and area tones reuse the
pure scoring helpers of diwali.py (_positions, _base_score, _area_term, _tones); nothing is
copied. No festival data lives here.

compute_annual(payload, as_of=None) returns:
  meta    server-side facts (product, lang, as_of, time_quality, basis ...)
  teaser  the free preview, exactly docs/annual/build/preview-contract.md
  facts   the normalised dict the report renderer consumes (keys = docs/annual/mock/_build/persona.py)

Timing is pinned to `as_of` (default today). The 12-month span is the 12 full months that
start the month AFTER as_of; the "past" months are the month before as_of's month and as_of's
own month. Months are read at 12:00 UTC on the 15th (same sampling as Diwali).
"""
from datetime import date, datetime, timedelta

import engine
import diwali
import divisional
from engine import NAKSHATRAS, SIGNS_EN, houses_from, vimshottari_tree

# ----------------------------------------------------------------- constants
TOPICS = ["career", "money", "marriage", "luck", "strengths"]
TOPIC_LABEL = {"career": "Career and work", "money": "Money and savings",
               "marriage": "Marriage and relationships", "luck": "Luck and big decisions",
               "strengths": "Strengths, study and growth"}
# Preview questions: wording from docs/annual/mock/annual-preview-v2.html (draft, owner review).
QUESTIONS = {"career": "Could a step forward in your work or studies come in the next 12 months?",
             "money": "Which months look stronger for saving, and which call for care with money?",
             "marriage": "Which months may bring good news in marriage and close bonds?",
             "luck": "Which months may suit a big decision, like a move, a purchase or a fresh start?",
             "strengths": "Which of your strengths can grow most in the next 12 months?"}
STEERING = tuple(TOPICS)
WORK_TYPES = diwali.WORK_TYPES
# Diwali has areas this report has no topic for: business reads as career, family as relationships.
_AREA_TOPIC = {"career": "career", "business": "career", "money": "money",
               "marriage": "marriage", "family": "marriage"}
TONE = {"best": "strong", "good": "strong", "steady": "mixed", "careful": "careful"}
CODES = {"Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me", "Jupiter": "Ju",
         "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke"}
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
BAND_MID = {"subah": "07:00", "din": "13:00", "shaam": "19:00", "raat": "01:00"}   # same as api.BAND_MID
BAND_TEXT = {"subah": "Morning (not sure of the time)", "din": "Daytime (not sure of the time)",
             "shaam": "Evening (not sure of the time)", "raat": "Night (not sure of the time)"}
CHANGE_PLANETS = ("Rahu", "Ketu", "Jupiter", "Saturn")
# Lagna-free yogas only: when the birth time is unsure the rising sign is a guess.
_MOON_YOGAS = ("Gajakesari", "Budha-Aditya", "Chandra-Mangala")
_STRENGTH = {"own": "Strong", "exalted": "Strong", "debilitated": "Needs care"}
_STRENGTH_PREVIEW = {"Strong": "strong", "Needs care": "care", "Average": "average"}


# ----------------------------------------------------------------- small helpers
def _ym(y, m):
    return f"{y:04d}-{m:02d}"


def _label(ym):
    return f"{MON[int(ym[5:]) - 1]} {ym[:4]}"


def _dmy(iso):
    """'2027-06-03' -> '3 Jun 2027'."""
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{d} {MON[m - 1]} {y}"


def _my(iso):
    """'2034-07-12' -> 'Jul 2034'."""
    return f"{MON[int(iso[5:7]) - 1]} {iso[:4]}"


def _to_dt(as_of):
    if as_of is None:
        t = date.today()
        return datetime(t.year, t.month, t.day)
    if isinstance(as_of, datetime):
        return as_of.replace(tzinfo=None)
    if isinstance(as_of, date):
        return datetime(as_of.year, as_of.month, as_of.day)
    if isinstance(as_of, str):
        try:
            return datetime.fromisoformat(as_of)
        except ValueError:
            raise ValueError("as_of must be an ISO date string, a date or a datetime")
    raise ValueError("as_of must be an ISO date string, a date or a datetime")


def _num(payload, key, lo, hi):
    v = payload.get(key)
    if isinstance(v, bool) or v is None:
        raise ValueError(f"{key} is required and must be a number")
    try:
        v = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be a number")
    if not lo <= v <= hi:
        raise ValueError(f"{key} must be between {lo} and {hi}")
    return v


def _validate(payload, as_of_dt):
    """Explicit errors, never a guessed default (mirrors compute_diwali). Returns clean values."""
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    name = (payload.get("name") or "").strip() if isinstance(payload.get("name"), str) else ""
    if not name:
        raise ValueError("name is required")
    gender = payload.get("gender")
    if gender not in ("male", "female"):
        raise ValueError("gender must be 'male' or 'female'")
    work_type = payload.get("work_type")
    if work_type not in WORK_TYPES:
        raise ValueError(f"work_type must be one of {WORK_TYPES}")
    steering = payload.get("steering") or None
    if steering is not None and steering not in STEERING:
        raise ValueError(f"steering must be one of {STEERING} or None")
    tq = payload.get("time_quality", "T0")
    if tq not in ("T0", "T1", "T2", "T3"):
        raise ValueError("time_quality must be T0..T3")
    try:
        dob = date.fromisoformat(payload.get("dob") or "")
    except (TypeError, ValueError):
        raise ValueError("dob must be YYYY-MM-DD")
    if dob >= as_of_dt.date():
        raise ValueError("dob must be before the report date")
    band = payload.get("time_band")
    if band is not None and band not in BAND_MID:
        raise ValueError(f"time_band must be one of {tuple(BAND_MID)}")
    tob = payload.get("tob")
    if tob is not None or tq in ("T0", "T1"):   # api passes the band midpoint / 12:00 as tob
        try:
            datetime.strptime(tob or "", "%H:%M")
        except ValueError:
            raise ValueError("tob must be HH:MM")
    elif tq == "T2":
        tob = BAND_MID.get(band or "", "13:00")
    else:
        tob = "12:00"
    lat, lon = _num(payload, "lat", -90, 90), _num(payload, "lon", -180, 180)
    tz = _num(payload, "tz", -14, 14)
    return dict(name=name, gender=gender, work_type=work_type, steering=steering, tq=tq,
                dob=dob.isoformat(), tob=tob, band=band, lat=lat, lon=lon, tz=tz,
                place=(payload.get("place") or "").strip())


def _first_topic(work_type, steering):
    """Steered topic, else the first topic of diwali.area_order (its first area never moves
    for an unpicked steering), mapped onto this report's topics."""
    if steering:
        return steering
    order, _ = diwali.area_order(work_type, None, {a: 0 for a in diwali.AREAS})
    return _AREA_TOPIC[order[0]]


# ----------------------------------------------------------------- month tones
def _months_scores(yms, refs, ref, moon_sign, female, capped):
    """Overall + five area tones for the given months, via diwali's pure scoring helpers."""
    pos = {ym: diwali._positions(datetime(int(ym[:4]), int(ym[5:]), 15, 12)) for ym in yms}
    base = {ym: diwali._base_score(pos[ym], refs, ref, moon_sign) for ym in yms}
    flags = [base[ym][2] for ym in yms]
    tone_of = dict(zip(yms, diwali._tones([base[ym][0] for ym in yms], flags, capped)))
    areas = {}
    for a in diwali.AREAS:
        sc = [base[ym][0] + 2 * diwali._area_term(pos[ym], ref, a, female)[0] for ym in yms]
        t = dict(zip(yms, diwali._tones(sc, flags, capped)))
        # same rule as Diwali: a careful month is never best/good for any area
        areas[a] = {ym: TONE["steady" if tone_of[ym] == "careful" and t[ym] in ("best", "good") else t[ym]]
                    for ym in yms}
    return {ym: TONE[t] for ym, t in tone_of.items()}, areas


# ----------------------------------------------------------------- preview month text (no AI)
_HEAD = {"strong": "A strong month", "mixed": "A mixed month", "careful": "A careful month"}
# kind -> tone -> [opener, 3 shared lines, closer]; the work line is picked by work_type.
_SHARED = {
    "past": {
        "strong": ["This looks like it was a strong month, with something helpful in most weeks.",
                   "Money in hand may have felt a little easier than before.",
                   "Friends and family may have stayed close and supportive.",
                   "A small plan you had held back may have been a good one to start.",
                   "Overall, it may have been a month that moved you ahead."],
        "mixed": ["This may have been a mixed month, with good days and plain days side by side.",
                  "Money in hand may have gone out and come in at about the same pace.",
                  "Talks at home may have needed a few extra words to be clear.",
                  "A friend may have offered a useful idea.",
                  "Overall, it may have been a month of small gains and small lessons."],
        "careful": ["This may have been a careful month, where small steps worked better than big moves.",
                    "Money in hand may have needed a closer look.",
                    "Talks at home may have needed a few extra words to be clear.",
                    "A plan made early may have saved you from a rushed choice.",
                    "Some weeks may have felt full and some quiet."]},
    "future": {
        "strong": ["This is likely to be a strong month, with many good days for your plans.",
                   "Money in hand may feel a bit easier.",
                   "A talk you have been putting off may go well.",
                   "A friend may bring good news.",
                   "Some weeks may be quiet and some full, but the month as a whole may feel like a step forward."],
        "mixed": ["This is likely to be a mixed month, with good days and plain days side by side.",
                  "Money in hand may go out and come in at about the same pace.",
                  "A talk at home may need a few extra words to be clear.",
                  "A friend may offer a useful idea.",
                  "Some weeks may be quiet and some full, so take it one week at a time."],
        "careful": ["This is likely to be a careful month, where small steps work better than big moves.",
                    "Money in hand may need a closer look before you spend.",
                    "A talk at home may need a few extra words to be clear.",
                    "A plan made early may save you from a rushed choice.",
                    "Some weeks may feel full and some quiet, so keep your plans simple."]},
}
_WORK = {
    "job": {"strong": "Your seniors may notice your effort, and a task done well may earn you thanks.",
            "mixed": "Work may move at an even pace, with one or two tasks that take longer than planned.",
            "careful": "Work may ask for more effort than you expected, so double-check what you hand in."},
    "business": {"strong": "Customers and deals may move well, and a payment you waited for may come in.",
                 "mixed": "Sales may stay about the same, with one or two deals that take longer to close.",
                 "careful": "Deals may need more follow-up than you expected, so keep your records tidy."},
    "student": {"strong": "Your effort in study may get noticed, and a teacher may think well of your work.",
                "mixed": "Study may move at an even pace, with one topic that needs a second look.",
                "careful": "Study may ask for more effort than you expected, so plan your days early."},
    "home": {"strong": "Home matters may run smoothly, and a small task you finish may bring thanks.",
             "mixed": "Home matters may run at an even pace, with one or two jobs that take longer than planned.",
             "careful": "Home matters may ask for more effort than you expected, so plan the week early."},
}


def _month_block(kind, ym, tone, work_type):
    s = _SHARED[kind][tone]
    text = " ".join([s[0], _WORK[work_type][tone], s[1], s[2], s[3], s[4]])
    return {"range": _label(ym), "tone": tone, "heading": _HEAD[tone], "text": text}


# ----------------------------------------------------------------- main
def compute_annual(payload, as_of=None):
    as_of_dt = _to_dt(as_of)
    v = _validate(payload, as_of_dt)
    female = v["gender"] == "female"
    wt, steering = v["work_type"], v["steering"]

    # ---- shared engine: tier logic (T2/T3 read from the Moon sign), chart, manglik, yogas
    rep = engine.compute_report(v["name"], v["dob"], v["tob"], v["tz"], v["lat"], v["lon"],
                                female=female, time_quality=v["tq"], as_of=as_of_dt, place=v["place"])
    dt_utc = datetime.fromisoformat(f"{v['dob']}T{v['tob']}:00") - timedelta(hours=v["tz"])
    ch = engine.compute_chart(dt_utc, v["lat"], v["lon"])
    g = ch["grahas"]
    moon = g["Moon"]
    use_moon = rep["meta"]["system"] == "chandra_lagna"
    basis = "moon" if use_moon else "lagna"
    ref = moon.sign if use_moon else ch["lagna_sign"]
    refs = [ref] if use_moon else [ch["lagna_sign"], moon.sign]
    capped = v["tq"] in ("T2", "T3")
    SN = diwali.SIGN_NAMES

    # ---- span: 12 full months from the month AFTER as_of; past = month before + as_of's month
    sy, sm = diwali._add_months(as_of_dt.year, as_of_dt.month, 1)
    span = [_ym(*diwali._add_months(sy, sm, k)) for k in range(12)]
    past = [_ym(*diwali._add_months(as_of_dt.year, as_of_dt.month, k)) for k in (-1, 0)]
    tones, areas = _months_scores(past + span, refs, ref, moon.sign, female, capped)
    area_span = {a: {ym: t[ym] for ym in span} for a, t in areas.items()}
    span_start = datetime(sy, sm, 1)
    span_end = datetime(*diwali._add_months(sy, sm, 12), 1)     # first day after the span

    # ---- planet period
    tree = vimshottari_tree(moon.lon, dt_utc, as_of_dt + timedelta(days=4 * 365))
    md = next((m for m in tree if m["start"] <= as_of_dt <= m["end"]), None)
    ad = next((a for a in md["ads"] if a["start"] <= as_of_dt <= a["end"]), None) if md else None
    if ad is None:
        raise ValueError("birth date and report date do not give a planet period")
    all_ads = [(m["lord"], a) for m in tree for a in m["ads"]]
    i_ad = next(i for i, (_, a) in enumerate(all_ads) if a is ad)
    nxt = all_ads[i_ad + 1] if i_ad + 1 < len(all_ads) else None
    period = {"main": md["lord"], "sub": ad["lord"], "until": ad["end"].strftime("%Y-%m-%d"),
              "next_sub": f"{nxt[0]}/{nxt[1]['lord']}" if nxt else None,
              "next_start": nxt[1]["start"].strftime("%Y-%m-%d") if nxt else None}

    # ---- doshas, manglik, yogas
    dos = engine.doshas(ch, as_of_dt)
    mg = engine.manglik(ch)
    yogas = [dict(name=y["name"], detail=y.get("detail"), effect=y.get("effect"))
             for y in divisional.yogas(ch)
             if not use_moon or y["name"].startswith(_MOON_YOGAS)]

    # ---- sign changes of the slow planets inside the span (exact IST days)
    sign_changes = sorted(
        (c for p in CHANGE_PLANETS for c in engine.sign_change_dates(p, span_start, span_end)),
        key=lambda c: (c["at"], CHANGE_PLANETS.index(c["planet"])))
    sign_changes = [{"planet": c["planet"], "date": c["date"], "from": c["from_name"], "to": c["to_name"]}
                    for c in sign_changes]
    # from as_of (not span start): a Saturn move between as_of and the span start still counts
    sat_moves = [{"date": c["date"], "from": c["from_name"], "to": c["to_name"]}
                 for c in engine.sign_change_dates("Saturn", as_of_dt, span_end)]
    saturn_changes = [{"date": c["date"], "from": c["from"], "to": c["to"],
                       "house_from_moon": houses_from(moon.sign, SIGNS_EN.index(c["to"]))}
                      for c in sat_moves]
    sat_dos = dos["shani_dhaiya"]

    # ---- Sade Sati stages (engine, exact dates) and Dhaiya start/end dates
    ss = engine.sade_sati_stages(moon.sign, as_of_dt, as_of_dt + timedelta(days=365 * 8))
    ss_stage = ss["stage_at_start"] if ss["active_at_start"] else None
    # every stage change from as_of to the span end; `stage` is the stage at as_of
    in_span = lambda d: as_of_dt.date().isoformat() <= d < span_end.date().isoformat()
    ss_changes = [{"date": c["date"], "stage": None if c["stage"] == "none" else c["stage"]}
                  for c in ss["changes"] if in_span(c["date"])]
    ss_ends = next((c["date"] for c in ss["changes"] if c["stage"] == "none"), None) if ss_stage else None
    tl = engine.saturn_house_timeline(moon.sign, as_of_dt, as_of_dt + timedelta(days=365 * 30), 24)
    dh_ends = dh_restarts = dh_next = None
    on = sat_dos["active"]
    for c in tl["changes"]:
        now_in = c["house"] in (4, 8)
        if sat_dos["active"] and on and not now_in and dh_ends is None:
            dh_ends, on = c["date"], False
        elif not on and now_in:
            if sat_dos["active"] and dh_restarts is None:
                dh_restarts = c["date"]
            elif not sat_dos["active"] and dh_next is None:
                dh_next = c["date"]
            on = True
    dhaiya = {"active": sat_dos["active"], "kind": sat_dos["kind"], "ends": dh_ends, "restarts": dh_restarts}

    # ---- chart tables
    planets = []
    for p in diwali.PLANET_ORDER:
        gr = g[p]
        planets.append({"planet": p, "sign": SIGNS_EN[gr.sign], "nakshatra": NAKSHATRAS[gr.nak],
                        "pada": gr.pada, "strength_label": _STRENGTH.get(gr.dignity, "Average")})
    kundli = {h: [] for h in range(1, 13)}
    for p in diwali.PLANET_ORDER:
        kundli[houses_from(ref, g[p].sign)].append(CODES[p])

    emphasis = _first_topic(wt, steering)
    if v["tq"] in ("T0", "T1"):
        time_text = v["tob"]
    else:
        time_text = BAND_TEXT.get(v["band"], "Not sure of the time") if v["tq"] == "T2" \
            else "Not known"
    facts = {
        "name": v["name"], "first_name": v["name"].split(" ")[0], "gender": v["gender"],
        "work_type": wt,
        "birth": {"date": v["dob"], "time_known": v["tq"] in ("T0", "T1"), "time_text": time_text,
                  "place": v["place"]},
        "today": as_of_dt.strftime("%Y-%m-%d"),
        "span_months": [{"ym": ym, "label": _label(ym)} for ym in span],
        "past_months": [{"ym": ym, "label": _label(ym)} for ym in past],
        "tones": tones, "moon_sign": SIGNS_EN[moon.sign], "nakshatra": NAKSHATRAS[moon.nak],
        "pada": moon.pada, "rising_sign": None if use_moon else SIGNS_EN[ch["lagna_sign"]],
        "planet_table": planets, "kundli": kundli, "planet_period": period,
        "manglik": {"status": mg["status"], "from_lagna": mg["from_lagna"], "from_moon": mg["from_moon"],
                    "cancelled": mg["status"] == "manglik_cancelled",
                    "note": "; ".join(mg["cancellations"]) or None},
        "kaal_sarp": dos["kaal_sarp"], "pitra": dos["pitra"],
        "saturn_now": {"sign": sat_dos["saturn_sign_name"], "house_from_moon": sat_dos["house_from_moon"],
                       "changes": saturn_changes},
        "sade_sati": {"active": ss_stage is not None, "stage": ss_stage, "change_dates": ss_changes},
        "dhaiya": dhaiya, "sign_changes": sign_changes, "yogas": yogas, "areas": area_span,
        "first_open_topic": TOPIC_LABEL[emphasis],
    }

    # ---- teaser (preview contract): locked months carry no tone and no text
    kd = {}
    for p in diwali.PLANET_ORDER:
        kd.setdefault(SN[g[p].sign], []).append(CODES[p])
    if not use_moon:
        kd.setdefault(SN[ch["lagna_sign"]], []).insert(0, "La")
    sk = diwali.SANSKRIT
    ss_stage_phase = {"first": "rising", "second": "peak", "third": "setting"}.get(ss_stage)
    strip = []
    for i, ym in enumerate(span):
        e = {"m": MON[int(ym[5:]) - 1][0], "label": _label(ym), "open": i < 2}
        if i < 2:
            e["tone"] = tones[ym]
        strip.append(e)
    preview = {
        "version": 1, "work_type": wt, "moon_basis": use_moon, "start_area": emphasis,
        "sign_names": dict(sk),
        "chart": {"rising": None if use_moon else sk[SN[ch["lagna_sign"]]],
                  "moon": sk[SN[moon.sign]], "star": NAKSHATRAS[moon.nak],
                  "period": f"{md['lord']} – {ad['lord']}", "period_end": _dmy(period["until"]),
                  "sade_sati": {"active": ss_stage is not None, "stage": ss_stage,
                                "ends": _dmy(ss_ends) if ss_ends else None,
                                "next_starts": None if ss_stage else (_my(ss["next_start"]) if ss["next_start"] else None)},
                  "dhaiya": {"active": dhaiya["active"], "kind": dhaiya["kind"],
                             "ends": _dmy(dh_ends) if dh_ends else None,
                             "restarts": _dmy(dh_restarts) if dh_restarts else None,
                             "next_starts": _my(dh_next) if dh_next else None}},
        "past": [_month_block("past", ym, tones[ym], wt) for ym in past],
        "future_free": _month_block("future", span[0], tones[span[0]], wt),
        "strip": strip,
    }
    teaser = {
        "name": v["name"], "moon_sign": SN[moon.sign], "nakshatra": NAKSHATRAS[moon.nak],
        "lagna_sign": SN[ch["lagna_sign"]], "basis": basis, "period": f"{md['lord']} – {ad['lord']}",
        "sade_sati": {"active": ss_stage is not None, "phase": ss_stage_phase},
        "planets": [{"name": p, "sign": SN[g[p].sign], "dignity": g[p].dignity,
                     "strength": _STRENGTH_PREVIEW[_STRENGTH.get(g[p].dignity, "Average")]}
                    for p in diwali.PLANET_ORDER],
        "kundli": kd, "emphasis_area": emphasis, "questions": [QUESTIONS[t] for t in TOPICS],
        "preview": preview,
    }
    meta = {"product": "annual_report", "lang": "en", "variant": "/en/annual-report",
            "name": v["name"], "first_name": facts["first_name"], "dob": v["dob"], "tob": v["tob"],
            "place": v["place"], "gender": v["gender"], "work_type": wt, "steering": steering,
            "time_quality": v["tq"], "basis": basis, "as_of": facts["today"],
            "span": f"{_label(span[0])} – {_label(span[-1])}",
            "two_timelines": rep["meta"]["two_timelines_detected"]}
    return {"product": "annual_report", "meta": meta, "teaser": teaser, "facts": facts}
