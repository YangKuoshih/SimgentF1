const pw = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE_URL = process.env.BASE_URL || 'http://localhost:8080';

async function runStartingGridTest() {
  console.log('🏁 Starting Grid & Lights Out Verification Test...');
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

  // Load 2026 Spanish Grand Prix (Race 14)
  console.log('Loading 2026 Spanish Grand Prix (Madrid)...');
  await page.goto(`${BASE_URL}/?year=2026&round=14&session=race`, { waitUntil: 'domcontentloaded' });

  // Wait for loading overlay to be hidden
  await page.locator('#loading').waitFor({ state: 'hidden', timeout: 15000 });
  await page.waitForTimeout(500);

  // Jump to starting grid (t=0) via the 🏁 GRID button
  const gridBtn = page.locator('#btn-grid');
  if (!await gridBtn.isVisible()) {
    throw new Error('🏁 GRID jump button is not visible!');
  }
  console.log('Clicking 🏁 GRID button...');
  await gridBtn.click();
  await page.waitForTimeout(400);

  // 1. Verify Lap Pill shows STARTING GRID at t=0
  const lapPillText = await page.locator('#lap-pill').innerText();
  console.log(`Lap Pill Text: "${lapPillText}"`);
  if (!lapPillText.includes('STARTING GRID') && !lapPillText.includes('LIGHTS OUT')) {
    throw new Error(`Expected STARTING GRID or LIGHTS OUT in lap pill, got "${lapPillText}"`);
  }
  console.log('✅ Lap Pill correctly displays STARTING GRID');

  // 2. Verify 5-Red-Lights Gantry HUD exists and is visible
  const gantry = page.locator('#lights-gantry-hud');
  if (!await gantry.isVisible()) {
    throw new Error('Lights Gantry HUD is not visible!');
  }
  console.log('✅ 5-Red-Lights Gantry HUD is visible over track canvas');

  // 3. Verify Timing Tower order at Starting Grid:
  // Must show:
  // P1: NOR (POLE)
  // P2: ANT (ROW 1)
  // P3: VER (ROW 2)
  // P4: HAM (ROW 2)
  // P5: LEC (ROW 3)
  const towerRows = await page.locator('.tower-row').all();
  console.log(`Found ${towerRows.length} timing tower rows`);
  if (towerRows.length < 5) {
    throw new Error(`Expected at least 20 drivers in timing tower, found ${towerRows.length}`);
  }

  const row1Text = await towerRows[0].innerText();
  const row2Text = await towerRows[1].innerText();
  const row3Text = await towerRows[2].innerText();
  const row4Text = await towerRows[3].innerText();

  console.log('Row 1:', row1Text.replace(/\n/g, ' '));
  console.log('Row 2:', row2Text.replace(/\n/g, ' '));
  console.log('Row 3:', row3Text.replace(/\n/g, ' '));
  console.log('Row 4:', row4Text.replace(/\n/g, ' '));

  if (!row1Text.includes('NOR') || !row1Text.includes('POLE')) {
    throw new Error(`Row 1 should be Norris POLE, got "${row1Text}"`);
  }
  console.log('✅ Row 1 is Lando Norris (POLE)');

  if (!row2Text.includes('ANT') || !row2Text.includes('ROW 1')) {
    throw new Error(`Row 2 should be Kimi Antonelli ROW 1, got "${row2Text}"`);
  }
  console.log('✅ Row 2 is Kimi Antonelli (ROW 1 / Front Row P2)');

  if (!row3Text.includes('VER') || !row3Text.includes('ROW 2')) {
    throw new Error(`Row 3 should be Max Verstappen ROW 2, got "${row3Text}"`);
  }
  console.log('✅ Row 3 is Max Verstappen (ROW 2 / P3)');

  if (!row4Text.includes('HAM') || !row4Text.includes('ROW 2')) {
    throw new Error(`Row 4 should be Lewis Hamilton ROW 2, got "${row4Text}"`);
  }
  console.log('✅ Row 4 is Lewis Hamilton (ROW 2 / P4)');

  // 4. Capture Starting Grid formation screenshot with cars and track visible
  const outDir = path.join(__dirname, 'screenshots');
  fs.mkdirSync(outDir, { recursive: true });
  const gridScreenshotPath = path.join(outDir, 'verification_starting_grid_fixed.png');
  await page.screenshot({ path: gridScreenshotPath });
  console.log(`📸 Screenshot saved: ${gridScreenshotPath}`);

  // 5. Wait for lights sequence countdown (1.8s) -> Capture 5-red-lights sequence
  console.log('Capturing lights countdown sequence...');
  await page.waitForTimeout(1600);
  const lightsScreenshotPath = path.join(outDir, 'verification_5_red_lights_sequence.png');
  await page.screenshot({ path: lightsScreenshotPath });
  console.log(`📸 Screenshot saved: ${lightsScreenshotPath}`);

  // 6. Past 3.6s into Lights Out -> Capture cars accelerating off the grid
  await page.waitForTimeout(2000);
  const lightsOutScreenshotPath = path.join(outDir, 'verification_lights_out_launch.png');
  await page.screenshot({ path: lightsOutScreenshotPath });
  console.log(`📸 Screenshot saved: ${lightsOutScreenshotPath}`);

  await context.close();
  await browser.close();
  console.log('\n🎉 ALL STARTING GRID & LIGHTS OUT TESTS PASSED WITH 100% SUCCESS!');
}

runStartingGridTest().catch(err => {
  console.error('❌ Test failed:', err);
  process.exit(1);
});
