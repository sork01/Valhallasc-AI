// Focused private-world playback check for four new outdoor night remixes.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-next-four-night-music', version: '1.0.0' });
const songs = [
  { zone: 16, x: 16, y: 112, key: 'moonsporeNightMusic', day: 'mmusic', seconds: 32 * 3 * 60 / 82 },
  { zone: 17, x: 90, y: 162, key: 'asterionNightMusic', day: 'hmusic', seconds: 32 * 4 * 60 / 92 },
  { zone: 19, x: 13, y: 105, key: 'stormglassNightMusic', day: 'stormglassMusic', seconds: 32 * 4 * 60 / 88 },
  { zone: 20, x: 13, y: 106, key: 'sunwardNightMusic', day: 'tmusic', seconds: 32 * 4 * 60 / 90 },
];
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
  await page.locator('#name').fill('NightFour'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.zone === 0 && !!valhalla.fmusic?.running, null, { timeout: 60000 });
  await debug(page, { op: 'set_time', hour: 12, freeze: true });

  for (const song of songs) {
    await debug(page, { op: 'teleport', zone: song.zone, x: song.x, y: song.y });
    await page.waitForFunction(z => Field.zone === z, song.zone, { timeout: 15000 });
    await debug(page, { op: 'set_time', hour: 19, freeze: true });
    await page.waitForFunction(key => Math.abs(DayNight.nightMix - .5) < .01 && valhalla.activeNightMusic === valhalla[key] && valhalla[key]?.running, song.key, { timeout: 15000 });
    await page.waitForFunction(key => valhalla[key]?.loaded, song.key, { timeout: 30000 });
    const duration = await page.evaluate(key => valhalla[key].duration, song.key);
    assert.ok(Math.abs(duration - song.seconds) < .25, `${song.key} duration ${duration}`);
    await debug(page, { op: 'set_time', hour: 0, freeze: true });
    await page.waitForFunction(key => DayNight.nightMix === 1 && valhalla[key].output.gain.value > .95, song.key, { timeout: 15000 });
    assert.equal(await page.evaluate(() => valhalla.nightMusic.running), false);
    console.log(`${song.zone}: decoded ${duration.toFixed(3)}s, crossfade and midnight playback`);
  }

  await page.keyboard.press('n');
  await page.waitForFunction(() => valhalla.sunwardNightMusic.output.gain.value < .01, null, { timeout: 10000 });
  await page.keyboard.press('n');
  await page.waitForFunction(() => valhalla.sunwardNightMusic.output.gain.value > .95, null, { timeout: 10000 });

  await debug(page, { op: 'teleport', zone: 25, x: 14, y: 128 });
  await page.waitForFunction(() => Field.zone === 25 && valhalla.activeNightMusic === valhalla.nightMusic && valhalla.nightMusic.running && !valhalla.sunwardNightMusic.running, null, { timeout: 15000 });
  await debug(page, { op: 'teleport', zone: 15, x: 16, y: 112 });
  await page.waitForFunction(() => Field.zone === 15 && DayNight.nightMix === 0 && !valhalla.nightMusic.running, null, { timeout: 15000 });
  await debug(page, { op: 'teleport', zone: 20, x: 13, y: 106 });
  await debug(page, { op: 'set_time', hour: 6, freeze: true });
  await page.waitForFunction(() => Field.zone === 20 && Math.abs(DayNight.nightMix - .5) < .01 && valhalla.sunwardNightMusic.running, null, { timeout: 15000 });
  await debug(page, { op: 'set_time', hour: 12, freeze: true });
  await page.waitForFunction(() => DayNight.nightMix === 0 && !valhalla.sunwardNightMusic.running && valhalla.tmusic.running, null, { timeout: 15000 });
  assert.deepEqual(errors, [], 'no browser errors');
  console.log('Four remixes route by zone, decode, crossfade, mute, yield to fallback, and stay out of enclosed zones');
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close().catch(() => {});
});
