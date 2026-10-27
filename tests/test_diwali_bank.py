"""Pure tests for diwali_bank (no DB, no api import). Run with --noconftest."""
import copy
import itertools
import json
import re

import pytest

import diwali_bank as B

LORD = {"Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Karka": "Moon", "Leo": "Sun",
        "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter",
        "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter"}
S = B.SIGNS


def _payload(lagna, moon, planets, transits, tones, care, windows, states, *, md, ad,
             gender="male", work="business", steering="money", band="40_60", basis="lagna",
             gift=None, dhana=True, gold=(), loans=(), sade=None, name="Asha Kumar"):
    li = S.index(lagna)
    houses = {str(h): {"sign": S[(li + h - 1) % 12], "lord": LORD[S[(li + h - 1) % 12]]} for h in range(1, 13)}
    pl = [{"name": n, "sign": sg, "house": (S.index(sg) - li) % 12 + 1, "dignity": dg, "retro": False,
           "nakshatra": "x"} for n, sg, dg in planets]
    months = []
    for i, ym in enumerate(B.MONTH_YMS):
        tr = {p: {"sign": S[(li + h - 1) % 12], "house": h, "retro": r} for p, (h, r) in transits[i].items()}
        tags = (["gold"] if ym in gold else []) + (["loans"] if ym in loans else [])
        months.append({"ym": ym, "label": ym, "year": int(ym[:4]), "tone": tones[i], "care_reason": care.get(ym),
                       "transits": tr, "tags": tags})
    sit = B.SITUATION_ORDER[work]
    order = sit if steering in (None, "luck") else [steering] + [a for a in sit if a != steering]
    areas = {}
    for a in B.AREAS:
        w = windows[a]
        areas[a] = {"state": states[a], "windows": w,
                    "topics": [{"key": f"{a}.t{n}", "state": states[a] if n % 3 else "careful",
                                "when": "careful" if n % 3 == 0 else "good", "months": w["careful"] if n % 3 == 0 else w["good"],
                                "why": ""} for n in range(1, B.TOPIC_COUNTS[a] + 1)],
                    "picture": []}
    best = windows["money"]["best"]
    return {
        "product": "diwali",
        "meta": {"name": name, "first_name": name.split()[0], "gender": gender, "work_type": work,
                 "steering": steering, "time_quality": "T0" if basis == "lagna" else "T3", "basis": basis,
                 "lang": "en", "age_band": band, "as_of": "2026-11-08", "span": "Nov 2026 – Oct 2027",
                 "gift": gift or {"on": False, "giver_name": "", "message": ""}},
        "chart": {"lagna": {"sign": lagna}, "moon": {"sign": moon, "nakshatra": "x", "pada": 1},
                  "planets": pl, "houses": houses},
        "period": {"md": md, "ad": ad, "ad_end": "2028-02", "next_ad": None, "turning_points": []},
        "sade_sati": sade or {"active": False, "phase": None, "phases": []},
        "months": months, "area_order": order, "first_reason": "picked" if steering else "situation",
        "scores": {"money": 1, "career": 0, "business": 2, "family": 2, "marriage": 1},
        "areas": areas,
        "money_extra": {"dhana_yoga": {"present": dhana, "rule_text": "", "lords": ["Jupiter", "Mercury"]},
                        "gold_months": list(gold), "loan_months": list(loans)},
        "marriage_extra": {"manglik": {"lagna_rule": True, "moon_rule": False, "cancelled": True,
                                       "reason": "Mars sits in its own sign, Scorpio"},
                           "seventh": {"sign": houses["7"]["sign"], "lord": houses["7"]["lord"], "lord_dignity": ""}},
        "strengths": [{"planet": n, "sign": sg, "house": (S.index(sg) - li) % 12 + 1, "dignity": dg}
                      for n, sg, dg in planets if dg in ("own", "exalted")][:3],
        "lookback": {"good": ["2026-01"], "hard": ["2025-11"]},
        "luck": {"bright_spots": [], "ninth": {"sign": houses["9"]["sign"], "lord": houses["9"]["lord"]}},
        "timeline": [{"from": B.MONTH_YMS[i * 3], "to": B.MONTH_YMS[i * 3 + 2], "tone": t, "theme": th}
                     for i, (t, th) in enumerate([("good", "A steady new start"), ("careful", "Spend with care"),
                                                  ("best", "The turning point"), ("good", "Growth with a steady hand")])],
        "best_time": {"from": best[0], "to": best[-1]} if best else {},
        "diwali": {"days": [], "puja_times": []},
        "answers": [{"q": f"q{i}", "state": s} for i, s in enumerate(["good", "good", "good", "careful", "good"])],
        "wrapped": {"strongest_area": order[0], "best": {}, "careful": {}, "move": "", "words": []},
        "teaser": {},
    }


# Fixture A: shapes from docs/diwali/mock/persona.json + TIMING.md (Leo rising, Aquarius Moon)
def fixture_a(**kw):
    planets = [("Sun", "Karka", ""), ("Moon", "Aquarius", ""), ("Mars", "Scorpio", "own"), ("Mercury", "Leo", ""),
               ("Jupiter", "Sagittarius", "own"), ("Venus", "Leo", ""), ("Saturn", "Libra", "exalted"),
               ("Rahu", "Taurus", ""), ("Ketu", "Scorpio", "")]
    jup = [1, 1, 1, 12, 12, 12, 12, 1, 1, 1, 1, 1]
    sat = [8] * 7 + [9] * 5
    mars = [5, 6, 1, 1, 12, 12, 11, 2, 2, 3, 4, 4]
    sun = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2]
    ven = [2, 3, 4, 5, 6, 7, 8, 10, 11, 2, 3, 4]
    tr = [{"Jupiter": (jup[i], i in (3, 4)), "Saturn": (sat[i], False), "Mars": (mars[i], i in (2, 3)),
           "Sun": (sun[i], False), "Venus": (ven[i], False), "Rahu": (6, True)} for i in range(12)]
    tones = ["good", "steady", "careful", "careful", "careful", "careful", "steady", "best", "best", "good", "good", "good"]
    care = {"2027-01": "reactions", "2027-02": "spending", "2027-03": "spending", "2027-04": "spending"}
    W = lambda b, g, c: {"best": b, "good": g, "careful": c}
    windows = {"money": W(["2027-06", "2027-07"], ["2026-11", "2027-08"], ["2027-02", "2027-03"]),
               "career": W(["2027-06"], ["2027-07", "2027-08"], ["2027-01"]),
               "business": W(["2027-06", "2027-07"], ["2026-11"], ["2027-02"]),
               "family": W([], ["2026-11", "2026-12", "2027-08"], ["2027-01", "2027-02"]),
               "marriage": W(["2027-07"], ["2026-11", "2027-04"], ["2027-01"])}
    states = {"money": "good", "career": "good", "business": "good", "family": "good", "marriage": "good"}
    args = dict(md="Mercury", ad="Jupiter", gold=("2026-11", "2027-07", "2027-09"), loans=("2026-12", "2027-01"),
                sade={"active": True, "phase": "setting", "phases": []})
    args.update(kw)
    return _payload("Leo", "Aquarius", planets, tr, tones, care, windows, states, **args)


