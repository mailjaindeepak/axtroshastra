# Audit: Annual Report (product `annual_report`), independent round, 6 Nov 2026

Reviewer: fresh independent agent (CLAUDE.md 20b, did not write the code). Read-only except this file.
Worktree `axtro-diwali-live`, branch `feat/annual-report`, HEAD `e4d52f7`. Scratch: `.../scratchpad/audit/`.

## Scope and diff
- `git diff upstream/aws-mysql...HEAD` is EMPTY: nothing is committed. All work is uncommitted: 7 modified files (`api.py` +96/-, `engine.py` +103, `narrative.py` +3, `ops/robot_customer/robot.spec.js`, `pages/home.html` +15, `tests/e2e/offer_timer.spec.js`, `tests/test_report_buttons.py`) plus 31 untracked paths (annual*.py, pages/annual-report.html, 8 sample jpgs, 6 test files, tests/e2e/annual.spec.js, tests/data/annual_anjali_golden.json, docs/annual/). `git fetch upstream` was NOT run (read-only brief), so "diff vs upstream" was not re-verified against a fresh fetch.
- Env: Python 3.13 (anaconda), `env -u DB_HOST`, docker MySQL `axtro-test-mysql` 127.0.0.1:3307 via the tests' conftest (copied to scratch for my probes). Never touched prod.
- Ran: annual tests + report_buttons (430 tests: 429 pass, 1 fail, see F4), diwali_api + birth_accuracy + verify (26 pass, so no Diwali regression seen). 200 seeded random payloads through compute_annual -> JSON round trip -> render_annual; 25 of them printed with headless Chrome.

## Measured results (rule 3 hunt)
- 200/200 payloads: 0 exceptions, 200/200 render exactly 58 pages, JSON round trip fine (as_of mix: 2026-01-01, 02-28, 08-31, 11-06, 12-31, 2027-01-31, 2028-02-29; T0..T3; both genders; all work types and steering).
- 25 PDFs (every 8th): 25/25 = 58 PDF pages at 323x623pt; page number y = 813 px on all 1450 pages (identical); lowest body text above 790 px on every page (0 violations).
- Banned/health/festival/Meta scan of all 200 rendered texts: 0 hits except "Karmadhipati" (64 reports, a yoga name inside the substring `karma`; not a real hit). No Diwali words. No Anjali/owner-persona (the 'Purva' hits are nakshatra names). Page text and 7 page reviews: clean. No dashes in reviews.
- Teaser locked-month leak: all 200 teasers: locked strip entries carry exactly `{label, m, open}`; only 2 `tone` fields exist; no `areas`/`tones`/`span_months` keys in the teaser; `/api/report/{rid}` unpaid returns teaser only; `/report/{rid}` and `.pdf` return 404 unpaid. No leak found.
- Engine spot checks: Saturn into Aries 2027-06-03 05:28 IST, Jupiter into Leo 2026-10-31, Rahu into Capricorn 2026-12-05; bracketing the reported minute by +-2 min flips the sign in the right direction every time (6 Saturn crossings 2024-2030 incl. retro re-entries 2027-10-20, 2029-10-05). Naive == aware(IST) results. Kaal Sarp strictness: planet exactly on the axis, conjunct Rahu -> False; wrap-around 350/355/5 -> True; all correct.

## CONFIRMED findings

