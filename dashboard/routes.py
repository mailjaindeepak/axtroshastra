"""dashboard/routes.py — the admin dashboard plugin routes.

Registered onto the FastAPI app by dashboard.install(app, ctx). Serves a gated
HTML shell at /admin plus JSON APIs under /api/admin/*. Every admin route calls
ctx['valid_admin_key'](key) and returns 403 on failure; when STATS_KEY is unset
valid_admin_key() is always False, so the whole surface is locked by default.

ctx contract (from api.py):
  db(): connection factory (sqlite/mysql via dbcompat)
  get_report(rid) -> {payload,paid,order_id,phone,user_phone} | None
  valid_admin_key(key) -> bool
  order_amount_paise(rec) -> int   # price charged for a report, by variant
"""
import base64
import hashlib
import hmac
import html as _html
import json
import os
import re
import time
import urllib.parse
from datetime import datetime, timedelta

from fastapi import HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from . import money, providers, store
from .config import CONFIG, SITE_BASE, REVENUE_START, WARN_DAYS, CRITICAL_DAYS

_HERE = os.path.dirname(os.path.abspath(__file__))
_INDEX = os.path.join(_HERE, "static", "index.html")

# variant (payload.meta.variant) -> friendly product label
_PRODUCT_LABELS = {
    "/en/compatibility": "Compatibility",
    "/hi/compatibility": "Compatibility",
    "/milan": "Marriage (Milan)",
    "/match": "Compatibility (Match)",
    "/shaadi": "Marriage (Shaadi)",
    "/career": "Career",
    "/vidyarthi": "Career (Vidyarthi)",
    "/padhai": "Career (Padhai)",
    "direct": "Report",
}


def _variant(payload):
    return ((payload or {}).get("meta") or {}).get("variant") or "direct"


def _product_label(payload):
    v = _variant(payload)
    return _PRODUCT_LABELS.get(v, v.strip("/").replace("-", " ").title() or "Report")


def _display_name(payload):
    return ((payload or {}).get("name") or "").strip() or "there"


def _payload_email(payload):
    return ((payload or {}).get("meta") or {}).get("_email") or ""


def _mask_phone(mobile):
    """Reveal ONLY the last 2 digits (privacy-first). '+919876543211' ->
    '+91 •••••••• 11'. Never returns more than the trailing 2 digits."""
    digits = re.sub(r"\D", "", mobile or "")
    if len(digits) < 2:
        return "••"
    last2 = digits[-2:]
    if len(digits) > 10:                # has a country code prefix
        cc = digits[:len(digits) - 10]
        return "+" + cc + " •••••••• " + last2
    return "•••••••• " + last2


def _mc_configured():
    """True when Message Central creds are present (reuse auth.py's env names —
    never hardcode a secret)."""
    return bool(os.getenv("MESSAGECENTRAL_AUTH_TOKEN", "").strip()
                or os.getenv("MESSAGECENTRAL_CUSTOMER_ID", "").strip())


def _classify_exclusion(created_at, deliver_phone, pay_phone, email,
                        team_phones, team_emails, payment_id=""):
    """Why (if at all) this paid row is excluded from real revenue.
    Returns "pre-launch" | "team" | "pass" | "" (empty = a real customer)."""
    if (payment_id or "").startswith("free_pass:") or payment_id == "demo":
        return "pass"
    if (created_at or "") < REVENUE_START:
        return "pre-launch"
    if store.norm_phone(deliver_phone) in team_phones or \
       store.norm_phone(pay_phone) in team_phones:
        return "team"
    if email and store.norm_email(email) in team_emails:
        return "team"
    return ""


def _team_label_map_from(team_data):
    """Build {normalized_value: label} from team_all() result."""
    labels = {}
    for p in team_data.get("phones", []):
        if p.get("label"):
            labels[p["value"]] = p["label"]
    for e in team_data.get("emails", []):
        if e.get("label"):
            labels[e["value"]] = e["label"]
    return labels


def _phone_tag(deliver_phone, pay_phone, team_labels, team_phones=None):
    """Return the team label for this phone, or '' if not a team member."""
    dp = store.norm_phone(deliver_phone)
    pp = store.norm_phone(pay_phone)
    tag = team_labels.get(dp) or team_labels.get(pp) or ""
    if not tag and team_phones:
        if dp in team_phones or pp in team_phones:
            tag = "team"
    return tag


def _forward_message(payload, rid, amount_inr):
    """A ready-to-paste WhatsApp message with the report links. Plain text so it
    pastes cleanly into WhatsApp support."""
    name = _display_name(payload)
    return (
        f"Namaste {name} \U0001f64f\n\n"
        f"Thank you for choosing Axtroshastra — your payment of ₹{amount_inr} "
        f"is confirmed. Apologies for the short delay in delivery on our side.\n\n"
        f"Here is your full report:\n"
        f"View online: {SITE_BASE}/report/{rid}\n"
        f"Download PDF: {SITE_BASE}/report/{rid}.pdf\n\n"
        f"If you have any questions about your report, just reply here — "
        f"we're happy to help. \U0001f31f\n— Team Axtroshastra"
    )


