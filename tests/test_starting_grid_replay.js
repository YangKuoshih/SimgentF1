const chromium = require('playwright').chromium;
const path = require('path');
const fs = require('fs');

async function testStartingGridReplay() {
  console.log('🏁 Starting Grid Replay Verification Test...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  try {
    await page.goto('http://localhost:8080', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    // Ensure replay model is loaded
    await page.waitForFunction(() => window.S && window.S.model && window.S.model.drivers && window.S.model.drivers.length > 0, { timeout: 15000 });

    // Inspect drivers at t = 0 (on the grid before start)
    const gridRows = await page.evaluate(() => {
      window.S.t = 0;
      if (window.renderReplay) window.renderReplay();
      const rows = window.classify ? window.classify(0) : [];
      return rows.map(r => ({
        pos: r.pos,
        code: r.d.code,
        grid: r.d.grid,
        gap: r.gap
      }));
    });

    console.log('📊 Starting Grid Classification (t = 0):');
    gridRows.slice(0, 10).forEach(r => console.log(`  P${r.pos}: ${r.code} (Grid ${r.grid}) - ${r.gap}`));

    // Assert Top 7 grid order
    if (gridRows[0].code !== 'VER' || gridRows[0].grid !== 1) {
      throw new Error(`P1 expected VER (grid 1), got ${gridRows[0].code} (grid ${gridRows[0].grid})`);
    }
    if (gridRows[1].code !== 'HAM' || gridRows[1].grid !== 2) {
      throw new Error(`P2 expected HAM (grid 2), got ${gridRows[1].code} (grid ${gridRows[1].grid})`);
    }
    if (gridRows[2].code !== 'ANT' || gridRows[2].grid !== 3) {
      throw new Error(`P3 expected ANT (grid 3), got ${gridRows[2].code} (grid ${gridRows[2].grid})`);
    }
    if (gridRows[3].code !== 'LEC' || gridRows[3].grid !== 4) {
      throw new Error(`P4 expected LEC (grid 4), got ${gridRows[3].code} (grid ${gridRows[3].grid})`);
    }
    if (gridRows[4].code !== 'NOR' || gridRows[4].grid !== 5) {
      throw new Error(`P5 expected NOR (grid 5), got ${gridRows[4].code} (grid ${gridRows[4].grid})`);
    }
    if (gridRows[5].code !== 'PIA' || gridRows[6].grid !== 7) {
      throw new Error(`P6 expected PIA, P7 expected RUS`);
    }
    if (gridRows[6].code !== 'RUS' || gridRows[6].grid !== 7) {
      throw new Error(`P7 expected RUS (grid 7), got ${gridRows[6].code} (grid ${gridRows[6].grid})`);
    }

    console.log('✓ Starting grid at t = 0 matches official 2026 Bahrain GP grid!');

    // Check Lap 1 order (t = 50s, mid Lap 1)
    const lap1Rows = await page.evaluate(() => {
      window.S.t = 50;
      if (window.renderReplay) window.renderReplay();
      const rows = window.classify ? window.classify(50) : [];
      return rows.map(r => ({
        pos: r.pos,
        code: r.d.code,
        grid: r.d.grid,
        gap: r.gap
      }));
    });

    console.log('📊 Lap 1 Race Classification (t = 50s):');
    lap1Rows.slice(0, 10).forEach(r => console.log(`  P${r.pos}: ${r.code} (Grid ${r.grid}) - ${r.gap}`));

    const rusLap1 = lap1Rows.find(r => r.code === 'RUS');
    if (!rusLap1) throw new Error('Russell not found in Lap 1 rows');
    if (rusLap1.pos > 10) {
      throw new Error(`Russell anomaly! Position on Lap 1 is P${rusLap1.pos}, expected front group!`);
    }
    console.log(`✓ Russell on Lap 1 is running in P${rusLap1.pos} (NOT P20)!`);

    // Capture screenshot
    const shotPath = path.join(__dirname, 'screenshots', 'verification_starting_grid_fixed.png');
    await page.screenshot({ path: shotPath, fullPage: true });
    console.log('📸 Screenshot saved to:', shotPath);

    console.log('🎉 ALL STARTING GRID VERIFICATION CHECKS PASSED!');
  } finally {
    await browser.close();
  }
}

testStartingGridReplay().catch(err => {
  console.error('❌ Test failed:', err);
  process.exit(1);
});
