// The compatibility launch-offer countdown is a GENUINE, server-clock-driven
// flash sale: ₹499 while the offer is ON, ₹999 while it is OFF, on a repeating
// cycle (see api.milan_offer_status). This guards the two things that keep it
// from looking (or being) fake:
//   1. what the page SHOWS matches /api/offer_status — the same source that sets
//      the amount actually charged — in BOTH phases, and
//   2. it is driven by the server clock, so it never resets to a fresh 30:00.
//
// ?offer=on|off is a DEMO_MODE-only hook that pins the phase for deterministic
// tests; in production the phase is purely the wall clock.
const { test, expect } = require('@playwright/test');

test('ON window shows the ₹499 launch offer and charges ₹499', async ({ page }) => {
  await page.goto('/en/compatibility?offer=on');
  const l2 = page.locator('.sticky .l2');
  await expect(l2).toContainText('₹499');
  await expect(l2).toContainText('left');
  await expect(page.locator('#offerTimer')).toContainText('Launch offer ends in');
  await expect(page.locator('#unlockBtn')).toContainText('₹499');

  const s = await page.evaluate(() => fetch('/api/offer_status?force=on').then(r => r.json()));
  expect(s.phase).toBe('on');
  expect(s.price_paise).toBe(49900); // what the page shows == what the server charges
});

test('OFF window honestly shows ₹999 now (₹499 returns) and charges ₹999', async ({ page }) => {
  await page.goto('/en/compatibility?offer=off');
  const l2 = page.locator('.sticky .l2');
  await expect(l2).toContainText('₹999');
  await expect(l2).toContainText('returns in');
  await expect(page.locator('#offerTimer')).toContainText('returns in');
  await expect(page.locator('#unlockBtn')).toContainText('₹999'); // charge matches display

  const s = await page.evaluate(() => fetch('/api/offer_status?force=off').then(r => r.json()));
  expect(s.phase).toBe('off');
  expect(s.price_paise).toBe(99900);
});

test('countdown comes from the server clock and never resets to 30:00', async ({ page }) => {
  await page.goto('/en/compatibility?offer=on');
  const clk = page.locator('.sticky .l2 .clk').first();
  // Real mm:ss derived from server seconds_left (ON window is 45:00), NOT the
  // static 30:00 placeholder ticking from full.
  await expect(clk).toHaveText(/^\d{2}:\d{2}$/);
  await expect(clk).not.toHaveText('30:00');

  const before = (await clk.textContent()).trim();
  await page.reload();
  const clk2 = page.locator('.sticky .l2 .clk').first();
  await expect(clk2).toHaveText(/^\d{2}:\d{2}$/);
  await expect(clk2).not.toHaveText('30:00'); // did not reset on refresh
  // continued forward in time (allow a couple seconds of slack for the reload)
  const after = (await clk2.textContent()).trim();
  const ms = (c) => { const [m, s] = c.split(':').map(Number); return m * 60 + s; };
  expect(ms(after)).toBeLessThanOrEqual(ms(before) + 3);
});
