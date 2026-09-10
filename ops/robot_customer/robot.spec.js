// Robot customer v2 — live site health check, four phases.
//
// Unlike v1, this robot NEVER calls /api/make_pass or /api/order, NEVER
// triggers LLM generation, and NEVER creates PDF reports. It exercises the
// form-to-teaser pipeline only — proving the site works without burning
// Claude API credits or cluttering the database with fake paid reports.
//
// Phases (from ops/ARCHITECTURE.md):
//   B1 — PAGE HEALTH     Every page returns 200, no JS errors, no horizontal
//                         overflow, loads in < 5 seconds.
//   B2 — FUNNEL SMOKE    Each product funnel's form loads, fills, submits,
//                         and the teaser/preview renders with a REPORT_ID.
//                         Stops BEFORE payment. No /api/order. No LLM.
//   B3 — SEO CHECKS      Every page has <title>, <meta description>, <h1>,
//                         canonical URL, and images have alt text.
//   B4 — CLEANUP         POST /api/admin/robot_cleanup to delete any reports
//                         the robot created during form submission.
//
// Runs against OPS_TARGET_URL on both mobile + desktop viewports (see
// playwright.config.js). Any failed assertion makes `npx playwright test`
// exit non-zero — the loud signal CI / the on-call mechanic reacts to.

const { test, expect } = require('@playwright/test');

// ---- Env / preconditions -------------------------------------------------
const TARGET = process.env.OPS_TARGET_URL;
const ADMIN_KEY = process.env.ADMIN_KEY || process.env.STATS_KEY;

test.beforeAll(() => {
  if (!TARGET) throw new Error('OPS_TARGET_URL is not set — point the robot at a deployment.');
  if (!ADMIN_KEY) throw new Error('ADMIN_KEY / STATS_KEY is not set — needed for cleanup.');
});

// ---- Pending-deploy gate -------------------------------------------------
// A page that is merged into the code but not yet on the LIVE deployment would
// 404 and turn the whole monitor red for no real reason (see backlog.md). Any
// route listed here is treated as "pending deploy": if it 404s on the live
// target it is SKIPPED (not failed); the moment it's actually deployed (200) it
// is tested normally — so this self-heals, and a genuine was-live-now-404
// regression on any route NOT listed here still fails hard.
//
// Seed via OPS_PENDING_DEPLOY (comma-separated paths); the default lists the
// routes we know are merged ahead of deploy. Remove a route once it's live
// (harmless if left — it self-heals — but stale).
//
// FUTURE (backlog): replace this manual allow-list with deployed-SHA gating —
// read /healthz {version} and run a feature's tests only when its commit is an
// ancestor of the live SHA. That needs the deploy to stamp APP_COMMIT first.
const PENDING_DEPLOY = new Set(
  (process.env.OPS_PENDING_DEPLOY || '/en/marriage-v3,/hi/marriage-v3,/en/business-growth,/hi/business-growth')
    .split(',').map((s) => s.trim()).filter(Boolean),
);

// If `path` is a pending-deploy route that isn't live yet (404 / unreachable),
// mark the current test SKIPPED (test.skip throws to abort it). If the route is
// live (2xx/3xx) or not gated, do nothing and let the test run.
async function skipIfPendingDeploy(path, request) {
  if (!PENDING_DEPLOY.has(path)) return;
  let status = 0;
  try {
    const r = await request.get(TARGET + path, { failOnStatusCode: false });
    status = r.status();
  } catch (e) {
    status = 0; // transport error — treat as not-confirmed-live
  }
  test.skip(
    status === 404 || status === 0,
    `pending deploy: ${path} not live yet (status ${status})`,
  );
}

