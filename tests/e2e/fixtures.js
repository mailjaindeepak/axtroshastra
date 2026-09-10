// Shared E2E fixtures.
//
// Aborts external Google Fonts requests (fonts.googleapis.com / fonts.gstatic.com)
// on every page. Every landing page pulls 2-3 font stylesheets from those hosts,
// and `page.goto`'s default `waitUntil: 'load'` blocks until they finish. On CI
// those hosts are intermittently slow / rate-limited, so `goto` hit the 30s
// navigation timeout and the test failed — the flaky offer_timer / padhai / shaadi
// failures. (`waitUntil: 'domcontentloaded'` does NOT help: a render-blocking
// <head> stylesheet followed by an inline <body> script also blocks DOMContentLoaded.)
//
// The fonts are irrelevant to what these tests assert (text, timers, form
// behaviour), so aborting the requests is safe and only makes navigation
// deterministic. Import { test, expect } from here instead of '@playwright/test'.
const base = require('@playwright/test');

const test = base.test.extend({
  page: async ({ page }, use) => {
    await page.route(/fonts\.(googleapis|gstatic)\.com/, (route) => route.abort());
    await use(page);
  },
});

module.exports = { test, expect: base.expect };
