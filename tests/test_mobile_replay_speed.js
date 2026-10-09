const chromium = require('playwright').chromium;
const fs = require('fs');
const path = require('path');

async function runTest() {
  console.log('📱 Testing Mobile Replay Speed Controls on iPhone 15 Pro Max & iPhone SE...');
  const browser = await chromium.launch({ headless: true });

  for (const [name, width] of [['iPhone 15 Pro Max', 430], ['iPhone SE', 375]]) {
    console.log(`\nTesting ${name} (${width}px)...`);
    const context = await browser.newContext({
      viewport: { width: width, height: 667 },
      isMobile: true,
      hasTouch: true
    });
    const page = await context.newPage();
    // These checks exercise replay controls after first-visit onboarding.
    await page.addInitScript(() => localStorage.setItem('simgent_welcomed_v1', '1'));
    await page.goto('http://localhost:8080', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    const cycleBtn = page.locator('#btn-speed-cycle-mobile');
    if (!await cycleBtn.isVisible()) throw new Error(`Quick cycle not visible on ${name}`);

    // Verify 60x click on mobile strip
    const btn60 = page.locator('.speed-btn[data-speed="60"]:visible');
    await btn60.click();
    await page.waitForTimeout(300);

    const txt = await page.locator('#speed-label-mobile').innerText();
    if (txt !== '60×') throw new Error(`Expected 60x on ${name}, got ${txt}`);
    console.log(`✓ ${name} speed controls verified with 60×`);

    const outDir = path.join(__dirname, 'screenshots');
    const screenshotPath = path.join(outDir, `${name.toLowerCase().replace(/\s+/g, '_')}_replay.png`);
    await page.screenshot({ path: screenshotPath });
    console.log(`📸 Screenshot saved: ${screenshotPath}`);
    await context.close();
  }

  await browser.close();
  console.log('\n✅ ALL MOBILE REPLAY SPEED CONTROL CHECKS PASSED ON ALL RESOLUTIONS!');
}

runTest().catch(err => {
  console.error('❌ Test failed:', err);
  process.exit(1);
});
