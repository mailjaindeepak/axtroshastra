"""dashboard/config.py — manually-maintained values for the dashboard tabs that
do NOT have a live data source wired yet.

Everything here is a PLACEHOLDER that a developer fills/updates by hand until the
corresponding provider API is connected. The dashboard renders the real card
structure and reads these numbers, so nothing is fabricated to *look* live — the
UI shows them plainly as manual figures. Wire each `// manual until API wired`
block to its real source and delete the note.

Tabs fed from here: Money & Feasibility (wallets/runway/investment), Traffic
(GA4), LLM (Claude credit), Ops (robots), AWS credits.

Live tabs (NOT from here): Overview triage, Delivery log, Customers — those come
straight from the `reports` + `dash_delivery` tables.
"""

# Base host used only to render human-readable links inside the ready-to-forward
# WhatsApp message. Report URLs served by the app are always the relative paths
# /report/{rid} and /report/{rid}.pdf; this is the display domain.
SITE_BASE = "https://axtroshastra.com"

# --- Revenue accounting ------------------------------------------------------
# Real revenue counts from the START OF TODAY onward. Everything before this
# instant was the TEAM verifying the Razorpay gateway (pre-launch test
# transactions) and must NOT count as real revenue or as a real customer needing
# manual delivery. ONGOING team/admin payments (any date) are excluded separately
# via the dash_team allowlist (see store.py team_* helpers) — matched by phone or
# email — so team members can keep test-buying after launch without polluting the
# numbers.
#   Stored as UTC because reports.created_at is UTC (datetime.utcnow()).
#   2026-08-07T18:30:00 UTC == 2026-08-08 00:00 IST  (i.e. "start of today").
# Edit this one line when the real go-live moment changes.
REVENUE_START = "2026-08-07T18:30:00"

# --- Low-balance alert thresholds (days of runway) ---------------------------
# The ops watcher (3×/day) alerts when a wallet's runway falls to/below these.
# CRITICAL fires a "critical" alert (and paints the Overview triage row red);
# WARN is the amber "act soon" band.
WARN_DAYS = 30
CRITICAL_DAYS = 14

