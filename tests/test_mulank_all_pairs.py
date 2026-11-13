"""Content completeness for every Mulank-Bhagyank combination (all 81) across every Personal Year (1-9).

The shipped ledger approves every key (owner, 4 Nov 2026). These tests use a clearly-test registry (every required key owner-approved) so they
prove that the DRAFTED TEXT is complete for every combination, independent of the ledger, and that the production renderer, the editorial QC and
the PDF engine all accept it. The "not approved" cases use an explicit empty ledger, never the shipped one.
Set MULANK_PDF_ALL=1 to render all 81 PDFs with Chrome; by default a spread of combinations covering every Mulank, Bhagyank and Personal Year is rendered."""
import os
import re
from datetime import date

import pytest

import mulank_content as mc
import mulank_qc as qc
import numerology
import numerology_report as R
import pdfgen

PIN = date(2026, 11, 3)
YEARS = range(2026, 2035)                       # nine consecutive calendar years: current Personal Year takes every value 1-9


@pytest.fixture(autouse=True)
def pinned(monkeypatch):
    monkeypatch.setattr(mc, "_today", lambda: PIN)


def _one_dob_per_pair():
    pairs = {}
    for y in range(1950, 2010):
        for m in range(1, 13):
            for d in range(1, 29):
                pairs.setdefault(numerology.compute_mulank(d, m, y, today=PIN)["pair_key"], (d, m, y))
    return pairs


PAIRS = _one_dob_per_pair()


def _approved(dob, today):
    E = numerology.compute_mulank(*dob, today=today)
    return {k: mc.Entry(mc.OWNER_APPROVED, editor="Test Editor", approved_by="Test Owner", approved_on="2026-11-03") for k in mc.required_keys(E)}


def test_every_one_of_the_81_combinations_exists():
    assert len(PAIRS) == 81 and {(int(k.split("-")[0]), int(k.split("-")[1])) for k in PAIRS} == {(m, b) for m in range(1, 10) for b in range(1, 10)}


def test_drafted_text_exists_for_every_key_every_combination_and_year_needs():
    for pk, dob in PAIRS.items():
        for yr in YEARS:
            E = numerology.compute_mulank(*dob, today=date(yr, 11, 3))
            missing = [k for k in mc.required_keys(E) if not mc.has_text(k)]
            assert not missing, (pk, yr, missing)


def test_the_shipped_ledger_opens_every_combination_and_an_empty_one_opens_none():
    for pk, dob in PAIRS.items():
        shipped = mc.pair_readiness(*dob, today=PIN)
        assert shipped["eligible"] is True and shipped["approved"] is True and shipped["complete"] is True and shipped["reason_code"] == "ok", (pk, shipped["missing"])
        empty = mc.pair_readiness(*dob, today=PIN, registry={})
        assert empty["eligible"] is False and empty["complete"] is True and empty["reason_code"] == "content_not_approved", pk
    assert mc.sale_open(today=PIN) is True and mc.sale_open(registry={}, today=PIN) is False


def test_all_81_combinations_build_a_full_15_card_report_for_every_personal_year_and_pass_the_editorial_qc():
    seen_years, problems = set(), []
    for pk, dob in PAIRS.items():
        for yr in YEARS:
            today = date(yr, 11, 3)
            E = numerology.compute_mulank(*dob, today=today)
            seen_years.add(E["personal_year"]["current"]["number"])
            r = R.build_report(*dob, "Test Person", today=today, registry=_approved(dob, today))
            assert r["mode"] == "production" and r["n_cards"] == 15, (pk, yr)
            problems += [(pk, yr, i) for i in qc.lint_report_html(r["html"])]
    assert seen_years == set(range(1, 10))
    assert not problems, problems[:5]


def test_no_combination_borrows_another_combinations_text_and_each_report_is_distinct():
    htmls = {}
    for pk, dob in PAIRS.items():
        h = R.build_report(*dob, "Test Person", today=PIN, registry=_approved(dob, PIN))["html"]
        assert len(re.findall(r'<section class="page', h)) == 15
        htmls[pk] = h
    assert len(set(htmls.values())) == 81


def test_the_only_way_to_a_production_report_is_approval_and_text_never_a_fallback():
    for pk in ("1-1", "9-9", "2-1", "5-8"):
        dob = PAIRS[pk]
        with pytest.raises(R.ReportNotAvailable):
            R.build_report(*dob, "Test Person", today=PIN, registry={})                    # nothing approved
        reg = _approved(dob, PIN)
        reg.pop("PM" + pk.split("-")[0])
        with pytest.raises(R.ReportNotAvailable):
            R.build_report(*dob, "Test Person", today=PIN, registry=reg)                   # one approval missing


# ------------------------------------------------------------------ PDF generation (Chrome)
def _pdf_pages(pdf: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page(?![s\w])", pdf))


def _spread():
    """"Every fourth combination (21 of 81, covering every Mulank and Bhagyank), each in a different calendar year."""
    return [(pk, YEARS[k % 9]) for k, pk in enumerate(sorted(PAIRS)[::4])]


@pytest.mark.skipif(not pdfgen.chrome_bin(), reason="no Chrome available (set CHROME_BIN)")
def test_pdf_generation_for_all_pairs_and_personal_years():
    cases = [(pk, YEARS[(i % 9)]) for i, pk in enumerate(sorted(PAIRS))] if os.getenv("MULANK_PDF_ALL") == "1" else _spread()
    assert {int(pk.split("-")[0]) for pk, _ in cases} == set(range(1, 10)) and {int(pk.split("-")[1]) for pk, _ in cases} == set(range(1, 10))
    years = set()
    for pk, yr in cases:
        today = date(yr, 11, 3)
        dob = PAIRS[pk]
        years.add(numerology.compute_mulank(*dob, today=today)["personal_year"]["current"]["number"])
        html = R.build_report(*dob, "Test Person", today=today, registry=_approved(dob, today))["html"]
        pdf = pdfgen.generate(html)
        assert pdf and pdf[:5] == b"%PDF-", pk
        assert _pdf_pages(pdf) == 15, (pk, yr, _pdf_pages(pdf))
    assert years == set(range(1, 10))
