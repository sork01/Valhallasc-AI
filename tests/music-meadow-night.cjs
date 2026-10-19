// Focused private-world check for Greenmeadow's own night remix and shared fallback.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-meadow-night-music', version: '1.0.0' });
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
  await page.locator('#name').fill('NightWander'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.zone === 0 && !!valhalla.fmusic?.running, null, { timeout: 60000 });

  await debug(page, { op: 'set_time', hour: 12, freeze: true });
  await page.waitForFunction(() => DayNight.nightMix === 0 && !valhalla.meadowNightMusic.running, null, { timeout: 10000 });
  assert.equal(await page.evaluate(() => valhalla.activeNightMusic === valhalla.meadowNightMusic), true);
  await debug(page, { op: 'set_time', hour: 19, freeze: true });
  await page.waitForFunction(() => Math.abs(DayNight.nightMix - .5) < .01 && valhalla.meadowNightMusic.running, null, { timeout: 10000 });
  assert.equal(await page.evaluate(() => valhalla.nightMusic.running), false, 'shared score stays out of Greenmeadow');
  await page.waitForFunction(() => valhalla.meadowNightMusic.loaded, null, { timeout: 30000 });
  const duration = await page.evaluate(() => valhalla.meadowNightMusic.duration);
  assert.ok(Math.abs(duration - 57.6) < .25, `Greenmeadow night MP3 duration ${duration}`);
  await debug(page, { op: 'set_time', hour: 0, freeze: true });
  await page.waitForFunction(() => DayNight.nightMix === 1 && valhalla.meadowNightMusic.running, null, { timeout: 10000 });
  await page.waitForFunction(() => valhalla.meadowNightMusic.output.gain.value > .95, null, { timeout: 10000 });
  await page.keyboard.press('n');
  await page.waitForFunction(() => valhalla.meadowNightMusic.output.gain.value < .01, null, { timeout: 10000 });
  await page.keyboard.press('n');
  await page.waitForFunction(() => valhalla.meadowNightMusic.output.gain.value > .95, null, { timeout: 10000 });

  await debug(page, { op: 'teleport', zone: 6, x: 9.5, y: 150 });
  await page.waitForFunction(() => Field.zone === 6 && valhalla.activeNightMusic === valhalla.nightMusic && valhalla.nightMusic.running && !valhalla.meadowNightMusic.running, null, { timeout: 10000 });
  await debug(page, { op: 'teleport', zone: 0, x: 36, y: 60 });
  await page.waitForFunction(() => Field.zone === 0 && valhalla.activeNightMusic === valhalla.meadowNightMusic && valhalla.meadowNightMusic.running && !valhalla.nightMusic.running, null, { timeout: 10000 });
  await debug(page, { op: 'set_time', hour: 12, freeze: true });
  await page.waitForFunction(() => DayNight.nightMix === 0 && !valhalla.meadowNightMusic.running, null, { timeout: 10000 });
  assert.deepEqual(errors, [], 'no browser errors');
  console.log('Greenmeadow night remix decodes, crossfades, follows mute, and yields to the shared score elsewhere');
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close().catch(() => {});
});
