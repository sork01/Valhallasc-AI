// Windows, the quest tracker and the chat resize only while Edit UI is on (Beta 1.55.2), Edit UI opens a window from its picker,
// and a fresh layout puts the DPS meter at the far right. Run: bash scripts/test-touch-bounded.sh tests/edit-only-resize-ui.cjs
// MUTATE=1 serves the previous settings.js (grips always on outside Edit UI) and must fail.
const assert = require('node:assert/strict');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-edit-only-resize', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`); return result.structuredContent;
}
const KEY = 'valhallasc.save.v1';
const stored = page => page.evaluate(k => JSON.parse(localStorage.getItem(k) || '{}'), KEY);
const rect = (page, selector) => page.locator(selector).evaluate(n => { const r = n.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom, w: r.width, h: r.height, cx: r.left + r.width / 2, cy: r.top + r.height / 2 }; });
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment() } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  if (process.env.MUTATE === '1') {
    const old = execFileSync('git', ['show', 'HEAD:client/settings.js'], { cwd: root, maxBuffer: 1 << 26 }).toString();
    await page.route(/\/settings\.js(\?.*)?$/, route => route.fulfill({ contentType: 'text/javascript', body: old }));
  }
  await page.addInitScript(() => {
    if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1'); localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })); }
  });
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-mage').click(); await page.locator('#name').fill('Editor'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.mageSprites, null, { timeout: 60000 });
  const stage = await rect(page, '#stage');

  // --- default DPS meter position: the far right, same height ---
  await page.evaluate(() => { document.getElementById('dps-meter').hidden = false; Settings.refresh(); });
  const dps = await rect(page, '#dps-meter');
  check(stage.r - dps.r < stage.w * .02, `The DPS meter starts at the far right (${(stage.r - dps.r).toFixed(1)} px from the edge)`);
  check(Math.abs(dps.b - (stage.b - stage.h * .11)) < stage.h * .1, 'At its old height');

  // --- outside Edit UI: windows and panels have no grips ---
  await page.keyboard.press('k');
  check(await page.locator('#skills-panel').isVisible(), 'K opens the skills window');
  check(await page.locator('.win-grip:visible').count() === 0, 'An open window has no resize grip outside Edit UI');
  check(await page.locator('.panel-grip:visible').count() === 0, 'The quest tracker and chat have no resize grips either');
  await page.keyboard.press('Escape');

  // --- inside Edit UI ---
  await page.keyboard.press('Escape'); await page.locator('#p-settings').click(); await page.locator('#set-edit-ui').click();
  check(await page.evaluate(() => Settings.editing), 'Edit UI is on');
  check(await page.locator('.panel-grip:visible').count() === 2, 'The tracker and chat grips show in Edit UI');
  check(await page.locator('.win-grip:visible').count() === 0, 'No window is open yet, so no window grip');
  await page.locator('#layout-window').selectOption('skills-panel');
  check(await page.evaluate(() => Settings.editing), 'Opening a window from the picker keeps Edit UI on');
  check(await page.locator('#skills-panel').isVisible(), 'The picked window opens');
  const grip = page.locator('.win-grip[aria-label^="Resize Skills"]');
  check(await grip.isVisible(), 'And has its resize grip');
  const win0 = await rect(page, '#skills-panel .skills-panel'), g0 = await rect(page, '.win-grip[aria-label^="Resize Skills"]');
  await page.mouse.move(g0.cx, g0.cy); await page.mouse.down(); await page.mouse.move(win0.cx + (g0.cx - win0.cx) * .6, win0.cy + (g0.cy - win0.cy) * .6, { steps: 8 }); await page.mouse.up();
  const win1 = await rect(page, '#skills-panel .skills-panel');
  check(win1.w < win0.w * .8, `Dragging the grip resizes the window (${win0.w.toFixed(0)} -> ${win1.w.toFixed(0)})`);
  check((await stored(page)).winScale?.['skills-panel'] < 1, 'The new size is saved');
  await page.locator('#layout-window').selectOption('worldmap');
  check(await page.locator('#skills-panel').isHidden() && await page.locator('#worldmap').isVisible(), 'Picking another window swaps the preview');
  await page.locator('#layout-window').selectOption('');
  check(await page.locator('#worldmap').isHidden(), 'The empty choice closes the preview');
  await page.locator('#layout-window').selectOption('equipment');
  check(await page.locator('.win-grip[aria-label^="Resize Character and bags"]').isVisible(), 'The Character window has its grip');
  await page.locator('#layout-done').click();
  check(await page.locator('#equipment').isHidden() && await page.locator('.win-grip:visible').count() === 0, 'Done closes the preview and the grips go');
  check(await page.locator('.panel-grip:visible').count() === 0, 'Panel grips go too');
  await page.locator('#set-back').click(); await page.locator('#p-resume').click();
  await page.keyboard.press('k');
  const win2 = await rect(page, '#skills-panel .skills-panel');
  check(Math.abs(win2.w - win1.w) < 2, `The size set in Edit UI is what the window opens at (${win2.w.toFixed(0)})`);
  check(errors.length === 0, `No page errors: ${errors.join('; ')}`);
  console.log(`${checks} edit-only resize checks passed`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
