// Shared E2E fixtures — hermetic navigation.
//
// Every served landing page pulls third-party scripts/stylesheets: Google Fonts,
// LinkedIn Insight (snap.licdn.com / px.ads.linkedin.com), Microsoft Clarity,
// Google Tag Manager / Analytics, Meta (connect.facebook.net), and the Razorpay
// checkout SDK (a deferred <script>). `page.goto`'s default `waitUntil: 'load'`
// blocks until ALL of them settle; when a CI runner's link to any of those hosts
// is slow or rate-limited, goto hits the 30s navigation timeout and the whole
// suite fails intermittently (every spec, ~35s each — not just the font-loading
// ones). None of them are needed by what these tests assert (text, timers, forms,
// buttons): the payment flow is stubbed in checkout.spec.js and the WhatsApp share
// is captured via window.open, so nothing functional depends on a third party.
//
// So block every CROSS-ORIGIN http(s) request (anything that isn't the local app
// under test) and let goto('load') settle on same-origin content only. A test that
// needs a specific third-party response (checkout.spec's Razorpay stub) registers
// its own route INSIDE the test, which Playwright checks before this one (routes
// match last-registered-first), so those still work.
//
// Import { test, expect } from here instead of '@playwright/test'.
const base = require('@playwright/test');

const test = base.test.extend({
  page: async ({ page }, use) => {
    await page.route('**/*', (route) => {
      const url = route.request().url();
      if (!/^https?:/i.test(url)) return route.continue();   // data:, blob:, etc.
      let host = '';
      try { host = new URL(url).hostname; } catch (e) { /* fall through to abort */ }
      if (host === '127.0.0.1' || host === 'localhost') return route.continue();
      return route.abort();
    });
    await use(page);
  },
});

module.exports = { test, expect: base.expect };
