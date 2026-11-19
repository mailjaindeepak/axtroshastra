# Vastu Career Report: finalised spec (DRAFT for owner approval)

Status: draft, 19 Nov 2026. Nothing is built. Per CLAUDE.md §18 the build is checked against this doc section by section; change it deliberately, never by drift. Per §8 a visual mock is approved before any renderer code.

Outline artifact (owner-reviewed pointers): https://claude.ai/artifact/WyA422W15biyqx2DxughFa
Build playbook the owner pointed to: https://claude.ai/artifact/LUqoswuKwZD5UT4t1UVMCb

## 1. Product meta
- Name: Vastu Career Report. Product key: `vastu_career`. Page: `/en/vastu-career` (bare `/vastu-career` 301s to it). Indexable, in `sitemap()`, added to `ops/robot_customer/robot.spec.js`.
- Price: Rs 99 ("for now"), server constant `VASTU_CAREER_PRICE_PAISE = 9900`, by product, never by variant. The real charged amount is stored at payment time (§13).
- English only at launch. Hindi twin is built after English is approved (owner, 19 Nov 2026); hreflang is added when it exists.
- No homepage card for now (owner). The product page still gets 5 to 8 on-page reviews in house style (§5, no em-dashes per §5c).
- No free passes in v1 (default, owner may change).
- A belief-system product: every claim reads "according to Vastu Shastra" or "traditionally". No promise of marks, jobs or income. The report says plainly it is traditional guidance for reflection, not a prediction.
- No Swiss Ephemeris and no chart: no "planetary data" or "NASA-grade" claim anywhere. The date-of-birth cards use number arithmetic (Mulank and/or Bhagyank) only.

## 2. Inputs and validation (explicit inline errors, never a silent default, §1)
| Field | Required | Rule |
|---|---|---|
| name | yes | 1 to 60 characters |
| dob | yes | `YYYY-MM-DD`, a real date, not in the future |
| segment | yes | one of `student`, `exam_aspirant`, `professional`, `wfh`, `owner`, `job_seeker` |
| desk_direction | yes | one of N, NE, E, SE, S, SW, W, NW, `not_sure` (the direction the buyer faces while sitting at the study or work desk) |
| door_direction | no | same eight directions or `not_sure`; adds a note on the entrance card |
| phone, email, consent_ts, consent_v, captcha_token, variant | as in the other funnels | same handling as `/api/iq-test` |
Time and place of birth are not collected.

## 3. Computed data (deterministic, no LLM)
`compute_vastu_career(name, dob, segment, desk_direction, door_direction)` returns facts and teaser:
1. **Desk check:** compares `desk_direction` with the ideal set for the segment. Result is one of `right`, `acceptable` (small change), `change` (change recommended), or `unknown` for `not_sure`.
2. **Date-of-birth cards:** favourable direction and favourable colour from the number table.
3. **Door note:** only if `door_direction` is given.

Ideal directions (PENDING owner approval against the source the owner trusts):
| Segment | Ideal | Acceptable | Change |
|---|---|---|---|
| student, exam_aspirant | E, NE, N | to be set by owner | the rest |
| professional | N, E | to be set by owner | the rest |
| wfh | NE, E, N | to be set by owner | the rest |
| owner | seat SW facing N or E | to be set by owner | the rest |
| job_seeker | E, N | to be set by owner | the rest |

Number table (PENDING owner approval): Mulank and/or Bhagyank to favourable direction and colour. The mapping differs between traditions, so no value is invented here. Reuse the number functions in `numerology.py`; do not fork them.