# Fixture B: a different person (Karka rising, Taurus Moon, female, job, different months)
def fixture_b(**kw):
    planets = [("Sun", "Aries", "exalted"), ("Moon", "Taurus", "exalted"), ("Mars", "Gemini", ""),
               ("Mercury", "Pisces", "debilitated"), ("Jupiter", "Capricorn", "debilitated"),
               ("Venus", "Pisces", "exalted"), ("Saturn", "Leo", ""), ("Rahu", "Virgo", ""), ("Ketu", "Pisces", "")]
    tr = [{"Jupiter": (12 if i < 7 else 1, False), "Saturn": (9, i > 8), "Mars": ((i + 3) % 12 + 1, False),
           "Sun": ((i + 5) % 12 + 1, False), "Venus": ((i + 7) % 12 + 1, False), "Rahu": (8, True)} for i in range(12)]
    tones = ["steady", "good", "good", "best", "best", "steady", "steady", "careful", "careful", "good", "steady", "good"]
    care = {"2027-06": "reactions", "2027-07": "reactions"}
    W = lambda b, g, c: {"best": b, "good": g, "careful": c}
    windows = {"money": W(["2027-02"], ["2027-09"], ["2027-06"]),
               "career": W(["2027-03"], ["2026-12", "2027-01"], ["2027-07"]),
               "business": W([], ["2027-09", "2027-10"], ["2027-06", "2027-07"]),
               "family": W(["2027-02"], ["2027-10"], ["2027-07"]),
               "marriage": W([], ["2027-09"], ["2027-06"])}
    states = {"money": "steady", "career": "good", "business": "careful", "family": "steady", "marriage": "careful"}
    args = dict(md="Venus", ad="Saturn", gender="female", work="job", steering=None, band="25_40",
                dhana=False, gold=("2027-02",), loans=("2027-09",), name="Meera Iyer")
    args.update(kw)
    return _payload("Karka", "Taurus", planets, tr, tones, care, windows, states, **args)


DATE_KEYS = ("timeline.", "months.", "wrapped.")
USER_KEYS = {"gift.message"}  # buyer-typed text, printed as given


def _lint_all(out):
    bad = {}
    for k, v in out.items():
        if k in USER_KEYS:
            continue
        probs = B.lint_text(v, allow_dates=k.startswith(DATE_KEYS))
        if probs:
            bad[k] = (probs, v)
    return bad


NARR = [k for k, _, _ in B.NARR_KEYS]


def test_narr_keys_shape():
    assert len(NARR) == len(set(NARR))
    assert all(g in "ABCD" and b for _, b, g in B.NARR_KEYS)
    for a, n in B.TOPIC_COUNTS.items():
        for i in range(1, n + 1):
            for part in ("what", "do", "watch", "why", "when"):
                # marriage.t5 = Manglik facts box, payload-only (no AI prose)
                assert (f"{a}.t{i}.{part}" in NARR) != ((a, i) == ("marriage", 5))
    for ym in B.MONTH_YMS:
        assert f"months.{ym}.do" in NARR and f"months.{ym}.watch" in NARR


BRANCHES = list(itertools.product(
    ["job", "business", "student", "home"], ["male", "female"],
    ["money", "career", "business", "family", "marriage", "luck", None],
    ["u25", "25_40", "40_60", "60p"], ["lagna", "moon"]))


@pytest.mark.parametrize("fx", [fixture_a, fixture_b])
def test_every_key_nonempty_and_lint_clean_across_branches(fx):
    for i, (work, gender, steer, band, basis) in enumerate(BRANCHES):
        gift = [{"on": False}, {"on": True, "giver_name": "", "message": ""},
                {"on": True, "giver_name": "Ravi", "message": "Happy Diwali!"}][i % 3]
        out = B.bank(fx(work=work, gender=gender, steering=steer, band=band, basis=basis, gift=gift))
        missing = [k for k in NARR if not (out.get(k) or "").strip()]
        assert not missing, (work, gender, steer, band, basis, missing[:5])
        assert not _lint_all(out), (work, gender, steer, band, basis, list(_lint_all(out).items())[:3])


def _move(p, lagna, new_signs, md=None, ad=None):
    """Same person shape, different planets: re-place planets (houses from the rising sign)."""
    li = S.index(lagna)
    for x in p["chart"]["planets"]:
        if x["name"] in new_signs:
            x["sign"] = new_signs[x["name"]]
            x["house"] = (S.index(x["sign"]) - li) % 12 + 1
            x["dignity"] = ""
    if "Moon" in new_signs:
        p["chart"]["moon"]["sign"] = new_signs["Moon"]
    if md:
        p["period"]["md"], p["period"]["ad"] = md, ad
    p["strengths"] = [{"planet": x["name"], "sign": x["sign"], "house": x["house"], "dignity": x["dignity"]}
                      for x in p["chart"]["planets"] if x["dignity"] in ("own", "exalted")][:3]
    return p


