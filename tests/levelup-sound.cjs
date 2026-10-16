// The level-up fanfare in a real browser. Every node that reaches the speakers is also fed to an analyser, so the test
// measures what the player would hear: nothing for another player's level-up, one audible fanfare for your own (even for
// a multi-level jump), loud enough to notice and below clipping. Music is set to zero so only effects are measured.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-levelup-sound', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`); return result.structuredContent;
}
(async () => {
  const env = { ...getDefaultEnvironment(), ...(process.env.VALHALLA_BINARY ? { VALHALLA_BINARY: process.env.VALHALLA_BINARY } : {}) };
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true, args: ['--autoplay-policy=no-user-gesture-required'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => {
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: true, musicVol: 0, sfxVol: 1, char: null, draft: null }));
    const tap = window.__tap = { peak: 0, oscillators: 0 }, connect = AudioNode.prototype.connect, create = AudioContext.prototype.createOscillator;
    AudioContext.prototype.createOscillator = function () { tap.oscillators++; return create.call(this); };
    AudioNode.prototype.connect = function (target, ...rest) {
      const result = connect.call(this, target, ...rest);
      if (target instanceof AudioDestinationNode) {
        const ctx = target.context;
        if (!ctx.__analyser) {
          ctx.__analyser = ctx.createAnalyser(); ctx.__analyser.fftSize = 2048;
          const data = new Float32Array(2048);
          setInterval(() => { ctx.__analyser.getFloatTimeDomainData(data); for (const v of data) tap.peak = Math.max(tap.peak, Math.abs(v)); }, 20);
        }
        connect.call(this, ctx.__analyser);
      }
      return result;
    };
  });
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('Chime'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero.level >= 1, null, { timeout: 60000 });
  const level = event => page.evaluate(e => Field._debug.event({ type: 'event', kind: 'levelup', x: Field.hero.x, y: Field.hero.y, unlocked: [], ...e, actor: e.own ? Online.id : 'someone-else' }), event);
  const tap = () => page.evaluate(() => ({ ...__tap }));
  const reset = () => page.evaluate(() => { __tap.peak = 0; });
  await page.waitForTimeout(1500);
  await reset();
  const quiet = await tap();
  await page.waitForTimeout(600);
  const baseline = await tap();
  check(baseline.peak < .02, `Nothing else is loud before the event (peak ${baseline.peak.toFixed(3)})`);

  await level({ own: false, value: 1, level: 5 }); await page.waitForTimeout(2000);
  const other = await tap();
  check(other.oscillators === baseline.oscillators && other.peak < .02, "Another player's level-up plays no fanfare for you");

  await reset(); await level({ own: true, value: 1, level: 5 }); await page.waitForTimeout(3600);
  const one = await tap(), notes = one.oscillators - other.oscillators;
  check(notes >= 25, `Your level-up plays the full fanfare (${notes} voices)`);
  check(one.peak >= .2, `The fanfare is clearly audible (peak ${one.peak.toFixed(2)})`);
  check(one.peak <= .95, `The fanfare does not clip (peak ${one.peak.toFixed(2)})`);

  await reset(); await level({ own: true, value: 3, level: 8 }); await page.waitForTimeout(3600);
  const jump = await tap();
  check(jump.oscillators - one.oscillators === notes, 'A multi-level jump plays the fanfare once');
  check(jump.peak <= .95, `The multi-level fanfare does not clip (peak ${jump.peak.toFixed(2)})`);
  await page.waitForTimeout(2000); await reset(); await page.waitForTimeout(800);
  check((await tap()).peak < .02, 'The fanfare ends by itself and leaves silence');
  check(errors.length === 0, `No page errors: ${errors.join('; ')}`);
  console.log(`${checks} level-up sound checks passed; own-event peak ${one.peak.toFixed(2)}, ${notes} voices`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