## 4. Report structure (one card per page, 430x830, shared `_VYAPAR_CSS` / `_VYAPAR_DEFS`)
1. Cover (name, segment, date). Welded page, same format as Career Intelligence.
2. A Note for You (first name). Welded page.
3. Desk check verdict (the verdict, the reason, the specific fix and a rental-friendly alternative).
4 to 8. The five segment cards (section 5).
9. Books, materials and desk organisation.
10. Fixes when the ideal direction isn't possible, with rental-friendly changes that need no demolition.
11. Small room and hostel.
12. Main door and entrance (with the door note if given).
13. Sleeping direction.
14. 10-minute quick fixes (do this tonight).
15. Do and don't one-pager.
16. Compass and desk diagram (drawn from the buyer's own desk direction).
17. Your favourable direction (date of birth).
18. Your favourable colour (date of birth).
19. Thank-you. Welded page.
Total 19 cards per buyer. Design and CSS are copied from the shared theme; none of Career Intelligence's or Business Growth's text is reused (leak grep, §8). Every non-report element is hidden with `@media print` (§8).

## 5. The five segment cards (pointers, copy to be written and approved per segment)
Titles are outcome-style at copy stage. Directions below are from general Vastu tradition and need the owner's source check.

**Student**
1. Which direction to face while studying: traditionally east or north-east; avoid facing south.
2. Desk placement: solid wall behind, door in view but not in line with it, no beam overhead, open space in front.
3. Colours traditionally linked with concentration: light green, light yellow, white, light blue.
4. Desk essentials and common mistakes: lamp, clean surface, books; avoid studying on the bed, clutter, a mirror facing the desk.
5. Light and fresh air: morning light from the east or north, a nearby window, a warm lamp for evenings.

**Exam aspirant**
1. Direction and seat for long hours: east or north-east, firm chair with back support, solid wall behind.
2. Revision corner: formulas and charts on the east or north wall, timetable in view.
3. Night-study light and air: a lamp that doesn't glare, a cracked window, short breaks away from the desk.
4. Reset routine: clear the desk every night, phone and gadgets away from the study area.
5. Common aspirant mistakes: studying in bed, a cluttered shelf above the head, back to the door, a dim corner.

**Working professional**
1. Office desk direction: traditionally north or east; avoid back to the door or a glass partition.
2. Seating and back support: solid wall or high-backed chair behind, a view of the entrance, not under a beam or AC vent.
3. Growth and promotion: keep the north (traditional career zone) open and tidy, an uncluttered desk.
4. Decor and symbols: plants and plain artwork traditionally linked to progress; avoid dead plants, stopped clocks, harsh imagery.
5. Common desk mistakes: clutter, facing a blank wall, heavy objects overhead, piled-up electronics.

**Work from home / freelancer**
1. Choosing the corner: north-east, east or north; avoid the toilet or kitchen wall behind you.
2. Bedroom as office: separate the work area from the bed, screen the bed during work, laptop off the bed.
3. Light and desk setup: side natural light, an evening lamp, screen not facing a window or mirror.
4. Productivity and creativity layout: a clear central space, a creative corner (north or east), few distractions.
5. Boundaries and mistakes: a daily "close the workspace" routine; avoid the sofa, cluttered cables, a mirror behind the screen.

**Business owner**
1. Owner's seat and cabin: south-west seat facing north or east, solid wall behind, visitor chairs opposite.
2. Cash counter and cash box: traditionally in the north or facing north; clean, closed, uncluttered.
3. Shop or office entrance: north, east or north-east traditionally favourable; clean, well lit, unobstructed.
4. Layout basics: heavy stock to the south or west, open space in the north-east.
5. Common premises mistakes: seat under a beam, a toilet near the entrance, broken or unused items piled up.

**Job seeker**
1. Interview-preparation space: a quiet corner facing east or north, a clean desk, soft lighting, resume in one place.
2. Career-growth zone at home: keep the north tidy, no heavy storage there, add a plant.
3. Main door and entrance: clean, bright, unobstructed, nameplate visible, no broken items or shoe pile.
4. Day-before routine: documents ready, a steady morning setup, the direction to face when leaving (if that tradition matters to the buyer).
5. Common job-search mistakes at home: working from bed, a dim cluttered corner, ignoring the entrance.

## 6. Free preview (real computed data, the rest locked, §1)
Shows: the desk-check verdict (right, small change, change recommended) and one date-of-birth tip. The fix, the five segment cards and every other card stay locked and must not leak into the page source before payment.

## 7. Tone, vocabulary and legal
- Insight first, reason second; "may", "traditionally"; never a guarantee.
- No Meta "Health and Wellness" words (§5b): avoid stress, calm, healthy, health, remedy, cure, relief, peace of mind, healing, wellness. Use "steady", "fixes", "clarity" instead. Grep every visible string before shipping.
- Chart-derived rules (§21, §22) do not apply (no chart), but no first name, number or trait from the sample persona may survive into a real report.
- Update privacy, terms and consent for any new field (desk direction, door direction).

## 8. Funnel, payment, delivery and tracking
- Create route: new `POST /api/vastu-career`, modelled on `/api/iq-test` (api.py `create_iq_test`), with its own input model. It validates, calls `compute_vastu_career`, saves with `reports_v2.save_report(..., product="vastu_career")` and returns `{report_id, teaser}`. `/api/kundli` is not changed, because it requires a place and a birth-chart compute (api.py:1788-1799).
- Payment: shared `/api/order`, `/api/verify`, `/api/webhook`, report at `/report/{id}`, same Razorpay gateway (owner, 19 Nov 2026, per the build playbook). Server price only; auto-capture on; webhook registered for `payment.captured`; `DEMO_MODE` unset in production.
- Shared-file touches in `api.py` (all additive): price constant and `_order_amount_paise` branch; `PRODUCT_LABEL` and icon entry; `_render_for` and `_full_report_html` branches; `_deliver_paid_report` needs no branch beyond the default path; page routes `/en/vastu-career` plus 301; `sitemap()`.
- Delivery: WhatsApp to the popup number only, never Razorpay's contact; both Twilio templates (media and text fallback) checked for this product.
- Tracking: fire both `fbq` and `gtag` at `form_start`, `generate_lead`, `begin_checkout`, `purchase`; page served through `_serve_page_with_nav`; standard analytics block in the head; page source contains `fbq('init'` and `fbq('track','Lead'`.
- Event id: the shared server Purchase uses the report id as `event_id`/`transaction_id` (`tracking.track_purchase`, called from `_deliver_paid_report`). The report id is also the link to the report. A hashed id would need a change to shared code. OPEN: keep the report id (like Career Intelligence) or change shared code; owner decides.

## 9. Gates (all must be green before any push; §10, §20)
Mock approved and printed to 323x623 pt PDF with page count equal to card count and nothing clipped; engine unit tests for every segment x every direction x door note, the number table, and every input branch (§12); a real end-to-end test of the production path (create, order, verify, report) in DEMO_MODE; vocabulary scan; leak grep for other products' names; full `pytest`, Playwright E2E, robot smoke, `tests/test_report_buttons.py`; independent convergent audit written to `docs/audits/` (§20).

## 10. Open items for the owner
- Approve the ideal, acceptable and change directions per segment, and the number-to-direction and number-to-colour table.
- Event id choice (section 8).
- Whether Rs 99 stays after launch (struck-through price or offer timer on the page).
- Who approves each segment's copy before it is written into code.

## 11. Build order
0 decisions (done except section 10) -> 1 this spec approved -> 2 visual mock approved -> 3 engine and tests -> 4 content -> 5 renderer -> 6 landing page and create route -> 7 payment wiring and DEMO_MODE test -> 8 tracking checks -> 9 gates and audit -> 10 launch checklist and owner go-ahead. Local commits only; push, PR and deploy only on the owner's explicit go-ahead each time.
