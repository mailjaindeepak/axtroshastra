# Vastu Career Report: finalised spec (DRAFT for owner approval)

Status: draft, updated 20 Nov 2026. Nothing is built.

Confirmed by the owner (19 to 20 Nov 2026): 16-page structure with five cards from the buyer's own segment only; `desk_flexibility` kept, and every fix must work for a buyer who cannot move the desk; event id stays the report id (opaque, section 8); both date-of-birth pages kept and labelled as numerology-based; date of birth adjusts the desk verdict by rule B (section 3). Still PENDING owner approval: every cell of the direction matrix, the number-to-direction and number-to-colour tables, Mulank only versus Mulank and Bhagyank, Ketu (Mulank 7), the business-owner cash box view, and the job-seeker source. Research and sources: `docs/vastu-career-research.md`.

Spec approved for the visual mock only (owner, 20 Nov 2026), with these working defaults for the pending items, all still changeable before copy and code: direction matrix as drafted in section 3 (extrapolated cells marked); job seeker uses the borrowed student and professional sets; business-owner cash box states the majority view only ("keep the cash box closed and tidy, in the north or south-west, opening north") and does not claim it is the only view; numbers use Mulank only; Ketu (Mulank 7) shows no direction and gives colour only. This approval does not cover copy, renderer code, push or deploy.

Per CLAUDE.md §18 the build is checked against this doc section by section; change it deliberately, never by drift. Per §8 a visual mock is approved before any renderer code.

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
| desk_flexibility | yes | one of `can_move`, `a_little`, `cannot_or_shared` ("Can you move your desk?"); decides which fixes the report gives |
| door_direction | no | same eight directions or `not_sure`; adds one line on the quick-fixes page |
| phone, email, consent_ts, consent_v, captcha_token, variant | as in the other funnels | same handling as `/api/iq-test` |
Time and place of birth are not collected.

## 3. Computed data (deterministic, no LLM)
`compute_vastu_career(name, dob, segment, desk_direction, desk_flexibility, door_direction)` returns facts and teaser:
1. **Desk check:** compares `desk_direction` with the segment matrix below. Result is one of `ideal`, `acceptable` (small change), `change` (change recommended), or `unknown` for `not_sure`. Rule B (owner, 20 Nov 2026): if the result is `acceptable` and `desk_direction` equals the buyer's number direction, it becomes `ideal`. A `change` result is never upgraded. A number direction that Vastu says to avoid never downgrades or overrides the Vastu result; the page says so plainly. The verdict is in the free preview, so the date of birth affects the preview.
2. **Fix set:** chosen from the desk check and `desk_flexibility`. `can_move`: turn or move the desk to a better direction. `a_little`: turn the chair or desk slightly, or use a better corner of the same room. `cannot_or_shared`: keep the desk as is and use the in-place fixes (what to place, what to remove, where to sit). An `ideal` result gets "keep it as it is" plus upkeep tips.
3. **Date-of-birth cards:** favourable direction and favourable colour from the number table.
4. **Door line:** only if `door_direction` is given.
The report only states what the form asked. It never claims to have assessed anything the buyer was not asked (for example the position of the seat in the room).

Direction matrix (PENDING: draft from the research in `docs/vastu-career-research.md`; the owner approves each cell). Direction means the way the buyer faces at the desk. The sources only cover E, N, NE, W and S; SE, SW and NW are extrapolations.
| Segment | Ideal | Acceptable | Change |
|---|---|---|---|
| student, exam_aspirant | E, N, NE | W (sources call it secondary) | S; SE, SW, NW (extrapolation) |
| professional | N, E | NE | S; W, SE, SW, NW (extrapolation) |
| wfh | N, E | NE (sources disagree) | S; W, SE, SW, NW (extrapolation) |
| owner | N, E (facing direction only; seat position is not asked, so it is never checked) | NE (one source) | S, W; SE, SW, NW (extrapolation) |
| job_seeker | E, N (no dedicated source; borrowed from the student and professional sets) | NE, W (borrowed) | S; SE, SW, NW (extrapolation) |

Number tables (PENDING owner approval). No source gave a full Mulank-to-direction table. Proposed derivation: Mulank (birth day reduced to one digit) to ruling planet (1 Sun, 2 Moon, 3 Jupiter, 4 Rahu, 5 Mercury, 6 Venus, 7 Ketu, 8 Saturn, 9 Mars) to that planet's classical direction (Sun E, Venus SE, Mars S, Rahu SW, Saturn W, Moon NW, Mercury N, Jupiter NE; Ketu is unsettled between traditions, so Mulank 7 needs an owner decision). Colours differ between sources and are shown as accents, not wall colours. Open: Mulank only, or Mulank and Bhagyank. A planet's direction is treated as the buyer's "number direction" for rule B; where it contradicts Vastu (for example Mulank 9, Mars, south) Vastu wins. Reuse the number functions in `numerology.py`; do not fork them.

