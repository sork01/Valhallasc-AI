// Scratch helper: open the world map in a private world and screenshot it. WM_OUT=<dir> WM_VIEWS=1440x900,390x844 [WM_EXPLORED=0]
const path = require('node:path');
const fs = require('node:fs');
const { chromium } = require('./playwright.cjs');
const { TestWorld } = require('../../scripts/testing/driver.cjs');
(async () => {
  const out = process.env.WM_OUT || '/tmp';
  fs.mkdirSync(out, { recursive: true });
  const world = new TestWorld(); let browser;
  try {
    await world.start();
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: Number(process.env.WM_SCALE || 1), reducedMotion: 'reduce' });
    await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
    await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.locator('#cls-warrior').click(); await page.locator('#name').fill('MapShot'); await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero.id, null, { timeout: 60000 });
    if (process.env.WM_EXPLORED !== '0') {
      await page.evaluate(() => Online.send({ type: 'debug', ref: 5, command: { op: 'explore_all' } }));
      await page.waitForFunction(() => Object.values(Field.explored || {}).filter(Boolean).length > 20, null, { timeout: 15000 });
    }
    for (const view of (process.env.WM_VIEWS || '1440x900').split(',')) {
      const [w, h] = view.split('x').map(Number);
      await page.setViewportSize({ width: w, height: h });
      await page.evaluate(() => document.activeElement?.blur?.());
      await page.keyboard.press('m');
      await page.waitForSelector('#wm-world .wm-tile', { timeout: 10000 });
      await page.waitForTimeout(700);
      await page.screenshot({ path: path.join(out, `worldmap_${view}.png`) });
      await page.keyboard.press('Escape'); await page.waitForTimeout(200);
    }
    console.log('ok', out);
  } finally { await browser?.close(); await world.stop(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