// ---- Page list -----------------------------------------------------------
// Hardcoded from `ls pages/` + the server's URL routes. Structured so
// swapping to a dynamic fetch is a one-line change:
//   const ALL_PAGES = await fetch(`${TARGET}/api/admin/sitemap`).then(r => r.json());
const ALL_PAGES = [
  { path: '/',                  label: 'Home (EN)' },
  { path: '/hi',                label: 'Home (HI)' },
  { path: '/en/compatibility',  label: 'Compatibility (EN)' },
  { path: '/hi/compatibility',  label: 'Compatibility (HI)' },
  { path: '/en/marriage',       label: 'Marriage (EN)' },
  { path: '/hi/marriage',       label: 'Marriage (HI)' },
  { path: '/en/marriage-v2',    label: 'Marriage V2 (EN)' },
  { path: '/hi/marriage-v2',    label: 'Marriage V2 (HI)' },
  { path: '/en/marriage-v3',    label: 'Marriage V3 Parent (EN)' },
  { path: '/hi/marriage-v3',    label: 'Marriage V3 Parent (HI)' },
  { path: '/career',            label: 'Career (EN)' },
  { path: '/hinglish/career',   label: 'Career (Hinglish)' },
  { path: '/en/business-growth', label: 'Business Growth (EN)' },
  { path: '/hi/business-growth', label: 'Business Growth (HI)' },
  { path: '/en/career-growth',  label: 'Career Growth (EN)' },
  { path: '/hi/career-growth',  label: 'Career Growth (HI)' },
  { path: '/en/career-intelligence', label: 'Career Intelligence (EN)' },
  { path: '/en/life-blueprint', label: 'Life Blueprint (EN)' },
  { path: '/hi/life-blueprint', label: 'Life Blueprint (HI)' },
  { path: '/login',             label: 'Login' },
  { path: '/about',             label: 'About' },
  { path: '/privacy',           label: 'Privacy' },
  { path: '/terms',             label: 'Terms' },
  { path: '/refunds',           label: 'Refunds' },
  { path: '/blog',              label: 'Blog Index' },
  { path: '/blog/birth-time-nahi-pata-chandra-lagna',  label: 'Blog: Birth Time' },
  { path: '/blog/kundli-milan-36-gun',                 label: 'Blog: 36 Gun' },
  { path: '/blog/manglik-dosha-cancellation',           label: 'Blog: Manglik' },
  { path: '/blog/shaadi-kab-hogi-marriage-timing',      label: 'Blog: Marriage Timing' },
  { path: '/blog/vimshottari-dasha-life-phases',        label: 'Blog: Dasha Phases' },
];

// ---- Console-noise denylist ----------------------------------------------
// Known-benign console.error sources on a live site (third-party beacons,
// favicon, ResizeObserver chatter). pageerror (an actual uncaught JS throw)
// is NEVER ignored — those are real bugs.
const BENIGN_CONSOLE = [
  /favicon/i,
  /ResizeObserver loop/i,
  /razorpay|checkout\.razorpay/i,
  /googletagmanager|google-analytics|gtag|facebook|fbevents|clarity|hotjar/i,
  /net::ERR_|ERR_BLOCKED_BY_CLIENT|Failed to load resource/i,
];

// ---- Shared helpers ------------------------------------------------------

// Attach error listeners; returns an object whose .assertClean() fails the
// test if anything genuinely broke. Call at the top of a test, before goto.
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

// ---- Unique phone (valid Indian mobile) ----------------------------------
// UNIQUE per call so we never collide with a prior robot account in the
// shared prod DB (mobile is the account key). Date.now()+counter+random
// keeps it unique even within the same millisecond.
let _phoneSeq = 0;
function testPhone() {
  const suffix = String(Date.now() + _phoneSeq++ + Math.floor(Math.random() * 1000)).slice(-9);
  return '9' + suffix;
}

// Birth time using option values the pages actually build:
//   hour -> "1".."12"    minute -> "00","05",...,"55"    ap -> "AM"/"PM"
const TIME = { hh: '10', mm: '30', ap: 'AM' };

