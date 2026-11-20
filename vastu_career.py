"""Vastu Career Report: deterministic engine for the free preview (no LLM, no chart, no ephemeris).

Spec: docs/vastu-career-report-spec.md (sections 2, 3, 6). Research and sources: docs/vastu-career-research.md.

IMPORTANT: every direction cell, number-to-direction pair and wording below is a WORKING DEFAULT that the owner
approved for the visual mock only (20 Nov 2026). Nothing here is final until the owner approves it cell by cell
(spec section 10). Keep it PENDING in the spec until then.

What this module returns is the FREE data only. The teaser never carries the fixes, the five segment cards or the
number colours: those stay locked until payment (spec section 6).

Number functions are reused from numerology.py, never forked.
"""
from datetime import date, datetime, timezone

import numerology

SEGMENTS = ("student", "exam_aspirant", "professional", "wfh", "owner", "job_seeker")
DIRECTIONS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
DIR_OR_UNSURE = DIRECTIONS + ("not_sure",)
FLEXIBILITY = ("can_move", "a_little", "cannot_or_shared")

DIR_NAME = {"N": "North", "NE": "North-East", "E": "East", "SE": "South-East",
            "S": "South", "SW": "South-West", "W": "West", "NW": "North-West"}
FLEX_LABEL = {"can_move": "Can move the desk", "a_little": "Can turn it a little", "cannot_or_shared": "Cannot move it"}

# ---- direction matrix (PENDING owner approval; E, N, NE, W, S are sourced, SE/SW/NW are extrapolations) ----
_STUDY = {"ideal": ("N", "NE", "E"), "acceptable": ("W",)}
MATRIX = {
    "student": _STUDY,
    "exam_aspirant": _STUDY,
    "professional": {"ideal": ("N", "E"), "acceptable": ("NE",)},
    "wfh": {"ideal": ("N", "E"), "acceptable": ("NE",)},
    "owner": {"ideal": ("N", "E"), "acceptable": ("NE",)},
    "job_seeker": {"ideal": ("E", "N"), "acceptable": ("NE", "W")},
}

# ---- Mulank to direction, derived via the ruling planet (PENDING). 7 (Ketu) has no direction: colour only ----
NUMBER_DIRECTION = {1: "E", 2: "NW", 3: "NE", 4: "SW", 5: "N", 6: "SE", 7: None, 8: "W", 9: "S"}

SEGMENT_META = {
    "student": dict(label="Student", noun="desk", who="a student", first="east, north and north-east", purpose="study"),
    "exam_aspirant": dict(label="Exam aspirant", noun="desk", who="an exam aspirant", first="east, north and north-east", purpose="long study"),
    "professional": dict(label="Working professional", noun="desk", who="a working professional", first="north and east", purpose="an office desk"),
    "wfh": dict(label="Work from home", noun="desk", who="someone working from home", first="north and east", purpose="a home desk"),
    "owner": dict(label="Business owner", noun="seat", who="a business owner", first="north and east", purpose="the owner's seat"),
    "job_seeker": dict(label="Job seeker", noun="desk", who="a job seeker", first="east and north", purpose="interview preparation"),
}

# the five questions each report answers (also the five locked answers in the preview); DRAFT copy, owner approves per segment
QUESTIONS = {
    "student": [
        ("Which way should you face while studying?", "Which direction suits you, and what to do if your desk cannot face it."),
        ("Is your desk placed well in the room?", "How the wall, the door and the space around your seat read in Vastu."),
        ("Which colours suit your study corner?", "Light, plain colours for the walls, curtains and desk mat."),
        ("What should stay on your desk, and what should go?", "A short keep and drop list, and a nightly reset."),
        ("How do light and fresh air help long hours?", "Where the light comes from, and a lamp for the evenings."),
    ],
    "exam_aspirant": [
        ("Which direction suits long study hours?", "The direction and seat for long hours, and what to do if the desk stays put."),
        ("Where should your revision corner be?", "Where charts and the timetable go so they catch your eye."),
        ("How should light and air work for night study?", "A lamp that does not glare, and fresh air through the evening."),
        ("What is a good nightly reset?", "A clear desk and a clear start for the next morning."),
        ("Which mistakes do aspirants tend to make?", "The habits tradition says to leave behind."),
    ],
    "professional": [
        ("Which way should your desk face?", "Your desk direction against the traditional first choices for office work."),
        ("Is your seat well supported?", "The wall behind you, the view of the door, and what sits overhead."),
        ("How do you keep your growth zone open?", "Keeping the north of your desk and room clear and tidy."),
        ("What decor helps, and what hurts?", "Plants, pictures and clocks, and what to remove."),
        ("Which desk mistakes should you fix first?", "The common ones, and how to fix them in a shared office."),
    ],
    "wfh": [
        ("Which corner of your home suits your work?", "Choosing the corner, and which walls to avoid behind you."),
        ("Can the bedroom double as an office?", "How to keep work and rest apart in one room."),
        ("How should light and your screen sit?", "Side light, an evening lamp, and reflections."),
        ("What layout leaves room to think?", "A clear centre, a creative corner and fewer distractions."),
        ("How do you end the workday at home?", "A closing routine, and the mistakes to drop."),
    ],
    "owner": [
        ("Which way should the owner's seat face?", "Your seat and cabin against the traditional first choices."),
        ("Where should the cash box go?", "The cash counter and cash box, and how to keep them."),
        ("What does your entrance say?", "The shop or office entrance, and what to keep clear."),
        ("How should stock and space be arranged?", "Layout basics for stock, space and the north-east."),
        ("Which premises mistakes should you fix?", "Beams, doors and clutter, and how to fix them."),
    ],
    "job_seeker": [
        ("Where should you prepare for interviews?", "The space, the direction and what sits on the desk."),
        ("How is your career corner at home?", "The north of your home, and what to keep there."),
        ("What does your main door say?", "The door and entrance, and what to clear."),
        ("What should the day before look like?", "Documents, a steady morning and the way you leave."),
        ("Which home habits should you drop?", "The common ones, and how to change them."),
    ],
}