CONFIG = {
    # ---- Money & Feasibility: wallet balances -------------------------------
    # These balances are REAL, read from the provider consoles on 08 Aug 2026
    # (manual until each usage API is wired) — hence dated. runway_days are
    # grounded estimates from current burn. Twilio's balance is LIVE via the
    # Twilio Balance API when reachable; its runway is live balance ÷ est burn.
    #   auto=True  -> balance updates itself (Twilio); no human refresh needed.
    #   auto absent/False -> MANUAL: a human tops up in the console AND refreshes
    #                        the saved balance here afterwards.
    "wallets": [
        {"name": "Twilio", "balance": "$19.98", "state": "ok", "auto": True,
         "note": "real 08 Aug · balance LIVE via Twilio Balance API when reachable",
         "runway_days": 900, "est_monthly_burn_usd": 0.02,
         "console": "https://console.twilio.com/us1/billing"},
        {"name": "Message Central", "balance": "₹1,000", "state": "ok",
         "note": "real 08 Aug · spend <₹5 so far (~₹0.30/OTP · ~20 OTP/mo)",
         "runway_days": 150,
         "console": "https://console.messagecentral.com/studio/credit"},
        {"name": "Claude / LLM", "balance": "$12.25", "state": "warn",
         "note": "real 08 Aug · $1.94 spent this cycle · resets Sep 1 · cap $2,000",
         "runway_days": 180,
         "console": "https://platform.claude.com/settings/billing"},
        {"name": "AWS credit", "balance": "$121.50", "state": "ok",
         "note": "real 08 Aug · $18.50 used of $140 · est $110.81 left",
         "runway_days": 1125,
         "console": "https://us-east-1.console.aws.amazon.com/costmanagement/home?region=us-east-1#/credits"},
    ],

    # ---- Money & Feasibility: your own money invested -----------------------
    # NOT SET — these are placeholders the founder must replace with the real
    # invested amount. Until then the UI shows an explicit "Not set" state; it
    # NEVER shows an invented figure.
    "investment": {
        "poured_in_usd": None, "used_usd": None, "left_usd": None,
        "poured_in_inr": None, "used_inr": None, "left_inr": None,
    },

    # ---- Overview: live visitors count --------------------------------------
    # NOT CONNECTED — needs GA4 realtime. Null until wired; the card shows "—".
    "on_site_now": None,

    # NOTE: `revenue_traffic_7d` was a fabricated Mon–Sun series and has been
    # REMOVED. The Overview "Revenue vs traffic (7 days)" chart now plots REAL
    # paid revenue per day from the reports DB (see /api/admin/overview
    # -> revenue_7d); the visitor overlay stays greyed until GA4 is connected.

    # ---- Traffic: GA4 / Clarity --------------------------------------------
    # NOT CONNECTED. All values null/empty so the tab shows an honest empty
    # state (no fabricated visitors, sources, or funnel).
    "traffic": {
        "visitors_now": None, "visitors_7d": None, "peak_today": None,
        "wow": None,
        "sources": [],
        "funnel": [],
        "connected": False,
        "note": "Traffic isn't connected yet — connect GA4 (and Microsoft "
                "Clarity) to see visitors, sources, and the funnel.",
        "ga4_url": "https://analytics.google.com/",
        "clarity_url": "https://clarity.microsoft.com/",
    },

    # ---- Traffic: Facebook Pixel / Meta ------------------------------------
    # NOT CONNECTED. Mirrors the GA4 "traffic" block above in the same honest
    # style — every event count is null and the 7-day series is empty until the
    # Meta Conversions/Marketing API is wired, so the UI shows an empty state
    # (no fabricated event counts or bars). `events` are the last-7-day totals
    # for the pixel events we actually fire on the funnel pages (PageView,
    # ViewContent, FormStart→Lead, InitiateCheckout, Purchase). `series_7d` is a
    # per-day breakdown: {day, PageView, Lead, InitiateCheckout, Purchase}.
    "facebook_pixel": {
        "connected": False,
        "pixel_id": "1498790608627206",   # the real site pixel
        "events": {"PageView": None, "ViewContent": None, "Lead": None,
                   "InitiateCheckout": None, "Purchase": None},  # last-7-day totals
        "series_7d": [],   # {day, PageView, Lead, InitiateCheckout, Purchase} — empty until wired (no fake bars)
        "note": "Facebook Pixel isn't connected yet — wire the Meta "
                "Conversions/Marketing API to see event counts and the events "
                "funnel.",
        "events_manager_url": "https://business.facebook.com/events_manager2/list/pixel/1498790608627206",
    },

    # ---- LLM: Claude credit + generation stats ------------------------------
    # manual until API wired (Anthropic usage/billing). `recent` is an optional
    # generation log — left empty on purpose (no live source; do NOT fabricate
    # per-call rows). Fill from the Anthropic usage export when wired.
    "llm": {
        # Kept in sync with the Claude wallet above (real 08 Aug 2026). `pct` is
        # the spend so far as a share of the cycle cap ($2,000) — deliberately
        # tiny, so the credit meter reads "barely used", not "almost empty".
        "credit_left": "$12.25", "spent_month": "$1.94", "pct": 1,
        "live_today": None, "fallbacks": None, "avg_gen_s": None, "slowest_s": None,
        "recent": [],
        "note": "manual — wire Anthropic usage API",
    },

    # ---- Ops: the three robots ---------------------------------------------
    # manual until API wired (UptimeRobot / GitHub Actions). History lists are
    # empty until the Actions/UptimeRobot APIs are wired (no fabricated runs).
    "ops": {
        "watcher": {"state": "ok", "last_ping": "manual"},
        "robot": {"state": "ok", "last_run": "manual", "next_run": "manual"},
        "mechanic": {"state": "warn", "live_version": "manual"},
        "run_history": [],       # {run, result, checks:[...]}
        "rollback_history": [],  # {when, event, from_to, why, alerted}
        "note": "manual — wire UptimeRobot + GitHub Actions",
    },

    # ---- Money & Feasibility: spend & revenue summary -----------------------
    # SPEND is an ESTIMATE (manual until provider invoices are wired) and is kept
    # small + consistent with the wallet notes above (Claude ~$1.94≈₹163, MC <₹5,
    # Twilio not yet billed). REVENUE + report COUNT are NOT read from here — the
    # dashboard pulls them LIVE from /api/admin/overview so Money always agrees
    # with Overview. `margin_pct` is likewise computed live (revenue vs spend).
    "spend_revenue": {
        "services_spend_inr": 168,   # estimated monthly total (Claude+MC+Twilio)
        # Current grounded per-provider estimate only — NO fabricated 6-month
        # history. Each is a single "~est/mo" figure; the trend builds once
        # provider invoices are wired.
        "by_service": [
            {"name": "Twilio", "note": "WhatsApp sends (not yet billed)", "this_month": 0},
            {"name": "Message Central", "note": "login OTPs", "this_month": 5},
            {"name": "Claude", "note": "report narratives", "this_month": 163},
        ],
        "history_note": "history builds once provider invoices are wired",
        "ledger": [],   # deposits & usage — empty until wired (no fabricated rows)
        "note": "estimated — wire provider invoices for exact figures",
    },
}
