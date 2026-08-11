"""dashboard/money.py — wallet runway/sustain-date logic + low-balance alerting.

One place that turns the config wallets (plus the LIVE Twilio balance) into the
enriched view the dashboard renders AND the ops watcher alerts on:

  * runway_days  — for Twilio, live balance ÷ est burn (capped); else the config
                   estimate. None when the balance is unknown.
  * sustain_date — the calendar date the balance runs out ("~14 Feb 2027"),
                   computed from an injected `today` (never a hardcoded date).
  * state        — "crit" (<= CRITICAL_DAYS), "warn" (<= WARN_DAYS), else the
                   wallet's own state.
  * auto/live    — Twilio auto-updates its balance; the rest are manual top-ups.

`check_low_balances(send_alert, ...)` is what the ops watcher calls on its 3×/day
schedule. It NEVER raises, skips wallets whose balance is unknown, and only sends
one alert per run (critical if any wallet is critical, else a warning).
"""
import re
from datetime import date, datetime, timedelta

from . import config as _cfg
from . import providers

_MAX_RUNWAY_DAYS = 3650   # cap absurd "balance ÷ tiny burn" results at ~10 years


def _to_date(today=None):
    if isinstance(today, date):
        return today
    if today:
        try:
            return date.fromisoformat(str(today)[:10])
        except ValueError:
            pass
    return datetime.utcnow().date()


def sustain_date(runway_days, today=None):
    """Calendar date the balance runs out, e.g. '~14 Feb 2027'. None if unknown."""
    if runway_days is None:
        return None
    d = _to_date(today) + timedelta(days=int(runway_days))
    return "~%d %s" % (d.day, d.strftime("%b %Y"))


def _amount(text):
    """Parse '$19.98' / '₹1,000' -> float; None if not numeric."""
    try:
        cleaned = re.sub(r"[^0-9.\-]", "", str(text))
        return float(cleaned) if cleaned not in ("", "-", ".") else None
    except (TypeError, ValueError):
        return None


def _twilio_runway_days(wallet, twilio):
    """Twilio: live balance ÷ est monthly burn (capped); else config estimate."""
    if twilio and twilio.get("live"):
        bal = _amount(twilio.get("balance"))
        burn_mo = wallet.get("est_monthly_burn_usd")
        if bal is not None and burn_mo:
            per_day = float(burn_mo) / 30.0
            if per_day > 0:
                return max(0, min(int(bal / per_day), _MAX_RUNWAY_DAYS))
    return wallet.get("runway_days")


def wallet_states(today=None, twilio="auto"):
    """Enriched wallet dicts for the dashboard + alerts. `twilio="auto"` fetches
    the live balance (cached ~10 min, never raises); pass a dict or None to
    override (used by tests)."""
    if twilio == "auto":
        twilio = providers.twilio_balance()
    out = []
    for w in _cfg.CONFIG.get("wallets", []):
        is_twilio = (w.get("name") == "Twilio")
        live = bool(is_twilio and twilio and twilio.get("live"))
        balance = twilio.get("balance") if live else w.get("balance")
        runway = _twilio_runway_days(w, twilio) if is_twilio else w.get("runway_days")
        unknown = runway is None
        # State is driven by the runway thresholds (not a stale manual flag): a
        # balance with months of runway must read healthy, not "top up soon".
        if unknown:
            state = "warn"
        elif runway <= _cfg.CRITICAL_DAYS:
            state = "crit"
        elif runway <= _cfg.WARN_DAYS:
            state = "warn"
        else:
            state = "ok"
        out.append({
            "name": w["name"],
            "balance": balance,
            "runway_days": runway,
            "sustain_date": sustain_date(runway, today),
            "state": state,
            "live": live,
            "auto": bool(w.get("auto")),   # Twilio auto-updates; others manual
            "unknown": unknown,
            "note": w.get("note", ""),
            "console": w.get("console", ""),
        })
    return out


def check_low_balances(send_alert, today=None, twilio="auto"):
    """Ops-watcher hook: alert when any wallet's runway is low.

    Sends exactly ONE alert per run — "critical" if any wallet is at/below
    CRITICAL_DAYS, else "warning" if any is at/below WARN_DAYS. Wallets whose
    balance is unknown (e.g. Twilio unreachable) are skipped, never alerted on.
    `send_alert(subject, body, severity)` is injected (ops.alerts.send_alert) so
    this module never imports ops. Never raises.
    """
    try:
        states = wallet_states(today=today, twilio=twilio)
    except Exception:
        return {"checked": 0, "alerted": None}

    known = [s for s in states if not s["unknown"]]
    crit = [s for s in known if s["runway_days"] <= _cfg.CRITICAL_DAYS]
    warn = [s for s in known
            if _cfg.CRITICAL_DAYS < s["runway_days"] <= _cfg.WARN_DAYS]

    if crit:
        severity, group = "critical", crit
    elif warn:
        severity, group = "warning", warn
    else:
        return {"checked": len(states), "alerted": None}

    lines = ["- %s: %s left · runs out %s (~%s days)" % (
                 s["name"], s["balance"], s["sustain_date"], s["runway_days"])
             for s in group]
    subject = "Low balance: " + ", ".join(s["name"] for s in group)
    body = ("These prepaid balances are running low:\n\n" + "\n".join(lines) +
            "\n\nTop up in the provider console, then refresh the saved balance "
            "on the admin dashboard (Money & Feasibility).")
    try:
        send_alert(subject, body, severity)
    except Exception:
        pass   # alerts.send_alert already never-raises; stay defensive
    return {"checked": len(states), "alerted": severity, "accounts": [s["name"] for s in group]}
