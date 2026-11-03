"""Mulank content registry and sale-eligibility check (server side, authoritative).

A (Mulank, Bhagyank) pair is sellable only if EVERY content key its paid report
would render is `verified` with a named reviewer and a review date. `sample_ok`,
`needs_review` and `pending` never count, and no flag promotes them. Nothing in
the registry below is verified today, so every pair is ineligible in production.
Tests pass their own registry to `pair_readiness`.
"""
from dataclasses import dataclass

import mulank_bank
import numerology

VERIFIED = "verified"
SAMPLE_OK = "sample_ok"
NEEDS_REVIEW = "needs_review"
PENDING = "pending"
STATUSES = (VERIFIED, SAMPLE_OK, NEEDS_REVIEW, PENDING)

CONTENT_VERSION = "mulank-content-0"


@dataclass(frozen=True)
class Entry:
    status: str = PENDING
    reviewed_by: str = ""
    reviewed_on: str = ""
    source_ids: tuple = ()


# Key shapes: M<n>, B<n>, Y<n>, PS:<m>-<b>, PB:<m>-<b> (cards 5-7 pair bank),
# CMP:<m>-<b> (card 10), LK:<m>-<b> (card 13), R:<Planet>><Planet>.
# Only entries that exist as drafted text are listed; absence means missing.
REGISTRY = {
    "M2": Entry(SAMPLE_OK),
    "B1": Entry(SAMPLE_OK),
    "PS:2-1": Entry(SAMPLE_OK),
    "Y1": Entry(SAMPLE_OK),
    "Y2": Entry(SAMPLE_OK),
    "R:Moon>Sun": Entry(SAMPLE_OK),
    "R:Sun>Moon": Entry(SAMPLE_OK),
    "PB:2-1": Entry(SAMPLE_OK),
    "CMP:2-1": Entry(SAMPLE_OK),
    "LK:2-1": Entry(SAMPLE_OK),
}


def _today():
    """Reference date for personal years; one place so tests can pin it."""
    from datetime import date
    return date.today()


has_text = mulank_bank.has_text          # tests may replace this; production never does


def is_verified(entry) -> bool:
    return bool(
        entry
        and entry.status == VERIFIED
        and entry.reviewed_by.strip()
        and entry.reviewed_on.strip()
    )


def required_keys(result: dict) -> list:
    """Every registry key the paid report needs for this computed result."""
    m = result["mulank"]["number"]
    b = result["bhagyank"]["number"]
    pm = result["mulank"]["planet"]
    pb = result["bhagyank"]["planet"]
    pair = f"{m}-{b}"
    py = result["personal_year"]
    keys = [f"M{m}", f"B{b}", f"PS:{pair}", f"PB:{pair}", f"CMP:{pair}",
            f"LK:{pair}",
            f"Y{py['current']['number']}", f"Y{py['next']['number']}"]
    if pm != pb:
        keys += [f"R:{pm}>{pb}", f"R:{pb}>{pm}"]
    return list(dict.fromkeys(keys))


def pair_readiness(day, month, year, today=None, registry=None) -> dict:
    """Returns {eligible, reason_code, content_version, missing, pair_key}.

    `missing` is for the server-side gap log only; never send it to a client.
    Raises NumerologyInputError for an invalid DOB.
    """
    reg = REGISTRY if registry is None else registry
    today = today or _today()
    result = numerology.compute_mulank(day, month, year, today=today)
    missing = [k for k in required_keys(result) if not is_verified(reg.get(k))]
    if registry is None:     # production ledger: verified is not enough, the drafted text must exist too
        missing += ["text:" + k for k in required_keys(result) if is_verified(reg.get(k)) and not has_text(k)]
    return {
        "eligible": not missing,
        "reason_code": "ok" if not missing else "content_not_verified",
        "content_version": CONTENT_VERSION,
        "missing": missing,
        "pair_key": result["pair_key"],
    }


def gap_log_line(readiness: dict) -> str:
    """One PII-free line for the content-gap log."""
    return "[mulank] ineligible pair=%s missing=%s" % (
        readiness["pair_key"], ",".join(readiness["missing"]))
