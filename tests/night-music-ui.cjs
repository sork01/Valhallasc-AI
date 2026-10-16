const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-night-music-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (ok, label) => { assert.ok(ok, label); checks++; };
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
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: true, musicVol: 1 })));
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('Night Listener'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && valhalla.fmusic?.running && valhalla.nightMusic, null, { timeout: 60000 });
  const setTime = async hour => {
    await page.evaluate(h => Online.send({ type: 'debug', command: { op: 'set_time', hour: h, freeze: true } }), hour);
    await page.waitForFunction(h => Math.abs(DayNight.hour - h) < .01, hour, { timeout: 10000 });
  };
  const levels = () => page.evaluate(() => ({ day: valhalla.fmusic.output.gain.value, night: valhalla.nightMusic.output.gain.value }));
  await setTime(12);
  await page.waitForFunction(() => !valhalla.nightMusic.running && valhalla.fmusic.output.gain.value > .9, null, { timeout: 10000 });
  check(true, 'daylight plays the zone score alone');
  await setTime(19);
  await page.waitForFunction(() => valhalla.nightMusic.running && DayNight.nightMix > .49 && DayNight.nightMix < .51, null, { timeout: 10000 });
  await page.waitForTimeout(2000);
  const dusk = await levels();
  check(dusk.day > .3 && dusk.day < .7 && dusk.night > .3 && dusk.night < .7, `dusk crossfade: ${JSON.stringify(dusk)}`);
  await setTime(22);
  await page.waitForFunction(() => valhalla.nightMusic.loaded && valhalla.nightMusic.output.gain.value > .9 && valhalla.fmusic.output.gain.value < .1, null, { timeout: 30000 });
  check(true, 'night plays the decoded nocturne');
  await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 1, x: 48, y: 86.5 } }));
  await page.waitForFunction(() => Field.zone === 1 && valhalla.cmusic.running && !valhalla.fmusic.running && valhalla.nightMusic.running, null, { timeout: 10000 });
  check(true, 'the nocturne follows the player between outdoor zones');
  await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 5, x: 36, y: 52 } }));
  await page.waitForFunction(() => Field.zone === 5 && !valhalla.nightMusic.running && DayNight.nightMix === 0 && valhalla.vmusic.running && valhalla.vmusic.output.gain.value > .8, null, { timeout: 10000 });
  check(true, 'enclosed zone keeps its normal score at night');
  await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 0, x: 36, y: 60 } }));
  await page.waitForFunction(() => Field.zone === 0 && valhalla.nightMusic.running, null, { timeout: 10000 });
  check(true, 'the outdoor nocturne returns after leaving the enclosure');
  await setTime(6);
  await page.waitForTimeout(2000);
  const dawn = await levels();
  check(dawn.day > .3 && dawn.day < .7 && dawn.night > .3 && dawn.night < .7, `dawn crossfade: ${JSON.stringify(dawn)}`);
  await setTime(8);
  await page.waitForFunction(() => !valhalla.nightMusic.running && valhalla.fmusic.output.gain.value > .9, null, { timeout: 10000 });
  check(true, 'the normal zone score returns after dawn');
  check(errors.length === 0, `no browser errors: ${errors.join('; ')}`);
  console.log(`${checks} night music browser checks passed`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  if (browser) await browser.close();
  if (started) { try { await call('stop_world'); } catch (_) {} }
  await client.close();
});
