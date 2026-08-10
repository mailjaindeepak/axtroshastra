// Playwright config for the Axtroshastra "robot customer".
//
// Unlike tests/e2e (which run against a local uvicorn with DEMO_MODE), this
// harness points at a LIVE deployment and walks the whole customer journey for
// real: get a free pass -> fill + submit the birth form -> redeem the pass via
// /api/order -> load the PAID report -> fetch the PDF. Any broken step fails a
// test, and a failed test makes `npx playwright test` exit non-zero so CI / the
// on-call mechanic gets a loud signal.
//
// Required env:
//   OPS_TARGET_URL  base URL of the deployment under test (e.g. https://axtroshastra.com)
//   STATS_KEY       admin key that gates /api/make_pass (issues the free unlock token)
//
// Runs every spec against BOTH a mobile and a desktop viewport.
const { defineConfig, devices } = require('@playwright/test');

const BASE_URL = process.env.OPS_TARGET_URL;

module.exports = defineConfig({
  testDir: '.',
  // Live compute (/api/kundli does a real ephemeris calc) is slower than the
  // stubbed local e2e run, so give each journey a generous budget.
  timeout: 90_000,
  expect: { timeout: 15_000 },
  // Journeys hit shared server state (one free pass each); keep them serial so
  // a flaky network step is easy to read in the report.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    // Both page navigations and the APIRequestContext (request fixture) resolve
    // relative paths against this, so `${OPS_TARGET_URL}/api/...` == `/api/...`.
    baseURL: BASE_URL,
    ignoreHTTPSErrors: true,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'mobile',  use: { ...devices['Pixel 5'] } },
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
  ],
});