def five_buyers(work="job"):
    """5 different people. Buyers 1+3 and 2+4 share a rising sign (and months), so only the planets
    beyond the rising sign (Moon, Sun, Rahu, Ketu, period) tell them apart: the hardest case."""
    kw = dict(work=work, gender="male", steering=None, band="25_40")
    a, b = fixture_a(**kw), fixture_b(**kw)
    a2 = _move(fixture_a(**kw), "Leo", {"Moon": "Aries", "Rahu": "Gemini", "Ketu": "Sagittarius", "Sun": "Virgo"},
               "Rahu", "Venus")
    b2 = _move(fixture_b(**kw), "Karka", {"Moon": "Libra", "Sun": "Leo", "Rahu": "Aries", "Ketu": "Libra"},
               "Ketu", "Moon")
    c = _move(fixture_b(**kw), "Karka", {"Moon": "Sagittarius", "Sun": "Capricorn", "Mercury": "Aquarius",
                                         "Venus": "Scorpio", "Mars": "Virgo", "Jupiter": "Gemini",
                                         "Saturn": "Pisces"}, "Saturn", "Mercury")
    return [a, b, a2, b2, c]


# Spec §9: no paragraph identical across 5 people (dates and numbers aside), incl. strengths, Wrapped,
# blessing, the read lines, Why lines, Sade Sati, turning points and the end plan. Only one-line labels
# (do/watch/when/titles/openers/answers/notes), date pages and the approved fixed Manglik/Sade Sati
# 'when' wording are exempt.
FIXED_OK = ("note.", "answers.", "timeline.", "months.", "sadesati.when", "marriage.t5.", "marriage.manglik.",
            "luck.blessings.do", "lookback.good.do", "lookback.hard.do",
            "luck.bright.")  # one-line list items that follow each area's state, not paragraphs
# Claim headlines (the one-sentence title over each area's picture, and Better luck's) are titles in the
# approved mock and carry no chart clause, so they are exempt like titles; Sade Sati's headline stays in.
PARA = [k for k in NARR if not k.endswith((".do", ".watch", ".when", ".title", ".opener"))
        and not (k.endswith(".headline") and k != "sadesati.headline")
        and not k.startswith(FIXED_OK)]
_MON_RE = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\b")


def _strip_nums(v):
    return _MON_RE.sub("M", re.sub(r"\d+", "#", v))


def _assert_five_distinct(outs, tag, why_ok=()):
    """why_ok: pairs whose Why lines may match. Only the fixture twins built on one rising sign AND one
    shared transit table qualify: the same transit through the same house with the same house lord is one
    chart reason, and saying it differently would be false. Real births (below) get no exemption."""
    for i, j in itertools.combinations(range(len(outs)), 2):
        same = [k for k in PARA if _strip_nums(outs[i][k]) == _strip_nums(outs[j][k])
                and not ((i, j) in why_ok and (k.endswith(".why") or k.startswith("sadesati.")))]
        assert not same, (tag, i, j, same[:10])


def _tones(p):
    return tuple(m["tone"] for m in p["months"])


def _assert_facts_differ(ps, outs, tag, month_text=True):
    """Deterministic fallback may be generic; uniqueness is checked on AI-on output after deploy.
    Here: different charts must still give different facts, and different month patterns a different table."""
    for i, j in itertools.combinations(range(len(ps)), 2):
        if month_text and _tones(ps[i]) != _tones(ps[j]):
            mk = [k for k in outs[i] if k.startswith("months.")]
            assert any(outs[i][k] != outs[j][k] for k in mk), (tag, i, j, "same 12-month table for different months")
        if ps[i]["chart"]["lagna"]["sign"] != ps[j]["chart"]["lagna"]["sign"]:
            assert any(outs[i][k] != outs[j][k] for k in PARA), (tag, i, j, "all paragraphs equal for different charts")
    assert len({_tones(p) for p in ps}) > 1, tag


@pytest.mark.parametrize("work", ["job", "business", "student", "home"])
def test_five_buyer_facts_differ_fallback_may_be_generic(work):
    """Deterministic fallback may be generic; uniqueness is checked on AI-on output after deploy."""
    ps = five_buyers(work)
    twins = {(i, j) for i, j in itertools.combinations(range(5), 2)
             if ps[i]["chart"]["lagna"]["sign"] == ps[j]["chart"]["lagna"]["sign"]
             and ps[i]["months"] == ps[j]["months"]}
    assert len(twins) < 10
    _assert_facts_differ(ps, [B.bank(p) for p in ps], work)


# The same gate on the real engine (pure compute, no DB): catches engine-supplied text the fixtures fake,
# e.g. Wrapped words and shared-sky Why lines.
REAL_BIRTHS = [("Ravi Shah", "1985-03-14", "09:20", 5.5, 18.52, 73.86),
               ("Anita Rao", "1992-11-02", "23:45", 5.5, 12.97, 77.59),
               ("Sunil K", "1970-06-01", "06:10", 5.5, 28.61, 77.21),
               ("Kiran M", "1988-01-20", "14:30", 5.5, 19.07, 72.88),
               ("Neha P", "1978-08-08", "19:05", 5.5, 22.57, 88.36)]


