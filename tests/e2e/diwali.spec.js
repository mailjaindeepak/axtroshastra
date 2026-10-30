// E2E for /en/diwali (Diwali Wealth & Prosperity Report), against the REAL page and
// the REAL backend (DEMO_MODE=1 server on the test MySQL, NARRATIVE_ENABLED=0 so the
// deterministic bank writes the report). Nothing on our side is mocked: city search,
// /api/kundli (engine + teaser), /api/order, /api/_demo_pay, /api/report polling,
// /report/{id} and /report/{id}.pdf all run for real.
//
// The only stub is Razorpay's hosted checkout (it cannot be automated, and CI has no
// keys): window.Razorpay.open() does what a real payment does on our side — the
// DEMO_MODE demo-pay marks the report paid, then the page's own success handler runs.
// /api/order still reaches the server (contact attach + amount); only when the
// server answers 503 "Payment not configured" (no keys) do we hand the page a stub
// order so the flow can continue.
//
// Screenshots for a human look: E2E_SHOTS=1 npx playwright test diwali.spec.js
// (saved to docs/diwali/e2e-shots/, Google Fonts allowed so the type looks real).
const path = require('path');
const { test, expect } = require('./fixtures');

// Month names in any case, built without the 'i' flag so the two month names that are also English
// words (the verb "may", the verb "march") count only where they are clearly months: capitalised
// mid-sentence ("in May.", "best in March"), next to another month or a year ("May–Jul", "may 2027"),
// or after a time preposition ("best in may"). "Which months may…", "May your Diwali…", "things march on" never hit.
const ci = (w) => w.replace(/[a-z]/gi, (c) => `[${c.toLowerCase()}${c.toUpperCase()}]`);
const OTHER = 'January|February|April|June|July|August|September|October|November|December|Jan|Feb|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec'
  .split('|').map(ci).join('|');
const WORDY = ['march', 'may'].map(ci).join('|');
const ANY = `${OTHER}|${WORDY}|${ci('mar')}`;
const MONTH_RE = new RegExp(
  `\\b(${OTHER})\\b` +
  `|\\b(March|MARCH|Mar|MAR)\\b` +
  `|\\b(May|MAY)\\b(?!\\s+(?:your|you|you\u2019re|the|this|that|it|he|she|they|we|I|all|every|each|our|his|her|their|these|those|a|an|be|God|Lakshmi)\\b)` +
  `|\\b(${ANY})\\s*[\u2013\u2014-]\\s*(${ANY})\\b` +
  `|\\b(${WORDY})\\s+(${OTHER})\\b|\\b(${OTHER})\\s+(${WORDY})\\b` +
  `|\\b(${WORDY}),?\\s+('\\d\\d|(19|20)\\d\\d)\\b|\\b20\\d\\d-\\d\\d\\b` +
  `|\\b(${['in', 'from', 'by', 'until', 'till', 'through', 'after', 'before', 'during', 'since', 'early', 'late', 'mid', 'for', 'around', 'near', 'of'].map(ci).join('|')})\\s+(${WORDY})\\b`);
const SHOTS = process.env.E2E_SHOTS ? path.resolve(__dirname, '../../docs/diwali/e2e-shots') : null;
// spec §6a Money set (owner-approved wording)
const MONEY_QS = [
  'Will your financial fortunes improve after this Diwali?',
  'When could your next period of financial growth begin?',
  'Does your birth chart suggest stronger wealth-building opportunities from this Diwali to the next?',
  'Which months may call for more care with spending?',
  'Which months may be favourable for buying gold or property?',
];

// shared test DB: mobile number is the account key, so one per test
const uniquePhone = () => '9' + String(Date.now() + Math.floor(Math.random() * 100000)).slice(-9);

async function shot(page, testInfo, name, opts = {}) {
  if (!SHOTS) return;
  await page.screenshot({ path: path.join(SHOTS, `${name}-${testInfo.project.name}.png`), ...opts });
}

async function pickCity(page, city) {
  await page.fill('#f-place', city);
  const item = page.locator('#f-place-list .ci', { hasText: city }).first();
  await item.waitFor({ timeout: 15_000 });
  await item.click();
}

