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
_TRACKERS = ("G-NKRQM1HJ97", "1454249773521031", "clarity.ms/tag")


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


def test_pixel_id_split_by_domain(client):
    # Same app, two domains: .com keeps its pixel, .in requests get theirs
    # swapped in by the _pixel_by_domain middleware. Any other host (including
    # the TestClient default) behaves like .com.
    com = client.get("/", headers={"host": "www.axtroshastra.com"}).text
    assert "1454249773521031" in com and "4575834769362738" not in com

    for host in ("axtroshastra.in", "www.axtroshastra.in"):
        html = client.get("/", headers={"host": host}).text
        assert "4575834769362738" in html, f"{host} missing .in pixel"
        assert "1454249773521031" not in html, f"{host} leaked .com pixel"


def test_linkedin_removed_on_in_only(client):
    # LinkedIn (Insight Tag + the fbq-wrapping bridge) stays on .com but is
    # stripped from .in, so .in's window.fbq is left native.
    com = client.get("/", headers={"host": "www.axtroshastra.com"}).text
    assert "snap.licdn.com" in com and "lintrk" in com

    for host in ("axtroshastra.in", "www.axtroshastra.in"):
        html = client.get("/", headers={"host": host}).text
        assert "snap.licdn.com" not in html, f"{host} still has LinkedIn tag"
        assert "lintrk" not in html, f"{host} still has LinkedIn bridge"
        assert "AXLI-START" not in html, f"{host} left marker behind"