| id | sev | file:line | failing scenario | reproduction and result |
|---|---|---|---|---|
| F1 | High | `annual_report_p2.py:1351` (`_c_LAST`), `annual_report_p2.py:1856` (`_d_LEAD43[1]`) | Hard-coded mock-persona dates in a chart/time-derived page (rule 22). Every report says "Dec 2027 and after are not covered here" and a quarter plan "from Dec 2026" regardless of the buyer's span. Buyer on 2027-03-15 has span Apr 2027 to Mar 2028 and is told Dec 2027 onward is not covered (it is inside the span). Correct only for a buyer in November. | `scratchpad/audit/asof.py`: as_of 2027-03-15 -> span "Apr 2027 – Mar 2028", text still "Dec 2027 and after are not covered". Across the 200 renders: "Dec 2027 and after" in 200/200 (valid only for the 37 with as_of 2026-11-06), "from Dec 2026" in 46. Wrong for every purchase from 1 Dec 2026. Tests do not catch it: golden is one persona at one as_of. |
| F2 | Medium | `annual.py` Sade Sati block (`ss_changes` filtered by `in_span`, `ss_stage` taken at `as_of`, ~lines 262-270) | Saturn changes sign between `as_of` and the 1st of next month (span start). Those changes are dropped and the stage reported is the stage at as_of, not at span start, so the report is wrong for the whole 12 months and contradicts its own change list. | `ss.py`: Moon Aries (dob 1990-03-01), as_of 2027-06-01 (Saturn enters Aries 2027-06-03). Facts: `stage "first"`, `change_dates [2027-10-20 'first', 2028-02-23 'second']`. Truth at 1 Jul 2027 is second stage; list implies second->first on 2027-10-20 while stage says first from the start. as_of 2027-05-31 correctly lists 2027-06-03 'second'; as_of 2027-06-04 gives 'second'. Affects buyers in the days before a Saturn move (up to 30 days per move). Dhaiya fields use as_of too (same class). Preview `chart.sade_sati.stage` shows the same wrong stage. |
| F3 | Medium | `annual.py` `md = next(m for m in tree if m["start"] <= as_of_dt <= m["end"])` (~line 208) and `api.py:1735-1806` (only `ValueError` mapped to 422) | DOB on or after the as_of day (future date, or born today) -> `StopIteration` -> uncaught -> HTTP 500 instead of 422. | `ap/test_probe.py` through `/api/kundli`: `dob "2030-01-01"` and `dob "2026-11-06"` both -> `RuntimeError: coroutine raised StopIteration` (TestClient raise, i.e. 500). Direct: `annual.compute_annual({..."dob":"2999-12-31"...}, "2026-11-06")` -> `StopIteration`. Fix: reject dob > as_of in `_validate` (explicit 422, rule 1). |
| F4 | Medium | `annual_report.py` fit-to-page net + `tests/test_annual_report.py:502-519` | The author's own test fails on a valid payload: page 15 (Dhaiya and Sade Sati) for `compute_t3_female` is shrunk so text is 9.9 px, below the 10 px floor; the test asserts no sub-10 px text on pages without an SVG. Same mechanism shrinks pages 15, 20, 21, 23, 24, 26, 27, 31, 36 to 9.8 px in my random set (page 24 in 10 of 25 PDFs). | `pytest tests/test_annual_report.py -k small_text_is_only_chart_labels` -> `AssertionError: page 15: small text on a page without an SVG, sizes px [9.9]` (1 failed, 3 passed). Full annual run: 429 passed, 1 failed. `small.py` over 25 PDFs lists the 9.8 px pages. Page 51 shows 8.0/8.9 px in 25/25 (chart labels, presumably legit). The gate is red locally; CI would be red. |
| F5 | Low | `api.py:1735-1800` (shared path; reproduced on annual) | Name of 5000 chars -> DB error 500 (`Data too long for column 'name'`) instead of 422. Page caps at 60, so only direct API callers. Shared with other products; not an annual regression. | `ap/test_probe.py`: `name "A"*5000` -> `DataError(1406, "Data too long for column 'name'")`. Same for `tob "99:99"` / `"9:5"` / `dob "abc"`: `ValueError` -> 500 (api computes `local_dt` before the product branch; pre-existing for all products). |
| F6 | Low | `annual_report_p*.py` cover (`.cov-name2`) | A first name that is one unbroken word of ~30+ characters is clipped on the cover and pages 2 and 58. The page allows `maxlength=60`. | `nm.py`: name "Abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz Kumar" -> `nm_long.pdf` page 1 text clipped at both edges (`long1.png`). HTML escaping is fine: `<img src=x onerror=...>` renders as `&lt;img...` in body and `<title>` (0 raw tags). |
| F7 | Low | `pages/home.html` (Annual Report reviews, Sneha 31) | Testimonial says "50 pages"; the report is 58 pages (and the contents card, spec, and tests say 58). | Count: `len(new) == 58` enforced in `annual_report.py:262`; 200/200 renders. |
| F8 | Low | `tests/test_annual_api.py:236-241` | `test_delivery_fast_sends_no_nudge` is timing-sensitive: nudge timer 0.3 s vs real render+compute ~0.4-0.5 s. It failed once (2 texts, expected 1) in a combined run while the machine was loaded by my Chrome jobs; passed alone twice and in the next full run. Flaky under CI load. | First annual run: `AssertionError: assert 2 == 1` at line 241; reruns pass. Intermittent, so labelled Low and a test-hygiene finding, not a product bug. (Diwali's twin uses the same 0.3 s trick with a lighter render.) |

## DISCARDED (could not reproduce)
- Price can be chosen by client / variant-based price: `_order_amount_paise` returns 49900 by product before any variant check; tampered `amount` fields on `/api/order` are not read (probe reached the Razorpay-not-configured 503 with no amount accepted); tests also cover variant `/milan` -> 49900. Not a bug.
- Locked-month leak in the teaser (strip, labels, counts, order, sample text): none found (see measured results).
- Kaal Sarp on-axis mis-classification, sign-change misses near retro, naive/aware mismatch, IST day boundary, leap-day, polar lat 89.9/-90, tz +-14: all behaved correctly in probes.
- Delivery to Razorpay contact: `_deliver_paid_report` uses `popup_phone` only; `_deliver_annual_task` takes that number; test with PAYER contact `+919999900001` passes. Both templates exercised by `test_real_twilio_templates_media_and_text_fallback`.
- Gift fields: sent with `product annual_report` -> 200, nothing stored (`meta` has no gift keys) and nothing in the teaser.
- `/hi/annual-report`: 404 and not linked from the annual page or home (served page has 0 `/hi` hrefs, 0 dead hrefs). Legacy `/annual-report?x=1` -> 301 `/en/annual-report?x=1`. Sitemap contains it. robot.spec.js has ALL_PAGES, FUNNELS and PENDING_DEPLOY entries.
- DB column: `reports.product` is `varchar(40)`; `annual_report` is 13 chars.
- Secrets: grep of the diff and annual*.py for key/token patterns: none (`SECRET = "rzp_key_secret_annual"` exists only as a test-local fake in tests).
- Hard-coded persona values in code (`Sagittarius`, `Leo`): only the 12-sign name lists; no Anjali/owner-persona/'12 May 2028'.
- Diwali regression: api diff touches Diwali branches only through shared helpers whose default behaviour is unchanged (`_add_diwali_actions` default bar, `_refresh_current_period` skip list); Diwali tests pass.

## Quality notes (not gated)
- `PAGE_TITLES_P2` (`annual_report_p2.py:8-14`) holds mock months ('Dec 2026'...) and is only used in `assert len(...) == 32` (line 1921): dead constant carrying persona dates; delete it so F1-class literals cannot hide there.
- `_to_dt` strips tzinfo without converting, and `as_of=None` uses `date.today()` (server local, UTC on EB): an IST buyer between 00:00 and 05:30 on the 1st gets the previous month's span. Not run on a UTC host, so unverified; consider `datetime.now(IST)`.
- Dhaiya "ends"/"restarts" are first sign-level exit/re-entry, so a retrograde loop can produce "comes back on <weeks later>" copy; check the wording with the owner.
- API silently maps a bad `time_band` to 13:00 (`api.py` `BAND_MID.get(..., "13:00")`; probe `time_band "zzz"` -> 200). Pre-existing, but §1 says never silently guess.
- Offer timer ("Offer ends in 30:00" with a struck Rs 999) restarts per tab session; same pattern as Diwali/CI. Consider whether a re-armed fake countdown is acceptable for the struck price.
- Home reviews: "Gifted to my sister" / page "Got it for my brother" are fine for a buyer entering the recipient's data, but there is no gift mode; "PDF came on WhatsApp in about ten minutes" is a delivery-time claim nothing guarantees; "Sade Sati dates were exact" claims accuracy that has no outside reference (see gaps).
- Golden test (`tests/data/annual_anjali_golden.json`) pins one persona at one as_of; it proves stability, not correctness, and is regenerable with an env var. Corner-cutting check (20a): no stubs returning canned success found; no tests skipped; `_generate_narrative_task` sets `{"_ready": "1"}` deliberately (documented) so the progress page moves on, which is an honest no-op, not a fake success.

## Known gaps (stated, not defects)
1. Rule 21: the new engine functions (`sign_change_dates`, `doshas`, `saturn_house_timeline`, `sade_sati_stages`) are checked only against a second method (bracketing the same ephemeris, and in-repo tests). There is NO outside reference (AstroSage or published ephemeris) for sign-entry dates, Sade Sati/Dhaiya dates or the Kaal Sarp/Pitra rules. `tests/birth_accuracy.json` covers the chart only. All new paths do route through the shared engine (no `swisseph` use or forked math in `annual*.py`; tests assert the engine calls).
2. AI prose is off (`narrative.generate_narrative` returns `{}` for the product); text is deterministic banks.
3. Hindi twin not built (`meta.lang` forced to "en"; no `/hi` route).
4. The funnel has no contact popup like Diwali's; the WhatsApp number is typed in the form and passed to `/api/order` as `phone` (still the "popup" number path, never Razorpay's).
5. Not run: Playwright e2e (`tests/e2e/annual.spec.js`, `offer_timer.spec.js`: no Playwright install here), `ops/robot_customer`, real Razorpay/Twilio, deployment-host PDF fonts, `git fetch upstream`, full `pytest -q` (only the annual, buttons, diwali_api, birth_accuracy, verify slices; stated, not "all green").

