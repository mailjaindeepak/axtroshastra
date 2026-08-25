#!/usr/bin/env python3
"""Persistent per-celebrity image index — search once, reuse forever.

WHY THIS EXISTS
Every build agent was re-searching Wikimedia Commons from scratch for each page, and
throwing the results away when it finished. On 25 Aug 2026 nine agents were killed by a
session API limit; eight lost their transcripts, and with them every verified candidate
they had found — one had 106 licence-verified files across 35 events. All of it had to be
re-searched from zero.

This index makes photo research CUMULATIVE and CRASH-PROOF:
  - An agent checks the index BEFORE hitting any API. Anything already recorded is free.
  - It records every candidate the moment it is judged — accepted OR rejected, with the
    reason. Rejections are as valuable as acceptances: they stop the next agent walking
    into the same dead end (watermarked Hungama files, deleted Commons entries, two crops
    of one photograph).
  - It survives transcript loss, because it lives on disk.
  - It makes cross-page duplicate reuse visible: if a photo is already used on another
    celebrity's page, that is recorded too.

USAGE (CLI)
  python3 _image_index.py lookup <slug>              # everything known for a celebrity
  python3 _image_index.py usable <slug>              # only the accepted candidates
  python3 _image_index.py rejected <slug>            # dead ends, with reasons
  python3 _image_index.py add <slug> <json-file>     # append records (list or single obj)
  python3 _image_index.py stats                      # coverage across all celebrities

USAGE (from Python)
  from _image_index import lookup, add_candidate, mark_used
"""
import json
import os
import sys
from datetime import date

INDEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "image-index.json")

# A candidate record. Only `title` and `status` are strictly required; everything else is
# recorded when known, because a partial record still saves the next agent a search.
FIELDS = (
    "title",        # File:Something.jpg  (or the source's own identifier)
    "api",          # commons | openverse | flickr
    "url",          # direct file URL at the time of recording
    "licence",      # human-readable, e.g. "CC BY-SA 4.0", "GODL-India"
    "licence_id",   # numeric id where the API gives one (Flickr/Openverse)
    "licence_ok",   # bool: passes the §2.2 whitelist AND the NC/ND exclusions
    "width", "height",
    "event",        # what the photo actually shows / where it was taken
    "date",         # capture date if known (EXIF DateTimeOriginal or file description)
    "solo",         # bool: solo portrait vs group shot
    "identified_by",  # HOW the subject was confirmed — never trust a filename
    "status",       # accepted | rejected | used
    "reason",       # why rejected, or which slot it was used in
    "used_on",      # slug of the page that embedded it, if any
    "md5",          # of the downloaded bytes, to spot re-uploads under new names
)


# Agents write the status field by hand, and they do not all spell it the same way.
# Yogi Adityanath's build recorded 22 candidates as "accept"/"reject"; both readers below
# matched only the -ed forms, so every one of those decisions was invisible and the next
# agent would have re-searched all 22 from scratch — the exact waste this index exists to
# prevent. Normalise on read so a spelling slip can never silently hide a decision again.
_STATUS = {
    "accept": "accepted", "accepted": "accepted", "ok": "accepted", "keep": "accepted",
    "reject": "rejected", "rejected": "rejected", "no": "rejected", "drop": "rejected",
    "used": "used", "use": "used", "shipped": "used",
}


def norm_status(value):
    """Canonical status, or None if the record never recorded one."""
    if not value:
        return None
    return _STATUS.get(str(value).strip().lower(), str(value).strip().lower())


def _load():
    if not os.path.exists(INDEX):
        return {"celebrities": {}}
    with open(INDEX, encoding="utf-8") as fh:
        return json.load(fh)


def _save(data):
    tmp = INDEX + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, INDEX)          # atomic: a crash mid-write can't corrupt the index


def lookup(slug):
    """Everything known about one celebrity's photo search."""
    return _load()["celebrities"].get(slug, {"candidates": [], "last_searched": None})


def usable(slug):
    """Candidates that passed every gate — start here before searching anything."""
    return [c for c in lookup(slug)["candidates"]
            if norm_status(c.get("status")) in ("accepted", "used")
            and c.get("licence_ok") is not False]


def rejected(slug):
    """Known dead ends, so they are never re-investigated."""
    return [c for c in lookup(slug)["candidates"]
            if norm_status(c.get("status")) == "rejected"]


def add_candidate(slug, record):
    """Record ONE candidate the moment it is judged. Idempotent on `title`."""
    data = _load()
    entry = data["celebrities"].setdefault(slug, {"candidates": [], "last_searched": None})
    rec = {k: record.get(k) for k in FIELDS if k in record}
    for i, existing in enumerate(entry["candidates"]):
        if existing.get("title") == rec.get("title"):
            entry["candidates"][i] = {**existing, **rec}   # update, don't duplicate
            break
    else:
        entry["candidates"].append(rec)
    entry["last_searched"] = date.today().isoformat()
    _save(data)
    return rec


def mark_used(slug, title, used_on, slot):
    """Flag that a photo actually shipped, and on which page/slot."""
    data = _load()
    for c in data["celebrities"].get(slug, {}).get("candidates", []):
        if c.get("title") == title:
            c["status"] = "used"
            c["used_on"] = used_on
            c["reason"] = f"embedded in {slot}"
            _save(data)
            return True
    return False


def find_cross_page(title):
    """Is this exact file already embedded on some other celebrity's page?"""
    out = []
    for slug, entry in _load()["celebrities"].items():
        for c in entry["candidates"]:
            if c.get("title") == title and norm_status(c.get("status")) == "used":
                out.append((slug, c.get("used_on"), c.get("reason")))
    return out


def _cli():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    if cmd == "stats":
        data = _load()
        if not data["celebrities"]:
            print("index is empty")
            return 0
        print(f"{'celebrity':28}{'total':>7}{'usable':>8}{'rejected':>10}  last searched")
        for slug, e in sorted(data["celebrities"].items()):
            cs = e["candidates"]
            ok = len([c for c in cs if norm_status(c.get("status")) in ("accepted", "used")])
            no = len([c for c in cs if norm_status(c.get("status")) == "rejected"])
            print(f"{slug:28}{len(cs):>7}{ok:>8}{no:>10}  {e.get('last_searched')}")
        return 0
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    slug = sys.argv[2]
    if cmd == "lookup":
        print(json.dumps(lookup(slug), indent=2, ensure_ascii=False))
    elif cmd == "usable":
        print(json.dumps(usable(slug), indent=2, ensure_ascii=False))
    elif cmd == "rejected":
        for c in rejected(slug):
            print(f"  ✗ {c.get('title')}\n      {c.get('reason')}")
    elif cmd == "add":
        with open(sys.argv[3], encoding="utf-8") as fh:
            payload = json.load(fh)
        for rec in (payload if isinstance(payload, list) else [payload]):
            add_candidate(slug, rec)
        print(f"recorded {len(payload) if isinstance(payload, list) else 1} for {slug}")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
