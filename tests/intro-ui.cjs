// INTRO-* in a real browser: the opening cutscene. A brand-new character cannot be made on a test server without the server's own first-tick trigger (covered
// by `cargo test cutscene`), so the scene is started the way the client does when the packet arrives: Cutscene.play(['intro'], { skippable }).
// Checks: it locks the hero (a held key moves nothing); the narrator speaks every line (speech synthesis is stubbed and records what is said, in order, in
// English with the English voice setting); the subtitles show; a scene that is not skippable cannot be skipped and shows no skip hint; a skippable one shows
// the hint after a few seconds and ends on a held key (and the narrator is silenced); Settings > Replay intro plays it skippable; the sea is on the canvas;
// and a full minute plays through to the end, returns control and leaves the hero where they were. MUTATE=lock|skip|narrate must each fail.
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-intro', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; console.log(`${checks}: ${message}`); };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`); return result.structuredContent;
}
const errors = [];
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0', ...(process.env.VALHALLA_BINARY ? { VALHALLA_BINARY: process.env.VALHALLA_BINARY } : {}) } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true, args: ['--disable-gpu'] });
  const page = await browser.newPage({ viewport: { width: 960, height: 600 }, reducedMotion: 'no-preference' });
  page.on('pageerror', e => { errors.push(e.message); console.log('PAGEERROR', e.message); });
  const mutations = {
    lock: ["for (const type of ['keydown', 'keyup', 'keypress'])", 'for (const type of [])'],
    skip: ['if (held >= 1) { finish(); return; }', 'if (held >= 9999) { finish(); return; }'],
    narrate: ['if (S.narrate) speak(tr(text), hold || 4);', ''],
  };
  if (process.env.MUTATE) {
    const [from, to] = mutations[process.env.MUTATE] || mutations.lock, src = fs.readFileSync(path.join(root, 'client/cutscene.js'), 'utf8');
    assert.ok(src.includes(from), 'the mutation applies');
    await page.route('**/cutscene.js*', route => route.fulfill({ contentType: 'text/javascript', body: src.replace(from, to) }));
  }
  // A stub narrator: records every utterance and every cancel.
  await page.addInitScript(() => {
    window.AudioContext = undefined; window.webkitAudioContext = undefined;
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: true, char: null, draft: null }));
    window.__said = []; window.__cancelled = 0;
    window.SpeechSynthesisUtterance = function (text) { this.text = text; };
    Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: { speak: u => window.__said.push({ text: u.text, lang: u.lang, rate: u.rate }), cancel: () => { window.__cancelled++; }, getVoices: () => [] } });
  });
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('Summoned'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
  await page.waitForTimeout(1500);
  const hero = () => page.evaluate(() => ({ x: Field.hero.nx ?? Field.hero.x, y: Field.hero.ny ?? Field.hero.y }));
  const state = () => page.evaluate(() => window.Cutscene.state);
  const home = await hero();

  // ---------- a first character: not skippable ----------
  await page.evaluate(() => window.Cutscene.play(['intro'], { skippable: false }));
  await page.waitForFunction(() => window.Cutscene.state?.scene === 'intro', null, { timeout: 5000 });
  check(true, 'The opening cutscene starts');
  check((await state()).dur > 55 && (await state()).dur < 70, `It is about a minute long (${(await state()).dur} s)`);
  await page.keyboard.down('ArrowRight'); await page.keyboard.down('KeyW');
  await page.waitForTimeout(2500);
  const moved = await hero();
  check(Math.hypot(moved.x - home.x, moved.y - home.y) < .05, 'A held key moves nothing while it plays');
  check(await page.locator('#cutscene').isVisible() && (await page.locator('#cutscene .cs-caption').innerText()).length > 20, 'The narration is shown as subtitles');
  const sea = await page.evaluate(() => {
    const c = document.getElementById('fieldcv'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0, blue = 0;
    for (let i = 0; i < d.length; i += 28) { n++; if (d[i + 2] > 110 && d[i + 2] > d[i] + 40) blue++; } return blue / n;
  });
  check(sea > .3, `The canvas shows the sea (${(sea * 100).toFixed(0)}% blue)`);
  await page.waitForTimeout(3000);
  const held = await state();
  check(held && held.scene === 'intro', 'Holding a key for seconds does not skip a scene that cannot be skipped');
  check(await page.locator('#cutscene .cs-skip').isHidden(), 'And it shows no skip hint');
  await page.keyboard.up('ArrowRight'); await page.keyboard.up('KeyW');
  const said = await page.evaluate(() => window.__said);
  check(said.length >= 1 && said[0].text.startsWith('Before the first harvest'), 'The narrator speaks the first line');
  check(said.every(s => s.lang === 'en-GB' && s.rate >= .72 && s.rate <= 1.18), 'In English, at a pace that fits each line');
  check(await page.evaluate(() => Cutscene.state?.skippable === false), 'The scene reports itself as not skippable');

  // ---------- the whole minute, then control returns ----------
  await page.waitForFunction(() => !window.Cutscene.active, null, { timeout: 70000 });
  const all = await page.evaluate(() => window.__said.map(s => s.text));
  check(all.length === 7 && all[4] === 'And it found you.' && all[6] === 'Welcome to Greenmeadow, hero.', `All seven lines are spoken in order (${all.length})`);
  check(await page.locator('#cutscene').isHidden(), 'The overlay hides at the end');
  const end = await hero();
  check(Math.hypot(end.x - home.x, end.y - home.y) < .05, 'The hero is exactly where they were: the scene never moved them');
  const before = await hero();
  await page.keyboard.down('ArrowRight'); await page.waitForTimeout(900); await page.keyboard.up('ArrowRight');
  const after = await hero();
  check(Math.hypot(after.x - before.x, after.y - before.y) > .4, 'Control returns afterwards');

  // ---------- Settings > Replay intro: skippable, and a held key ends it and silences the narrator ----------
  await page.evaluate(() => { window.__said.length = 0; window.__cancelled = 0; });
  await page.evaluate(() => document.getElementById('set-replay-intro')?.click());   // the button is part of Settings; clicking it directly keeps the test short
  await page.waitForFunction(() => window.Cutscene.state?.scene === 'intro', null, { timeout: 6000 });
  check(await page.evaluate(() => Cutscene.state.skippable === true), 'The replay from Settings can be skipped');
  await page.waitForFunction(() => window.Cutscene.state?.el > 3, null, { timeout: 8000 });
  check(await page.locator('#cutscene .cs-skip').isVisible(), 'The skip hint shows after a few seconds');
  await page.keyboard.down('Space'); await page.waitForTimeout(500);
  check(await page.evaluate(() => Cutscene.active), 'A short press does not skip (it must be held)');
  await page.waitForTimeout(1300); await page.keyboard.up('Space');
  await page.waitForFunction(() => !window.Cutscene.active, null, { timeout: 4000 });
  check(true, 'Holding a key for a second skips it');
  check((await page.evaluate(() => window.__cancelled)) >= 1, 'And the narrator is silenced');
  assert.deepEqual(errors, []);
  console.log(`intro-ui: ${checks} checks passed`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
});
