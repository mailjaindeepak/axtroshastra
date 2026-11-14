"""Server-side validation for the Mulank form. Pure functions, no I/O, no logging of values.

Every error carries the field and a stable code so the page can show the message beside the
right input. Gender is optional, never used in the calculation, and 'prefer_not_to_say' is
stored as no gender at all.
"""
import re
from datetime import date

import numerology
import numerology_preview

GENDERS = ("female", "male", "other", "prefer_not_to_say")
DB_GENDERS = ("female", "male", "other")       # report_subjects.gender enum; anything else is NULL
MESSAGES = {
    "name_required": "Please enter your full name.",
    "name_invalid": "Please enter your name using letters (up to 80 characters).",
    "dob_required": "Please enter your date of birth as DD/MM/YYYY.",
    "dob_format": "Please enter your date of birth as DD/MM/YYYY.",
    "dob_invalid": "That date does not exist. Please check the day, month and year.",
    "dob_future": "Your date of birth cannot be in the future.",
    "dob_too_old": "Please enter a year from 1900 onwards.",
    "gender_invalid": "Please choose one of the listed options.",
    "country_unsupported": "WhatsApp delivery is available for +91 numbers only right now.",
    "phone_required": "Please enter your WhatsApp number.",
    "phone_invalid": "Please enter a valid 10-digit Indian mobile number.",
    "consent_required": "Please accept the Terms of Service and Privacy Policy to continue.",
    "invalid": "Something went wrong. Please try again.",
}


class FormError(Exception):
    def __init__(self, field: str, code: str):
        super().__init__(code)
        self.field, self.code = field, code

    def detail(self) -> dict:
        return {"field": self.field, "code": self.code, "message": MESSAGES.get(self.code, MESSAGES["invalid"])}


def parse_dob(raw, today=None) -> tuple:
    """Accepts DD/MM/YYYY (what people type) or YYYY-MM-DD (what we store). Returns (day, month, year)."""
    s = str(raw or "").strip()
    if not s:
        raise FormError("dob", "dob_required")
    m = re.fullmatch(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", s)
    if m:
        d, mo, y = (int(x) for x in m.groups())
    else:
        m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
        if not m:
            raise FormError("dob", "dob_format")
        y, mo, d = (int(x) for x in m.groups())
    try:
        numerology.compute_mulank(d, mo, y, today=today)
    except numerology.NumerologyInputError as e:
        msg = str(e)
        code = "dob_future" if "future" in msg else "dob_too_old" if "1900" in msg else "dob_invalid"
        raise FormError("dob", code)
    return d, mo, y


def clean_phone(country_code, raw) -> str:
    """Ten-digit Indian mobile (v1 is +91 only). Accepts spaces, dashes, a leading 0 or 91."""
    cc = re.sub(r"\s", "", str(country_code or "+91"))
    if cc not in ("+91", "91", "0091"):
        raise FormError("phone", "country_unsupported")
    digits = re.sub(r"[\s\-().]", "", str(raw or ""))
    if digits.startswith("+91"):
        digits = digits[3:]
    elif len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if not digits:
        raise FormError("phone", "phone_required")
    if not re.fullmatch(r"[6-9]\d{9}", digits):
        raise FormError("phone", "phone_invalid")
    return digits


def validate(form: dict, today=None) -> dict:
    """Returns {name, dob_iso, day, month, year, gender, phone, marketing_optin}. Raises FormError."""
    if not form.get("consent_terms") is True:
        raise FormError("consent_terms", "consent_required")
    try:
        name = numerology_preview.clean_name(form.get("name"))
    except ValueError:
        raise FormError("name", "name_required" if not str(form.get("name") or "").strip() else "name_invalid")
    if not any(ch.isalpha() for ch in name):
        raise FormError("name", "name_invalid")
    d, mo, y = parse_dob(form.get("dob"), today=today)
    gender = form.get("gender")
    gender = None if gender in (None, "") else gender
    if gender is not None and gender not in GENDERS:
        raise FormError("gender", "gender_invalid")
    phone = clean_phone(form.get("country_code"), form.get("phone"))
    return {"name": name, "dob_iso": date(y, mo, d).isoformat(), "day": d, "month": mo, "year": y,
            "gender": gender, "phone": phone, "marketing_optin": form.get("marketing_optin") is True}
