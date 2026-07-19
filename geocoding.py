"""
Accurate geocoding with a persistent cache. (#1)

Resolution order for a place string:
  1. in-memory CITY_CACHE (hot Indian metros)
  2. CITIES_IN (auto-generated top-cities dict)
  3. persistent SQLite `geocache` table (previously resolved places)
  4. external provider (Nominatim by default, or Google if GEOCODER=google + key),
     result written back to the cache
  5. Delhi fallback (previous behaviour) so the app never fails to produce a chart

Timezone: India observes no DST, so IST (+5.5) is correct for the whole country and
is the default. For non-Indian coordinates, if `timezonefinder` + `zoneinfo` are
installed, the real offset is computed; otherwise +5.5 is returned.

Env:
  GEOCODER              "nominatim" (default) | "google" | "off"
  GOOGLE_GEOCODING_KEY  API key when GEOCODER=google
  GEOCODER_USER_AGENT   contact string required by the Nominatim usage policy
  DB_PATH               shared SQLite path (same DB the app uses)
"""
import json
import os
import sqlite3
import dbcompat
import threading
import urllib.parse
import urllib.request
from datetime import datetime

from cities_in import CITIES_IN

DELHI = (28.61, 77.21, 5.5)

CITY_CACHE = {
    "delhi": (28.61, 77.21, 5.5),      "new delhi": (28.61, 77.21, 5.5),
    "mumbai": (19.08, 72.88, 5.5),     "bangalore": (12.97, 77.59, 5.5),
    "bengaluru": (12.97, 77.59, 5.5),  "hyderabad": (17.38, 78.49, 5.5),
    "chennai": (13.08, 80.27, 5.5),    "kolkata": (22.57, 88.36, 5.5),
    "pune": (18.52, 73.86, 5.5),       "jaipur": (26.91, 75.79, 5.5),
    "lucknow": (26.85, 80.95, 5.5),    "ahmedabad": (23.02, 72.57, 5.5),
}

_BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DB_PATH", os.path.join(_BASE, "data", "reports.db"))
_lock = threading.Lock()


def _db():
    conn = dbcompat.connect()
    conn.execute("""CREATE TABLE IF NOT EXISTS geocache(
        place TEXT PRIMARY KEY, lat REAL, lon REAL, tz REAL,
        source TEXT, created_at TEXT)""")
    return conn


def _cache_get(key):
    with _db() as c:
        row = c.execute("SELECT lat,lon,tz FROM geocache WHERE place=?", (key,)).fetchone()
    return tuple(row) if row else None


def _cache_put(key, lat, lon, tz, source):
    with _lock, _db() as c:
        c.execute("INSERT OR REPLACE INTO geocache(place,lat,lon,tz,source,created_at)"
                  " VALUES(?,?,?,?,?,?)",
                  (key, lat, lon, tz, source, datetime.utcnow().isoformat()))


def _tz_for(lat, lon):
    """IST for India (no DST). Try timezonefinder elsewhere; fall back to +5.5."""
    if 6.0 <= lat <= 37.5 and 68.0 <= lon <= 97.5:
        return 5.5
    try:  # optional dependency; only used for non-Indian coordinates
        from timezonefinder import TimezoneFinder
        from zoneinfo import ZoneInfo
        tzname = TimezoneFinder().timezone_at(lat=lat, lng=lon)
        if tzname:
            off = datetime.now(ZoneInfo(tzname)).utcoffset()
            if off is not None:
                return off.total_seconds() / 3600.0
    except Exception:
        pass
    return 5.5


def _geocode_external(place):
    provider = os.getenv("GEOCODER", "nominatim").lower()
    if provider == "off":
        return None
    try:
        if provider == "google":
            key = os.getenv("GOOGLE_GEOCODING_KEY", "")
            if not key:
                return None
            url = ("https://maps.googleapis.com/maps/api/geocode/json?"
                   + urllib.parse.urlencode({"address": place, "key": key}))
            with urllib.request.urlopen(url, timeout=6) as r:
                data = json.load(r)
            if data.get("status") == "OK":
                loc = data["results"][0]["geometry"]["location"]
                return float(loc["lat"]), float(loc["lng"]), "google"
            return None
        # default: Nominatim (OpenStreetMap)
        ua = os.getenv("GEOCODER_USER_AGENT", "axtroshastra/1.0 (contact: axtroshastra@gmail.com)")
        url = ("https://nominatim.openstreetmap.org/search?"
               + urllib.parse.urlencode({"q": place, "format": "json", "limit": 1}))
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        with urllib.request.urlopen(req, timeout=6) as r:
            data = json.load(r)
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"]), "nominatim"
    except Exception:
        return None
    return None


def resolve_detailed(place: str) -> dict:
    """Resolve a place to coordinates with provenance.

    Returns {"lat","lon","tz","source","resolved"}.
      resolved=True  -> we found the actual place (cache/list/geocoder).
      resolved=False -> nothing matched; caller is using the Delhi fallback and the
                        ascendant/lagna (and everything derived from it) may be
                        wrong. Longitude, not just latitude, shifts the lagna, so a
                        wrong city can flip the lagna sign for ~1 in 6 births.
    Never raises.
    """
    key = (place or "").lower().split(",")[0].strip()
    if not key:
        return {"lat": DELHI[0], "lon": DELHI[1], "tz": DELHI[2],
                "source": "default_delhi", "resolved": False}
    if key in CITY_CACHE:
        la, lo, tz = CITY_CACHE[key]
        return {"lat": la, "lon": lo, "tz": tz, "source": "city_cache", "resolved": True}
    if key in CITIES_IN:
        la, lo, tz = CITIES_IN[key]
        return {"lat": la, "lon": lo, "tz": tz, "source": "cities_in", "resolved": True}
    cached = _cache_get(key)
    if cached:
        la, lo, tz = cached
        return {"lat": la, "lon": lo, "tz": tz, "source": "geocache", "resolved": True}
    ext = _geocode_external(place)
    if ext:
        lat, lon, source = ext
        tz = _tz_for(lat, lon)
        _cache_put(key, lat, lon, tz, source)
        return {"lat": lat, "lon": lon, "tz": tz, "source": source, "resolved": True}
    return {"lat": DELHI[0], "lon": DELHI[1], "tz": DELHI[2],
            "source": "default_delhi", "resolved": False}


def resolve(place: str):
    """Return (lat, lon, tz_offset_hours). Never raises; falls back to Delhi.

    Thin back-compat wrapper over resolve_detailed(); use resolve_detailed() when
    you need to know whether the place actually resolved (see accuracy note there).
    """
    d = resolve_detailed(place)
    return (d["lat"], d["lon"], d["tz"])


# Back-compat alias so api.py can `from geocoding import geocode`
geocode = resolve
