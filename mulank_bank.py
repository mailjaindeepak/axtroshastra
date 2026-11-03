"""Mulank content bank: the approved wording rows and the drafted banks, loaded from mulank_bank.json.

This module holds TEXT only. Whether a piece of text may be shown to a customer is decided by
mulank_content.REGISTRY (status, named reviewer, review date). Having text here never makes anything
eligible: a pair is sellable only when every key is verified AND its text exists here.
"""
import json
import os

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mulank_bank.json")
with open(_PATH, encoding="utf-8") as _f:
    BANK = json.load(_f)

ROWS = BANK["rows"]
M = {int(k): v for k, v in BANK["M"].items()}
B = {int(k): v for k, v in BANK["B"].items()}
Y = {int(k): v for k, v in BANK["Y"].items()}
PS, PB, CMP, LK, REL = BANK["PS"], BANK["PB"], BANK["CMP"], BANK["LK"], BANK["REL"]


def row(row_id: str) -> str:
    return ROWS[row_id]


def has_text(key: str) -> bool:
    """True if drafted text exists for a registry key (M2, B1, Y1, PS:2-1, PB:2-1, CMP:2-1, LK:2-1, R:Moon>Sun)."""
    try:
        if key[0] == "M" and key[1:].isdigit():
            return int(key[1:]) in M
        if key[0] == "B" and key[1:].isdigit():
            return int(key[1:]) in B
        if key[0] == "Y" and key[1:].isdigit():
            return int(key[1:]) in Y
        kind, _, rest = key.partition(":")
        table = {"PS": PS, "PB": PB, "CMP": CMP, "LK": LK, "R": REL}.get(kind)
        return table is not None and rest in table
    except (IndexError, ValueError):
        return False