// ---- City autosuggest (identical to the e2e specs) -----------------------
// Type it, wait for the matching `.ci` row under <prefix>-place-list, then
// click (a plain fill leaves the report un-geocoded and the API 422s).
async function pickCity(page, prefix, city) {
  const input = page.locator(`#${prefix}-place`);
  await input.scrollIntoViewIfNeeded();
  await input.fill(city);
  const item = page.locator(`#${prefix}-place-list .ci`, { hasText: city }).first();
  await item.waitFor();
  await item.click();
}

// ---- Form fillers --------------------------------------------------------
// Names use "Smoke" / "Test" prefixes so they're obviously fake but NOT
// "Robot"-prefixed (the cleanup endpoint can target these if needed).

// Marriage (shaadi): single person, #kundliForm, has gender field.
async function fillMarriage(page) {
  await page.fill('#f-name', 'Smoke Priya');
  await page.selectOption('#f-gender', 'female');
  await page.fill('#f-dd', '12');
  await page.selectOption('#f-mm', '03');
  await page.fill('#f-yy', '1995');
  await page.selectOption('#f-hh', TIME.hh);
  await page.selectOption('#f-mm2', TIME.mm);
  await page.selectOption('#f-ap', TIME.ap);
  await pickCity(page, 'f', 'Jaipur');
  await page.locator('#kundliForm button[type="submit"]').click();
}

// Marriage V2: single person, #kundliForm, has gender + WhatsApp fields.
// V2 goes STRAIGHT to Razorpay after /api/kundli (no teaser step).
// The /api/order route is blocked by the test harness.
async function fillMarriageV2(page) {
  await page.fill('#f-name', 'Test Meera');
  await page.selectOption('#f-gender', 'female');
  await page.fill('#f-dd', '22');
  await page.selectOption('#f-mm', '07');
  await page.fill('#f-yy', '1996');
  await page.selectOption('#f-hh', TIME.hh);
  await page.selectOption('#f-mm2', TIME.mm);
  await page.selectOption('#f-ap', TIME.ap);
  await pickCity(page, 'f', 'Delhi');
  await page.fill('#f-whatsapp', testPhone());
  await page.locator('#kundliForm button[type="submit"]').click();
}

// Compatibility (milan): two people, #milanForm (p1 = girl, p2 = boy).
async function fillCompatibility(page) {
  for (const p of ['p1', 'p2']) {
    await page.fill(`#${p}-name`, p === 'p1' ? 'Smoke Nisha' : 'Test Rahul');
    await page.fill(`#${p}-dd`, '18');
    await page.selectOption(`#${p}-mm`, '04');
    await page.fill(`#${p}-yy`, p === 'p1' ? '1994' : '1993');
    await page.selectOption(`#${p}-hh`, TIME.hh);
    await page.selectOption(`#${p}-mm2`, TIME.mm);
    await page.selectOption(`#${p}-ap`, TIME.ap);
    await pickCity(page, p, 'Jaipur');
  }
  await page.fill('#wa-phone', testPhone());
  await page.locator('#milanForm button[type="submit"]').click();
}

// Career: single person, #kundliForm, has #f-stage, NO gender field.
// "10th" avoids revealing the field-of-study sub-select.
async function fillCareer(page) {
  await page.fill('#f-name', 'Test Vikram');
  await page.selectOption('#f-stage', '10th');
  await page.fill('#f-dd', '05');
  await page.selectOption('#f-mm', '11');
  await page.fill('#f-yy', '2008');
  await page.selectOption('#f-hh', TIME.hh);
  await page.selectOption('#f-mm2', TIME.mm);
  await page.selectOption('#f-ap', TIME.ap);
  await pickCity(page, 'f', 'Mumbai');
  await page.locator('#kundliForm button[type="submit"]').click();
}

