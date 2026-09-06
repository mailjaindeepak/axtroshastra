"""
flows_v2.py — application-level flows built on the MySQL-native db_v2 layer.

Piece 2 — the "report + lead" flow. When a visitor submits the birth-details form
(which now carries their phone), we do ONE atomic thing:
  * create/find the user by phone — this is the LEAD; the user is born HERE, at
    form-submit, not at payment (fixes the old "account only exists after paying"),
  * create the report with status='preview',
  * attach its subjects (1 person for solo products, 2 for compatibility).

The route layer will call submit_report() after running the astrology engine, so
the DB shape lives in one tested place. Functions take an open connection and DO
NOT commit — the caller owns the transaction, so the whole submission is
all-or-nothing.
"""
import re

import db_v2


def split_phone(raw: str):
    """'+91 98765 43210' -> ('+91', '9876543210'). Returns (None, None) if fewer
    than 10 digits. Country code = digits before the last 10, else defaults +91."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) < 10:
        return None, None
    return ("+" + digits[:-10]) if len(digits) > 10 else "+91", digits[-10:]


def clean_email(raw: str | None):
    """Real email or None — never the void@razorpay.com sentinel or a test addr."""
    e = (raw or "").strip().lower()
    if not e or e == "void@razorpay.com" or e.endswith("@axtroshastra.test"):
        return None
    return e


def submit_report(conn, *, product: str, phone: str, report_data: dict | None,
                  subjects: list[dict], email: str | None = None,
                  lang: str = "en", variant: str | None = None):
    """Atomic report submission (a lead). Returns (report_id, user_id).

    subjects: a list of dicts, each with any of role / name / gender / dob / tob /
    time_quality / birth_place / birth_lat / birth_lon / birth_tz. Solo -> 1 dict;
    compatibility -> 2. The caller commits.
    """
    cc, mobile = split_phone(phone)
    if not mobile:
        raise ValueError("submit_report needs a phone with at least 10 digits")
    if not subjects:
        raise ValueError("submit_report needs at least one subject")

    user_id = db_v2.create_or_get_user(conn, cc, mobile, email=clean_email(email))
    report_id = db_v2.create_report(conn, user_id, product, report_data,
                                    lang=lang, variant=variant, status="preview")
    for s in subjects:
        db_v2.add_subject(
            conn, report_id, s.get("role", "self"),
            name=s.get("name"), gender=s.get("gender"), dob=s.get("dob"),
            tob=s.get("tob"), time_quality=s.get("time_quality"),
            birth_place=s.get("birth_place"), birth_lat=s.get("birth_lat"),
            birth_lon=s.get("birth_lon"), birth_tz=s.get("birth_tz"),
        )
    return report_id, user_id
