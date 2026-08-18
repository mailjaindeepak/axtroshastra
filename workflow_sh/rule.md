# rule.md — Working rules, gates, agent workflow & report architecture

Single reference for how we work on AxtroShastra. Consolidates the memory rules,
the gates built so far, the agent workflow, and the shared backend pipeline every
product must follow. Read this before starting any report/page work.

---

## 1. Collaboration hierarchy
- **Commander** (the user) directs. **Sergeant** (Claude, main session) orchestrates, gates, reports. **Agents** (subagents) build.
- **Sergeant's core duty is the GATE**: independently cross-check every agent's output against the working reference (the compatibility / milan pipeline) *before* reporting up. Catch gaps at the gate, never after they reach the Commander.
- Always report transparently: which agent is doing what, its status, and findings.

## 2. Process rules (hard)
- **Preview before commit/push.** Show the change on localhost and get explicit OK first. *(preview-prod-change-first)*
- **Never push, force-push, or open a PR without an explicit "push"/"go" from the Commander.** Pushing is outward-facing.
- **Check upstream at the moment of hand-off** (`git fetch upstream aws-mysql`) — not earlier; state changes. Stack onto unmerged branches; don't fragment into new PRs. *(check-upstream-before-pr, pr-workflow-check-upstream)*
- **Plain language**: explain in plain English, define every jargon term, state cost plainly. *(plain-language-explanations)*
- **Never handle prod secrets** (API keys, tokens). The Commander generates + `eb setenv` himself. *(secrets-never-exposed-to-assistant)*
- Hand off PRs as **pre-filled compare URLs** to upstream `aws-mysql`. *(pr-links-prefilled)*
- Each mock/artifact change = a NEW artifact URL; never overwrite prior versions. *(artifact-versioning)*