// Business growth (vyapar): single person, #kundliForm, WhatsApp field, no
// gender/stage. Submit reveals the personalized preview and sets REPORT_ID
// (payment happens inside that preview, so this stops before any charge).
async function fillVyapar(page) {
  await page.fill('#f-name', 'Test Rohit');
  await page.fill('#f-dd', '06');
  await page.selectOption('#f-mm', '10');
  await page.fill('#f-yy', '1987');
  await page.selectOption('#f-hh', TIME.hh);
  await page.selectOption('#f-mm2', TIME.mm);
  await page.selectOption('#f-ap', TIME.ap);
  await pickCity(page, 'f', 'Jaipur');
  await page.fill('#f-whatsapp', testPhone());
  await page.locator('#kundliForm button[type="submit"]').click();
}

// Career Growth: single person, #kundliForm, has gender + employment situation
// + experience fields. Free-preview teaser step (#teaser), same pattern as
// compatibility/marriage — WhatsApp is collected later via the unlock-time
// contact modal, not in this form.
async function fillCareerGrowth(page) {
  await page.fill('#f-name', 'Test Rohan');
  await page.selectOption('#f-gender', 'male');
  await page.selectOption('#f-employment', 'changing-job');
  await page.selectOption('#f-experience', '5-10');
  await page.fill('#f-dd', '14');
  await page.selectOption('#f-mm', '06');
  await page.fill('#f-yy', '1996');
  await page.selectOption('#f-hh', TIME.hh);
  await page.selectOption('#f-mm2', TIME.mm);
  await page.selectOption('#f-ap', TIME.ap);
  await pickCity(page, 'f', 'Bengaluru');
  await page.locator('#kundliForm button[type="submit"]').click();
}

// Life Blueprint: single person, #kundliForm, split dd/mm/yy DOB fields
// (same shape as career-growth) and an "approximate time" fallback we don't
// exercise here since we always provide an exact known time. WhatsApp is
// collected later via the unlock-time contact modal, same as compatibility.
async function fillBlueprint(page) {
  await page.fill('#f-name', 'Test Ananya');
  await page.selectOption('#f-gender', 'female');
  await page.fill('#f-dd', '23');
  await page.selectOption('#f-mm', '09');
  await page.fill('#f-yy', '1992');
  await page.selectOption('#f-hh', TIME.hh);
  await page.selectOption('#f-mm2', TIME.mm);
  await page.selectOption('#f-ap', TIME.ap);
  await pickCity(page, 'f', 'Pune');
  await page.locator('#kundliForm button[type="submit"]').click();
}

// ---- Funnel definitions --------------------------------------------------
const FUNNELS = [
  {
    name: 'marriage',
    paths: { en: '/en/marriage', hi: '/hi/marriage' },
    form: '#kundliForm',
    fill: fillMarriage,
    hasTeaser: true,
  },
  {
    name: 'marriage-v2',
    paths: { en: '/en/marriage-v2', hi: '/hi/marriage-v2' },
    form: '#kundliForm',
    fill: fillMarriageV2,
    hasTeaser: false,   // v2 goes straight to Razorpay; no teaser step
  },
  {
    name: 'marriage-v3',
    paths: { en: '/en/marriage-v3', hi: '/hi/marriage-v3' },
    form: '#kundliForm',
    fill: fillMarriageV2,   // identical form structure/IDs to v2 — only copy differs
    hasTeaser: false,       // same straight-to-Razorpay funnel as v2
  },
  {
    name: 'compatibility',
    paths: { en: '/en/compatibility', hi: '/hi/compatibility' },
    form: '#milanForm',
    fill: fillCompatibility,
    hasTeaser: true,
  },
  {
    name: 'career',
    paths: { en: '/career', hi: '/hinglish/career' },
    form: '#kundliForm',
    fill: fillCareer,
    hasTeaser: true,
  },
  {
    name: 'business-growth',
    paths: { en: '/en/business-growth', hi: '/hi/business-growth' },
    form: '#kundliForm',
    fill: fillVyapar,
    hasTeaser: false,   // submit reveals #sampleReport + sets REPORT_ID; pay is inside it
  },
  {
    name: 'career-growth',
    paths: { en: '/en/career-growth', hi: '/hi/career-growth' },
    form: '#kundliForm',
    fill: fillCareerGrowth,
    hasTeaser: true,    // free-preview teaser, same as marriage/compatibility
  },
  {
    name: 'life-blueprint',
    paths: { en: '/en/life-blueprint', hi: '/hi/life-blueprint' },
    form: '#kundliForm',
    fill: fillBlueprint,
    hasTeaser: true,    // free-preview teaser, same as marriage/compatibility
  },
];

