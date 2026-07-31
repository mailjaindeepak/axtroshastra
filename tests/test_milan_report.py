"""Regression guards for the compatibility (milan) report render.

Bug 1 (calc display): the appendix showed "{raw_sum}/36 → {pct}%", but pct is the
EFFECTIVE score after dosha cancellation, so the line was mathematically false
whenever a dosha was cancelled (e.g. 18.0/36 shown as 72%, when 72% is 26/36).

Bug 2 (share): "Share on WhatsApp" shared only the text, never the report link,
so recipients got a score with no way to open the report.
"""
import re

import products
import milan_v2

# Fixed lat/lon/tz so the engine is deterministic and needs no geocoding.
P1 = {"name": "Asha", "dob": "1992-04-15", "tob": "08:30", "tz": 5.5,
      "lat": 28.61, "lon": 77.20, "gender": "female"}
P2 = {"name": "Vikram", "dob": "1990-11-02", "tob": "21:10", "tz": 5.5,
      "lat": 19.07, "lon": 72.87, "gender": "male"}


def _render():
    p = products.compute_milan(P1, P2)
    p.setdefault("meta", {})["report_id"] = "TESTRID"
    return milan_v2.render_milan_v2(p), p


def test_total_equation_percentage_matches_its_fraction():
    """The final 'N/36 = P%' in the appendix total bar must actually satisfy
    P == round(N/36*100), and equal the engine's headline match_pct."""
    html, p = _render()
    m = re.search(r'<div class="total">(.*?)</div>', html, re.S)
    assert m, "no .total equation block found"
    text = re.sub(r"<[^>]+>", "", m.group(1))          # strip inner tags
    pairs = re.findall(r"([\d.]+)/36 = (\d+)%", text)
    assert pairs, f"no 'N/36 = P%' equality in total bar: {text!r}"
    n, pcent = float(pairs[-1][0]), int(pairs[-1][1])
    assert pcent == round(n / 36 * 100), \
        f"{n}/36 displayed as {pcent}% (should be {round(n / 36 * 100)}%): {text!r}"
    assert pcent == p["match_pct"], "displayed % must equal the engine match_pct"


def test_share_button_shares_the_live_report_url():
    """The WhatsApp share must attach the current report URL, not text only."""
    html, _ = _render()
    assert "location.href" in html and "encodeURIComponent" in html, \
        "share button must build the URL from the live page"
    # the old text-only share link must be gone
    assert "wa.me/?text=Our%20Kundli" not in html
