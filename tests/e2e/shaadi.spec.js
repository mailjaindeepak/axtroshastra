// End-to-end / UI tests for the /shaadi (Marriage Timing) funnel form.
// These assert the things that are easy to break in the browser and invisible
// to the Python tests: layout, form controls, city autosuggest, language, and
// the happy-path submit. Runs on both mobile and desktop viewports.
const { test, expect } = require('@playwright/test');

test.beforeEach(async ({ page }) => {
  await page.goto('/en/marriage');
});

test('DOB row: Month is the widest field and keeps its label; no horizontal overflow', async ({ page }) => {
  const dd = page.locator('#f-dd');
  const mm = page.locator('#f-mm');
  const yy = page.locator('#f-yy');
  const [ddBox, mmBox, yyBox] = [await dd.boundingBox(), await mm.boundingBox(), await yy.boundingBox()];
  // Month (dropdown, holds words) must be wider than Day and Year (2 / 4 digits).
  expect(mmBox.width).toBeGreaterThan(ddBox.width);
  expect(mmBox.width).toBeGreaterThan(yyBox.width);
  // Month prompt is visible (regression: it was squeezed to a chevron sliver).
  const label = await mm.evaluate((el) => el.options[el.selectedIndex].textContent.trim());
  expect(label).toBe('Month');
  // Nothing overflows the viewport horizontally.
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 2);
  expect(overflow).toBe(false);
});

test('DOB uses typed DD / YYYY inputs (no long day/year scroll)', async ({ page }) => {
  await expect(page.locator('#f-dd')).toHaveAttribute('placeholder', 'DD');
  await expect(page.locator('#f-yy')).toHaveAttribute('placeholder', 'YYYY');
});

test('Date validation blocks an impossible date (31 Feb)', async ({ page }) => {
  await page.fill('#f-name', 'QA');
  await page.selectOption('#f-gender', 'male');
  await page.fill('#f-dd', '31');
  await page.selectOption('#f-mm', '02');
  await page.fill('#f-yy', '2000');
  await page.locator('#kundliForm button[type="submit"]').click();
  // The teaser must NOT render for an invalid date.
  await expect(page.locator('#teaser')).toBeHidden();
});

test('Time: minute is in 5-minute steps and prompts are not selectable', async ({ page }) => {
  const mins = await page.locator('#f-mm2 option').evaluateAll((os) => os.map((o) => o.value).filter(Boolean));
  expect(mins).toEqual(['00', '05', '10', '15', '20', '25', '30', '35', '40', '45', '50', '55']);
  const apPromptDisabled = await page.locator('#f-ap option').first().evaluate((o) => o.disabled);
  expect(apPromptDisabled).toBe(true);
});

test('City autosuggest: opens directly under the input, above the helper, no localities', async ({ page }) => {
  const place = page.locator('#f-place');
  await place.scrollIntoViewIfNeeded();
  await place.fill('Delhi');
  const list = page.locator('#f-place-list');
  await expect(list).toBeVisible();
  await expect(list).toContainText('Delhi');
  await expect(list).not.toContainText(/Cantonment/i); // sub-locality must be filtered out
  const inpBox = await place.boundingBox();
  const listBox = await list.boundingBox();
  // Dropdown top should sit at the input's bottom (anchored to the input, not the whole field).
  expect(Math.abs(listBox.y - (inpBox.y + inpBox.height))).toBeLessThan(6);
});

test('Language: /en/marriage by default; toggle links to the Hindi page and back', async ({ page }) => {
  // English landing by default, with EN marked active in the URL toggle.
  await expect(page.locator('h1')).toContainText(/married/i);
  await expect(page.locator('#axlang a.on')).toHaveText('EN');
  // The हिंदी control is a link to the Devanagari page (not a client-side text swap).
  const hiLink = page.locator('#axlang a', { hasText: 'हिंदी' });
  await expect(hiLink).toHaveAttribute('href', '/hi/marriage');
  await hiLink.click();
  await page.waitForURL(/\/hi\/marriage$/);
  await expect(page.locator('h1')).toContainText(/शादी|होगी/);
  await expect(page.locator('#axlang a.on')).toHaveText('हिंदी');
  // And EN links back to the English page.
  const enLink = page.locator('#axlang a', { hasText: 'EN' });
  await expect(enLink).toHaveAttribute('href', '/en/marriage');
  await enLink.click();
  await page.waitForURL(/\/en\/marriage$/);
  await expect(page.locator('h1')).toContainText(/married/i);
});

test('/shaadi redirects (301) to /en/marriage', async ({ page }) => {
  const resp = await page.goto('/shaadi');
  expect(new URL(page.url()).pathname).toBe('/en/marriage');
  expect(resp.status()).toBeLessThan(400);
});

test('Happy path: a valid submission renders the free teaser snapshot', async ({ page }) => {
  await page.fill('#f-name', 'QA Tester');
  await page.selectOption('#f-gender', 'male');
  await page.fill('#f-dd', '15');
  await page.selectOption('#f-mm', '06');
  await page.fill('#f-yy', '1992');
  await page.selectOption('#f-hh', '10');
  await page.selectOption('#f-mm2', '30');
  await page.selectOption('#f-ap', 'AM');
  const place = page.locator('#f-place');
  await place.fill('Jaipur');
  const item = page.locator('#f-place-list .ci', { hasText: 'Jaipur' }).first();
  await item.waitFor();
  await item.click();
  await page.locator('#kundliForm button[type="submit"]').click();
  await expect(page.locator('#teaser')).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('#teaser')).toContainText(/kundli ready|ready/i);
});