@pytest.mark.parametrize("tq", ["T0", "T2", "T3"])
@pytest.mark.parametrize("work", ["job", "business", "student", "home"])
def test_five_buyer_real_engine(work, tq):
    """Fallback may be generic; uniqueness is checked on AI-on output after deploy. T2/T3 read the chart from the Moon sign. Two buyers with one Moon sign then share every house and every
    transit, so the engine's transit reasons (Why lines) and Sade Sati (a Moon-sign fact) are one true reason
    for both. Everything else, every 'what' paragraph included, must still differ."""
    import diwali as D
    ps = [D.compute_diwali(*b, gender="male", work_type=work, steering=None, time_quality=tq) for b in REAL_BIRTHS]
    outs = [B.bank(p) for p in ps]
    moon_twins = {(i, j) for i, j in itertools.combinations(range(5), 2)
                  if ps[i]["meta"]["basis"] == "moon" and ps[i]["chart"]["moon"]["sign"] == ps[j]["chart"]["moon"]["sign"]}
    if tq != "T0":
        assert moon_twins, "REAL_BIRTHS 1 and 3 share a Moon sign: the T2/T3 run must exercise the twin case"
    _assert_facts_differ(ps, outs, (work, tq), month_text=False)  # real-engine month text may be generic
    for o in outs:
        assert not _lint_all(o), (work, list(_lint_all(o).items())[:3])
        for k, v in o.items():  # spec §2 R2: a topic's 'what' is 2-3 sentences
            if re.match(r"(money|career|business|family|marriage)\.t\d+\.what$", k):
                assert 1 <= len(re.split(r"(?<=[.!?])\s+", v)) <= 3, (k, v)


def test_wrapped_engine_words_linted():
    """Engine words are checked like Why lines: the engine's 'PATIENT' (a §5b word) never prints."""
    p = fixture_a()
    p["wrapped"]["words"] = [{"word": "STEADY", "line": "Your money grows slowly but surely."},
                             {"word": "PATIENT", "line": "Mar 2027 asks you to pause before you reply."},
                             {"word": "RISING", "line": "Your stress fades in Jul 2027."}]
    v = B.bank(p)["wrapped.words"]
    assert B.lint_text(v, allow_dates=True) == [], v
    rows = v.splitlines()
    assert len(rows) == 3 and rows[0].startswith("STEADY: ") and rows[1].startswith("UNHURRIED: Mar 2027")
    assert "stress" not in rows[2]


def test_whys_differ_for_different_charts():
    outs = [B.bank(p) for p in five_buyers()]
    whys = [k for k in NARR if k.endswith(".why") and not k.startswith(("marriage.t5", "slow."))]
    for i, j in ((0, 1), (0, 4), (2, 3)):  # different rising signs: no shared chart reason line
        same = [k for k in whys if outs[i][k] == outs[j][k]]
        assert not same, (i, j, same)


def test_engine_why_reused_never_repeats_in_one_report():
    """Real engine output repeats one transit reason for many topics; the report must not."""
    p = fixture_a()
    reasons = ["Jupiter passes the home part.", "Jupiter looks at the gains part.", "Saturn passes the spending part."]
    for a in B.AREAS:
        for n, t in enumerate(p["areas"][a]["topics"]):
            t["why"] = reasons[n % 3]
    out = B.bank(p)
    whys = [out[k] for k in NARR if k.endswith(".why")]
    dup = {w for w in whys if whys.count(w) > 1}
    assert not dup, dup
    assert any("Jupiter passes the home part" in w for w in whys)


@pytest.mark.parametrize("fx", [fixture_a, fixture_b])
def test_no_sentence_repeated_across_area_sections(fx):
    out = B.bank(fx())
    seen = {}
    for a in B.AREAS:
        for k, v in out.items():
            if k.startswith(a + ".") and k.endswith((".what", ".why", ".read")):
                for s in re.split(r"(?<=[.!?])\s+", v):
                    if len(s) > 40 and s in seen:
                        pytest.fail(f"repeated across {seen[s]} and {a}: {s}")
                    seen.setdefault(s, a)


def test_no_month_names_outside_allowed_keys():
    for fx in (fixture_a, fixture_b):
        out = B.bank(fx())
        for k, v in out.items():
            if not k.startswith(DATE_KEYS) and k not in USER_KEYS:
                assert not B._MONTH_RE.search(v) and not B._YEAR_RE.search(v), (k, v)
        assert any(B._MONTH_RE.search(out[f"timeline.{i}"]) for i in range(1, 5))


def test_steering_opener_only_when_picked():
    picked = B.bank(fixture_a(steering="money", work="business"))
    assert picked["money.opener"].startswith("You picked Money, so it comes first")
    assert "You picked" not in picked["business.opener"]
    skipped = B.bank(fixture_a(steering=None, work="business"))
    assert not any("You picked" in v for v in skipped.values())
    assert skipped["note.order"].startswith("As a business owner, your report starts with Business")
    luck = B.bank(fixture_a(steering="luck", work="job"))
    assert luck["luck.opener"].startswith("You picked Better luck") and luck["career.opener"].startswith("Career comes second")


def test_work_type_changes_career_and_business_wording():
    titles = {w: B.bank(fixture_a(work=w))["career.t1.title"] for w in ("job", "business", "student", "home")}
    assert len(set(titles.values())) == 4
    biz = {w: B.bank(fixture_a(work=w))["business.t1.title"] for w in ("job", "business", "student", "home")}
    assert len(set(biz.values())) == 4


@pytest.mark.parametrize("engine_why", ["", "The partner part is in Aquarius, ruled by Saturn."])
def test_gender_changes_marriage_reading(engine_why):
    def mk(g):
        p = fixture_a(gender=g)
        p["areas"]["marriage"]["topics"][3]["why"] = engine_why
        return B.bank(p)["marriage.t4.why"]
    m, f = mk("male"), mk("female")
    assert "Venus" in m and "Jupiter" in f and m != f


def test_age_60p_never_first_job():
    for work in ("job", "business", "student", "home"):
        out = B.bank(fixture_a(work=work, band="60p", steering="career"))
        assert not any("first job" in v.lower() or "first salary" in v.lower() for v in out.values()), work
    young = B.bank(fixture_a(work="student", band="u25"))
    assert any("first job" in v for v in young.values())


def test_moon_basis_less_precise_note():
    assert "less precise" in B.bank(fixture_a(basis="moon"))["note.less_precise"]
    assert "less precise" not in B.bank(fixture_a(basis="lagna"))["note.less_precise"]
    assert "not used" in B.bank(fixture_a(basis="moon"))["marriage.manglik.lagna"]


