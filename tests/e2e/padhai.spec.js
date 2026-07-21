// End-to-end / UI tests for the /padhai (Career & Academic Timing) funnel form.
// The form is copied 1:1 from /shaadi (same field ids), so these mirror
// shaadi.spec.js's structure — this file adds the product-specific assertions
// (product: "vidyarthi" in the request, career-specific teaser copy) rather
// than re-testing generic form mechanics already covered there.
const { test, expect } = require('@playwright/test');

test.beforeEach(async ({ page }) => {
  await page.goto('/padhai');
});

test('Hero and pricing show the career product, not marriage', async ({ page }) => {
  await expect(page.locator('h1')).toContainText(/career/i);
  await expect(page.locator('.paywall h3')).toContainText(/Career.*Academic/i);
});

test('Date validation blocks an impossible date (31 Feb)', async ({ page }) => {
  await page.fill('#f-name', 'QA');
  await page.fill('#f-dd', '31');
  await page.selectOption('#f-mm', '02');
  await page.fill('#f-yy', '2000');
  await page.locator('#kundliForm button[type="submit"]').click();
  await expect(page.locator('#teaser')).toBeHidden();
});

test('Happy path: a valid submission renders the free teaser with vidyarthi product', async ({ page }) => {
  let kundliBody = null;
  await page.route('**/api/kundli', async (route) => {
    kundliBody = route.request().postDataJSON();
    await route.continue();
  });

  await page.fill('#f-name', 'QA Student');
  await page.fill('#f-dd', '15');
  await page.selectOption('#f-mm', '08');
  await page.fill('#f-yy', '2008');
  await page.selectOption('#f-hh', '10');
  await page.selectOption('#f-mm2', '30');
  await page.selectOption('#f-ap', 'AM');
  const place = page.locator('#f-place');
  await place.fill('Delhi');
  const item = page.locator('#f-place-list .ci', { hasText: 'Delhi' }).first();
  await item.waitFor();
  await item.click();
  await page.locator('#kundliForm button[type="submit"]').click();

  await expect(page.locator('#teaser')).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('#wfLine')).toContainText(/career breakthrough window/i);
  await expect(page.locator('#tlTitle')).toContainText(/career timeline/i);

  // The trust-boundary product routing: the request must say "vidyarthi",
  // not the default "marriage" — this is what makes api.py render the
  // right engine and the right report template.
  await expect.poll(() => kundliBody && kundliBody.product).toBe('vidyarthi');
});