async function fillValid(page, o = {}) {
  await page.fill('#f-name', o.name || 'Meera Kulkarni');
  await page.selectOption('#f-gender', o.gender || 'female');
  await page.fill('#f-dd', '14');
  await page.selectOption('#f-mm', '08');
  await page.fill('#f-yy', '1984');
  await page.selectOption('#f-hh', '7');
  await page.fill('#f-mm2', '40');
  await page.selectOption('#f-ap', 'AM');
  await pickCity(page, 'Pune');
  await page.selectOption('#f-work', o.work || 'business');
  if (o.area) await page.selectOption('#f-area', o.area);
  await page.fill('#f-whatsapp', uniquePhone());
}

// submit and wait for the REAL /api/kundli answer; returns {req, data}
async function submitReal(page) {
  const [resp] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith('/api/kundli') && r.request().method() === 'POST', { timeout: 40_000 }),
    page.locator('#kundliForm button[type="submit"]').click(),
  ]);
  expect(resp.status(), await resp.text()).toBe(200);
  const data = await resp.json();
  await expect(page.locator('#teaser')).toBeVisible({ timeout: 15_000 });
  return { req: resp.request().postDataJSON(), data };
}

async function noHorizontalScroll(page) {
  const over = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(over, 'page scrolls sideways').toBeLessThanOrEqual(1);
}

test.beforeEach(async ({ page }) => {
  // Each test is its own visitor: ratelimit.py buckets by X-Forwarded-For, so without this the
  // real /api/kundli + /api/city-suggest calls here would drain the one 127.0.0.1 bucket and
  // 429 the other specs. (A CI-wide RATE_LIMIT_ENABLED=0 on the e2e server would also do.)
  const ip = `10.${(Math.random() * 250) | 0}.${(Math.random() * 250) | 0}.${1 + ((Math.random() * 250) | 0)}`;
  await page.setExtraHTTPHeaders({ 'x-forwarded-for': ip });
  if (SHOTS) {   // real fonts only for the look check; the default run stays hermetic
    await page.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.continue());
  }
  await page.addInitScript(() => { window.__axFast = true; window.__axNoScroll = true; });
  await page.goto('/en/diwali');
});

test('Landing: head tags, ₹499 shown, no sideways scroll', async ({ page }, testInfo) => {
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href', 'https://www.axtroshastra.com/en/diwali');
  await expect(page.locator('link[hreflang="hi"]')).toHaveCount(0);
  await expect(page.locator('#offerTimer')).toContainText('₹499');
  await expect(page.locator('#submitBtn')).toContainText('Check my Diwali report');
  await noHorizontalScroll(page);
  await page.evaluate(() => document.fonts && document.fonts.ready);
  await shot(page, testInfo, 'landing');
  await shot(page, testInfo, 'landing-full', { fullPage: true });
});

test('Legacy /diwali redirects to /en/diwali', async ({ request }) => {
  const r = await request.get('/diwali', { maxRedirects: 0 });
  expect(r.status()).toBe(301);
  expect(r.headers()['location']).toBe('/en/diwali');
});

test.describe('Validation errors never reach the server', () => {
  let kundliCalls;
  test.beforeEach(async ({ page }) => {
    kundliCalls = 0;
    page.on('request', (r) => { if (r.url().endsWith('/api/kundli')) kundliCalls++; });
    await fillValid(page);
  });
  test.afterEach(async ({ page }) => {
    await expect(page.locator('#teaser')).toBeHidden();
    expect(kundliCalls).toBe(0);
  });
  const submit = (page) => page.locator('#kundliForm button[type="submit"]').click();

  test('partial birth time', async ({ page }) => {
    await page.fill('#f-mm2', '');
    await submit(page);
    await expect(page.locator('#h-tob')).toContainText(/full time/);
  });
  test('date that does not exist', async ({ page }) => {
    await page.fill('#f-dd', '31');
    await page.selectOption('#f-mm', '02');
    await submit(page);
    await expect(page.locator('#h-dob')).toContainText(/does not exist/);
  });
  test('year out of range', async ({ page }) => {
    await page.fill('#f-yy', '1850');
    await submit(page);
    await expect(page.locator('#h-dob')).toContainText(/between 1900 and today/);
  });
  test('bad WhatsApp number', async ({ page }) => {
    await page.fill('#f-whatsapp', '12345');
    await submit(page);
    await expect(page.locator('#h-wa')).toContainText(/10-digit/);
  });
  test('city typed but not picked from the list', async ({ page }) => {
    await page.fill('#f-place', 'Pune');           // typing clears the picked city
    await page.locator('#f-name').click();          // close the list without picking
    await submit(page);
    await expect(page.locator('#f-place-hint')).toContainText(/pick the birth city/);
  });
});