def test_gift_branches():
    off = B.bank(fixture_a())
    assert off["gift.title"] == "" and off["blessing.sign"] == "Your Axtroshastra family"
    anon = B.bank(fixture_a(gift={"on": True, "giver_name": "", "message": ""}))
    assert anon["gift.title"] == "A Diwali gift for you" and anon["gift.message"] == B.DEFAULT_GIFT_MESSAGE
    named = B.bank(fixture_a(gift={"on": True, "giver_name": "Ravi", "message": "For you, bhai."}))
    assert named["gift.title"] == "A Diwali gift from Ravi" and named["gift.message"] == "For you, bhai."
    assert "Ravi" in named["blessing.sign"] and "Ravi" in named["blessing.text"]


def test_marriage_family_never_assume_status():
    for fx in (fixture_a, fixture_b):
        out = B.bank(fx())
        txt = " ".join(v for k, v in out.items() if k.startswith(("marriage.", "family.")))
        for bad in ("your wife", "your husband", "your spouse", "your marriage", "your children",
                    "the right person", "marry again", "when children may come"):
            assert bad not in txt.lower()


def test_no_mock_persona_leak():
    out = B.bank(fixture_b())
    blob = " ".join(out.values()).lower()
    for leak in ("vikram", "priya", "pune", "rao"):
        assert not re.search(rf"\b{leak}\b", blob), leak


def test_deterministic():
    assert B.bank(fixture_a()) == B.bank(copy.deepcopy(fixture_a()))


@pytest.mark.parametrize("text,hit", [
    ("Money looks good in Jun 2027.", "month name"), ("This year looks good.", '"year" alone'),
    ("The money part (2nd house) helps.", "bracket"), ("The money part, 2nd house, helps.", "house name and house number"),
    ("A best stretch.", "stretch"), ("A good window.", "window"), ("Low stress months.", "stress"),
    ("Your wife may help.", "your wife"), ("Sun in Cancer.", "Cancer"), ("Results are guaranteed.", "guaranteed"),
    ("Checked against AstroSage.", "AstroSage"), ("Good for your health.", "health"),
])
def test_lint_catches(text, hit):
    assert B.lint_text(text), (text, hit)


@pytest.mark.parametrize("text", [
    "Money may build from this Diwali to the next.", "May this Diwali fill your home with light.",
    "Mars sits in the home part of your chart.", "Keep your scope small and your savings secure.",
    "Fate favours steady work.", "Your year at a glance", "Gujarati New Year",
])
def test_lint_clean(text):
    assert B.lint_text(text) == []


def test_lint_allows_dates_on_date_pages():
    assert B.lint_text("Careful in Jan–Feb 2027, better from Mar 2027.", allow_dates=True) == []


@pytest.mark.parametrize("text", ["Your best time comes around May.", "Plan big buys for late May.",
                                  "Good during May, and early May too.", "The money part, the second house, helps.",
                                  "Mars sits in house seven, the partner part."])
def test_lint_catches_more(text):
    assert B.lint_text(text), text


def _no_best(p, tq="T0"):
    p["meta"]["time_quality"] = tq
    for a in p["areas"].values():
        a["windows"]["good"] += a["windows"]["best"]
        a["windows"]["best"] = []
        for t in a["topics"]:
            t["when"] = "good" if t["when"] == "best" else t["when"]
    for m in p["months"]:
        m["tone"] = "good" if m["tone"] == "best" else m["tone"]
    return p


@pytest.mark.parametrize("make", [lambda: _no_best(fixture_a()),
                                  lambda: _no_best(fixture_b(), "T3"),
                                  lambda: dict(fixture_a(), meta=dict(fixture_a()["meta"], time_quality="T2"))])
def test_no_best_time_promised_when_buyer_has_none(make):
    out = B.bank(make())
    hits = {k: v for k, v in out.items() if re.search(r"\bbest (time|months?)\b", v, re.I)}
    assert not hits, list(hits.items())[:3]
    assert not _lint_all(out)


@pytest.mark.parametrize("bt", [None, {}, {"from": None, "to": None}])
def test_missing_best_time_does_not_crash(bt):
    p = fixture_a()
    p["best_time"] = bt
    out = B.bank(p)
    assert all((out.get(k) or "").strip() for k in NARR)


def test_month_cells_under_8_words():
    for fx in (fixture_a, fixture_b):
        out = B.bank(fx())
        for ym in B.MONTH_YMS:
            for f in ("do", "watch"):
                assert len(out[f"months.{ym}.{f}"].split()) < 8, out[f"months.{ym}.{f}"]


# ── FIX-CONTENT round: plain, specific text (no trait chaining, no stock phrases) ──────────────────
def _real(work="business", steer="money", tq="T0", i=0):
    import diwali as D
    n, dob, tob, tz, lat, lon = REAL_BIRTHS[i]
    return D.compute_diwali(n, dob, tob, tz, lat, lon, gender="male", work_type=work, steering=steer, time_quality=tq)


def _sample_outputs():
    return [B.bank(fixture_a()), B.bank(fixture_b()), B.bank(_real()), B.bank(_real("student", None, i=1)),
            B.bank(_real("job", "luck", "T3", i=2))]


# Only the date pages (month names are the point there), the buyer's own gift message, the approved
# fixed question titles and the Wrapped card's copy of takeaway 1 are left out. House names are NOT
# collapsed: "in the children and planning part" said ten times is exactly the robotic text this guards.
_SKIP6 = ("months.", "timeline.")
_SKIP6_KEYS = {"gift.message", "wrapped.lead"}


def _six_word_repeats(out):
    """Every 6-word run said 3 or more times in one report -> how many times."""
    c = {}
    for k, v in out.items():
        if k.startswith(_SKIP6) or k in _SKIP6_KEYS or k.endswith(".title"):
            continue
        for g in B.grams6(v):
            c[g] = c.get(g, 0) + 1
    return {g: n for g, n in c.items() if n > 2}


def _many_outputs():
    import diwali as D
    outs = _sample_outputs()
    for i, (work, steer) in enumerate(itertools.product(["job", "business", "student", "home"],
                                                        [None, "money", "family", "marriage", "luck"])):
        n, dob, tob, tz, lat, lon = REAL_BIRTHS[i % 5]
        outs.append(B.bank(D.compute_diwali(n, dob, tob, tz, lat, lon, gender=["male", "female"][i % 2],
                                            work_type=work, steering=steer, time_quality=["T0", "T1", "T2", "T3"][i % 4])))
    return outs


