# Axtroshastra — universal repo rules

Tracked, ships with every clone. Read this before adding, editing, or scaling any
page/product. Personal workflow prefs (how *I* like to collaborate) live in the
gitignored `CLAUDE.local.md` — this file is the opposite: rules the *site* needs
regardless of who's driving. Full rationale + proof-of-catch for each rule is in
`docs/HANDOVER-2026-08-27.md` and `workflow_sh/rule.md` — this is the compressed,
enforceable version. Every rule below traces to a real incident from that handover,
not a hypothetical — grep the doc for the task number in parens if you want the
original story.

## Quick checklist — read this before starting any new page/product

1. Confirm the funnel follows the standard shape (§1) — call out anything different.
   Form inputs reject bad data explicitly, never silently guess (§1).
2. Build both language files together: `<slug>.html` + `<slug>.hi.html` (§7). Ask
   whether Hindi ships side-by-side or after English is approved — don't assume.
3. For Hindi text: reuse the existing dictionaries (§7) — never re-translate from
   scratch. Check JS-built popups too, not just the static HTML (§7). Sanity-check
   Devanagari headlines don't clip (§7).
4. For the paid report's PDF: reuse an existing theme (§8), mock it visually and get
   it approved *before* touching the real renderer/pipeline (§8), and hide every
   non-report chrome element with `@media print` (§8).
5. Every page: the exact `<head>` block (§2), registered in `sitemap.xml` **and**
   `ops/robot_customer`'s route list (§3) — never hand-rolled nav (§6). Renaming a
   live URL keeps a 301 by default — ask whether it's forever or temporary (§2).
   Never link to a route that isn't registered yet (§2).
6. Ask whether the new product belongs on the homepage — card + reviews (§4). It
   won't happen on its own; the homepage was deliberately trimmed once before.
7. Write the page's own on-page reviews (§5) — every product page gets these,
   regardless of the homepage answer in §4.
8. Every paid report page: PDF-download + WhatsApp-share buttons (with a text-only
   fallback template, not just the PDF one) (§9), funnel tracking, EN/HI toggle that
   carries form fields but clears the name+preview on switch, if it has this
   mechanism at all (§7, §9).
9. If the product has a gender- or condition-branching path, both branches need
   their own test, not just the default one (§12).
10. Any new money/admin-facing logic: persist the real charged amount, reuse the
    canonical test-data flag (§13).
11. Before push: all gates green (§10), and upstream checked directly, not assumed
    from an earlier "merged" statement (§15).
12. Any claim in this file (or anywhere else) about how a live page behaves gets
    checked against the actual live site before it's trusted or repeated (§14).
13. When the task is done: post the rule-by-rule checklist (§16) — don't wait to be
    asked "did you also do X."

---

## 1. Standard funnel flow — every product follows this shape

This is the shape you already see on `/en/compatibility` (milan) and every other
product. A new product follows it by default:

**Form filled → preview/teaser shown → popup asks for name+phone (+optional email)
→ payment → full report generated & delivered (page + PDF + WhatsApp).**

- The popup is where we capture contact details — *before* payment, not after.
  Its phone number is what WhatsApp delivery actually uses (`tests/test_contact_capture.py`).
- **WhatsApp delivery always goes to that popup number, never to Razorpay's own
  payment-contact number** — confirmed in code: `phone = rec.get("user_phone") or
  pay_phone` (`api.py:1214`) explicitly prefers the popup number and only falls back
  to Razorpay's contact if no popup number was ever captured. A new product's
  delivery step must follow the same preference order, not deliver to whatever
  number Razorpay happened to collect at checkout.
- The teaser/preview must be real computed data, not a placeholder — it's what
  convinces someone to pay.
- **Never let ambiguous or partial input silently default to a specific guessed
  value — force an explicit inline error instead.** A partial time-of-birth used to
  silently submit as 1 AM; an out-of-range birth date used to submit unchecked. Both
  were fixed to block submission with a clear inline message instead. Any new form
  field with a "we don't actually know this" state should follow that pattern, not
  invent a silent default.
