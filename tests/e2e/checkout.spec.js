// End-to-end coverage for the PAYMENT / UNLOCK flow on /shaadi.
//
// Why this exists: the report has to be *persisted* for checkout to work at all.
// The unlock path is: submit -> /api/kundli (persist) -> click Unlock ->
// /api/order -> Razorpay checkout -> on success poll /api/report/{id} until paid
// -> redirect to /report/{id}. If a write is silently not durable (the prod bug
// we hit), the demo-pay step below 404s, the report never flips to paid, and this
// test fails at the redirect — exactly the loud signal we want.
//
// Razorpay's own hosted modal cannot (and must not) be automated with real cards
// in CI, so we stub two things and drive everything else for real:
//   1. block the real checkout.js (so it can't overwrite our stub), and
//   2. replace window.Razorpay with a stub whose .open() simulates a successful
//      payment by hitting the DEMO_MODE /api/_demo_pay/{id} endpoint, then firing
//      the site's success handler — the same handler a real payment triggers.
// /api/order itself is mocked (a live order needs live keys, which CI doesn't
// have); its server-side branches are covered separately by the Python tests.

const { test, expect } = require('@playwright/test');

async function stubRazorpay(page) {
  // Prevent the real SDK from loading and clobbering our stub.
  await page.route('**/checkout.razorpay.com/**', (route) =>
    route.fulfill({ status: 200, contentType: 'application/javascript',
      body: '/* Razorpay SDK blocked in test */' }));

  // Install the stub BEFORE any page script runs.
  await page.addInitScript(() => {
    window.__rzpOpened = false;
    window.Razorpay = function (opts) {
      window.__rzpOpts = opts;
      this.open = async function () {
        window.__rzpOpened = true;
        // Simulate the payment succeeding + the webhook marking the report paid.
        try {
          await fetch('/api/_demo_pay/' + window.REPORT_ID, { method: 'POST' });
        } catch (e) { /* surfaced by the redirect assertion below */ }
        // Fire the site's own success handler (starts polling for the paid report).
        if (opts && typeof opts.handler === 'function') opts.handler({ razorpay_payment_id: 'pay_TEST' });
      };
    };
  });
}


// The pre-payment contact popup (T1-CONTACT) now intercepts the first Unlock
// click: fill the WhatsApp number and continue. Cached in sessionStorage, so
// it appears once per browser context.
async function completeContactModal(page) {
  const phone = page.locator('#axcPhone');
  await phone.waitFor({ timeout: 10_000 });
  await phone.fill('9812345678');
  await page.locator('.axc-go').click();
}

async function fillValidForm(page) {
  await page.fill('#f-name', 'Checkout Tester');
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
}

test('Checkout happy path: unlock -> Razorpay -> paid report page', async ({ page }) => {
  test.setTimeout(60_000); // absorb the real /api/kundli compute on slower (mobile) runners
  await stubRazorpay(page);

  let orderCalledWith = null;
  await page.route('**/api/order', async (route) => {
    orderCalledWith = route.request().postDataJSON();
    await route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({ razorpay_order_id: 'order_TEST', amount: 49900,
        currency: 'INR', key_id: 'rzp_test_dummy' }) });
  });

  await page.goto('/shaadi');
  await fillValidForm(page);

  await page.locator('#unlockBtn').click();
  await completeContactModal(page);

  // The site must have sent the report_id to /api/order (bound to the created report).
  await expect.poll(() => orderCalledWith && orderCalledWith.report_id).toBeTruthy();

  // Razorpay checkout was actually opened with the mocked order.
  await expect.poll(() => page.evaluate(() => window.__rzpOpened)).toBe(true);
  const rzpKey = await page.evaluate(() => window.__rzpOpts && window.__rzpOpts.key);
  expect(rzpKey).toBe('rzp_test_dummy');

  // After a successful payment the app polls the persisted report and redirects.
  // If the write were not durable this navigation never happens -> test fails loudly.
  await page.waitForURL(/\/report\//, { timeout: 30_000 });
  await expect(page.locator('body')).not.toContainText(/Report not found/i);
});

test('Checkout aborts gracefully when order creation fails (503)', async ({ page }) => {
  test.setTimeout(60_000); // absorb the real /api/kundli compute on slower (mobile) runners
  await stubRazorpay(page);
  await page.route('**/api/order', (route) =>
    route.fulfill({ status: 503, contentType: 'text/plain', body: 'Payment not configured' }));

  await page.goto('/shaadi');
  await fillValidForm(page);

  // Capture any dialog with a persistent handler registered BEFORE the click. This
  // avoids the waitForEvent/click ordering race that made this flaky on mobile: the
  // alert fires after an awaited fetch, and a late listener could miss it.
  let dialogMessage = null;
  page.on('dialog', async (d) => {
    dialogMessage = d.message();
    await d.dismiss().catch(() => {});
  });

  // Make the click deterministic — the unlock button can be below the fold after the
  // teaser reveals, and on mobile the auto-scroll occasionally raced the 30s budget.
  const unlock = page.locator('#unlockBtn');
  await unlock.scrollIntoViewIfNeeded();
  await expect(unlock).toBeEnabled();
  await unlock.click();
  await completeContactModal(page);

  // The site must alert ("Payment setup issue…") and stay put — never navigate to a report.
  await expect.poll(() => dialogMessage, { timeout: 15_000 }).toMatch(/payment setup issue/i);
  expect(new URL(page.url()).pathname).toBe('/shaadi');
});
