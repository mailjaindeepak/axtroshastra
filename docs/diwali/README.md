# Diwali 2026 report: research and decisions

**Status (26 Oct 2026): ON HOLD (owner).** The spec was updated on 26 Oct with the re-order hybrid and all owner decisions up to 26 Oct. Build stays on hold until the owner approves it. Next: a new mock (Mock 3) on the new structure. Mock 1.2 and Mock 2 v2 show the old shape and are kept as history.

| File | What it is |
|---|---|
| this file | Summary reports from round 1 and round 2, the plan so far, decisions made, open questions |
| [diwali-report-spec.md](diwali-report-spec.md) | **The build spec (source of truth):** sections, inputs, funnel, engine work, exceptions, tests, open items. Updated 26 Oct (re-order hybrid); awaiting owner approval |
| [uncle-research.md](uncle-research.md) | Deepak's (uncle's) Diwali research, copied word for word (23 Oct) |
| [structure-check-2026-10-23.md](structure-check-2026-10-23.md) | 4-agent check of the draft structure: facts, code, coverage, recipe (23 Oct) |
| [research-round1-raw.md](research-round1-raw.md) | Full output from round 1 (23 agents): competitors, user questions, new-year communities, inputs. Includes every source and the fact-check results |
| [research-round2-raw.md](research-round2-raw.md) | Full output from round 2 (27 agents): audience and gifting, questions by theme, our sales and CI history, remedies, price, plus the 3 product-council proposals |
| [../bugs.md](../bugs.md) | Bugs found during this research that need fixing (some must be fixed before the Diwali launch) |

## Key dates (Drik Panchang)
| Day | Date |
|---|---|
| Dhanteras | Fri 6 Nov 2026 |
| Kali Chaudas; Tamil Deepavali (oil bath, Tamil calendar; confirm against Drik, spec O-4) | Sat 7 Nov |
| Lakshmi Puja; Narak Chaturdashi / Choti Diwali (North Indian calendar, Drik); Chopda Pujan | Sun 8 Nov |
| Gap day | Mon 9 Nov |
| Gujarati New Year, Samvat 2083 / Padwa / Govardhan | Tue 10 Nov |
| Bhai Dooj | Wed 11 Nov |

Lakshmi Puja start times on Sun 8 Nov:

| City | Time |
|---|---|
| Delhi | 5:54 PM |
| Mumbai | 6:27 PM |
| Bengaluru | 6:17 PM |
| Chennai | 6:06 PM |
| Ahmedabad | 6:22 PM |
| Kolkata | 5:20 PM |

Launch target: Sun 1 Nov. Last possible day: Thu 5 Nov. Sales close on 8 Nov.

---

## Round 1 summary (19 Oct)

**Competitors.**
- Nobody sells a Diwali report. AstroSage, AstroTalk, GaneshaSpeaks, Clickastro, MyPandit and Astroyogi sell Jan-Dec yearly reports and discount them at Diwali.
- AstroSage's Diwali 2025 sale priced reports at ₹299-₹399.
- Other prices:
  - Yearly reports: ₹549-₹1,299.
  - Money reports: AstroTalk ₹1,299, Clickastro ₹1,768.
  - A Lakshmi puja done online in the buyer's name: ₹799-₹3,501.
- Gaps we can fill:
  - a year that runs from Diwali to Diwali
  - the buyer's own puja time
  - a new-year and new-account-books section for business families

**What people ask around Diwali.**
1. Which day is Diwali or Dhanteras?
2. What is the puja time for my city?
3. When should I buy gold?
4. How will my money go from this Diwali to the next?
5. Which rashi is lucky?

The top complaints about paid reports are: the same text for everyone, padded PDFs, wrong dates, fear-selling, and late delivery.

**Communities.**
- For Gujarati, Marwari and Jain business families, a new year starts on 10 Nov and new account books are opened. These families overlap most with our buyers in Mumbai, Pune, Bengaluru and Chennai.
- In Tamil Nadu and Karnataka, Diwali is not a new year.
- Things to avoid:
  - Don't target Sikh buyers.
  - Don't use Lakshmi Puja wording for Jain buyers.
  - Frame Diwali around Kali Puja for Bengali buyers.

**Engine.**
- The birth-chart side (chart, dasha, D9/D10, Sade Sati) can be reused.
- None of the date side exists yet: no panchang, sunrise or muhurat, and no month-by-month transits.

**Template.** Clone Business Growth (Vyapar). Do not clone Career Intelligence (CI): it never calls the AI and gives everyone nearly the same text.

## Round 2 summary (20 Oct)

**A. What makes anyone want to buy it.**
- Young buyers want comfort, something they can share, and no fear. Astroyogi's own data says about 80% of Gen Z questions are about relationships.
- Buyers aged 35-54 want money, career and dates.
- Both groups dislike generic text and fear-selling.
- 42% of Diwali gift buyers buy 1-4 weeks before the festival (YouGov 2024).
- Buyers distrust fake discounts. A real deadline works better.
- A gift with a "because..." note from the giver is valued more (University of Bath study).
- Correction to round 1: AstroMedha already sells a year-ahead gift for ₹599. A Diwali-to-Diwali themed gift is still unclaimed.

