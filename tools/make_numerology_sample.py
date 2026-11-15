"""Build the Numerology SAMPLE report that the landing page's "View a sample report" button shows.

    python tools/make_numerology_sample.py

Writes static/numerology-sample.json (the report cards, drawn inside the landing page like the preview) and static/numerology-sample.pdf
(the download). Run it again, and commit the two files, when the report content or design changes or when the sample's years go stale.

The sample is the REAL production render (the same approved text and layout a customer gets) for a made-up person and date of birth. It is
labelled as a sample on every page and in the document title. It is built ahead of time and served as plain files because sample mode of the
renderer refuses to run while live payment keys are configured, and a production server has them. Needs Chrome for the PDF (set CHROME_BIN)."""
import datetime
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "db"))

NAME = "Sample Reader"                      # clearly made up
DOB = (14, 3, 1991)                         # day, month, year: Mulank 5, Bhagyank 2 (neither is a 4 or 7 edge case)
PREPARED = datetime.date(2026, 11, 13)      # pinned, so the personal years in the sample are stable
FOOT_OLD = '<div class="rp-foot">Axtroshastra &middot; Mulank numerology report</div>'
FOOT_NEW = '<div class="rp-foot">Axtroshastra &middot; Mulank numerology report &middot; SAMPLE for a made-up person</div>'
TITLE_OLD = "<title>Your Mulank Numerology Report</title>"
TITLE_NEW = "<title>Sample Mulank Numerology Report (made-up person)</title>"


def build() -> tuple[dict, bytes | None, str]:
    import mulank_qc
    import numerology_report
    import numerology_viewer
    import pdfgen
    res = numerology_report.build_report(DOB[0], DOB[1], DOB[2], NAME, today=PREPARED, mode="production")
    html = res["html"]
    issues = mulank_qc.lint_report_html(html, slots=True)       # the release-gate lint, BEFORE the sample label (which the lint rightly treats as a marker)
    if issues:
        raise SystemExit("the report fails the release lint, so no sample was written: " + "; ".join(i[1] for i in issues))
    for old in (FOOT_OLD, TITLE_OLD):
        if old not in html:
            raise SystemExit(f"expected text not found in the report, so it cannot be labelled as a sample: {old}")
    html = html.replace(FOOT_OLD, FOOT_NEW).replace(TITLE_OLD, TITLE_NEW)
    if res["n_cards"] != 15 or html.count(FOOT_NEW) != 15:
        raise SystemExit("the sample must have 15 cards, each labelled as a sample")
    frag = numerology_viewer.render_fragment(html)
    return frag, pdfgen.generate(html), html


def main() -> int:
    frag, pdf, _html = build()
    out = os.path.join(ROOT, "static")
    with open(os.path.join(out, "numerology-sample.json"), "w", encoding="utf-8") as f:
        json.dump(frag, f, ensure_ascii=False, separators=(",", ":"))
    print("wrote static/numerology-sample.json", len(json.dumps(frag)), "bytes")
    if pdf and pdf[:4] == b"%PDF":
        with open(os.path.join(out, "numerology-sample.pdf"), "wb") as f:
            f.write(pdf)
        print("wrote static/numerology-sample.pdf", len(pdf), "bytes")
    else:
        print("PDF NOT written: Chrome was not found or failed (set CHROME_BIN)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
