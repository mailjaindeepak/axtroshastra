"""Static guards for the 5 funnel-page UX/correctness fixes (bugs 3–7).

Each of the FOUR funnel pages must carry the SAME fixes:
  - pages/milan.html   (compat, English)  form #milanForm, names p1-name/p2-name
  - pages/milan.hi.html (compat, Hindi)   idem
  - pages/shaadi.html  (marriage, English) form #kundliForm, name f-name
  - pages/shaadi.hi.html (marriage, Hindi) idem

The tests read each page's SOURCE (like tests/test_gazetteer_hi.py) and assert the
markers of every fix are present and the buggy patterns are gone.
"""
import pathlib
import re

import pytest

PAGES_DIR = pathlib.Path(__file__).resolve().parent.parent / "pages"

# (filename, form id, sticky id, [name field ids])
PAGES = [
    ("milan.html", "milanForm", "stickyBar", ["p1-name", "p2-name"]),
    ("milan.hi.html", "milanForm", "stickyBar", ["p1-name", "p2-name"]),
    ("shaadi.html", "kundliForm", "stickyBar", ["f-name"]),
    ("shaadi.hi.html", "kundliForm", "stickyBar", ["f-name"]),
]

IDS = pytest.mark.parametrize("fname,form_id,sticky_id,name_ids", PAGES,
                              ids=[p[0] for p in PAGES])


def _page(name):
    return (PAGES_DIR / name).read_text(encoding="utf-8")


# --------------------------------------------------------------- BUG 3
# The language-switch restore() must NOT carry the previously-created report
# across a switch (its variant/language is stale). No REPORT_ID from saved state.

@IDS
def test_bug3_restore_does_not_carry_report(fname, form_id, sticky_id, name_ids):
    html = _page(fname)
    assert "st.reportId && st.teaser" not in html, fname
    assert "window.REPORT_ID=st.reportId" not in html, fname
    # positive marker: restore() explicitly nulls the report after a switch
    assert "window.REPORT_ID=null" in html, fname
    assert "window.__teaserData=null" in html, fname


# --------------------------------------------------------------- BUG 4
# The name field id(s) are excluded from the language-switch restore, while
# dob/time/place/city are still restored.

@IDS
def test_bug4_name_excluded_from_switch_restore(fname, form_id, sticky_id, name_ids):
    html = _page(fname)
    assert "SKIP_ON_SWITCH" in html, fname
    # the restore loop skips the flagged ids
    assert "if(SKIP_ON_SWITCH[id]) return;" in html, fname
    for nid in name_ids:
        assert "'%s':1" % nid in html, "%s missing %s in SKIP_ON_SWITCH" % (fname, nid)
    # a non-name field (place) is still in the restore ID list
    place = "p1-place" if form_id == "milanForm" else "f-place"
    assert place in html, fname


# --------------------------------------------------------------- BUG 5
# startPayment ALWAYS opens the contact modal — no early skip when a saved
# contact exists, and the sessionStorage number is not used to bypass it.

@IDS
def test_bug5_startpayment_always_asks_contact(fname, form_id, sticky_id, name_ids):
    html = _page(fname)
    # the old "skip popup when a contact already exists" guard is gone
    assert "if(!AX_CONTACT){ axContactModal(startPayment); return; }" not in html, fname
    # per-click confirmation flag drives a single modal open per unlock
    assert "__axContactConfirmed" in html, fname
    assert "axContactModal(function(){ window.__axContactConfirmed = true; startPayment(); });" in html, fname


# --------------------------------------------------------------- BUG 6
# The paid-report recovery banner has a close control AND auto-hides.

@IDS
def test_bug6_banner_close_and_autohide(fname, form_id, sticky_id, name_ids):
    html = _page(fname)
    # a × close button exists inside the banner markup
    assert ">×</button>" in html, fname
    # auto-hide timer (~8s) and its handler
    assert "__axCloseBanner" in html, fname
    assert "setTimeout(__axCloseBanner, 8000)" in html, fname
    # keeps the "view it here" link (english) / "यहाँ देख" (hindi)
    assert ("view it here" in html) or ("यहाँ देख" in html), fname
    # the old header-covering banner (no close, never hides) is gone
    assert "position:fixed;top:0;left:0;right:0;background:#2E7D53;color:#fff;padding:10px 16px" not in html, fname


# --------------------------------------------------------------- BUG 7
# The sticky ₹499 bar is hidden while a form field is focused (keyboard open)
# and restored on blur, without breaking the scroll-reveal behaviour.

@IDS
def test_bug7_sticky_hidden_on_focus(fname, form_id, sticky_id, name_ids):
    html = _page(fname)
    assert ".sticky.kbd{display:none!important}" in html, fname
    assert "sticky.classList.add('kbd')" in html, fname
    assert "sticky.classList.remove('kbd')" in html, fname
    # focusin/focusout handlers exist on the form
    assert "focusout" in html, fname
    assert "addEventListener('focusin'" in html, fname
    # scroll-reveal behaviour is preserved
    assert "sticky.hidden = window.scrollY" in html, fname


# --------------------------------------------------------------- integrity

@IDS
def test_pages_have_balanced_script_tags(fname, form_id, sticky_id, name_ids):
    html = _page(fname)
    opens = len(re.findall(r"<script\b", html))
    closes = html.count("</script>")
    assert opens == closes, "%s: %d <script> vs %d </script>" % (fname, opens, closes)


@IDS
def test_pages_have_required_ids(fname, form_id, sticky_id, name_ids):
    html = _page(fname)
    assert 'id="%s"' % form_id in html, fname
    assert 'id="%s"' % sticky_id in html, fname
    for nid in name_ids:
        assert 'id="%s"' % nid in html, "%s missing id=%s" % (fname, nid)
    # unlock button + payment/contact entry points still present
    assert "startPayment" in html, fname
    assert "axContactModal" in html, fname
