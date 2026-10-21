// Focused private-world playback check after removing the first two night leads.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-first-two-no-lead', version: '1.0.0' });
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
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: true, musicVol: .8 })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('QuietNight'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.zone === 0 && !!valhalla.fmusic?.running, null, { timeout: 60000 });

  for (const song of [
    { zone: 0, x: 36, y: 60, key: 'meadowNightMusic', day: 'fmusic', seconds: 32 * 4 * 60 / 82 },
    { zone: 1, x: 48, y: 86.5, key: 'cragsNightMusic', day: 'cmusic', seconds: 32 * 4 * 60 / 92 },
  ]) {
    await debug(page, { op: 'set_time', hour: 12, freeze: true });
    await debug(page, { op: 'teleport', zone: song.zone, x: song.x, y: song.y });
    await page.waitForFunction(z => Field.zone === z, song.zone, { timeout: 15000 });
    await page.waitForFunction(key => DayNight.nightMix === 0 && !valhalla[key].running, song.key, { timeout: 15000 });
    await debug(page, { op: 'set_time', hour: 19, freeze: true });
    await page.waitForFunction(key => Math.abs(DayNight.nightMix - .5) < .01 && valhalla.activeNightMusic === valhalla[key] && valhalla[key].running, song.key, { timeout: 15000 });
    await page.waitForFunction(key => valhalla[key].loaded, song.key, { timeout: 30000 });
    const duration = await page.evaluate(key => valhalla[key].duration, song.key);
    assert.ok(Math.abs(duration - song.seconds) < .25, `${song.key} duration ${duration}`);
    await debug(page, { op: 'set_time', hour: 0, freeze: true });
    await page.waitForFunction(key => DayNight.nightMix === 1 && Math.abs(valhalla[key].output.gain.value - .64) < .03, song.key, { timeout: 15000 });
    assert.equal(await page.evaluate(() => valhalla.nightMusic.running), false);
    await page.keyboard.press('n');
    await page.waitForFunction(key => valhalla[key].output.gain.value < .01, song.key, { timeout: 15000 });
    await page.keyboard.press('n');
    await page.waitForFunction(key => Math.abs(valhalla[key].output.gain.value - .64) < .03, song.key, { timeout: 15000 });
    await debug(page, { op: 'set_time', hour: 12, freeze: true });
    await page.waitForFunction(key => DayNight.nightMix === 0 && !valhalla[key].running, song.key, { timeout: 15000 });
    await page.waitForFunction(key => valhalla[key].running, song.day, { timeout: 15000 });
    console.log(`${song.zone}: ${duration.toFixed(3)}s loop, dusk and dawn fades, saved volume and mute`);
  }
  assert.deepEqual(errors, [], 'no browser errors');
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close().catch(() => {});
});
