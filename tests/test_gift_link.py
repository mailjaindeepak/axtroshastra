"""Gift-a-friend CTA regression tests (T4).

The milan v2 report's referral button ("Gift a friend their reading") must
target the live, language-matched funnel with an ABSOLUTE url — root-relative
hrefs die inside the Chrome-rendered PDF (file:///match) — and the legacy
/match Hinglish funnel must 301 to /en/compatibility preserving the query
string so already-issued /match?pass=<token> unlock links keep working.
"""

MILAN = {"p1_name": "Ravi", "p1_dob": "1995-08-15", "p1_tob": "10:30",
         "p1_place": "Delhi",
         "p2_name": "Priya", "p2_dob": "1996-01-20", "p2_tob": "14:00",
         "p2_place": "Mumbai"}

ORIGIN = "https://www.axtroshastra.com"   # PUBLIC_BASE_URL fallback in milan_v2


def _paid_milan_report_html(client, variant):
    r = client.post("/api/milan", json={**MILAN, "variant": variant})
    assert r.status_code == 200, r.text
    rid = r.json()["report_id"]
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    page = client.get(f"/report/{rid}")
    assert page.status_code == 200
    return page.text


def test_gift_cta_targets_english_funnel_on_en_report(client):
    html = _paid_milan_report_html(client, "/en/compatibility")
    assert f'<a class="refbtn" href="{ORIGIN}/en/compatibility">' in html
    assert 'href="/match"' not in html
    assert "Start a reading" in html          # visible copy unchanged


def test_gift_cta_targets_hindi_funnel_on_hi_report(client):
    html = _paid_milan_report_html(client, "/hi/compatibility")
    assert f'<a class="refbtn" href="{ORIGIN}/hi/compatibility">' in html
    assert 'href="/match"' not in html
    # the localiser swaps the label text but must never touch the href
    assert "एक रीडिंग शुरू करें" in html


def test_match_redirects_to_en_compatibility(client):
    r = client.get("/match", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "/en/compatibility"


def test_match_redirect_preserves_pass_query(client):
    r = client.get("/match?pass=tok123", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "/en/compatibility?pass=tok123"


def test_compatibility_funnels_serve_200(client):
    assert client.get("/en/compatibility").status_code == 200
    assert client.get("/hi/compatibility").status_code == 200
