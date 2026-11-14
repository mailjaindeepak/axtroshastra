"""Mulank content ledger and sale-eligibility check (server side, authoritative).

Two things decide whether a (Mulank, Bhagyank) pair may be sold, and they are tracked separately:

  APPROVED  every content key the paid report needs has an entry in mulank_registry.json that is either
              `verified`        reviewed by an external expert (reviewed_by + reviewed_on), or
              `owner_approved`  editorially reviewed by a named editor and approved by a named business owner
                                (editor + approved_by + approved_on).
            `sample_ok`, `needs_review` and `pending` never count, whatever else is set.
  COMPLETE  drafted text for every one of those keys exists in mulank_bank.json, so the report can be rendered
            with no fallback line, no sample text and no other pair's reading.

A pair is eligible only if it is both. Approval without text, or text without approval, is never enough.
Tests pass their own registry to `pair_readiness`.
"""
import json
import os
import re
from dataclasses import dataclass

import mulank_bank
import numerology

VERIFIED = "verified"                 # external expert verification
OWNER_APPROVED = "owner_approved"     # editorial review + business-owner approval (no external expert)
SAMPLE_OK = "sample_ok"
NEEDS_REVIEW = "needs_review"
PENDING = "pending"
STATUSES = (VERIFIED, OWNER_APPROVED, SAMPLE_OK, NEEDS_REVIEW, PENDING)

CONTENT_VERSION = "mulank-content-1"
NODES = ("Rahu", "Ketu")
REL_CONFLICTS = (frozenset(("Venus", "Mars")),)     # the sources disagree on this table cell (REL-20)
_LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mulank_registry.json")
_KEY = re.compile(r"^((M|B|PM|PG|CB|LK|Y)[1-9]|PS:[1-9]-[1-9]|R:[A-Z][a-z]+>[A-Z][a-z]+)$")


@dataclass(frozen=True)
class Entry:
    status: str = PENDING
    reviewed_by: str = ""        # external expert (status verified)
    reviewed_on: str = ""
    source_ids: tuple = ()
    approved_by: str = ""        # business owner (status owner_approved)
    approved_on: str = ""
    editor: str = ""             # internal editorial reviewer (status owner_approved)


def load_ledger(path: str = _LEDGER) -> dict:
    """Read the approval ledger. Strict: an unknown status or key shape is a hard error, never silently ignored."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    out = {}
    for key, e in (raw.get("entries") or {}).items():
        if not _KEY.match(key):
            raise ValueError(f"bad registry key: {key}")
        if e.get("status") not in STATUSES:
            raise ValueError(f"bad status for {key}: {e.get('status')}")
        fields = {k: e[k] for k in ("status", "reviewed_by", "reviewed_on", "approved_by", "approved_on", "editor") if k in e}
        out[key] = Entry(source_ids=tuple(e.get("source_ids", ())), **fields)
    return out


REGISTRY = load_ledger()


def _today():
    """Reference date for personal years; one place so tests can pin it."""
    from datetime import date
    return date.today()


has_text = mulank_bank.has_text          # tests may replace this; production never does


def is_expert_verified(entry) -> bool:
    return bool(entry and entry.status == VERIFIED and entry.reviewed_by.strip() and entry.reviewed_on.strip())


def is_owner_approved(entry) -> bool:
    return bool(entry and entry.status == OWNER_APPROVED and entry.editor.strip()
                and entry.approved_by.strip() and entry.approved_on.strip())


def is_approved(entry) -> bool:
    """The only test that lets content into a production report."""
    return is_expert_verified(entry) or is_owner_approved(entry)


is_verified = is_expert_verified         # kept for callers that mean strictly "expert verified"


def relation_keys(pm: str, pb: str) -> list:
    """Registry keys for the planetary-links box. Pairs sharing a planet, pairs involving Rahu or Ketu and the
    conflicted Venus/Mars pair show the approved line 4i ('published tables differ'), which needs no table cell."""
    if pm == pb or pm in NODES or pb in NODES or frozenset((pm, pb)) in REL_CONFLICTS:
        return []
    return [f"R:{pm}>{pb}", f"R:{pb}>{pm}"]


def required_keys(result: dict) -> list:
    """Every registry key the paid report needs for this computed result."""
    m, b = result["mulank"]["number"], result["bhagyank"]["number"]
    pair = f"{m}-{b}"
    py = result["personal_year"]
    keys = [f"M{m}", f"B{b}", f"PM{m}", f"PG{b}", f"CB{m}", f"LK{m}", f"LK{b}",
            f"Y{py['current']['number']}", f"Y{py['next']['number']}"]
    keys += relation_keys(result["mulank"]["planet"], result["bhagyank"]["planet"])
    return list(dict.fromkeys(keys))


def pair_readiness(day, month, year, today=None, registry=None) -> dict:
    """{eligible, reason_code, content_version, missing, pair_key, approved, complete, approval_basis}.

    `missing` is for the server-side gap log only; never send it to a client. `approved` and `complete` are
    reported separately so a gap can be told apart: reason_code is "content_incomplete" when drafted text is
    missing, "content_not_approved" when text exists but is not approved, "ok" when both hold.
    With an explicit `registry` (tests) completeness is reported but not enforced.
    Raises NumerologyInputError for an invalid DOB."""
    reg = REGISTRY if registry is None else registry
    today = today or _today()
    result = numerology.compute_mulank(day, month, year, today=today)
    keys = required_keys(result)
    unapproved = [k for k in keys if not is_approved(reg.get(k))]
    untexted = [k for k in keys if not has_text(k)]
    approved, complete = not unapproved, not untexted
    enforce_text = registry is None
    missing = unapproved + (["text:" + k for k in untexted] if enforce_text else [])
    missing = list(dict.fromkeys(missing))
    eligible = approved and (complete or not enforce_text)
    if eligible:
        reason = "ok"
    else:
        reason = "content_incomplete" if (enforce_text and not complete) else "content_not_approved"
    kinds = {("expert" if is_expert_verified(reg.get(k)) else "owner") for k in keys if is_approved(reg.get(k))}
    basis = None if not approved else ("mixed" if len(kinds) > 1 else next(iter(kinds)))
    return {"eligible": eligible, "reason_code": reason, "content_version": CONTENT_VERSION, "missing": missing,
            "pair_key": result["pair_key"], "approved": approved, "complete": complete, "approval_basis": basis}


_sale_cache = {}


def sale_open(registry=None, today=None) -> bool:
    """True if at least one customer (some birthday) could be sold a report today. Used by public pages so they
    never imply the complete report is available when nothing can be sold."""
    reg = REGISTRY if registry is None else registry
    today = today or _today()
    ck = (id(reg), len(reg), today)
    if ck not in _sale_cache:
        _sale_cache.clear()
        ok = False
        for month in range(1, 13):
            for day in range(1, 29):
                try:
                    if pair_readiness(day, month, 1990, today=today, registry=registry)["eligible"]:
                        ok = True
                        break
                except numerology.NumerologyInputError:
                    continue
            if ok:
                break
        _sale_cache[ck] = ok
    return _sale_cache[ck]


def any_verified(registry=None) -> bool:
    """True once any entry is approved (kept name; includes owner approval)."""
    reg = REGISTRY if registry is None else registry
    return any(is_approved(e) for e in reg.values())


def gap_log_line(readiness: dict) -> str:
    """One PII-free line for the content-gap log."""
    return "[mulank] ineligible pair=%s reason=%s missing=%s" % (
        readiness["pair_key"], readiness["reason_code"], ",".join(readiness["missing"]))