**B. Real questions by theme.** Reddit and X blocked automated reading, so quotes come from search snippets and must not be used in ads until a person has checked them.
- **Career (biggest theme):**
  - When will I get a job or my big break?
  - Should I switch or stay?
  - When will my raise or appraisal come?
  - When will I recover after a layoff?
- **Marriage and love (second):**
  - When will I marry?
  - Love or arranged?
  - Are a low guna score or Manglik a problem?
  - What will my partner be like?
  - We fight. Will it work out?
- **Money and business:**
  - When should I start or expand?
  - When should I buy gold?
  - How do I recover from debt?
- **Every report:**
  - How does my year go month by month?
  - What are my best months, and which months should I go slow?
  - Am I in Sade Sati?
  - What one thing should I start this Diwali?

**C. Our own data.**
- Deepak (the repo owner, "uncle") made almost every CI change after launch. CI's report text has not changed since 20 Sep. He changed only the price and the free preview.
- The redesigned preview (13-21 Sep) shows the buyer's own chart for free, locks the answers, and never shows dates for free.
- Weekly sales went from under 5 to 157 after that redesign. Price cuts and an X ads push happened in the same week, so we cannot prove which change caused it.
- Real prices: CI ₹259, Milan ₹249, Life Blueprint ₹499. Most sales happen at ₹199-₹259.
- Cheaper does not sell on its own: Marriage at ₹199 converts only 2.2%.
- Half of buyers pay within 2 minutes.

**D. Remedies, warnings, hope.**
- Remedies come in pairs: "Tradition says X; the habit behind it helps because Y". Nothing to buy.
- Warnings follow 4 parts: what, when, what to do, how much it helps.
- Never predict death, illness or divorce.
- Legal limits:
  - No "cure" or "prevent" wording (Drugs and Magic Remedies Act).
  - No fake timers or fake reviews (dark-pattern rules, 2023).
  - Add a word filter for dosha, curse, danger, guaranteed and cure.

**E. Code problems.** See [../bugs.md](../bugs.md). The most serious: the WhatsApp PDF is built before the AI text is written.

## Proposed plan (not yet approved)

> ⚠️ SUPERSEDED by the decisions below / the spec ([diwali-report-spec.md](diwali-report-spec.md)). Kept as history.

**Name:** "Shubh Varsh: Your Year from Diwali 2026 to Diwali 2027". In gift mode the cover adds "From [giver], because...".

| # | Section | Content | Why |
|---|---|---|---|
| 1 | Cover and gift note | Name, Moon sign, birth star, the giver's note | Makes it feel like a gift (Bath study) |
| 2 | Your Year in 3 Words and Your Best Month | 3 words and the best month with dates, each with its chart reason | An early "wow" moment that is clearly about this person |
| 3 | Straight Answers | 5 one-line answers for the chosen theme, each with a date range | Copies the CI verdict page that came just before sales rose |
| 4 | Your Theme in Depth | Each theme question gets a window, a reason and a step | Answers what people actually ask |
| 5 | Month by Month, Nov 2026 to Oct 2027 | 12 rows: mood, one thing to do, one thing to watch | The number 1 question in every theme |
| 6 | The Other Two Themes | Half a page each | So the buyer doesn't feel they missed out |
| 7 | Best Dates for Big Buys and New Starts | Personal windows for gold, vehicle, property, launch; a gold fact box (hallmark, ask for making charges in writing) | The top Dhanteras question |
| 8 | Months to Go Slow | Gentle warnings in the 4-part pattern | Honest without scaring |
| 9 | Sade Sati Check | Exact dates, or "You are NOT in Sade Sati" | A common fear, answered calmly as a fact |
| 10 | Your 3 Strengths | Each strength with one action | Hope grounded in their own chart |
| 11 | Free Remedies | Tradition, habit, household step | Owner's rule: nothing superstitious, nothing to sell |
| 12 | Diwali Fresh Start | 3 if-then plans, plus 3 blessings from the past year | Fresh-start effect; if-then plans are proven to help |
| 13 | Blessing and Share Card | Family blessing, new-year greeting, WhatsApp status card with no birth data | Ends on a happy note; the card works as free advertising |

**Leave out:**
- gemstones, yantras, colours, paid pujas
- Kaal Sarp, Manglik presented as doom
- stock tips, gold-price forecasts, lucky-rashi lists, long puja guides
- the family/health theme (add it after Diwali)

**Inputs:**
- Who it's for: Me or Someone else
- Name, birth date, birth place
- Birth time, plus "how sure are you?"
- Theme: Career, Marriage and Love, or Money and Business
- Work type
- WhatsApp number
- In gift mode: the giver's name and a "because..." note
- Tradition (optional)

Skip: email, gotra, marital status, current city.

**Price:**
- ₹299 until Sun 8 Nov, then ₹399.
- A second report as a gift costs ₹199 (₹498 for two). Build it as a normal second order, not as a free pass.
- No fake struck-out price and no 30-minute timer.
- The AI costs roughly ₹6-12 per report (an estimate).

**Free preview:**
- Free to see: their own chart, current planet period, the 3-word card, and whether they are in Sade Sati.
- Locked: the best month and the 5 answers, each with a teaser line.
- A "Gift it" button next to "Unlock ₹299".