def install(app, ctx):
    db = ctx["db"]
    get_report = ctx["get_report"]
    valid_admin_key = ctx["valid_admin_key"]
    order_amount_paise = ctx["order_amount_paise"]

    # ---------------------------------------------------------------- admin auth
    # ENV (all optional; read here, never hardcoded):
    #   ADMIN_PATH  — dashboard URL slug. Default "admin" (keeps local/tests
    #                 working). Prod sets a long random slug e.g. "mgmt-7f3a9c2e"
    #                 so the real path is unguessable and "/admin" 404s.
    #   ADMIN_KEY   — the admin secret. When unset, falls back to STATS_KEY, so
    #                 qa-key still works locally/in tests. Constant-time compare.
    # The signed session cookie removes the key from the URL (no more ?key= in
    # browser history / logs); ?key= is kept only as a back-compat fallback.
    ADMIN_PATH = (os.getenv("ADMIN_PATH", "admin").strip() or "admin").strip("/")
    COOKIE_NAME = "admin_session"
    SESSION_TTL = 8 * 3600   # 8 hours

    def _admin_secret():
        """The secret used to SIGN cookies: ADMIN_KEY, else STATS_KEY (env)."""
        return os.getenv("ADMIN_KEY", "") or os.getenv("STATS_KEY", "")

    def _valid_admin_secret(key):
        """Constant-time check of a submitted key against ADMIN_KEY (if set),
        else against STATS_KEY via the app's own validator (which honours any
        api.STATS_KEY override in tests)."""
        admin_key = os.getenv("ADMIN_KEY", "")
        if admin_key:
            return hmac.compare_digest(key or "", admin_key)
        return valid_admin_key(key)

    def _b64(raw):
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    def _unb64(txt):
        return base64.urlsafe_b64decode(txt + "=" * (-len(txt) % 4))

    def _make_token():
        """Signed session token: base64(issued_at) . base64(hmac_sha256)."""
        secret = _admin_secret()
        payload = str(int(time.time())).encode()
        sig = hmac.new(secret.encode(), payload, hashlib.sha256).digest()
        return _b64(payload) + "." + _b64(sig)

    def _valid_cookie(request):
        """True only for an untampered, unexpired cookie signed with the current
        admin secret."""
        tok = request.cookies.get(COOKIE_NAME, "")
        secret = _admin_secret()
        if not tok or "." not in tok or not secret:
            return False
        try:
            p_b64, s_b64 = tok.split(".", 1)
            payload = _unb64(p_b64)
            sig = _unb64(s_b64)
        except Exception:
            return False
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return False
        try:
            issued = int(payload.decode())
        except Exception:
            return False
        now = int(time.time())
        return 0 <= (now - issued) < SESSION_TTL   # not expired, not future

    def _authed(request, key):
        # a valid signed cookie OR the back-compat ?key= both grant access
        return _valid_admin_secret(key) or _valid_cookie(request)

    def _gate(request, key):
        if not _authed(request, key):
            raise HTTPException(403, "forbidden")

    def _paid_rows():
        """All PAID reports, newest-first, joined with any manual delivery
        status. Returns a list of fully-shaped row dicts ready for the UI.

        A row is flagged is_test (excluded from real revenue) when:
        - it was unlocked with a free pass (payment_id starts with free_pass:)
        - it was paid before REVENUE_START (pre-launch gateway testing)
        - its phone/email is on the dash_team allowlist (team purchases)
        The team sets are loaded once here and tested in-memory."""
        statuses = store.all_statuses(db)
        team_phones, team_emails = store.team_sets(db)
        team_labels = _team_label_map_from(store.team_all(db))
        with db() as c:
            rows = c.execute(
                "SELECT id, created_at, payload, phone, user_phone, payment_id "
                "FROM reports WHERE paid=1 ORDER BY created_at DESC"
            ).fetchall()
        out = []
        for rid, created_at, payload_json, pay_phone, deliver_phone, payment_id in rows:
            try:
                payload = json.loads(payload_json) if payload_json else {}
            except (TypeError, ValueError):
                payload = {}
            amount_inr = order_amount_paise({"payload": payload}) // 100
            st = statuses.get(rid) or {}
            reason = _classify_exclusion(created_at, deliver_phone, pay_phone,
                                         _payload_email(payload),
                                         team_phones, team_emails,
                                         payment_id)
            tag = _phone_tag(deliver_phone, pay_phone, team_labels, team_phones)
            out.append({
                "rid": rid,
                "created_at": created_at or "",
                "product": _product_label(payload),
                "amount_inr": amount_inr,
                "is_test": bool(reason),
                "exclude_reason": reason,
                "payment_id": payment_id or "",
                "pay_phone": pay_phone or "",
                "deliver_phone": deliver_phone or "",
                "team_tag": tag,
                "status": st.get("status") or "pending",
                "note": st.get("note") or "",
                "report_url": f"/report/{rid}",
                "pdf_url": f"/report/{rid}.pdf",
                "forward_message": _forward_message(payload, rid, amount_inr),
            })
        return out

    # ---------------------------------------------------------------- HTML shell
    # Served under the (possibly secret) ADMIN_PATH slug only. With a valid cookie
    # (or ?key=) it returns the dashboard; otherwise a small POST login form.
    @app.get("/" + ADMIN_PATH, include_in_schema=False)
    def admin_shell(request: Request, key: str = ""):
        if not _authed(request, key):
            return HTMLResponse(_login_html(ADMIN_PATH))
        try:
            with open(_INDEX, "r", encoding="utf-8") as f:
                return HTMLResponse(f.read())
        except OSError as e:
            raise HTTPException(500, f"dashboard shell missing: {e}")

    @app.post("/" + ADMIN_PATH + "/login", include_in_schema=False)
    async def admin_login(request: Request):
        # Parse the urlencoded body ourselves (Starlette's request.form() would
        # pull in python-multipart, which we don't depend on). Field name "key".
        raw = (await request.body()).decode("utf-8", "ignore")
        key = (urllib.parse.parse_qs(raw).get("key") or [""])[0]
        if not _valid_admin_secret(key):
            return HTMLResponse(_login_html(ADMIN_PATH, error=True), status_code=401)
        # Only mark the cookie Secure over real HTTPS, so local/test http still
        # round-trips it (prod sits behind an HTTPS load balancer).
        is_https = (request.url.scheme == "https"
                    or os.getenv("PUBLIC_BASE_URL", "").startswith("https"))
        resp = RedirectResponse("/" + ADMIN_PATH, status_code=303)
        resp.set_cookie(COOKIE_NAME, _make_token(), max_age=SESSION_TTL,
                        httponly=True, secure=is_https, samesite="strict", path="/")
        return resp

    @app.get("/" + ADMIN_PATH + "/logout", include_in_schema=False)
    def admin_logout():
        resp = RedirectResponse("/" + ADMIN_PATH, status_code=303)
        resp.delete_cookie(COOKIE_NAME, path="/")
        return resp

    # ---------------------------------------------------------------- JSON APIs
    @app.get("/api/admin/overview")
    def admin_overview(request: Request, key: str = ""):
        _gate(request, key)
        rows = _paid_rows()
        real = [r for r in rows if not r["is_test"]]
        test = [r for r in rows if r["is_test"]]
        passes = [r for r in rows if r["exclude_reason"] == "pass"]
        team = [r for r in rows if r["exclude_reason"] == "team"]
        pending = sum(1 for r in real if r["status"] in ("pending", "failed"))
        revenue = sum(r["amount_inr"] for r in real)
        return {
            "totals": {
                "paid_count": len(real),
                "revenue_inr": revenue,
                "pending_count": pending,
                "test_count": len(test),
                "test_revenue_inr": sum(r["amount_inr"] for r in test),
                "pass_count": len(passes),
                "team_count": len(team),
                "revenue_start": REVENUE_START,
            },
            "revenue_7d": _revenue_7d(real),
            "reports": rows,
        }

    def _revenue_7d(real_rows):
        """REAL paid revenue per day for the last 7 calendar days (UTC), test
        payments already excluded. Days with no sales are 0 (not omitted) so the
        chart is honest. Visitors are NOT included — GA4 isn't connected."""
        today = datetime.utcnow().date()
        buckets = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
        by_day = {d.isoformat(): 0 for d in buckets}
        for r in real_rows:
            day = (r.get("created_at") or "")[:10]
            if day in by_day:
                by_day[day] += r["amount_inr"]
        return [{"date": d.isoformat(),
                 "day": d.strftime("%a"),
                 "paid_inr": by_day[d.isoformat()]} for d in buckets]

    @app.get("/api/admin/deliveries")
    def admin_deliveries(request: Request, key: str = ""):
        _gate(request, key)
        rows = _paid_rows()
        return {
            "deliveries": [{
                "pay_phone": r["pay_phone"],
                "deliver_phone": r["deliver_phone"],
                "rid": r["rid"],
                "product": r["product"],
                "status": r["status"],
                "created_at": r["created_at"],
                "is_test": r["is_test"],
                "exclude_reason": r["exclude_reason"],
                "payment_id": r["payment_id"],
                "team_tag": r["team_tag"],
                "forward_message": r["forward_message"],
                "report_url": r["report_url"],
                "pdf_url": r["pdf_url"],
            } for r in rows]
        }

    @app.get("/api/admin/customers")
    def admin_customers(request: Request, key: str = "", q: str = ""):
        """Three-category customer list:
        - customers: phone has ANY report with paid=1 (real paying user)
        - testers:   phone has reports but none with paid=1
        - developers: manually added to dash_team exclusion list
        Team-excluded phones are skipped from both customers and testers.
        """
        _gate(request, key)
        q = (q or "").strip()
        like = f"%{q}%"
        team_phones, team_emails = store.team_sets(db)
        team_data = store.team_all(db)
        team_labels = _team_label_map_from(team_data)
        with db() as c:
            if q:
                rows = c.execute(
                    "SELECT id, created_at, payload, phone, user_phone, paid, payment_id "
                    "FROM reports WHERE user_phone LIKE ? OR phone LIKE ? "
                    "ORDER BY created_at DESC",
                    (like, like),
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT id, created_at, payload, phone, user_phone, paid, payment_id "
                    "FROM reports WHERE "
                    "(user_phone IS NOT NULL AND user_phone <> '') "
                    "OR (phone IS NOT NULL AND phone <> '') "
                    "ORDER BY created_at DESC"
                ).fetchall()
        all_phones = {}
        for rid, created_at, payload_json, pay_phone, deliver_phone, paid, payment_id in rows:
            phone = (deliver_phone or pay_phone or "").strip()
            if not phone:
                continue
            try:
                payload = json.loads(payload_json) if payload_json else {}
            except (TypeError, ValueError):
                payload = {}
            dp = store.norm_phone(deliver_phone)
            pp = store.norm_phone(pay_phone)
            em = store.norm_email(_payload_email(payload))
            is_team = (dp in team_phones or pp in team_phones
                       or (em and em in team_emails))
            if is_team:
                continue
            tag = _phone_tag(deliver_phone, pay_phone, team_labels, team_phones)
            is_real_pay = (bool(paid)
                          and not ((payment_id or "").startswith("free_pass:") or payment_id == "demo")
                          and (created_at or "") >= REVENUE_START)
            entry = all_phones.setdefault(phone, {
                "phone": phone, "name": "", "reports": 0, "paid": 0,
                "spend_inr": 0, "last_at": created_at or "", "team_tag": tag,
                "_has_real_pay": False,
            })
            if not entry["name"]:
                entry["name"] = _display_name(payload)
            entry["reports"] += 1
            if paid:
                entry["paid"] += 1
            if is_real_pay:
                entry["_has_real_pay"] = True
                entry["spend_inr"] += order_amount_paise({"payload": payload}) // 100
        customers = []
        testers = []
        for e in all_phones.values():
            has_pay = e.pop("_has_real_pay")
            if has_pay:
                customers.append(e)
            else:
                testers.append(e)
        dev_spend = {}
        if team_phones:
            with db() as c:
                likes = []
                params = []
                for tp in team_phones:
                    likes.append("(user_phone LIKE ? OR phone LIKE ?)")
                    params.extend([f"%{tp}%", f"%{tp}%"])
                params.append("pay_%")
                rp = c.execute(
                    "SELECT user_phone, phone, payload FROM reports "
                    "WHERE (" + " OR ".join(likes) + ") "
                    "AND payment_id LIKE ?",
                    tuple(params),
                ).fetchall()
                for uph, pph, payload_json in rp:
                    matched = None
                    for tp in team_phones:
                        if tp in (uph or "") or tp in (pph or ""):
                            matched = tp
                            break
                    if not matched:
                        continue
                    try:
                        pl = json.loads(payload_json) if payload_json else {}
                    except (TypeError, ValueError):
                        pl = {}
                    amt = order_amount_paise({"payload": pl}) // 100
                    entry = dev_spend.setdefault(matched, {"spend_inr": 0, "paid_count": 0})
                    entry["spend_inr"] += amt
                    entry["paid_count"] += 1
        linked_map = {}
        for p in team_data.get("phones", []):
            lt = p.get("linked_to", "")
            if lt:
                linked_map.setdefault(lt, []).append(p["value"])
        developers = []
        seen_linked = set()
        for p in team_data.get("phones", []):
            val = p["value"]
            lt = p.get("linked_to", "")
            if lt:
                seen_linked.add(val)
                continue
            sp = dev_spend.get(val) or {}
            total_spend = sp.get("spend_inr", 0)
            total_paid = sp.get("paid_count", 0)
            linked_phones = linked_map.get(val, [])
            for lp in linked_phones:
                seen_linked.add(lp)
                lsp = dev_spend.get(lp) or {}
                total_spend += lsp.get("spend_inr", 0)
                total_paid += lsp.get("paid_count", 0)
            entry = {
                "value": val, "kind": "phone",
                "label": p.get("label", ""), "added_at": p.get("added_at", ""),
                "spend_inr": total_spend,
                "paid_count": total_paid,
            }
            if linked_phones:
                linked_labels = []
                for lp in linked_phones:
                    ll = next((x.get("label", "") for x in team_data["phones"]
                               if x["value"] == lp), "")
                    linked_labels.append({"value": lp, "label": ll,
                                          "spend_inr": (dev_spend.get(lp) or {}).get("spend_inr", 0),
                                          "paid_count": (dev_spend.get(lp) or {}).get("paid_count", 0)})
                entry["linked"] = linked_labels
            developers.append(entry)
        for e in team_data.get("emails", []):
            developers.append({
                "value": e["value"], "kind": "email",
                "label": e.get("label", ""), "added_at": e.get("added_at", ""),
                "spend_inr": 0, "paid_count": 0,
            })
        return {
            "customers": customers,
            "testers": testers,
            "developers": developers,
        }

    @app.get("/api/admin/customer")
    def admin_customer(request: Request, key: str = "", phone: str = ""):
        _gate(request, key)
        phone = (phone or "").strip()
        if not phone:
            raise HTTPException(422, "phone required")
        like = f"%{phone}%"
        team_data = store.team_all(db)
        team_phones = {p["value"] for p in team_data["phones"]}
        team_emails = {e["value"] for e in team_data["emails"]}
        team_labels = _team_label_map_from(team_data)
        statuses = store.all_statuses(db)
        with db() as c:
            rows = c.execute(
                "SELECT id, created_at, payload, phone, user_phone, paid, payment_id "
                "FROM reports WHERE user_phone LIKE ? OR phone LIKE ? "
                "ORDER BY created_at DESC",
                (like, like),
            ).fetchall()
        history = []
        for rid, created_at, payload_json, pay_phone, deliver_phone, paid, payment_id in rows:
            try:
                payload = json.loads(payload_json) if payload_json else {}
            except (TypeError, ValueError):
                payload = {}
            amount_inr = order_amount_paise({"payload": payload}) // 100
            st = statuses.get(rid) or {}
            reason = _classify_exclusion(created_at, deliver_phone, pay_phone,
                                         _payload_email(payload),
                                         team_phones, team_emails,
                                         payment_id) if paid else ""
            tag = _phone_tag(deliver_phone, pay_phone, team_labels, team_phones)
            history.append({
                "rid": rid,
                "created_at": created_at or "",
                "product": _product_label(payload),
                "amount_inr": amount_inr,
                "paid": bool(paid),
                "is_test": bool(reason),
                "exclude_reason": reason,
                "payment_id": payment_id or "",
                "pay_phone": pay_phone or "",
                "deliver_phone": deliver_phone or "",
                "team_tag": tag,
                "status": st.get("status") or ("pending" if paid else "unpaid"),
                "report_url": f"/report/{rid}",
                "pdf_url": f"/report/{rid}.pdf",
                "forward_message": _forward_message(payload, rid, amount_inr),
            })
        return {"phone": phone, "history": history}

    @app.post("/api/admin/delivery_status")
    def admin_delivery_status(request: Request, body: dict, key: str = ""):
        _gate(request, key)
        rid = (body or {}).get("rid", "")
        status = (body or {}).get("status", "")
        note = (body or {}).get("note", "")
        if not rid or not status:
            raise HTTPException(422, "rid and status required")
        # verify the report exists (don't create orphan status rows)
        rec = get_report(rid)
        if not rec:
            raise HTTPException(404, "report not found")
        return {"ok": True, "row": store.set_status(db, rid, status, note)}

    @app.get("/api/admin/config")
    def admin_config(request: Request, key: str = ""):
        _gate(request, key)
        # Placeholder values for tabs with no live source yet (see config.py),
        # PLUS server-computed wallet states (runway + sustain date, live Twilio
        # overlaid) and today's date — so the UI never has to compute dates.
        today = datetime.utcnow().date().isoformat()
        cfg = dict(CONFIG)
        cfg["wallet_states"] = money.wallet_states(today=today)
        cfg["today"] = today
        cfg["thresholds"] = {"warn_days": WARN_DAYS, "critical_days": CRITICAL_DAYS}
        db_ledger = store.ledger_all(db)
        sr = dict(cfg.get("spend_revenue") or {})
        sr["ledger"] = db_ledger + (sr.get("ledger") or [])
        cfg["spend_revenue"] = sr
        llm_stats = store.llm_log_stats(db)
        llm_recent = store.llm_log_recent(db, limit=30)
        llm = dict(cfg.get("llm") or {})
        llm["live_today"] = llm_stats["live_today"]
        llm["fallbacks"] = llm_stats["fallbacks"]
        llm["avg_gen_s"] = llm_stats["avg_gen_s"]
        llm["slowest_s"] = llm_stats["slowest_s"]
        llm["recent"] = llm_recent
        cfg["llm"] = llm
        return JSONResponse({"config": cfg, "site_base": SITE_BASE})

    @app.get("/api/admin/twilio_balance")
    def admin_twilio_balance(request: Request, key: str = ""):
        """Live Twilio account balance (cached ~10 min, never raises). On
        failure/missing creds returns {"live": False, ...} and the UI falls back
        to the config value."""
        _gate(request, key)
        return providers.twilio_balance()

    @app.get("/api/admin/payments")
    def admin_payments(request: Request, key: str = ""):
        """Live Razorpay payment history. Returns only captured (real money)
        payments, with team exclusion tags and pass-vs-real classification."""
        _gate(request, key)
        rzp = providers.razorpay_payments(limit=200)
        team_phones, team_emails = store.team_sets(db)
        team_labels = _team_label_map_from(store.team_all(db))
        payments = []
        real_revenue = 0
        team_revenue = 0
        for p in rzp.get("payments", []):
            contact = p.get("contact") or ""
            email = p.get("email") or ""
            tag = ""
            is_team = False
            normed = store.norm_phone(contact)
            normed_email = store.norm_email(email)
            if normed in team_phones:
                is_team = True
                tag = team_labels.get(normed) or "team"
            elif normed_email and normed_email in team_emails:
                is_team = True
                tag = team_labels.get(normed_email) or "team"
            if not is_team:
                real_revenue += p.get("amount_inr", 0)
            else:
                team_revenue += p.get("amount_inr", 0)
            payments.append({
                "id": p.get("id", ""),
                "amount_inr": p.get("amount_inr", 0),
                "contact": contact,
                "email": p.get("email", ""),
                "method": p.get("method", ""),
                "created_at": p.get("created_at", ""),
                "order_id": p.get("order_id", ""),
                "report_id": (p.get("notes") or {}).get("report_id", ""),
                "is_team": is_team,
                "team_tag": tag,
            })
        return {
            "live": rzp.get("live", False),
            "payments": payments,
            "real_revenue": real_revenue,
            "team_revenue": team_revenue,
            "total_count": len(payments),
            "real_count": sum(1 for p in payments if not p["is_team"]),
            "team_count": sum(1 for p in payments if p["is_team"]),
            "note": rzp.get("note", ""),
        }

    # ------------------------------------------------ ops event recording + live health
    @app.post("/api/admin/ops_event")
    def admin_ops_event(request: Request, body: dict, key: str = ""):
        """Record an ops event (run/rollback/alert). Called by GitHub Actions
        workflows after each watcher or robot-customer run."""
        _gate(request, key)
        kind = (body or {}).get("kind", "")
        if kind not in ("watcher", "robot", "rollback", "alert", "deploy"):
            raise HTTPException(422, "kind must be watcher, robot, rollback, alert, or deploy")
        row = store.ops_log_add(db, kind,
                                status=(body or {}).get("status", ""),
                                detail=(body or {}).get("detail", ""),
                                run_url=(body or {}).get("run_url", ""),
                                from_ver=(body or {}).get("from_ver", ""),
                                to_ver=(body or {}).get("to_ver", ""),
                                severity=(body or {}).get("severity", ""))
        return {"ok": True, "row": row}

    @app.get("/api/admin/ops_health")
    def admin_ops_health(request: Request, key: str = ""):
        """Live health check — hits the app's own healthz endpoints and returns
        green/red per check. Called when the Ops tab opens."""
        _gate(request, key)
        import urllib.request
        base = str(request.base_url).rstrip("/")
        checks = []
        for name, path in [("DB liveness", "/healthz"),
                           ("DB write-durability", "/healthz/db")]:
            try:
                r = urllib.request.urlopen(base + path, timeout=10)
                ok = r.status == 200
            except Exception:
                ok = False
            checks.append({"name": name, "ok": ok})
        try:
            otp_url = base + "/api/otp/health?key=" + (_admin_secret() or "")
            r = urllib.request.urlopen(otp_url, timeout=10)
            otp_ok = r.status == 200
        except Exception:
            otp_ok = False
        checks.append({"name": "OTP provider", "ok": otp_ok})
        return {
            "checks": checks,
            "all_ok": all(c["ok"] for c in checks),
            "last_watcher": store.ops_log_last(db, "watcher"),
            "last_robot": store.ops_log_last(db, "robot"),
            "last_rollback": store.ops_log_last(db, "rollback"),
            "last_deploy": store.ops_log_last(db, "deploy"),
            "watcher_events": store.ops_log_recent(db, limit=50, kind="watcher"),
            "robot_events": store.ops_log_recent(db, limit=50, kind="robot"),
            "rollbacks": store.ops_log_recent(db, limit=20, kind="rollback"),
            "deploy_events": store.ops_log_recent(db, limit=20, kind="deploy"),
        }

    # ------------------------------------------------ LLM health
    @app.get("/api/admin/llm_health")
    def admin_llm_health(request: Request, key: str = ""):
        """Verify the Anthropic API key is set AND accepted by the API.

        Sends a single tiny prompt ("Reply OK") to claude-haiku-4-5-20251001
        with max_tokens=5 — cost per call is well under $0.001. Never raises;
        always returns JSON with ``ok`` true/false."""
        _gate(request, key)
        import json as _json, urllib.error, urllib.request

        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            return {"ok": False, "error": "ANTHROPIC_API_KEY not set"}

        model = "claude-haiku-4-5-20251001"
        body = _json.dumps({
            "model": model,
            "max_tokens": 5,
            "messages": [{"role": "user", "content": "Reply OK"}],
        }).encode()
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body, headers=headers, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read().decode())
            reply = "".join(
                p.get("text", "") for p in (data.get("content") or [])
                if p.get("type") == "text"
            )
            return {"ok": True, "model": model,
                    "note": f"API responded: {reply[:40]}"}
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode()[:200]
            except Exception:
                pass
            return {"ok": False, "model": model,
                    "error": f"HTTP {e.code}", "detail": detail}
        except Exception as e:
            return {"ok": False, "model": model,
                    "error": f"{type(e).__name__}: {e}"}

    # ------------------------------------------------ Razorpay health
    @app.get("/api/admin/razorpay_health")
    def admin_razorpay_health(request: Request, key: str = ""):
        """Verify Razorpay credentials are set AND accepted by the API.

        Fetches a single payment (count=1) using Basic auth — the lightest
        authenticated call available. Never raises; always returns JSON with
        ``ok`` true/false."""
        _gate(request, key)
        import json as _json, urllib.error, urllib.request

        key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
        key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
        if not key_id:
            return {"ok": False, "error": "RAZORPAY_KEY_ID not set"}
        if not key_secret:
            return {"ok": False, "error": "RAZORPAY_KEY_SECRET not set"}

        auth = base64.b64encode(f"{key_id}:{key_secret}".encode()).decode()
        req = urllib.request.Request(
            "https://api.razorpay.com/v1/payments?count=1",
            headers={"Authorization": "Basic " + auth},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read().decode())
            count = len(data.get("items") or [])
            return {"ok": True,
                    "note": f"credentials accepted ({count} payment(s) returned)"}
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode()[:200]
            except Exception:
                pass
            return {"ok": False,
                    "error": f"HTTP {e.code}", "detail": detail}
        except Exception as e:
            return {"ok": False,
                    "error": f"{type(e).__name__}: {e}"}

    # ------------------------------------------------ robot cleanup
    @app.get("/api/admin/robot_cleanup")
    def admin_robot_preview(request: Request, key: str = ""):
        _gate(request, key)
        return store.robot_cleanup(db, dry_run=True)

    @app.post("/api/admin/robot_cleanup")
    def admin_robot_cleanup(request: Request, key: str = ""):
        _gate(request, key)
        return store.robot_cleanup(db, dry_run=False)

    # ------------------------------------------------ team exclusion allowlist
    def _valid_pass(passcode):
        """Team-management passcode. Order: DASH_TEAM_PASSCODE, else ADMIN_KEY,
        else STATS_KEY (via the app's validator). No secret is hardcoded."""
        want = os.getenv("DASH_TEAM_PASSCODE", "") or os.getenv("ADMIN_KEY", "")
        if want:
            return hmac.compare_digest(passcode or "", want)
        return valid_admin_key(passcode)   # fallback: STATS_KEY doubles as the passcode

    def _team_gate(request, key, passcode):
        # a valid admin session (cookie or key) AND the team passcode
        if not _authed(request, key) or not _valid_pass(passcode):
            raise HTTPException(403, "forbidden")

    @app.get("/api/admin/team")
    def admin_team_list(request: Request, key: str = "", passcode: str = Query("", alias="pass")):
        _team_gate(request, key, passcode)
        return store.team_all(db)

    @app.post("/api/admin/team")
    def admin_team_add(request: Request, body: dict, key: str = "", passcode: str = Query("", alias="pass")):
        _team_gate(request, key, passcode)
        kind = (body or {}).get("kind", "")
        value = (body or {}).get("value", "")
        label = (body or {}).get("label", "")
        try:
            row = store.team_add(db, kind, value, label)
        except ValueError as e:
            raise HTTPException(422, str(e))
        return {"ok": True, "row": row}

    @app.post("/api/admin/team/remove")
    def admin_team_remove(request: Request, body: dict, key: str = "", passcode: str = Query("", alias="pass")):
        _team_gate(request, key, passcode)
        value = (body or {}).get("value", "")
        if not value:
            raise HTTPException(422, "value required")
        return {"ok": True, "removed": store.team_remove(db, value)}

    @app.post("/api/admin/team/link")
    def admin_team_link(request: Request, body: dict, key: str = "", passcode: str = Query("", alias="pass")):
        _team_gate(request, key, passcode)
        secondary = (body or {}).get("secondary", "")
        primary = (body or {}).get("primary", "")
        if not secondary or not primary:
            raise HTTPException(422, "secondary and primary required")
        try:
            return {"ok": True, **store.team_link(db, secondary, primary)}
        except ValueError as e:
            raise HTTPException(422, str(e))

    @app.post("/api/admin/team/unlink")
    def admin_team_unlink(request: Request, body: dict, key: str = "", passcode: str = Query("", alias="pass")):
        _team_gate(request, key, passcode)
        value = (body or {}).get("value", "")
        if not value:
            raise HTTPException(422, "value required")
        return {"ok": True, **store.team_unlink(db, value)}

    # ------------------------------------------------ ledger (manual top-ups)
    @app.get("/api/admin/ledger")
    def admin_ledger(request: Request, key: str = ""):
        _gate(request, key)
        return {"ledger": store.ledger_all(db)}

    @app.post("/api/admin/ledger")
    def admin_ledger_add(request: Request, body: dict, key: str = ""):
        _gate(request, key)
        try:
            row = store.ledger_add(
                db,
                service=(body or {}).get("service", ""),
                entry=(body or {}).get("entry", "deposit"),
                amount=(body or {}).get("amount", ""),
                date=(body or {}).get("date", ""),
                note=(body or {}).get("note", ""),
            )
        except ValueError as e:
            raise HTTPException(422, str(e))
        return {"ok": True, "row": row}

    # ------------------------------------------------ OTP login delivery log
    @app.get("/api/admin/otp_logins")
    def admin_otp_logins(request: Request, key: str = ""):
        """Login-OTP log from dash_otp_log (append-only — every OTP send is
        recorded and never deleted). The old login_otps table is a pending-OTP
        store (PK on mobile, deletes on verify) so it's useless for history.

        SECURITY: the OTP code is NEVER stored or returned here.
        Status reflects what we recorded at send/verify time:
        sent = we asked MC to send it, verified = user entered correct code,
        locked = 5+ wrong attempts."""
        _gate(request, key)
        mc_ready = _mc_configured()
        this_month = datetime.utcnow().isoformat()[:7]
        logins = store.otp_log_recent(db, limit=200)
        month_count = sum(1 for r in logins if (r.get("time") or "")[:7] == this_month)
        est_inr = round(month_count * 0.30, 2)
        note = ("Connect Message Central API for delivered/rejected status."
                if not mc_ready else
                "Message Central configured — wire its reports API for "
                "delivered/rejected status.")
        return {
            "logins": logins,
            "month_count": month_count,
            "cost_estimate": {
                "per_otp_inr": 0.30,
                "month_inr": est_inr,
                "line": f"~₹0.30/OTP · ₹{est_inr}/mo (est)",
                "estimated": True,
            },
            "mc_configured": mc_ready,
            "note": note,
        }


