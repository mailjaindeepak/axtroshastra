// Robot customer — an A–Z live health check against a LIVE deployment.
//
// This behaves like a real buyer against every funnel, in both languages, on
// both a desktop and a mobile viewport (Playwright "projects", see
// playwright.config.js). It never pays: it unlocks with a FREE pass
// (GET /api/make_pass -> POST /api/order {report_id, pass_token, phone, email},
// the site's free-pass branch in api.py) so it stays $0 while exercising the
// whole paid path.
//
// What it asserts, per the ops framework:
//   1. FUNNELS load       — every product in BOTH languages returns 200, the
//                           birth form fills, and the free teaser/preview renders.
//   2. FREE-PASS UNLOCK    — make_pass -> order(pass_token) -> /report/{id}
//                           renders the PAID report -> /report/{id}.pdf is 200,
//                           application/pdf and non-empty (compat + marriage +
//                           career, English).
//   3. CTAs               — the primary CTA(s) exist, are visible + enabled, and
//                           target the right action (form submit; #unlockBtn ->
//                           startPayment()).
//   4. PREVIEWS           — the teaser snapshot renders after submit.
//   5. RESPONSIVE         — on the mobile project, funnel pages have no
//                           horizontal overflow (scrollWidth <= innerWidth+tol).
//   6. NO CONSOLE ERRORS  — every page gets console(error) + pageerror listeners;
//                           an uncaught throw fails the test (a small denylist
//                           absorbs known third-party/network noise on console).
//   7. PAYMENT HEALTH     — GET /api/pdf_health?key=STATS_KEY reports render_ok
//                           true, and the free-pass order returns success.
//
// Selectors/flow mirror tests/e2e/{shaadi,padhai,checkout}.spec.js. Marriage &
// career use the single-person #kundliForm (#f-* ids; career adds a required
// #f-stage and has no gender field); compatibility uses the two-person
// #milanForm (p1-*/p2-* ids, gender inferred by role — no gender field).
//
// Any failed assertion fails the test, which makes `npx playwright test` exit
// non-zero — the loud signal CI / the on-call mechanic reacts to.

const { test, expect } = require('@playwright/test');

// ---- Env / preconditions -------------------------------------------------
const TARGET = process.env.OPS_TARGET_URL;
const STATS_KEY = process.env.STATS_KEY;

test.beforeAll(() => {
  if (!TARGET) throw new Error('OPS_TARGET_URL is not set — point the robot at a deployment.');
  if (!STATS_KEY) throw new Error('STATS_KEY is not set — needed to mint a free unlock pass.');
});

// A valid 10-digit Indian mobile, UNIQUE per call so we never collide with a
// prior robot account in the shared prod DB (mobile is the account key, and the
// app de-dupes contacts by mobile). Date.now()+counter+random keeps it unique
// even for two journeys that start within the same millisecond.
let _phoneSeq = 0;
function testPhone() {
  const suffix = String(Date.now() + _phoneSeq++ + Math.floor(Math.random() * 1000)).slice(-9);
  return '9' + suffix;
}
function testEmail() {
  return `robot-${Date.now()}-${Math.floor(Math.random() * 1e6)}@axtroshastra.test`;
}

// Full valid birth time using option values the pages actually build:
//   hour  -> "1".."12"      minute -> "00","05",... ,"55"      ap -> "AM"/"PM"
const TIME = { hh: '10', mm: '30', ap: 'AM' };

// Console-noise denylist: known-benign console.error sources on a live site
// (third-party beacons, favicon, ResizeObserver chatter). pageerror (an actual
// uncaught JS throw) is NEVER ignored — those are real bugs.
const BENIGN_CONSOLE = [
  /favicon/i,
  /ResizeObserver loop/i,
  /razorpay|checkout\.razorpay/i,
  /googletagmanager|google-analytics|gtag|facebook|fbevents|clarity|hotjar/i,
  /net::ERR_|ERR_BLOCKED_BY_CLIENT|Failed to load resource/i,
];