**Before launch:**
- Fix the PDF bug.
- Run a 5-buyer test where no paragraph may be identical across reports.
- Add the word filter.
- Add a render queue.

## Decisions so far
- Gen Z was an example. The report must excite every age group: it should be something you want to buy for yourself, family or friends, it should look good, and it should be easy to understand. (Owner, 20 Oct)
- No gemstones or superstitious products. Remedies must be astrological, science-backed, or household. Warn about serious things without scaring. (Owner)
- No Hinglish for new products (CLAUDE.md §7).
- **Look back at the past year, chart only (option a).** The report names the hard months and the area of life they touched, each with its chart reason, and says when things improve. It never names a specific event, and it adds no extra form field. (Owner, 20 Oct)
- **Wording uses everyday words that Indians whose first language isn't English understand.** No vague phrases like "heavy stretch". No words from the CLAUDE.md §5b list (health, illness, stress, worry, tension, medical...). (Owner, 20 Oct)
- **The form asks for life stage, and the family section changes with it.** Single: marriage and future children. Married with no children: when children may come. Married with children: how the whole family will be doing, plus the children's future. (Owner, 20 Oct)
- **No 12-page limit.** (Owner, 23 Oct)
- **Only the STRUCTURE is fixed (sections and what kind of material each holds). The CONTENT is never fixed.** Every buyer has a different birth date and different questions, so every chart-derived word must come from that buyer's data. This avoids the CI mistake (bugs.md #2, #13), and follows CLAUDE.md §22. (Owner, 23 Oct)
- **No data leakage:** no sample-persona name, number, date or sentence may reach a real buyer. (Owner, 23 Oct)
- **Design must feel like Diwali** (occasion-specific), while following the recipe in `docs/career-intelligence-report-recipe.md` for the page and the report. How far the Diwali look may depart from the recipe's fixed theme is an open question. (Owner, 23 Oct)
- **Design:** same layout as the recipe (430×830 card pages, page rules, the 3 fixed pages), with a Diwali look on top (diyas, rangoli, marigold, a deep-night palette). The recipe's existing SVGs (mandalas, constellations, icons) are reused. (Owner, 23 Oct)
- **The buyer picks ONE main area** (Career / Marriage / Money and Business / Family). That area gets the deep section, and the others get short summaries. (Owner, 23 Oct)
- **Length:** the section list decides it. There is no page target. (Owner, 23 Oct)
- **Hindi ships after the English version is approved.** (Owner, 23 Oct, CLAUDE.md §7)
- **Homepage:** yes, add a card and tagged reviews in home.html. (Owner, 23 Oct, CLAUDE.md §4)
- **Price:** ~~₹299 until 8 Nov, then ₹399~~ → **₹499** (owner switched to the uncle's price, 23 Oct). The ₹199 gift price for a second report has not been re-decided.
- **The main-area / "biggest wish" question is OPTIONAL** (uncle's approach). (Owner, 23 Oct)
- **Focus: COMBINE both pieces of research.** The report includes every "only in uncle's" item and every "only in ours" item. Neither money nor whole-life should overpower the other; how to balance them is still to be designed. (Owner, 23 Oct)
- **Steering choices (optional):** Money, Career, Business, Family happiness, Better luck, and Marriage. (Owner, 23 Oct)
- **Timeline:** both the 4-part year and month by month. **Money:** a separate Prosperity overview (with Dhana Yoga) AND a separate Business section. (Owner, 23 Oct)
- **Everyday English only, no complex words.** (Owner, 23 Oct)
- **The Lakshmi section keeps "Lakshmi" in its name**, even though round-1 research flagged Jain buyers. The owner chose this knowingly. (23 Oct)
- **If the steering question is skipped, the chart chooses the deep area:** the area with the strongest period this year. (Owner, 23 Oct)
- **Ad targeting is in this build:** send ONLY the chosen category, never birth details, to the ad tracking. (Owner, 23 Oct)
- **Scope: full scope, risk accepted.** The launch may slip from 1 Nov toward the 5 Nov cutoff. (Owner, 23 Oct)
- **"Better luck and a fresh beginning" deep section** (approved, POSITIVES ONLY): bright spots (the strongest point from each area, with its chart reason), turning points (planet-period changes as month ranges), what last year was building, strengths with actions, and small fresh-start habits. Cautions stay in "Months to go slow". (Owner, 23 Oct)
- **Dates rule:** no single "lucky days". Month ranges calculated from the chart are allowed (planet-period changes, the 4-part year, the 12 months, good months for gold). (Owner, 23 Oct)
- **4-part year:** a one-page overview, with month-by-month detail on later pages. (Owner, 23 Oct)
- **Astrology terms are kept for credibility**, written as everyday words first and the term in brackets: "the money part of your chart (2nd house)". (Owner, 23 Oct)
- **Structure (approved):** front pages with the answers first. Then **Part 0, the most important points from ALL parts**. Then Part 1 Your Year, Part 2 Deep Dive, Part 3 Your Diwali. At the back: chart pages, a short astrology course, an FAQ answering doubts, methodology, and Thank you. Everything important sits in the first pages and the detail comes later. (Owner, 23 Oct)
- WhatsApp delivery (bug #4) is handled separately by the owner. (23 Oct)
- **Bug #1 is fixed IN this build.** After payment the order becomes: AI text, then the PDF, then WhatsApp. The free preview stays without AI, and AI cost is unchanged because it still runs only for buyers. (Owner, 23 Oct)
- **Structure check (23 Oct, 4 agents):** fact check, code check, coverage check and recipe check. All fixes applied to the draft structure: added Sat 7 Nov plus Chopda Pujan and "for New Delhi, your city may differ by a day"; Sade Sati shown in phases (Saturn moves backward in 2027); no guna score for one person (show their own matching traits instead); 9th house added for Better luck; no practices tied to children or health (Drugs and Magic Remedies Act); "how home life will go"; children's studies need the child's own chart; "not financial, legal or professional advice"; strengths always 3; date fixed to Diwali 2026 (`as_of`).
- **Name:** "Diwali Wealth & Prosperity Report" (the uncle's name). (Owner, 23 Oct)
- **The gift note gets its own page after the cover**, so the cover stays locked as the recipe requires. Gift mode switches on when the optional fields "Giver's name" and "Note" are filled in. There is no toggle. (Owner, 23 Oct)
- **"A Note for You" sits at page 2, as in the recipe.** (Owner, 23 Oct)
- **Gift price for the 2nd report:** ask the uncle. (23 Oct)
- **12 months:** add the fast planets (Sun, Mars, Venus) to the slow periods so each month reads differently. (Owner, 23 Oct)
- **Gold months:** use our own rule, labelled clearly as "our method". (Owner, 23 Oct)
- **City puja times:** a hand-checked table for the top cities, the same for everyone. (Owner, 23 Oct)
- **Inputs:** gender, work type, life stage (3 options: not married / married, no children / married, with children), and optional gift fields. **No tradition field**, so the new-year greeting is general and the dates page lists every community's day. (Owner, 23 Oct)
- **Tradition field: confirmed NO.** The Diwali pages are the same for everyone:
  - a "Diwali across India" table of each community's day (Tamil Deepavali Sat 7 Nov; Lakshmi Puja and Chopda Pujan Sun 8 Nov; Kali Puja on the night of 8 Nov; Gujarati New Year, Padwa and Govardhan Tue 10 Nov; Bhai Dooj Wed 11 Nov)
  - a city puja-time table
  - a general greeting

  Reasons: tradition doesn't change the chart content; where you live isn't the same as your tradition (someone in Mumbai with Tamil roots); it would make the form longer; and asking about community can feel personal. Revisit only if sales show strong demand from a community (for example a dedicated new-account-books page). (Owner, 23 Oct)
- **Unsure birth time:** ~~leave out the parts that need the exact time~~ → **use the Moon-sign fallback (Chandra lagna) and tell the buyer it's less precise.** (Owner, 23 Oct.) This reuses the existing tiers in `engine.compute_report` (upstream `engine.py:344-380`): T0 exact, T1 ±45 min (falls back to the Moon chart if the rising sign is unstable), T2 a ±3 h band, T3 unknown (also checks whether the Moon changes star during the day). Good periods are capped at "Moderate" for T2/T3 (`engine.py:445`).
- **What changes the report** (23 Oct):
  - steering choice: Part 2, the 5 answers and the fresh-start plan
  - birth-time tier: the house reference and the grade cap
  - life stage: Home and children, Marriage and partner, and the Marriage and Family deep dives
  - work type: career and business wording
  - gender: the marriage reading
  - gift fields: the gift page

  That makes about 670 combinations. Test each branch of each input (CLAUDE.md §12), not every combination.
- **Palette:** light base (recipe cream and sand) with Diwali accents. (Owner, 23 Oct)
- **Free preview and "Your Diwali answers":** the 5 questions follow the area the buyer picks, or the area the chart picks. (Owner, 23 Oct)
- **After 8 Nov:** keep selling as a "Year Ahead" report; only the Diwali dates page changes. (Owner, 23 Oct)
- **Mocks: 2.** (Owner, 23 Oct)
  - **Mock 1, the "all sections" catalogue:** every section in depth, all 6 deep dives, every area's summary version, and all 3 life-stage versions of Home and Marriage. It also shows the unsure-birth-time note as a variant. It is for content and design approval and is not a real report.
  - **Mock 2, "one real buyer":** the exact report one person receives (for example married with children, business owner, picked Money, exact time, gift fields filled in). It checks the flow, page count, Part 0 answers, page links, gift page and the recipe's PDF gate.
  - Everything else is covered by testing: per-branch tests (§12), an automated PDF gate on about 21 generated reports (7 deep-dive outcomes × 3 life stages), the 5-buyer no-identical-paragraph test, and a leak grep.
- **Work type: student and home** keep the same sections with different wording and never an empty page. Student: studies and first job (reuse `vidyarthi.py`), plus a future business-or-job leaning. Home: home-run income or returning to work, plus small home ventures and the family money picture. (Owner, 23 Oct)
- **Age:** 4 bands (under 25 / 25-40 / 40-60 / 60+) change the WORDING only (examples, tone), never which sections appear. Unusual age and life-stage combinations are not questioned. (Owner, 23 Oct)
- **Gift price:** recommend ₹299 to the uncle (₹499 + ₹299 for two; still above CI's ₹259; AI cost about ₹6-12). Uncle decides. (23 Oct)
- **Spec final check (23 Oct, owner pop-up answers):** (Owner, 23 Oct)
  - **Page order in gift mode:** Cover, Gift page, Note. The Note sits on page 2 normally and page 3 in gift mode.
  - **"Year in 3 words" is kept. The WhatsApp share card is dropped.**
  - **Bug #1 is fixed for the Diwali product only.** The other products get a separate fix later, so bugs.md #1 stays open for them.
  - **When the steering choice is skipped, the chart picks from the 5 life areas only, never "Better luck".**
  - Spec: [diwali-report-spec.md](diwali-report-spec.md), checked by an independent verifier and given a final check. Open items O-1 to O-26 are listed in spec §13.
- **Blocking items (23 Oct, owner pop-ups):** (Owner, 23 Oct)
  - **Free preview** follows the CI pattern. Free: the chart, Moon sign, birth star, current planet period, Sade Sati yes/no, the year in 3 words, and the uncle's emphasis line. Locked: the 5 answers, and every month and date.
  - **Fixed pages:** I draft Diwali text for the cover, Note and Thank-you in Mock 1, and the owner approves it there.
  - **Gold months:** months when Jupiter or Venus moves over the 2nd or 11th house, or when the sub-period lord rules those houses. Labelled "our method".
  - **Dhana Yoga:** the classical definition, using the lords of houses 1, 2, 5, 9 and 11.
  - **Area pick when the choice is skipped:** the best period this year among the 5 life areas. Ties go by work type.
  - **Strengths:** ranked by planet dignity first, with ashtakavarga only to break ties. No numbers are shown.
  - **5 questions per area: DECIDED.** These are the uncle-style sets in spec §6a. Three earlier drafts were rejected: too generic, promising too much, and too flat. The research agent's version was used, with 4 fixes from the final check: "months" instead of "dates"; no children's studies; no "challenges" and no Sade Sati question in Better luck, which is positives only.
  - **New open item O-27:** the zodiac sign "Cancer" collides with the banned word "cancer". To decide later.
- **Mock 1 v1 built (23 Oct):** the "all sections" catalogue.
  - Link: https://claude.ai/artifact/VpY9gw8bLic6ibMzh5nMrT
  - 75 cards. It passes the recipe gate: 75 PDF pages = 75 cards, each 323×623 pt, 0 leaks, no §5b words.
  - Files: [mock/mock1-v1.html](mock/mock1-v1.html) (standalone, prints correctly) and [mock/mock1-v1.pdf](mock/mock1-v1.pdf).
  - Sample person: Vikram Rao, a made-up person. His chart comes from the shared engine: Leo rising, Aquarius Moon, the Mercury–Jupiter planet period, and the last phase of Sade Sati.
  - Built by 6 parallel agents from [mock/BRIEF.md](mock/BRIEF.md). The final check fixed 3 places where sections disagreed: the best money stretch is Jun–Sep 2027; loan-clearing months are Dec 2026–Jan 2027 and Jul–Aug 2027; and the page references.
  - Waiting for owner review.
- **Birth chart style: South-Indian.** The owner asked Claude to choose (23 Oct). Reasons:
  - Two of the top 3 buyer states, Karnataka and Tamil Nadu, read the South-Indian chart.
  - It is the same grid as Career Intelligence and Business Growth.
  - The sign boxes stay fixed, so everyday labels like "your money part" always point to the same place.

  The chart page carries one line for North-Indian readers.
- Critique (a)-(c) below is now RESOLVED: (a) by the Better luck decision, (b) by the spec's one-line jobs (§5), (c) by spec §2.4. Original note: Critique noted on 23 Oct, still open: (a) give "Better luck" deep-section content that comes from the chart; (b) write a one-line job for each section so overlapping money and timeline sections don't repeat; (c) house names always appear after the everyday words ("the money part of your chart (2nd house)").
- **Sample report idea (to discuss):** following the recipe, build ONE sample report that covers ALL areas in depth, so we can see and check what a buyer gets for each area they pick. (Owner, 23 Oct)
- Uncle's research compared with ours on 23 Oct, and the comparison was checked by a verifier agent. Code facts: CI charges ₹259 (`api.py:436`) and CI v2 charges ₹499. Business Growth already computes Dhana Yoga (`products.py:1175-1202`). No Lakshmi yoga exists in the code.
- **Gift delivery:** the WhatsApp number is taken in the FORM itself, not the popup, and only the receiver gets the report. A copy for the giver will be decided later. This differs from the standard funnel in CLAUDE.md §1, where the popup captures the number, so it must be called out in the spec. **The popup is removed:** the flow is form, then free preview, then Razorpay. (Owner, 23 Oct)
- Uncle's (Deepak's) research: owner will paste it next; the final plan waits for it. (23 Oct)
- "Family and children's future" is a launch theme, because our core buyers (35-54) are worried parents. (Owner's father, 20 Oct)

## Current state (25 Oct 2026, on hold)

| Item | State | Where |
|---|---|---|
| Research (rounds 1 and 2, uncle, structure check) | Done | this folder |
| Spec | Updated 26 Oct to the re-order hybrid; awaiting owner approval | [diwali-report-spec.md](diwali-report-spec.md) |
| Mock 1 v1 (catalogue) | Superseded by 1.2 | https://claude.ai/artifact/VpY9gw8bLic6ibMzh5nMrT · [mock/mock1-v1.html](mock/mock1-v1.html) |
| **Mock 1.2** (catalogue: 84 pages, 194 links, 5 questions for every area) | Verified in 2 rounds + final check | https://claude.ai/artifact/DGmTqMGN4vDN2HQV1wGuVr · [mock/mock1-v1.2.html](mock/mock1-v1.2.html) |
| **Mock 2 v2** (one real buyer: 47 pages, 120 links) | Verified in 2 rounds + final check | https://claude.ai/artifact/9qNZ6q2z2ZEbQD2tHmexR7 · [mock/mock2-v2.html](mock/mock2-v2.html) |
| Timing reference for the sample buyer | Every month range in the mocks matches it | [mock/TIMING.md](mock/TIMING.md) |
| Production code (engine work, renderer, page, tests) | **Not started, on hold** | spec §7, §12 |

**Owner feedback on the mocks (25 Oct):** "visuals are okay but it is very difficult to understand and lacks content." The uncle asks how Life Blueprint covers so many areas (career, marriage, money…) in a way buyers find easy to understand and buy.

**The uncle's proposal, as clarified by the owner on 25 Oct:** every buyer gets the SAME list of sections at full depth, and the text inside is still computed from THEIR birth chart (CLAUDE.md §22 is kept). Only the order changes by theme. **Uncle's proposal (25 Oct), not decided:** instead of a dynamic report, keep the report THE SAME for everyone and only RE-ORDER the sections by the chosen theme. For example, someone who picks Career sees the Career section first and the rest after it. A comparison with Life Blueprint is in progress.

## Open questions (live list, 25 Oct)
**Big decision (blocks everything else):**
- **DECIDED (Owner, 25 Oct): the re-order hybrid.** Every area gets a full section for every buyer, written from their own chart. The chosen area comes first, the front-page answers still follow the theme, and there is no separate deep-dive Part. **Each area must have ENOUGH content that the buyer is left with no doubt.**
- **DECIDED (Owner, 25 Oct): a "wheel"-style overview of all areas is OK.** It must NOT look like Life Blueprint's wheel (no same or similar SVG), so a buyer who owns both reports never feels cheated. It needs a Diwali-specific design.
- **DECIDED (Owner, 25 Oct): R2 + R3 approved.**
  - **R2:** every topic follows the same easy order: one-word answer (Good / Steady / Careful) → what it means for you (2–3 plain sentences with real-life examples) → what to do / what to watch → one short "why" line → when (this year's good and careful months).
  - **R3:** remove clutter. No astrology reasons in brackets inside sentences. Each date appears only in the year timeline and the 12-month table. Use the plain name OR the house number, not both. "How to read this" goes at the front. Fewer pages that only point elsewhere.
- **DECIDED (Owner, 25 Oct): keep the mocks' SVGs and visual design as they are.** The owner and uncle love them.
- **DECIDED (Owner, 25 Oct): plain timing words.** Use "best time" (and similar everyday words) instead of "stretch", "window" and the like. Mock 1 does this in places and wins there.
- **DECIDED (Owner, 25 Oct): remove the line saying the chart is accuracy-checked against AstroSage** from the report (the Methodology page and anywhere else buyers can see it). The AstroSage check stays as an internal test only (CLAUDE.md §21); it is just never mentioned to buyers.
- **Overview design, round 1 (25 Oct):** 3 options (A six lamps, B marigold door garland, C lamp calendar), saved at [design/overview-options-v1.html](design/overview-options-v1.html) and on https://claude.ai/artifact/XEucQuQKn2EbUAnkVBC9pR. **Owner: not final, make MORE options with more Diwali elements (sweets, firecrackers and more). C feels very cluttered.** Keep all options saved.
- **Overview design, round 2 (25 Oct):** 8 new options with more Diwali elements, built by 2 agents and checked by Claude. All 11 options are on one numbered page: https://claude.ai/artifact/HsRTU79P9gHqAUfDHtmMv7 · [design/overview-options-v2-gallery.html](design/overview-options-v2-gallery.html) (page images `design/overview-v2a-p1..4.png`, `overview-v2b-p1..4.png`).
  - No. 1–3: round 1 (six diyas, door garland, lamp calendar)
  - No. 4: mithai box
  - No. 5: anar fountains (gentle fireworks; the Jain sensitivity was flagged)
  - No. 6: akash kandils
  - No. 7: Diwali thali
  - No. 8: diya path with Lakshmi's footprints
  - No. 9: door garland v2
  - No. 10: Lakshmi kalash with coins
  - No. 11: rangoli tiles

  All use "Best time / Good time / Careful time" and "From this Diwali to the next (Nov 2026 – Oct 2027)", with no "year", no scores, and nothing round like Life Blueprint.
- **DECIDED (Owner, 25 Oct): pictures and their jobs.**
  - **Data pictures** (they show Best / Good / Careful time):
    - **No. 8 diya path:** the front-page overview of all areas.
    - **No. 9 door garland v2:** the home, family and marriage sections.
    - **No. 6 akash kandils:** time, e.g. the 12 months.
    - **No. 1 diyas:** time and areas on other pages.
    - **No. 5 anar fountains:** luck / best-time highlights. The owner chose it knowing the Jain-buyer note.
  - **Decoration only** (they show NO data states, because the owner found they cannot show good vs careful accurately):
    - **No. 4 mithai box:** for example the blessing / gift page.
    - **No. 11 rangoli tiles:** art across pages.
  - **Not used:** No. 10 kalash, No. 7 thali, No. 2/3 (round 1).
  - **APPROVED (Owner, 25 Oct): the state marks v3 for the akash kandil, the diya (No. 1/No. 8) and the anar.** "Everything is perfect."
  - **REVERTED (Owner, 25 Oct): the door garland (No. 9) goes back to its v2 marks with NO glow or rays, because flowers don't glow.** Full bloom = Best, half-open flower = Good, bud = Careful (as in [design/overview-v2b-p2.png](design/overview-v2b-p2.png)). The v3 glowing-flower version (state-marks-v3 p5) is NOT used.
  - **Owner (25 Oct): no more design options for now. Design comes later.**
- **Mock 3 v1 built and published (26 Oct), on the re-order hybrid:**
  - **3A** (one buyer, 57 pages, 162 links): https://claude.ai/artifact/4gE6vJWtVakNbkKrjuBjKo · [mock/mock3a-v1.html](mock/mock3a-v1.html)
  - **3B** (buyer versions, 16 pages): https://claude.ai/artifact/KtQmwoEYr41KECc173r71S · [mock/mock3b-v1.html](mock/mock3b-v1.html)
  - Built by 7 agents from [mock/BRIEF3.md](mock/BRIEF3.md). 3 verify rounds with fresh agents; fix rules in [mock/FIXES_R1.md](mock/FIXES_R1.md), including the round-2 split between overall month tone and area windows.
  - Round-3 leftovers were fixed and checked by Claude: the June gold mark, the repeated Rahu line, the gold section title, dashed careful pills, "best for gold" wording, a vague "when" line, and "big move".
  - Gate: 57 = 57 pages and 16 = 16 pages at 323×623, leak 0, banned none, dates only on the allowed pages. **Waiting for owner review.** O-29 (page budget) is to be judged from 3A.
- **Free preview mock v1 (26 Oct):** site-style preview for Vikram in the CI preview layout, Diwali skin, story-style Wrapped card with months locked (O-9): https://claude.ai/artifact/HrQP7QpygE6S7oUgduUe6Q · [mock/diwali-preview-vikram-v1.html](mock/diwali-preview-vikram-v1.html)
- **Age bands CONFIRMED (Owner, 26 Oct):** no age field in the form. Age is worked out from the date of birth and changes examples and tone only (spec §3). Counts: 2,688 order/wording versions; about 71 automated tests + 10 PDF reports (72 once a "married, no children" wording test is added).
- **Uncle question (26 Oct): "unmarried buyer, Family 4 pages + Marriage 3 pages, awkward?"** Answer: no. Life stage swaps the content (spec §5 table, §6). Life Blueprint asks no life stage and uses the same hedged text for everyone (report_view.py:1908, 2019; jyotish_maps.py:138). Open suggestion: "married, no children" Family Q4 → "happy news in your family" (spec lines 274, 449, 521; 3B one card; 3A unaffected). Uncle to decide.
- **Mock 3C v2 (26 Oct):** Wrapped card (p46) and 5 takeaways (p49) restyled in the report's light theme (agent build, checked by Claude): https://claude.ai/artifact/L3zLR4YadAznx9XxxiHc86 · [mock/mock3c-v2.html](mock/mock3c-v2.html). Gate 58 = 58, 323×623, leak 0, banned none, links OK. Gift page in 3C still shows the old gift wording; the new toggle flow lives on the landing page, not in the report.
- **Gift flow DECIDED (Owner, 26 Oct):** Self / Gift toggle on the form. Gift → optional giver's name + optional message (placeholder shows an example; empty → our ready-written message; no name → "A Diwali gift for you"). Same ₹499. Delivered exactly like Self, to the form's number; the giver downloads/forwards it. Receiver's number is no longer collected (supersedes the 23 Oct "receiver only" rule below and the ₹199/₹299 gift price). O-1, O-3, O-25 closed.
- **Mock 3C v1 (26 Oct):** 3A with general Marriage + Family pages (no life stage), the approved Marriage questions + Manglik facts box (new card, 58 pages), and two light Wrapped touches (2.6 Wrapped card as a dark story panel + the 3 words in state colours; 12-months legend → "in numbers" tally). https://claude.ai/artifact/Hfxt5gUSt1RiJGrNDFpo2M · [mock/mock3c-v1.html](mock/mock3c-v1.html). Gate: 58 = 58 at 323×623, leak 0, banned none, 0 status phrases, 0 dead links, all page refs match. Waiting for owner review.
- **Life-stage version ARCHIVED (26 Oct):** Mock 3A/3B, the spec before the drop and the full build kit are saved in [archive/life-stage-version-2026-10-26/](archive/life-stage-version-2026-10-26/README.md) for future use (rebuild checked: 57 pages, 323×623).
- **Life stage DROPPED (Owner + uncle, 26 Oct):** no marriage/children question in the form. Marriage and Family & children have one general version that never assumes status; "not married 25+ → Marriage 2nd" rule removed; Marriage stays a pickable area (neutral content). Versions 2,688 → 896; tests about 72 → about 66 (+1 "no assumed status" lint). Neutral Marriage questions are PROPOSED (uncle to approve). Mock 3A Marriage + Family pages need the general rewrite; 3B life-stage cards obsolete. Spec backup before edit in session scratchpad.
- **Change map (25 Oct):** [changes-vs-mocks-2026-10-25.md](changes-vs-mocks-2026-10-25.md), page by page Mock 2 v2 → the new plan, plus the writing and picture changes. **All 6 decisions were answered (25 Oct):**
  - keep 5 front questions
  - a short Better luck section for everyone
  - when the choice is skipped, the chart picks the first area
  - add CI's end plan (priorities, 30/90/365 days, 5 takeaways)
  - add "The read" line per section
  - no archetype

  Next: fold everything into the spec (waiting for the owner's go-ahead; the work is still ON HOLD). **Done 26 Oct** (spec updated; the "chart picks the first area" answer above is superseded by the situation order, changes doc §5 item 7).
  - **Glow fix done (25 Oct), waiting for owner review:** [design/state-marks-v3.html](design/state-marks-v3.html) (page images `state-marks-v3-p1..5.png`).
    - Best = biggest, filled glow, rays all round, gold body, solid green tag.
    - Good = medium, one thin ring, no rays, cream body, outlined tag.
    - Careful = unlit, dashed outline, grey-sand fill, dashed tag.

    The states read in black-and-white print too. A sample 12-month kandil row is included and matches TIMING.md.
  - **Fix needed (original note):** in No. 6 (and every glow-based picture: diyas, kandils, anar), the owner cannot tell glowing from dim. The 3 states must be clearly different at a glance and in black-and-white print.
- **DECIDED (Owner, 25 Oct): never use "year" alone as a tag ("very good year").** Indians follow the normal calendar, so a buyer may think the good "year" ends in Jan 2027 instead of at Diwali 2027. Always name the span: "from this Diwali to the next (Nov 2026 – Oct 2027)".
- **NEXT (Owner, 25 Oct): one more sweep of Career Intelligence** (the best seller), compared with our mock and Life Blueprint. Remove the negatives of each and combine the strengths of all three.
- The comparison is done (25 Oct): [lifeblueprint-comparison-2026-10-25.md](lifeblueprint-comparison-2026-10-25.md). It recommends R1 (hybrid re-order), R2 (Life Blueprint's per-area pattern), R3 (fix density: brackets, dates, paired names) and R4 (Life Blueprint selling patterns). Waiting for the owner's decision.
- **Q1. Dynamic vs re-ordered report.** Keep the current plan (one deep dive for the chosen area, the other areas as summaries, branch-specific wording)? Or the uncle's plan (every buyer gets every section at full depth, and the chosen theme only decides the order)? The Life Blueprint comparison feeds this decision.
- **Q2. Readability and content depth.** The mocks are "hard to understand and lack content". What Life Blueprint does better, and what to copy, comes from the comparison.

**Waiting on the owner or uncle:**
- Q3. Gift price for a 2nd report (uncle). ₹299 recommended. (spec O-1)
- Q4. Does the giver get a copy? (O-3)
- Q5. Slug `/en/diwali-report` and product key `diwali` (O-2)
- Q6. Mock review: the Note text (p3), the Diwali look, and the agents' own readings ("love or arranged: both pull", where a partner may be met, hiring months)

**Facts to confirm before launch:**
- Q7. Tamil Deepavali date, Sat 7 Nov (confirm against Drik's Tamil calendar) (O-4)
- Q8. Which cities go in the puja table (O-18), and Chopda Pujan times (O-26)
- Q9. Helpline name and wording, checked by a person (O-11)
- Q10. The sign "Cancer" vs the banned word "cancer": "Karka" was used in the mocks (O-27)
- Q11. Gender options; the engine is binary (O-7)
- Q12. After 8 Nov: pinned date, window, dates page (O-8)
- Q13. Reviews for a new product vs the CCPA rules (O-14)
- Q14. Practices wording (O-16), Manglik rule when the birth time is unsure (O-17), gift note handling (O-19), Hindi fields now or later (O-22), the money vs whole-life balance (O-23), gift offer vs drip pricing (O-25)

**Already decided (kept for history):**
1. ⚠️ SUPERSEDED by the decisions below / the spec (decided later, spec O-3). In gift mode, does the giver also get a copy on WhatsApp? Today a report is only sent to the popup number.
2. ⚠️ SUPERSEDED by the decisions below / the spec (English first, Hindi after approval). Ship the Hindi version at launch, or English first? Hindi sales are close to zero, but the rule is both languages together.
3. ⚠️ SUPERSEDED by the decisions below / the spec (hand-checked top-cities table). Should we include a hand-checked puja-time table for the top 10 cities, or no city times at all?
4. ⚠️ SUPERSEDED by the decisions below / the spec (look back from the chart only, never naming an event). Parents' input (20 Oct): their worry is the family's future and the children's future. Can the report "read back" past events, like a hospital stay this year, to build trust? (Being discussed.)
