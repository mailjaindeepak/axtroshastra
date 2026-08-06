// Robot customer — end-to-end journey against a LIVE deployment.
//
// For each funnel (compatibility /en/compatibility, marriage /en/marriage) it
// behaves like a real buyer and asserts every step of the paid journey:
//
//   1. Get a free unlock token   GET  /api/make_pass?key=STATS_KEY&n=1
//   2. Fill + submit the birth form in a real browser; confirm the free teaser
//   3. Redeem the pass WITHOUT paying:  POST /api/order
//        {report_id, pass_token, phone, email}   (the site's free-pass branch)
//   4. Load /report/<rid>; assert the PAID report renders (not the pending 404)
//   5. Assert /report/<rid>.pdf is 200 with a PDF content-type
//
// Selectors/flow mirror tests/e2e/shaadi.spec.js + checkout.spec.js. Marriage
// uses the single-person #kundliForm (#f-* ids); compatibility uses the two-
// person #milanForm (p1-*/p2-* ids, gender inferred by role — no gender field).
//
// Any failed assertion fails the test, which makes `npx playwright test` exit
// non-zero — the loud signal CI / the mechanic reacts to.

const { test, expect } = require('@playwright/test');

// ---- Env / preconditions -------------------------------------------------
const TARGET = process.env.OPS_TARGET_URL;
const STATS_KEY = process.env.STATS_KEY;

test.beforeAll(() => {
  if (!TARGET) throw new Error('OPS_TARGET_URL is not set — point the robot at a deployment.');
  if (!STATS_KEY) throw new Error('STATS_KEY is not set — needed to mint a free unlock pass.');
});

// A valid 10-digit Indian mobile, unique per run so we never collide with a
// prior robot account in the shared prod DB (mobile is the account key).
function testPhone() {
  return '9' + String(Date.now()).slice(-9);
}
function testEmail() {
  return `robot-${Date.now()}@axtroshastra.test`;
}

// Full valid birth time using option values the pages actually build:
//   hour  -> "1".."12"      minute -> "00","05",... ,"55"      ap -> "AM"/"PM"
const TIME = { hh: '10', mm: '30', ap: 'AM' };

// Pick a city from the autosuggest exactly like the e2e specs: type it, wait for
// the matching `.ci` row under <prefix>-place-list, then click it (a plain fill
// leaves the report un-geocoded and /api/kundli 422s with "city_not_selected").
async function pickCity(page, prefix, city) {
  const input = page.locator(`#${prefix}-place`);
  await input.scrollIntoViewIfNeeded();
  await input.fill(city);
  const item = page.locator(`#${prefix}-place-list .ci`, { hasText: city }).first();
  await item.waitFor();
  await item.click();
}

// ---- Form fillers (copied from the e2e specs) ----------------------------

// Marriage / shaadi: single person on #kundliForm.
async function fillMarriage(page) {
  await page.fill('#f-name', 'Robot Customer');
  await page.selectOption('#f-gender', 'male');
  await page.fill('#f-dd', '15');
  await page.selectOption('#f-mm', '06');
  await page.fill('#f-yy', '1992');
  await page.selectOption('#f-hh', TIME.hh);
  await page.selectOption('#f-mm2', TIME.mm);
  await page.selectOption('#f-ap', TIME.ap);
  await pickCity(page, 'f', 'Jaipur');
  await page.locator('#kundliForm button[type="submit"]').click();
}

// Compatibility / milan: two people (p1 = GIRL, p2 = BOY) on #milanForm.
async function fillCompatibility(page) {
  for (const p of ['p1', 'p2']) {
    await page.fill(`#${p}-name`, p === 'p1' ? 'Robot Aisha' : 'Robot Arjun');
    await page.fill(`#${p}-dd`, '15');
    await page.selectOption(`#${p}-mm`, '06');
    await page.fill(`#${p}-yy`, p === 'p1' ? '1994' : '1992');
    await page.selectOption(`#${p}-hh`, TIME.hh);
    await page.selectOption(`#${p}-mm2`, TIME.mm);
    await page.selectOption(`#${p}-ap`, TIME.ap);
    await pickCity(page, p, 'Jaipur');
  }
  await page.locator('#milanForm button[type="submit"]').click();
}

// ---- The journey, parametrised per funnel --------------------------------
const JOURNEYS = [
  { name: 'compatibility', path: '/en/compatibility', fill: fillCompatibility },
  { name: 'marriage',      path: '/en/marriage',      fill: fillMarriage },
];

for (const journey of JOURNEYS) {
  test(`${journey.name}: free-pass unlock journey renders a paid report + PDF`, async ({ page, request }) => {
    // 1) Mint a one-time free unlock token via the admin route.
    const passResp = await request.get(`/api/make_pass?key=${encodeURIComponent(STATS_KEY)}&n=1`);
    expect(passResp.ok(), `make_pass HTTP ${passResp.status()}`).toBeTruthy();
    const passBody = await passResp.json();
    expect(Array.isArray(passBody.passes)).toBeTruthy();
    const token = passBody.passes && passBody.passes[0];
    expect(token, 'make_pass returned no token').toBeTruthy();

    // 2) Real browser: open the funnel, fill the birth form, submit, see teaser.
    await page.goto(journey.path);
    await journey.fill(page);
    await expect(page.locator('#teaser'), 'free teaser never appeared after submit')
      .toBeVisible({ timeout: 30_000 });

    // The page stashes the persisted report id on window after /api/kundli.
    const rid = await page.evaluate(() => window.REPORT_ID);
    expect(rid, 'window.REPORT_ID was not set — /api/kundli did not persist').toBeTruthy();

    // 3) Redeem the pass WITHOUT paying — the exact call the site makes for a
    //    free pass (api.py /api/order pass_token branch). Success is either a
    //    fresh free unlock ({free:true}) or an already-paid report.
    const orderResp = await request.post('/api/order', {
      data: {
        report_id: rid,
        pass_token: token,
        phone: testPhone(),
        email: testEmail(),
      },
    });
    expect(orderResp.ok(), `/api/order HTTP ${orderResp.status()}`).toBeTruthy();
    const order = await orderResp.json();
    expect(order.error, `/api/order rejected the pass: ${order.error}`).toBeFalsy();
    expect(
      order.free === true || order.already_paid === true,
      `pass was not redeemed (order response: ${JSON.stringify(order)})`,
    ).toBeTruthy();

    // 4) Load the report page: it must be the real PAID report, not the
    //    "payment pending" 404 stub. A non-durable write shows up loudly here.
    const reportResp = await page.goto(`/report/${rid}`);
    expect(reportResp.status(), `report page HTTP ${reportResp.status()} (payment pending?)`)
      .toBeLessThan(400);
    await expect(page.locator('body')).not.toContainText(/Report not found|payment pending/i);
    // Sanity: the paid page carries real report chrome (download / PDF affordance).
    await expect(page.locator('body')).not.toBeEmpty();

    // 5) The PDF must be fetchable: 200 + a PDF content-type.
    const pdfResp = await request.get(`/report/${rid}.pdf`);
    expect(pdfResp.status(), `PDF HTTP ${pdfResp.status()}`).toBe(200);
    expect(
      (pdfResp.headers()['content-type'] || '').toLowerCase(),
      'PDF response was not application/pdf',
    ).toContain('pdf');
  });
}
