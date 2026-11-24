"""Record the owner's approval of reviewed Mulank content in mulank_registry.json.

This is the owner's step, run AFTER reading the content (see docs/numerology-content-model.md). It writes names and a date into the
ledger; the change then goes through a normal reviewed PR. Nothing here approves content on its own: a name, an editor and a date are required.

    python tools/approve_mulank_content.py --editor "Name" --approved-by "Name" --date 2026-11-10 --keys M1 M2 PM1 Y1
    python tools/approve_mulank_content.py ... --all            # every key that has drafted text
    python tools/approve_mulank_content.py --status             # what is approved, what is not, which pairs are sellable

Keys with no drafted text are refused. Use --dry-run to see what would change.
"""
import argparse
import json
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import mulank_bank  # noqa: E402
import mulank_content as mc  # noqa: E402

LEDGER = os.path.join(ROOT, "mulank_registry.json")


def _load():
    with open(LEDGER, encoding="utf-8") as f:
        return json.load(f)


def _save(raw):
    with open(LEDGER, "w", encoding="utf-8", newline="\n") as f:
        json.dump(raw, f, indent=1, ensure_ascii=False)
        f.write("\n")


def status() -> int:
    reg = mc.load_ledger(LEDGER)
    approved = sorted(k for k, e in reg.items() if mc.is_approved(e))
    print(f"{len(approved)} of {len(reg)} keys approved")
    ready = [f"{m}-{b}" for m in range(1, 10) for b in range(1, 10)
             if all(k in reg and mc.is_approved(reg[k]) and mulank_bank.has_text(k) for k in _pair_keys(m, b))]
    print(f"combinations whose number blocks are approved (year blocks are checked separately): {len(ready)} of 81")
    return 0


def _pair_keys(m, b):
    return [f"M{m}", f"B{b}", f"PM{m}", f"PG{b}", f"CB{m}", f"LK{m}", f"LK{b}"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--editor")
    ap.add_argument("--approved-by")
    ap.add_argument("--date", default=None, help="approval date, YYYY-MM-DD (default: today)")
    ap.add_argument("--keys", nargs="*", default=[])
    ap.add_argument("--all", action="store_true", help="every ledger key that has drafted text")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args(argv)
    if a.status:
        return status()
    when = a.date or date.today().isoformat()
    if not (a.editor and a.editor.strip() and a.approved_by and a.approved_by.strip()):
        ap.error("--editor and --approved-by (real names) are required")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", when):
        ap.error("--date must be YYYY-MM-DD")
    raw = _load()
    entries = raw["entries"]
    keys = [k for k in entries if mulank_bank.has_text(k)] if a.all else a.keys
    if not keys:
        ap.error("give --keys or --all")
    unknown = [k for k in keys if k not in entries]
    notext = [k for k in keys if k in entries and not mulank_bank.has_text(k)]
    if unknown or notext:
        print("refused:", {"not in ledger": unknown, "no drafted text": notext})
        return 2
    for k in keys:
        entries[k] = {"status": mc.OWNER_APPROVED, "editor": a.editor.strip(), "approved_by": a.approved_by.strip(), "approved_on": when}
    if a.dry_run:
        print(f"would approve {len(keys)} keys")
        return 0
    _save(raw)
    mc.load_ledger(LEDGER)
    print(f"approved {len(keys)} keys as {a.approved_by.strip()} (editor {a.editor.strip()}) on {when}. Open a PR for review.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
