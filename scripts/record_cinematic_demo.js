#!/usr/bin/env node
/**
 * scripts/record_cinematic_demo.js
 * 
 * Records an authentic, feature-packed cinematic video demo of F1 Simgent:
 * 1. Opens 2024 Round 3 (Australian GP) replay cockpit.
 * 2. Starts live replay playback (cars racing on track).
 * 3. Collapses Driver Telemetry Card and Circuit Intel HUD so racetrack is 100% unobstructed.
 * 4. Toggles Light Mode and switches back to Dark Mode.
 * 5. Asks the SI Pit Wall Radio: "Why did Hamilton retire in Australia 2024?"
 * 6. Clicks the synthesized Tactical Action Card ("JUMP TO LAP 17 REPLAY") to trigger incident scrub.
 * 7. Explores Strategy Lab tab (Monte Carlo simulation) and Pit Wall SI terminal tab.
 * 8. Returns to Race Replay with clean, unobstructed telemetry.
 */

const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');

function addGlobalModulePath() {
  try {
    const globalRoot = execSync('npm root -g', { encoding: 'utf8' }).trim();
    if (globalRoot && fs.existsSync(globalRoot) && !module.paths.includes(globalRoot)) {
      module.paths.unshift(globalRoot);
    }
  } catch (e) {}
}
addGlobalModulePath();

const { chromium } = require('playwright');

function loadFrameAssets() {
  const dir = path.join(__dirname, '..', 'build-with-gemini', '.agents', 'skills', 'record-demo', 'assets');
  try {
    return {
      css: fs.readFileSync(path.join(dir, 'overlay.css'), 'utf8'),
      logo: fs.readFileSync(path.join(dir, 'logo.svg'), 'utf8'),
    };
  } catch (e) {
    return null;
  }
}

async function injectFrame(page, { title, assets }) {
  if (!assets) return;
  try {
    await page.evaluate(({ title, css, logo }) => {
      if (!document.getElementById('gwt-overlay-style')) {
        const style = document.createElement('style');
        style.id = 'gwt-overlay-style';
        style.textContent = css;
        (document.head || document.documentElement).appendChild(style);
      }
      if (!document.getElementById('gwt-frame')) {
        const frame = document.createElement('div');
        frame.id = 'gwt-frame';
        const badge = document.createElement('div');
        badge.id = 'gwt-badge';
        badge.innerHTML = logo;
        const label = document.createElement('span');
        label.textContent = title;
        badge.appendChild(label);
        frame.appendChild(badge);
        document.documentElement.appendChild(frame);
      }
    }, { title, css: assets.css, logo: assets.logo });
  } catch (e) {}
}