## Must fix before push (ranked)
1. F1: remove the two mock-date literals; derive from `span_months[-1]` and `span_months[0]`; add a test that renders at two different as_of values and asserts no label outside the span appears. Delete `PAGE_TITLES_P2`.
2. F4: make `tests/test_annual_report.py -k small_text` green (page 15 for T3 female): fix the layout or adjust the card, not the assertion.
3. F3: validate `dob <= as_of` in `annual._validate` (422), add a test through `/api/kundli`.
4. F2: compute the Sade Sati and Dhaiya stage at span start (and keep gap changes), or include changes from as_of; test with Moon Aries at as_of 2027-06-01.
5. F7 (copy "50 pages" -> "58 pages" or drop the number), F6 (cover wraps long names), F8 (make the nudge test deterministic).
6. Then fetch upstream, re-run the full CI gate (pytest -q incl. db/, Playwright e2e, robot), commit, and run the next independent round (20b needs two consecutive rounds with the same confirmed set).


## Round 2

Reviewer: fresh independent agent (CLAUDE.md 20b-20g), read-only except this section. Branch `feat/annual-report`, HEAD `e4d52f7`, all work still uncommitted. I ran `git fetch upstream` (updates remote-tracking refs only): `upstream/aws-mysql` is still `e4d52f7`, 0 commits ahead, so the base is current. Scratch: `.../scratchpad/audit2/`. Never touched prod; DB was docker `axtro-test-mysql` 127.0.0.1:3307 only; app on port 8014 (stopped), DB `axtroshastra_v2_audit2` (dropped).

