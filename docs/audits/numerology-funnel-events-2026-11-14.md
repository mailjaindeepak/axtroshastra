# Audit: Numerology funnel events (14 Nov 2026) - round 1, independent reviewer

Scope: uncommitted diff (pages/numerology.html evId fallback, ops/robot_customer/robot.spec.js, tests/test_mulank_funnel_events.py). Read-only review; pytest not run (shared DB in use).

## Confirmed findings
1. LOW - ops/robot_customer/robot.spec.js:543-544. The old call `waitForFunction(() => ..., { timeout: 30_000 })` passed the options as the *arg* (so the 30s timeout never applied). The new `waitForFunction(ridFn, null, { timeout })` is the correct signature, so every funnel (marriage, milan, career, ...) now has a real 30s cap where it used to run to the test timeout. Scenario: a slow live /api/kundli on a loaded host takes more than 30s to set REPORT_ID, a previously green run goes red. Behaviour for the default `window.REPORT_ID` is otherwise preserved. Fix: keep (it is what the comment already claims) or raise to 45s; just know it is a deliberate tightening.
2. LOW - tests/test_mulank_funnel_events.py:78-85. `except ImportError` around `from test_mulank_browser import ...` hides a genuine ImportError (renamed symbol in test_mulank_browser) as "Playwright not installed", so all browser tests silently skip, which s20e forbids. Fix: only catch the playwright import; import the test_mulank_browser symbols outside the try, and make CI fail (not skip) when CHROME is missing.
3. LOW (accuracy of intent) - only `purchase` carries a report id to /api/event (api.py:1057 maps `transaction_id` to report_id; generate_lead and begin_checkout send none). So the old 'mk' fallback only lost `purchase`, never the lead. Test `test_purchase_is_still_saved_when_the_browser_cannot_hash` (line ~177) asserts generate_lead too, which would pass on old code; the purchase assertion is the one that bites. Docstring/commit message should say "purchase", not "lead and purchase".

## Verified OK
- Cleanup: mulank_routes.py:314-322 stores the submitted name in report_data ("name") and the subject; "Robot Customer Numerology" matches `%Robot Customer%` in dashboard/store.py:462. The test checks this against the real pattern list.
- Privacy: browser sends only mk_<hash>; events_v2.py:67 nulls it; test asserts report_id NULL for every row and that the raw rid is absent from every selected column (event_name, report_id, page_url, value, currency). No name/phone is selected or sent by the beacon.
- Phone: browser test uses 9591+6 digits (ms clock); no other test uses 9591 (grep), existing mulank browser tests use 98/97 prefixes. Robot uses testPhone().
- robot defaults: `funnel.teaser || '#teaser'` and `funnel.reportId || (() => window.REPORT_ID)` preserve old behaviour; `page.evaluate(ridFn)` fine. Submit selector `#mkForm button[type="submit"]` matches `#mkGo` (numerology.html:340). Page registered at robot.spec.js:94 and sitemap api.py:3027.
- Ordering asserts: events are seconds apart (fill, preview, checkout, pay); no same-ms race.

## Discarded (no concrete failing scenario)
- Test events/reports/visitors left in the shared DB (vis_mkfe visitor row, "Funnel Check" paid report): same as existing test_mulank_browser; mark-based id window means no cross-test assertions are affected; serial pytest.
- Possible phone collision across runs (ms mod 1e6 recurs every ~17 min): needs the identical millisecond; probability negligible.
- `purchase` count == 1 could miss a late duplicate (poll stops once all names seen): speculative, no known duplicate path.
- Name "Funnel Check" not matching robot patterns: test DB only, not production.

## Round 2 (fresh independent reviewer)
No findings above NOTE level. Round 1's three LOW findings were fixed before this round (robot `waitForFunction` call restored to its original form for funnels without `reportId`; test imports no longer swallow ImportError; docstring says purchase). Round 2's verified and discarded lists match round 1's. Converged: rounds 1 and 2 agree (CLAUDE.md section 20e).

## Gate results (Python 3.11, local)
- Full pytest: 1577 passed, 33 failed, 6 skipped, 5 collection errors. 27 failures and the 5 collection errors are the known Diwali/Annual Python 3.11 f-string/encoding baseline. The other 6 (4 in test_ops_workflows.py, 2 in test_pdf_download_header.py) fail identically on a clean checkout of c6ed2e2, so they are not caused by this change (Windows cp1252 file reads, PDF renderer).
- Numerology and funnel tests: all pass (36 in the affected group after the review fixes).
- Not run: Python 3.12 suite, the Node robot spec (Node is not installed on this machine; a Python Playwright stand-in using the same selectors passed against the local app), Playwright E2E in tests/e2e (needs Node), real Razorpay.