test('Birth time toggle: "Don\'t know your exact birth time?" swaps the boxes for "Approximate time"', async ({ page }) => {
  await expect(page.locator('#f-sure')).toHaveCount(0);                 // the old "How sure" question is gone
  await expect(page.locator('#tobField')).toBeVisible();
  await expect(page.locator('#tobApprox')).toBeHidden();
  await expect(page.locator('label.tob-toggle')).toContainText("It's our specialty.");
  await page.check('#unknownTime');
  await expect(page.locator('#tobField')).toBeHidden();
  await expect(page.locator('#tobApprox')).toBeVisible();
  await expect(page.locator('#f-approx option')).toHaveText(['Select approximate time…',
    'Morning (4 AM – 10 AM)', 'Day (10 AM – 4 PM)', 'Evening (4 PM – 10 PM)', 'Night (10 PM – 4 AM)', 'No idea at all']);
  await page.uncheck('#unknownTime');
  await expect(page.locator('#tobField')).toBeVisible();
  await expect(page.locator('#tobApprox')).toBeHidden();
  // Clear empties all three time boxes
  await page.selectOption('#f-hh', '7'); await page.fill('#f-mm2', '40'); await page.selectOption('#f-ap', 'AM');
  await page.locator('#tobField .tob-clear').click();
  await expect(page.locator('#f-mm2')).toHaveValue('');
  expect(await page.evaluate(() => [document.getElementById('f-hh').value, document.getElementById('f-ap').value, document.getElementById('f-tob').value])).toEqual(['', '', '']);
});

test('Birth time: ticked but no approximate time picked is an inline error, never a guess', async ({ page }) => {
  let kundliCalls = 0;
  page.on('request', (r) => { if (r.url().endsWith('/api/kundli')) kundliCalls++; });
  await fillValid(page);
  await page.check('#unknownTime');
  await page.locator('#kundliForm button[type="submit"]').click();
  await expect(page.locator('#h-approx')).toContainText(/approximate time/);
  await expect(page.locator('#teaser')).toBeHidden();
  expect(kundliCalls).toBe(0);
});

for (const [band, tq, label] of [['shaam', 'T2', 'a part of the day'], ['unknown', 'T3', 'No idea at all']]) {
  test(`Birth time: ${label} submits ${tq} and the preview reads from the Moon sign`, async ({ page }) => {
    test.setTimeout(90_000);
    await fillValid(page, { area: 'money' });
    await page.check('#unknownTime');
    await page.selectOption('#f-approx', band);
    const { req, data } = await submitReal(page);
    expect(req.time_quality).toBe(tq);
    expect(req.tob).toBeNull();
    expect(req.time_band).toBe(tq === 'T2' ? band : null);   // band values = api.py BAND_MID keys
    expect(data.teaser.basis).toBe('moon');
    await expect(page.locator('#kd .k-asc')).toHaveText('Moon');
    expect(await page.locator('#teaser').evaluate((el) => el.textContent)).not.toMatch(MONTH_RE);
  });
}

