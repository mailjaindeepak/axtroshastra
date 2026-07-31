// Regression: the `form_start` funnel event must fire ONCE per genuine fill,
// and must NOT re-fire when the user toggles language after starting the form.
//
// Bug (compatibility page, long form): on a language toggle the page really
// navigates and restores the retained form state. `_formStarted` reset to false
// on the fresh page, and a focus event generated during state restoration
// re-fired `form_start` to GA4 + Pixel. Fix: persist the "already started" flag
// in the retained state so restore() marks the form started before any restore
// focus event can fire.
const { test, expect } = require('@playwright/test');

test('form_start is NOT re-fired when toggling language after starting the compatibility form', async ({ page }) => {
  await page.goto('/en/compatibility');

  // A genuine start: focus a field, type something.
  await page.locator('#p1-name').focus();
  await page.fill('#p1-name', 'Asha');
  expect(await page.evaluate(() => window._formStarted)).toBe(true);

  // Toggle to Hindi via the real capsule link (it flags the switch, then navigates).
  await page.click('#axlang a[href="/hi/compatibility"]');
  await page.waitForURL('**/hi/compatibility');

  const res = await page.evaluate(() => {
    let n = 0;
    const g = window.gtag;
    window.gtag = function () { if (arguments[1] === 'form_start') n++; if (g) return g.apply(this, arguments); };
    const startedAfterRestore = window._formStarted;              // restored -> true
    const nameRestored = (document.getElementById('p1-name') || {}).value;
    // Simulate the focus event that restoration (city apply / field repopulation) can generate.
    const el = document.getElementById('p1-name');
    if (el) el.dispatchEvent(new Event('focusin', { bubbles: true }));
    return { startedAfterRestore, refires: n, nameRestored };
  });

  expect(res.startedAfterRestore).toBe(true);   // restore() carried the "already started" flag
  expect(res.nameRestored).toBe('Asha');        // form data survived the toggle
  expect(res.refires).toBe(0);                  // THE FIX: form_start does not fire again
});

test('form_start STILL fires on a genuine first fill (no toggle)', async ({ page }) => {
  await page.goto('/en/compatibility');
  const res = await page.evaluate(() => {
    let n = 0;
    const g = window.gtag;
    window.gtag = function () { if (arguments[1] === 'form_start') n++; if (g) return g.apply(this, arguments); };
    const before = window._formStarted;
    document.getElementById('p1-name').dispatchEvent(new Event('focusin', { bubbles: true }));
    return { before, after: window._formStarted, fires: n };
  });
  expect(res.before).toBe(false);   // fresh page, not started
  expect(res.after).toBe(true);
  expect(res.fires).toBe(1);        // genuine start still tracked exactly once
});
