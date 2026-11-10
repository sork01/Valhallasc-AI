// CUTSCENE-* in a real browser: the first real crossing of each kind plays its locked cutscene once, and never again.
//   6 -> 7 Wyrdwood up to Bifrost: sky_up       7 -> 8 Bifrost into Ran's Deep: sky_down then dive (sky_down already seen: dive only)
//   7 -> 6 Bifrost down to the Wyrdwood: sky_down (played first below)       8 -> 7 the Deep back to Bifrost: surface
// While a scene plays: a held arrow key and a canvas click do not move the hero, the plain zone-journey notice stays hidden, the letterbox bars
// and a caption show, the canvas really carries the scene (cloud and streak white, or sea blue) and, in the dive, the lead shoes go on after
// the caption says so. When it ends control returns. A scene already seen is never played again.
// Needs the bounded runner and a `--profile test` server binary. MUTATE=lock serves a cutscene.js that does not swallow keys, MUTATE=draw one that
// never paints the scene; each must fail.
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-cutscene', version: '1.0.0' });
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
    draw: ['g.save(); g.globalAlpha = cover; g.drawImage(layer, 0, 0); g.restore();', ''],
  };
  if (process.env.MUTATE) {
    const [from, to] = mutations[process.env.MUTATE] || mutations.lock, src = fs.readFileSync(path.join(root, 'client/cutscene.js'), 'utf8');
    assert.ok(src.includes(from), 'the mutation applies');
    await page.route('**/cutscene.js*', route => route.fulfill({ contentType: 'text/javascript', body: src.replace(from, to) }));
  }
  await page.addInitScript(() => { window.AudioContext = undefined; window.webkitAudioContext = undefined; localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })); });
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('Traveller'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
  const debug = command => page.evaluate(command => Online.send({ type: 'debug', command }), command);
  await debug({ op: 'enable_cutscenes' });   // test servers play none unless asked
  const state = () => page.evaluate(() => window.Cutscene.state);
  const hero = () => page.evaluate(() => ({ x: Field.hero.nx ?? Field.hero.x, y: Field.hero.ny ?? Field.hero.y, zone: Field.zone, shoes: !!Field.hero.leadShoes }));
  // Pixels of the real game canvas: how much of it is cloud/streak white, and how much sea blue.
  const pixels = () => page.evaluate(() => {
    const c = document.getElementById('fieldcv'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let white = 0, sea = 0, n = 0;
    for (let i = 0; i < d.length; i += 4 * 7) { n++; const r = d[i], g = d[i + 1], b = d[i + 2]; if (r > 225 && g > 235 && b > 240) white++; if (b > 110 && b > r + 50 && g > r + 20 && b < 220) sea++; }
    return { white: white / n, sea: sea / n };
  });

  // Walk through the real gate between two zones, the way a player does.
  async function cross(from, to) {
    const p = await page.evaluate(([from, to]) => Field._debug.zones[from].portals.find(p => p.to === to && p.walk), [from, to]);
    assert.ok(p, `a real walking crossing ${from} -> ${to}`);
    await page.evaluate(() => { Field.clearInput(); Online.send({ type: 'stop' }); });
    await debug({ op: 'teleport', zone: from, x: p.x - p.walk[0] * 6, y: p.y - p.walk[1] * 6 });
    await page.waitForFunction(from => Field.zone === from, from); await page.waitForTimeout(1300);
    await page.evaluate(p => Field.setTouchDirection(p.walk[0] - p.walk[1], p.walk[0] + p.walk[1]), p);
    await page.waitForFunction(to => Field.zone === to, to, { timeout: 25000 });
    await page.evaluate(() => { Field.clearInput(); Online.send({ type: 'stop' }); });
  }
  const noScene = async (why) => { await page.waitForTimeout(1800); check(!(await state()), `no cutscene: ${why}`); };
  const waitScene = async id => { await page.waitForFunction(id => window.Cutscene.state?.scene === id, id, { timeout: 8000 }); };
  const waitOver = async () => { await page.waitForFunction(() => !window.Cutscene.active, null, { timeout: 20000 }); };

  // ---------- 6 -> 7: the updraft up, played in full once ----------
  await cross(6, 7);
  await waitScene('sky_up');
  check(true, 'The first climb to Bifrost plays the updraft cutscene');
  const at = await hero();
  await page.keyboard.down('ArrowRight'); await page.keyboard.down('KeyW');
  await page.mouse.click(300, 300); await page.mouse.click(700, 420);
  await page.waitForTimeout(2200);
  const mid = await hero();
  await page.keyboard.up('ArrowRight'); await page.keyboard.up('KeyW');
  check(Math.hypot(mid.x - at.x, mid.y - at.y) < .05, `A held key and clicks do not move the hero during the scene (${Math.hypot(mid.x - at.x, mid.y - at.y).toFixed(3)} tiles)`);
  check(await page.locator('#cutscene').isVisible(), 'The letterbox overlay is shown');
  check((await page.locator('#cutscene .cs-caption').innerText()).length > 3, `With a caption (${await page.locator('#cutscene .cs-caption').innerText()})`);
  check(await page.locator('#zone-journey').isHidden(), 'The plain zone-journey notice stays hidden');
  const during = await pixels(); console.log('pixels during sky_up', JSON.stringify(during));
  check(during.white > .02, `The canvas carries the scene: cloud and streak white (${(during.white * 100).toFixed(1)}% of sampled pixels)`);
  await waitOver();
  const after = await pixels(); console.log('pixels after sky_up', JSON.stringify(after));
  check(during.white > after.white + .015, `And it is gone afterwards (${(during.white * 100).toFixed(1)}% against ${(after.white * 100).toFixed(1)}%)`);
  check(await page.locator('#cutscene').isHidden(), 'The overlay hides again');
  const free0 = await hero();
  await page.keyboard.down('ArrowRight'); await page.waitForTimeout(900); await page.keyboard.up('ArrowRight');
  const free1 = await hero();
  check(Math.hypot(free1.x - free0.x, free1.y - free0.y) > .5, `Control returns when it ends (moved ${Math.hypot(free1.x - free0.x, free1.y - free0.y).toFixed(2)} tiles)`);

  // ---------- 7 -> 6: the way down; then the climb again plays nothing ----------
  await cross(7, 6); await waitScene('sky_down'); check(true, 'The first descent from Bifrost plays the fall cutscene'); await waitOver();
  await cross(6, 7); await noScene('the climb is already seen');
  await cross(7, 6); await noScene('and so is the descent');

  // Sample a running scene until it ends: its clock, whether the shoes are on, the caption and (when asked) the sea blue of the canvas.
  async function record(withPixels) {
    const samples = [];
    for (let i = 0; i < 400; i++) {
      const s = await page.evaluate(() => window.Cutscene.state && ({ scene: window.Cutscene.state.scene, el: window.Cutscene.state.el, shoes: window.Cutscene.shoes(), caption: document.querySelector('#cutscene .cs-caption').textContent, announces: [...document.querySelectorAll('#announce .announce-line')].map(e => e.textContent) }));
      if (!s) { if (samples.length) break; await page.waitForTimeout(60); continue; }
      if (withPixels && s.el > 3.4 && s.el < 5) s.sea = (await pixels()).sea;
      samples.push(s); await page.waitForTimeout(150);
    }
    return samples;
  }

  // ---------- 6 -> 7 -> 8: Bifrost into the sea ----------
  await cross(6, 7); await page.waitForTimeout(500);
  // Sampling starts before the crossing, so the first samples are the first moments of the scene.
  const diving = record(true); await cross(7, 8);
  const dive = await diving;
  check(dive.length > 5 && dive.every(s => s.scene === 'dive'), `Bifrost into Ran's Deep plays only the dive (the fall was already seen): ${dive.length} samples`);
  const early = dive.filter(s => s.el < .4), later = dive.filter(s => s.el > .8);
  check(early.length > 0 && later.length > 0, `The scene was sampled before and after the shoes go on (${early.length} early, ${later.length} later)`);
  check(early.every(s => !s.shoes) && later.every(s => s.shoes), 'The lead shoes go on during the scene, a half second in');
  check(dive.some(s => /Equipping lead shoes/.test(s.caption)), 'Its caption says "Equipping lead shoes"');
  check(dive.every(s => !s.announces.some(t => /lead shoes/i.test(t))), 'And the plain announce is left out (no double message)');
  const seaBlue = Math.max(...dive.map(s => s.sea || 0)); console.log('sea blue during the dive', seaBlue.toFixed(2));
  check(seaBlue > .25, `Sinking through the sea: the canvas is sea blue (${(seaBlue * 100).toFixed(0)}%)`);
  check((await hero()).shoes, 'Afterwards the hero stands in Ran\'s Deep in lead shoes');

  // ---------- 8 -> 7: back up ----------
  const rising = record(false); await cross(8, 7);
  const up = await rising;
  check(up.length > 5 && up.every(s => s.scene === 'surface'), `The sea back to Bifrost plays only the surfacing (the updraft was already seen): ${up.length} samples`);
  check(up.filter(s => s.el < .35).every(s => s.shoes) && up.filter(s => s.el > .9).every(s => !s.shoes) && up.some(s => s.el > .9), 'The shoes come off during the scene');
  check(up.some(s => /Removing lead shoes/.test(s.caption)), 'Its caption says "Removing lead shoes"');
  await cross(7, 8); await noScene('the dive is seen');
  assert.deepEqual(errors, []);
  console.log(`cutscene-ui: ${checks} checks passed`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
});
