"""Report-page cleanup regression tests.

The "Gift a friend" referral section was removed from every report template
(owner-confirmed), and the "Account created" banner CARD was removed from the
served report chrome (the auto-hiding toast stays). These tests pin both
removals on paid EN and HI milan reports and on a marriage report.

The legacy /match Hinglish funnel must still 301 to /en/compatibility
preserving the query string, so already-issued /match?pass=<token> unlock
links (and old PDFs whose CTA pointed at /match) keep working.
"""

MILAN = {"p1_name": "Ravi", "p1_dob": "1995-08-15", "p1_tob": "10:30",
         "p1_place": "Delhi",
         "p2_name": "Priya", "p2_dob": "1996-01-20", "p2_tob": "14:00",
         "p2_place": "Mumbai"}

KUNDLI = {"name": "Gift Tester", "dob": "1990-05-10", "tob": "09:20",
          "time_quality": "T0", "place": "Delhi", "gender": "male"}


def _paid_milan_report_html(client, variant):
    r = client.post("/api/milan", json={**MILAN, "variant": variant})
    assert r.status_code == 200, r.text
    rid = r.json()["report_id"]
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    page = client.get(f"/report/{rid}")
    assert page.status_code == 200
    return page.text


def _paid_marriage_report_html(client):
    r = client.post("/api/kundli", json=KUNDLI)
    assert r.status_code == 200, r.text
    rid = r.json()["report_id"]
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    page = client.get(f"/report/{rid}")
    assert page.status_code == 200
    return page.text


def _assert_no_gift_no_banner(html):
    # gift/referral section gone
    assert "refbtn" not in html
    assert "refbox" not in html
    assert "Gift a friend" not in html
    assert "Start a reading" not in html
    # account banner card gone; the toast JS snippet is still shipped
    assert "acct-banner" not in html
    assert "Saved from this purchase" not in html
    assert "axs_acct_toast_" in html


def test_en_milan_report_has_no_gift_section_or_banner(client):
    html = _paid_milan_report_html(client, "/en/compatibility")
    _assert_no_gift_no_banner(html)


def test_hi_milan_report_has_no_gift_section_or_banner(client):
    html = _paid_milan_report_html(client, "/hi/compatibility")
    _assert_no_gift_no_banner(html)
    # localised gift copy gone too
    assert "गिफ़्ट" not in html
    assert "एक रीडिंग शुरू करें" not in html


def test_marriage_report_has_no_gift_section_or_banner(client):
    html = _paid_marriage_report_html(client)
    _assert_no_gift_no_banner(html)


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
