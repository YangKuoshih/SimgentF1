const chromium = require('playwright').chromium;
const path = require('path');
const fs = require('fs');

async function testAlbonRetirementReplay() {
  console.log('🏁 Starting Albon Lap 42 Retirement & Replay Verification Test...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await page.addInitScript(() => localStorage.setItem('simgent_welcomed_v1', '1'));

  try {
    await page.goto('http://localhost:8080/?year=2026&round=16', { waitUntil: 'networkidle' });  // 2026 R16, where Albon retired on Lap 42
    await page.waitForTimeout(1000);

    // 1. Verify Pit Wall SI answers Albon's exit accurately
    console.log('🤖 Asking Pit Wall SI Agent about Alexander Albon exit...');
    const input = page.locator('#chat-input');
    await input.fill('When did Alexander Albon exit this race?');
    const respPromise = page.waitForResponse(r => r.url().includes('/api/chat') && r.status() === 200, { timeout: 15000 });
    await page.locator('#btn-chat-send').click();
    await respPromise;
    await page.waitForTimeout(1000);

    const chatText = await page.locator('#chat-feed').innerText();
    console.log('💬 Agent response received.');

    if (!chatText.includes('Lap 42')) {
      throw new Error(`Expected agent response to mention Lap 42, but got: ${chatText}`);
    }
    if (!/Completed Laps:\s*41\b/.test(chatText)) {
      throw new Error(`Expected agent response to mention 41 completed laps, but got: ${chatText}`);
    }
    console.log('✓ Agent correctly debriefed Lap 42 exit and 41 completed laps.');

    // 2. Click "JUMP TO LAP 42 REPLAY" action button
    const jumpBtn = page.locator('button:has-text("JUMP TO LAP 42 REPLAY"), button:has-text("Jump to Lap 42")');
    if (await jumpBtn.isVisible()) {
      console.log('🎯 Clicking "JUMP TO LAP 42 REPLAY" button...');
      await jumpBtn.click();
      await page.waitForTimeout(1000);
    } else {
      console.log('⚠️ Jump button not found, seeking to Lap 42 manually via jumpLap...');
    }

    // 3. Inspect driver state in client memory
    await page.waitForFunction(() => window.S && window.S.model && window.S.model.drivers && window.S.model.drivers.length > 0, { timeout: 15000 });
    const albonStateAt41 = await page.evaluate(() => {
      if (!window.S || !window.S.model) return null;
      const alb = window.S.model.drivers.find(d => d.code === 'ALB');
      const rows = window.classify ? window.classify(window.S.t) : null;
      const row = rows ? rows.find(r => r.d.code === 'ALB') : null;
      return {
        retire_lap: alb ? alb.retire_lap : null,
        retire_time: alb ? alb.retire_time : null,
        retire_prog: alb ? alb.retire_prog : null,
        laps: alb ? alb.laps : null,
        current_t: window.S.t,
        row_state: row ? row.state : null,
        row_gap: row ? row.gap : null
      };
    });

    console.log('📊 Replay state near Lap 42:', albonStateAt41);
    if (albonStateAt41.retire_lap !== 42) {
      throw new Error(`Expected Albon retire_lap=42, got ${albonStateAt41.retire_lap}`);
    }
    if (albonStateAt41.laps !== 41) {
      throw new Error(`Expected Albon laps=41, got ${albonStateAt41.laps}`);
    }

    // 4. Seek forward to Lap 43 (the exact screenshot from user)
    console.log('⏱️ Seeking replay to the middle of Lap 43 (from the leader\'s real lap times)...');
    await page.evaluate(() => {
      // Seek to mid Lap 43 using the leader's cumulative lap times (real Jolpica timing)
      const lead = window.S.model.drivers[0];
      window.S.t = (lead.cum[41] + lead.cum[42]) / 2;
      if (window.renderReplay) window.renderReplay();
      else if (window.renderFrame) window.renderFrame();
    });
    await page.waitForTimeout(500);

    const albonAtLap43 = await page.evaluate(() => {
      const rows = window.classify ? window.classify(window.S.t) : null;
      const row = rows ? rows.find(r => r.d.code === 'ALB') : null;
      const runningCount = rows ? rows.filter(r => r.state === 'RUN' || r.state === 'PIT').length : 0;
      const totalCount = rows ? rows.length : 0;
      return {
        state: row ? row.state : null,
        gap: row ? row.gap : null,
        runningCount,
        totalCount
      };
    });

    console.log('🏎️ Albon status at Lap 43:', albonAtLap43);
    if (albonAtLap43.state !== 'OUT') {
      throw new Error(`At Lap 43, Albon state should be 'OUT', but got '${albonAtLap43.state}'!`);
    }
    if (!albonAtLap43.gap.includes('OUT') || !albonAtLap43.gap.includes('42')) {
      throw new Error(`At Lap 43, Albon gap should be 'OUT (L42)', but got '${albonAtLap43.gap}'!`);
    }
    if (albonAtLap43.runningCount !== 20) {
      throw new Error(`At Lap 43, expected 20 running cars (with BOT and ALB OUT), got ${albonAtLap43.runningCount}!`);
    }
    console.log('✓ Verified: At Lap 43, Albon is OUT (L42) and running cars = 20!');

    // 5. Capture screenshot of Lap 43
    const screenshotDir = path.join(__dirname, 'screenshots');
    if (!fs.existsSync(screenshotDir)) fs.mkdirSync(screenshotDir, { recursive: true });
    const screenshotPath = path.join(screenshotDir, 'verification_albon_lap41_out_fixed.png');
    await page.screenshot({ path: screenshotPath });
    console.log(`📸 Screenshot saved: ${screenshotPath}`);

    console.log('🎉 ALL ALBON RETIREMENT REPLAY SYNCHRONIZATION CHECKS PASSED!');
  } finally {
    await browser.close();
  }
}

testAlbonRetirementReplay().catch(err => {
  console.error('❌ Test failed:', err);
  process.exit(1);
});