## 4. Report structure (one card per page, 430x830, shared `_VYAPAR_CSS` / `_VYAPAR_DEFS`)
1. Cover (name, segment, date). Welded page, same format as Career Intelligence.
2. A Note for You (first name). Welded page.
3. Desk check verdict (the verdict and the reason, from the buyer's own desk direction).
4 to 8. The five cards for the buyer's own segment only (section 5). A buyer sees the five cards of the one segment they chose, never another segment's. The renderer picks the set from `segment`; a test checks that exactly five segment cards appear and that none come from another segment.
9. Desk organisation, books and materials.
10. Your fixes, chosen by the desk check and `desk_flexibility` (section 3), including rental-friendly changes that need no demolition.
11. Small room, hostel and shared space (includes one line on sleeping direction).
12. Quick fixes for tonight, with the do and don't list on the same page (includes one line on the main door if `door_direction` was given).
13. Compass and desk diagram (drawn from the buyer's own desk direction).
14. Your favourable direction (date of birth).
15. Your favourable colour (date of birth).
16. Thank-you. Welded page.
Total 16 cards per buyer (revised 19 Nov 2026 from 19: do and don't merged with quick fixes, door and sleeping reduced to a line each, entrance and sleeping pages removed). Design and CSS are copied from the shared theme; none of Career Intelligence's or Business Growth's text is reused (leak grep, §8). Every non-report element is hidden with `@media print` (§8).
Date-of-birth pages (14 and 15) stay as pages of the report by owner decision and are explicitly labelled as numerology-based. Their wording must say they come from the number-based tradition and the buyer's birth number, and must not present them as a Vastu direction rule or as a prediction. Their direction is shown as the buyer's number direction (a zone for something to be placed, not an instruction to face that way). They need the approved number tables.

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
1. Owner's seat and cabin: facing north or east, solid wall behind, visitor chairs opposite. The south-west of the room is traditionally preferred for the owner's seat; this is general guidance and the report does not check it, because the form does not ask where the seat is.
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
Shows: the desk-check verdict (ideal, acceptable, change recommended) and one date-of-birth tip. The fixes, the five segment cards and every other card stay locked and must not leak into the page source before payment.

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
- Event id (decided by the owner, 19 Nov 2026): keep the report id as `event_id`/`transaction_id` (`tracking.track_purchase`, called from `_deliver_paid_report`), provided it is opaque and holds no personal data. Checked: the create route copies `create_iq_test`, which sets `rid = secrets.token_urlsafe(12)`, a random id with no personal data. The report id is also the link to the report, so anyone with it can open the report. No change to shared code.

## 9. Gates (all must be green before any push; §10, §20)
Mock approved and printed to 323x623 pt PDF with page count equal to card count and nothing clipped; engine unit tests for every segment x every direction x every `desk_flexibility` value x door line, the number table, the "exactly five own-segment cards" check, and every input branch (§12); a real end-to-end test of the production path (create, order, verify, report) in DEMO_MODE; vocabulary scan; leak grep for other products' names; full `pytest`, Playwright E2E, robot smoke, `tests/test_report_buttons.py`; independent convergent audit written to `docs/audits/` (§20).

## 10. Open items for the owner
- Approve each cell of the direction matrix (section 3), especially the "acceptable" column and the extrapolated directions.
- Job seeker: keep the borrowed student and professional sets, or provide a source.
- Business owner cash box: sources split (SW opening north, north or east, or counter in the north or north-east); say which view the card follows.
- Number tables: Mulank only or Mulank and Bhagyank; Ketu and Mulank 7; approve the number-to-direction derivation and the colour lists.
- Whether Rs 99 stays after launch (struck-through price or offer timer on the page).
- Revision log, 19 Nov 2026: from an external review the owner pasted, adopted the 16-page structure, the `desk_flexibility` input, the explicit "own segment only" rule, the owner-seat correction, and one-line door and sleeping mentions. Not adopted by owner choice: moving the date-of-birth pages out of the Vastu findings (kept as two pages, with the careful wording in section 4).
- Who approves each segment's copy before it is written into code.

## 11. Build order
0 decisions (done except section 10) -> 1 this spec approved -> 2 visual mock approved -> 3 engine and tests -> 4 content -> 5 renderer -> 6 landing page and create route -> 7 payment wiring and DEMO_MODE test -> 8 tracking checks -> 9 gates and audit -> 10 launch checklist and owner go-ahead. Local commits only; push, PR and deploy only on the owner's explicit go-ahead each time.