// Attach error listeners; returns an object whose .assertClean() fails the test
// if anything genuinely broke. Call at the very top of a test, before goto.
function watchErrors(page) {
  const pageErrors = [];
  const consoleErrors = [];
  page.on('pageerror', (err) => pageErrors.push(String(err && err.message || err)));
  page.on('console', (msg) => {
    if (msg.type() !== 'error') return;
    const text = msg.text();
    if (BENIGN_CONSOLE.some((re) => re.test(text))) return;
    consoleErrors.push(text);
  });
  return {
    assertClean() {
      expect(pageErrors, `uncaught page error(s):\n${pageErrors.join('\n')}`).toEqual([]);
      expect(consoleErrors, `console error(s):\n${consoleErrors.join('\n')}`).toEqual([]);
    },
  };
}

// Assert no horizontal overflow. Strict on mobile (the point of the check);
// desktop scrollbars make a tiny tolerance sane.
async function assertNoHorizontalOverflow(page) {
  const vw = page.viewportSize();
  const isMobile = vw && vw.width <= 600;
  const tol = isMobile ? 2 : 24;
  const metrics = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  expect(
    metrics.scrollWidth,
    `horizontal overflow: scrollWidth ${metrics.scrollWidth} > innerWidth ${metrics.innerWidth} (+${tol})`,
  ).toBeLessThanOrEqual(metrics.innerWidth + tol);
}

// ---- City autosuggest (identical to the e2e specs) -----------------------
// Type it, wait for the matching `.ci` row under <prefix>-place-list, then click
// (a plain fill leaves the report un-geocoded and /api/kundli 422s with
// "city_not_selected").
async function pickCity(page, prefix, city) {
  const input = page.locator(`#${prefix}-place`);
  await input.scrollIntoViewIfNeeded();
  await input.fill(city);
  const item = page.locator(`#${prefix}-place-list .ci`, { hasText: city }).first();
  await item.waitFor();
  await item.click();
}

// ---- Form fillers (copied from the e2e specs) ----------------------------

// Marriage / shaadi: single person on #kundliForm (has a gender field).
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

