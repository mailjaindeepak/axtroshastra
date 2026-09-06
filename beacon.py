"""beacon.py — request-parsing for the /api/event first-party analytics beacon.

Kept OUT of api.py on purpose: this module imports with NO side effects (it does
not load .env / RDS creds and does not open a DB connection the way importing
api.py does), so the logic below can be unit-tested in isolation. The actual
route + DB write live in api.py; this is only the pure derivation.
"""
import secrets
import urllib.parse

from pydantic import BaseModel


class EventIn(BaseModel):
    """Beacon request body. `extra="ignore"` so a future frontend field can be
    added without breaking older served pages."""
    model_config = {"extra": "ignore"}
    event: str
    page_url: str | None = None
    product: str | None = None
    report_id: str | None = None
    value_paise: int | None = None
    currency: str | None = None
    is_free_unlock: bool = False
    sequence: int | None = None


def beacon_context(request, page_url: str | None):
    """Derive (visitor_id, is_new_vid, visit_id, is_new_vis, session dict) from the
    request cookies + headers. Pure — no DB, no env. `request` is any object with
    `.cookies` (dict-like), `.headers` (dict-like, lowercase keys), and `.client`
    (with `.host`, or None). The visit id is a browser-close session cookie (see the
    ponytail note in api.py where it's set)."""
    vid = request.cookies.get("ax_vid")
    is_new_vid = not vid
    if is_new_vid:
        vid = secrets.token_urlsafe(16)
    vis = request.cookies.get("ax_vis")
    is_new_vis = not vis
    if is_new_vis:
        vis = secrets.token_urlsafe(16)

    utm_source = utm_medium = utm_campaign = None
    try:
        if page_url:
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(page_url).query)
            utm_source = (qs.get("utm_source") or [None])[0]
            utm_medium = (qs.get("utm_medium") or [None])[0]
            utm_campaign = (qs.get("utm_campaign") or [None])[0]
    except Exception:
        pass

    # GA client id from the _ga cookie: "GA1.1.<a>.<b>" -> "<a>.<b>".
    ga_client_id = None
    try:
        ga = request.cookies.get("_ga")
        if ga:
            parts = ga.split(".")
            if len(parts) >= 4:
                ga_client_id = ".".join(parts[-2:])
    except Exception:
        pass

    xff = request.headers.get("x-forwarded-for")
    ip = xff.split(",")[0].strip() if xff else (request.client.host if request.client else None)

    session = {
        "user_agent": request.headers.get("user-agent"),
        "ip": ip,
        "referrer": request.headers.get("referer"),
        "landing_url": page_url,
        "utm_source": utm_source, "utm_medium": utm_medium, "utm_campaign": utm_campaign,
        "ga_client_id": ga_client_id,
        "fbc": request.cookies.get("_fbc"),
        "fbp": request.cookies.get("_fbp"),
        "li_fat_id": request.cookies.get("ax_li_fat"),
    }
    return vid, is_new_vid, vis, is_new_vis, session
