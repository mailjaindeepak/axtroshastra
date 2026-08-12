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


def _make_paid(rid, deliver_phone, pay_phone="9111100001", variant="/milan"):
    """Directly stamp a report paid with a distinct popup (delivery) number vs
    the Razorpay (pay) number, via the app's own module-level helpers."""
    api.store_user_contact(rid, phone=deliver_phone)   # -> reports.user_phone
    api.mark_paid(rid, payment_id="pay_" + rid[:8], phone=pay_phone)  # -> reports.phone
    # tag the funnel variant so the price/label logic has something to read
    with api._lock, api.db() as c:
        row = c.execute("SELECT payload FROM reports WHERE id=?", (rid,)).fetchone()
        payload = json.loads(row[0])
        payload.setdefault("meta", {})["variant"] = variant
        c.execute("UPDATE reports SET payload=? WHERE id=?", (json.dumps(payload), rid))


# 1. plugin did not break the site --------------------------------------------
def test_site_still_serves_existing_route(client):
    assert client.get("/healthz").status_code == 200
    assert client.get("/en/compatibility").status_code == 200


# 2. every admin surface is locked without / with a wrong key ------------------
def test_admin_routes_locked_without_key(client):
    for path in ("/api/admin/overview", "/api/admin/deliveries",
                 "/api/admin/customers", "/api/admin/customer?phone=9",
                 "/api/admin/config"):
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
        c.execute("UPDATE reports SET created_at=? WHERE id=?", ("2000-01-01T00:00:00", r_old))
        c.execute("UPDATE reports SET created_at=? WHERE id=?", ("2999-01-01T00:00:00", r_new))
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
        c.execute("UPDATE reports SET created_at=? WHERE id=?", ("2999-06-01T00:00:00", rid))
    before = client.get(f"/api/admin/overview?key={KEY}").json()
    row_before = next(r for r in before["reports"] if r["rid"] == rid)
    assert row_before["is_test"] is False           # a real customer, for now
    rev_before = before["totals"]["revenue_inr"]
    # add the delivery number to the team allowlist (formatting-insensitive)
    r = client.post(f"/api/admin/team?key={KEY}&pass={KEY}",
                    json={"kind": "phone", "value": "+91 93123-00071", "label": "Dev"})
    assert r.status_code == 200 and r.json()["ok"] is True
    after = client.get(f"/api/admin/overview?key={KEY}").json()
    row = next(r for r in after["reports"] if r["rid"] == rid)
    assert row["is_test"] is True
    assert row["exclude_reason"] == "team"
    assert after["totals"]["revenue_inr"] == rev_before - 499   # dropped from revenue
    # cleanup so the shared DB doesn't carry the entry into other tests
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


# 12. OTP login log: gated, phone masked, NEVER exposes the code --------------
def _seed_otp(mobile, vid="", attempts=0, minutes_ahead=5):
    from datetime import datetime, timedelta
    exp = (datetime.utcnow() + timedelta(minutes=minutes_ahead)).isoformat()
    with api._lock, api.db() as c:
        c.execute("DELETE FROM login_otps WHERE mobile=?", (mobile,))
        c.execute("INSERT INTO login_otps(mobile,code_hash,mc_verification_id,"
                  "expires_at,attempts) VALUES(?,?,?,?,?)",
                  (mobile, "SECRETHASH", vid, exp, attempts))


def test_otp_logins_requires_key(client):
    assert client.get("/api/admin/otp_logins").status_code == 403
    assert client.get("/api/admin/otp_logins?key=wrong").status_code == 403


def test_otp_logins_masks_phone_and_never_returns_code(client):
    _seed_otp("+919876500011", vid="vid-abc", attempts=1)
    d = client.get(f"/api/admin/otp_logins?key={KEY}").json()
    assert "logins" in d and d["logins"]
    row = next(r for r in d["logins"] if r["phone_masked"].endswith("11"))
    # only the last 2 digits are revealed — the full number never appears
    assert "9876500011" not in row["phone_masked"]
    assert row["phone_masked"].endswith("11")
    assert row["provider"] == "Message Central"     # mc_verification_id present
    # the response must carry NO code / code_hash — not as a field, not anywhere
    assert "code" not in row and "code_hash" not in row
    assert "SECRETHASH" not in json.dumps(d)
    # cost estimate present and clearly flagged estimated
    assert d["cost_estimate"]["estimated"] is True
    assert d["month_count"] >= 1


def test_otp_logins_count_reflects_seeded_rows(client):
    _seed_otp("+919000000031")
    _seed_otp("+919000000032")
    d = client.get(f"/api/admin/otp_logins?key={KEY}").json()
    masks = [r["phone_masked"] for r in d["logins"]]
    assert any(m.endswith("31") for m in masks)
    assert any(m.endswith("32") for m in masks)
    assert d["month_count"] >= 2


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
    assert fp["pixel_id"] == "2417544725436982"
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
    api.mark_paid(rid, payment_id="pay_payonly", phone="9700000401")
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
