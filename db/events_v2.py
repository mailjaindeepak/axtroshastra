"""
events_v2.py — first-party analytics (Piece 4, backend): visitor -> visit_session
-> event. This is what the /api/event beacon calls; it replaces relying on GA4.

MySQL-native, no commit (caller owns the transaction). The three-level model:
  * visitors      — one row per anonymous browser (the visitor_id cookie), with
                    FIRST-TOUCH source (kept forever) and the link to a user once known.
  * visit_sessions — one browsing session; the session's source/device captured ONCE,
                    plus started_at/ended_at (=> session time) and page_count.
  * events        — each page view / funnel milestone.

record_event() lazily creates the visitor and the visit on the first event, so the
frontend just sends events. identify() stitches an anonymous visitor to a known
user and back-attributes their prior events.
"""
from datetime import datetime, timezone

import db_v2

VALID_EVENTS = {"page_view", "form_start", "generate_lead", "begin_checkout",
                "purchase", "payment_failed", "identify"}


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def ensure_visitor(conn, visitor_id, *, utm_source=None, utm_medium=None,
                   utm_campaign=None, landing_url=None, referrer=None) -> None:
    """First-touch insert (INSERT IGNORE keeps the first values), then bump last_seen."""
    now = _now()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT IGNORE INTO visitors(visitor_id, first_seen, last_seen, "
            "first_utm_source, first_utm_medium, first_utm_campaign, first_landing_url, "
            "first_referrer) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
            (visitor_id, now, now, utm_source, utm_medium, utm_campaign, landing_url, referrer))
        cur.execute("UPDATE visitors SET last_seen=%s WHERE visitor_id=%s", (now, visitor_id))


def ensure_visit(conn, visit_id, visitor_id, *, landing_url=None, referrer=None,
                 utm_source=None, utm_medium=None, utm_campaign=None, fbc=None,
                 fbp=None, li_fat_id=None, ga_client_id=None, user_agent=None,
                 ip=None) -> None:
    """Create the visit_session on first sight (source captured ONCE); else bump ended_at."""
    now = _now()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT IGNORE INTO visit_sessions(visit_id, visitor_id, started_at, ended_at, "
            "page_count, landing_url, referrer, utm_source, utm_medium, utm_campaign, fbc, "
            "fbp, li_fat_id, ga_client_id, user_agent, ip) "
            "VALUES(%s,%s,%s,%s,0,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (visit_id, visitor_id, now, now, landing_url, referrer, utm_source, utm_medium,
             utm_campaign, fbc, fbp, li_fat_id, ga_client_id, user_agent, ip))
        cur.execute("UPDATE visit_sessions SET ended_at=%s WHERE visit_id=%s", (now, visit_id))


def record_event(conn, *, visitor_id, event_name, visit_id=None, user_id=None,
                 report_id=None, product=None, page_url=None, sequence=None,
                 value_paise=None, currency=None, is_free_unlock=False,
                 session=None) -> int:
    """Log one event. `session` (dict) carries the session-level fields
    (utm_*/referrer/landing_url/fbc/fbp/li_fat_id/ga_client_id/user_agent/ip) used to
    lazily create the visitor + visit on the first event. Returns the event id."""
    if event_name not in VALID_EVENTS:
        raise ValueError(f"unknown event_name: {event_name!r}")
    s = session or {}
    ensure_visitor(conn, visitor_id, utm_source=s.get("utm_source"),
                   utm_medium=s.get("utm_medium"), utm_campaign=s.get("utm_campaign"),
                   landing_url=s.get("landing_url"), referrer=s.get("referrer"))
    if visit_id:
        ensure_visit(conn, visit_id, visitor_id, landing_url=s.get("landing_url"),
                     referrer=s.get("referrer"), utm_source=s.get("utm_source"),
                     utm_medium=s.get("utm_medium"), utm_campaign=s.get("utm_campaign"),
                     fbc=s.get("fbc"), fbp=s.get("fbp"), li_fat_id=s.get("li_fat_id"),
                     ga_client_id=s.get("ga_client_id"), user_agent=s.get("user_agent"),
                     ip=s.get("ip"))
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO events(visit_id, visitor_id, user_id, event_name, report_id, "
            "product, page_url, sequence, value_paise, currency, is_free_unlock) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (visit_id, visitor_id, user_id, event_name, report_id, product, page_url,
             sequence, value_paise, currency, 1 if is_free_unlock else 0))
        eid = cur.lastrowid
    if visit_id and event_name == "page_view":
        with conn.cursor() as cur:
            cur.execute("UPDATE visit_sessions SET page_count=page_count+1 WHERE visit_id=%s",
                        (visit_id,))
    return eid


def identify(conn, visitor_id, user_id) -> None:
    """Stitch an anonymous visitor to a known user: set the link on the visitor and
    its visits, and back-attribute all their prior events (where user_id was NULL)."""
    with conn.cursor() as cur:
        cur.execute("UPDATE visitors SET user_id=%s WHERE visitor_id=%s AND user_id IS NULL",
                    (user_id, visitor_id))
        cur.execute("UPDATE visit_sessions SET user_id=%s WHERE visitor_id=%s AND user_id IS NULL",
                    (user_id, visitor_id))
        cur.execute("UPDATE events SET user_id=%s WHERE visitor_id=%s AND user_id IS NULL",
                    (user_id, visitor_id))
