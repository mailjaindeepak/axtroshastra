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
    # and it renders on the /account page (milan label is "Compatibility Report")
    assert "Compatibility Report" in client.get("/account").text


def test_account_name_update_requires_session(client):
    """POST /api/account/name is session-gated — no cookie -> 401, no write."""
    client.post("/api/auth/logout")
    r = client.post("/api/account/name", json={"name": "Hacker"})
    assert r.status_code == 401


def test_account_name_update_persists(client):
    """A logged-in user can set their own name and it persists to the DB and
    renders on the /account page (name is user-editable, never auto-set)."""
    mobile = "9876500070"
    _login(client, mobile)
    r = client.post("/api/account/name", json={"name": "  Deepak Jain  "})
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    # persisted (trimmed) — visible via /api/me and on the dashboard
    me = client.get("/api/me").json()
    assert me["user"]["name"] == "Deepak Jain"
    acct = client.get("/account").text
    assert 'value="Deepak Jain"' in acct           # prefilled in the edit form
    assert "Namaste, Deepak Jain" in acct          # greeting uses the saved name


def test_account_page_shows_name_placeholder_when_blank(client):
    """A user with no name set sees a placeholder prompting them to add one,
    plus the edit form — not a blank/leftover value."""
    _login(client, "9876500071")
    html = client.get("/account").text
    assert 'placeholder="Your name"' in html
    assert "Add your name" in html                 # explicit prompt, not empty


def test_nav_injected_on_marketing_pages(client):
    for path in ("/", "/about", "/privacy"):
        html = client.get(path).text
        assert "axs-nav" in html, f"nav missing on {path}"
        assert 'href="/account"' in html and 'href="/blog"' in html


def test_login_page_serves_without_params(client):
    """Regression: the /login decorator once got attached to a helper with a
    required query param, 422-ing the whole login page. GET /login must serve
    the page with no params, and ?next= must be accepted."""
    client.post("/api/auth/logout")
    r = client.get("/login")
    assert r.status_code == 200
    assert "Send OTP" in r.text
    r = client.get("/login?next=%2Faccount")
    assert r.status_code == 200


def test_mc_send_hits_v3_send_with_contract_params(monkeypatch):
    """Regression: Message Central 'Verify Now' send must POST to
    /verification/v3/send with a bare 10-digit mobileNumber and the auth token in
    the `authToken` header. A wrong endpoint version (the old v2/verification/send)
    silently delivers no SMS."""
    calls = {}

    def fake_request(method, url, headers):
        calls["method"] = method
        calls["url"] = url
        calls["headers"] = headers
        return {"data": {"verificationId": "vid-123"}}

    monkeypatch.setenv("MESSAGECENTRAL_CUSTOMER_ID", "C123")
    monkeypatch.setenv("MESSAGECENTRAL_AUTH_TOKEN", "static-tok")
    monkeypatch.setattr(auth, "_mc_request", fake_request)

    assert auth._otp_provider() == "messagecentral"
    res = auth._mc_send_otp(api.db, "+919876500099")
    assert res == {"ok": True, "channel": "sms"}

    assert calls["method"] == "POST"
    assert "/verification/v3/send?" in calls["url"]
    assert "/verification/v2/" not in calls["url"]
    assert "mobileNumber=9876500099" in calls["url"]   # bare 10 digits, no +91
    assert "countryCode=91" in calls["url"]
    assert "flowType=SMS" in calls["url"]
    assert calls["headers"].get("authToken") == "static-tok"


def test_mc_validate_hits_v3_validate(monkeypatch):
    """Regression: validate must GET /verification/v3/validateOtp with verificationId."""
    calls = {}

    def fake_request(method, url, headers):
        calls["url"] = url
        return {"data": {"verificationStatus": "VERIFICATION_COMPLETED"}}

    monkeypatch.setenv("MESSAGECENTRAL_CUSTOMER_ID", "C123")
    monkeypatch.setenv("MESSAGECENTRAL_AUTH_TOKEN", "static-tok")
    monkeypatch.setattr(auth, "_mc_request", fake_request)

    mobile = "+919876500098"
    with api.db() as c:
        c.execute("DELETE FROM login_otps WHERE mobile=?", (mobile,))
        c.execute("INSERT INTO login_otps(mobile,code_hash,mc_verification_id,"
                  "expires_at,attempts) VALUES(?,?,?,?,0)",
                  (mobile, "", "vid-xyz", "2999-01-01T00:00:00"))
    assert auth._mc_check_otp(api.db, mobile, "123456") is True
    assert "/verification/v3/validateOtp?" in calls["url"]
    assert "/verification/v2/" not in calls["url"]
    assert "verificationId=vid-xyz" in calls["url"]


def test_login_redirects_when_already_logged_in(client):
    _login(client, "9876500044")
    r = client.get("/login?next=%2Freport%2Fabc", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/report/abc"
    r = client.get("/login?next=//evil.com", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/account"
