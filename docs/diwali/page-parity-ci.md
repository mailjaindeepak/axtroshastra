# /en/diwali vs /en/career-intelligence: element parity (26 Oct 2026)

Compared `pages/diwali.html` with `pages/career-intelligence.html`, with a look at `jeevan.html`, `shaadi.html` and `milan.html`.
The rule was add only: every existing Diwali element stays, and anything new uses the Diwali palette, fonts and diya/garland look.
Status key: **present** = already on the Diwali page · **ADDED** = inserted in this pass · **n/a** = does not apply · **NOT COPIED** = left out on purpose.

| # | CI element / behaviour | Diwali status | What was done / why |
|---|---|---|---|
| 1 | Hero brand line + eyebrow | present | `.brand` "AxtroShastra · Diwali 2026" |
| 2 | H1 + sub line | present | |
| 3 | Hero `sub2` "55+ pages · Personalised · Private" | **ADDED** | `.sub2` "55+ pages · Made from your own chart · Private" (the sample is 58 pages; spec §1 estimates 55 to 62) |
| 4 | Hero kundli-diagram background | present (equivalent) | Diwali has its own toran, diyas and fireworks canvas |
| 5 | "View a sample report" hero button | present | `#heroSampleBtn` |
| 6 | Form: name, gender, DOB (DD/Month/YYYY), place autocomplete + hint + "city or district" note, WhatsApp +91 with note, submit, btn-note | present | |
| 7 | Time of birth hour/min/AM-PM + hidden `#f-tob` | present | kept (ids unchanged) |
| 8 | Time "Clear" button | **ADDED** | same JS as CI, Diwali styling `.tob-clear` |
| 9 | `.tob-toggle` "Don't know your exact birth time? … It's our specialty." + hidden `#tobApprox` "Approximate time" select | **ADDED** (Job 2) | replaces the "How sure are you of the birth time?" select (owner) |
| 10 | Time mapping to `/api/kundli` | **ADDED** (Job 2) | exact → `T0` + `tob`; part of the day → `T2` + `time_band` (`subah/din/shaam/raat` = `api.py` `BAND_MID` keys); "No idea at all" → `T3`. Partial time or ticked-with-no-band → inline error (CLAUDE.md §1) |
| 11 | Consent checkbox (Terms/Privacy) | present | injected server-side by `api.py`, not in the page file |
| 12 | 30-minute launch-offer countdown (`#offerTimer`, sticky clock) | **NOT COPIED** | owner + bugs.md: fake urgency |
| 13 | Strikethrough ₹999 anchor price | **NOT COPIED** | no real ₹999 price; the Diwali price is ₹499 everywhere, server-set |
| 14 | Trust strip (data quality, IIT–IIM alumni, speed) | present + **ADDED** | kept the 3 product facts; added "Exact planet positions" and "Built by IIT–IIM alumni". The engine uses Swiss Ephemeris, so "NASA JPL data" was not claimed |
| 15 | Calculating overlay with steps + progress bar | present | `#calcOv` |
| 16 | Preview cover card (brand, title, name, birth line, 5 questions) | present | |
| 17 | Cover "Report prepared <date>" | **NOT COPIED** | the free preview shows no month names (spec R3, `teaser` contract); the E2E month check covers the whole `#teaser` |
| 18 | Preview stat strip (14,200+ reports, 4.8★, 2 min) | present (equivalent) / **NOT COPIED** | Diwali `.strip` shows product facts (5+1 areas, 12 months, PDF). The hard-coded 14,200+ / 4.8★ were left out (owner) |
| 19 | Kundli drawing + planet table with strength badges | present | |
| 20 | Current Mahadasha bar | present | "Planet period now" fact box |
| 21 | Chart summary "N planets in strong positions" | **ADDED** | `#chartSum`, counted from the teaser's own `planets[].dignity` (exalted/own). No retrograde count because the Diwali teaser doesn't carry `retro` |
| 22 | About You / archetype / Career DNA bars / stat pills | n/a | specific to the career product; the Diwali equivalents are the Wrapped story and the emphasis card |
| 23 | Current phase card | present (equivalent) | `.card.emph` "Your report starts with …" |
| 24 | Locked 5 questions + teaser lines + "also in your report" grid | present | |
| 25 | Unlock CTA + sub note + "view the full sample" link | present | `#unlockBtn`, `.fine`, `#sampleOpen2` |
| 26 | In-preview social proof: 3 reviews + 3 credibility badges | **ADDED** | `.lb-proof` in `#unlock`: 3 new reviews in house style (no em/en dashes, §5c; no month names) + badges "Exact planet positions · IIT–IIM alumni · Secure payment" |
| 27 | Preview caption | present | `.tag` "Your free preview, made from your birth details" |
| 28 | Sample-report modal: page images, close, Esc, backdrop, focus return, hides nav | present | 58 `diwali-sample-NN.jpg` |
| 29 | Modal buy button (opens payment, or scrolls to form) | present | |
| 30 | Modal "Download full sample (PDF)" link | **NOT COPIED** | no `static/diwali-sample.pdf` exists; a link would be dead (CLAUDE.md §2) |
| 31 | Reviews section `.revs` | present | 7 reviews |
| 32 | Stats row (live `/api/count` "25,000+", "4.8★", "2 min") | **NOT COPIED** | owner: no counters. The rating is hard-coded, and the count is site-wide rather than for this product |
| 33 | "Why it's different" (2 blocks + IIT–IIM cred card) | **ADDED** | `section.why`, Diwali copy; dark card in the night-purple + marigold palette |
| 34 | Rectification "Don't know your exact birth time? … our specialty" | **ADDED** | `section.rectify#birthTime` in the night-sky style with diyas: a 3-row list (exact → rising sign; part of the day → Moon sign; no idea → Moon sign + birth-star check). The CI "30–40%" stat was dropped because nothing backs it |
| 35 | FAQ: accurate? / unknown time / when / computer-generated? / safe? | present + **ADDED** | added "Is this accurate?" and "Is this computer-generated?"; rewrote the unknown-time answer for the new toggle (question kept) |
| 36 | Final CTA | present | |
| 37 | Footer + "probability estimates, not guarantees" note | present + **ADDED** | note reworded as "… not certainties" (avoids the banned "guaranteed") |
| 38 | Sticky bar (hides on keyboard, shows after hero) | present | |
| 39 | Sticky: filled form + no preview → submits the form | **ADDED** | the submit handler still validates |
| 40 | Funnel events form_start / Lead / InitiateCheckout / begin_checkout / Purchase / oaiq | present | Diwali sends the real server amount, never a hard-coded value |
| 41 | `/api/order` → Razorpay → `/api/verify` → poll | present (better) | Diwali has the progress screen with fireworks |
| 42 | Contact-capture popup | n/a | the owner removed the popup (spec §4); the WhatsApp number comes from the form |
| 43 | EN/हिंदी `#axlang` toggle + state carry | n/a | no `/hi/diwali` route yet (Hindi ships after English, spec §1). Never link to a missing route |
| 44 | Astrologer / `static/acharya-*.jpg` block | n/a | CI doesn't use one (only `about.html` does) |
| 45 | WhatsApp share / PDF buttons | n/a on landing | they live on the report page (`_wire_report_chrome`), covered by the Purchase E2E |
| 46 | Exit / abandon behaviour | n/a | none on CI or the other pages |
| 47 | "People viewing now" / fake counters | **NOT COPIED** | owner |
