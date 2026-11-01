"""Mulank numerology - deterministic engine (pipeline step 1).

compute_mulank() is the single entry point. DOB only (no gender, name, time or
place). It returns facts + meta in the usual product / meta / full shape; no
prose, no LLM. A renderer keys interpretations on result["pair_key"].
"""

import calendar
from datetime import date, datetime

MIN_YEAR = 1900

PLANETS = {1: "Sun", 2: "Moon", 3: "Jupiter", 4: "Rahu", 5: "Mercury",
           6: "Venus", 7: "Ketu", 8: "Saturn", 9: "Mars"}


class NumerologyInputError(ValueError):
    """Raised for a missing, partial, impossible or out-of-range date of birth."""


def _digit_sum(n: int) -> int:
    return sum(int(c) for c in str(n))


def _reduce(n: int) -> list:
    """Working for reducing n to one digit: [n, sum, ..., digit].

    11 and 22 are always reduced (no master-number carve-out).
    """
    steps = [n]
    while steps[-1] > 9:
        steps.append(_digit_sum(steps[-1]))
    return steps


def _as_int(value, label: str) -> int:
    if value is None or isinstance(value, bool) or not isinstance(value, int):
        raise NumerologyInputError(f"{label} is required and must be a whole number")
    return value


def _reference_date(today) -> date:
    if today is None:
        return date.today()
    if isinstance(today, datetime):
        return today.date()
    if isinstance(today, date):
        return today
    raise NumerologyInputError("today must be a date")


def _validate_dob(day, month, year, ref: date) -> date:
    day, month, year = _as_int(day, "day"), _as_int(month, "month"), _as_int(year, "year")
    if not 1 <= month <= 12:
        raise NumerologyInputError("month must be between 1 and 12")
    if year < MIN_YEAR:
        raise NumerologyInputError(f"year must be {MIN_YEAR} or later")
    if year > ref.year:
        raise NumerologyInputError("date of birth cannot be in the future")
    if not 1 <= day <= calendar.monthrange(year, month)[1]:
        raise NumerologyInputError("day does not exist in that month")
    dob = date(year, month, day)
    if dob > ref:
        raise NumerologyInputError("date of birth cannot be in the future")
    return dob


def _personal_year(day: int, month: int, year: int) -> dict:
    day_part, month_part, year_part = (_digit_sum(day), _digit_sum(month),
                                       _digit_sum(year))
    total = day_part + month_part + year_part
    steps = _reduce(total)
    return {
        "year": year,
        "number": steps[-1],
        "parts": {"day": day_part, "month": month_part, "year": year_part},
        "total": total,
        "working": steps,
    }


def compute_mulank(day: int, month: int, year: int, today=None) -> dict:
    """Return Mulank, Bhagyank, ruling planets and personal years for a DOB.

    `today` (date/datetime, default the real date) is the reference for the
    current and next personal year and for the future-date check. Invalid or
    partial input raises NumerologyInputError; nothing is ever defaulted.
    """
    ref = _reference_date(today)
    dob = _validate_dob(day, month, year, ref)

    mulank_steps = _reduce(dob.day)
    bhagyank_total = _digit_sum(dob.day) + _digit_sum(dob.month) + _digit_sum(dob.year)
    bhagyank_steps = _reduce(bhagyank_total)
    mulank, bhagyank = mulank_steps[-1], bhagyank_steps[-1]

    return {
        "product": "numerology_mulank",
        "meta": {
            "dob": dob.isoformat(),
            "reference_date": ref.isoformat(),
            "current_year": ref.year,
            "next_year": ref.year + 1,
        },
        "mulank": {"number": mulank, "planet": PLANETS[mulank],
                   "working": mulank_steps},
        "bhagyank": {"number": bhagyank, "planet": PLANETS[bhagyank],
                     "working": bhagyank_steps},
        "pair_key": f"{mulank}-{bhagyank}",
        "personal_year": {
            "current": _personal_year(dob.day, dob.month, ref.year),
            "next": _personal_year(dob.day, dob.month, ref.year + 1),
        },
    }