- **WhatsApp delivery needs two templates, not one**: the real PDF-media template,
  plus a text-only fallback for when the PDF isn't ready yet at send time
  (`TWILIO_CONTENT_SID` / `TWILIO_CONTENT_SID_TEXT`). A new product's delivery step
  should wire both, not just the happy-path media one.
- If a product genuinely needs a different shape (e.g. no preview, or a multi-step
  form), that's fine — but it's a deliberate exception the developer calls out
  up front, not a silent deviation.

## 2. Every new static page needs this exact `<head>` block

Copy the pattern from `pages/shaadi.html` or `pages/marriage-v2.html`, not from memory:

```html
<link rel="canonical" href="https://www.axtroshastra.com/en/<slug>">
<link rel="alternate" hreflang="en" href="https://www.axtroshastra.com/en/<slug>">
<link rel="alternate" hreflang="hi" href="https://www.axtroshastra.com/hi/<slug>">
<link rel="alternate" hreflang="x-default" href="https://www.axtroshastra.com/en/<slug>">
<meta property="og:title" content="...">
<meta property="og:description" content="...">
<meta property="og:image" content="https://www.axtroshastra.com/static/og.png">
<meta property="og:url" content="https://www.axtroshastra.com/en/<slug>">
<meta property="og:type" content="website">
<meta name="description" content="...">
```

- The Hindi twin's `canonical` and `og:url` point at **its own** `/hi/<slug>` URL, not
  back to English — hreflang, not canonical, is what links the two languages together.
  Every EN/HI pair site-wide already follows this; don't collapse it to one canonical.
- A page that should never rank (dead-link fallback, ad-only funnel variant you don't
  want competing with the main page) gets `<meta name="robots" content="noindex,follow">`
  instead of the canonical block — see `pages/coming-soon.html`.
- If a page exists as a paid-ads-only variant of an existing page (see `marriage-v2`/`-v3`,
  which run alongside `/en/marriage` for A/B ad copy), it stays **out of `sitemap.xml`** and
  keeps its own self-canonical — don't canonical it onto the main page or you break the
  A/B split; don't add it to the sitemap or Google will rank it against the page it's
  supposed to be an ad variant of.
- **Never write a link to a route that doesn't exist yet.** A dead primary CTA
  (`/en/kundli`, never a real route) and 62 dead "guide" links to hub pages that were
  never built both shipped this way — assumed a page "should" exist instead of
  checking it was actually registered in `api.py`. Confirm the target route exists
  before publishing the link; if it doesn't yet, point at `coming-soon.html` instead.
- **Renaming or restructuring a live URL always keeps a 301 from the old path by
  default.** Every URL change on this site so far (`/shaadi`→`/en/marriage`, the
  celebrity slug restructure, etc.) shipped a redirect specifically so nothing already
  indexed, bookmarked, or shared externally breaks. Never just move a route with no
  redirect. But "permanent" isn't automatic either — **ask the dev whether the old
  URL should keep redirecting forever, or eventually be removed entirely** (e.g. once
  its old links have had time to age out of search/bookmarks). Default to keeping the
  redirect until told otherwise; don't silently delete an old route, and don't
  silently assume it must live forever either.

## 3. Register every indexable page in the sitemap **and** the smoke-test route list

`api.py`'s `sitemap()` builds `urls` from a hardcoded list — a new page is invisible to
search until it's added there. Non-indexable pages (ads variants, legal-adjacent
utility pages, `/report/<id>`) deliberately stay out. Celebrity pages are the one
exception — their slugs are read straight off disk (`_celebrity_slugs()`), so they
sitemap themselves automatically; every other product page is manual.

**Separately, and just as easy to forget:** `ops/robot_customer/robot.spec.js` has
its own hardcoded page/product lists (`ALL_PAGES`, the per-product `paths` block) that
drive the live-site health smoke test. Business Growth was added there by hand
(`robot.spec.js:89-90,338-339`) when it shipped — a new product needs the same, or the
smoke suite simply never checks it, silently.

## 4. Homepage discoverability — ask, don't assume either way

`pages/home.html` currently lists only 2 product cards (Marriage, Compatibility) and
its reviews carousel only has entries tagged for those two. **This was a deliberate
cut, not an oversight** — Business Growth and Career Growth already exist as full
products with their own working pages and their own on-page reviews, but were never
added back to the homepage after that cut, so they're effectively invisible to
anyone who only lands on `/`.

