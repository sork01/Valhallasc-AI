// Focused private-world check for Greenmeadow's own night remix and shared fallback.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const loopSeconds = 32 * 4 * 60 / 82;
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
  if (process.env.MEADOW_NIGHT_ASSET) {
    await page.route('**/assets/music_meadow_night.mp3', route => route.fulfill({
      path: path.resolve(process.env.MEADOW_NIGHT_ASSET), contentType: 'audio/mpeg',
    }));
  }
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: true, musicVol: .8 })));
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
  assert.ok(Math.abs(duration - loopSeconds) < .025, `Greenmeadow night MP3 duration ${duration}`);
  const decoded = await page.evaluate(async () => {
    const bytes = await (await fetch('assets/music_meadow_night.mp3')).arrayBuffer();
    const context = new OfflineAudioContext(2, 1, 48000);
    const buffer = await context.decodeAudioData(bytes);
    const left = buffer.getChannelData(0), right = buffer.getChannelData(1);
    let sum = 0, peak = 0;
    for (let i = 0; i < left.length; i++) {
      sum += ((left[i] + right[i]) / 2) ** 2;
      peak = Math.max(peak, Math.abs(left[i]), Math.abs(right[i]));
    }
    return { seconds: buffer.duration, rms: 10 * Math.log10(sum / left.length), peak };
  });
  assert.ok(Math.abs(decoded.seconds - loopSeconds) < .025, `Decoded loop length: ${decoded.seconds}`);
  assert.ok(Math.abs(decoded.rms + 24) < .2, `Decoded mono RMS: ${decoded.rms}`);
  assert.ok(decoded.peak < .95, `Decoded peak: ${decoded.peak}`);
  await page.waitForFunction(() => Math.abs(valhalla.meadowNightMusic.output.gain.value - .32) < .025 &&
    Math.abs(valhalla.fmusic.output.gain.value - .32) < .025, null, { timeout: 10000 });
  await debug(page, { op: 'set_time', hour: 0, freeze: true });
  await page.waitForFunction(() => DayNight.nightMix === 1 && valhalla.meadowNightMusic.running, null, { timeout: 10000 });
  await page.waitForFunction(() => Math.abs(valhalla.meadowNightMusic.output.gain.value - .64) < .025, null, { timeout: 10000 });
  await page.keyboard.press('n');
  await page.waitForFunction(() => valhalla.meadowNightMusic.output.gain.value < .01, null, { timeout: 10000 });
  await page.keyboard.press('n');
  await page.waitForFunction(() => Math.abs(valhalla.meadowNightMusic.output.gain.value - .64) < .025, null, { timeout: 10000 });

  // All outdoor zones now have remixes. The unmapped indoor Deep selects the
  // shared fallback, with no night playback indoors.
  await debug(page, { op: 'teleport', zone: 8, x: 9.5, y: 150 });
  await page.waitForFunction(() => Field.zone === 8 && valhalla.activeNightMusic === valhalla.nightMusic &&
    !valhalla.nightMusic.running && !valhalla.meadowNightMusic.running && DayNight.nightMix === 0,
  null, { timeout: 10000 });
  await debug(page, { op: 'teleport', zone: 0, x: 36, y: 60 });
  await page.waitForFunction(() => Field.zone === 0 && valhalla.activeNightMusic === valhalla.meadowNightMusic && valhalla.meadowNightMusic.running && !valhalla.nightMusic.running, null, { timeout: 10000 });
  await debug(page, { op: 'set_time', hour: 6, freeze: true });
  await page.waitForFunction(() => Math.abs(DayNight.nightMix - .5) < .01 &&
    Math.abs(valhalla.meadowNightMusic.output.gain.value - .32) < .025, null, { timeout: 10000 });
  await debug(page, { op: 'set_time', hour: 7, freeze: true });
  await page.waitForFunction(() => DayNight.nightMix === 0 && !valhalla.meadowNightMusic.running, null, { timeout: 10000 });
  assert.deepEqual(errors, [], 'no browser errors');
  console.log(JSON.stringify({ ...decoded, checks: '82 BPM 4/4 loop decode, -24 dB mono RMS, dusk/dawn crossfades, saved volume, mute, travel and shared indoor fallback' }));
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close().catch(() => {});
});
