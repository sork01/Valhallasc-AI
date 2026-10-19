// Focused private-world check for the two new zone night remixes.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-two-night-music', version: '1.0.0' });
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
  await page.locator('#name').fill('FrostEmber'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.zone === 0 && !!valhalla.fmusic?.running, null, { timeout: 60000 });
  await debug(page, { op: 'set_time', hour: 12, freeze: true });
  await debug(page, { op: 'teleport', zone: 1, x: 48, y: 86.5 });
  await page.waitForFunction(() => Field.zone === 1 && DayNight.nightMix === 0 && valhalla.cmusic.running && !valhalla.cragsNightMusic.running, null, { timeout: 10000 });
  await debug(page, { op: 'set_time', hour: 19, freeze: true });
  await page.waitForFunction(() => Field.zone === 1 && Math.abs(DayNight.nightMix - .5) < .01 && valhalla.activeNightMusic === valhalla.cragsNightMusic && valhalla.cragsNightMusic.running, null, { timeout: 10000 });
  await page.waitForFunction(() => valhalla.cragsNightMusic.loaded, null, { timeout: 30000 });
  assert.ok(Math.abs((await page.evaluate(() => valhalla.cragsNightMusic.duration)) - 83.48) < .25);
  assert.equal(await page.evaluate(() => valhalla.nightMusic.running), false);

  await debug(page, { op: 'set_time', hour: 0, freeze: true });
  await debug(page, { op: 'teleport', zone: 2, x: 64, y: 118.5 });
  await page.waitForFunction(() => Field.zone === 2 && DayNight.nightMix === 1 && valhalla.rimeNightMusic.running && !valhalla.cragsNightMusic.running && valhalla.activeNightMusic === valhalla.rimeNightMusic, null, { timeout: 10000 });
  await page.waitForFunction(() => valhalla.rimeNightMusic.loaded, null, { timeout: 30000 });
  assert.ok(Math.abs((await page.evaluate(() => valhalla.rimeNightMusic.duration)) - 65.45) < .25);
  await page.keyboard.press('n');
  await page.waitForFunction(() => valhalla.rimeNightMusic.output.gain.value < .01, null, { timeout: 10000 });
  await page.keyboard.press('n');
  await page.waitForFunction(() => valhalla.rimeNightMusic.output.gain.value > .95, null, { timeout: 10000 });

  await debug(page, { op: 'teleport', zone: 6, x: 9.5, y: 150 });
  await page.waitForFunction(() => Field.zone === 6 && valhalla.activeNightMusic === valhalla.nightMusic && valhalla.nightMusic.running && !valhalla.rimeNightMusic.running, null, { timeout: 10000 });
  await debug(page, { op: 'teleport', zone: 2, x: 64, y: 118.5 });
  await debug(page, { op: 'set_time', hour: 12, freeze: true });
  await page.waitForFunction(() => Field.zone === 2 && DayNight.nightMix === 0 && !valhalla.rimeNightMusic.running && valhalla.rmusic.running, null, { timeout: 10000 });
  assert.deepEqual(errors, [], 'no browser errors');
  console.log('Crags and Rimeveil night remixes decode, crossfade, mute, and return to the shared fallback');
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close().catch(() => {});
});