Because the 2-product homepage was a real, intentional decision once, a new product
does **not** get auto-added — but it also doesn't get silently left off just because
the last product was. **Ask explicitly**: does this new page get a homepage card
(`.prod .card`, same pattern as the existing 2) and matching entries in the homepage
reviews carousel (`#revsTrack`)? Get a yes/no, then act on it — don't decide either
way on your own.

## 5. Reviews — write for every new product page, in the site's existing voice

Every product page ships with its own on-page reviews block (`.rev` / `.who`, same
pattern as `business-growth.html`, `career-growth.html`, `marriage-v2.html`). Write
5–8 of them for any new page, before calling the page done. If §4 says the product
also goes on the homepage, add matching tagged entries to `home.html`'s `#revsTrack`
too — same review, or a fresh one, tagged with the product name like the existing
`<div class="tag">Kundli Milan</div>` entries.

**House style — match what's already live, don't default to generic ad copy:**
- Short. 1–2 sentences, not a paragraph. Every existing review on the site is this
  length.
- One concrete, specific detail beats generic praise — an age, an occasion, a
  number, a family member's reaction, an occupation. "Great service, highly
  recommend" reads nothing like the reviews already on this site.
- Casual, slightly imperfect phrasing over polished sentences — the way someone
  actually types, not how ad copy is written.
- Mix in Hinglish where the product's audience would naturally use it (heavy for
  casual/young-audience products like Marriage/Milan, as already shown) — for a
  more formal-audience product like Business Growth, follow *that* page's existing
  reviews instead (plain English, occupation + concrete numbers, no slang) rather
  than forcing the same casual style everywhere. Match the audience already
  established on that product's own page.
- Emojis used the way people actually text them (💀 🙏 😅 ✨ 🥺 💯), not decorative
  bullets — and not on every single review.
- Vary sentence structure, length, and punctuation between reviews. The biggest
  tell that a batch of reviews isn't genuine is that they all follow the same
  template — avoid that.
- Avoid stock phrasing that reads as written *about* a product rather than *by* a
  customer: "seamless," "game-changer," "highly recommend," "elevate," "unlock,"
  "robust," "testament to," "in today's world."
- 5 stars, reviewer as first-name+age / first-name+occupation / two names for a
  couple — same format as every existing review.

**Carousel mechanics:** don't build the auto-scroll with cloned/duplicated review
elements to fake an infinite loop — that already shipped once as a real bug (duplicate
clones, a jarring jump from the last review back to the first). The current
`#revsTrack` implementation deliberately shows the real reviews once, no cloning —
follow that, not the old pattern.

## 6. Never hand-roll nav/footer/tracking — serve through the injection chain

Every page must go through `_serve_page_with_nav()` in `api.py`, which pipes
`_inject_tracking → _inject_nav → _inject_footer_link`. Pasting nav/footer HTML
directly into a new page file means it silently drifts from every other page's nav
the next time the nav changes once, centrally.

Two separate CSS token systems exist — don't cross them:
- **Marketing pages** (`pages/*.html`): `--ink --midnight --midnight-2 --paper --sindoor
  --haldi --muted --line --radius`.
- **Admin dashboard** (`dashboard/static/index.html`): `--panel --panel2 --line --ink
  --body --mut --gold --ok --warn --crit`.
A real bug shipped when dashboard code was written against marketing-page-style
variable names that don't exist in the dashboard's own `:root` — 76+ silent no-op
overrides. Grep the actual `:root{...}` block of the file you're editing before
naming a variable; never assume a token exists because it exists elsewhere.

## 7. Language registers — build order, reuse dictionaries, and Devanagari's own quirks

`<slug>.html` = English, `<slug>.hi.html` = Hindi (Devanagari). A feature isn't done
until both files have it.

**Build order is a question, not a default.** Ask whether the Hindi twin ships
*side-by-side* with English or *after* English copy is finalized — both are valid
depending on how settled the English content is; don't silently pick one.

**Never translate from scratch — reuse what already exists:**
- `jyotish_maps.py`'s `*_HI` glossary — shared astrology-term translations
  (nakshatras, houses, planets, etc.) every product should pull from.
