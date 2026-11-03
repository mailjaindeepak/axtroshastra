"""Mulank content bank: the approved wording rows and the drafted per-number blocks, loaded from mulank_bank.json.

This module holds TEXT only. Whether a piece of text may be shown to a customer is decided by
mulank_content.REGISTRY / mulank_registry.json (status, named people, date). Having text here never makes anything
eligible: a pair is sellable only when every key is approved AND its text exists here.

Per-number model (the same approved 15-card layout, built from nine blocks per kind instead of 81 pair texts):
  M<n>   Mulank block (themes, work style, strengths ...)          cards 4, 8, 9
  B<n>   Bhagyank block                                              cards 4, 8, 9
  PM<n>  personality block for a Mulank (how you come across)       cards 5, 6, 7
  PG<n>  personality overlay for a Bhagyank (inner drive, direction) cards 5, 6, 7
  CB<n>  bonds block for a Mulank                                    card 10
  LK<n>  lucky references for a number's planet (table LP)          card 13
  Y<n>   personal-year block (table row and three prompts)           cards 11, 14
  PS:<m>-<b>  optional sourced pair statement (2-1 only)
  R:<Planet>><Planet>  planetary-links label
"""
import json
import os

import numerology

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mulank_bank.json")
with open(_PATH, encoding="utf-8") as _f:
    BANK = json.load(_f)

ROWS = BANK["rows"]
M = {int(k): v for k, v in BANK["M"].items()}
B = {int(k): v for k, v in BANK["B"].items()}
Y = {int(k): v for k, v in BANK["Y"].items()}
PM = {int(k): v for k, v in BANK["PM"].items()}
PG = {int(k): v for k, v in BANK["PG"].items()}
CB = {int(k): v for k, v in BANK["CB"].items()}
LP = BANK["LP"]
VERB = BANK["VERB"]
PS, REL = BANK["PS"], BANK["REL"]

_FULL_Y = ("theme", "pace", "often", "explore", "continue_", "reconsider")


def row(row_id: str) -> str:
    return ROWS[row_id]


def has_text(key: str) -> bool:
    """True if drafted text exists for a registry key."""
    try:
        if key[0] == "M" and key[1:].isdigit():
            return int(key[1:]) in M
        if key[0] == "B" and key[1:].isdigit():
            return int(key[1:]) in B
        if key[0] == "Y" and key[1:].isdigit():
            y = Y.get(int(key[1:]))
            return bool(y) and all(y.get(f) for f in _FULL_Y)     # all three prompts: any year can be current or next
        if key[:2] in ("PM", "PG", "CB", "LK") and key[2:].isdigit():
            n = int(key[2:])
            if key[:2] == "PM":
                return n in PM
            if key[:2] == "PG":
                return n in PG
            if key[:2] == "CB":
                return n in CB
            return numerology.PLANETS.get(n) in LP
        kind, _, rest = key.partition(":")
        table = {"PS": PS, "R": REL}.get(kind)
        return table is not None and rest in table
    except (IndexError, ValueError):
        return False