def _login_html(admin_path, error=False):
    """Tiny gate page shown at /{ADMIN_PATH} without a valid session. Posts the
    key to /{ADMIN_PATH}/login, which sets a signed HttpOnly cookie — so the key
    never rides in the URL. Never exposes any dashboard data."""
    action = "/" + admin_path + "/login"
    err = ("<p style='color:#B3372B'>Wrong key — try again.</p>" if error else
           "<p>Enter the admin key to continue.</p>")
    return (
        "<!doctype html><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta name='robots' content='noindex,nofollow'>"
        "<title>Axtroshastra Admin — sign in</title>"
        "<style>body{background:#EFE8D8;color:#4A3D2A;font:15px/1.6 -apple-system,"
        "BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;display:flex;min-height:100vh;"
        "align-items:center;justify-content:center;margin:0}"
        ".box{background:#FBF7EF;border:1px solid #E7DCC6;border-radius:14px;padding:26px 28px;"
        "max-width:340px;width:92%;box-shadow:0 3px 14px rgba(90,60,20,.08)}"
        "h1{font:600 20px/1.2 Georgia,serif;color:#3a2c18;margin:0 0 6px}"
        "p{color:#9c8f77;font-size:13px;margin:0 0 16px}"
        "input{width:100%;padding:11px 13px;border:1px solid #E7DCC6;border-radius:9px;"
        "background:#F6F0E2;font-size:14px;color:#4A3D2A;box-sizing:border-box}"
        "button{width:100%;margin-top:12px;padding:11px;border:0;border-radius:9px;"
        "background:#3a2c18;color:#EFE8D8;font:600 14px/1 -apple-system,sans-serif;cursor:pointer}"
        "</style>"
        "<form class='box' method='post' action='" + _html.escape(action, quote=True) + "'>"
        "<h1>Admin dashboard</h1>"
        + err +
        "<input name='key' type='password' placeholder='Admin key' autofocus autocomplete='current-password'>"
        "<button type='submit'>Sign in</button>"
        "</form>"
    )