- Per-product phrase banks already written: `milan_hi_data.py`, `shaadi_hi_data.py`,
  `vyapar_hi_data.py`. A new product's Hindi should start by copying the closest
  existing `*_hi_data.py` file and adapting it, not writing Devanagari prose fresh —
  this is both faster and keeps wording consistent across products.

**Content rule:** zero Roman-script Hindi, zero stray English in visible text
(brand/product words like AxtroShastra/WhatsApp/PDF are allowlisted). This is
enforced by `tests/test_hindi_leakage.py`, not just a guideline.

**Hinglish is dead — do not build one for a new product.** The route
`/hinglish/{slug}` (`api.py:2459`) still technically serves `<slug>.hinglish.html`
files, and `career.hinglish.html` is the one legacy page still using it, but this
register is discontinued. English + Hindi is the only pair for any new page —
Hinglish is not an option to offer or default to, even if asked loosely for "the
usual language versions."

**Three Devanagari-specific gotchas, each a real bug once:**
- **Letter-spacing breaks conjuncts.** CSS `letter-spacing` tuned for Latin text
  visually splits joined Devanagari characters apart — don't apply a blanket
  letter-spacing value to a block that might render Hindi.
- **Matras (vowel signs) can overflow their container** if the layout was only ever
  sized/tested against the English version. This bit business-growth's Hindi hero
  and wasn't a hero-only issue — it was page-wide. Actually look at the rendered
  Hindi page, don't assume a layout that fits English text fits its Hindi twin.
- **JS-built content is invisible to a plain HTML check.** The site's contact popup
  is built by JavaScript, not static markup — it shipped un-translated the first time
  because nobody thought to check content that isn't literally sitting in the `.hi.html`
  file. Any modal/popup/dynamically-inserted text needs the same Hindi check as the
  static page around it.

**The EN/HI toggle preserves form fields, but deliberately clears the name and the
generated preview — this is correct, not a bug, don't "fix" it back.** Checked
directly against the live `/en/compatibility` and `/en/marriage` pages
(`pages/milan.html:1153-1197`, `pages/shaadi.html` same block), not just the
handover doc's word for it:
- DOB, time-of-birth, place/city fields **are** carried across a language switch
  (`sessionStorage`, keyed `axtro_milan_state` / equivalent), so the user doesn't
  have to re-type them.
- The **name field is explicitly skipped** (`SKIP_ON_SWITCH`) — a name typed in one
  script shouldn't linger in the other.
- The **generated preview/report is explicitly nulled** (`REPORT_ID=null;
  window.__teaserData=null`) on switch, on purpose: the existing preview is in the
  *old* language, and letting someone pay against it would unlock a report in the
  wrong language. A fresh preview is forced instead.
- A `_formStarted` flag is carried too, specifically so the programmatic restore of
  field values doesn't spuriously re-fire the `form_start` funnel-tracking event —
  this is the "funnel firing" guard the preview-nulling and name-skipping logic
  exists alongside; don't strip it out while touching this code.

**This mechanism does not exist on every funnel page.** `shaadi.html`, `milan.html`,
`marriage-v2.html`, `marriage-v3.html`, and `business-growth.html` all have it;
`career-growth.html` and `jeevan.html` (life-blueprint) currently do not. Don't
assume a new product has this "for free" — copy the block from `milan.html` if it
needs it, and preserve the same three exclusions (name, preview, and the
form-start-tracking guard), not just the field-carrying part.

## 8. PDF / report visual theme — reuse the theme, only write new content

**The PDF converter itself (`pdfgen.py`) is already 100% generic** — it turns
whatever HTML it's handed into a PDF, with zero product-specific logic. The part
that actually needs "explaining" every time is the report page's own HTML+CSS
(theme, layout, section chrome) — because today that is **not** a single shared
template; it's copy-pasted per product with only the colors changed.

**The fix already proven to work once — make it the default going forward:**
`_VYAPAR_CSS` + `_VYAPAR_DEFS` (`report_view.py`, business-growth's theme — the
"card-per-page" v17 look) is a real shared constant that `render_blueprint` already
reuses **verbatim**, no changes. Any new report product (health-growth, etc.) should
do the same: import `_VYAPAR_CSS`/`_VYAPAR_DEFS` and build its sections inside that
theme, instead of writing new CSS. Only the marriage/milan/career_growth family
still has each product's CSS hand-duplicated — don't extend that pattern; every new
product goes into the shared Vyapar theme unless there's a specific reason not to.

