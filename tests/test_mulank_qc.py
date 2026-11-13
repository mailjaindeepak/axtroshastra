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


# ---------------------------------------------------------------- release gate (R1)
def test_lint_scans_the_wording_rows_for_notes_empty_text_and_flagged_words():
    b = copy.deepcopy(bank.BANK)
    b["rows"]["10a"] = "NO CHANGE"
    b["rows"]["12a"] = "(deleted; repeats card 12)"
    b["rows"]["8g_one"] = "   "
    b["rows"]["13c"] = "Gentle advice for your health."
    b["rows"]["4e_text"] = "Heading: Planetary links. Text: {X} counts {Y} as {labXY}."
    msgs = {w: p for w, p in qc.lint_bank(b)}
    assert "editing note" in msgs["rows/10a"] and "editing note" in msgs["rows/12a"] and "editing note" in msgs["rows/4e_text"]
    assert msgs["rows/8g_one"] == "empty text" and "flagged vocabulary" in msgs["rows/13c"]
    assert "rows/4e_text" in msgs and not any(w == "rows/11a" for w in msgs)           # slots such as {X} are fine in rows; notes are not


def test_the_renderer_never_splits_a_wording_row():
    """Rows hold final customer text only. Splitting a row on an editing note is what once made a reworded row break a paid report."""
    import pathlib
    import re
    src = pathlib.Path(R.__file__).read_text(encoding="utf-8")
    assert not re.search(r'row\([^)]*\)\s*\.split\(', src)
    assert not re.search(r'\bg\.split\(|\.split\("Text: ', src)


def test_leftover_slots_and_notes_fail_the_release_gate_but_not_the_runtime_guard():
    doc = ('<section class="page"><p>Numerology is a belief system, not a science.</p>'
           '<p>Your Personal Year {n1} matches. NO CHANGE</p></section>')
    gate = [p for _, p in qc.lint_report_html(doc, 1, slots=True)]
    assert any("slot" in p for p in gate) and any("note" in p for p in gate)
    assert qc.lint_report_html(doc, 1) == []                                          # runtime guard unchanged (a name may hold a brace)


def _one_dob_per_pair(today):
    seen = {}
    for y in range(1950, 2010):
        for m in range(1, 13):
            for d in range(1, 29):
                seen.setdefault(numerology.compute_mulank(d, m, y, today=today)["pair_key"], (d, m, y))
    assert len(seen) == 81
    return list(seen.values())


@pytest.mark.parametrize("today", [PIN, date(2026, 12, 31), date(2027, 1, 1)])
def test_all_81_pairs_pass_the_release_gate(today):
    """Every pair renders 15 cards with no leftover slot, editing note, fallback or sample marker, with the shipped ledger,
    across the year boundary too (personal years change on 1 January). Also: no mock persona may reach a real report (CLAUDE.md 22)."""
    for dob in _one_dob_per_pair(today):
        h = R.build_report(*dob, "Test Person", today=today)["html"]
        assert qc.lint_report_html(h, 15, slots=True) == [], dob
        assert "Kiran Mehta" not in h and "29 July 1990" not in h, dob


def test_changing_the_content_bank_requires_a_content_version_bump():
    """Release gate: edit mulank_bank.json, then bump CONTENT_VERSION (mulank_content.py) and update mulank_content_version.json,
    so every delivered report records which wording produced it."""
    import hashlib
    import json
    import pathlib
    rec = json.loads((pathlib.Path(mc.__file__).parent / "mulank_content_version.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256(json.dumps(bank.BANK, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
    assert rec["content_version"] == mc.CONTENT_VERSION, "CONTENT_VERSION and mulank_content_version.json disagree"
    assert rec["bank_sha256"] == digest, "mulank_bank.json changed: bump CONTENT_VERSION and update mulank_content_version.json"


def test_the_planetary_links_statement_4i_is_allowed_in_a_complete_report():
    # 4i ("does not state a planetary friendship... published tables differ") is approved wording, not an incomplete marker
    assert "does not include" not in bank.row("4i") and not any(m.lower() in bank.row("4i").lower() for m in qc.INCOMPLETE_MARKERS)
