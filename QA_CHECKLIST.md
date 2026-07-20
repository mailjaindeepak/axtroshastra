# QA Checklist — pre-release manual pass

Run this on a **real phone** (and once on desktop) against **staging** before any
change is promoted to production. Automated checks (`pytest` + Playwright) run in
CI on every push and cover most of this — this list is the human "walk the actual
experience" pass that catches the things automation misses (feel, wording, real
device rendering, payment).

**Environment:** ____________  (staging URL)   **Build/commit:** ____________
**Tester:** ____________   **Date:** ____________   **Devices:** phone ______ / desktop ______

How to use: tick each box. If anything fails, note it under *Issues* at the bottom
and do **not** promote until fixed or explicitly waived.

---

## 1. Page load & layout (phone + desktop)
- [ ] `/shaadi` loads with no console errors, no horizontal scroll/overflow.
- [ ] Loads in **English by default**; no flash of Hinglish before it settles.
- [ ] Hero, form card, sticky CTA and footer all render correctly.

## 2. Date of birth
- [ ] Row reads **DD · Month · YYYY**; Month is the widest and shows its "Month" label.
- [ ] Day and Year accept typing and pop a numeric keypad on mobile.
- [ ] Month dropdown lists Jan–Dec and is easy to open/tap.
- [ ] Invalid dates are rejected: 31 Feb, day 32, year 1850 / 2050, a 3-digit year.
- [ ] A single-digit day ("5") is accepted and normalised.

## 3. Time of birth
- [ ] Hour (1–12), Minute (**5-min steps**), AM/PM all open and select cleanly.
- [ ] The "Hour" / "Min" / "AM/PM" prompts are **not** selectable rows.
- [ ] "Don't know exact birth time" toggles to the approximate-time selector and back.

## 4. Place of birth (city)
- [ ] Suggestions appear **directly under the input**, above the helper line.
- [ ] "Delhi" → Delhi / New Delhi only (no "Delhi Cantonment" / localities).
- [ ] "Jai", "Mumbai", a small district town — all return sensible results.
- [ ] Keyboard ↑/↓/Enter and tap both select a city; the field fills with the picked name.
- [ ] Typing a name that isn't picked from the list is blocked on submit with a clear hint.

## 5. Language toggle
- [ ] Toggle English ⇄ Hinglish: headline, labels, placeholders, dropdown prompts, and helper text all switch.
- [ ] Choice persists on reload.

## 6. Submit → teaser → report
- [ ] Valid submission shows the loading messages, then the **free snapshot/teaser** (moon sign, nakshatra, current period).
- [ ] No console/network errors on submit.
- [ ] Report content is coherent (windows, grades, no obviously broken/empty sections).
- [ ] PDF download and WhatsApp share work.
- [ ] Payment: real Razorpay checkout opens (on staging use a test method / demo unlock) and delivers the report.

## 7. Cross-device / regression
- [ ] Repeat §1–4 on a second device or browser (one iOS, one Android if possible).
- [ ] Open the link from inside the **Instagram / WhatsApp in-app browser** — form usable, no crash on the time/date fields.
- [ ] Other funnels still load and submit: `/milan`, `/jeevan`, `/match`.

## 8. Sign-off
- [ ] All above pass (or failures explicitly waived below).
- [ ] Approved to promote to production by: ____________

---

## Issues found this pass
| # | Area | Device | What happened | Severity | Fixed? |
|---|------|--------|---------------|----------|--------|
|   |      |        |               |          |        |

---

### Adding test cases
- **Automate what you can:** anything with a deterministic pass/fail belongs in
  `tests/e2e/*.spec.js` (UI) or `tests/test_*.py` (logic) so CI enforces it forever.
- **Keep here** the exploratory / judgement / real-payment / real-device cases.
- When adding a case, note which funnel(s) it applies to (`/shaadi`, `/milan`,
  `/jeevan`, `/match`) — several forms share the same widgets.
