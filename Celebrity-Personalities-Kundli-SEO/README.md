# Celebrity / Personalities Kundli SEO — target data

> **BUILDERS START HERE → `PAGE-BUILD-RULES.md`** — the single consolidated checklist (accuracy, images, content, SEO, gates, publish). Do not build from memory.

`data.json` is the master target list for the celebrity kundli page pipeline.
One row per person. Sort/filter on `search_volume_monthly` (estimated monthly
kundli-intent searches, India) or `search_tier`.

## Schema
| field | meaning |
|---|---|
| `rank` | position when sorted by search interest |
| `name` | full name |
| `category` | cricket / bollywood / politics / business / spiritual / viral |
| `dob` | date of birth, YYYY-MM-DD — REQUIRED before a page is built |
| `pob` | place of birth |
| `tob` | time of birth, HH:MM IST, or null — NOT required (pages work without it; see the 3 live no-TOB pages) |
| `tob_status` | verified / disputed / unverified / none |
| `rodden` | Astro-Databank data-quality grade (AA best → DD conflicting, X no time, null = no entry) |
| `search_volume_monthly` | estimated monthly searches, kundli-intent keywords, India |
| `search_tier` | VERY HIGH / HIGH / MEDIUM / LOW |
| `search_evidence` | where the estimate comes from |
| `page_status` | live / needs_rebuild / not_built |
| `notes` | anything the builder must know before starting |

## Search-volume caveat
Volumes are ESTIMATES assembled from public SEO signals (AstroSage's celebrity
page prominence, keyword-tool screenshots in public SEO writeups, Google Trends
relatives). Real Keyword Planner numbers need an ads account — treat tiers as
reliable, exact numbers as directional.

## TOB policy (decided 22 Aug 2026)
TOB is optional. The engine publishes sign-level facts + dasha eras without it;
house claims are banned on any page whose TOB is missing or disputed. If a TOB
exists, record it AND its Rodden rating; the birth-time gate in the pipeline
decides how much of it is usable.
