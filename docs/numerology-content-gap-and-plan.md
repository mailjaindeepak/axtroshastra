# Mulank content: gap analysis, recommended model, estimate and approvals (4 Nov 2026)

## 1. What exists and what is missing (measured from the repo)
| Content | Needed | Drafted | Notes |
|---|---|---|---|
| Mulank blocks M1-M9 (card 4, 8, 9) | 9 | 9 | strong sources for 1, 2, 3, 6, 8; planet disagreements for 4 and 7 |
| Bhagyank blocks B1-B9 | 9 | 9 | no Bhagyank-specific source for B2, B5, B9; one source each for B3, B4, B6, B7, B8 |
| Personal-year blocks Y1-Y9 (cards 11, 14) | 9 | 9 | Y3-Y9 drafted after this analysis was written (commit 69646b3); `lint_bank` clean. The note below on 2-1 only predates it |
| Pair statement PS (card 4, 8) | 81 | **1** | only 2-1 (single source) |
| Personality, dials, strengths table PB (cards 5-7) | 81 | **1** | only 2-1 (editorial, no source) |
| Bonds + compatibility CMP (card 10) | 81 | **1** | basis for the lists is an open owner decision |
| Lucky references LK (card 13) | 81 | **1** | the selection rule is an open owner decision |
| Planetary-links cells | 72 | 42 | the 30 Rahu/Ketu cells have no source: handled by the approved line 4i ("published tables differ"), so they are NOT blocking |

Today only pair 2-1 can be completed, and only for about 9% of 2-1 birthdays (those whose personal years are 1 then 2). After 1 January 2027 even that closes until Y3 exists. Every other pair and birthday is blocked by missing text, not by approval.

Size if authored per pair: PS 59 + PB 251 + CMP 86 words = about 400 words x 80 pairs = **about 32,000 words**, plus the lookups. Too slow for a fast launch, and for most pairs there is no source to base it on.

## 2. Recommended model: compose from per-number blocks (same cards, same layout)
Write content per number, not per pair, and combine at render time. The cards and wording slots stay as approved.
- Cards 4, 8, 9 already work this way (M and B blocks exist).
- Pair statement (card 4): one approved sentence template that combines the Mulank and Bhagyank themes and the relation line; keep the sourced 2-1 sentence as an override.
- Cards 5-7: a Mulank block (outer style: first impressions, how you decide, 4 dial positions, 5 strengths and growth rows) plus a Bhagyank block (direction: inner drive, what you grow toward). About 3,400 words.
- Card 10: 4 bond points per Mulank (about 800 words) plus 9 compatibility rows once the basis is decided.
- Card 13: a 9-row lookup (numbers, colours, days, gemstones per number) combined for the pair once the rule is decided.
- Years: Y3-Y9, 6 short fields each (about 800 words). **Do this first.**
Total new prose about 5,000-6,000 words plus two lookup tables, versus about 32,000. The owner approves about 27 units (9 Mulank, 9 Bhagyank, 9 years) instead of hundreds.

Honest limits: most of this text has no external source, so it must stay in the approved voice ("contemporary writers associate...", reflection prompts, the belief-system disclaimer on every card). B2, B5 and B9 are the weakest. That is the owner's call; the QC lint and the render guard catch incompleteness and wording problems, not accuracy.

## 3. Estimate (working days; assumes quick owner responses)
| Package | Effort | Depends on |
|---|---|---|
| Free preview + landing live | 2-4 days elapsed (4-6 with the preview redesign) | legal approval, PR review, deploy button |
| Y3-Y9 drafted | 0.5 | nothing (can start now) |
| Decisions 2.1-2.3 | 1-1.5 | owner |
| Data model + renderer for number-keyed content, with tests | 3-4 | decision 2.1 |
| Per-number drafting | 1.5-2 | decisions 2.1, 2.2 |
| Internal editorial review + owner approval | 2-4 | drafting |
| Render and visual QA of all 81 pairs and year combinations | 1-1.5 | renderer |
| Razorpay test mode, webhook, recovery | 1-1.5 | keys from the owner |
| Production checks, live keys, first purchase and refund | 0.5 | everything above |
**Paid product: about 10-14 working days end to end** (engineering and drafting overlap; the owner's review time and Razorpay keys set the pace). Confidence: moderate; the largest uncertainties are CI-only failures on Python 3.12, how many editorial revisions the owner wants, and Razorpay dashboard access.

## 4. Decisions needed from the owner now
1. Content model: approve the composed model (section 2), or choose per-pair authoring (about 3-4 weeks).
2. Name the internal editor and the approving owner (these names are stored with every approval).
3. Rules: how card 10 compatibility lists are chosen; how card 13 lucky references are chosen; which planet rules Mulank 4 (Rahu or Mercury) and Mulank 7 (Ketu or Neptune); how to word Bhagyank 2, 5 and 9, which have no source.
4. Legal text: privacy, terms, consent, marketing opt-in, refund policy (drafts ready).
5. Preview: keep as is or accept the redesign; keep or drop the Rs 499 strike-through (only honest if Rs 499 was a real price).
6. Slug and product name; homepage card; whether to remove `noindex` at launch.
7. Razorpay: test keys, then the webhook registration, then live keys (set by the owner with `eb setenv`).
8. Open the PR, review and merge it, and press the protected deploy.
9. The older wording decisions in the paid-report review (disclaimer density, "Neither is ranked", fallback wording) if they should change.