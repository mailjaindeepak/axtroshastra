"""Safety-net tests for the admin dashboard plugin (dashboard/).

These prove the plugin is additive: the site keeps working, every /api/admin/*
route is locked without the key, the endpoints return well-formed JSON with the
key, a paid report surfaces with the POPUP number as its delivery target, manual
delivery status round-trips, and the whole surface locks down when STATS_KEY is
empty.

Fixtures follow tests/conftest.py: STATS_KEY is set to "test-stats-key" before
api is imported, so that is the valid admin key. Phone numbers are per-test
unique (the suite shares one DB).
"""
import json
from datetime import datetime

import api

KEY = "test-stats-key"
KUNDLI = {"name": "Dash User", "dob": "1990-04-12", "tob": "08:15",
          "time_quality": "T0", "place": "Delhi", "gender": "female"}


def _new_report(client, **overrides):
    r = client.post("/api/kundli", json={**KUNDLI, **overrides})
    assert r.status_code == 200, r.text
    return r.json()["report_id"]


def _make_paid(rid, deliver_phone, pay_phone="9111100001", variant="/milan",
               method="upi"):
    """v2: attach the popup/deliver user (the account/delivery number), tag the
    funnel variant in report_data, create a CAPTURED payment (pay_phone is the
    Razorpay contact, kept separate), and mark the report paid. method='free_pass'
    makes it a non-revenue pass unlock (payment_id surfaces as 'free_pass:…')."""
    import db_v2
    from datetime import timezone
    from flows_v2 import split_phone
    conn = db_v2.get_conn()
    try:
        cc, mob = split_phone(deliver_phone)
        uid = db_v2.create_or_get_user(conn, cc, mob)
        rec = db_v2.get_report(conn, rid)
        data = (rec or {}).get("report_data") or {}
        data.setdefault("meta", {})["variant"] = variant
        slug = rid.replace("-", "")[:10]
        with conn.cursor() as c:
            c.execute("UPDATE reports SET user_id=%s, report_data=%s WHERE id=%s",
                      (uid, json.dumps(data), rid))
        db_v2.record_payment(
            conn, rid, uid, 49900,
            razorpay_payment_id=(None if method == "free_pass" else f"pay_TEST{slug}"),
            status="captured", method=method, payment_contact=pay_phone,
            paid_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
        db_v2.set_report_paid(conn, rid)
        conn.commit()
    finally:
        conn.close()


# 1. plugin did not break the site --------------------------------------------
def test_site_still_serves_existing_route(client):
    assert client.get("/healthz").status_code == 200
    assert client.get("/en/compatibility").status_code == 200


# 2. every admin surface is locked without / with a wrong key ------------------
def test_admin_routes_locked_without_key(client):
    for path in ("/api/admin/overview", "/api/admin/deliveries",
                 "/api/admin/customers", "/api/admin/customer?phone=9",
                 "/api/admin/payments", "/api/admin/config"):
        assert client.get(path).status_code == 403, path
        assert client.get(path + ("&" if "?" in path else "?") + "key=wrong").status_code == 403, path
    # POST route too
    assert client.post("/api/admin/delivery_status", json={"rid": "x", "status": "y"}).status_code == 403
    # /admin shell without a key returns the login prompt, NOT the dashboard
    r = client.get("/admin")
    assert r.status_code == 200
    assert "Admin dashboard" in r.text
    assert 'id="p-overview"' not in r.text   # the real shell is not served


# 3. with the correct key the endpoints return well-formed JSON ----------------
def test_admin_endpoints_ok_with_key(client):
    ov = client.get(f"/api/admin/overview?key={KEY}")
    assert ov.status_code == 200
    body = ov.json()
    assert "totals" in body and "reports" in body
    assert {"paid_count", "revenue_inr", "pending_count"} <= set(body["totals"])

    dl = client.get(f"/api/admin/deliveries?key={KEY}")
    assert dl.status_code == 200 and "deliveries" in dl.json()

    cfg = client.get(f"/api/admin/config?key={KEY}")
    assert cfg.status_code == 200 and "config" in cfg.json()

    # the real HTML shell is served with a valid key
    shell = client.get(f"/admin?key={KEY}")
    assert shell.status_code == 200 and 'id="p-overview"' in shell.text


# 4. a paid report shows up with deliver_phone == user_phone (NOT Razorpay's) --
def test_paid_report_uses_popup_number_for_delivery(client):
    rid = _new_report(client)
    _make_paid(rid, deliver_phone="9967124332", pay_phone="9812345678")
    ov = client.get(f"/api/admin/overview?key={KEY}").json()
    row = next(r for r in ov["reports"] if r["rid"] == rid)
    assert row["deliver_phone"] == "+919967124332"  # normalised popup number
    assert row["pay_phone"] == "9812345678"          # Razorpay number, kept separate
    assert row["deliver_phone"] != row["pay_phone"]
    assert row["report_url"] == f"/report/{rid}"
    assert row["pdf_url"] == f"/report/{rid}.pdf"
    assert str(rid) in row["forward_message"]
    assert row["amount_inr"] == 499
    # counted somewhere (real vs team-test split depends on REVENUE_START cutoff)
    assert ov["totals"]["paid_count"] + ov["totals"]["test_count"] >= 1


# 5. manual delivery status round-trips through dash_delivery ------------------
def test_manual_delivery_status_roundtrip(client):
    rid = _new_report(client)
    _make_paid(rid, deliver_phone="9700000005")
    # starts pending
    ov = client.get(f"/api/admin/overview?key={KEY}").json()
    assert next(r for r in ov["reports"] if r["rid"] == rid)["status"] == "pending"
    # mark delivered
    r = client.post(f"/api/admin/delivery_status?key={KEY}",
                    json={"rid": rid, "status": "delivered", "note": "sent by hand"})
    assert r.status_code == 200 and r.json()["ok"] is True
    ov2 = client.get(f"/api/admin/overview?key={KEY}").json()
    assert next(x for x in ov2["reports"] if x["rid"] == rid)["status"] == "delivered"


def test_customer_lookup_matches_both_numbers(client):
    rid = _new_report(client)
    _make_paid(rid, deliver_phone="9700000006", pay_phone="9600000006")
    # match on the popup number
    cs = client.get(f"/api/admin/customers?key={KEY}&q=9700000006").json()["customers"]
    assert any("9700000006" in c["phone"] for c in cs)
    # match on the Razorpay number
    cs2 = client.get(f"/api/admin/customers?key={KEY}&q=9600000006").json()["customers"]
    assert cs2, "expected a match on the Razorpay number too"
    # full history for the popup number
    hist = client.get(f"/api/admin/customer?key={KEY}&phone=9700000006").json()["history"]
    assert any(h["rid"] == rid and h["paid"] for h in hist)


# 6. dashboard is safe (all locked) when STATS_KEY is empty --------------------
def test_locked_when_stats_key_empty(client, monkeypatch):
    monkeypatch.setattr(api, "STATS_KEY", "", raising=False)
    # even the previously-valid key is now rejected
    assert client.get(f"/api/admin/overview?key={KEY}").status_code == 403
    assert client.get(f"/admin?key={KEY}").status_code == 200
    assert "Admin dashboard" in client.get(f"/admin?key={KEY}").text  # login prompt
    # the rest of the site is unaffected
    assert client.get("/healthz").status_code == 200


# 8. revenue cutoff: team gateway-tests are excluded from real KPIs -----------
def test_revenue_cutoff_excludes_team_test_payments(client):
    from dashboard.config import REVENUE_START
    r_old = _new_report(client); _make_paid(r_old, deliver_phone="9700000091")
    r_new = _new_report(client); _make_paid(r_new, deliver_phone="9700000092")
    with api._lock, api.db() as c:  # force one before and one after the cutoff
        c.execute("UPDATE reports SET created_at=? WHERE id=?", ("2000-01-01 00:00:00", r_old))
        c.execute("UPDATE reports SET created_at=? WHERE id=?", ("2999-01-01 00:00:00", r_new))
    ov = client.get(f"/api/admin/overview?key={KEY}").json()
    rows = {r["rid"]: r for r in ov["reports"]}
    assert rows[r_old]["is_test"] is True     # pre go-live team verification
    assert rows[r_new]["is_test"] is False    # real customer
    assert ov["totals"]["revenue_inr"] >= 499        # real ₹499 counted
    assert ov["totals"]["test_revenue_inr"] >= 499   # test ₹499 quarantined
    assert ov["totals"]["revenue_start"] == REVENUE_START


# 9. team allowlist excludes a post-launch payment by phone -------------------
def test_team_allowlist_excludes_by_phone(client):
    rid = _new_report(client)
    _make_paid(rid, deliver_phone="9312300071", pay_phone="9312300072")
    # force clearly AFTER the cutoff so only the allowlist can exclude it
    with api._lock, api.db() as c:
        c.execute("UPDATE reports SET created_at=? WHERE id=?", ("2999-06-01 00:00:00", rid))
    before = client.get(f"/api/admin/overview?key={KEY}").json()
    row_before = next(r for r in before["reports"] if r["rid"] == rid)
    assert row_before["is_test"] is False           # a real customer, for now
    rev_before = before["totals"]["revenue_inr"]
    # add the delivery number to the team allowlist (formatting-insensitive)
    r = client.post(f"/api/admin/team?key={KEY}&pass={KEY}",
                    json={"kind": "phone", "value": "+91 93123-00071", "label": "Dev"})
    assert r.status_code == 200 and r.json()["ok"] is True
    try:
        after = client.get(f"/api/admin/overview?key={KEY}").json()
        row = next(r for r in after["reports"] if r["rid"] == rid)
        assert row["is_test"] is True
        assert row["exclude_reason"] == "team"
        assert after["totals"]["revenue_inr"] == rev_before - 499
    finally:
        client.post(f"/api/admin/team/remove?key={KEY}&pass={KEY}", json={"value": "9312300071"})


# 10. team add/remove round-trips through the endpoints ----------------------
def test_team_add_remove_roundtrip(client):
    r = client.post(f"/api/admin/team?key={KEY}&pass={KEY}",
                    json={"kind": "email", "value": "  DEV@Team.com ", "label": "Dev email"})
    assert r.status_code == 200
    lst = client.get(f"/api/admin/team?key={KEY}&pass={KEY}").json()
    assert any(e["value"] == "dev@team.com" for e in lst["emails"])   # normalised
    r2 = client.post(f"/api/admin/team/remove?key={KEY}&pass={KEY}", json={"value": "dev@team.com"})
    assert r2.status_code == 200
    lst2 = client.get(f"/api/admin/team?key={KEY}&pass={KEY}").json()
    assert not any(e["value"] == "dev@team.com" for e in lst2["emails"])
    # invalid kind -> 422
    assert client.post(f"/api/admin/team?key={KEY}&pass={KEY}",
                       json={"kind": "fax", "value": "x"}).status_code == 422


# 11. team endpoints require the passcode (with env fallback to STATS_KEY) ----
def test_team_passcode_gate(client, monkeypatch):
    monkeypatch.delenv("DASH_TEAM_PASSCODE", raising=False)
    # fallback: when DASH_TEAM_PASSCODE is unset, the admin key doubles as the passcode
    assert client.get(f"/api/admin/team?key={KEY}&pass={KEY}").status_code == 200
    assert client.get(f"/api/admin/team?key={KEY}&pass=wrong").status_code == 403
    assert client.get(f"/api/admin/team?key={KEY}").status_code == 403          # missing pass
    assert client.get(f"/api/admin/team?key=wrong&pass={KEY}").status_code == 403  # bad admin key
    # when DASH_TEAM_PASSCODE IS set, it (not the admin key) is the passcode
    monkeypatch.setenv("DASH_TEAM_PASSCODE", "sekret")
    assert client.get(f"/api/admin/team?key={KEY}&pass=sekret").status_code == 200
    assert client.get(f"/api/admin/team?key={KEY}&pass={KEY}").status_code == 403


# 12. OTP login log: gated, NEVER exposes the code ----------------------------
def _seed_otp_log(mobile, provider="Message Central", status="sent", attempts=0):
    """Seed dash_otp_log (the primary source for the OTP logins endpoint)."""
    from dashboard import store
    store._ensure_otp_log(api.db)
    now = datetime.utcnow().isoformat()
    with api.db() as c:
        c.execute(
            "INSERT INTO dash_otp_log(mobile,provider,status,attempts,created_at) "
            "VALUES(?,?,?,?,?)",
            (mobile, provider, status, attempts, now),
        )


def test_otp_logins_requires_key(client):
    assert client.get("/api/admin/otp_logins").status_code == 403
    assert client.get("/api/admin/otp_logins?key=wrong").status_code == 403


def test_otp_logins_shows_data_from_dash_otp_log(client):
    _seed_otp_log("+919876500011", provider="Message Central", status="verified", attempts=1)
    d = client.get(f"/api/admin/otp_logins?key={KEY}").json()
    assert "logins" in d and d["logins"]
    row = next(r for r in d["logins"] if "9876500011" in r["phone"])
    assert row["phone"] == "+919876500011"
    assert row["provider"] == "Message Central"
    assert row["status"] == "verified"
    assert "code" not in row and "code_hash" not in row
    assert d["cost_estimate"]["estimated"] is True
    assert d["month_count"] >= 1


def test_otp_logins_count_reflects_seeded_rows(client):
    _seed_otp_log("+919000000031")
    _seed_otp_log("+919000000032")
    d = client.get(f"/api/admin/otp_logins?key={KEY}").json()
    phones = [r["phone"] for r in d["logins"]]
    assert any("9000000031" in p for p in phones)
    assert any("9000000032" in p for p in phones)
    assert d["month_count"] >= 2


def test_otp_log_store_functions():
    """Verify dash_otp_log store helpers round-trip correctly."""
    from dashboard import store
    store.otp_log_add(api.db, "+919999900041", "Message Central")
    rows = store.otp_log_recent(api.db, limit=5)
    match = [r for r in rows if "9999900041" in r["phone"]]
    assert match and match[0]["status"] == "sent"
    store.otp_log_update_status(api.db, "+919999900041", "verified")
    rows = store.otp_log_recent(api.db, limit=5)
    match = [r for r in rows if "9999900041" in r["phone"]]
    assert match[0]["status"] == "verified"


def test_otp_log_update_with_attempts():
    from dashboard import store
    store.otp_log_add(api.db, "+919999900042", "Message Central")
    store.otp_log_update_status(api.db, "+919999900042", "locked", attempts=5)
    rows = store.otp_log_recent(api.db, limit=5)
    match = [r for r in rows if "9999900042" in r["phone"]]
    assert match[0]["status"] == "locked"
    assert match[0]["attempts"] == 5


# 13. Twilio live balance endpoint (gated, never raises) ----------------------
def test_twilio_balance_requires_key(client):
    assert client.get("/api/admin/twilio_balance").status_code == 403


def test_twilio_balance_degrades_without_creds(client, monkeypatch):
    # no TWILIO creds in the test env -> live:False, note, never a 500
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    import dashboard.providers as _p
    _p._twilio_cache["data"] = None  # bypass any cache from a prior call
    r = client.get(f"/api/admin/twilio_balance?key={KEY}")
    assert r.status_code == 200
    body = r.json()
    assert body["live"] is False
    assert "note" in body


# 14. Cookie login flow: secret path + signed session cookie ------------------
def _fresh_client():
    """Isolated client so its cookie jar never leaks into the shared fixture."""
    from fastapi.testclient import TestClient
    return TestClient(api.app)


def test_login_sets_cookie_and_grants_access_without_key(client):
    c = _fresh_client()
    # no cookie, no key -> blocked
    assert c.get("/api/admin/overview").status_code == 403
    # POST the login form with the right key -> sets admin_session cookie
    r = c.post("/admin/login", data={"key": KEY}, follow_redirects=False)
    assert r.status_code == 303
    assert "admin_session" in c.cookies
    # now the cookie alone (NO key in URL) grants access
    ov = c.get("/api/admin/overview")
    assert ov.status_code == 200 and "totals" in ov.json()
    # and the shell serves the real dashboard, not the login form
    shell = c.get("/admin")
    assert shell.status_code == 200 and 'id="p-overview"' in shell.text


def test_wrong_login_key_is_401_and_sets_no_cookie(client):
    c = _fresh_client()
    r = c.post("/admin/login", data={"key": "nope"}, follow_redirects=False)
    assert r.status_code == 401
    assert "admin_session" not in c.cookies
    assert c.get("/api/admin/overview").status_code == 403


def test_tampered_or_absent_cookie_is_blocked(client):
    c = _fresh_client()
    # absent cookie -> blocked
    assert c.get("/api/admin/overview").status_code == 403
    # tampered cookie -> rejected (signature check fails)
    c.cookies.set("admin_session", "AAAA.BBBB")
    assert c.get("/api/admin/overview").status_code == 403


def test_key_in_url_still_works_backcompat(client):
    # the shared fixture never logged in (no cookie) — the ?key= path must work
    assert client.get(f"/api/admin/overview?key={KEY}").status_code == 200
    assert client.get(f"/admin?key={KEY}").text.count('id="p-overview"') == 1


def test_logout_clears_cookie(client):
    c = _fresh_client()
    c.post("/admin/login", data={"key": KEY}, follow_redirects=False)
    assert "admin_session" in c.cookies
    c.get("/admin/logout", follow_redirects=False)
    assert not c.cookies.get("admin_session")


# 15. Accuracy pass — honest empty states, real 7-day chart, sustain dates ----
def test_config_has_no_fabricated_traffic_or_investment(client):
    cfg = client.get(f"/api/admin/config?key={KEY}").json()["config"]
    # traffic is NOT connected -> null/empty, never fake numbers
    tr = cfg["traffic"]
    assert tr["visitors_now"] is None and tr["visitors_7d"] is None
    assert tr["sources"] == [] and tr["funnel"] == []
    assert tr.get("connected") is False
    # on-site visitors need GA4 -> null
    assert cfg["on_site_now"] is None
    # investment is a placeholder -> all None (no invented figures)
    inv = cfg["investment"]
    assert all(inv[k] is None for k in inv)
    # spend history bars removed (no fabricated 6-month series)
    for s in cfg["spend_revenue"]["by_service"]:
        assert "series" not in s


def test_config_has_facebook_pixel_block_without_fabricated_numbers(client):
    cfg = client.get(f"/api/admin/config?key={KEY}").json()["config"]
    fp = cfg["facebook_pixel"]
    # the real site pixel id is carried through
    assert fp["pixel_id"] == "1498790608627206"
    assert fp["events_manager_url"].endswith(fp["pixel_id"])
    # NOT connected -> every event count is null and the series is empty
    assert fp.get("connected") is False
    assert set(fp["events"]) == {
        "PageView", "ViewContent", "Lead", "InitiateCheckout", "Purchase"}
    assert all(v is None for v in fp["events"].values())  # no fabricated counts
    assert fp["series_7d"] == []                            # no fabricated bars
    assert fp["note"]


def test_config_wallet_states_carry_sustain_dates(client):
    cfg = client.get(f"/api/admin/config?key={KEY}").json()["config"]
    assert "today" in cfg and cfg["today"]
    states = cfg["wallet_states"]
    assert states, "expected server-computed wallet states"
    for w in states:
        assert "runway_days" in w and "state" in w and "auto" in w
        if not w["unknown"]:
            assert w["sustain_date"], f"{w['name']} should have a sustain date"
            assert w["sustain_date"].startswith("~")
    # Twilio is the auto-updating one; the rest are manual top-ups
    twilio = next(w for w in states if w["name"] == "Twilio")
    assert twilio["auto"] is True
    assert any(w["auto"] is False for w in states if w["name"] != "Twilio")


def test_overview_revenue_7d_uses_real_db_revenue(client):
    rid = _new_report(client)
    _make_paid(rid, deliver_phone="9700000201")   # dated today (real customer)
    ov = client.get(f"/api/admin/overview?key={KEY}").json()
    series = ov["revenue_7d"]
    assert len(series) == 7
    today = datetime.utcnow().date().isoformat()
    today_bucket = next(d for d in series if d["date"] == today)
    # today's real paid revenue is reflected; the whole week sums to real revenue
    assert today_bucket["paid_inr"] >= 499
    assert sum(d["paid_inr"] for d in series) <= ov["totals"]["revenue_inr"] + 0  # only real counted


# 16. Low-balance alerts (Task 4) --------------------------------------------
def test_sustain_date_is_computed():
    from dashboard import money
    # 14 days from a fixed base date
    assert money.sustain_date(14, today="2026-08-08") == "~22 Aug 2026"
    assert money.sustain_date(None) is None


def test_low_wallet_triggers_critical_alert(monkeypatch):
    from dashboard import money, config as dcfg
    calls = []
    monkeypatch.setattr(dcfg, "CONFIG", {
        "wallets": [
            {"name": "Message Central", "balance": "₹40", "state": "ok",
             "runway_days": 5, "console": "https://mc"},
            {"name": "AWS credit", "balance": "$120", "state": "ok",
             "runway_days": 900, "console": "https://aws"},
        ]
    })
    res = money.check_low_balances(
        lambda subject, body, severity: calls.append((subject, body, severity)),
        today="2026-08-08", twilio=None)
    assert res["alerted"] == "critical"
    assert len(calls) == 1
    subject, body, severity = calls[0]
    assert severity == "critical"
    assert "Message Central" in subject and "Message Central" in body
    assert "runs out" in body   # includes the run-out date


def test_healthy_wallets_do_not_alert(monkeypatch):
    from dashboard import money, config as dcfg
    calls = []
    monkeypatch.setattr(dcfg, "CONFIG", {
        "wallets": [{"name": "AWS credit", "balance": "$120", "state": "ok",
                     "runway_days": 900, "console": ""}]
    })
    res = money.check_low_balances(lambda *a: calls.append(a),
                                   today="2026-08-08", twilio=None)
    assert res["alerted"] is None and calls == []


def test_ops_watcher_runs_wallet_check(monkeypatch):
    # the watcher's wallet hook delegates to money.check_low_balances and fires
    from ops import watcher
    from dashboard import config as dcfg
    calls = []
    monkeypatch.setattr(watcher.alerts, "send_alert",
                        lambda *a, **k: calls.append((a, k)) or {"email": True})
    monkeypatch.setattr(dcfg, "CONFIG", {
        "wallets": [{"name": "Claude / LLM", "balance": "$3", "state": "ok",
                     "runway_days": 8, "console": "https://x"}]
    })
    watcher._check_wallet_balances()
    assert len(calls) == 1
    args, kwargs = calls[0]
    severity = kwargs.get("severity", args[2] if len(args) > 2 else None)
    assert severity == "critical"


# ===================================================================
# NEW TESTS — ledger, SITE_BASE, customer empty-query, config mutation
# ===================================================================

# 17. Ledger API: add, list, validation, config merge ---------------------------
def test_ledger_requires_key(client):
    assert client.get("/api/admin/ledger").status_code == 403
    assert client.post("/api/admin/ledger",
                       json={"service": "x", "amount": "10"}).status_code == 403


def test_ledger_add_and_list(client):
    r = client.post(f"/api/admin/ledger?key={KEY}",
                    json={"service": "Claude / LLM", "entry": "deposit",
                          "amount": "$50", "date": "2026-08-10", "note": "topped up"})
    assert r.status_code == 200 and r.json()["ok"] is True
    row = r.json()["row"]
    assert row["service"] == "Claude / LLM"
    assert row["entry"] == "deposit"
    assert row["amount"] == "$50"
    lst = client.get(f"/api/admin/ledger?key={KEY}").json()["ledger"]
    assert any(e["service"] == "Claude / LLM" and e["amount"] == "$50" for e in lst)


def test_ledger_rejects_invalid_entry_type(client):
    r = client.post(f"/api/admin/ledger?key={KEY}",
                    json={"service": "Twilio", "entry": "refund", "amount": "$5"})
    assert r.status_code == 422


def test_ledger_rejects_missing_service_or_amount(client):
    r = client.post(f"/api/admin/ledger?key={KEY}",
                    json={"service": "", "entry": "deposit", "amount": "$5"})
    assert r.status_code == 422
    r2 = client.post(f"/api/admin/ledger?key={KEY}",
                     json={"service": "AWS", "entry": "deposit", "amount": ""})
    assert r2.status_code == 422


# 18. Config endpoint merges DB ledger without mutating the original CONFIG ------
def test_config_ledger_merge_does_not_mutate_global(client):
    from dashboard.config import CONFIG
    original_ledger = list(CONFIG.get("spend_revenue", {}).get("ledger", []))
    client.post(f"/api/admin/ledger?key={KEY}",
                json={"service": "test-svc", "entry": "usage",
                      "amount": "99", "date": "2026-08-11"})
    cfg1 = client.get(f"/api/admin/config?key={KEY}").json()["config"]
    cfg2 = client.get(f"/api/admin/config?key={KEY}").json()["config"]
    ledger1 = cfg1["spend_revenue"]["ledger"]
    ledger2 = cfg2["spend_revenue"]["ledger"]
    assert len(ledger1) == len(ledger2), "config mutation: ledger grew between calls"
    after_ledger = CONFIG.get("spend_revenue", {}).get("ledger", [])
    assert after_ledger == original_ledger, "CONFIG was mutated by /api/admin/config"


# 19. SITE_BASE includes https — forward messages contain clickable links --------
def test_forward_message_contains_https_links(client):
    rid = _new_report(client)
    _make_paid(rid, deliver_phone="9700000301")
    ov = client.get(f"/api/admin/overview?key={KEY}").json()
    row = next(r for r in ov["reports"] if r["rid"] == rid)
    assert "https://" in row["forward_message"], \
        "forward_message should contain https:// links"
    assert f"https://axtroshastra.com/report/{rid}" in row["forward_message"]


# 20. Customer page empty-query returns reports with only pay-phone (no user_phone)
def test_customer_empty_query_includes_pay_phone_only(client):
    rid = _new_report(client)
    # v2 orphan capture: no popup number, so the user is attached from the Razorpay
    # contact — the account/delivery number == the pay number (9700000401).
    _make_paid(rid, deliver_phone="9700000401", pay_phone="9700000401")
    cs = client.get(f"/api/admin/customers?key={KEY}").json()["customers"]
    phones = [c["phone"] for c in cs]
    assert any("9700000401" in p for p in phones), \
        "reports with only a Razorpay phone (no popup number) should appear"


# 21. Ledger entries appear in the config endpoint response ----------------------
def test_ledger_entries_appear_in_config(client):
    client.post(f"/api/admin/ledger?key={KEY}",
                json={"service": "Twilio", "entry": "deposit",
                      "amount": "$20", "date": "2026-08-09"})
    cfg = client.get(f"/api/admin/config?key={KEY}").json()["config"]
    ledger = cfg.get("spend_revenue", {}).get("ledger", [])
    assert any(e["service"] == "Twilio" and e["amount"] == "$20" for e in ledger)


# 22. LLM log: write, read, stats, config merge --------------------------------
def test_llm_log_roundtrip(client):
    from dashboard.store import llm_log_add, llm_log_recent, llm_log_stats
    llm_log_add(api.db, "test-rid-001", {
        "mode": "live Claude", "latency_s": 4.2, "product": "marriage",
        "model": "claude-sonnet-5", "input_tokens": 1200,
        "output_tokens": 800, "sections": 28, "total_sections": 32,
    })
    recent = llm_log_recent(api.db, limit=5)
    assert any(r["rid"] == "test-rid-001" and r["mode"] == "live Claude" for r in recent)
    stats = llm_log_stats(api.db)
    assert stats["live_today"] >= 1
    assert stats["avg_gen_s"] is not None


def test_llm_log_appears_in_config(client):
    from dashboard.store import llm_log_add
    llm_log_add(api.db, "test-rid-002", {
        "mode": "live Claude", "latency_s": 3.1, "product": "career",
        "model": "claude-sonnet-5", "input_tokens": 900,
        "output_tokens": 600, "sections": 10, "total_sections": 12,
    })
    cfg = client.get(f"/api/admin/config?key={KEY}").json()["config"]
    llm = cfg["llm"]
    assert llm["live_today"] >= 1
    assert any(r["rid"] == "test-rid-002" for r in llm["recent"])


# 23. Ops log: store functions + event endpoint --------------------------------
def test_ops_log_roundtrip():
    from dashboard.store import ops_log_add, ops_log_recent, ops_log_last
    ops_log_add(api.db, "watcher", status="pass", detail="all checks green",
                run_url="https://github.com/actions/runs/1", severity="info")
    ops_log_add(api.db, "robot", status="fail", detail="payment flow broken",
                run_url="https://github.com/actions/runs/2", severity="critical")
    ops_log_add(api.db, "rollback", status="triggered", detail="2 failures",
                from_ver="v12", to_ver="v11", severity="critical")
    watchers = ops_log_recent(api.db, limit=5, kind="watcher")
    assert any(r["status"] == "pass" and r["detail"] == "all checks green" for r in watchers)
    robots = ops_log_recent(api.db, limit=5, kind="robot")
    assert any(r["status"] == "fail" and r["detail"] == "payment flow broken" for r in robots)
    rbs = ops_log_recent(api.db, limit=5, kind="rollback")
    assert any(r["from_ver"] == "v12" and r["to_ver"] == "v11" for r in rbs)
    last = ops_log_last(api.db, "watcher")
    assert last is not None and last["status"] == "pass"


def test_ops_event_requires_key(client):
    r = client.post("/api/admin/ops_event",
                    json={"kind": "watcher", "status": "pass"})
    assert r.status_code == 403


def test_ops_event_records_watcher(client):
    r = client.post(f"/api/admin/ops_event?key={KEY}",
                    json={"kind": "watcher", "status": "pass",
                          "detail": "DB + PDF + OTP all green",
                          "run_url": "https://github.com/actions/runs/99"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_ops_event_records_robot(client):
    r = client.post(f"/api/admin/ops_event?key={KEY}",
                    json={"kind": "robot", "status": "pass",
                          "detail": "E2E journey passed",
                          "run_url": "https://github.com/actions/runs/100"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_ops_event_rejects_bad_kind(client):
    r = client.post(f"/api/admin/ops_event?key={KEY}",
                    json={"kind": "invalid"})
    assert r.status_code == 422


def test_ops_health_requires_key(client):
    r = client.get("/api/admin/ops_health")
    assert r.status_code == 403


def test_ops_health_returns_structure(client):
    r = client.get(f"/api/admin/ops_health?key={KEY}")
    assert r.status_code == 200
    d = r.json()
    assert "checks" in d
    assert "all_ok" in d
    assert "watcher_events" in d
    assert "robot_events" in d
    assert "rollbacks" in d
    assert "deploy_events" in d


# ---- Payments (Razorpay) endpoint -------------------------------------------
def test_payments_endpoint_returns_structure(client):
    r = client.get(f"/api/admin/payments?key={KEY}")
    assert r.status_code == 200
    d = r.json()
    assert "payments" in d
    assert "real_revenue" in d
    assert "team_revenue" in d
    assert "total_count" in d
    assert "real_count" in d
    assert "team_count" in d
    assert isinstance(d["live"], bool)


def test_payments_endpoint_locked(client):
    assert client.get("/api/admin/payments").status_code == 403


# ---- Customers 3-category endpoint -----------------------------------------
def test_customers_returns_three_categories(client):
    rid = _new_report(client, phone="9877700001")
    _make_paid(rid, deliver_phone="9877700002")
    r = client.get(f"/api/admin/customers?key={KEY}")
    assert r.status_code == 200
    d = r.json()
    assert "customers" in d
    assert "testers" in d
    assert "developers" in d


def test_customers_pass_users_appear_as_testers(client):
    rid = _new_report(client, phone="9877700010")
    # a free-pass unlock: deliver number 9877700011, method free_pass -> not a real
    # paying customer, so it lands in "testers" (pass = excluded from revenue).
    _make_paid(rid, deliver_phone="9877700011", pay_phone="9877700010",
               method="free_pass")
    r = client.get(f"/api/admin/customers?key={KEY}")
    d = r.json()
    testers = d["testers"]
    assert any("9877700011" in t["phone"] for t in testers)


def test_customers_team_exclusion_in_developers(client):
    from dashboard import store
    store.team_add(api.db, "phone", "9877700020", "TestDev")
    try:
        r = client.get(f"/api/admin/customers?key={KEY}")
        d = r.json()
        dev_values = [dev["value"] for dev in d["developers"]]
        assert "9877700020" in dev_values
    finally:
        store.team_remove(api.db, "9877700020")


def test_deliveries_include_team_tag(client):
    from dashboard import store
    store.team_add(api.db, "phone", "9877700030", "QA-lead")
    try:
        rid = _new_report(client, phone="9877700030")
        _make_paid(rid, deliver_phone="9877700030", pay_phone="9877700030")
        r = client.get(f"/api/admin/deliveries?key={KEY}")
        rows = r.json()["deliveries"]
        tagged = [d for d in rows if d.get("team_tag") == "QA-lead"]
        assert len(tagged) >= 1
    finally:
        store.team_remove(api.db, "9877700030")


def test_customer_detail_includes_team_tag(client):
    from dashboard import store
    store.team_add(api.db, "phone", "9877700040", "Backend")
    try:
        rid = _new_report(client, phone="9877700040")
        _make_paid(rid, deliver_phone="9877700040", pay_phone="9877700040")
        r = client.get(f"/api/admin/customer?key={KEY}&phone=9877700040")
        history = r.json()["history"]
        assert any(h.get("team_tag") == "Backend" for h in history)
    finally:
        store.team_remove(api.db, "9877700040")


# ---- Robot cleanup endpoint --------------------------------------------------

def test_robot_cleanup_dry_run(client):
    r = client.get(f"/api/admin/robot_cleanup?key={KEY}")
    assert r.status_code == 200
    d = r.json()
    assert d["dry_run"] is True
    assert "would_delete" in d


def test_robot_cleanup_execute(client):
    rid = _new_report(client, name="Robot Customer TestBot")
    r = client.post(f"/api/admin/robot_cleanup?key={KEY}")
    assert r.status_code == 200
    d = r.json()
    assert d["dry_run"] is False
    assert d["deleted"] >= 1


def test_robot_cleanup_requires_key(client):
    assert client.post("/api/admin/robot_cleanup").status_code == 403


# ---- Team link/unlink endpoints ---------------------------------------------

def test_team_link_and_unlink(client):
    from dashboard import store
    store.team_add(api.db, "phone", "9877700050", "Primary")
    store.team_add(api.db, "phone", "9877700051", "Secondary")
    try:
        r = client.post(f"/api/admin/team/link?key={KEY}&pass={KEY}",
                        json={"secondary": "9877700051", "primary": "9877700050"})
        assert r.status_code == 200
        assert r.json()["ok"] is True
        lst = client.get(f"/api/admin/team?key={KEY}&pass={KEY}").json()
        sec_entry = next(p for p in lst["phones"] if p["value"] == "9877700051")
        assert sec_entry["linked_to"] == "9877700050"
        r2 = client.post(f"/api/admin/team/unlink?key={KEY}&pass={KEY}",
                         json={"value": "9877700051"})
        assert r2.status_code == 200
        lst2 = client.get(f"/api/admin/team?key={KEY}&pass={KEY}").json()
        sec2 = next(p for p in lst2["phones"] if p["value"] == "9877700051")
        assert sec2.get("linked_to") is None
    finally:
        store.team_remove(api.db, "9877700050")
        store.team_remove(api.db, "9877700051")


def test_team_link_rejects_missing_phone(client):
    r = client.post(f"/api/admin/team/link?key={KEY}&pass={KEY}",
                    json={"secondary": "0000000000", "primary": "0000000001"})
    assert r.status_code == 422


def test_team_unlink_requires_value(client):
    r = client.post(f"/api/admin/team/unlink?key={KEY}&pass={KEY}",
                    json={"value": ""})
    assert r.status_code == 422


# ---- ops_event: kind=rollback, alert, deploy ---------------------------------

def test_ops_event_records_deploy(client):
    r = client.post(f"/api/admin/ops_event?key={KEY}",
                    json={"kind": "deploy", "status": "pass",
                          "detail": "Guarded deploy succeeded",
                          "run_url": "https://github.com/actions/runs/200",
                          "severity": "info"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_ops_event_records_rollback(client):
    r = client.post(f"/api/admin/ops_event?key={KEY}",
                    json={"kind": "rollback", "status": "triggered",
                          "detail": "2 consecutive failures",
                          "from_ver": "v20260810", "to_ver": "v20260809",
                          "severity": "critical"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_ops_event_records_alert(client):
    r = client.post(f"/api/admin/ops_event?key={KEY}",
                    json={"kind": "alert", "status": "sent",
                          "detail": "test alert event",
                          "severity": "warning"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


# ---- Email-based team exclusion from revenue ---------------------------------

def test_team_email_exclusion_from_revenue(client):
    from dashboard import store
    rid = _new_report(client)
    _make_paid(rid, deliver_phone="9312300081", pay_phone="9312300082")
    import db_v2
    conn = db_v2.get_conn()
    try:                                  # v2: email lives in report_data.meta._email
        rec = db_v2.get_report(conn, rid)
        data = (rec or {}).get("report_data") or {}
        data.setdefault("meta", {})["_email"] = "teamtest@example.com"
        with conn.cursor() as c:
            c.execute("UPDATE reports SET report_data=%s, created_at=%s WHERE id=%s",
                      (json.dumps(data), "2999-07-01 00:00:00", rid))
        conn.commit()
    finally:
        conn.close()
    before = client.get(f"/api/admin/overview?key={KEY}").json()
    row_b = next(r for r in before["reports"] if r["rid"] == rid)
    assert row_b["is_test"] is False
    store.team_add(api.db, "email", "teamtest@example.com", "QA email")
    try:
        after = client.get(f"/api/admin/overview?key={KEY}").json()
        row_a = next(r for r in after["reports"] if r["rid"] == rid)
        assert row_a["is_test"] is True
        assert row_a["exclude_reason"] == "team"
    finally:
        store.team_remove(api.db, "teamtest@example.com")