test('Parity with the other product pages: trust, why, birth-time section, FAQ, footer note', async ({ page }) => {
  await expect(page.locator('.hero .sub2')).toContainText('55+ pages');
  await expect(page.locator('.trust li')).toHaveCount(5);
  await expect(page.locator('.trust')).toContainText('IIT–IIM alumni');
  await expect(page.locator('section.why .block')).toHaveCount(2);
  await expect(page.locator('section.why .cred')).toContainText('Built by IIT–IIM engineers.');
  await expect(page.locator('#birthTime')).toContainText("It's our specialty.");
  await expect(page.locator('#birthTime li')).toHaveCount(3);
  const faq = page.locator('.faq summary');
  await expect(faq).toContainText(['Is this accurate?', 'Is this computer-generated?']);
  await expect(page.locator('.faq details', { hasText: "I don't know my exact birth time" }).locator('.a'))
    .toContainText('Moon sign');
  await expect(page.locator('footer')).toContainText('not certainties');
  // things deliberately NOT copied from the CI page (owner / bugs.md)
  await expect(page.locator('#reportCount')).toHaveCount(0);
  // owner (27 Oct) asked for the CI offer countdown + struck ₹999 back: present and counting down
  await expect(page.locator('#offerTimer')).toBeVisible();
  const clk = page.locator('#otClock');
  await expect(clk).toHaveText(/^\d\d:\d\d$/);
  const t0 = await clk.textContent();
  await page.waitForTimeout(2200);
  expect(await clk.textContent()).not.toBe(t0);
  await expect(page.locator('#offerTimer s')).toHaveText('₹999');
  const body = await page.locator('body').textContent();
  expect(body).not.toMatch(/14,200|25,000|people viewing|AstroSage/);
  // the unlock box carries reviews + badges; reviews never use em or en dashes (CLAUDE.md §5c)
  await expect(page.locator('#unlock .lb-rev')).toHaveCount(3);
  for (const t of await page.locator('#unlock .lb-rev p, .revs .rev p').allTextContents()) expect(t).not.toMatch(/[\u2013\u2014]/);
  await expect(page.locator('#unlock .cred-row span')).toHaveCount(3);
});

test('Sticky bar submits a filled form (same as the CI page)', async ({ page }) => {
  test.setTimeout(90_000);
  await fillValid(page);
  await page.evaluate(() => { const cb = document.getElementById('axConsent'); if (cb) cb.checked = true;
    document.getElementById('stickyBar').hidden = false; document.getElementById('stickyBar').classList.remove('kbd'); });
  const [resp] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith('/api/kundli') && r.request().method() === 'POST', { timeout: 40_000 }),
    page.locator('#stickyBtn').click(),
  ]);
  expect(resp.status()).toBe(200);
  await expect(page.locator('#teaser')).toBeVisible({ timeout: 15_000 });
});

test('Self: real preview, no months anywhere, Wrapped months locked, 5 locked Money questions, ₹499', async ({ page }, testInfo) => {
  test.setTimeout(90_000);
  await fillValid(page, { area: 'money' });
  const { req, data } = await submitReal(page);

  expect(req.product).toBe('diwali');
  expect(req.gift_mode).toBe('self');
  expect(req.steering).toBe('money');
  expect(req.tob).toBe('07:40');
  expect(req.time_quality).toBe('T0');
  expect(req.time_band).toBeNull();
  expect(data.report_id).toBeTruthy();
  expect(JSON.stringify(data.teaser)).not.toMatch(MONTH_RE);     // server never sends a month pre-payment

  const teaser = page.locator('#teaser');
  await expect(page.locator('#cvName')).toHaveText('Meera Kulkarni');
  await expect(page.locator('#emLabel')).toHaveText('You picked Money');
  const text = await teaser.evaluate((el) => el.textContent);
  expect(text).not.toMatch(MONTH_RE);
  expect(text).not.toMatch(/Cancer|Vikram|Priya/);

  // Wrapped: best + careful time are locked, the 3 words' month parts are masked
  await expect(page.locator('#story .slide.s3 .locked')).toContainText('●●●');
  await expect(page.locator('#story .slide.s4 .locked')).toContainText('●●●');
  // locked answers: the 5 §6a Money questions, as the server sent them (cover card list)
  await expect(page.locator('#cvQlabel')).toHaveText('Your 5 Diwali answers · Money');
  const cvQTexts = await page.locator('#cvQs li').evaluateAll((els) => els.map((el) => el.textContent.replace(/^\d+/, '')));
  expect(cvQTexts).toEqual(MONEY_QS);
  expect(data.teaser.questions).toEqual(MONEY_QS);
  await expect(page.locator('#cvQs li')).toHaveCount(5);
  await expect(page.locator('#unlockBtn')).toContainText('₹499');
  await expect(page.locator('#unlockBtn s')).toHaveText('₹999');
  await expect(page.locator('#unlockBtn')).toContainText(/₹999\s*₹499/);
  await expect(page.locator('#chartSum')).toContainText(/\d+ planets? in strong positions/);
  await noHorizontalScroll(page);

  if (SHOTS) {
    // Wrapped is a stacked scroll list now (no tap-through carousel), so every slide is
    // already visible and stable to shoot directly.
    const el = (sel, name) => page.locator(sel).first().screenshot({ path: path.join(SHOTS, `${name}-${testInfo.project.name}.png`) });
    await el('#teaser .cover', 'preview-cover');
    await el('#teaser .card:has(.kundli)', 'preview-chart');
    await el('#story .slide.s3', 'preview-wrapped-locked');
    await el('#unlock', 'preview-locked');
  }
});

