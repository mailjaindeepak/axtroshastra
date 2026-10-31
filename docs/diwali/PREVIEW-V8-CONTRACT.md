# Diwali free preview, build contract (approved mock: v8)

Approved visual spec (read-only reference, do not copy the mock chrome): `docs/diwali/mock/diwali-preview-v8.html`
(artifact https://claude.ai/artifact/62NcxfKeY1869WVaXaxd9a, local file in this worktree, untracked).
Live code base: `upstream/aws-mysql` @ 47859ea (this worktree, branch feat/diwali-preview-v2).

## Owner decisions (31 Oct 2026) that this build implements
- One visitor's preview, in this order: (1) cover with the 5-questions card (NO verdict tags/chips) + one plain line "Your report starts with <area>";
  (2) full kundli: full-size North-Indian chart, planet table OPEN, then a 2x2 grid of equal boxes: Moon sign, Birth star, Planet period now, Sade Sati; rising sign only in the chart caption;
  (3) "Your months before this Diwali": 2 identical-size cards (last two 2-month blocks before this Diwali, i.e. Jul-Aug 2026 and Sep-Oct 2026) + plain line "Does this match what you lived through?" (no buttons);
  (4) ONE free future card "Your first months after Diwali" (Nov-Dec 2026), same size as the past cards;
  (5) ONE combined "Your full report" card: a 12-block future strip (Nov 2026 .. Oct 2027, initials N D J F M A M J J A S O; blocks 1-2 open + coloured by tone, blocks 3-12 locked with NO tone), 3 short "what you get" lines, ONE Unlock button, a "See a sample report" BUTTON directly under it (opens the existing sample modal), then the line "Your report is made for you and sent right after payment. If it does not reach you, we will resend it.".
- The sticky bar (30-minute timer + struck 999 -> 499 + Unlock) is the only other buy element; it is hidden at the top, shown after the cover, and HIDDEN while the main Unlock button is on screen (never two Unlock buttons visible).
- Removed from the preview area: the Wrapped story (all slides), the emphasis card, the "Also in your report" grid, badges, in-preview reviews, the info strip, the "PDF on WhatsApp" text/buttons, the bead-string card borders, gold stroke bars and the tiny caption lines. Sections BELOW the preview on the landing page (what's inside, reviews, why different, don't know the time, FAQ, final CTA) and the hero (incl. the hero offer-timer pill) stay as they are on the live page.
- Festive art: toran garland, diyas, fireworks canvas (stops after ~6 s, none under prefers-reduced-motion), 4 swaying approved kandil lanterns on the cover, faint rangoli corners, diya icons in section labels. Decorative only.
- No refund wording. No claims (no IIT-IIM, no "exact planet positions", no comparison claims).
- Sanskrit sign names everywhere: Mesha, Vrishabha, Mithuna, Karka, Simha, Kanya, Tula, Vrishchika, Dhanu, Makara, Kumbha, Meena.
- Past/future text is chosen by the buyer's WORK TYPE (job / business / student / home; the form already asks it) and the engine's tone for that block. No age logic. No AI call for the preview.
- Plain words. Banned in all visible copy: stretch, window, phase, tendency/tended/tends, steadier, favourable, pivotal, culminate, auspicious, pressure, karma, dasha, house, bhav, transit, "dues", "patient", "year" alone; plus every CLAUDE.md section 5b health/mental word; never AstroSage.

## Teaser contract (server -> browser, BEFORE payment)
`/api/kundli` returns only `report["teaser"]`. Keep every existing teaser key. ADD `teaser["preview"]`:
```
"preview": {
  "version": 8,
  "work_type": "job" | "business" | "student" | "home",
  "moon_basis": true|false,              // true when the chart is read from the Moon sign (unsure birth time)
  "start_area": "Career",               // same text as the existing emphasis area
  "chart": {
     "rising": "Mesha" | null,          // null when basis is moon
     "moon": "Kanya", "star": "Uttara Phalguni",
     "period": "Rahu – Mars",
     "sade_sati": {"active": false, "stage": null | "first" | "middle" | "last"}
  },
  "past": [ {"range": "Jul – Aug 2026", "tone": "good|steady|careful", "heading": "A good time", "text": "<7 plain sentences>"},
            {"range": "Sep – Oct 2026", ...} ],
  "future_free": {"range": "Nov – Dec 2026", "tone": "...", "heading": "...", "text": "..."},
  "strip": [ {"m": "N", "label": "Nov 2026", "open": true, "tone": "steady"},
             {"m": "D", "label": "Dec 2026", "open": true, "tone": "steady"},
             {"m": "J", "label": "Jan 2027", "open": false}, ... 12 entries, locked ones have NO tone key ]
}
```
Do NOT change the existing `teaser.planets[].sign`, `kundli`, `moon_sign`, `lagna_sign` values (the chart drawing keys off them). Instead add `preview.sign_names` = {"Aries":"Mesha","Taurus":"Vrishabha","Gemini":"Mithuna","Cancer":"Karka","Leo":"Simha","Virgo":"Kanya","Libra":"Tula","Scorpio":"Vrishchika","Sagittarius":"Dhanu","Capricorn":"Makara","Aquarius":"Kumbha","Pisces":"Meena"} and the page maps every DISPLAYED sign name through it (planet table, tiles, chart caption, chart cells). `preview.chart.rising/moon` are already Sanskrit.
Tone mapping: engine tones best/good -> "good", steady -> "steady", careful -> "careful". Block tone = the more serious of its two months (careful > steady > good). Heading by tone: good "A good time", steady "A mixed time", careful "A slower, costlier time".
Past blocks come from the PAST window = a second compute with as_of one year earlier (same chart, as_of `<as_of year-1>-11-08`), last two 2-month blocks; the future block from the normal months list (first 2 months).
SECURITY / NO LEAK: the teaser may contain month names ONLY in `preview.past[*].range`, `preview.future_free.range`, `preview.strip[*].label`; never tones or text for locked months; never best/careful windows; never any other future text. The browser must not receive locked content at all (CSS blur is not protection).
Readings text: `diwali_readings.pick(kind, work_type, tone, seed) -> str` (kind "past" | "future"; tone good|steady|careful; seed int). Data in `diwali_readings_past.py` (PAST[work_type][tone] = [v1, v2, v3]) and `diwali_readings_future.py` (FUTURE[work_type][tone] = [v1, v2, v3]); each text = opening line + 5 short sentences each about a DIFFERENT everyday area + a summing-up line (7 sentences, each max 18 words), plain daily English; past tense for PAST, future-looking hedged ('may', 'is likely') for FUTURE; at most one 'probably'; every careful text has one easing line and a non-gloomy ending. seed = (sum of ord() of moon sign + rising sign names + block index) % 3 so two buyers with different charts often differ.

## Files and owners
- diwali.py + new diwali_readings.py + tests/test_diwali_preview.py (+ small edits to tests/test_diwali_engine.py leak tests): BACKEND agent.
- diwali_readings_past.py: PAST-TEXT agent. diwali_readings_future.py: FUTURE-TEXT agent.
- pages/diwali.html: FRONTEND agent. tests/e2e/diwali.spec.js: updated later by a TEST agent.
- Nobody commits, pushes or touches git. Never read diwali_bank.py whole.