## 3. Backend CONSISTENCY rule  ← the important one
- Every product (marriage, compatibility/milan, career/vidyarthi, blueprint, career_growth, vyapar) **must follow the same report pipeline** (section 5). A new product **conforms to the pattern** — it is never a bolt-on plug-in loosely wired to the rest.
- A fix or change to the shared pattern is applied to **all** pages, so the site stays one coherent system, not a puzzle of pieces holding onto each other.
- **Do NOT copy a bug or legacy quirk** from one page into another (e.g. milan's v1/v2 legacy toggle handling). Conform to the clean pattern and **flag** the quirk instead of replicating it. If a reference page has a gap that would break ours, we do NOT implement it.
- **Fine-tune, don't mimic**: adapt the shared contract to the page's own content (vyapar has its own slots/tables), but keep the pipeline/contract identical.
- **Before diverging from the shared pattern, ask the Commander.**

## 4. Consistency-fix scope
- Making a product conform may touch **shared** files (e.g. `narrative.py`, `report_view*.py`, `tests/test_hindi_leakage.py`). That is expected.
- Do **not** change another page's *behavior* while doing so. If a genuine shared-backend bug/gap affecting all pages is found: **flag it** to the Commander (default) — fix-across-all-pages only on the Commander's say-so.

## 5. The shared report pipeline (every product follows this)
1. **`compute_<product>(inputs)`** [products.py / engine] — deterministic astrology only (Swiss Ephemeris, Lahiri). Returns the facts + `teaser` (**with authored `_hi` Devanagari twin fields** for the `/hi` funnel) + `meta.lang`. No LLM here.
2. **`narrative.py`** — the LLM writes only the **prose layer** in `meta.lang` (Devanagari for `hi`), validated; it **never computes or changes a fact**. `SECTION_SPECS[<product>]` lists the prose slots. `_resolve_lang(payload)` decides the output language from `meta.lang`.
3. **`render_<product>(payload)`** [report_view*.py] — builds the HTML. Each slot is `prose(key, bank) = narr(key) or bank`. **When `meta.lang=='hi'`, every deterministic `bank` fallback is composed in Devanagari** (the `hi` flag + bank-twin pattern; `report_view_v2.render_report_v2` is the reference at lines ~452, 564-568). LLM slots override the bank in either language.
4. **`<product>_hi.py` localizer (+ `<product>_hi_data.py`)** — translates the FIXED shell (headings, labels) to Devanagari *after* render. Reuse the shared `jyotish_maps` `*_HI` glossary and existing `*_hi_data` phrasings; never re-derive.
5. **`api._render_for`** — dispatches to the renderer and wires the `_hi` localizer when `meta.lang=='hi'`.
6. **Serve chrome** (`_wire_report_chrome`) — nav, one-tap PDF + WhatsApp-share buttons, toasts injected AFTER localization, in-language.
7. **Routing + toggle**: explicit `/en/<slug>` + `/hi/<slug>` routes + legacy `/<slug>` 301→`/en/<slug>`; inline `#axlang` two-link toggle (EN / हिंदी) on each page; the `.hi` page renders the teaser via `hv(_hi, en)` (Devanagari-first, English fallback).

## 6. Gates (all green before hand-off)
- **pytest** — full unit/integration suite.
- **Playwright E2E** (`tests/e2e`) — funnel flows.
- **ops robot smoke** (`ops/robot_customer`) — live page/funnel/SEO health on mobile+desktop. A `PENDING_DEPLOY` allow-list skips a route that's merged-but-not-yet-deployed (404) and auto-tests it once live (self-heals).
- **Button deploy-gate** (`tests/test_report_buttons.py`) — every product's paid report page must ship the wired Download-PDF (`axPdfDl`) + WhatsApp-share (`axShare`) bar. Mutation-checked.
- **Hindi-leakage gate** (`tests/test_hindi_leakage.py`) — renders each Hindi report **with the LLM off (worst case) and on**, and FAILS on any run of ≥4 consecutive English words (brand/data words allowlisted). **This is how "pure Hindi" is guaranteed — not by promise.** Every Hindi product must be covered here.
- **Pre-push CI simulation** — verify imports vs `requirements.build.txt`, run pytest, boot the server, run E2E — never push without simulating CI locally. *(pre-push-ci-simulation, env-getenv-or-pattern)*

## 7. Agent workflow
- Delegate buildable/parallel work to background agents; **partition by file** (each agent owns specific files). Sergeant keeps git + glue + the gate. *(delegate-to-agents)*
- Agents: never run git; never use the Sergeant's running server port; verify in-process or on a unique port; report findings + anything uncertain.
- Sergeant re-verifies agent output independently (structure parity, leak scans, `node --check` / `python` import) before integrating — and previews to the Commander before any commit.

## 8. Language / register
- Registers: English / Hindi-Devanagari / (historically Hinglish) — one register per file, fixed route+file naming. *(language-registers-and-routing, build-for-both-languages)*
- Hindi = clean, simple, everyday Devanagari; **zero** Roman-script Hindi and zero stray English in visible text (brand tokens like AxtroShastra/WhatsApp/PDF allowlisted). Reuse `milan_hi_data`, `shaadi_hi_data`, `jyotish_maps *_HI`.

## 9. Repo / deploy topology
- `origin` = fork **shreyansh0714/axtroshastra**; `upstream` = the Commander's repo; deploy branch **aws-mysql**; **no `gh` CLI** (hand off compare URLs). *(repo-pr-topology)*
- Razorpay `pay_*` ids are the sole truth for real customers; free_pass/demo = testers. *(razorpay-sole-truth-customer)*
- Report delivery / WhatsApp goes to the **popup number only**, never Razorpay's. *(deliver-report-to-popup-number-only)*
- Desktop repo is TCC-blocked for the assistant; work happens in a session clone of `aws-mysql` (ephemeral — must be pushed to persist).

## 10. Open product considerations (not bugs — parked)
- **Family-business / single-chart limit**: the report reads one person's natal chart ("you, in business"), not a business founding-chart (muhurta) or multiple stakeholders. Father vs son giving different windows = different *stewardship*, not a contradiction. Options if pursued: (1) a framing line that it reads the business through the active head's (karta's) chart; (2) a family/succession multi-chart reading; (3) a business founding-chart (muhurta). Requires Commander direction.
