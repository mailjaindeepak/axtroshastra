"""Geocoding ACCURACY guard — the city a user picks must resolve to the RIGHT
coordinates, OFFLINE, across every Indian state.

Why this exists: the chart's ascendant (lagna) depends on the exact longitude &
latitude, so a wrong city silently produces a wrong chart. The autosuggest
offers ~3.6k cities (geonamescache), but the server-side resolver used to know
only ~454 + a flaky network geocoder, then silently defaulted to Delhi — a
wrong-city chart with no warning. This suite pins that a spread of real cities
across all states/UTs resolves offline (never Delhi), within tolerance of the
authoritative GeoNames coordinates.

The external network geocoder is disabled here so we prove OFFLINE coverage and
CI never depends on Nominatim.
"""
import math
import unicodedata

import pytest

import gazetteer
import geocoding

DELHI = (28.61, 77.21)


def _norm(s):
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def _haversine(a, b):
    R = 6371.0
    (la1, lo1), (la2, lo2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = math.radians(la2 - la1), math.radians(lo2 - lo1)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


# At least one city per state / UT (capitals of the small NE states are
# deliberately included — they are absent from the 454-list, so they exercise
# the new geonames path and prove every state is covered).
CITIES = [
    "Srinagar", "Leh", "Shimla", "Amritsar", "Chandigarh", "Gurugram", "Dehradun",
    "Delhi", "Jaipur", "Lucknow", "Varanasi", "Patna", "Ranchi", "Kolkata",
    "Siliguri", "Gangtok", "Guwahati", "Itanagar", "Dimapur", "Imphal", "Aizawl",
    "Agartala", "Shillong", "Bhubaneswar", "Raipur", "Bhopal", "Indore",
    "Ahmedabad", "Rajkot", "Mumbai", "Nagpur", "Pune", "Panaji", "Bengaluru",
    "Mysuru", "Hyderabad", "Warangal", "Vijayawada", "Visakhapatnam", "Chennai",
    "Madurai", "Kochi", "Thiruvananthapuram", "Puducherry", "Port Blair",
]


@pytest.fixture(scope="module")
def offline():
    # No network, no prior geocache — prove the OFFLINE chain (cities_in -> geonames).
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    mp.setattr(geocoding, "_geocode_external", lambda place: None)
    mp.setattr(geocoding, "_cache_get", lambda key: None)
    yield
    mp.undo()


@pytest.mark.parametrize("city", CITIES)
def test_city_resolves_offline_and_is_not_delhi(city, offline):
    r = geocoding.resolve_detailed(city)
    assert r["resolved"] is True, f"{city} did not resolve (would be a Delhi chart)"
    assert r["source"] != "default_delhi", f"{city} silently fell back to Delhi"
    # Cross-check against the authoritative, alt-name-aware GeoNames coordinate.
    # (None only when the town is below GeoNames' 15k floor and came from our
    # curated cities_in list — resolved!=default is guarantee enough there.)
    g = gazetteer.coords_for_name(city)
    if g:
        dist = _haversine((r["lat"], r["lon"]), (g[0], g[1]))
        assert dist < 40, f"{city}: resolved {dist:.0f} km from GeoNames ({r['source']})"


def test_geonames_path_covers_cities_missing_from_454_list(offline):
    """The core fix: cities absent from cities_in resolve via the authoritative
    geonames set, not Delhi. (Before, with the network off, these were Delhi.)"""
    from cities_in import CITIES_IN
    proved = 0
    for city in ["Itanagar", "Gangtok", "Aizawl", "Karimnagar", "Nadiad"]:
        if city.lower() in CITIES_IN:
            continue
        r = geocoding.resolve_detailed(city)
        assert r["source"] == "geonames", f"{city} expected geonames, got {r['source']}"
        assert r["resolved"] is True
        proved += 1
    assert proved >= 3, "expected several non-454 cities to prove the geonames path"


def test_unknown_place_falls_back_to_delhi_flagged(offline):
    """A place we genuinely cannot resolve still yields a chart (never hard-fail)
    but is marked resolved=False so it is visible, not silently wrong."""
    r = geocoding.resolve_detailed("Zzxqwerty Nowhereville")
    assert r["resolved"] is False
    assert r["source"] == "default_delhi"


def test_coords_for_name_none_for_gibberish():
    assert gazetteer.coords_for_name("qwertzxcv123") is None
    assert gazetteer.coords_for_name("") is None
