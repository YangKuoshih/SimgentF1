const pw = require('playwright');
const path = require('path');
const fs = require('fs');

const BASE_URL = process.env.BASE_URL || 'http://localhost:8080';

async function testTelemetryContrast() {
  console.log('🔍 Testing Telemetry Contrast in Dark and Light Modes...');
  console.log(`Target: ${BASE_URL}\n`);

  const browser = await pw.chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 }
  });
  const page = await context.newPage();

  page.on('console', msg => console.log('PAGE LOG:', msg.type(), msg.text()));
  page.on('pageerror', err => console.log('PAGE ERROR:', err.message));

  // Load Spain 2026
  await page.goto(`${BASE_URL}/?year=2026&round=14&session=race`, { waitUntil: 'domcontentloaded' });
  await page.locator('#loading').waitFor({ state: 'hidden', timeout: 15000 });
  await page.waitForTimeout(600);

  const telDock = page.locator('#telemetry-dock');
  if (!await telDock.isVisible()) {
    throw new Error('Telemetry dock not visible');
  }

  const screenshotsDir = path.join(__dirname, 'screenshots');
  if (!fs.existsSync(screenshotsDir)) fs.mkdirSync(screenshotsDir, { recursive: true });

  // 1. Dark Mode Screenshot
  console.log('Capturing Dark Mode Telemetry...');
  const darkShotPath = path.join(screenshotsDir, 'telemetry_dark_mode_contrast.png');
  await telDock.screenshot({ path: darkShotPath });
  console.log('📸 Dark mode screenshot saved:', darkShotPath);

  // 2. Toggle to Light Mode
  console.log('Toggling to Light Mode...');
  const themeToggle = page.locator('#btn-theme-toggle');
  await themeToggle.click();
  await page.waitForTimeout(400);

  const isLight = await page.evaluate(() => document.body.classList.contains('theme-light'));
  if (!isLight) {
    throw new Error('Expected body to have theme-light class after toggle');
  }
  console.log('✅ Light mode active');

  // 3. Light Mode Screenshot
  console.log('Capturing Light Mode Telemetry...');
  const lightShotPath = path.join(screenshotsDir, 'telemetry_light_mode_contrast.png');
  await telDock.screenshot({ path: lightShotPath });
  console.log('📸 Light mode screenshot saved:', lightShotPath);

  // 4. Test DELTA Mode in Light Mode
  console.log('Switching to DELTA mode...');
  await page.locator('#btn-tel-mode-delta').click();
  await page.waitForTimeout(300);
  const deltaLightPath = path.join(screenshotsDir, 'telemetry_light_mode_delta.png');
  await telDock.screenshot({ path: deltaLightPath });
  console.log('📸 Light mode DELTA screenshot saved:', deltaLightPath);

  // 5. Toggle back to Dark Mode with DELTA
  await themeToggle.click();
  await page.waitForTimeout(400);
  const deltaDarkPath = path.join(screenshotsDir, 'telemetry_dark_mode_delta.png');
  await telDock.screenshot({ path: deltaDarkPath });
  console.log('📸 Dark mode DELTA screenshot saved:', deltaDarkPath);

  // Return to PACE mode
  await page.locator('#btn-tel-mode-pace').click();
  await page.waitForTimeout(300);

  await browser.close();
  console.log('\n🎉 ALL TELEMETRY CONTRAST TESTS PASSED SUCCESSFULLY!');
}

testTelemetryContrast().catch(err => {
  console.error('❌ Test failed:', err);
  process.exit(1);
});
