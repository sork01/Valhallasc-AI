const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-daynight-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, label) => { assert.ok(value, label); checks++; };
async function call(name, args = {}) {
  const reply = await client.callTool({ name, arguments: args });
  assert.ok(!reply.isError, `${name}: ${JSON.stringify(reply.content)}`);
  return reply.structuredContent;
}

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment() } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => { localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })); });
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('Clockwatcher'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!window.DayNight && DayNight.hour >= 0, null, { timeout: 60000 });
  check(await page.locator('#world-clock').isVisible(), 'the HUD has a visible world clock');

  await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'set_time', hour: 23.5, freeze: true } }));
  await page.waitForFunction(() => Math.abs(DayNight.hour - 23.5) < .01 && document.querySelector('#world-clock').textContent.includes('23:30'), null, { timeout: 10000 });
  check(true, 'the server frozen hour reaches the HUD');
  check(await page.locator('#world-clock').getAttribute('title').then(t => t.includes('Night') && t.includes('20 minutes')), 'the tooltip explains the phase and cycle');
  const zones = await page.evaluate(() => [
    DayNight.isOutdoor({ theme: 'meadow' }), DayNight.isOutdoor(WORLD_MAP.zones[0]),
    DayNight.isOutdoor(WORLD_MAP.zones[4]), DayNight.isOutdoor(WORLD_MAP.zones[14]),
    DayNight.isOutdoor(WORLD_MAP.zones[25]), DayNight.isOutdoor(WORLD_MAP.zones[27]),
  ]);
  check(JSON.stringify(zones) === JSON.stringify([true, true, false, false, true, true]), `outdoor and enclosed zone data: ${zones}`);

  const pixels = await page.evaluate(() => {
    const sample = (h, setting) => {
      Prefs.set({ night: setting }); DayNight.setZone({ theme: 'meadow' });
      DayNight.sync({ hour: h, hoursPerSecond: 0 }); DayNight.tick(20);
      const canvas = document.createElement('canvas'); canvas.width = 200; canvas.height = 120;
      const g = canvas.getContext('2d'); g.fillStyle = '#a0b0a0'; g.fillRect(0, 0, 200, 120);
      DayNight.draw(g, 200, 120, [], () => [0, 0]);
      return [...g.getImageData(100, 85, 1, 1).data].slice(0, 3);
    };
    return { noon: sample(12, 1), midnight: sample(0, 1), off: sample(0, 0) };
  });
  check(pixels.midnight[0] < pixels.noon[0] && pixels.midnight[1] < pixels.noon[1], `midnight tint darkens the world: ${JSON.stringify(pixels)}`);
  check(JSON.stringify(pixels.off) === JSON.stringify(pixels.noon), 'the night darkening setting can remove the tint');

  await page.keyboard.press('Escape'); await page.locator('#p-settings').click();
  check(await page.locator('#set-night').inputValue() === '0', 'the settings panel reads the saved night slider');
  await page.locator('#set-night').fill('50');
  check(await page.locator('#set-night-out').textContent() === '50%' && await page.evaluate(() => JSON.parse(localStorage.getItem('valhallasc.save.v1')).night) === .5, 'the slider saves a reduced tint');
  await page.keyboard.press('Escape'); await page.keyboard.press('Escape');
  await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 5, x: 36, y: 52 } }));
  await page.waitForFunction(() => Field.zone === 5 && !DayNight.isOutdoor(WORLD_MAP.zones[4]), null, { timeout: 10000 });
  await page.waitForFunction(() => document.querySelector('#world-clock').title.includes('indoor light'), null, { timeout: 3000 });
  check(await page.locator('#world-clock').getAttribute('title').then(t => t.includes('indoor light')), 'the dungeon reports fixed indoor light');
  await page.waitForFunction(() => DayNight.outdoorBlend < .15, null, { timeout: 5000 });
  check(true, 'the outdoor tint fades away inside the dungeon');
  await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 0, x: 36, y: 60 } }));
  await page.waitForFunction(() => Field.zone === 0 && DayNight.outdoorBlend > .7, null, { timeout: 5000 });
  check(true, 'the outdoor tint fades back in on return');
  check(errors.length === 0, `no browser errors: ${errors.join('; ')}`);
  console.log(`${checks} day/night browser checks passed`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  if (browser) await browser.close();
  if (started) { try { await call('stop_world'); } catch (_) {} }
  await client.close();
});