(async () => {
  const tempDir = path.join(process.cwd(), '.video_tmp');
  if (fs.existsSync(tempDir)) {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
  fs.mkdirSync(tempDir, { recursive: true });

  const targetUrl = 'http://127.0.0.1:8080/?year=2024&round=3';
  const outputFile = path.join(process.cwd(), 'f1_simgent_demo.webm');
  const viewport = { width: 1600, height: 1000 };
  const assets = loadFrameAssets();
  const title = 'SimGent — Autonomous SI Race Engineer & Telemetry Cockpit';

  console.log('--- Launching Playwright Chromium Browser ---');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport,
    recordVideo: { dir: tempDir, size: viewport },
  });

  const page = await context.newPage();
  console.log(`Navigating to ${targetUrl}...`);
  await page.goto(targetUrl, { waitUntil: 'networkidle', timeout: 30000 });
  await injectFrame(page, { title, assets });
  await page.waitForTimeout(2000);

  // 1. Start Replay Playback
  console.log('1. Starting replay playback...');
  const playBtn = page.locator('#btn-play');
  if (await playBtn.isVisible()) {
    await playBtn.click();
  }
  await page.waitForTimeout(2500);

  // 2. Collapse Driver Card to clear track view
  console.log('2. Collapsing Driver Telemetry Card to unblock track...');
  const collapseFc = page.locator('#fc-toggle-collapse');
  if (await collapseFc.isVisible()) {
    await collapseFc.click();
  }
  await page.waitForTimeout(1500);

  // 3. Collapse Track Intel HUD to clear upper track view
  console.log('3. Collapsing Circuit Intel HUD to unblock full circuit...');
  const collapseTi = page.locator('#tic-toggle-collapse');
  if (await collapseTi.isVisible()) {
    await collapseTi.click();
  }
  await page.waitForTimeout(2500);

  // 4. Switch between Light Mode and Dark Mode
  console.log('4. Demonstrating Light Mode...');
  const themeToggle = page.locator('#btn-theme-toggle');
  if (await themeToggle.isVisible()) {
    await themeToggle.click();
    await page.waitForTimeout(2500);
    console.log('   Switching back to Dark Mode...');
    await themeToggle.click();
    await page.waitForTimeout(1500);
  }

  // 5. Ask Pit Wall Radio about Hamilton's Australian GP retirement
  console.log('5. Transmitting incident inquiry to Pit Wall Radio...');
  const chatInput = page.locator('#chat-input');
  if (await chatInput.isVisible()) {
    await chatInput.click();
    await chatInput.pressSequentially('Why did Hamilton retire in Australia 2024?', { delay: 45 });
    await page.waitForTimeout(600);
    const sendBtn = page.locator('#btn-chat-send');
    await sendBtn.click();
    console.log('   Waiting for SI Race Engineer telemetry response & action card...');
    await page.waitForTimeout(4000);
  }

  // 6. Click Tactical Replay Action Card
  console.log('6. Triggering Tactical Action Card (Jump to Lap 17 Replay)...');
  const actionCardBtn = page.locator('.a2ui-card-btn').first();
  if (await actionCardBtn.isVisible()) {
    await actionCardBtn.click();
    await page.waitForTimeout(3500); // observe telemetry jump & race control banner
  }

  // 7. Tour Strategy Lab Tab
  console.log('7. Exploring Strategy Lab Tab...');
  const strategyTab = page.locator('button[data-tab="strategy"]');
  if (await strategyTab.isVisible()) {
    await strategyTab.click();
    await injectFrame(page, { title, assets });
    await page.waitForTimeout(1500);
    const simBtn = page.locator('#btn-run-sim');
    if (await simBtn.isVisible()) {
      await simBtn.click();
      await page.waitForTimeout(2500);
    }
  }

  // 8. Tour Pit Wall SI Terminal Tab
  console.log('8. Exploring Pit Wall SI Terminal Tab...');
  const aiTab = page.locator('button[data-tab="playground"]');
  if (await aiTab.isVisible()) {
    await aiTab.click();
    await injectFrame(page, { title, assets });
    await page.waitForTimeout(2000);
    const testCard = page.locator('.pg-test-card').first();
    if (await testCard.isVisible()) {
      await testCard.click();
      await page.waitForTimeout(3000);
    }
  }

  // 9. Return to Race Replay tab with full unobstructed racetrack
  console.log('9. Returning to Race Replay view...');
  const raceTab = page.locator('button[data-tab="race"]');
  if (await raceTab.isVisible()) {
    await raceTab.click();
    await injectFrame(page, { title, assets });
    await page.waitForTimeout(3000);
  }

  console.log('Finalizing video recording...');
  await page.close();
  await context.close();
  await browser.close();

  const files = fs.readdirSync(tempDir).filter(f => f.endsWith('.webm'));
  if (files.length === 0) {
    console.error('ERROR: No webm file recorded.');
    process.exit(1);
  }

  const srcPath = path.join(tempDir, files[0]);
  fs.copyFileSync(srcPath, outputFile);
  console.log(`SUCCESS: Video saved to ${outputFile} (${(fs.statSync(outputFile).size / (1024 * 1024)).toFixed(2)} MB)`);
  fs.rmSync(tempDir, { recursive: true, force: true });
})();
