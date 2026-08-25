# Model build assignments — tier-mixed, updated as builds land

Standing rule (set 2026-08-22): VERY HIGH / HIGH tier celebrities must NOT all land on
one model. Both Opus 5 and Sonnet 5 get a genuine mix across all five search tiers.
This file is the single source of truth for "who's building whom" — update it every
time a page moves status. `data.json` carries the same `build_agent` / `page_status`
fields per row; this file is the human-readable view.

Already live (built before the tier-mixed split, not reassigned): Sachin Tendulkar,
Yuvraj Singh, Shah Rukh Khan, Hardik Pandya (Sonnet, https://claude.ai/code/artifact/fd5464ab-5ca6-4abf-bf05-98368e554751 —
photo coverage is genuinely thin: only 3 freely-licensed Commons photos of him exist, all
from one PM felicitation event 2024-07-04; 6 of 7 real-photo slots reuse those 2 source
frames under distinct crops, disclosed in the page's own footer; the 2018–19 timeline
tile is an honest gpx dead-end).

## Sonnet 5 — 10 assigned

Deploy-prep note (24 Aug 2026): all 9 rows below were dead-link-audited, stripped
to production HTML, given canonical URL + Person JSON-LD, and committed to
`axtroshastra/axtroshastra` on branch `feature/celebrity-kundli-pages`
(pages/celebrity/<slug>.html + new `/en/celebrity-horoscope-{slug}-kundli`
routes + `/en/celebrity` hub + `/en/coming-soon` fallback). Pushed to origin;
PR hand-off pending Commander review — not yet merged into aws-mysql or
deployed. Hardik/SRK/Sachin/Yuvraj held back for a later PR (Opus).

| Tier | Name | Status |
|---|---|---|
| VERY HIGH | Virat Kohli | **live_deployed** — pages/celebrity/virat-kohli.html — https://claude.ai/code/artifact/6cb1ecbf-f2e1-4269-943b-83be6b385ba7 |
| VERY HIGH | MS Dhoni | **live_deployed** — pages/celebrity/ms-dhoni.html — https://claude.ai/code/artifact/6ba67425-6293-467d-9672-f05d2bce63ff |
| HIGH | Rohit Sharma | **live_deployed** — pages/celebrity/rohit-sharma.html — https://claude.ai/code/artifact/3d9783d7-5ee5-4fac-adc0-a9a69a762bb3 |
| HIGH | Katrina Kaif | **live_deployed** — pages/celebrity/katrina-kaif.html — https://claude.ai/code/artifact/580f6fff-7958-4b99-8e67-769e38810e14 |
| HIGH | Deepika Padukone | **live_deployed** — pages/celebrity/deepika-padukone.html — https://claude.ai/code/artifact/c6532fc0-da45-4965-9b00-944f23f875f4 |
| MEDIUM-HIGH | Kareena Kapoor Khan | **live_deployed** — pages/celebrity/kareena-kapoor-khan.html — https://claude.ai/code/artifact/3ecdb8ff-5535-463e-a090-df9ecb1f5465 |
| MEDIUM | Rashmika Mandanna | **live_deployed** — pages/celebrity/rashmika-mandanna.html — https://claude.ai/code/artifact/8a7ec5c6-6592-4f08-9ada-a380d7d8ceef |
| MEDIUM | Alia Bhatt | **live_deployed** — pages/celebrity/alia-bhatt.html — https://claude.ai/code/artifact/388c9e42-b767-4b26-95f0-0bcd95262032 |
| MEDIUM | Anushka Sharma | **live_deployed** — pages/celebrity/anushka-sharma.html — https://claude.ai/code/artifact/58db0d93-69f6-4dfa-8c1d-bccd2e05bfe3 |
| LOW-MEDIUM | Ravi Kishan | **blocked** — DOB uncertainty (1969 vs 1971) unresolved, skipped per §1.6 until resolved |

## Opus 5 — 10 assigned

| Tier | Name | Status |
|---|---|---|
| VERY HIGH | Narendra Modi | queued |
| VERY HIGH | Amitabh Bachchan | queued |
| VERY HIGH | Aishwarya Rai Bachchan | queued |
| HIGH | Salman Khan | queued |
| HIGH | Mukesh Ambani | queued |
| HIGH | Dharmendra | queued |
| MEDIUM-HIGH | Rahul Gandhi | queued |
| MEDIUM-HIGH | Smriti Mandhana | queued |
| MEDIUM | Yogi Adityanath | queued |
| MEDIUM | Vaibhav Sooryavanshi | queued — age 14, editorial framing (praise-only, no marriage/spice content) still needs a final call before building |

## Tier balance check

| Tier | Opus | Sonnet |
|---|---|---|
| VERY HIGH | 3 | 2 |
| HIGH | 3 | 3 |
| MEDIUM-HIGH | 2 | 1 |
| MEDIUM | 2 | 3 |
| LOW-MEDIUM | 0 | 1 |

Neither model is stacked with all the top-traffic names — both carry real VERY HIGH /
HIGH volume alongside lower-tier work.

## Process per page (PAGE-BUILD-RULES.md, no drift)
1. Read `PAGE-BUILD-RULES.md` first, state which build mode applies (TOB verified vs
   no-TOB vs disputed-TOB-disclosed).
2. Orchestrating session does chart computation (engine.py), biography research,
   image sourcing (Commons API, uniqueness + face-visible gates), keyword check
   (data.json already has harvested keywords for all 24 rows — re-run `_harvest.py`
   only if a name isn't in data.json yet).
3. A build agent gets a complete, fact-locked brief and does content writing +
   HTML assembly only — no re-research, no new image sourcing.
4. Orchestrating session runs the §5 quality-gate checklist, then publishes.
5. Update `page_status` here and in `data.json`.
