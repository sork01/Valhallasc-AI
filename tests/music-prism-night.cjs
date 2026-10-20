// Focused private-world playback check for the Prismwaste night remix.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-prism-night-music', version: '1.0.0' });
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
  await page.locator('#name').fill('SaltglassNight'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.zone === 0 && !!valhalla.fmusic?.running, null, { timeout: 60000 });
  await debug(page, { op: 'set_time', hour: 12, freeze: true });
  await debug(page, { op: 'teleport', zone: 14, x: 64, y: 116 });
  await page.waitForFunction(() => Field.zone === 14 && DayNight.nightMix === 0 && valhalla.pmusic.running && !valhalla.prismNightMusic.running, null, { timeout: 10000 });
  await debug(page, { op: 'set_time', hour: 19, freeze: true });
  await page.waitForFunction(() => Field.zone === 14 && Math.abs(DayNight.nightMix - .5) < .01 && valhalla.activeNightMusic === valhalla.prismNightMusic && valhalla.prismNightMusic.running, null, { timeout: 10000 });
  await page.waitForFunction(() => valhalla.prismNightMusic.loaded, null, { timeout: 30000 });
  assert.ok(Math.abs((await page.evaluate(() => valhalla.prismNightMusic.duration)) - 91.429) < .25);
  assert.equal(await page.evaluate(() => valhalla.nightMusic.running), false);

  await debug(page, { op: 'set_time', hour: 0, freeze: true });
  await page.waitForFunction(() => DayNight.nightMix === 1 && valhalla.prismNightMusic.output.gain.value > .95, null, { timeout: 10000 });
  await page.keyboard.press('n');
  await page.waitForFunction(() => valhalla.prismNightMusic.output.gain.value < .01, null, { timeout: 10000 });
  await page.keyboard.press('n');
  await page.waitForFunction(() => valhalla.prismNightMusic.output.gain.value > .95, null, { timeout: 10000 });

  await debug(page, { op: 'teleport', zone: 16, x: 12, y: 112 });
  await page.waitForFunction(() => Field.zone === 16 && valhalla.activeNightMusic === valhalla.moonsporeNightMusic && valhalla.moonsporeNightMusic.running && !valhalla.prismNightMusic.running, null, { timeout: 10000 });
  await debug(page, { op: 'teleport', zone: 15, x: 12, y: 112 });
  await page.waitForFunction(() => Field.zone === 15 && DayNight.nightMix === 0 && !valhalla.prismNightMusic.running, null, { timeout: 10000 });
  await debug(page, { op: 'teleport', zone: 14, x: 64, y: 116 });
  await debug(page, { op: 'set_time', hour: 6, freeze: true });
  await page.waitForFunction(() => Field.zone === 14 && Math.abs(DayNight.nightMix - .5) < .01 && valhalla.prismNightMusic.running, null, { timeout: 10000 });
  await debug(page, { op: 'set_time', hour: 12, freeze: true });
  await page.waitForFunction(() => Field.zone === 14 && DayNight.nightMix === 0 && !valhalla.prismNightMusic.running && valhalla.pmusic.running, null, { timeout: 10000 });
  assert.deepEqual(errors, [], 'no browser errors');
  console.log('Prismwaste night remix decodes, crossfades, mutes, keeps Orrery enclosed, and routes to Moonspore after travel');
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close().catch(() => {});
});
