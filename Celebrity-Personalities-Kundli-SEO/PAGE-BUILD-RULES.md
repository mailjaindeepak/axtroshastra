# PAGE-BUILD-RULES — the single checklist for every celebrity kundli page
Consolidated 23 Aug 2026. This file is the operating manual. If a rule here
conflicts with memory or habit, THIS FILE WINS. Detailed rationale lives in
docs/celebrity/*.md; this is the checklist you actually run.

⛔ MANDATORY FIRST STEP — before starting ANY new page, the building agent
   (Claude Code session, subagent, or API pipeline) READS THIS FILE top to
   bottom and states which build mode applies (see word budget below). A build
   that starts without reading this file is a drifted build: stop and restart.

════════════════════════════════════════════════════════════════════════
## 0 · THE PRIME RULE — never build from scratch
The pipeline exists. Design, format, boilerplate and engine are FIXED assets.
Per-page work is exactly three jobs:
   (1) RESEARCH   — arcs, keywords, birth-data verification
   (2) CONTENT    — see WORD BUDGET (content rule 8): interactive Claude Code
                    builds = quality first, no hard cap; API pipeline builds =
                    LLM-generated words capped at 2,500
   (3) PHOTOS     — source + crop under the image gates
Anything beyond those three jobs is drift. Stop and check this file.

### Fixed assets (reuse, never recreate)
| Asset | Where |
|---|---|
| Design system (CSS, 2 skins, scrim, gold #E5B25A) | scratchpad v7_style.css → to be committed as static/celebrity.css |
| SVG ornaments (mandala, constellation, orn divider) | _bgart.txt / _orn.txt partials |
| Section format (11 sections, hero→TL;DR→graph+timeline→spice→arcs→planets→facts→chart→lessons→explore→CTA) | any live page is the reference |
| Reusable lessons + CTA + tag-rule copy | live pages (identical blocks) |
| Engine | axtroshastra/engine.py (compute_chart, vimshottari_tree) |
| Target data + keywords | Celebrity-Personalities-Kundli-SEO/data.json |
| Keyword harvester | _harvest.py (re-run for any new celeb) |
| Shared CTA photos (per category, NOT planet photos — see §2.11-12) | shared-assets/ (see MANIFEST.md) — reuse verbatim, don't re-source |
| Image-completeness auditor (structural only, not a quality check) | _audit_images.py <page.html> — run before every publish |

════════════════════════════════════════════════════════════════════════
## 1 · DATA & ACCURACY GATES (run before writing one word)
1. Engine computes EVERYTHING. The LLM never states a placement it wasn't handed.
   (The Hardik PDF was wrong on 4/10 placements. Never trust prose sources.)
   HOW TO CALL IT — exact signatures, and the trap that has already bitten twice:
     from datetime import datetime, timedelta
     import engine
     birth_utc = datetime(Y,M,D,HH,MM) - timedelta(hours=5, minutes=30)   # IST -> UTC
     r = engine.compute_chart(birth_utc, lat, lon)      # (dt_utc, lat, lon_geo)
     g = r["grahas"]        # dict: "Sun","Moon",... -> Graha(lon, sign, nak, pada,
                            #        dignity, combust, retro)
     tree = engine.vimshottari_tree(g["Moon"].lon, birth_utc, horizon_end)
   ⚠️ `Graha.sign` and `Graha.nak` are ZERO-INDEXED. Use SIGNS[g.sign] and
      NAKSHATRAS[g.nak] — NOT [g.sign - 1]. An off-by-one here shifts EVERY sign on
      the page by one (Pisces printed as Aquarius, Sagittarius as Scorpio) and looks
      completely plausible. Always sanity-check one planet by hand before trusting the
      table: int(lon // 30) must equal g.sign.
   ⚠️ compute_chart returns keys ["jd","grahas","lagna_lon","lagna_sign"] — there is no
      "planets" key, and Graha objects are not JSON-serializable.
   VERIFY against tests/celebrity_charts.json when the person has a row there.
2. BIRTH-TIME GATE: run the chart at every competing TOB.
   ⛔ RUN THIS FIRST, BEFORE ANY OTHER WORK ON THE PAGE:
        python3 _tob_crosscheck.py "<Celebrity Name>" --lat <lat> --lon <lon>
   It collects EVERY birth time we hold across data.json and
   axtroshastra/tests/celebrity_charts.json, computes all of them, and tells you which
   signs are stable, whether the Moon's nakshatra flips, and whether the lagna moves.
   ⚠️ data.json's `tob` and `rodden` fields are NOT authoritative. As of 25 Aug 2026,
   FIVE of the six celebrities present in both files carry CONTRADICTORY birth times —
   including two labelled "Rodden A", which §1.3 would otherwise read as licence for
   house-based claims:
       Amitabh Bachchan  03:30 (DD) vs 16:00 ("Accurate")  — 12.5 hours apart
       Shah Rukh Khan    06:25 (A)  vs 02:30 ("Reference")
       Salman Khan       10:45 (A)  vs 14:30 ("Accurate")
       Sachin Tendulkar  13:00 (A)  vs 14:25 ("Reference")
       Virat Kohli       none  (DD) vs 10:28 ("Dirty")
   Two build agents caught this the hard way, one after the other, each having nearly
   shipped a page asserting a time the repo itself contradicts. Do not be the third.
   If the sources disagree AT ALL, it is a disputed-TOB build no matter what `rodden` says,
   and you must correct data.json's tob_status so the next build does not inherit the
   false confidence.
   ⚠️ A NAKSHATRA FLIP IS NOT JUST A DATE PROBLEM. The birth nakshatra sets the Vimshottari
   dasha LORD SEQUENCE. Amitabh's Moon is in Chitra at 03:30 and Swati at 16:00 — Mars-ruled
   vs Rahu-ruled — so the two candidate times give two entirely different dasha ladders.
   When the nakshatra flips you may publish NO dasha order at all, only the signs.
   - Nakshatra stable across the dispute → dasha ORDER publishable. See the hard
     warning below before you publish any dasha DATE.
   - Nakshatra flips → eras with explicit disclosure (SRK model).
   - No TOB at all → no-TOB page (Hardik model).
   ⚠️⚠️ NAKSHATRA STABILITY DOES **NOT** MAKE DASHA DATES PUBLISHABLE. This rule used
   to read "nakshatra stable → dasha sequence publishable as eras", which is WRONG and
   nearly shipped fabricated timelines on two pages (24 Aug 2026, caught by the Yogi
   Adityanath build agent escalating under §7H).
   WHY: the Moon travels ~12-13° per day and a nakshatra spans only 13°20'. So even when
   the Moon stays inside ONE nakshatra all day, its position WITHIN that nakshatra — which
   is exactly what sets the Vimshottari balance-at-birth — sweeps almost the entire span.
   The dasha ORDER is fixed by the nakshatra; every DATE slides with the unknown minute.
   MEASURED EXAMPLES (full-day sweep, both nakshatra-stable):
     Yogi Adityanath 1972-06-05  → 1st mahadasha ends anywhere 1973 … 1985;
       the mahadasha running TODAY is Ketu or Venus depending on the hour.
     Vaibhav Sooryavanshi 2011-03-27 → Venus mahadasha ends anywhere 2014 … 2028
       (a 14-year swing); the mahadasha running TODAY is Venus, Sun OR Moon. His Moon
       also LEAVES Purva Ashadha at 22:26 IST, so even the dasha ORDER only holds for
       93.5% of the day — after that it starts at Sun, skipping Venus. Disclose that
       boundary rather than claiming full stability (found by the build agent, 24 Aug).
   ⚠️ SWEEP AT FINE GRANULARITY — 10 MINUTES, NOT 3 HOURS. I originally swept this chart
   at 3-hour steps, concluded "nakshatra stable all day", and wrote that into this file.
   It was wrong: a coarse sweep steps straight over a boundary that sits at 22:26. A
   nakshatra boundary can fall anywhere, and missing one makes an unstable chart look
   stable — the most dangerous possible error, because it licenses claims the data does
   not support. Sweep every 10 minutes, then bisect to find the exact boundary minute,
   and REPORT the percentage coverage rather than a bare "stable".
   THEREFORE, on any page without a verified minute:
     - PUBLISH the dasha LORD ORDER (Jupiter → Saturn → Mercury → …). That is real.
     - DO NOT publish dated dasha periods, "he was in X dasha when Y happened", or any
       claim about which dasha is running now. Those are inventions dressed as computation.
     - Before writing ANY dasha date, sweep the day and check the spread yourself. If the
       first-mahadasha end moves by more than a few months, dates are off the table.
     - A narrative hook built on "this event fell in his X period" is DEAD unless the
       minute is verified. Find the hook in the SIGNS instead (dignity, own-sign,
       debilitation, combustion, nakshatra symbolism) — those hold all day.
3. NO HOUSE CLAIMS unless TOB is verified (Rodden A/AA and undisputed).
   No lagna, no marriage house, no manglik VERDICT — ever, on disputed pages.
   The manglik question is ANSWERED honestly (sign-level + "houses need the minute").
4. Eras, not exact dates, whenever TOB is anything less than verified.
5. Birth-time status disclosed on-page in ≥3 places: chart caption, lesson, footer.
6. DOB itself uncertain (e.g. Ravi Kishan 1969/1971)? Resolve before build or skip.

════════════════════════════════════════════════════════════════════════
## 2 · IMAGE GATES (docs/celebrity/image-sourcing-rule.md is the long form)
1. Source via a LICENCE-VERIFYING API. The API response IS the verification —
   never accept filenames/licences from a model, a chat, or a web page.
   Permitted APIs:
     a) Wikimedia Commons API (search + category) — always try this FIRST.
     b) Openverse API (api.openverse.org) — no key required; aggregates Flickr and
        other CC sources and returns a machine-readable `license` + `license_version`
        field. Use ONLY when (a) is sourcing-exhausted.
     c) Flickr API — only if an API key is available; same licence gate as (b).
   (EXTENDED 24 Aug 2026: Hardik Pandya's page hit a hard wall — Commons contains
   exactly 3 freely-licensed photos of him, ALL from one July 2024 PM event, so
   Commons-only sourcing could only ever produce 9 crops of 3 photos plus a glyph.
   That is the "repeated pics + empty glyph" defect the user rejected. The §2.2
   licence whitelist was always about the LICENCE, not the host; §2.1 restricted the
   host purely for verification integrity, which Openverse/Flickr APIs also satisfy.)
   ⚠️ NOT ALL "CREATIVE COMMONS" IS USABLE HERE. AxtroShastra is a COMMERCIAL site
   and every image is CROPPED to the slot. Therefore:
     - NonCommercial (NC) licences are BANNED — commercial site.
     - NoDerivatives (ND) licences are BANNED — we crop, which is a derivative.
   Allowed Flickr/Openverse licence values ONLY: CC-BY (Flickr id 4), CC-BY-SA (5),
   "No known copyright restrictions" (7), US Government Work (8), CC0 (9),
   Public Domain Mark (10). Reject ids 1, 2, 3, 6 (all NC and/or ND).
   Everything in §2.2's BANNED list stays banned no matter which API surfaced it —
   a press-wire image does not become usable because someone re-posted it under a
   CC tag. Apply the §2.2 recropped-press-wire and watermark checks to every
   non-Commons hit, and record which API + licence id each photo came from.
2. Licence whitelist: CC-BY, CC-BY-SA, CC0, public domain, GODL-India.
   BANNED: Getty, AFP, PTI, Reuters, AP, IPL/BCCI official, iStock/stock,
   wallpaper sites, fan-page reposts, AI-generated.
   BOLLYWOOD PRESS AGENCIES (Bollywood Hungama etc.) — CONDITIONAL, not outright
   banned (revised 23 Aug 2026: Anushka Sharma's page was sourcing-exhausted —
   ~70+ of the only Commons files of her are Hungama-credited, and excluding
   them left no way to fill 9 required slots). Allowed ONLY with per-photo
   verification, because Hungama is also where the original mislabeling incident
   came from (a Hungama file on Alia's page was captioned as her but showed an
   unrelated person):
     - Open the actual image and visually confirm it really is the subject —
       never trust the filename/caption.
     - Reject anything watermarked, or that reads as a reused/recropped press
       wire image rather than original photography. Resolution alone is judged
       by the visual-sharpness-at-display-size standard in §2.4, not a raw
       pixel-count cutoff.
     - Prefer non-Hungama sources first; reach for Hungama only once a genuine
       broadened search (see §2.11) comes up short.
3. QUALITY BAR: the Sachin/SRK V3 pages are the visual benchmark — sharp,
   well-lit, deliberately cropped, colour-graded to the palette. If the best
   available photo looks worse than that bar after treatment, prefer the
   glyph-panel degraded mode over shipping a muddy image.
4. RESOLUTION — visual check, not a hard pixel floor (REVISED 23 Aug 2026: Anushka
   Sharma's page hit a real wall where ~90 of ~90 Commons files of her were under
   the old numeric floor, meaning the floor itself — not sourcing effort — was
   about to force empty slots, the exact defect the user has already flagged
   twice). Old guide numbers, now a starting expectation rather than a hard gate:
   hero ~1400px short side (4:3 crop; canvas-extend right so subject sits ~30%) ·
   cards ~800w · arcs ~1000w · band ~1600×900.
   - When nothing available clears these numbers: crop the best candidate to the
     EXACT aspect ratio and size the slot displays at (check the page's own CSS —
     `.pc .im`/`.mo .mim` aspect-ratio), decode the result, and LOOK at it. Ship
     it only if the face reads sharp and legible at that actual display size.
     Reject it if it looks soft/muddy/pixelated at that size — that's still a
     real fail, just judged by eye instead of by a pixel count.
   - This does not relax the WATERMARK or RECROPPED-PRESS-WIRE checks (§2.2) —
     those are still hard rejects regardless of how sharp the image looks.
5. UNIQUENESS: every slot a distinct photograph — distinct FRAMES, not files.
   Two shots from one event/burst = duplicates. Track source event per slot.
6. FACE VISIBLE: simulate the exact display crop (cards 16:10, arcs 16:7, hero
   both breakpoints), render a contact sheet, and LOOK. Face cut/hidden = fail.
   Exception: the CTA atmosphere band (contains no person).
   SOLO PREFERRED, GROUP ACCEPTABLE (user decision, 24 Aug 2026 — Hardik Pandya's
   page could not be filled from solo photos alone): a photo does NOT have to be a
   solo portrait. Order of preference:
     1st — solo photo of the subject;
     2nd — the subject in a group/with another person.
   A group photo is fully acceptable as long as ALL of these hold:
     - the subject is genuinely, unambiguously identifiable — verify by eye, and
       state in the report HOW you identified him (kit number, position in frame,
       the file description naming him). Never assume from a filename.
     - after cropping toward him for the slot's aspect ratio, his face still reads
       sharp and legible at the ACTUAL display size (§2.4). A team photo where he
       is 40px tall fails this — cropping in far enough to see him makes it mush.
     - the caption is honest about what the photo actually is ("with the T20 World
       Cup squad", "receiving X alongside Y") — never imply a solo portrait.
   ⚠️ COMMONS PUTS FILES IN **MONTHLY** SUBCATEGORIES, NOT YEAR CATEGORIES. This is the
   single most common reason an era looks "sourcing-exhausted" when it is not. Narendra
   Modi's 2001-2013 Chief Minister era appeared to have nothing because
   "Category:Narendra Modi in 2013" is nearly EMPTY — the files live in
   "Category:Narendra Modi in September 2013" and its eleven siblings. Walking the monthly
   subcategories turned a declared dead end into 10 accepted, dated, licence-clean photos.
   ALWAYS walk `Category:<Person> in <Month> <Year>` before concluding a period is empty.
   ⚠️ NEVER GUESS A SUBCATEGORY NAME — ENUMERATE THE PARENT. Commons naming is not
   predictable, and a guessed name returns an empty result that looks exactly like
   "nothing exists". A sourcing session generated its own false negative this way: it
   guessed `Category:Vibrant Gujarat Global Summit 2015`, got nothing, and nearly recorded
   the tree as exhausted — the real name is YEAR-FIRST, `Category:2015 Vibrant Gujarat`.
   Always list a parent's actual subcategories (`list=categorymembers`, `cmtype=subcat`)
   and walk what is really there.
   ⚠️ A PERSON CATEGORY'S FILE COUNT IS NOT THE CEILING. `Category:Mukesh Ambani` holding
   33 files is not evidence that Commons has only 33 — the monthly subcats, the event and
   summit trees, and files catalogued under OTHER people all sit outside it.
   ⚠️ OPENVERSE: EXPECT ~ZERO NET YIELD; run it LAST, never instead of a direct Commons
   sweep. It re-indexes Commons (a strict SUBSET of a direct sweep, and it lags deletions
   by years — four "finds" on one subject were all files deleted from Commons) plus Flickr,
   which is overwhelmingly NonCommercial and therefore banned here. Re-verify every hit
   against the Commons API before believing it exists.
   ⚠️ ALSO CHECK THE SHARED INDEX FIRST — `python3 _image_index.py usable <slug>` and
   `rejected <slug>`. Rejections carry SWEEP-RESULT notes recording what was already tried
   and what was deliberately excluded, so nothing gets re-searched or wrongly "rescued".
   ⚠️ SEARCH IMPLICATION, and this is the part that gets missed: group photos are
   usually catalogued under the EVENT or the TEAM, not the person, so a search for
   the celebrity's name alone will never surface them. When a subject looks
   sourcing-exhausted, search Commons CATEGORIES for their teams, tournaments,
   squads, award ceremonies and tours before concluding nothing exists.
7. DEGRADED MODE — LAST RESORT ONLY, AND ONLY AFTER EVERY §2.1 API IS EXHAUSTED.
   (HARDENED 24 Aug 2026: the user has now rejected glyph panels on sight three
   separate times — "empty glyph area even though i mentioned it should not be
   there". Glyph panels are NOT a convenient fallback, and "Commons came up short"
   is NO LONGER sufficient justification for one, because §2.1 now permits
   Openverse/Flickr CC sourcing.)
   Before ANY glyph panel ships, all of these must be true and stated in writing:
     - Commons API exhausted (multiple query strategies + category walk), AND
     - Openverse API exhausted for the same subject, AND
     - the shortfall is genuine unavailability, not a resolution/sharpness
       preference — a real photo that passes §2.4 always beats a glyph.
   If a slot still cannot be filled, prefer REMOVING the slot (shorten the
   timeline) over shipping a visible empty glyph panel. Never a silent
   substitution, never a press image, never a second crop of a frame already used
   elsewhere on the page (that is the §2.5 duplicate defect, not a fix).
8. Every image ships with photographer + licence → footer attribution block.
9. "file photo" caption on any arc image that isn't from the described event.
10. IMAGE COMPLETENESS (Kohli V1 incident, 22 Aug 2026 — a build agent used the .gpx
    glyph fallback for 4 planet cards and dropped the CTA photo entirely, and it LOOKED
    intentional enough that nobody caught it until the user did):
    - The .gpx glyph-fallback class exists for EXACTLY ONE situation: no freely-licensed
      photo of the KUNDLI SUBJECT THEMSELVES exists for a specific life-era timeline
      slot. That's it. Never for a planet card, never for the CTA.
    - Before returning ANY built page, run:
      `python3 Celebrity-Personalities-Kundli-SEO/_audit_images.py <page.html>`
      A non-zero exit means the page is not done. Fix and re-run. NOTE: this script
      only checks that image slots are non-empty — it cannot judge photo quality, crop
      correctness, or whether an image is the right SUBJECT. A clean exit is necessary,
      not sufficient. It does not replace looking at the rendered page yourself.

11. PLANET CARDS USE PHOTOS OF THE CELEBRITY — NEVER stock imagery, NEVER text-only
    (CORRECTED TWICE — 22 Aug 2026 batch-2 incident, then corrected AGAIN 23 Aug 2026
    after a build "fixed" the batch-2 incident by stripping the images out entirely and
    shipping text-only kicker labels instead. The user's exact words: "who told u to
    remove them, i clearly said that it should not have planet photo, instead have the
    respective person photo, but u completely remove it." Checked against the real
    Sachin/SRK artifacts: their `.pc .im` slots hold real photos of THE CELEBRITY —
    decoded one from Sachin's page and it's him on the field in his Sahara jersey.
    There is no astronomy imagery anywhere in the real design, and there is no
    text-only planet card anywhere in the real design either):
    - A "planet card" is a themed section about one placement (e.g. "Sun — debilitated"),
      illustrated with a real, distinct photo of the celebrity that fits that placement's
      story — not a photo of the Sun. The shared-assets/planets/ NASA library was a
      fabrication and must not be used anywhere, on any page, ever.
    - EVERY planet card gets a real photo. EVERY timeline/arc slot gets a real photo.
      This means sourcing 4+ additional real photos per page beyond the hero/CTA —
      same method as every other slot (Commons API, licence whitelist, uniqueness,
      face-visible), just more of them. This is more work, not a shortcut.
    - "No good photo turned up in the first search" is not a stopping point. Broaden the
      query (event name, award name, teammate/co-star name, year, venue), accept an
      honestly-captioned era-adjacent "file photo" over leaving a slot empty, and only
      after that broadened search still comes up empty does a slot go without a photo.
    - CORRECTED AGAIN, 23 Aug 2026 — the "last resort" framing above was still too soft:
      after this exact defect (`.gpx` glyph tiles and one genuinely empty tile) turned
      up simultaneously on 6 of 9 pages, all traceable to searches that stopped at the
      literal described era/event instead of the celebrity's WHOLE career. `.gpx` and
      text-only are no longer an acceptable resting state, full stop — not even as a
      flagged last resort. Before ever landing on one: widen the search to ANY era of
      that person's public life (not just the one the slot's copy narrates), accept a
      real, clearly-identifiable, honestly "file photo"-captioned image from a
      completely different year/event if that's what's available, and only reach for
      `.gpx` if literally zero freely-licensed photos of the subject exist anywhere —
      which should be vanishingly rare for any public figure with a built page. If that
      genuine dead-end happens, stop and ask the user before publishing rather than
      shipping the glyph silently.

12. CTA BACKGROUND — ONE fixed photo per category, reused verbatim, never re-sourced
    per page (CORRECTED, 22 Aug 2026 — builds were each re-sourcing or reprocessing
    their own CTA image per page, producing inconsistent, sometimes poor-quality
    results; one page's independent pick was visibly low-quality and got called out):
    - Exactly one photo per category, stored in shared-assets/cta-<category>-common.jpg,
      used byte-for-byte identical across every page in that category. Do not crop it
      differently, re-blur it, or swap in an alternative per page.
    - Established so far: `cta-cricketer-common.jpg` (packed floodlit stadium, sourced
      from the live Sachin page — confirmed correct, keep as-is) and
      `cta-bollywood-common.jpg` (Raj Mandir cinema hall facade, Jaipur — sharp, no
      identifiable named individual, real GODL/CC licensing).
    - A new category with no shared photo yet: source ONE real, sharp, evocative,
      no-named-individual atmosphere photo, save it to shared-assets/, add it to
      MANIFEST.md, and it becomes that category's fixed photo from then on. Do not let
      two parallel builds each source their own — check MANIFEST.md first.

13. STRUCTURAL LAYOUT — verify NESTING, not just counts (CORRECTED, 22 Aug 2026 — a
    build put a `</div><!-- /wrap -->` right before the FAQ section instead of right
    before the final CTA section, so FAQ + People-Also-Search rendered full-width/
    unconstrained on 5 of 9 pages. A prior "div balance" check only counted opens vs.
    closes and missed this, because the COUNT was still correct — just the ORDER wasn't):
    - The real design closes `.wrap` exactly once, immediately before the final CTA
      section (`<div class="cta">`), which is intentionally full-bleed. Every other
      section — including FAQ and People-Also-Search — stays INSIDE `.wrap`.
    - Checking div open/close COUNTS is not enough to catch a misplaced closing tag.
      Verify structurally: confirm the text immediately before `<div class="cta">` is
      `</div><!-- /wrap -->`, and that no other `/wrap` comment appears earlier in the
      document body.
    - More generally: when self-auditing HTML structure, check ORDER/NESTING against
      a real reference page, not just that bracket counts match.

14. INTERNAL LINKS — never link to a page that doesn't exist yet (NEW, 24 Aug 2026 —
    found live on 11 of 13 published pages: capsule pills AND inline prose links
    pointing at family members/co-stars/spouses with no built page — e.g. Katrina's
    page linked "Vicky Kaushal kundli" three times, Kareena's linked Saif Ali Khan,
    Taimur, Jeh and Karisma Kapoor, none of which exist):
    - Before linking to `/en/celebrity-horoscope-<slug>-kundli` (capsule pill OR
      inline text, e.g. "curious about his chart? [link]"), check the slug is
      `page_status: live*` in data.json. If it isn't — including names never added
      to data.json at all — do NOT link the real slug.
    - Route the link to `/en/coming-soon?name=<Display+Name>` instead (URL-encode
      spaces). This shared page (`coming-soon.html`, Royal Parchment skin, lists
      every currently-live kundli) exists specifically for this. Never leave the
      anchor text or styling looking different — same pill/link, different href.
    - Guide pages (`/en/guides/*`), category hubs (`/en/celebrity/<category>`),
      and the `/en/kundli` funnel are NOT covered by this rule — they're
      site-wide infrastructure, not per-celebrity long-tail pages.
    - Grep every new page for `href="[^"]*celebrity-horoscope-[^"]*"` before
      publish and check each slug against data.json's live rows.

════════════════════════════════════════════════════════════════════════
## 3 · CONTENT RULES
1. Voice: plain English, Gen-Z-leaning but meaningful slang, bullets over walls
   of text, technical terms only at section ends with anchors. No jargon dumps.
2. Every claim about the person's life = public record. Where someone was
   CLEARED, the clearance travels with the claim in the same breath
   (Aryan Khan model). Pending legal matters: stated as pending, never judged.
3. NEVER: crime/affair/addiction claims, house-level divorce "analysis",
   astrology-as-blame for any real event.
4. HEALTH RULE: document medical facts only as the person made them public;
   never imply the chart predicted/caused/explains illness (Yuvraj model).
5. MINORS: praise-only framing, no spice/marriage/relationship content
   (Vaibhav flag). Prefer skip if in doubt.
6. POLITICIANS: strict neutrality; no election predictions as fact — frame
   "what astrologers discuss" vs what we compute (Modi/Rahul/Yogi).
7. MEMORIAL (deceased, e.g. Dharmendra): respectful tone, no spice section.
8. WORD BUDGET — two build modes:
   a) INTERACTIVE (Claude Code session, like now): no hard cap — quality and
      completeness first; still write lean, but never cut disclosures to save words.
   b) API PIPELINE (future bulk runs): LLM-generated prose ≤2,500 words HARD CAP —
      it is the paid portion. Boilerplate and engine-templated blocks don't count.
      At the cap, per-page LLM cost ≈ ₹13.5 (Opus 5) / ₹5.4 (Sonnet 5) at ₹90/$
      (~4,325 output + ~8,300 input tokens; batching + caching roughly halves it).
      If a draft runs over, cut the weakest section — never disclosures or FAQ.
9. The hook comes FROM the computed chart (debilitated Sun, era handover,
   two-exalted-two-debilitated). Find it in the data; don't force a template hook.

════════════════════════════════════════════════════════════════════════
## 4 · SEO RULES — smart, never forced  (NEW, 23 Aug 2026)
Source: per-celeb harvested queries in data.json → seo_keywords.queries
(real Google autosuggest, gl=IN). 15-60 real queries per celeb.

PLACEMENT TIERS — where keywords go:
   T1 <title>: "<Name> Kundli — Birth Chart, Nakshatra & Dasha Analysis | AxtroShastra"
   T2 meta description: name + kundli + birth chart + nakshatra + birth time, one sentence.
   T3 H1 zone: "Kundli" visible near the name (tag chip).
   T4 body, NATURALLY: kundli · janam kundli · birth chart · birth time ·
      zodiac sign · nakshatra · horoscope — each ≥1×, inside real sentences.
   T5 FAQ block: question-form queries answered honestly
      ("is <name> manglik", "<name> birth time", "and <partner> kundli matching").
   T6 People-also-search block: family_confirmed + related links.

THE SMART RULE — this is a ranking rule, not a checkbox rule:
   - A keyword may ONLY appear inside a sentence that would survive editing if
     the keyword were removed. If deleting the phrase breaks nothing, it was
     stuffing — rewrite or drop.
   - Never repeat any exact keyword phrase >3× in body copy.
   - Never paste the harvested list anywhere on the page. It is a coverage
     checklist for the AUDIT, not content.
   - Question-form queries → FAQ answers. Couple queries → one natural mention
     + compatibility CTA. Language variants (in hindi / tamil) → the hindi-page
     link satisfies them; do NOT sprinkle "in tamil" into English copy.
   - Density sanity: "kundli" family ≤ ~2% of body words. Reads-like-a-human
     beats exact-match count every time.

AUDIT: grep the built page for T4 terms (all must hit) + count exact-phrase
repeats (≤3) + confirm FAQ answers ≥2 question-form harvested queries.

════════════════════════════════════════════════════════════════════════
## 5 · QUALITY GATES (all must pass before publish)
□ Engine cross-check: every on-page placement == engine output
□ Birth-time gate decision recorded (verified / disputed-eras / no-TOB)
□ Image gates: licence + resolution + uniqueness + face-visible contact sheet
□ Structural audit: `_audit_images.py <page.html>` exits 0 — run this YOURSELF, never
  trust a build agent's self-report of having run it. The script was extended 24 Aug 2026
  and now covers far more than images; a PASS today means more than a PASS did last week:
    checks 1-9   images: count, .gpx cap, CTA photo, banned stock, wrap ORDER,
                 every .pc and .mo actually holds a photo, truncated data URIs
    check 10     every href="#x" resolves to a real id="x"  (Yuvraj shipped a dead
                 #p-manglik pill)
    check 11     no claude.ai <!-- frame-runtime --> wrapper, no doubled doctype/head/body
                 (two agents republished the wrapper and silently lost the <title>)
    check 12     >=3 FAQ blocks  (Deepika shipped with ZERO; Sachin/SRK/Yuvraj too)
    check 13     near-duplicate photos by colour signature  (Hardik shipped 9 images that
                 were 3 photos re-cropped; every byte-hash was unique, so hashing missed
                 it and the user caught it by eye)
    check 14     no link to a celebrity slug that is neither built nor in data.json
□ Keyword audit (T4 complete, no stuffing, FAQ coverage)
□ Contrast AA: worst text ≥4.5:1 in BOTH skins (incl. hero over scrim)
□ Hero: face never covered by the name at any breakpoint; scrim present;
  hook highlight = #E5B25A standard
□ Layout: no horizontal overflow at 375px; tables scroll in-container;
  timeline badges z-index above arc photos; graph at standard (no min-width hack)
□ Structure: divs balanced AND correctly nested/ordered (§2.13) — verify the text
  immediately before `<div class="cta">` is `</div><!-- /wrap -->`; every class has CSS;
  zero broken anchors
□ Planet cards (if any) use real, distinct celebrity photos or ship text-only — never
  stock/astronomy imagery (§2.11)
□ CTA uses the exact shared category photo, unmodified (§2.12)
□ Leak scan: no other celebrity's data/prose on this page (token scan vs
  the other live pages; investigate hits before acting — false positives exist)
□ Footer: method + photo attributions + sensitive-topic disclaimers present
□ Internal links: every `celebrity-horoscope-<slug>-kundli` href (capsule pill
  or inline) checked against data.json — not-yet-live slugs route to
  `/en/coming-soon?name=...` instead (§2.14)
□ Versioning: every revision = NEW artifact URL (never overwrite prior versions)


════════════════════════════════════════════════════════════════════════
## 6 · PUBLISH / SITE PUSH
Route: /en/celebrity-horoscope-<celeb-name>-kundli  (keyword-rich URL, user-set)
   e.g. /en/celebrity-horoscope-shah-rukh-khan-kundli · Hindi twin: /hi/celebrity-horoscope-<celeb-name>-kundli
   file: pages/celebrity/<celeb-name>.html · canonical URL uses the full route · per-row `url` field in data.json is authoritative
1. Strip artifact wrapper; add canonical URL + JSON-LD (Person + FAQPage).
2. Feature branch; NEVER push or open a PR without explicit user approval.
3. Local CI simulation is mandatory before any hand-off: import audit vs
   requirements.build.txt → pytest → boot server → Playwright E2E
   (pages/* changes ALWAYS trigger E2E).
4. git fetch upstream FIRST; hand off as a prefilled compare-URL PR onto
   aws-mysql. Commander merges + eb deploys. No gh CLI.
5. sitemap.xml entry + hreflang stub for the /hi/ twin (every page ships with
   its Hindi twin per the language rule — same build, hi content).
6. Update data.json page_status + HANDOVER task log.


════════════════════════════════════════════════════════════════════════
## 7 · FAILURE MODES FROM THE SONNET ROUND (read before building anything new)

13 pages were built by Sonnet 5 in Aug 2026. Every defect below shipped to a live
page and had to be fixed after the fact — several were caught by the USER, by eye,
not by any gate. They are listed with the gate that now catches them, so the next
round does not rediscover them the expensive way.

### A. Silently empty slots
A `.mo` timeline tile or `.pc` planet card with no photo and no fallback renders as
a blank box. Shipped on Sachin (tile 4), SRK (tile 1) and Yuvraj (tile 5).
→ Gate: auditor checks 7-8. But note the auditor ITSELF had two bugs here (see D).

### B. Repeated photos that every hash said were unique
Hardik's page shipped 9 images that were really THREE photographs re-cropped, six of
them sharing one orange backdrop. Byte-hashing and even a naive dHash pass them,
because a different crop is genuinely different bytes. The user spotted it instantly.
→ Gate: auditor check 13 (colour-signature similarity, threshold 0.90, calibrated
  against known-good pages at 0.878 and Hardik at 0.902-0.920).
→ Rule: §2.5 means distinct FRAMES from distinct EVENTS. Two crops of one photo is
  the defect, never the fix. If supply runs out, SHORTEN the page (§2.7).

### C. The FAQ section simply missing
Deepika shipped with ZERO FAQ blocks; Sachin, SRK and Yuvraj had none either. It is
the page's main long-tail SEO surface (birth time / zodiac / nakshatra / manglik).
Nothing flagged it for weeks.
→ Gate: auditor check 12 (>=3 blocks).

### D. The auditor lying to you — twice
1. The LAST `.pc`/`.mo` element's search window was capped at +4000 chars, so a real
   high-res photo read as "missing" (false FAIL).
2. Fixing that by extending the window to end-of-document swung it the other way: an
   empty last tile "borrowed" an image from later in the page and PASSED (false PASS).
   Yuvraj tile 5 was blank while the tool said PASS.
→ Now bounded at the nearest section landmark, and for `.mo` also at the next `.pc`.
→ LESSON: when a tool says PASS on something the eye says is broken, distrust the
  tool and go read it. Never let a green check override a visible defect.

### E. Structure bugs a div COUNT cannot see
A misplaced `</div><!-- /wrap -->` renders FAQ + People-Also-Search full-bleed. The
open/close counts still balance, so counting proves nothing. It hit 5 of 9 pages in
one batch, then all 3 V3.1 pages.
→ Gate: auditor check 5 tests document ORDER, not counts.

### F. Dead links
- Links to celebrity slugs with no page (§2.14; the route now 302s to
  /en/coming-soon, so a PENDING celebrity is fine — a slug that is neither built nor
  in data.json is not).
- `href="#p-manglik"` with no matching id anywhere: a dead click on a live page.
- An index/hub card pointing at a page that was deferred.
→ Gates: auditor checks 10 and 14, PLUS a built-vs-linked cross-check on any hub page.

### G. Republishing the runtime wrapper
WebFetch returns an artifact wrapped in a claude.ai `<!-- frame-runtime -->` preamble
that is NOT part of the stored page. Two separate agents republished it, burying the
real `<title>` past the byte window the Artifact tool scans, silently renaming the
artifact to the working filename.
→ Gate: auditor check 11. Always strip the wrapper, and verify the title AFTER publish.

### H. data.json contradicting the page
data.json called Sachin's 13:00 birth time "verified (Rodden A)". Three competing
times actually circulate (13:00 / 14:25 / 16:20), and §1.3 requires Rodden A AND
undisputed. A brief written from data.json told an agent to assert a verified time,
which would have contradicted the page's own prose in 7 places. The agent stopped and
escalated rather than comply — the correct call.
→ Rule: data.json is a STARTING POINT, not an authority. Before asserting a birth
  time, cross-check tests/celebrity_charts.json and the page's own existing prose. If
  they disagree, the cautious reading wins and data.json gets corrected.
→ Rule for briefs: if an instruction in your brief contradicts what the page or the
  engine says, STOP and escalate. Do not ship a page that argues with itself.

### I. Portrait heroes over-zooming on desktop
A tight-headshot source forced to `cover` in the ~1.95-ratio desktop banner zooms hard
— cap and chin cropped, reading as a fragment. Hit Kohli. Dhoni had the wide image but
with a hard unfeathered seam and the subject jammed to the left edge.
→ Rule (§2.4 already says it; nothing enforced it): canvas-extend so the subject sits
  ~30% with headline room right. Build the extension from the photo's OWN EDGE STRIPS,
  never the whole frame (that puts a blurred ghost of the face in the extension), and
  feather ~150px so there is no seam. Desktop-only override — the wide canvas crops far
  too tight on mobile, so mobile keeps the portrait.
→ Always render the hero at 1440x900 AND 375x812 and LOOK before shipping.

### J. Agents reporting success they did not achieve
Multiple agents reported a fix as done when it was not (a flagged-but-unfixed broken
anchor; a claimed audit run that had not happened).
→ Rule: the orchestrating session re-runs the gates ITSELF on the LIVE artifact after
  every agent hand-back. An agent's self-report is a claim, not evidence.

════════════════════════════════════════════════════════════════════════
## 8 · CHECKPOINTING — never lose a build to a limit or a crash

Added 25 Aug 2026 after nine simultaneous build agents were killed mid-flight by a session
API limit. Eight of the nine lost their transcripts entirely, so hours of chart
computation, photo harvesting (one had 106 licence-verified candidates across 35 events)
and drafting evaporated. Only one could be resumed. The work itself was fine — it simply
was not written down anywhere durable.

EVERY build agent MUST checkpoint to disk as it goes. Treat the transcript as volatile.

Working directory, one per page:
  <scratchpad>/opus_build/<slug>/
    chart.json      the computed placements, the birth-time sweep (10-min granularity),
                    the dasha spread, and which features are stable. WRITE THIS FIRST,
                    immediately after computing — before any prose.
    photos/         every downloaded candidate, plus manifest.json recording for each:
                    filename, source API, licence, licence id, event, date, whether solo
                    or group, how the subject was identified, accepted or rejected + why.
                    WRITE EACH ENTRY AS YOU VERIFY IT, not in a batch at the end.
    draft.html      the page as it is assembled. Save after each section is completed,
                    not once at the end.
    PROGRESS.md     a short running log: what is DONE, what is IN PROGRESS, what is NEXT,
                    and any decision made that a fresh agent would otherwise have to
                    re-derive (e.g. "rejected X.jpg — same shoot as tile 2").

RULES:
  1. Write chart.json before writing one word of prose. It is the most expensive thing to
     recompute and the easiest to persist.
  2. Update PROGRESS.md at every phase boundary. One or two lines is enough.
  3. Never hold a verified photo only in memory — download it and record it in
     manifest.json the moment you accept or reject it.
  4. On resume: READ the checkpoint directory FIRST and continue from it. Do not restart
     work that chart.json or manifest.json already answers.
  5. The orchestrating session should point a replacement agent at the dead agent's
     checkpoint directory rather than starting it from zero.

This costs a few seconds per phase and converts a total loss into a resume.

PROVEN, twice, on 25 Aug 2026:
  - Rahul Gandhi's agent was killed by the session limit at the very last step, with the
    page finished. Because PROGRESS.md said "PHASE 5 — PUBLISH : NEXT" and the built file
    was on disk, the orchestrator verified it and published it directly. Zero rework, and
    no replacement agent had to be spawned at all.
  - Smriti Mandhana's photo research survived the same limit through image-index.json.

### 8.1 · Write the index status field in CANONICAL form

`_image_index.py` records each candidate with a `status`. Write EXACTLY one of:

    accepted | rejected | used

Yogi Adityanath's agent wrote `accept` / `reject` instead. Both readers matched only the
-ed forms, so all 22 of its decisions were invisible to `usable()` and `rejected()` — the
index reported `0 usable, 0 rejected` and the next agent would have re-searched every one
of them, which is precisely the waste the index exists to prevent. The readers now
normalise common variants on read, so this specific slip is survivable, but the
normaliser is a safety net and not a licence: write the canonical value.

A rejection is a first-class record. Always include `reason` — "watermark burned in",
"same shoot as tile 2", "12-person group, face mush". A rejection without a reason forces
the next agent to re-open the dead end to find out why it was a dead end.
