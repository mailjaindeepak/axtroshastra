"""OTP login + session layer. Twilio Verify is not configured in the test env, so
`auth` uses its dev-code fallback (code stored in login_otps, surfaced via
DEMO_MODE). We exercise: request -> verify -> session cookie -> /api/me -> the
/account dashboard -> logout, plus the guards (wrong code, expiry, gating)."""
import api
import auth


def _request(client, mobile="9876500001"):
    r = client.post("/api/auth/request-otp", json={"mobile": mobile})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] and body["channel"] == "dev"
    assert body.get("dev_code"), "dev_code should be surfaced under DEMO_MODE"
    return body["dev_code"]


def _login(client, mobile="9876500001"):
    code = _request(client, mobile)
    r = client.post("/api/auth/verify-otp", json={"mobile": mobile, "code": code})
    assert r.status_code == 200, r.text
    return r


def test_full_login_flow_sets_session(client):
    r = _login(client, "9876500010")
    assert r.json()["ok"] is True
    assert auth.SESSION_COOKIE in r.cookies
    # session now works
    me = client.get("/api/me")
    assert me.status_code == 200
    assert me.json()["user"]["mobile"] == "+919876500010"
    assert me.json()["reports"] == []


def test_wrong_code_rejected(client):
    _request(client, "9876500020")
    r = client.post("/api/auth/verify-otp",
                    json={"mobile": "9876500020", "code": "000000"})
    assert r.status_code == 401


def test_account_page_requires_session(client):
    client.post("/api/auth/logout")            # ensure logged out
    r = client.get("/account", follow_redirects=False)
    assert r.status_code == 302
    # carries the destination so login can bounce straight back
    assert r.headers["location"] == "/login?next=%2Faccount"


def test_account_page_shows_details_when_logged_in(client):
    _login(client, "9876500030")
    r = client.get("/account")
    assert r.status_code == 200
    assert "Your Details" in r.text
    assert "+91 98765 00030" in r.text          # formatted mobile from the DB
    assert "axs-nav" in r.text                    # hamburger nav injected


def test_logout_clears_session(client):
    _login(client, "9876500040")
    assert client.get("/api/me").status_code == 200
    client.post("/api/auth/logout")
    assert client.get("/api/me").status_code == 401


def test_login_creates_account_for_new_number(client):
    """Logging in with a number that never purchased still creates the account
    (idempotent upsert) so a first-time visitor gets a home."""
    mobile = "9876500050"
    _login(client, mobile)
    me = client.get("/api/me").json()
    assert me["user"]["mobile"] == "+919876500050"


def test_login_surfaces_prior_paid_reports(client):
    """A report already linked to this mobile's account shows up on the dashboard."""
    mobile = "+919876500060"
    uid = api.users.upsert_user_from_payment(api.db, mobile=mobile, name="Prior Buyer")
    # a paid report owned by that user
    rid = "r_authtest_1"
    with api.db() as c:
        c.execute("INSERT INTO reports(id,payload,paid,phone,user_id,created_at) "
                  "VALUES(?,?,?,?,?,?)",
                  (rid, api.json.dumps({"product": "milan",
                                        "meta": {"p1": "A", "p2": "B"}}),
                   1, mobile, uid, "2026-07-01T00:00:00"))
    _login(client, "9876500060")
    me = client.get("/api/me").json()
    ids = [x["id"] for x in me["reports"]]
    assert rid in ids
    # and it renders on the /account page
    assert "Kundli Milan" in client.get("/account").text


def test_nav_injected_on_marketing_pages(client):
    for path in ("/", "/about", "/privacy"):
        html = client.get(path).text
        assert "axs-nav" in html, f"nav missing on {path}"
        assert 'href="/account"' in html and 'href="/blog"' in html
