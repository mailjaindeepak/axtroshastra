"""Regression tests for the pyswisseph thread-local ayanamsa bug.

engine.py calls swe.set_sid_mode(SIDM_LAHIRI) once at import, on the main
thread. In pyswisseph 2.10 the sidereal mode is THREAD-LOCAL, so the worker
threads FastAPI/uvicorn use to serve requests previously fell back to the
default Fagan-Bradley ayanamsa (~0.88 deg off Lahiri) -- silently corrupting
every live chart and dasha. These tests fail if the engine ever stops
re-asserting Lahiri per computation.
"""
import concurrent.futures
from datetime import datetime

import engine

# 18 Mar 1984, 00:45 IST, New Delhi -> UTC 1984-03-17 19:15.
_UTC = datetime(1984, 3, 17, 19, 15)
_LAT, _LON = 28.61, 77.21
_LAHIRI_MOON = 159.16      # Fagan-Bradley (the bug) would give ~158.28


def _moon_lon():
    return engine.compute_chart(_UTC, _LAT, _LON)["grahas"]["Moon"].lon


def test_moon_identical_on_worker_thread():
    """compute_chart must give the same Lahiri Moon on a worker thread as on main."""
    main_lon = _moon_lon()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        worker_lon = ex.submit(_moon_lon).result()
    assert abs(main_lon - worker_lon) < 1e-6, (
        f"ayanamsa differs across threads: main={main_lon:.5f} worker={worker_lon:.5f} "
        "(sid_mode is thread-local; Lahiri must be re-asserted per computation)")
    assert abs(main_lon - _LAHIRI_MOON) < 0.05, f"expected Lahiri Moon ~{_LAHIRI_MOON}, got {main_lon:.5f}"


def test_kundli_endpoint_uses_lahiri(client):
    """End-to-end: the HTTP route (served on a worker thread) must use Lahiri.

    Chart chosen so Lahiri -> Anuradha but Fagan-Bradley -> Vishakha, giving a
    single discriminating field in the teaser.
    """
    body = {"name": "Ayanamsa Guard", "dob": "1990-04-13", "tob": "12:00",
            "time_quality": "T0", "place": "Delhi", "gender": "male"}
    r = client.post("/api/kundli", json=body)
    assert r.status_code == 200, r.text
    nak = r.json()["teaser"]["nakshatra"]
    assert nak == "Anuradha", (
        f"expected Lahiri nakshatra 'Anuradha', got {nak!r} "
        "(Fagan-Bradley fallback would give 'Vishakha')")