// Career / padhai(=career) / vidyarthi: single person on #kundliForm with a
// required #f-stage and NO gender field. "10th" needs no field-of-study reveal.
async function fillCareer(page) {
  await page.fill('#f-name', 'Robot Student');
  await page.selectOption('#f-stage', '10th');
  await page.fill('#f-dd', '15');
  await page.selectOption('#f-mm', '08');
  await page.fill('#f-yy', '2008');
  await page.selectOption('#f-hh', TIME.hh);
  await page.selectOption('#f-mm2', TIME.mm);
  await page.selectOption('#f-ap', TIME.ap);
  await pickCity(page, 'f', 'Delhi');
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

// ---- Funnels, parametrised -----------------------------------------------
// `en`/`hi` are the two language routes for each product. NOTE: career has no
// Devanagari /hi/career; its second-language variant is the Hinglish page at
// /hinglish/career (see assumptions in the task summary). `form` is the CSS id
// of the birth form, used for the pre-submit CTA (submit-button) assertion.
const FUNNELS = [
  { name: 'compatibility', en: '/en/compatibility', hi: '/hi/compatibility', form: '#milanForm', fill: fillCompatibility },
  { name: 'marriage',      en: '/en/marriage',      hi: '/hi/marriage',      form: '#kundliForm', fill: fillMarriage },
  { name: 'career',        en: '/career',           hi: '/hinglish/career',  form: '#kundliForm', fill: fillCareer },
];

// ==========================================================================
// 1/3/4/5/6 — Funnel loads, CTAs, preview renders, responsive, no console errors.
// Runs for every product in BOTH languages, and (via projects) on BOTH the
// mobile and desktop viewport.
// ==========================================================================
for (const funnel of FUNNELS) {
  for (const lang of ['en', 'hi']) {
    const path = funnel[lang];
    test(`${funnel.name} [${lang}] loads, CTAs healthy, preview renders, responsive, no console errors`, async ({ page }) => {
      const errors = watchErrors(page);

      // (1) The page loads with a 2xx/3xx.
      const resp = await page.goto(path);
      expect(resp, `no response for ${path}`).toBeTruthy();
      expect(resp.status(), `${path} HTTP ${resp.status()}`).toBeLessThan(400);

      // (3) Pre-submit CTA: the form's submit button is visible + enabled.
      const submitBtn = page.locator(`${funnel.form} button[type="submit"]`).first();
      await expect(submitBtn, 'form submit CTA missing').toBeVisible();
      await expect(submitBtn, 'form submit CTA disabled').toBeEnabled();

      // (5) No horizontal overflow (strict on mobile).
      await assertNoHorizontalOverflow(page);

      // (1/4) Fill + submit; the free teaser/preview must render.
      await funnel.fill(page);
      await expect(page.locator('#teaser'), 'free teaser/preview never appeared after submit')
        .toBeVisible({ timeout: 30_000 });

      // The page stashes the persisted report id on window after /api/kundli.
      const rid = await page.evaluate(() => window.REPORT_ID);
      expect(rid, 'window.REPORT_ID was not set — /api/kundli did not persist').toBeTruthy();

      // (3) Post-submit CTA: the primary Unlock button is visible, enabled, and
      // wired to the payment action (onclick -> startPayment()).
      const unlock = page.locator('#unlockBtn');
      await unlock.scrollIntoViewIfNeeded();
      await expect(unlock, 'primary unlock CTA missing').toBeVisible();
      await expect(unlock, 'primary unlock CTA disabled').toBeEnabled();
      const onclick = await unlock.getAttribute('onclick');
      expect(onclick || '', 'unlock CTA not wired to startPayment()').toMatch(/startPayment/);

      // (5) Still no overflow once the teaser + CTAs have expanded the page.
      await assertNoHorizontalOverflow(page);

      // (6) No uncaught JS / console errors across the whole journey.
      errors.assertClean();
    });
  }
}

// ==========================================================================
// 2/7 — Free-pass unlock end-to-end -> paid report + PDF. English funnels.
// Also proves the free-pass order returns success (part of payment health).
// ==========================================================================
for (const funnel of FUNNELS) {
  test(`${funnel.name}: free-pass unlock renders a paid report + PDF`, async ({ page, request }) => {
    const errors = watchErrors(page);

    // 1) Mint a one-time free unlock token via the admin route.
    const passResp = await request.get(`/api/make_pass?key=${encodeURIComponent(STATS_KEY)}&n=1`);
    expect(passResp.ok(), `make_pass HTTP ${passResp.status()}`).toBeTruthy();
    const passBody = await passResp.json();
    expect(Array.isArray(passBody.passes)).toBeTruthy();
    const token = passBody.passes && passBody.passes[0];
    expect(token, 'make_pass returned no token').toBeTruthy();

    // 2) Real browser: open the funnel, fill the birth form, submit, see teaser.
    await page.goto(funnel.en);
    await funnel.fill(page);
    await expect(page.locator('#teaser'), 'free teaser never appeared after submit')
      .toBeVisible({ timeout: 30_000 });

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
    await expect(page.locator('body')).not.toBeEmpty();

    // 5) The PDF must be fetchable: 200 + a PDF content-type + non-empty body.
    const pdfResp = await request.get(`/report/${rid}.pdf`);
    expect(pdfResp.status(), `PDF HTTP ${pdfResp.status()}`).toBe(200);
    expect(
      (pdfResp.headers()['content-type'] || '').toLowerCase(),
      'PDF response was not application/pdf',
    ).toContain('pdf');
    const pdfBody = await pdfResp.body();
    expect(pdfBody.length, 'PDF body was empty').toBeGreaterThan(1000);
    expect(pdfBody.slice(0, 4).toString('latin1'), 'not a real PDF (missing %PDF header)').toBe('%PDF');

    errors.assertClean();
  });
}

// ==========================================================================
// 7 — Payment / render-pipeline health (no real charge).
// The PDF-maker (headless Chrome) is what WhatsApp delivery downloads; a URL
// health check makes its status visible without SSH.
// ==========================================================================
test('payment health: pdf_health reports render_ok', async ({ request }) => {
  const resp = await request.get(`/api/pdf_health?key=${encodeURIComponent(STATS_KEY)}`);
  expect(resp.ok(), `pdf_health HTTP ${resp.status()}`).toBeTruthy();
  const body = await resp.json();
  expect(
    body.render_ok === true,
    `PDF pipeline unhealthy: ${JSON.stringify(body)}`,
  ).toBeTruthy();
});
