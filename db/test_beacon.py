"""Unit test for the /api/event beacon's pure request-parsing (beacon.beacon_context
+ EventIn). Imports ONLY beacon.py — NOT api.py, which would load .env (the RDS
creds) and open a live DB connection at import. No DB is touched here; the DB write
path (events_v2.record_event) is covered by db/test_events_v2.py.

Run: python3 -m pytest db/test_beacon.py -v      (no DB password needed)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root, for `import beacon`
import beacon  # noqa: E402


class _FakeClient:
    def __init__(self, host):
        self.host = host


class _FakeRequest:
    """Minimal stand-in for a Starlette Request: dict cookies + lowercase-keyed
    headers + a .client with .host (matching what beacon_context reads)."""
    def __init__(self, cookies=None, headers=None, host="1.2.3.4"):
        self.cookies = cookies or {}
        self.headers = headers or {}
        self.client = _FakeClient(host) if host is not None else None


def test_mints_ids_and_parses_session_when_no_cookies():
    req = _FakeRequest(headers={"user-agent": "UA/1", "referer": "https://ref.example",
                                "x-forwarded-for": "9.9.9.9, 10.0.0.1"})
    vid, new_vid, vis, new_vis, sess = beacon.beacon_context(
        req, "/en/marriage?utm_source=fb&utm_medium=cpc&utm_campaign=diwali")
    assert new_vid and new_vis and vid and vis          # both ids freshly minted
    assert vid != vis                                    # visitor and visit are distinct
    assert sess["utm_source"] == "fb"
    assert sess["utm_medium"] == "cpc"
    assert sess["utm_campaign"] == "diwali"
    assert sess["ip"] == "9.9.9.9"                       # first XFF hop, not the load balancer
    assert sess["user_agent"] == "UA/1"
    assert sess["referrer"] == "https://ref.example"
    assert sess["landing_url"].startswith("/en/marriage")


def test_reuses_existing_cookies_and_parses_ga_and_fb_ids():
    req = _FakeRequest(cookies={"ax_vid": "V1", "ax_vis": "S1", "_ga": "GA1.1.111.222",
                                "_fbp": "fbpX", "_fbc": "fbcY", "ax_li_fat": "liZ"})
    vid, new_vid, vis, new_vis, sess = beacon.beacon_context(req, "/en/compatibility")
    assert (vid, vis) == ("V1", "S1")                    # existing cookies reused
    assert not new_vid and not new_vis                   # nothing minted -> no Set-Cookie
    assert sess["ga_client_id"] == "111.222"             # last two dot-parts of _ga
    assert sess["fbp"] == "fbpX" and sess["fbc"] == "fbcY" and sess["li_fat_id"] == "liZ"
    assert sess["ip"] == "1.2.3.4"                       # falls back to client.host with no XFF


def test_no_page_url_and_no_client_are_safe():
    req = _FakeRequest(host=None)                        # request.client is None
    vid, new_vid, vis, new_vis, sess = beacon.beacon_context(req, None)
    assert new_vid and new_vis                           # still mints ids
    assert sess["ip"] is None and sess["utm_source"] is None and sess["ga_client_id"] is None


def test_eventin_validates_and_ignores_extra_fields():
    e = beacon.EventIn(event="page_view", value_paise=49900, junk="ignored")
    assert e.event == "page_view" and e.value_paise == 49900
    assert not hasattr(e, "junk")                        # extra="ignore" drops unknown keys
    assert e.is_free_unlock is False                     # default holds
