// End-to-end coverage for the REPORT ACTION BUTTONS (Download PDF + WhatsApp
// share) on the paid report page.
//
// Why this exists: the report page's two actions are assembled across layers —
// each renderer emits the buttons, then the server swaps the PDF button's
// window.print sentinel for axPdfDl() (a fetch of the headless-chrome
// /report/{rid}/pdf). A renderer that forgets the buttons, or a wiring change
// that breaks the swap, ships paid reports customers can't save or share.
// That happened twice (vyapar, blueprint) before this spec existed. The Python
// tests assert the buttons exist on every product's page; this spec goes one
// step further on one product and proves BOTH buttons actually work when
// clicked. Runs against the DEMO_MODE server CI boots (same as checkout.spec).
//
// Phone note: the WhatsApp number is unique per run (shared test DB — mobile
// is the account key; see tests' phone-uniqueness convention).

const { test, expect } = require('@playwright/test');

const uniquePhone = () =>
  '9' + String(Date.now() + Math.floor(Math.random() * 1000)).slice(-9);

async function createPaidVyaparReport(request) {
  const r = await request.post('/api/kundli', {
    data: {
      name: 'Button E2E', dob: '1988-03-21', tob: '11:20',
      place: 'Indore', lat: 22.7196, lon: 75.8577, tz: 'Asia/Kolkata',
      gender: 'male', product: 'vyapar', variant: '/business-growth',
      whatsapp: uniquePhone(),
    },
  });
  expect(r.ok(), await r.text()).toBeTruthy();
  const rid = (await r.json()).report_id;
  const pay = await request.post(`/api/_demo_pay/${rid}`);
  expect(pay.ok(), 'DEMO_MODE demo-pay failed — is the server in DEMO_MODE=1?').toBeTruthy();
  return rid;
}

test('paid report: Download PDF button fetches the real PDF', async ({ page, request }) => {
  const rid = await createPaidVyaparReport(request);
  await page.goto(`/report/${rid}`);

  const pdfBtn = page.locator('#ax-stickybar .pdf');
  await expect(pdfBtn).toBeVisible();

  // axPdfDl fetches /report/{rid}/pdf (headless-chrome render) — clicking the
  // button must produce a successful PDF response, not a print dialog.
  const [resp] = await Promise.all([
    page.waitForResponse((r) => r.url().includes(`/report/${rid}`) &&
                               r.url().includes('pdf') && r.ok(),
                         { timeout: 90_000 }),
    pdfBtn.click(),
  ]);
  expect(resp.status()).toBe(200);
  expect((await resp.body()).subarray(0, 5).toString()).toContain('%PDF');
});

test('paid report: WhatsApp share button opens a wa.me share link', async ({ page, request }) => {
  const rid = await createPaidVyaparReport(request);

  // Headless Chromium has no navigator.share, so axShare falls back to
  // window.open(wa.me). Capture that call instead of opening a real popup.
  await page.addInitScript(() => {
    window.__shared = null;
    window.open = (url) => { window.__shared = url; return null; };
  });
  await page.goto(`/report/${rid}`);

  const waBtn = page.locator('#ax-stickybar .wa');
  await expect(waBtn).toBeVisible();
  await waBtn.click();

  const shared = await page.evaluate(() => window.__shared);
  expect(shared, 'axShare did not open a share URL').toBeTruthy();
  expect(shared).toContain('wa.me');
  expect(decodeURIComponent(shared)).toContain(`/report/${rid}`); // shares THIS report's link
});