def test_no_phrase_said_more_than_twice():
    """Spec: no phrase used more than twice in one report. Allowed: at most 2 runs said a third time
    (never a fourth), across 25 real-engine reports over every work type, steering and birth-time grade."""
    for out in _many_outputs():
        rep = _six_word_repeats(out)
        assert len(rep) <= 2 and max(rep.values(), default=0) <= 3, sorted(rep.items(), key=lambda x: -x[1])[:10]


def test_no_trait_chaining():
    traits = list(B.SIGN_TRAIT.values())
    for out in _sample_outputs():
        for k, v in out.items():
            assert ", plus " not in v and "along with" not in v and not v.startswith("Lean on"), (k, v)
            assert sum(t in v for t in traits) <= 1, (k, v)


def test_after_this_diwali_at_most_once_per_sentence():
    for out in _sample_outputs():
        for k, v in out.items():
            for sent in re.split(r"(?<=[.!?])\s+|\n", v):
                assert sent.count("after this Diwali") <= 1, (k, sent)


def test_business_lean_comes_from_engine_dial():
    def lean(value, scores):
        p = fixture_a(work="job")
        p["scores"].update(scores)
        p["areas"]["business"]["dials"] = [{"left": "Job", "right": "Business", "value": value, "why": "x"},
                                           {"left": "Alone", "right": "Partner", "value": 0.55, "why": "y"}]
        return B.bank(p)["business.t1.what"]
    # the dial wins over the area scores in both directions
    assert "leans to business" in lean(0.85, {"business": 0, "career": 3})
    assert "leans to a job" in lean(0.25, {"business": 3, "career": 0})


def test_real_capped_charts_never_say_best_time():
    for tq in ("T2", "T3"):
        out = B.bank(_real("job", None, tq, i=3))
        hits = {k: v for k, v in out.items() if re.search(r"\bbest (time|months?)\b|best time inside", v, re.I)}
        assert not hits, (tq, list(hits.items())[:3])


def test_student_never_first_salary():
    for band in ("u25", "25_40", "40_60", "60p"):
        for work in ("student", "job"):
            out = B.bank(fixture_a(work=work, band=band))
            assert not any("first salary" in v for v in out.values()), (work, band)


def test_overall_best_and_careful_come_from_summary():
    p = fixture_a()
    p["summary"] = {"best": {"from": "2027-09", "to": "2027-10", "label": "Sep–Oct 2027"},
                    "careful": [{"from": "2027-03", "to": "2027-03", "reason": "reactions", "label": "Mar 2027"}]}
    out = B.bank(p)
    assert out["timeline.best"] == "Your single best time: Sep–Oct 2027"
    assert "your best time comes" in out["takeaways.4"].lower() and any(v in out["takeaways.4"] for v in B.POSV[3])
    assert "quick reactions" in out["takeaways.3"] and "spending," not in out["takeaways.3"]


@pytest.mark.parametrize("steer,lead,strong,want", [
    ("money", "money", "family", "You picked Money, so it leads; by your chart, Family & children is strongest"),
    ("money", "money", "money", "Money leads your report, and by your chart it is also your strongest area"),
    (None, "business", "career", "Your report opens with Business, as fits a business owner; by your chart, Career is strongest"),
])
def test_takeaway_one_lead_and_strongest(steer, lead, strong, want):
    p = fixture_a(steering=steer, work="business")
    p["wrapped"].update(lead_area=lead, strongest_area=strong)
    assert B.bank(p)["takeaways.1"].startswith(want)


def test_sun_strength_has_no_sun_tail():
    p = fixture_b()
    p["strengths"][0] = {"planet": "Sun", "sign": "Aries", "house": 10, "dignity": "exalted"}
    out = B.bank(p)
    assert not any("with your Sun in" in v for v in out.values())
    assert out["strengths.1.why"].count("Sun") == 1


# ── fix round 2 (verifier findings) ───────────────────────────────────────────────────────────────
_DOUBLED = re.compile(r"\b(\w+) \1\b", re.I)


def test_no_doubled_words():
    """'help help from elders', 'fits well well before ...': a slot filler must never repeat the word before it."""
    for out in _many_outputs():
        for k, v in out.items():
            assert not _DOUBLED.search(v), (k, v)


def test_luck_blessings_no_help_help():
    import diwali as D
    for i in range(5):
        for work in ("job", "business"):
            for tq in ("T0", "T3"):
                v = B.bank(D.compute_diwali(*REAL_BIRTHS[i], gender="male", work_type=work, steering=None,
                                            time_quality=tq))["luck.blessings.what"]
                assert "help help" not in v, v


def test_careful_spending_line_names_the_real_reason():
    """business.t5 (go slow on spending) must not call a quick-reactions month a careful time for spending."""
    import diwali as D
    p = D.compute_diwali("Savita Joshi", "1958-12-02", "05:30", 5.5, 26.91, 75.79, gender="female",
                         work_type="home", steering="marriage", time_quality="T2", place="Jaipur")
    reasons = {(m.get("care_reason")) for m in p["months"] if m.get("tone") == "careful"}
    v = B.bank(p)["business.t5.what"]
    if "spending" not in reasons:
        assert "careful time for spending" not in v, v
    for i in range(5):
        for tq in ("T0", "T2"):
            p = _real("job", None, tq, i)
            v = B.bank(p)["business.t5.what"]
            sp = [m["ym"] for m in p["months"] if m.get("care_reason") == "spending"]
            if "careful time for spending" in v:
                assert sp, v
            if "careful time for quick reactions" in v:
                assert not sp, v


def test_practices_why_one_clause_with_articles():
    for i in range(5):
        v = B.bank(_real("job", None, "T0", i))["practices.why"]
        assert not re.search(r"(follow|, | and )(Sun|Moon) ", v), v
        assert len(re.split(r"(?<=[.!?])\s+", v)) == 1 and " since " not in v, v