### Re-verification of round 1 (original failing scenario re-run on current code)

| id | verdict | command and output |
|---|---|---|
| F1 | FIXED | `compute_annual(..., as_of 2027-03-15)` -> span Apr 2027 to Mar 2028; rendered text contains 'Dec 2027 and after' = False, 'from Dec 2026' = False. Plus 60 seeded payloads (as_of incl. 2026-11-30, 2027-01-31, 2028-02-28, 2028-02-29, 2028-12-31, 2029-02-28, 2030-12-31 and random to 2030): 0 'Mon YYYY' strings outside span + past 2 + month after span + birth month + as_of month + planet-period / dhaiya / Sade Sati / sign-change dates. The detector works (234 dates found in one doc). |
| F2 | FIXED | Moon Aries dob 1990-03-01, as_of 2027-06-01 -> `stage 'first'`, `change_dates` = 2027-06-03 'second', 2027-10-20 'first', 2028-02-23 'second' (the 3 June change is now kept; list and stage agree). |
| F3 | FIXED | `compute_annual` with dob 2030-01-01, 2026-11-06, 2999-12-31 -> `ValueError: dob must be before the report date`. Live `/api/kundli` (app on 8014): dob 2030-01-01, 2026-11-06, today -> 422; 2026-11-05, 1900-01-01, 1850-01-01 -> 200. |
| F4 | FIXED | `pytest tests/test_annual_report.py -k small_text` -> 4 passed. 22 printed PDFs: no body text under 10px outside charts; DOM check on 10 docs (computed font-size x zoom, text outside `<svg>`, all pages): min 10.0px (sanity: at a 10.6 threshold it lists pages, so the check bites). No `zoom` stage fired in any sample. |
| F5 | FIXED (oversize); residual below | name 5000 chars -> 422; name 61 -> 422; place 121 -> 422, place 120 -> 200. Residual: see R2-4 (`tob 99:99`, `dob abc` still 500, pre-existing shared path). |
| F6 | FIXED | name `Abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz Kumar` printed: page 1 text x 30.0 to 292.4, page 2 67.9 to 254.7, page 58 22.9 to 299.6 of 323.04 pt (wrapped, nothing clipped). Devanagari name 'अनन्या शर्मा' renders (cover image viewed). |
| F7 | FIXED | `git diff pages/home.html`: Sneha review now "every page used my own dates", no page count; `grep '50 pages'` = 0. |
| F8 | NOT RE-PRODUCED (not a gate) | `test_annual_api.py` 54 passed in a clean copy and in the full annual run; the 0.3 s timer race was not exercised under load. Still a test-hygiene risk. |