// ==========================================================================
// Phase B1 — Page health
// For EVERY page on the site: HTTP 200, no JS errors, no horizontal
// overflow, loads in < 5 seconds.
// ==========================================================================
test.describe('B1 — Page health', () => {
  for (const pg of ALL_PAGES) {
    test(`${pg.label} (${pg.path}): 200, no errors, no overflow, < 5s`, async ({ page, request }) => {
      await skipIfPendingDeploy(pg.path, request);
      const errors = watchErrors(page);

      const t0 = Date.now();
      const resp = await page.goto(pg.path, { waitUntil: 'load' });
      const loadMs = Date.now() - t0;

      // HTTP 200 (or 2xx/3xx — anything below 400).
      expect(resp, `no response for ${pg.path}`).toBeTruthy();
      expect(resp.status(), `${pg.path} returned HTTP ${resp.status()}`).toBeLessThan(400);

      // Loads in under 5 seconds.
      expect(loadMs, `${pg.path} took ${loadMs}ms (limit 5000ms)`).toBeLessThan(5000);

      // No horizontal overflow (strict on mobile).
      await assertNoHorizontalOverflow(page);

      // No uncaught JS or console errors.
      errors.assertClean();
    });
  }
});

// ==========================================================================
// Phase B2 — Funnel smoke
// For each funnel (marriage, marriage-v2, compatibility, career) in both
// languages: fill form, submit, verify teaser/REPORT_ID, stop. NO payment.
// ==========================================================================
test.describe('B2 — Funnel smoke', () => {
  for (const funnel of FUNNELS) {
    for (const lang of Object.keys(funnel.paths)) {   // only the languages a funnel actually defines
      const path = funnel.paths[lang];

      test(`${funnel.name} [${lang}] form -> submit -> pipeline works (no payment)`, async ({ page, request }) => {
        await skipIfPendingDeploy(path, request);
        const errors = watchErrors(page);

        // --- Safety net: block payment routes so no charge can ever occur ---
        // /api/order: return a response that makes startPayment() exit cleanly
        // (the "invalid_pass" error path shows an alert and returns — no
        // Razorpay, no redirect, no uncaught error).
        await page.route('**/api/order', (route) =>
          route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ error: 'invalid_pass' }),
          }),
        );
        await page.route('**/api/make_pass**', (route) => route.abort());

        // Dismiss any alert dialogs (from the blocked /api/order in v2).
        page.on('dialog', (d) => d.dismiss());

        // 1) Load the funnel page.
        const resp = await page.goto(path);
        expect(resp, `no response for ${path}`).toBeTruthy();
        expect(resp.status(), `${path} returned HTTP ${resp.status()}`).toBeLessThan(400);

        // 2) Form is present; submit button is visible + enabled.
        const submitBtn = page.locator(`${funnel.form} button[type="submit"]`).first();
        await expect(submitBtn, 'form submit CTA missing').toBeVisible();
        await expect(submitBtn, 'form submit CTA disabled').toBeEnabled();

        // 3) Fill and submit the form (this triggers /api/kundli or /api/milan
        //    on the backend — a real ephemeris calc, but NO LLM call).
        await funnel.fill(page);

        // 4) For funnels with a teaser step, the free preview must render.
        if (funnel.hasTeaser) {
          await expect(
            page.locator('#teaser'),
            'teaser/preview never appeared after submit',
          ).toBeVisible({ timeout: 30_000 });
        }

        // 5) REPORT_ID must be set — proves the backend processed the chart.
        //    Marriage-v2 has a 9s min-wait animation; milan has 7s; shaadi and
        //    career have 9s. 30s timeout covers all cases comfortably.
        await page.waitForFunction(() => window.REPORT_ID != null, { timeout: 30_000 });
        const rid = await page.evaluate(() => window.REPORT_ID);
        expect(rid, 'window.REPORT_ID was not set — backend did not persist').toBeTruthy();

        // 6) No horizontal overflow after the form/teaser expanded the page.
        await assertNoHorizontalOverflow(page);

        // 7) No uncaught JS / console errors across the whole journey.
        errors.assertClean();
      });
    }
  }
});