**Be clear about what this does and doesn't save:** reusing the CSS means the new
report *looks and behaves* identical (same fonts, colors, spacing, page-break rules,
buttons) automatically — no design/theme conversation needed. It does **not** mean
the new report's sections write themselves: there's no "content-only" template engine
today (nothing loops over a list of sections to build the HTML — every product's
`render_<product>()` still hand-writes its own section markup, just inside the shared
CSS). So think of it as **reusing the Canva theme, not an auto-filled Canva template**
— you skip the "what should this look like" conversation entirely, but still write
each section's HTML once, following business-growth's `<!-- 01 COVER --> ... <!-- NN -->`
section-comment structure as the copy-paste starting skeleton.

**If a true swap-content-keep-everything template is wanted** (genuinely no new
section markup, only new text/data per product), that needs a real one-time build —
a generic renderer that takes a list of `(section_type, content)` and produces the
HTML, which nothing in the codebase does today. That's a deliberate, scoped project,
not something to assume — ask before starting it.

**Mock the PDF visually before touching the real renderer — don't iterate on the
slow path.** This is how Business Growth's PDF was actually built, and it's the
default for any new product's report:
1. Finalize the report's content and section list first.
2. Build a standalone preview of the PDF (an HTML mock — an artifact works well for
   this) reusing the shared theme from above, not the real `render_<product>()`
   function and not the real `narrative.py`/LLM pipeline.
3. Print/export that preview to PDF from the browser and actually look at it —
   page breaks, overflow, spacing, whether a section reads right.
4. Fix what's wrong in the mock and repeat step 3 until it's right.
5. Only once the mock is approved, port it into the real `render_<product>()`
   function and wire it through the actual pipeline (`api._render_for` → LLM
   narrative → `pdfgen.py`).

The real pipeline is expensive to iterate on for a pure layout/content tweak — it
involves an LLM narrative pass and a real WeasyPrint/xhtml2pdf conversion. Mocking
first means every visual fix happens in the cheap, fast loop; the expensive path
only runs once, after the design is already locked, not on every small correction.

**Every non-report UI element needs an explicit `@media print` hide.** The language
toggle, the download/share buttons, the sticky CTA bar — none of these belong in the
generated PDF, and none of them hide themselves automatically. Every existing report
renderer has a `@media print{#axlang{display:none}...}` block for exactly this (see
`report_view.py`, e.g. lines ~364, 557, 1680, 2285, 2521). A new product's report
needs the same, or its chrome silently prints/PDFs into the customer's paid document —
this already happened once with an account banner that leaked into print output
before being fixed.

## 9. What must be identical on every paid report page

By default, unchanged from product to product — a developer explicitly calls out
anything that needs to differ:
- Download-PDF button (`axPdfDl`) + WhatsApp-share button (`axShare`) — checked by
  `tests/test_report_buttons.py`, which fails the build if either is missing.
- Funnel tracking fires at the same points (page load / lead / checkout / purchase)
  every other product fires at — this is what LinkedIn/Meta ad tracking depends on.
- The `#axlang` EN/हिंदी toggle, same two-link pattern as every other page, carrying
  form fields but clearing the name and preview on switch, per §7.

## 10. Gates that must be green before any push — no exceptions

- `pytest` (full suite)
- Playwright E2E (`tests/e2e`)
- `ops/robot_customer` smoke (live funnel/page/SEO health, mobile+desktop) — only
  actually covers a new page if it was added to the route lists per §3
- `tests/test_report_buttons.py` — PDF/WhatsApp buttons (see §9)
- `tests/test_hindi_leakage.py` — every Hindi product rendered with the LLM **off**
  (worst case) and **on**, fails on ≥4 consecutive English words. This is the only
  thing that actually guarantees "pure Hindi" — not a promise, a test.
- Import audit vs `requirements.build.txt`, server boot + `/healthz`, auth-gate check

## 11. Any new report *product* — the backend pipeline

