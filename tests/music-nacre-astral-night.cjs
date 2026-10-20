// Focused private-world playback check for Nacrehold and Astralhollow night music.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-nacre-astral-night-music', version: '1.0.0' });
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
  await page.locator('#name').fill('MoonGarden'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.zone === 0 && !!valhalla.fmusic?.running, null, { timeout: 60000 });
  await debug(page, { op: 'set_time', hour: 12, freeze: true });
  await debug(page, { op: 'teleport', zone: 9, x: 96, y: 174 });
  await page.waitForFunction(() => Field.zone === 9 && DayNight.nightMix === 0 && valhalla.nmusic.running && !valhalla.nacreNightMusic.running, null, { timeout: 10000 });
  await debug(page, { op: 'set_time', hour: 19, freeze: true });
  await page.waitForFunction(() => Field.zone === 9 && Math.abs(DayNight.nightMix - .5) < .01 && valhalla.activeNightMusic === valhalla.nacreNightMusic && valhalla.nacreNightMusic.running, null, { timeout: 10000 });
  await page.waitForFunction(() => valhalla.nacreNightMusic.loaded, null, { timeout: 30000 });
  assert.ok(Math.abs((await page.evaluate(() => valhalla.nacreNightMusic.duration)) - 64) < .25);
  assert.equal(await page.evaluate(() => valhalla.nightMusic.running), false);

  await debug(page, { op: 'set_time', hour: 0, freeze: true });
  await debug(page, { op: 'teleport', zone: 13, x: 64, y: 116 });
  await page.waitForFunction(() => Field.zone === 13 && DayNight.nightMix === 1 && valhalla.astralNightMusic.running && !valhalla.nacreNightMusic.running && valhalla.activeNightMusic === valhalla.astralNightMusic, null, { timeout: 10000 });
  await page.waitForFunction(() => valhalla.astralNightMusic.loaded, null, { timeout: 30000 });
  assert.ok(Math.abs((await page.evaluate(() => valhalla.astralNightMusic.duration)) - 100) < .25);
  await page.keyboard.press('n');
  await page.waitForFunction(() => valhalla.astralNightMusic.output.gain.value < .01, null, { timeout: 10000 });
  await page.keyboard.press('n');
  await page.waitForFunction(() => valhalla.astralNightMusic.output.gain.value > .95, null, { timeout: 10000 });

  await debug(page, { op: 'teleport', zone: 14, x: 64, y: 116 });
  await page.waitForFunction(() => Field.zone === 14 && valhalla.activeNightMusic === valhalla.prismNightMusic && valhalla.prismNightMusic.running && !valhalla.astralNightMusic.running, null, { timeout: 10000 });
  await debug(page, { op: 'teleport', zone: 8, x: 80, y: 160 });
  await page.waitForFunction(() => Field.zone === 8 && DayNight.nightMix === 0 && !valhalla.nacreNightMusic.running && !valhalla.astralNightMusic.running, null, { timeout: 10000 });
  await debug(page, { op: 'teleport', zone: 13, x: 64, y: 116 });
  await debug(page, { op: 'set_time', hour: 6, freeze: true });
  await page.waitForFunction(() => Field.zone === 13 && Math.abs(DayNight.nightMix - .5) < .01 && valhalla.astralNightMusic.running, null, { timeout: 10000 });
  await debug(page, { op: 'set_time', hour: 12, freeze: true });
  await page.waitForFunction(() => Field.zone === 13 && DayNight.nightMix === 0 && !valhalla.astralNightMusic.running && valhalla.amusic.running, null, { timeout: 10000 });
  assert.deepEqual(errors, [], 'no browser errors');
  console.log('Nacrehold and Astralhollow night remixes decode, crossfade, mute, keep enclosed zones quiet, and route to Prismwaste after travel');
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close().catch(() => {});
});
