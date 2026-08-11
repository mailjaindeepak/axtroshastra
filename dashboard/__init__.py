"""dashboard/ — self-contained admin dashboard plugin for the Axtroshastra app.

Mirrors the extensions.py plugin idiom: expose install(app, ctx) and let api.py
call it once. Adds a gated HTML shell at /admin plus JSON APIs under /api/admin/*.
Nothing here touches the core reports table's write paths; the only new storage
is dash_delivery (see store.py), and the whole surface is locked whenever
STATS_KEY is unset (valid_admin_key -> False).
"""
from . import routes


def install(app, ctx):
    """ctx keys: db, get_report, valid_admin_key, order_amount_paise."""
    routes.install(app, ctx)
