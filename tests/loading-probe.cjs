// Diagnostic, not a gate: how long the loading screen stays up and what holds it. Run: bash scripts/test-touch-bounded.sh tests/loading-probe.cjs (REAL_SPRITES=1 for real art)
const fs = require('node:fs'), path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const root = path.resolve(__dirname, '..');
(async () => {
  const world = new TestWorld(root, { env: { VALHALLA_LEVEL_SPREAD: '0' } });
  await world.start();
  const browser = await chromium.launch({ headless: true });
  try {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    const page = await ctx.newPage();
    await page.addInitScript(() => { window.AudioContext = undefined; window.webkitAudioContext = undefined; localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {}, char: null, draft: null })); });
    await page.goto(world.url);
    await page.waitForFunction(() => window.LoadGate?.art.ready.length === 5, null, { timeout: 15000 });
    await page.locator('#start').click(); await page.locator('#login-guest').click(); await page.locator('#name').fill('Prober'); await page.locator('#go').click({ timeout: 60000 });
    const t0 = Date.now();
    for (let i = 0; i < 60; i++) {
      const s = await page.evaluate(() => ({ hidden: document.getElementById('connection-overlay').hidden, pending: LoadGate.pending, waiting: LoadGate.waiting.slice(0, 6) }));
      console.log(`${((Date.now() - t0) / 1000).toFixed(1)}s hidden=${s.hidden} pending=${s.pending} ${JSON.stringify(s.waiting)}`);
      if (s.hidden && i > 2) break;
      await page.waitForTimeout(1000);
    }
  } finally { await browser.close().catch(() => {}); await world.stop().catch(() => {}); }
})().catch(e => { console.error(e); process.exit(1); });