# one small, practical use of the number's direction (DRAFT copy); never an instruction to face that way
_NUMBER_TIP = {
    "N": "A plant or a lamp on the north side of your desk is a simple way to use this.",
    "NE": "Keeping the north-east corner of your room tidy and bright is a simple way to use this.",
    "E": "A window or a light on the east side of your room is a simple way to use this.",
    "SE": "A small lamp in the south-east corner of your room is a simple way to use this.",
    "S": "Vastu advises against facing south at a desk, so treat south as a place to put something, not the way to face.",
    "SW": "A shelf of books in the south-west corner of the room is a simple way to use this.",
    "W": "Your work files or a plant on the west side of your room is a simple way to use this.",
    "NW": "Keeping the north-west corner of your room clear is a simple way to use this.",
}
_NO_DIRECTION_TIP = ("Traditions place the planet linked with {n} in different directions, so this report gives you a "
                     "colour instead of a direction.")


class VastuInputError(ValueError):
    """Bad input. `field` names the form field so the page can show an inline error."""

    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field
        self.message = message

    def detail(self) -> dict:
        return {"field": self.field, "message": self.message}


def _parse_dob(dob: str, today: date) -> date:
    try:
        y, m, d = (int(x) for x in str(dob or "").split("-"))
        parsed = date(y, m, d)
    except (ValueError, TypeError):
        raise VastuInputError("dob", "Please enter a real date of birth.")
    if parsed.year < 1900:
        raise VastuInputError("dob", "Please enter a year from 1900 onwards.")
    if parsed > today:
        raise VastuInputError("dob", "Your date of birth cannot be in the future.")
    return parsed


def validate(name, dob, segment, desk_direction, desk_flexibility, door_direction=None, today=None) -> dict:
    """Explicit inline errors, never a silent default (CLAUDE.md section 1)."""
    today = today or date.today()
    nm = " ".join(str(name or "").split())
    if not nm:
        raise VastuInputError("name", "Please enter your full name.")
    if len(nm) > 60:
        raise VastuInputError("name", "Please use up to 60 characters for your name.")
    d = _parse_dob(dob, today)
    if segment not in SEGMENTS:
        raise VastuInputError("segment", "Please choose the option that describes you.")
    if desk_direction not in DIR_OR_UNSURE:
        raise VastuInputError("desk_direction", "Please choose the way you face at your desk, or 'Not sure'.")
    if desk_flexibility not in FLEXIBILITY:
        raise VastuInputError("desk_flexibility", "Please tell us whether you can move your desk.")
    if door_direction in (None, ""):
        door = None
    elif door_direction in DIR_OR_UNSURE:
        door = door_direction
    else:
        raise VastuInputError("door_direction", "Please choose a direction for your main door, or leave it blank.")
    return {"name": nm, "dob": d, "segment": segment, "desk_direction": desk_direction,
            "desk_flexibility": desk_flexibility, "door_direction": door}


def desk_verdict(segment: str, desk_direction: str, number_direction) -> dict:
    """Vastu verdict from the segment matrix, then rule B (owner, 20 Nov 2026):
    an `acceptable` verdict becomes `ideal` when the desk faces the buyer's number direction. A `change` verdict is
    never upgraded, and a number direction never downgrades or overrides the Vastu result."""
    if desk_direction == "not_sure":
        return {"verdict": "unknown", "rule_b": False}
    cell = MATRIX[segment]
    if desk_direction in cell["ideal"]:
        return {"verdict": "ideal", "rule_b": False}
    if desk_direction in cell["acceptable"]:
        if number_direction is not None and desk_direction == number_direction:
            return {"verdict": "ideal", "rule_b": True}
        return {"verdict": "acceptable", "rule_b": False}
    return {"verdict": "change", "rule_b": False}


