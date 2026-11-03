"""Internal editorial QC: the content bank and rendered reports must pass before anything is approved or delivered."""
import copy

import pytest

import mulank_bank as bank
import mulank_content as mc
import mulank_qc as qc
import numerology
import numerology_report as R
from datetime import date

PIN = date(2026, 11, 3)


@pytest.fixture(autouse=True)
def pinned(monkeypatch):
    monkeypatch.setattr(mc, "_today", lambda: PIN)


def _approved_2_1():
    E = numerology.compute_mulank(29, 7, 1990, today=PIN)
    return {k: mc.Entry(mc.OWNER_APPROVED, editor="Editor", approved_by="Owner", approved_on="2026-11-03") for k in mc.required_keys(E)}


def test_the_content_bank_passes_editorial_lint():
    assert qc.lint_bank() == []


def test_lint_catches_flagged_words_placeholders_empty_text_and_substituted_paragraphs():
    b = copy.deepcopy(bank.BANK)
    b["M"]["3"]["themes"] = "healing and stress relief for everyone"
    b["M"]["4"]["style"] = "TODO write this {slot}"
    b["M"]["5"]["want"] = "   "
    para = "The same long paragraph that was written for one pair and must never be reused for another pair here."
    b["PS"]["2-1"]["general"] = para
    b["PS"]["3-3"] = {"general": para, "work": "Something else entirely about this pair of numbers in working life."}
    msgs = " | ".join(f"{w}: {p}" for w, p in qc.lint_bank(b))
    assert "flagged vocabulary" in msgs and "placeholder" in msgs and "empty text" in msgs and "another pair's reading" in msgs


def test_a_complete_production_report_passes_the_report_lint():
    r = R.build_report(29, 7, 1990, "Test Person", today=PIN, registry=_approved_2_1())
    assert qc.lint_report_html(r["html"]) == []


@pytest.mark.parametrize("marker", ["This report does not include a work reading for Mulank 3 in this edition.",
                                    "Sample report", "PENDING EXPERT REVIEW", "This reference is not included for your numbers in this edition."])
def test_lint_flags_incomplete_or_sample_markers(marker):
    doc = '<section class="page"><p>Numerology is a belief system, not a science.</p><p>' + marker + "</p></section>"
    assert any("marker" in p for _, p in qc.lint_report_html(doc, 1))


def test_lint_flags_wrong_card_count_and_missing_disclaimer():
    issues = [p for _, p in qc.lint_report_html('<section class="page"><p>hello</p></section>', 15)]
    assert any("cards" in p for p in issues) and any("disclaimer" in p for p in issues)


def test_production_renderer_refuses_to_deliver_a_report_that_fails_the_guard(monkeypatch):
    monkeypatch.setattr(qc, "INCOMPLETE_MARKERS", qc.INCOMPLETE_MARKERS + ("Your two numbers",))   # simulate a marker appearing in output
    with pytest.raises(R.ContentMissing):
        R.build_report(29, 7, 1990, "Test Person", today=PIN, registry=_approved_2_1())


def test_the_planetary_links_statement_4i_is_allowed_in_a_complete_report():
    # 4i ("does not state a planetary friendship... published tables differ") is approved wording, not an incomplete marker
    assert "does not include" not in bank.row("4i") and not any(m.lower() in bank.row("4i").lower() for m in qc.INCOMPLETE_MARKERS)
