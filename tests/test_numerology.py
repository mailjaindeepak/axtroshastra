"""Mulank numerology engine - hand-verified values, validation, dynamic years."""
import inspect
from datetime import date, datetime

import pytest

import numerology as nm

REF = date(2026, 11, 1)


def _c(d, m, y, today=REF):
    return nm.compute_mulank(d, m, y, today=today)


def test_persona_core_numbers():
    r = _c(29, 7, 1990)
    assert r["mulank"] == {"number": 2, "planet": "Moon", "working": [29, 11, 2]}
    assert r["bhagyank"] == {"number": 1, "planet": "Sun", "working": [37, 10, 1]}
    assert r["pair_key"] == "2-1"


def test_persona_personal_years_2026_2027():
    py = _c(29, 7, 1990, today=date(2026, 3, 5))["personal_year"]
    assert py["current"]["year"] == 2026
    assert py["current"]["parts"] == {"day": 11, "month": 7, "year": 10}
    assert py["current"]["working"] == [28, 10, 1]
    assert py["current"]["number"] == 1
    assert py["next"]["year"] == 2027
    assert py["next"]["parts"] == {"day": 11, "month": 7, "year": 11}
    assert py["next"]["working"] == [29, 11, 2]
    assert py["next"]["number"] == 2


@pytest.mark.parametrize("day,number,working", [
    (22, 4, [22, 4]),          # master number reduced
    (11, 2, [11, 2]),
    (9, 9, [9]),
    (1, 1, [1]),
    (10, 1, [10, 1]),
    (20, 2, [20, 2]),
    (30, 3, [30, 3]),
    (29, 2, [29, 11, 2]),
])
def test_mulank_day_reduction(day, number, working):
    m = _c(day, 1, 2000)["mulank"]
    assert m["number"] == number and m["working"] == working


def test_master_numbers_never_returned():
    for d in range(1, 29):
        for mo in range(1, 13):
            r = _c(d, mo, 1985)
            assert 1 <= r["mulank"]["number"] <= 9
            assert 1 <= r["bhagyank"]["number"] <= 9
            assert 1 <= r["personal_year"]["current"]["number"] <= 9


def test_leap_day():
    assert _c(29, 2, 2000)["meta"]["dob"] == "2000-02-29"
    with pytest.raises(nm.NumerologyInputError):
        _c(29, 2, 2001)


@pytest.mark.parametrize("args", [
    (31, 4, 1990), (31, 2, 1990), (0, 5, 1990), (32, 1, 1990),
    (1, 0, 1990), (1, 13, 1990),
    (1, 1, 1899), (1, 1, 0), (1, 1, 2027), (2, 11, 2026),   # range / future
    (None, 5, 1990), (5, None, 1990), (5, 5, None),          # partial
    ("5", 5, 1990), (5.0, 5, 1990), (True, 5, 1990),         # not whole numbers
])
def test_invalid_dob_rejected(args):
    with pytest.raises(nm.NumerologyInputError):
        _c(*args)


def test_error_is_value_error_with_message():
    with pytest.raises(ValueError, match="required"):
        _c(None, 1, 1990)


def test_boundaries_accepted():
    assert _c(1, 1, nm.MIN_YEAR)["meta"]["dob"] == "1900-01-01"
    assert _c(1, 11, 2026)["meta"]["dob"] == "2026-11-01"   # born on reference day


def test_year_rollover_dec_31():
    r = _c(29, 7, 1990, today=date(2026, 12, 31))
    assert (r["meta"]["current_year"], r["meta"]["next_year"]) == (2026, 2027)
    r = _c(29, 7, 1990, today=date(2027, 1, 1))
    assert (r["meta"]["current_year"], r["meta"]["next_year"]) == (2027, 2028)
    assert r["personal_year"]["current"]["number"] == 2
    # 2028: 11 + 7 + 12 = 30 -> 3
    assert r["personal_year"]["next"]["working"] == [30, 3]
    assert r["personal_year"]["next"]["number"] == 3


def test_results_follow_reference_year():
    a = _c(29, 7, 1990, today=date(2026, 6, 1))["personal_year"]
    b = _c(29, 7, 1990, today=date(2027, 6, 1))["personal_year"]
    assert a["current"]["year"] != b["current"]["year"]
    assert a["current"]["number"] != b["current"]["number"]
    assert a["next"] == b["current"]          # next year then == current year later


def test_today_accepts_datetime_and_defaults_to_real_date():
    assert _c(5, 5, 1990, today=datetime(2026, 12, 31, 23, 59))["meta"]["current_year"] == 2026
    assert nm.compute_mulank(5, 5, 1990)["meta"]["current_year"] == date.today().year
    with pytest.raises(nm.NumerologyInputError):
        _c(5, 5, 1990, today="2026-01-01")


def test_planet_table():
    assert nm.PLANETS == {1: "Sun", 2: "Moon", 3: "Jupiter", 4: "Rahu",
                          5: "Mercury", 6: "Venus", 7: "Ketu", 8: "Saturn",
                          9: "Mars"}


def test_all_mulank_values_reachable():
    seen = {_c(d, 1, 2000)["mulank"]["number"] for d in range(1, 32)}
    assert seen == set(range(1, 10))


def test_all_81_pair_keys_reachable_and_well_formed():
    keys = set()
    for y in range(1900, 1926):
        for mo in range(1, 13):
            for d in (1, 2, 3, 4, 5, 6, 7, 8, 9):
                keys.add(_c(d, mo, y)["pair_key"])
    assert keys == {f"{m}-{b}" for m in range(1, 10) for b in range(1, 10)}
    for k in keys:
        m, b = k.split("-")
        assert m.isdigit() and b.isdigit() and 1 <= int(m) <= 9 and 1 <= int(b) <= 9


def test_no_gender_input_and_facts_only():
    params = set(inspect.signature(nm.compute_mulank).parameters)
    assert params == {"day", "month", "year", "today"}
    with pytest.raises(TypeError):
        nm.compute_mulank(1, 1, 1990, gender="f")
    assert set(_c(1, 1, 1990)) == {"product", "meta", "mulank", "bhagyank",
                                   "pair_key", "personal_year"}