test('Gift: real preview with giver name + message; skipped area leads with the chart’s first area', async ({ page }) => {
  test.setTimeout(90_000);
  await page.locator('label:has(#m-gift)').click();
  await expect(page.locator('#giftBox')).toBeVisible();
  await expect(page.locator('#l-name')).toHaveText('Their name');
  await page.fill('#f-giver', 'Rohan');
  await page.fill('#f-msg', 'Happy Diwali, Maa');
  await fillValid(page, { name: 'Sunita Joshi', work: 'home' });
  const { req, data } = await submitReal(page);

  expect(req.gift_mode).toBe('gift');
  expect(req.giver_name).toBe('Rohan');
  expect(req.gift_message).toBe('Happy Diwali, Maa');
  expect(req.steering).toBeNull();
  expect(JSON.stringify(data.teaser)).not.toMatch(MONTH_RE);
  expect(JSON.stringify(data.teaser)).not.toContain('Happy Diwali, Maa');   // gift note stays server-side

  await expect(page.locator('#tagWho')).toHaveText('Sunita’s');
  await expect(page.locator('#emLabel')).not.toContainText('You picked');
  const cvQTexts = await page.locator('#cvQs li').evaluateAll((els) => els.map((el) => el.textContent.replace(/^\d+/, '')));
  expect(cvQTexts).toEqual(data.teaser.questions);
  await expect(page.locator('#cvQs li')).toHaveCount(5);
  expect(await page.locator('#teaser').evaluate((el) => el.textContent)).not.toMatch(MONTH_RE);
});

