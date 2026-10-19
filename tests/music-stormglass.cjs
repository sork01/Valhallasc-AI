// Focused private-world check for Stormglass Shore's own daytime score.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-stormglass-music', version: '1.0.0' });
let browser, started = false;
async function call(name, args = {}) {
  const reply = await client.callTool({ name, arguments: args });
  assert.ok(!reply.isError, `${name}: ${JSON.stringify(reply.content)}`);
  return reply.structuredContent;
}
const debug = (page, command) => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);

(async () => {
  const env = { ...getDefaultEnvironment(), ...(process.env.VALHALLA_BINARY ? { VALHALLA_BINARY: process.env.VALHALLA_BINARY } : {}) };
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: true, musicVol: 1 })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('ShoreBard'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!valhalla.fmusic?.running, null, { timeout: 60000 });
  await debug(page, { op: 'set_time', hour: 12, freeze: true });
  const spawn = await page.evaluate(() => WORLD_MAP.zones[18].spawn);
  await debug(page, { op: 'teleport', zone: 19, x: spawn.x, y: spawn.y });
  await page.waitForFunction(() => Field.zone === 19 && valhalla.stormglassMusic?.running && !valhalla.vmusic?.running, null, { timeout: 10000 });
  await page.waitForFunction(() => valhalla.stormglassMusic.loaded, null, { timeout: 30000 });
  const duration = await page.evaluate(() => valhalla.stormglassMusic.duration);
  assert.ok(Math.abs(duration - 80) < 1, `Stormglass MP3 duration ${duration}`);
  await debug(page, { op: 'set_time', hour: 0, freeze: true });
  await page.waitForFunction(() => DayNight.nightMix === 1 && valhalla.nightMusic?.running, null, { timeout: 10000 });
  assert.equal(await page.evaluate(() => valhalla.stormglassMusic.running), true, 'day score stays available for the dawn crossfade');
  await debug(page, { op: 'set_time', hour: 12, freeze: true });
  await page.waitForFunction(() => DayNight.nightMix === 0 && !valhalla.nightMusic.running, null, { timeout: 10000 });
  assert.deepEqual(errors, [], 'no browser errors');
  console.log('Stormglass score selects, decodes and follows the existing night mix');
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close().catch(() => {});
});
