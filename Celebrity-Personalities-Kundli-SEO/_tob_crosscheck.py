#!/usr/bin/env python3
"""Cross-check a celebrity's birth time across every source we hold, and measure what
the disagreement actually changes.

WHY THIS EXISTS
data.json's `tob` / `rodden` fields read as authoritative and are not. As of 25 Aug 2026,
FIVE of the six celebrities present in both data.json and tests/celebrity_charts.json carry
CONTRADICTORY birth times — including two labelled "Rodden A", which §1.3 would otherwise
read as licence to publish house-based claims:

    Amitabh Bachchan   data.json 03:30 (DD)  vs  fixture 16:00 ("Accurate")  -> 12.5h apart
    Shah Rukh Khan     data.json 06:25 (A)   vs  fixture 02:30 ("Reference")
    Salman Khan        data.json 10:45 (A)   vs  fixture 14:30 ("Accurate")
    Sachin Tendulkar   data.json 13:00 (A)   vs  fixture 14:25 ("Reference")
    Virat Kohli        data.json None  (DD)  vs  fixture 10:28 ("Dirty")

Two build agents independently caught this the hard way (Sachin, then Salman) and each
nearly shipped a page asserting a birth time the repo itself contradicts. Run this FIRST,
before writing a word, so the third one doesn't have to rediscover it.

WHAT IT REPORTS
  - every birth time we hold for the subject, and where it came from
  - which planet SIGNS are stable across all of them (safe to publish)
  - whether the Moon's NAKSHATRA flips (if it does, the whole Vimshottari dasha LORD
    SEQUENCE changes, not just the dates — §1.2's SRK model applies and no dasha order
    may be published)
  - whether the LAGNA moves (it almost always does; §1.3 then forbids house claims)

USAGE
    python3 _tob_crosscheck.py "Salman Khan"
    python3 _tob_crosscheck.py --all        # every celebrity in both files
"""
import json
import os
import sys
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data.json")
FIXTURE = os.path.join(HERE, "..", "axtroshastra", "tests", "celebrity_charts.json")
ENGINE_DIR = os.path.join(HERE, "..", "axtroshastra")

BODIES = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu"]


def _engine():
    if ENGINE_DIR not in sys.path:
        sys.path.insert(0, ENGINE_DIR)
    import engine
    return engine


def sources_for(name):
    """Every birth time we hold, with provenance."""
    out = []
    for r in json.load(open(DATA, encoding="utf-8")):
        if r["name"].lower() == name.lower():
            if r.get("tob"):
                out.append({"tob": r["tob"], "src": "data.json",
                            "rating": f"Rodden {r.get('rodden')}",
                            "note": r.get("tob_status", "")})
            meta = r
            break
    else:
        return None, []
    try:
        for c in json.load(open(FIXTURE, encoding="utf-8")):
            if c["name"].lower() == name.lower() and c.get("tob"):
                out.append({"tob": c["tob"], "src": "tests/celebrity_charts.json",
                            "rating": c.get("rating", "?"), "note": c.get("source", "")})
    except FileNotFoundError:
        pass
    return meta, out


def compare(name, lat=None, lon=None, tz=5.5):
    engine = _engine()
    SIG = getattr(engine, "SIGNS_EN", None) or engine.SIGNS
    NAK = getattr(engine, "NAKSHATRAS_EN", None) or engine.NAKSHATRAS
    meta, srcs = sources_for(name)
    if meta is None:
        print(f"'{name}' not found in data.json")
        return 2
    if len(srcs) < 2:
        print(f"{name}: only {len(srcs)} birth time on record — nothing to cross-check.")
        print("  (That does NOT mean it is verified. Still run the §1.2 day sweep.)")
        return 0

    # Coordinates: caller supplies them; we do not guess from a place string.
    if lat is None or lon is None:
        print(f"{name}: pass --lat/--lon (from data.json pob: {meta.get('pob')})")
        return 2

    print(f"\n{name} — {len(srcs)} birth times on record")
    for s in srcs:
        print(f"   {s['tob']:>6}  {s['src']:32} {s['rating']:16} {s['note'][:44]}")

    charts = {}
    for s in srcs:
        hh, mm = (int(x) for x in s["tob"].split(":")[:2])
        r = engine.compute_chart(datetime(*[int(x) for x in meta["dob"].split("-")], hh, mm)
                                 - timedelta(hours=tz), lat, lon)
        g = r["grahas"]
        charts[s["tob"]] = {"signs": {b: SIG[g[b].sign] for b in BODIES},
                            "moon_nak": NAK[g["Moon"].nak],
                            "lagna": r["lagna_sign"]}

    keys = list(charts)
    moved = [b for b in BODIES
             if len({charts[k]["signs"][b] for k in keys}) > 1]
    naks = {charts[k]["moon_nak"] for k in keys}
    lagnas = {charts[k]["lagna"] for k in keys}

    print(f"\n   signs differing across times : {moved or 'NONE — all 9 stable, safe to publish'}")
    print(f"   Moon nakshatra               : {sorted(naks)}"
          + ("   ** FLIPS — dasha LORD SEQUENCE changes; publish NO dasha order (§1.2 SRK model) **"
             if len(naks) > 1 else "   (stable — dasha ORDER is fixed, but dates still are not)"))
    print(f"   lagna                        : {sorted(lagnas)}"
          + ("   ** moves — NO house/lagna/manglik claims (§1.3) **" if len(lagnas) > 1 else ""))
    print("\n   VERDICT: the sources DISAGREE, so this is a disputed-TOB build regardless of "
          "what data.json's rodden field says.\n")
    return 0


def _cli():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    lat = lon = None
    if "--lat" in args:
        lat = float(args[args.index("--lat") + 1])
    if "--lon" in args:
        lon = float(args[args.index("--lon") + 1])
    if args[0] == "--all":
        seo = {r["name"] for r in json.load(open(DATA, encoding="utf-8"))}
        try:
            fx = {c["name"] for c in json.load(open(FIXTURE, encoding="utf-8"))}
        except FileNotFoundError:
            fx = set()
        both = sorted(seo & fx)
        print(f"{len(both)} celebrities appear in BOTH files — each needs a cross-check:")
        for n in both:
            _, s = sources_for(n)
            times = {x["tob"] for x in s}
            flag = "  ** CONTRADICTION **" if len(times) > 1 else "  consistent"
            print(f"   {n:28}{sorted(times)}{flag}")
        return 0
    return compare(args[0], lat, lon)


if __name__ == "__main__":
    sys.exit(_cli())
