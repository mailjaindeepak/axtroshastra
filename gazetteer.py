"""
Offline city gazetteer for Axtroshastra — autosuggest + exact resolution.

Backed by the bundled `geonamescache` dataset (~32k cities, population > 15k, worldwide),
so there is NO external API, no key, no network at deploy. Each city carries real
lat/lon and an IANA timezone. Replaces open-text geocoding + the Delhi fallback.

Public API:
  suggest(q, limit=8)      -> ranked list of dicts (autosuggest)
  resolve(geonameid)       -> single city dict or None
  tz_offset_hours(iana, local_dt) -> float UTC offset AT that date (handles DST/historical)

Each city dict: {id, name, label, country, cc, lat, lon, tz, pop}
`label` is display-ready, e.g. "Hyderabad, India" (disambiguates cross-border duplicates).
"""
from datetime import datetime
import unicodedata

_CITIES = None          # loaded once
_BY_ID = None
_COUNTRY = None


def _ascii(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c)).lower().strip()


def _load():
    global _CITIES, _BY_ID, _COUNTRY
    if _CITIES is not None:
        return
    from geonamescache import GeonamesCache
    gc = GeonamesCache()
    _COUNTRY = {c["iso"]: c["name"] for c in gc.get_countries().values()}
    rows = []
    for c in gc.get_cities().values():
        name = c["name"]
        cc = c.get("countrycode", "")
        if cc != "IN":            # India-only for now: hide foreign cities (avoids confusion)
            continue
        # keep only ascii/latin alternate names (user types Roman script)
        alts = set()
        for a in c.get("alternatenames", []) or []:
            aa = _ascii(a)
            if aa and all(ch.isalpha() or ch in " .-" for ch in aa):
                alts.add(aa)
        rows.append({
            "id": c["geonameid"], "name": name, "name_l": _ascii(name),
            "alts": alts, "cc": cc, "country": _COUNTRY.get(cc, cc),
            "lat": round(float(c["latitude"]), 4), "lon": round(float(c["longitude"]), 4),
            "tz": c.get("timezone", ""), "pop": int(c.get("population", 0) or 0),
        })
    rows.sort(key=lambda r: -r["pop"])          # population-ranked for suggest priority
    _CITIES = rows
    _BY_ID = {r["id"]: r for r in rows}


def _public(r: dict) -> dict:
    return {"id": r["id"], "name": r["name"], "label": f"{r['name']}, {r['country']}",
            "country": r["country"], "cc": r["cc"], "lat": r["lat"], "lon": r["lon"],
            "tz": r["tz"], "pop": r["pop"]}


def suggest(q: str, limit: int = 8) -> list:
    """Ranked autosuggest. Prefix-on-name > prefix-on-altname > substring, then by population."""
    _load()
    qq = _ascii(q or "")
    if len(qq) < 2:
        return []
    pre_name, pre_alt, sub = [], [], []
    for r in _CITIES:                            # already population-sorted
        if r["name_l"].startswith(qq):
            pre_name.append(r)
        elif any(a.startswith(qq) for a in r["alts"]):
            pre_alt.append(r)
        elif qq in r["name_l"]:
            sub.append(r)
        if len(pre_name) >= limit and len(pre_alt) >= limit:
            break
    out, seen = [], set()
    for bucket in (pre_name, pre_alt, sub):
        for r in bucket:
            if r["id"] in seen:
                continue
            seen.add(r["id"]); out.append(_public(r))
            if len(out) >= limit:
                return out
    return out


def resolve(geonameid) -> dict | None:
    _load()
    r = _BY_ID.get(int(geonameid)) if geonameid is not None else None
    return _public(r) if r else None


def tz_offset_hours(iana: str, local_dt: datetime) -> float | None:
    """UTC offset (hours) for an IANA zone at a given LOCAL date — DST/historical aware."""
    if not iana:
        return None
    try:
        from zoneinfo import ZoneInfo
        off = local_dt.replace(tzinfo=ZoneInfo(iana)).utcoffset()
        return round(off.total_seconds() / 3600, 2) if off is not None else None
    except Exception:
        return None