Must follow the same pipeline every existing product follows — this is
`workflow_sh/rule.md` §5, don't re-derive it:

1. `compute_<product>()` — deterministic astrology only, no LLM, returns facts +
   teaser (with authored `_hi` Devanagari twin fields) + `meta.lang`.
2. `narrative.py` — LLM writes prose only, in `meta.lang`, never computes a fact.
3. `render_<product>()` — HTML from `prose(key, bank) = narr(key) or bank`; when
   `meta.lang=='hi'`, every deterministic fallback is itself composed in Devanagari.
   Theme = §8 above.
4. `<product>_hi.py` (+ `_hi_data.py`) — localizes the fixed shell (headings/labels)
   after render, reusing the dictionaries in §7.
5. `api._render_for` dispatches; `_wire_report_chrome` adds nav/PDF/WhatsApp/toasts
   **after** localization, in-language.
6. Explicit `/en/<slug>` + `/hi/<slug>` routes, legacy `/<slug>` → 301 `/en/<slug>`,
   inline `#axlang` EN/हिंदी toggle.

Do not copy a legacy quirk from an existing product into a new one (e.g. milan's old
v1/v2 toggle handling) — conform to the clean pattern and flag the quirk instead of
propagating it.

## 12. Test data and branch coverage

The whole suite shares one DB. Every new test needs a phone number that's unique
across the **entire** suite, not just its own file — mobile number is the de-dupe key
(first email wins on a collision), so a reused number silently corrupts an unrelated
test's assertions.

**Any gender- or condition-branching logic needs a test on every branch, not just the
default one.** A real bug shipped where Jupiter was silently dropped as a marriage
significator specifically for female reports — the male path was tested, the female
path wasn't, so it went unnoticed. If a new product's engine branches on an input
(gender, a yes/no flag, a regional variant), write a test per branch, not one test
that happens to exercise whichever branch is default.

## 13. Money and admin-reporting data integrity

Two standing invariants for anything that touches payments or the admin dashboard's
numbers, both learned from real dashboard bugs:

- **Persist the actual amount charged at payment time; never recompute it later from
  current pricing.** `amount_paise` is stored on the `reports` row precisely because
  prices change over time — recomputing an old order's amount from today's price
  config silently rewrites history. A new paid product must store its real charged
  amount the same way, not derive it after the fact.
- **Test/demo data is excluded from real numbers through exactly one flag: `is_test`**
  (computed in `dashboard/routes.py`'s `_classify_exclusion()` — free-pass unlocks,
  pre-launch rows, and the team allowlist all funnel into it). Any new report/revenue
  view must filter on that same flag, never invent a second, slightly-different
  test-exclusion condition — that's exactly the kind of drift that produced the
  dashboard's original CSS-variable-style bugs.
- **A "real customer" specifically means a genuine Razorpay `pay_*` payment id** —
  `_classify_exclusion()` checks this directly (`not _is_razorpay_id(payment_id)` →
  excluded as `"test"`). A `free_pass:`-prefixed or `demo` id is a tester, not a
  customer, no matter how the row otherwise looks. Any new admin view or metric that
  counts "customers" must use this same check, not just `paid=1`.

## 14. Never trust a build/agent's own "done" report — or a doc's word for how the live site behaves

Independently re-run the real checks against the actual output every time:
`Celebrity-Personalities-Kundli-SEO/_audit_images.py` for any celebrity page, a
dead-link sweep for anything touching routes/nav, `git diff`/grep for anything an
agent claims it fixed. This has caught real evasions (class renames to dodge a
completeness checker, duplicate closing tags, wrong dates) that the agent that made
them reported as clean.

