// Private-world playback of the indoor night tracks. Use a fresh page for each
// zone so the bounded browser can release the previous zone's map and audio.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhalla-indoor-night-music', version: '1.0.0' });
let browser, started = false;
async function call(name) {
  const result = await client.callTool({ name, arguments: {} });
  assert.ok(!result.isError, JSON.stringify(result.content));
  return result.structuredContent;
}
const debug = (page, command) => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);
const songs = [
  { zone: 8, x: 96, y: 212, name: 'Deep', day: 'dmusic', night: 'deepNightMusic', seconds: 119.29 },
  { zone: 15, x: 66, y: 301, name: 'Orrery', day: 'omusic', night: 'orreryNightMusic', seconds: 117.073 },
];

(async () => {
  await client.connect(new StdioClientTransport({
    command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')],
    cwd: root, stderr: 'pipe', env: getDefaultEnvironment(),
  }));
  const world = await call('start_world'); started = true;
  for (const song of songs) {
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ viewport: { width: 960, height: 600 }, reducedMotion: 'reduce' });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    if (process.env.MUTATE === 'indoor') {
      await page.route('**/daynight.js*', async route => {
        const response = await route.fetch();
        const source = await response.text();
        const body = source.replace('(allowIndoor || isOutdoor(zone))', 'isOutdoor(zone)');
        assert.notEqual(body, source, 'mutation must disable night music indoors');
        await route.fulfill({ response, body });
      });
    }
    await page.addInitScript(() => {
      window.__musicReleaseS = 1;
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: true, musicVol: 1 }));
    });
    await page.goto(world.url);
    await page.locator('#start').click();
    await page.locator('#login-guest').click();
    await page.locator('#name').fill(song.name + ' Listener');
    await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && valhalla.fmusic, null, { timeout: 60000 });
    await debug(page, { op: 'set_time', hour: 12, freeze: true });
    await debug(page, { op: 'teleport', zone: song.zone, x: song.x, y: song.y });
    await page.waitForFunction(({ zone, day, night }) => Field.zone === zone &&
      valhalla.activeNightMusic === valhalla[night] && !valhalla[night].running &&
      valhalla[day].running && valhalla[day].output.gain.value > .9, song, { timeout: 15000 });
    await debug(page, { op: 'set_time', hour: 19, freeze: true });
    await page.waitForFunction(({ day, night }) => valhalla[night].running &&
      !valhalla[day].running &&
      valhalla[night].output.gain.value > .9, song, { timeout: 15000 });
    await debug(page, { op: 'set_time', hour: 22, freeze: true });
    await page.waitForFunction(({ day, night }) => valhalla[night].loaded &&
      valhalla[night].output.gain.value > .9 && !valhalla[day].running, song, { timeout: 15000 });
    const { duration, indoorLight } = await page.evaluate(night => ({
      duration: valhalla[night].duration,
      indoorLight: DayNight.nightMix === 0,
    }), song.night);
    assert.ok(Math.abs(duration - song.seconds) < .25, `${song.name} night track decodes`);
    assert.ok(indoorLight, `${song.name} retains indoor lighting`);
    await debug(page, { op: 'set_time', hour: 8, freeze: true });
    await page.waitForFunction(({ day, night }) => !valhalla[night].running &&
      valhalla[day].output.gain.value > .9, song, { timeout: 15000 });
    assert.deepEqual(errors, []);
    console.log(`${song.name}: day and night playback, dusk sequential fade, dawn return, indoor lighting`);
    await browser.close();
    browser = null;
  }
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  if (browser) await browser.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
