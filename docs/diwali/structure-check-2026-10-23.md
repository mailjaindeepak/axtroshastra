# Structure check, 23 Oct 2026 (4 independent agents)

These agents checked the draft structure. Their findings feed the spec. Code citations are from `upstream/aws-mysql` @ b437be0.

## 1. Facts and wording (research agent)
- **Dates (Drik Panchang, New Delhi):**
  - Dhanteras Fri 6 Nov
  - **Kali Chaudas Sat 7 Nov**
  - Narak Chaturdashi and Lakshmi Puja Sun 8 Nov
  - Mon 9 Nov: Amavasya, no festival
  - Govardhan, Gujarati New Year (Samvat 2083) and Bali Pratipada/Padwa Tue 10 Nov
  - Bhai Dooj Wed 11 Nov
- **Tamil Deepavali falls on Sat 7 Nov.** The source is Hindutone; it needs checking against Drik's Tamil calendar.
- Some calendars put the Gujarati New Year 1 day earlier or later, so print "dates for New Delhi; your city may differ by a day".
- In the North Indian calendar, Vikram Samvat 2083 began in March 2026, so say "Gujarati New Year (Samvat 2083)".
- **Sade Sati:** Saturn enters Aries 3 Jun 2027, goes back into Pisces 20 Oct 2027, and re-enters Aries 23 Feb 2028.
  - Aquarius Moon: ends Jun 2027, then restarts.
  - Taurus Moon: starts Jun 2027, pauses Oct 2027, resumes Feb 2028.
  - So show phases across the whole of Nov 2026 to Oct 2027.
- **Guna score needs 2 charts.** One buyer has no guna score. Manglik works from one chart; the report must state the rule used (from the rising sign, the Moon, or both).
- **Better luck = the 9th house (bhagya).** Add it to the deep dive and to B.3.
- **§5b word fixes:**
  - "calm facts" → "plain facts"
  - "medical advice" → "professional advice"
  - "how everyone at home will be keeping" → "how home life will go", because in Indian English the first one suggests a health prediction.
- **Drugs and Magic Remedies Act 1954:** never link a prayer or ritual to having children or to health. Practices cover money and luck only, with no promised outcome.
- **ASCI:** money and career timing are "good periods", never promises. The FAQ must say nothing is guaranteed.
- **Dhana Yoga "absent"** depends on the definition used, so fix one definition before saying it is absent.
- **CCPA:** ₹499 must be shown before checkout. No add-ons added later in the flow (drip pricing), and no fake countdown.

## 2. What the code can already compute (code agent)
| Section | Status | Source |
|---|---|---|
| Cover | EXISTS | `engine.py:117` `compute_chart` |
| 5 answers, 4 parts, at a glance, blessing/share card | WRAP | built from other sections, `vimshottari_tree` `engine.py:149` |
| Year gone by | WRAP | vyapar last-3-years `products.py:1018-1060`, `_past_analysis` `engine.py:635` |
| Money picture | EXISTS | Dhana Yoga `products.py:1175-1202`, vyapar money ~1092, blueprint wealth ~557 |
| Money timing | WRAP | vyapar strong window `products.py:962`, `year_by_year` 1144, blueprint `_ad_phases` ~659 |
| Career and income | EXISTS | `career_growth_report.py:298` (takes `as_of`); 6th house is a small WRAP |
| Business | EXISTS | `compute_vyapar` `products.py:785` (has no `as_of`) |
| Home and children | WRAP | blueprint HOME_4/CHILDREN_5 ~589, `_ad_phases`, `vidyarthi.py:70` |
| Marriage | EXISTS/WRAP | `engine.compute_report` `engine.py:342`, manglik `:312`, `marriage_extras` `:757` |
| Sade Sati | WRAP | `_sade_sati` `engine.py:612` has no start month when active, no end month when not active, and misses the re-entry. Needs a 2-way scan plus a re-entry check, about 15 lines. |
| 3 strengths | WRAP | blueprint strengths ~525 only counts own/exalted planets, so it can be empty. Rank by `_biz_planet_power` `:766` or `bhinnashtakavarga` `divisional.py:166` so there are always 3. |
| Months to go slow | WRAP | vyapar careful `products.py:1069`, `_dasha_remedies` `engine.py:705` |
| 12 months | WRAP | No month-by-house function exists. About 10 lines on `sidereal_lon`/`sign_of`/`houses_from` (`engine.py:79/86/99`). **Decision: add the fast planets (Sun, Mars, Venus).** |
| Chart picks the strongest area | WRAP | blueprint `wheel` ~601 and `_phase_read` ~650, about 15 lines |
| Gold months | NEW | No traditional rule exists. **Decision: our own rule, labelled.** |
| Practices | WRAP | `REMEDY_7L`/`REMEDY_NODE`, `_biz_remedy_line` `products.py:772`. **Strip the gemstones.** |
| Chart, planets, houses | EXISTS | `report_view.py:67` `north_chart_svg`, blueprint `chart.planets`, `houses_1_12` ~700 |