def _why(segment: str, verdict: str, desk_direction: str, flexibility: str) -> str:
    m = SEGMENT_META[segment]
    base = f"For {m['who']}, tradition names {m['first']} as the first choices for {m['purpose']}."
    if verdict == "unknown":
        return base + " Tell us which way you face, and your result appears here."
    dn = DIR_NAME[desk_direction]
    if verdict == "ideal":
        txt = base + (" You are already facing one of them." if desk_direction in MATRIX[segment]["ideal"]
                      else f" {dn} is named as acceptable, and your birth number points the same way, so this report reads your {m['noun']} as ideal.")
    elif verdict == "acceptable":
        txt = base + f" {dn} is a secondary option, so a small change can move you to a stronger setup."
    else:
        txt = base + f" {dn} is not among them, so a change helps."
        if flexibility == "cannot_or_shared":
            txt += f" This report gives you fixes that work without moving the {m['noun']}."
    if segment == "owner":
        txt += " This check covers the way you face only, not where in the room you sit."
    return txt


def _stand(segment: str, verdict: str, rule_b: bool, desk_direction: str, flexibility: str) -> str:
    m = SEGMENT_META[segment]
    if verdict == "unknown":
        return f"Stand at your {m['noun']} and note which way you face. A compass app on your phone helps."
    if verdict == "ideal":
        return (f"Your {m['noun']} already faces a favoured direction, and your birth number agrees." if rule_b
                else "You are already facing a first-choice direction.")
    if verdict == "acceptable":
        return f"Your {m['noun']} is one small turn from a first-choice direction."
    dn = DIR_NAME[desk_direction].lower()
    if flexibility == "cannot_or_shared":
        return f"Your {m['noun']} faces {dn}, which tradition does not list here, so your fixes focus on seat, light and layout."
    return f"Your {m['noun']} faces {dn}, which tradition does not list here, and you can change it."


def compute_vastu_career(name, dob, segment, desk_direction, desk_flexibility, door_direction=None, today=None) -> dict:
    """Validate, compute and return the report dict that is saved (product `vastu_career`). `teaser` is FREE data only."""
    today = today or date.today()
    f = validate(name, dob, segment, desk_direction, desk_flexibility, door_direction, today=today)
    d = f["dob"]
    E = numerology.compute_mulank(d.day, d.month, d.year, today=today)          # reuse, never fork
    mulank, planet = E["mulank"]["number"], E["mulank"]["planet"]
    ndir = NUMBER_DIRECTION[mulank]
    v = desk_verdict(f["segment"], f["desk_direction"], ndir)
    m = SEGMENT_META[f["segment"]]
    verdict = v["verdict"]
    labels = {"ideal": "Ideal", "acceptable": "Acceptable", "change": "Change advised", "unknown": "Not sure yet"}
    tip = _NUMBER_TIP[ndir] if ndir else _NO_DIRECTION_TIP.format(n=mulank)
    teaser = {
        "name": f["name"],
        "dob_text": f"{d.day} {d.strftime('%B %Y')}",
        "segment": f["segment"], "segment_label": m["label"], "noun": m["noun"],
        "desk_direction": f["desk_direction"],
        "desk_label": DIR_NAME.get(f["desk_direction"], "Not sure"),
        "flexibility": f["desk_flexibility"], "flexibility_label": FLEX_LABEL[f["desk_flexibility"]],
        "door_label": DIR_NAME.get(f["door_direction"], "Not sure") if f["door_direction"] else "Not given",
        "verdict": verdict, "verdict_label": labels[verdict], "rule_b": v["rule_b"],
        "first_choices": m["first"],
        "why": _why(f["segment"], verdict, f["desk_direction"], f["desk_flexibility"]),
        "stand": _stand(f["segment"], verdict, v["rule_b"], f["desk_direction"], f["desk_flexibility"]),
        "compass": {"ideal": list(MATRIX[f["segment"]]["ideal"]), "acceptable": list(MATRIX[f["segment"]]["acceptable"]),
                    "desk": f["desk_direction"] if f["desk_direction"] != "not_sure" else None},
        "number": {"mulank": mulank, "planet": planet, "working": E["mulank"]["working"],
                   "direction": DIR_NAME[ndir] if ndir else None, "tip": tip,
                   "planets": numerology.PLANETS},
        "questions": [{"q": q, "d": dsc} for q, dsc in QUESTIONS[f["segment"]]],
        "generated": today.isoformat(),
    }
    return {
        "product": "vastu_career",
        "meta": {"name": f["name"], "dob": d.isoformat(), "segment": f["segment"],
                 "desk_direction": f["desk_direction"], "desk_flexibility": f["desk_flexibility"],
                 "door_direction": f["door_direction"], "lang": "english",
                 "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
        "teaser": teaser,
    }