**This applies to this file's own rules too, not just an agent's output.** A rule in
here can go stale or just be wrong — §7's language-toggle rule was written from the
handover doc's summary of an old task and got the actual current behavior backwards
(it claimed the preview was preserved; the live code deliberately clears it). That
was only caught by `curl`-ing the real `/en/compatibility` page and reading the
actual script, not by re-reading the doc more carefully. So: **before stating a rule
about how a live page behaves, or before trusting an existing rule that makes a live
behavior claim, check it against the actual live site** (`curl`, the browser tools,
or at minimum the exact source file that's actually deployed) — not against what a
handover doc, a code comment, or a previous version of this file says should be true.

## 15. Repo hygiene — checking upstream, not assuming "merged" or "done"

General git/process discipline, not specific to any one page — applies to anyone
touching this repo, human or agent:

- **Always check the actual upstream state right before pushing or opening a PR**
  (`git fetch upstream` + `git log upstream/aws-mysql`), not earlier in the session —
  state changes. Stack new work onto an unmerged branch that already covers the same
  area instead of fragmenting into a parallel PR.
- **Being told "X is merged" is not the same as verifying it.** A PR can merge from
  an earlier commit than the last one actually pushed, if the merge button was
  clicked before the final push landed — this happened for real and was only caught
  by diffing upstream's actual file content, not by trusting the merge status shown
  in a UI or stated in chat. Verify directly against upstream before reporting
  anything as done, the same way §14 says not to trust a bare "done."
- **Split PRs by what kind of change it is (fix / new feature / infra), not by when
  it happened to be built.** Things built in the same sitting can still belong in
  separate PRs if they're different *kinds* of change — makes each PR reviewable and
  revertible on its own.
- **Checkpoint long-running or multi-step work to disk as it goes** (a progress file,
  a decision log, intermediate output) rather than only at the end. A session or
  process that gets killed mid-task can resume cleanly from a checkpoint with no lost
  work; without one, an interruption loses everything done so far.
- **If told to ship something exactly as-is, ship exactly that** — including a
  disclosed known gap or limitation. Don't silently "improve," pad, or rebuild it
  further on top of what was actually asked for; an unrequested improvement is still
  a scope change. This generalizes beyond "as-is" instructions: don't silently
  narrow, widen, or "improve" the scope of *any* task from what was actually asked —
  flag the idea instead of just doing it.
- **Deploying to production and deleting a git branch both require the repo owner's
  explicit go-ahead, every time** — one bad `eb deploy` or one deleted branch can't
  be quietly undone the way a bad commit can. Never treat an earlier approval as
  covering a later, similar action.
- **Docs for a change go in `docs/`** (tracked, ships with the repo) — not scattered
  loose in the repo root or left undocumented. The Celebrity Kundli workstream has
  its own narrative-handover folder, `Celebrity-Personalities-Kundli-SEO/session-handovers/`,
  for session-by-session notes specific to that pipeline.

## 16. End of every major task — post a rule-by-rule checklist, not a prose summary

A "major task" = anything that adds/edits a page, a product, a route, SEO metadata,
Hindi content, or a report/PDF. (A one-line copy fix or a pure bug fix doesn't need
this — match the ceremony to the size of the change.)

Before saying a major task is done, go through the rules in this file **that
actually apply to what was touched** and report each as a line, not a paragraph —
checked (with how it was checked), not applicable, or skipped (with why). This is
the point: the developer should never have to re-ask "did you also do the sitemap /
the Hindi twin / the buttons" — the checklist answers it up front, every time,
without being asked. Example shape:

```
§1 funnel/validation  — unchanged, not touched
§2 head block/links    — added canonical+hreflang+OG, verified by curl; no dead links
§3 sitemap+robot        — added /en/<slug> to both; confirmed in /sitemap.xml output
§4 homepage             — asked; dev said yes, added card + reviews to home.html
§5 reviews               — wrote 6 on-page reviews in the product's own voice
§7 Hindi twin            — built side-by-side, reused shaadi_hi_data.py phrases,
                          checked the JS popup, no matra clipping on the hero
§8 PDF theme             — reused _VYAPAR_CSS/_VYAPAR_DEFS verbatim; added @media
                          print hides for the new sticky bar
§9 report buttons        — n/a, this task didn't touch a report page
§10 gates                — pytest 521/521, E2E not re-run (no funnel logic touched)
```

Each "checked" line should reflect something actually verified this session (a
command run, a file grepped, a test passed) — not an assumption. This is what §14
("never trust a bare 'done'") looks like when *I'm* the one reporting, not just a
rule for auditing someone else's agent.

## 17. Secrets

Never write a real key/token/secret value into a file, commit, or chat. Reference the
env var name only — secrets are generated and set (`eb setenv`) by the repo owner.