Notes:
- **Date drift.** `compute_vyapar` and `compute_blueprint` use `datetime.utcnow()` (`products.py` ~522, ~804). The report must pin `as_of` to Diwali 2026.
- **Dhana Yoga is narrow.** It only checks whether the 2nd and 11th lords are linked, so "absent" will come up often.
- **Children.** The 5th house in a parent's chart describes the parent, so a child's studies need the child's own chart. There is no timing engine for when children may come, so give only a soft range.
- **Marriage windows.** When nothing is strong, the code lifts weak periods to "Building" (`engine.py` ~415). Say so in the report.

## 3. Coverage (verify agent)
- **Fully covered:** all 7 of the uncle's sections, his 4 dimensions, his 4-part view, the no-scores rule, the father's needs, and 10 of his 12 questions.
- **Partly covered:** Q8 (turning point) and Q12 (new beginnings).
- **Gaps found:**
  - Chopda Pujan (in both research rounds and all 3 council proposals)
  - ad-intent (it belongs in the build notes)
  - Sade Sati free steps
  - a helpline line for married couples in conflict
  - debt recovery
  - layoff recovery (only covered in the deep dive)
  - "love or arranged"
  - city puja times (later decided: a top-cities table)
  - unsure birth-time behaviour (later decided: the Moon-sign fallback)
- **README sections now superseded:** ₹299→₹399, 3 themes, "leave out family", "skip marital status", WhatsApp via popup, "other two themes half a page", and the 20 Oct status / Open Question 2.
- **Invented by neither research:** nothing, apart from the guna "score", which was then removed.

## 4. Recipe compliance (recipe agent)
- The recipe "welds" (locks) the cover, "A Note for You" (page 2, only the first name changes) and Thank you. **Decided:** the gift note gets its own page after the cover, and A Note for You stays at page 2.
- **Diwali look:** the recipe allows re-skinning through `:root` tokens only. New motifs need a written exception. Opacity values in recipe §06 only cover cream/sand. **Decided:** light base plus Diwali accents.
- **Exhibit grammar (§05):** every data page uses exlabel → action → subtitle → rule → SVG → legend → takeaway. The spec must assign an exhibit to the 4-part year, money timing, strengths, 12 months and the birth chart. The 12 months probably needs 2 cards to avoid clipping.
- **Page numbers:** they change per buyer. A CSS counter cannot be cross-referenced, so the renderer computes them for "read more on page X".
- **Pipeline:** recipe §12.3 string-replaces values into one approved body (CI style). This report branches and uses AI text, so the spec says: the recipe for the design, the CLAUDE.md §11 pipeline (compute → narrative → render) for the content.
- **Leak-gate grep list:** vyapar, business growth, rohit, Rajesh Menon, the Diwali mock persona, every §5b word, dosha, curse, danger, guaranteed, cure. Watch for false hits on "Business outlook" text.
- **Recipe contradiction:** the Note tile is 224px in §06A but "158px" in the §10 log. Follow §06A.
- Written exceptions the spec must record:
  - popup removed (§1)
  - Hindi after English (§7)
  - gift page added to the fixed pages
  - Diwali skin (§01/§06)
  - pipeline (§12.3 vs §11)