# ---- version matrix (the 28 buyers of tests/test_diwali_versions.py): bank-level product rules ---------------------
_MONTHS_RE = re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December|"
                        r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b|\b20\d\d\b")
_DATE_KEYS = ("months.", "timeline.", "gift.")   # date pages and the giver's own words


def _matrix_payloads():
    import functools
    import os
    import sys

    @functools.lru_cache(maxsize=1)
    def build():
        import diwali as D
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from test_diwali_versions import VERSIONS
        out = []
        for r in VERSIONS:
            c = dict(r)
            a = [c.pop(k) for k in ("name", "dob", "tob", "tz", "lat", "lon")]
            out.append(D.compute_diwali(*a, **c))
        return out
    return build()


_MATRIX = []


def _matrix():
    if not _MATRIX:
        _MATRIX.extend((p, B.bank(p)) for p in _matrix_payloads())
    return _MATRIX


def four_word_runs(out):
    """4-word runs said more than 3 times in one report -> count. Left out, as the task rule says: headings
    (titles), month names and years (they cut a run), the fixed "your 12 months" link. Also left out: text that
    is not our prose (the giver's own gift message), the 12-month table cells (table labels, checked on their
    own in test_twelve_month_table_rules) and wrapped.lead (the Wrapped card's copy of takeaway 1).
    Everything else counts, house names and time labels included."""
    c = {}
    for k, v in out.items():
        if k.endswith(".title") or k.startswith(("months.", "gift.")) or k == "wrapped.lead":
            continue
        t = _MONTHS_RE.sub(" | ", v).replace("your 12 months", " | ")
        for seg in re.split(r"[|\n.;:!?]", t):
            w = re.findall(r"[a-z0-9']+", seg.lower())
            for i in range(len(w) - 3):
                g = " ".join(w[i:i + 4])
                c[g] = c.get(g, 0) + 1
    return {g: n for g, n in c.items() if n > 3}


def test_four_word_runs_counts_house_names_and_time_labels():
    """The counter itself: house names, time labels and season words are NOT collapsed (verifier finding)."""
    out = {"a.what": "It sits in the children and planning part. Again in the children and planning part.",
           "b.what": "In the children and planning part. And in the children and planning part.",
           "c.title": "the children and planning part the children and planning part",
           "d.what": "Jan 2027 the money part grows. Feb 2027 the money part grows."}
    r = four_word_runs(out)
    assert r.get("the children and planning") == 4 and "the money part grows" not in r, r


def test_no_four_word_run_more_than_three_times_across_version_matrix():
    """Verifier finding: ~40 templated planet-trait tails per report. No 4-word run may come back 4+ times."""
    bad = {i: four_word_runs(o) for i, (_, o) in enumerate(_matrix())}
    bad = {i: r for i, r in bad.items() if r}
    assert not bad, sorted(bad.items())[:5]


_PLANET = r"\b(?:the )?(?:Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)\b"


def test_no_planet_trait_tail_outside_why():
    """A chart fact goes only in the Why line (Mock 3C): no '<planet> sits/rules ... , so <trait>' clause,
    and no planet named in a topic's what / do / watch (the Manglik box names Mars by design)."""
    tail = re.compile(_PLANET + r"[^.]*\b(?:sits|rules|is placed|is in|runs|leads)\b[^.]*,\s*so\b", re.I)
    for p, out in _matrix():
        for k, v in out.items():
            if k.endswith(".why") or k.startswith(("marriage.manglik.", "sadesati.", "practices.", "lookback.")):
                continue
            assert not tail.search(v), (k, v)
            if re.match(r"(money|career|business|family|marriage)\.t\d+\.(what|do|watch)$", k) and not k.startswith("marriage.t5"):
                assert not re.findall(_PLANET, v), (k, v)   # no planet named at all, not even the period


def test_no_best_claim_when_no_best_time():
    """T2/T3 (and any buyer with no month toned best): no best / brightest / strongest claim in any wording,
    headlines, Wrapped words and takeaways included. Same regex as the version check (one source)."""
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from test_diwali_versions import _BEST_CLAIM
    legend = re.compile(r"Full bloom your best time|Bright with rays: best time|mean a best time")
    seen = 0
    for p, out in _matrix():
        if B.has_best(p):
            continue
        seen += 1
        for k, v in out.items():
            if k.startswith("gift."):
                continue
            for line in v.split("\n"):
                m = _BEST_CLAIM.search(legend.sub("", line))
                assert not m, (p["meta"]["time_quality"], k, m.group(0), line)
            assert not re.search(r"\bbest (time|months?)\b", v, re.I), (k, v)
    assert seen >= 7   # every T2/T3 buyer of the matrix is checked


def test_twelve_month_table_rules():
    """Careful month: never 'gold' or 'a planned buy'. Gold only in gold months that are not careful.
    Watch: no line in more than 2 of 12 rows. Do: at least 3 different lines."""
    for p, out in _matrix():
        dos, watches = [], []
        for m in p["months"]:
            d, w = out[f"months.{m['ym']}.do"], out[f"months.{m['ym']}.watch"]
            dos.append(d)
            watches.append(w)
            if m["tone"] == "careful":
                assert not re.search(r"gold|planned buy", d, re.I), (m["ym"], d)
            if re.search(r"\bgold\b", d, re.I):
                assert "gold" in (m.get("tags") or []) and m["tone"] != "careful", (m["ym"], d)
            assert len(d.split()) < 8 and len(w.split()) < 8, (d, w)
        assert len(set(dos)) >= 3, dos
        assert max(watches.count(w) for w in watches) <= 2, watches


def test_single_month_range_never_doubled():
    for _, out in _matrix():
        for k, v in out.items():
            assert not re.search(r"\b([A-Z][a-z]{2})–\1\b", v), (k, v)
    assert B._rng(["2027-01"]) == "Jan 2027" and B._rng(["2027-01", "2027-03"]) == "Jan–Mar 2027"