// ==========================================================================
// Phase B3 — SEO checks
// For EVERY page: <title>, <meta description>, <h1>, canonical URL, and
// all images have alt text.
// ==========================================================================
test.describe('B3 — SEO checks', () => {
  for (const pg of ALL_PAGES) {
    test(`${pg.label} (${pg.path}): SEO tags present`, async ({ page, request }) => {
      await skipIfPendingDeploy(pg.path, request);
      await page.goto(pg.path, { waitUntil: 'domcontentloaded' });

      // <title> exists and is non-empty.
      const title = await page.evaluate(() => {
        const el = document.querySelector('title');
        return el ? el.textContent.trim() : '';
      });
      expect(title, `${pg.path} missing <title>`).toBeTruthy();

      // <meta name="description"> exists and has content.
      const description = await page.evaluate(() => {
        const el = document.querySelector('meta[name="description"]');
        return el ? (el.getAttribute('content') || '').trim() : '';
      });
      expect(description, `${pg.path} missing <meta name="description">`).toBeTruthy();

      // At least one <h1> exists.
      const h1Count = await page.evaluate(() => document.querySelectorAll('h1').length);
      expect(h1Count, `${pg.path} has no <h1>`).toBeGreaterThan(0);

      // <link rel="canonical"> exists.
      const canonical = await page.evaluate(() => {
        const el = document.querySelector('link[rel="canonical"]');
        return el ? (el.getAttribute('href') || '').trim() : '';
      });
      expect(canonical, `${pg.path} missing <link rel="canonical">`).toBeTruthy();

      // Every <img> has a non-empty alt attribute.
      // Decorative images should use alt="" (empty but present); missing alt
      // attribute entirely is the SEO failure we flag.
      const missingAlt = await page.evaluate(() => {
        const imgs = Array.from(document.querySelectorAll('img'));
        return imgs
          .filter((img) => !img.hasAttribute('alt'))
          .map((img) => img.src || img.outerHTML.slice(0, 120));
      });
      expect(
        missingAlt,
        `${pg.path} has ${missingAlt.length} image(s) without alt:\n${missingAlt.join('\n')}`,
      ).toEqual([]);
    });
  }
});

// ==========================================================================
// Phase B4 — Cleanup
// Delete any reports the robot created during B2 form submissions.
// Runs AFTER all other tests (Playwright runs tests in file order).
// ==========================================================================
test.describe('B4 — Cleanup', () => {
  test('robot_cleanup deletes smoke-test reports', async ({ request }) => {
    const resp = await request.post(
      `/api/admin/robot_cleanup?key=${encodeURIComponent(ADMIN_KEY)}`,
    );
    expect(resp.ok(), `robot_cleanup HTTP ${resp.status()}`).toBeTruthy();
    const body = await resp.json();
    // The endpoint should return a summary; log it for visibility.
    // eslint-disable-next-line no-console
    console.log('[B4] robot_cleanup response:', JSON.stringify(body));
  });
});
