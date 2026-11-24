// The compatibility launch-offer countdown is a simple 30-minute timer whose
// end-time is kept in sessionStorage, so a page REFRESH must not restart it.
// (A fresh visit / new tab intentionally starts a new 30:00 — that's fine at our
// current low traffic.) The timer script updates #otClockSticky even before the
// sticky bar is scrolled into view, so we read its text directly.
//
// Uses ./fixtures (aborts external Google Fonts) so page.goto's 'load' wait can't
// hang on those hosts — that was the intermittent 30s-timeout flake on CI.
const { test, expect } = require('./fixtures');

const secs = (c) => { const [m, s] = c.split(':').map(Number); return m * 60 + s; };

test('offer timer does not reset to 30:00 on refresh', async ({ page }) => {
  await page.goto('/en/compatibility');
  const clk = page.locator('#otClockSticky');
  await page.waitForTimeout(1500); // let it tick below 30:00
  const before = (await clk.textContent()).trim();
  expect(before).toMatch(/^\d{2}:\d{2}$/);
  expect(before).not.toBe('30:00');

  const end1 = await page.evaluate(() => sessionStorage.getItem('axs_milan_offer_end'));
  expect(end1).toBeTruthy();

  await page.reload();
  await page.waitForTimeout(300);
  const after = (await page.locator('#otClockSticky').textContent()).trim();
  const end2 = await page.evaluate(() => sessionStorage.getItem('axs_milan_offer_end'));

  expect(end2).toBe(end1);         // same end-time kept across the refresh
  expect(after).not.toBe('30:00'); // did NOT restart
  expect(secs(after)).toBeLessThanOrEqual(secs(before) + 1); // moved forward in time
});

test('compat keeps the ₹999 -> ₹249 cut on the sticky bar', async ({ page }) => {
  await page.goto('/en/compatibility');
  const l2 = page.locator('.sticky .l2');
  await expect(l2).toContainText('₹999');
  await expect(l2).toContainText('₹249');
});

// Annual Report: before the preview the sticky bar has no price and no countdown (the struck price appears on its button only after the preview; see annual.spec.js).
test('annual sticky bar before the preview shows no price and no countdown, on desktop too with a form field focused', async ({ page }) => {
  await page.goto('/en/annual-report');
  await page.locator('#f-name').focus();
  await page.evaluate(() => window.scrollTo(0, document.getElementById('kundliForm').offsetTop + 400));
  const bar = page.locator('#stickyBar');
  if (!(await page.evaluate(() => matchMedia('(hover:none)').matches))) await expect(bar).toBeVisible();
  await expect(bar).not.toContainText('₹');
  await expect(page.locator('#otClockSticky, #otClock, #offerTimer')).toHaveCount(0);
});
