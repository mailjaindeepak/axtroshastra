"""Guards for the premium free-teaser preview on the compatibility funnel.

The free teaser now shows a real GLIMPSE of the paid report: the actual match
score, the "one breath" one-line summary, and the top theme cards. Two things
must hold:

1. The one-breath summary is a single source of truth (report_view.milan_one_breath)
   reused by BOTH the full report render and the teaser — they must not drift.
2. The teaser exposes the score/themes/one-breath for the preview WITHOUT leaking
   the paid depth (per-koota detail, action plan, dosha verdicts).
"""
import products
import milan_v2
from report_view import milan_one_breath

P1 = {"name": "Asha", "dob": "1992-04-15", "tob": "08:30", "tz": 5.5,
      "lat": 28.61, "lon": 77.20, "gender": "female"}
P2 = {"name": "Vikram", "dob": "1990-11-02", "tob": "21:10", "tz": 5.5,
      "lat": 19.07, "lon": 72.87, "gender": "male"}


def test_teaser_reveals_real_score_and_summary():
    p = products.compute_milan(P1, P2)
    t = p["teaser"]
    # score is now revealed (the hook), not blurred/locked
    assert t["score_locked"] is False
    assert t["match_pct"] == p["match_pct"]
    assert 0 <= t["match_pct"] <= 100
    assert t["verdict"]                       # verdict word present
    assert t["strongest"]                     # strongest theme named
    # 2-3 elegant theme cards, strongest first, each with what the UI needs
    assert 2 <= len(t["themes"]) <= 3
    assert t["themes"][0]["name"] == t["strongest"]
    for c in t["themes"]:
        assert set(c) >= {"name", "emoji", "pct", "blurb", "band"}
        assert c["band"] in {"strong", "solid", "grow"}


def test_one_breath_is_single_source_of_truth():
    """The teaser's one-breath text must be exactly what milan_one_breath()
    produces from the same kootas — so report and preview never diverge."""
    p = products.compute_milan(P1, P2)
    assert p["teaser"]["one_breath"] == milan_one_breath(p["kootas"])
    # html variant bolds key phrases and is used verbatim in the report render
    html = milan_one_breath(p["kootas"], html=True)
    assert "<b>" in html
    assert milan_v2.render_milan_v2(p).count(html) == 1


def test_teaser_does_not_leak_paid_depth():
    """The preview shows quality, not the paid detail: no per-koota scores,
    friction points, action plan or dosha verdicts in the teaser payload."""
    t = products.compute_milan(P1, P2)["teaser"]
    leaked = {"kootas", "watchouts", "cancellations", "manglik", "notes",
              "effective", "total", "profiles"}
    assert not (set(t) & leaked), f"teaser leaks paid depth: {set(t) & leaked}"
