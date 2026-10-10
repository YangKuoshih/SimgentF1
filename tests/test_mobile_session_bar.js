// Phones: the header hides the session dropdown, so the weekend's sessions are a row of
// buttons under it. Checks the row offers the right sessions and switches between them.
const { chromium, devices } = require('playwright');

const BASE_URL = process.env.BASE_URL || 'http://localhost:8080';
let failures = 0;
function check(cond, msg) {
  console.log(`${cond ? '✅' : '❌'} ${msg}`);
  if (!cond) failures++;
}

async function towerLoaded(page) {
  await page.waitForFunction(() => document.querySelectorAll('.tower-row').length > 0, null, { timeout: 30000 });
}

(async () => {
  console.log('📱 Mobile session picker (iPhone 13)...');
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext(devices['iPhone 13']);
    await context.addInitScript(() => localStorage.setItem('simgent_welcomed_v1', '1'));
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(String(e)));

    // Sprint weekend: all four sessions, in weekend order
    await page.goto(`${BASE_URL}/?year=2026&round=17&session=sprint`, { waitUntil: 'domcontentloaded' });
    await towerLoaded(page);
    const bar = page.locator('#mobile-session-bar');
    check(await bar.isVisible(), 'session buttons visible on a phone');
    const sessions = await bar.locator('button').evaluateAll(bs => bs.map(b => b.dataset.session));
    check(sessions.join(',') === 'sprint_qualifying,sprint,qualifying,race', `sprint weekend offers ${sessions.join(', ')}`);

    for (const s of ['sprint_qualifying', 'qualifying', 'sprint']) {
      await bar.locator(`button[data-session="${s}"]`).click();
      await page.waitForFunction(x => new URL(location.href).searchParams.get('session') === x, s, { timeout: 15000 });
      await towerLoaded(page);
      const active = await bar.locator('button[aria-selected="true"]').getAttribute('data-session');
      check(active === s, `tapping ${s} loads it and highlights it`);
    }

    // Weekend without a Sprint: Qualifying and Grand Prix only
    await page.goto(`${BASE_URL}/?year=2026&round=16`, { waitUntil: 'domcontentloaded' });
    await towerLoaded(page);
    const plain = await bar.locator('button').evaluateAll(bs => bs.map(b => b.dataset.session));
    check(plain.join(',') === 'qualifying,race', `weekend without a Sprint offers ${plain.join(', ')}`);
    check(errors.length === 0, `no page errors${errors.length ? ': ' + errors.join('; ') : ''}`);

    // Desktop keeps the dropdown; the phone row stays hidden
    const desktop = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
    await desktop.goto(`${BASE_URL}/?year=2026&round=17&session=sprint`, { waitUntil: 'domcontentloaded' });
    await towerLoaded(desktop);
    check(await desktop.locator('#session-select').isVisible() && !(await desktop.locator('#mobile-session-bar').isVisible()),
      'desktop shows the dropdown, not the phone row');
  } finally {
    await browser.close();
  }
  if (failures) {
    console.error(`\n❌ ${failures} mobile session check(s) failed`);
    process.exit(1);
  }
  console.log('\n🎉 ALL MOBILE SESSION PICKER CHECKS PASSED!');
})();
