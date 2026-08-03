"""Integration tests for the feature endpoints wired via extensions.install."""

KUNDLI = {"name": "Deep User", "dob": "1990-03-21", "tob": "08:15",
          "time_quality": "T0", "place": "Delhi", "gender": "female"}


def _paid_report(client):
    rid = client.post("/api/kundli", json=KUNDLI).json()["report_id"]
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    return rid


def test_i18n_endpoint(client):
    r = client.get("/api/i18n?lang=en")
    assert r.status_code == 200
    body = r.json()
    assert body["lang"] == "en"
    assert body["catalog"]["field.name"] == "Your name"
    assert any(s["code"] == "hi" for s in body["supported"])


def test_deep_analysis_requires_payment_then_works(client):
    rid = client.post("/api/kundli", json=KUNDLI).json()["report_id"]
    assert client.get(f"/api/deep/{rid}").status_code == 402  # payment required
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    r = client.get(f"/api/deep/{rid}")
    assert r.status_code == 200
    body = r.json()
    assert body["sav_total"] == 337                 # ashtakavarga invariant
    assert "D9" in body["divisional"] and "D10" in body["divisional"]
    assert isinstance(body["yogas"], list)


def test_pdf_route_is_gated(client):
    # Unpaid -> 404; paid -> 200 (PDF) or 503 (renderer not installed), never 500
    rid = client.post("/api/kundli", json=KUNDLI).json()["report_id"]
    assert client.get(f"/report/{rid}/pdf").status_code == 404
    client.post(f"/api/_demo_pay/{rid}")
    assert client.get(f"/report/{rid}/pdf").status_code in (200, 503)


def test_pdf_dotext_route_matches_folder_route(client):
    # WhatsApp's approved media template points at /report/{rid}.pdf (Twilio
    # rejects a bare extensionless path segment like '/pdf' at template
    # submission time). This dot-extension address must be gated the same
    # way and return byte-identical content to /report/{rid}/pdf — a past
    # regression silently dropped this route while both test suites stayed
    # green, since nothing exercised this exact URL.
    rid = client.post("/api/kundli", json=KUNDLI).json()["report_id"]
    assert client.get(f"/report/{rid}.pdf").status_code == 404
    client.post(f"/api/_demo_pay/{rid}")
    folder = client.get(f"/report/{rid}/pdf")
    dotext = client.get(f"/report/{rid}.pdf")
    assert dotext.status_code == folder.status_code
    if folder.status_code == 200:
        assert dotext.content == folder.content


def test_admin_reconcile_requires_key(client):
    assert client.post("/api/reconcile").status_code == 403
    assert client.post("/api/reconcile?key=test-stats-key").status_code == 200


# --- Analytics coverage: the report page, /login and static marketing pages all
# carry GA + Meta Pixel + Clarity, and pages that embed the block by hand are not
# double-injected. Guards the gap where server-rendered pages had zero tracking.
_TRACKERS = ("G-NKRQM1HJ97", "2417544725436982", "clarity.ms/tag")


def test_report_page_has_all_trackers(client):
    rid = _paid_report(client)
    html = client.get(f"/report/{rid}").text
    for t in _TRACKERS:
        assert t in html, f"report page missing tracker {t}"
    # Injected exactly once — the Clarity tag must not appear twice.
    assert html.count("clarity.ms/tag") == 1


def test_login_page_has_all_trackers(client):
    html = client.get("/login").text
    for t in _TRACKERS:
        assert t in html, f"login page missing tracker {t}"


def test_static_page_not_double_injected(client):
    # A marketing page already embeds the block by hand; the injector must skip
    # it so page_view / PageView fire once, not twice.
    html = client.get("/en/marriage").text
    assert html.count("clarity.ms/tag") == 1
    assert html.count("fbq('init'") == 1
