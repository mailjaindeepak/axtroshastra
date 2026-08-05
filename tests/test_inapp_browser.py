"""In-app-browser (Instagram / Facebook / TikTok WebView) handling on the served
report page.

Reports are opened a lot from Instagram/FB links, which force a restricted
WebView where (a) the blob-based "Download PDF" silently fails and (b) wa.me /
external links throw "Page can't be loaded". The report chrome (api.py
_wire_report_chrome) now injects:
  * window.axInApp() UA detection,
  * a dismissible, on-brand "open in your browser" banner (platform-aware,
    Hindi copy on the HI report),
  * an in-app branch in axPdfDl that opens the direct /pdf URL instead of the
    blob, plus a tappable direct-PDF fallback link,
  * an axShare clipboard fallback.

These are static guards over the SERVED report HTML (paid via the demo-pay
helper), in the style of tests/test_funnel_bug_fixes.py / test_hindi_leakage.py.
"""

KUNDLI = {"name": "Inapp Tester", "dob": "1992-03-15", "tob": "11:40",
          "time_quality": "T0", "place": "Delhi", "gender": "female"}


def _served_report(client, variant, phone):
    r = client.post("/api/kundli", json={**KUNDLI, "variant": variant})
    assert r.status_code == 200, r.text
    rid = r.json()["report_id"]
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    html = client.get(f"/report/{rid}").text
    return html


def _report_en(client):
    return _served_report(client, "/en/marriage", "+919812300011")


def _report_hi(client):
    return _served_report(client, "/hi/marriage", "+919812300012")


# --------------------------------------------------------------- detection
def test_inapp_detection_helper_present(client):
    html = _report_en(client)
    assert "window.axInApp=function" in html
    # the common in-app WebViews are all matched
    for token in ("Instagram", "FBAN", "FBAV", "FB_IAB",
                  "Snapchat", "musical_ly", "BytedanceWebview", "Line", "Twitter"):
        assert token in html, "UA token %s missing from axInApp" % token


# --------------------------------------------------------------- banner (EN)
def test_inapp_banner_markup_and_logic_en(client):
    html = _report_en(client)
    assert "b.className='ax-inapp'" in html            # banner container
    assert "Open in your browser for the best experience" in html
    assert "axs_inapp_dismiss" in html                # dismissible + guarded
    assert 'class="ax-inapp-x"' in html               # dismiss control
    # platform-aware steps (Android ⋮ / iOS •••)
    assert "Open in Chrome" in html
    assert "Open in browser" in html
    # only shows when an in-app browser is detected
    assert "var app=window.axInApp();if(!app)return;" in html
    # direct-PDF fallback link, opened in a new tab
    assert 'class="ax-inapp-pdf"' in html
    assert "or open the PDF directly" in html
    assert 'target="_blank"' in html


# --------------------------------------------------------------- banner (HI)
def test_inapp_banner_hindi_copy(client):
    html = _report_hi(client)
    assert "b.className='ax-inapp'" in html
    # Hindi copy shipped, English shell copy gone
    assert "बेहतर अनुभव के लिए अपने ब्राउज़र में खोलें" in html
    assert "Open in your browser for the best experience" not in html
    assert "या PDF सीधे खोलें" in html                 # direct-PDF link (HI)
    assert "बंद करें" in html                          # dismiss (HI)
    # detection + guard logic still present on the HI report
    assert "window.axInApp=function" in html
    assert "axs_inapp_dismiss" in html


# --------------------------------------------------------------- download fix
def test_download_has_inapp_direct_pdf_branch(client):
    for html in (_report_en(client), _report_hi(client)):
        # axPdfDl branches on the in-app detector and opens the DIRECT /pdf URL
        assert "if(window.axInApp&&window.axInApp())" in html
        assert "location.pathname.replace(/\\/+$/,'')+'/pdf'" in html
        assert "window.open(pu,'_blank')" in html
        # the normal-browser blob download is NOT regressed (still present)
        assert "URL.createObjectURL" in html
        assert "a.download=" in html


# --------------------------------------------------------------- share fallback
def test_inapp_share_clipboard_fallback(client):
    html = _report_en(client)
    assert "navigator.clipboard" in html
    assert "Report link copied" in html


# --------------------------------------------------------------- balanced <script>
def test_report_script_tags_balanced(client):
    for html in (_report_en(client), _report_hi(client)):
        opens = html.count("<script")
        closes = html.count("</script>")
        assert opens == closes, "unbalanced <script> tags: %d open / %d close" % (opens, closes)