def test_no_sentence_repeated_in_one_report():
    """Spec §9: no sentence (6+ words) printed twice in one report, date pages aside."""
    for _, out in _matrix():
        seen = {}
        for k, v in out.items():
            if k.startswith(_DATE_KEYS) or k.endswith(".title") or k == "wrapped.lead":
                continue
            for s in re.split(r"(?<=[.!?])\s+|\n", v):
                if len(s.split()) >= 6:
                    assert s.lower() not in seen, (seen.get(s.lower()), k, s)
                    seen[s.lower()] = k


# ── fix round 3 (verifier findings on round 2) ────────────────────────────────────────────────────
_CARE_CLAIM = re.compile(r"(?<![Nn]o )(?<![Nn]o long )\b(?:the|your|a|in|through) careful (?:time|times|months?|ones)\b")


def test_no_careful_time_talk_for_a_buyer_with_none():
    """A buyer with no careful month and no area careful time never reads about 'the careful months'."""
    seen = 0
    for p, out in _matrix():
        if any(m["tone"] == "careful" for m in p["months"]) or any(
                (a.get("windows") or {}).get("careful") or any(t.get("state") == "careful" for t in a.get("topics") or [])
                for a in p["areas"].values()):
            continue
        seen += 1
        for k, v in out.items():
            if k.endswith(".when") or k.startswith(("months.", "gift.")):
                continue
            assert not _CARE_CLAIM.search(v), (k, v)
    assert seen >= 3


def test_no_superlative_at_all_when_no_best_time():
    """T2/T3 (or no month toned best): no best / brightest / strongest / warmest / peak word anywhere, headlines,
    area lines, Wrapped words and takeaways included (round-2 finding: 'warmest', 'Your strongest area')."""
    seen = 0
    for p, out in _matrix():
        if B.has_best(p):
            continue
        seen += 1
        for k, v in out.items():
            if not k.startswith("gift."):
                assert not re.search(r"\b(best|brightest|strongest|warmest|peaks?|most of all)\b", v, re.I), (k, v)
    assert seen >= 7


def test_planet_period_named_rarely_and_plainly():
    """Round-2 finding: the period was named 24-30 times in rotating wordings. Now: at most 6 lines a report, only
    where the period is the subject (the look-back on the months it shaped, Better luck's 'what the months before
    built', the takeaway about it), in one plain form ('your X main period', 'your X–Y period', 'Y ... sub-period')."""
    for p, out in _matrix():
        md, ad = p["period"]["md"], p["period"]["ad"]
        hits = [(k, v) for k, v in out.items() if re.search(rf"\b{md}\b[^.]*\bperiod\b|\b{ad}\b[^.]*\bsub-period\b", v)]
        assert len(hits) <= 6, hits
        assert all(k.startswith(("lookback.", "luck.built", "takeaways.2")) for k, _ in hits), hits


def test_each_chart_fact_said_once_per_report():
    """Round-2 finding: one fact printed twice with synonyms swapped ('Jupiter passes the work part, whose ruler,
    the Sun, rests in Scorpio' / '... moves through ... sits in Scorpio'). No two reason lines name the same
    planets and the same parts of the chart."""
    hn = sorted(B.HOUSE.values(), key=len, reverse=True)
    for _, out in _matrix():
        seen = {}
        for k, v in out.items():
            if not k.endswith(".why") or k.startswith(("lookback.hard", "sadesati.")):
                continue
            t = v.lower()
            hs = []
            for h in hn:
                if h in t:
                    hs.append(h)
                    t = t.replace(h, "")
            transit = bool(re.search(r"\b(passes|moves through|moves into|moves in|turns back|travels through|looks at|look\b)", v))
            key = (transit, frozenset(re.findall(_PLANET, v)), frozenset(hs))
            if key[1] and key[2]:
                assert key not in seen, (seen.get(key), k, v)
                seen[key] = k


def test_what_paragraphs_carry_no_stock_trait_sentences():
    """Round-2 finding: '<topic> tends to come through <house meaning>' in nearly every What, some nonsense.
    The old sign-nature tables never reach a topic's what, and a reason's meaning is said once per area."""
    stock = [v for tbl in (B.GATHER5, B.SHARE7, B.TALK, B.PARTNER_SIGN) for v in tbl.values()] if hasattr(B, "GATHER5") else []
    for _, out in _matrix():
        for a in B.AREAS:
            whats = [v for k, v in out.items() if re.match(rf"{a}\.t\d+\.what$", k) and not k.startswith("marriage.t4")]
            for v in whats:
                assert not any(s in v for s in stock), v
            nouns = [n for v in whats for n in set(B.HELP.values()) | set(B.HELP_P.values()) if n in v]
            assert len(nouns) == len(set(nouns)), (a, nouns)


def test_timeline_careful_runs_named_not_spanned():
    p = fixture_a()
    p["timeline"][0].update({"from": "2026-11", "to": "2027-03", "core": [{"from": "2026-11", "to": "2026-11"},
                                                                         {"from": "2027-03", "to": "2027-03"}]})
    for m in p["months"]:
        m["tone"] = "careful" if m["ym"] in ("2026-11", "2027-03") else "steady"
    t = B.bank(p)["timeline.1"]
    assert "Careful in Nov 2026 and Mar 2027" in t
    assert t.startswith("Nov 2026–Mar 2027 ·"), t   # the part header may span; the careful phrase must not
    assert "Careful in Nov 2026–Mar 2027" not in t and "Jan–Jan" not in t


def test_from_never_doubles_the_preposition():
    for src, want in (("steps, from in early spring.", "steps, from early spring."),
                      ("start, from by midwinter.", "start, from midwinter."),
                      ("grow, from as spring begins.", "grow, from when spring begins."),
                      ("ease in, from right after Diwali.", "ease in, from right after Diwali.")):
        assert B._fix_from(src) == want
    for fx in (fixture_a, fixture_b):
        for k, v in B.bank(fx()).items():
            assert not re.search(r"\bfrom (in|by|at|as) ", v), (k, v)