test('Purchase: unlock -> /api/order -> demo pay -> progress screen -> report with PDF + WhatsApp; PDF route works', async ({ page, request }, testInfo) => {
  test.setTimeout(180_000);
  await page.route('**/checkout.razorpay.com/**', (r) => r.fulfill({ status: 200, contentType: 'application/javascript', body: '' }));
  await page.addInitScript(() => {
    window.__shared = null;
    window.open = (url) => { window.__shared = url; return null; };
    window.Razorpay = function (opts) {
      this.open = async function () {
        await fetch('/api/_demo_pay/' + window.REPORT_ID, { method: 'POST' });
        opts.handler({ razorpay_payment_id: 'pay_E2E', razorpay_order_id: opts.order_id, razorpay_signature: 'x' });
      };
    };
  });
  let order = null;
  await page.route('**/api/order', async (route) => {
    const resp = await route.fetch();                       // the real server handles it
    order = { status: resp.status(), body: route.request().postDataJSON(), server: null };
    if (resp.ok()) {
      order.server = await resp.json();                     // what the server created at Razorpay + stored
      return route.fulfill({ response: resp });
    }
    expect(await resp.text()).toContain('Payment not configured');   // got all the way to Razorpay
    // no keys: the server charged nothing, so the stub carries NO price (0) and nothing below reads it
    return route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({ razorpay_order_id: 'order_E2E', amount: 0, currency: 'INR', key_id: 'rzp_test_x' }) });
  });
  // progress screen log: survives the redirect to /report/{id}, so the 1.2 s 'ready' state is never missed
  const prog = [];
  await page.exposeFunction('__progLog', (e) => { prog.push(e); });

  await page.reload();
  await fillValid(page, { name: 'Arjun Mehta', gender: 'male', work: 'job', area: 'career' });
  const { data } = await submitReal(page);
  const rid = data.report_id;

  await page.locator('#unlockBtn').click();
  await expect(page.locator('#progOv')).toBeVisible({ timeout: 15_000 });
  await expect(page.locator('#progMsg')).toBeVisible();
  await page.evaluate(() => {
    const snap = () => window.__progLog({ msg: document.getElementById('progMsg').textContent,
      done: document.querySelectorAll('#progTicks li.done').length });
    new MutationObserver(snap).observe(document.getElementById('progOv'), { subtree: true, childList: true,
      characterData: true, attributes: true, attributeFilter: ['class'] });
    snap();
  });
  // the 5 ticks, in order
  await expect(page.locator('#progTicks li')).toHaveText(['Payment received', 'Reading your chart',
    'Writing your 5 answers', 'Mapping your 12 months', 'Making your PDF']);
  // Diwali fireworks: the canvas is there, on screen, sized, and the animation started on it
  const fw = page.locator('#progOv canvas#fwProg');
  await expect(fw).toHaveCount(1);
  await expect(fw).toBeVisible();
  expect(await fw.evaluate((c) => ({ fw: c._fw, w: c.width, h: c.height })))
    .toEqual(expect.objectContaining({ fw: 1 }));
  expect(await fw.evaluate((c) => c.getBoundingClientRect().width * c.getBoundingClientRect().height)).toBeGreaterThan(0);
  if (SHOTS) await page.waitForTimeout(1100);         // bar width animates 1.1s
  await shot(page, testInfo, 'progress');
  expect(order.body.report_id).toBe(rid);
  expect(order.body.phone).toMatch(/^\+919\d{9}$/);
  expect([200, 503]).toContain(order.status);
  if (order.status === 200) {
    // the server's own order: ₹499 by product, the same amount Razorpay is opened with
    expect(order.server.amount).toBe(49900);
    expect(order.server.currency).toBe('INR');
  } else {
    // CI has no Razorpay keys, so no order (and no payments row) exists to read here; the stored
    // payments.amount_paise == 49900 is asserted in tests/test_diwali_api.py::test_diwali_full_paid_path.
    testInfo.annotations.push({ type: 'price', description: 'no Razorpay keys: server price checked in test_diwali_api.py' });
  }

  await page.waitForURL(`**/report/${rid}`, { timeout: 90_000 });
  // progress screen ended with every tick done and the 'ready' message (the bank report is ready on the
  // first poll, so it can go 0 -> 5 in one step; no in-between state is required)
  expect(prog).toContainEqual({ msg: 'Your Diwali report is ready', done: 5 });
  await expect(page.locator('#ax-pdf')).toBeVisible();
  const share = page.locator('button.ax-share');
  await expect(share).toBeVisible();
  await share.click();                                        // headless: no navigator.share -> wa.me
  const shared = await page.evaluate(() => window.__shared);
  expect(shared, 'WhatsApp share opened nothing').toContain('wa.me');
  expect(decodeURIComponent(shared)).toContain(`/report/${rid}`);
  const html = await page.content();
  expect(html).toContain('Arjun');
  expect(html).not.toMatch(/Vikram|Priya/);
  await expect(page.locator('section.page').first()).toBeVisible();
  await noHorizontalScroll(page);
  await shot(page, testInfo, 'report');

  const pdf = await request.get(`/report/${rid}.pdf`, { timeout: 120_000 });
  expect(pdf.status()).toBe(200);
  expect(pdf.headers()['content-type']).toContain('application/pdf');
  expect((await pdf.body()).subarray(0, 5).toString()).toContain('%PDF');
});

test('Sample modal shows the 58 sample pages', async ({ page }) => {
  await page.locator('#heroSampleBtn').click();
  await expect(page.locator('#sampleModal')).toBeVisible();
  await expect(page.locator('#sampleBody img')).toHaveCount(58);
  await page.locator('#sampleModalClose').click();
  await expect(page.locator('#sampleModal')).toBeHidden();
});