### Hunt for bugs introduced by the fixes (60 seeded payloads, dob 1945-2012, Port Blair 11.62/92.73, Leh 34.15/77.58, Itanagar, Bhuj, Kanyakumari, 120-char place; T0-T3 with tob 00:00 / 23:59 / random; all work types; all steering values; as_of 2026-11-06 .. 2030-12-31)
- compute_annual -> render_annual -> JSON round trip: 60/60 no exception, 60/60 = 58 cards, 60/60 round-trip HTML identical (`render(rep) == render(json.loads(json.dumps(rep)))`).
- Banned list (slow, stretch, window, phase, house, dasha, transit, pressure, karma as whole words), health words, Diwali words, mock names (owner-persona, Anjali, Deshpande unless in the buyer's own name): 0 hits in 60 docs. Dead `href="#..."` targets: 0. 'page N' mentions all in 1..58.
- 22 Chrome PDFs (payload indexes 0,3,6,8,9,12,15,18,21,24,27,28,30,33,36,38,42,45,48,51,54,58): all 58 pages at 323.04 x 623.04 pt; page-number y = 799.2 px on every page of every file; lowest text 788 px (limit 800); every character of each card's HTML text is present in the PDF text layer (0 of 1276 pages short, so tt/tt2/tt3 change no text and hide none).
- Staged fit: `data-fit` fired `tt` 25 times and `tt3` 3 times (all three on page 15, Dhaiya and Sade Sati, payloads 8, 27, 51), `zoom` 0 times. Pages 15 of payloads 8 and 27 viewed: the compact branch fits, nothing overlaps the page number (lowest text 784 vs number 799), the 12-month strip and table are intact. The Manglik page (16) viewed: wheel complete. DOM check on 10 docs: no `<svg>` extends outside its card.
- Wiring: see hunks list below.

### NEW confirmed findings (all in tests/hygiene; zero in product code)

| id | sev | file:line | scenario | reproduction |
|---|---|---|---|---|
| R2-1 | High (CI red) | `.gitignore:19` (`data/`), `tests/data/annual_anjali_golden.json` | The golden file, named in the brief as the CI anchor, is gitignored, so a normal `git add` will not commit it. `git ls-files tests/data` is empty and no tracked file lives under any `data/` dir. | `git check-ignore -v tests/data/annual_anjali_golden.json` -> `.gitignore:19:data/`; `git ls-files --others --exclude-standard` does not list it; `git status --short --ignored` shows `!! tests/data/`. Fix: `git add -f` it, or add `!tests/data/` to .gitignore. |
| R2-2 | High (CI red) | `tests/test_annual_report.py:46-47,111` (`_persona()` loads `docs/annual/mock/_build/persona.py` inside `reports()`), `tests/test_annual_compute.py:15,101` (`NOTES` + `_persona()`) | The golden test (`:190`) is NOT an independent anchor: it renders `mock_anjali` built from `persona.py` too, so it cannot run in a clean checkout even with the golden file present. | Clean copy = `git ls-files` + untracked minus `docs/annual/` and `docs/diwali/mock/` (682 files, `scratchpad/audit2/clean`), `env -u DB_HOST pytest` per file: `test_annual_report.py` -> collection ERROR `FileNotFoundError .../docs/annual/mock/_build/persona.py` (whole file, 457 tests); `test_annual_banned_words.py` -> collection ERROR (it imports `test_annual_report`); `test_annual_compute.py` -> 3 failed (`test_persona_a_facts`, `test_persona_b_facts`, `test_facts_keys_and_types`), 72 passed; `test_annual_assets.py` 14 passed; `test_annual_api.py` 54 passed; `test_engine_annual.py` 19 passed. `test_anjali_equals_v8_mock` skips by design but the golden test then errors at collection. |
| R2-3 | Medium | `tests/test_annual_report.py:35,450` and `tests/test_annual_assets.py:18,272` | The fit regression tests (`need_pdf`: the 4 small-text/page-number/PDF tests that guard F4) and the print smoke test hard-code the macOS Chrome path, so on the Linux CI runner (`ci.yml`, ubuntu, python 3.12, no Chrome step) they all SKIP. The F4 fix is guarded only on the owner's Mac. | Code: `CHROME = "/Applications/Google Chrome.app/..."`, `skipif(not os.path.exists(CHROME) ...)`; `ci.yml` has no Chrome install. Locally 471 passed, 0 skipped. Fix: resolve Chrome from `shutil.which`/env, or state in the PR that these are local-only. |
| R2-4 | Low (pre-existing, shared path) | `api.py:1764` (`datetime.fromisoformat(f"{inp.dob}T{tob}:00")` runs before the product branch; the annual guards check lengths only) | Residual of F5: malformed values within the length limits still give 500 for annual. | Live app: `tob "99:99"` -> 500, `dob "abc"` -> 500 (T0 payload). The page validates both, so only direct API callers. |

### Discarded (could not reproduce)
- Teaser leak for locked months: 20 payloads through the live `/api/kundli` (steering None and 'strengths' alternating): every locked strip entry is exactly `{m, label, open}`; open months Dec 2026 and Jan 2027 only; exactly 5 `tone` fields (2 past + future_free + 2 open strip entries); no `areas`, `tones`, `span_months`, `change_dates`, `sign_changes` keys; no locked month in any `range`. No leak.
- Unpaid `/report/{id}` and `.pdf` -> 404 for T0, T1, T2, T3; after `/api/_demo_pay/{rid}` `/report/{id}` -> 200 with 58 pages for all four.
- 422 guards block valid input: 'Ananya Sharma', Devanagari name with joiner, `Shaun O'Neil D.Souza-Iyer`, 60-char Latin name, 120-char place, phones `919876543210`, `+919876543210`, `9876543210`, `+91 98765 43210`, `+91-9876543210`, tz '5.5' and 'Asia/Kolkata', T2 with time_band, T3 without tob, dob 2012-12-31: all 200. (My first 'Devanagari60' test was actually 61 codepoints, correctly 422.)
- Price 49900 as `amount_paise`: not checkable on the live app (no Razorpay keys -> `/api/order` 503; `payments` table empty after demo pay). Covered by `tests/test_annual_api.py:104-119` (`_order_amount_paise == 49900` for annual, variant `/milan` ignored, stored `[49900]` through the stub order); 54 passed. Not a defect.
- Delivery: `_deliver_paid_report` -> `wa_phone = popup_phone or ""`; all four call sites (`api.py` 2138, 2209, 2270, 2357) pass `popup_phone`; `pay_phone` is CAPI-only. `_deliver_annual_task` sends only to that number. No change.
- Secrets (rule 19): grep of `git diff` + all new files: no keys/tokens. Hits are public: support WhatsApp +91 95998 27297 and Ads id in the page chrome (same as other pages), fake `rzp_test_x` in e2e mock, test-only phones 99880003xx / 9999900001 (fake).

### api.py hunks touching shared code (judged)
1. `PRODUCT_LABEL`, `PRODUCT_SVG` entries: additive. OK.
2. `_render_for`: new `if product == "annual_report"` before career_growth; Diwali branch untouched. OK.
3. `ANNUAL_PRICE_PAISE` + `_order_amount_paise` branch placed after diwali, before career: other products unaffected. OK.
4. `_generate_narrative_task`: Diwali branch unchanged (comment only); new `elif annual_report` sets `{"_ready":"1"}`. OK.
5. `create_kundli`: annual guards run only for product annual_report; Diwali's own guard above is untouched. `elif inp.product == "annual_report"` compute branch; `lang` branch: annual forced 'en', others identical (`elif != diwali`). `chart_svg` skip list now (diwali, annual_report). OK.
6. `_deliver_annual_task` + `_deliver_paid_report` elif: Diwali path unchanged. OK.
7. `_refresh_current_period`: skip tuple adds annual_report. OK.
8. `_add_diwali_actions(html, bar=_DIWALI_ACTIONS)`: default keeps Diwali identical; `_ANNUAL_ACTIONS` is a string replace of the share text. OK.
9. `report_page`: new `elif annual_report`. Sitemap adds `/en/annual-report`; two new routes before `/{slug}`. OK.
`engine.py`: import `timezone` + 100 additive lines (pure additions; `git diff engine.py` has 1 removed line, the import). `narrative.py`: early `return {}` for annual only.

### Quality notes (not gated)
- `tests/test_annual_compute.py:88` and `tests/test_annual_report.py:313` carry `... or True` asserts that cannot fail (the next assertions do the real work); delete them.
- `api.py` does not pass `time_band` into `compute_annual`, so for T2 the report prints the generic 'Not sure of the time' (`annual.py:333-335`) and `BAND_TEXT` is unused through the API; the tob midpoint is still used for the chart (T2 fix OK). Read from code, not run.
- `annual._to_dt(None)` uses `date.today()` (server local). On a UTC host an IST buyer in the first 5.5 h of a month gets a span one month earlier; not run on a UTC host.
- `tests/test_annual_report.py:444` has a dead line `pymupdf = pytest.importorskip("pymupdf") if False else None`.
- Python 3.12 on CI vs 3.13 here: not verified on 3.12.
- Static images: 8 files, 1.7 MB total (108 to 244 KB each); referenced dynamically by `SAMPLE_PAGES=8` in the page and the e2e spec. Fine.
- Server PDF fonts (Devanagari fallback) on the EB host not checked.

### Clean-checkout test list (branch files only, docs/annual and docs/diwali/mock absent)
Would ERROR at collection: `tests/test_annual_report.py` (all 457 tests, incl. golden and F4 guards), `tests/test_annual_banned_words.py` (imports the former). Would FAIL: `tests/test_annual_compute.py::test_persona_a_facts`, `::test_persona_b_facts`, `::test_facts_keys_and_types`. Would pass: `test_annual_assets.py` (14), `test_annual_api.py` (54), `test_engine_annual.py` (19), remaining 72 in `test_annual_compute.py`. On the Linux runner the Chrome-dependent tests would additionally skip (R2-3). Untracked-path dependencies: `docs/annual/mock/_build/persona.py` (report:47, compute:101), `docs/annual/mock/_notes/*.json` (compute:15 via `J()`), `docs/annual/mock/annual-report-full-v8-anjali.html` (report:33, skip-guarded), `tests/data/annual_anjali_golden.json` (gitignored, R2-1). Comment-only mentions in `annual.py:11-12,30`, `annual_report.py:3`, `annual_assets.py:3`.

### Ship list vs do-not-ship
MUST commit (new): `annual.py`, `annual_assets.py`, `annual_report.py`, `annual_report_p1.py`, `annual_report_p2.py`, `annual_report_p3.py`, `pages/annual-report.html`, `static/annual-sample-01..08.jpg`, `tests/test_annual_api.py`, `tests/test_annual_assets.py`, `tests/test_annual_banned_words.py`, `tests/test_annual_compute.py`, `tests/test_annual_report.py`, `tests/test_engine_annual.py`, `tests/e2e/annual.spec.js`, `tests/data/annual_anjali_golden.json` (needs `git add -f`, R2-1), `docs/audits/annual-report-2026-11-06.md`. MUST commit (modified): `api.py`, `engine.py`, `narrative.py`, `pages/home.html`, `ops/robot_customer/robot.spec.js`, `tests/e2e/offer_timer.spec.js`, `tests/test_ops_workflows.py`, `tests/test_report_buttons.py`. No product doc outside the audit exists in tracked-to-be paths.
DO NOT ship: `docs/annual/` (untracked, incl. gitignored `docs/annual/build/` and `_build/__pycache__`), `docs/diwali/mock/`, any scratch. Ignored dirs (`tests/e2e/node_modules`, `test-results`, `.pytest_cache`, `data/`) stay out.

### Convergence status (rule 20b)
Round 1 confirmed set: F1-F8. Round 2: F1-F7 verified FIXED, F8 not reproduced; product-code bugs found in round 2: 0. NEW confirmed items: 4 (R2-1, R2-2, R2-3 test/CI integrity; R2-4 Low residual of F5), none in `annual*.py` or the api wiring. NOT converged under 20b: the new set is not empty, and R2-1/R2-2 would turn CI red. Fix those (commit the golden with `-f`, make the tests independent of `docs/annual`, make Chrome tests discover Chrome or declare them local-only), then run round 3; a clean round 3 with zero new confirmed would converge.

## Final status (6 Nov 2026, evening)

### Round 3
Not run. The owner waived it for tonight's release ("skip round 3, I verify myself"). Convergence under rule 20b is therefore NOT formally reached: round 1 found 8 findings (all fixed and re-verified in round 2); round 2 found 0 new product bugs and 4 test/hygiene findings (R2-1 golden file git-ignored, R2-2 tests depended on untracked docs/annual, R2-3 Chrome path hard-coded, R2-4 dob/tob 500). All four were fixed and re-checked by the coordinator (clean-checkout run of the annual tests: 599 passed; live endpoint returns 422 for bad dob/tob/time_quality/time_band).

### Gates run on the final tree
| Gate | Result |
|---|---|
| Main pytest (CI env, docker MySQL) | 2462 passed, 3 failed, 42 errors at the time of the run. The 3 failures were caused by our new tests (module-level DB_BACKEND leak; swisseph import map) and are fixed and re-verified. The 42 errors are the missing local `playwright` python package for Diwali print checks (environment, not annual). |
| db/ suite | 51 passed |
| Playwright e2e (all specs, both projects) | 119 passed, 0 failed, 1 flaky (Diwali sticky bar, passed on retry) |
| Annual tests in a clean checkout (no docs/annual) | 599 passed, 0 failed, 0 skipped |
| API + Diwali API + report buttons | 95 passed |
| Compute tests | 75 passed |

Not re-run after the last fixes: the full main pytest and the full Playwright suite.

### Known gaps (ship decisions)
- The new engine checks (Kaal Sarp, Pitra, Shani Dhaiya, Sade Sati dates, sign-change dates) have a second-method cross-check on 50 charts, NOT an outside reference (rule 21 gap; owner chose this).
- Annual prose is deterministic only (AI prose off). Hindi twin not built (no /hi route, no hreflang hi).
- The funnel has no contact popup: name and phone come from the form, as on Diwali. WhatsApp goes to that number only.
- Engine area tones for Nov 2027 differ from the approved mock (engine: strong; mock: mixed). The engine is correct; the mock used a different start month. The approved-text golden hashes pin the mock snapshot as the renderer regression anchor.
- Diwali and marriage return 500 for oversize names or bad dob/tob (pre-existing, not changed).
- Not tested locally: real Razorpay payment, real WhatsApp delivery, the server PDF font environment, Python 3.12.
- Python `playwright` package missing in the local interpreter (Diwali print tests error locally; CI installs requirements-dev).

### Rule 16 checklist
- §1 funnel: cloned from Diwali, no popup (deliberate, same as Diwali); WhatsApp to the form phone only; both templates wired. Verified by tests.
- §2 head block: canonical + hreflang en + x-default for /en/annual-report; no hreflang hi because no Hindi page exists. Verified.
- §3 sitemap and robot: /en/annual-report added; robot.spec.js updated (not run: live-site smoke).
- §4 homepage: card added at the owner's request. §5 reviews: 7 on the page, 7 on home, no dashes, no health words (tests).
- §7 Hindi: not built (English first, owner decision).
- §8 PDF theme: v8 theme in annual_assets.py, 430x830 cards, fixed footer page number; 58 pages for every buyer (checked on 200 random charts, 22 PDFs).
- §9 buttons: axPdfDl and axShare present (test_report_buttons).
- §10 gates: see table above. §13 amount_paise stored from ANNUAL_PRICE_PAISE=49900 (explicit branch). §19 no secrets in the diff.
- §20 audit: rounds 1 and 2 done, round 3 waived. §21 accuracy gate: second-method only (gap above). §22 personalization: tests prove no persona text in other buyers' output.
