// Boss mechanics on the screen (BOSSMECH-CLIENT), in a real browser against a real private server. No shipped boss has a mechanic
// yet, so the world loads a small table of its own (VALHALLA_BOSSMECH_FILE, honoured only with test commands): a kill ring on a
// green slime, a break bar on a blue one, moving walls on a pink one, a mark on a yellow one. The server decides everything; this
// checks what the player sees: each telegraph is drawn where it is sent, stays for the whole cast and clears when it lands, the
// cast bar counts down, a death names its cause on the defeat screen and in the log, and the new texts exist in Swedish.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const release = path.join(root, 'target/release/valhalla-server');
const debug = path.join(root, 'target/debug/valhalla-server');
// The newer of the two builds: the release binary is the live service's and is only rebuilt at a deploy, so it is often the stale one.
const newest = [release, debug].filter(f => fs.existsSync(f)).sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs)[0];
const binary = process.env.VALHALLA_BINARY || newest;
const dir = fs.mkdtempSync(path.join(root, 'test-results', 'bossmech-'));
const table = path.join(dir, 'boss-mechanics.txt');
fs.writeFileSync(table, JSON.stringify({
  green: { mechanics: [{ name: 'Test Toll', block: 'zone', shape: { kind: 'circle', r: 6 }, effect: 'kill', cast: 5, every: 25, first: 1 }] },
  blue: { mechanics: [{ name: 'Test Dirge', block: 'break', cast: 8, every: 30, first: 1, bar: 0.05, stun: 6, vulnerable: 0.3 }] },
  pink: { mechanics: [{ name: 'Test Bramble', block: 'sweep', every: 60, first: 1, kind: { shape: 'walls', warn: 4, speed: 4, thickness: 3, gap: 4, walls: [{ from: 'west', gap: 'middle' }] } }] },
  yellow: { mechanics: [{ name: 'Test Downpour', block: 'mark', count: 1, every: 40, first: 1, cast: 5, effect: { kind: 'burst', r: 4 } }] },
}));
const client = new Client({ name: 'valhallasc-bossmech-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe',
    env: { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0', VALHALLA_BOSSMECH_FILE: table, ...(binary ? { VALHALLA_BINARY: binary } : {}) } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: true })));
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('Watcher'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.hero.x, null, { timeout: 60000 });
  const debug = command => page.evaluate(command => { Online.send({ type: 'debug', ref: Math.floor(Math.random() * 1e9), command }); }, command).then(() => page.waitForTimeout(300));
  const hero = () => page.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y }));
  const fights = () => page.evaluate(() => JSON.parse(JSON.stringify(BossMech.fights)));
  const spawn = async kind => {
    const h = await hero();
    await debug({ op: 'spawn_enemy', kind, x: h.x + 3, y: h.y, level: 1 });
    await page.waitForFunction(() => BossMech.active, null, { timeout: 15000 });
  };
  // A fight ends with its boss: kill every boss that is fighting now.
  const endFights = async () => {
    for (const f of await fights()) await debug({ op: 'kill_enemy', id: f.boss }).catch(() => {});
    await page.waitForFunction(() => !BossMech.active, null, { timeout: 8000 });
  };
  const pixels = (cx, cy, half = 10) => page.evaluate(({ cx, cy, half }) => {
    const [sx, sy] = Field._debug.w2s(cx, cy), cv = document.getElementById('fieldcv'), k = cv.width / 1600, g = cv.getContext('2d');
    const data = g.getImageData(Math.round((sx - half) * k), Math.round((sy - half / 2) * k), Math.round(half * 2 * k), Math.round(half * k)).data;
    let tint = 0; for (let i = 0; i < data.length; i += 4) tint += data[i] - (data[i + 1] + data[i + 2]) / 2;   // how much redder than green and blue
    return tint / (data.length / 4);
  }, { cx, cy, half });
  const hud = (x, y, w = 6, h = 4) => page.evaluate(({ x, y, w, h }) => {
    const cv = document.getElementById('fieldcv'), k = cv.width / 1600, g = cv.getContext('2d');
    const d = g.getImageData(Math.round(x * k), Math.round(y * k), Math.round(w * k), Math.round(h * k)).data; let r = 0, gr = 0, b = 0;
    for (let i = 0; i < d.length; i += 4) { r += d[i]; gr += d[i + 1]; b += d[i + 2]; }
    const n = d.length / 4; return [r / n, gr / n, b / n];
  }, { x, y, w, h });

  // ---- 1. a kill ring: drawn where it is sent, for the whole cast, cleared when it lands ---------------------------------------
  await spawn('green');
  await page.waitForFunction(() => BossMech.fights[0]?.tele.some(t => t.tele === 'red'), null, { timeout: 15000 });
  const first = (await fights())[0];
  const ringTele = first.tele.find(t => t.tele === 'red');
  check(ringTele && ringTele.shapes[0].t === 'circle' && ringTele.shapes[0].r === 6, 'the server sent a red circle of radius 6');
  check(first.cast.name === 'Test Toll' && first.cast.total === 5, 'the cast bar data names the ability and its 5 s cast');
  const c = ringTele.shapes[0];
  await page.waitForFunction(() => BossMech.fights[0]?.cast?.left < 3, null, { timeout: 8000 });
  const inside = await pixels(c.x + 3.5, c.y + 1), outside = await pixels(c.x + 12, c.y + 1);
  check(inside - outside > 15, `the ring tints the ground red inside (${inside.toFixed(1)}) and not outside (${outside.toFixed(1)})`);
  const bar = await hud((1600 - 360) / 2 + 20, 168 + 10, 8, 6);
  check(bar[0] > 150 && bar[1] < 110 && bar[2] < 110, `the cast bar is filled red at the left (${bar.map(Math.round)})`);
  // Walk the rest of the cast: the telegraph is there on every sample until the cast ends, and the time only goes down.
  let last = Infinity, samples = 0, gone = null;
  const began = Date.now();
  while (Date.now() - began < 7000) {
    const f = (await fights())[0];
    if (!f) { gone = Date.now() - began; break; }
    const t = f.tele.find(t => t.tele === 'red');
    if (f.cast && f.cast.left > 0.4) { check(!!t, 'the red ring stays drawn while the cast runs'); samples++; check(f.cast.left <= last + 0.001, 'the countdown only goes down'); last = f.cast.left; }
    if (!t && !f.cast) { gone = Date.now() - began; break; }
    await page.waitForTimeout(120);
  }
  check(samples >= 3, `watched the cast on ${samples} samples`);
  check(gone !== null, 'the ring is cleared once the cast has landed');
  const cues = await page.evaluate(() => window.__bossCueLog || []);
  check(cues.includes('warn') && cues.includes('land') && cues.indexOf('warn') < cues.indexOf('land'), `the cast played its warning cue and then its landing cue (${cues})`);
  const decoded = await page.evaluate(async () => (await Promise.all(['warn', 'land', 'shield', 'broken'].map(n => fetch(`assets/sfx_boss_${n}.mp3`).then(r => r.ok ? r.arrayBuffer().then(b => b.byteLength) : 0)))).every(n => n > 10000));
  check(decoded, 'all four cue files are served');
  check(/Would have been killed by Test Toll/.test(await page.locator('#chat-log').innerText()), 'god mode: the log says "Would have been killed by Test Toll"');

  // The same cast on a phone-sized screen: the bar still fits (its width is min(360, screen - 40) in drawing units).
  await page.setViewportSize({ width: 844, height: 390 });
  await page.waitForFunction(() => BossMech.fights[0]?.cast?.left < 3, null, { timeout: 40000 });   // the next cast starts 25 s after the last
  await page.screenshot({ path: path.join(world.artifacts, 'bossmech-phone.png') });
  check(await page.evaluate(() => { const cv = document.getElementById('fieldcv'), r = cv.getBoundingClientRect(); return r.width <= innerWidth + 1 && r.height <= innerHeight + 1; }), 'the field fits a phone-sized screen');
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.screenshot({ path: path.join(world.artifacts, 'bossmech-ring.png') });
  await debug({ op: 'set_god_mode', enabled: false });

  // ---- 2. the death cause on the defeat screen and in the log -----------------------------------------------------------------
  await page.waitForFunction(() => Field.hero.dead, null, { timeout: 60000 });
  await page.waitForFunction(() => !document.getElementById('dead-cause').hidden, null, { timeout: 5000 });
  check(await page.locator('#dead-cause').innerText() === 'Killed by Test Toll', 'the defeat screen says "Killed by Test Toll"');
  check(await page.evaluate(() => getComputedStyle(document.getElementById('dead-cause')).display !== 'none'), 'the cause is visible');
  await page.screenshot({ path: path.join(world.artifacts, 'bossmech-defeat.png') });
  check(/You were killed by Test Toll\./.test(await page.locator('#system-log').innerText()), 'the system tab says "You were killed by Test Toll."');
  await page.waitForFunction(() => !Field.hero.dead, null, { timeout: 30000 });
  check(await page.evaluate(() => document.getElementById('dead-cause').hidden), 'the cause is gone after the respawn');
  await debug({ op: 'set_god_mode', enabled: true });

  // ---- 3. a break bar ---------------------------------------------------------------------------------------------------------
  await spawn('blue');
  await page.waitForFunction(() => BossMech.fights.some(f => f.break), null, { timeout: 15000 });
  const brk = (await fights()).find(f => f.break);
  check(brk.break.name === 'Test Dirge' && brk.break.needed > 0 && brk.break.dealt >= 0, 'the break bar data carries the name, the damage dealt and the damage needed');
  const track = await hud((1600 - 360) / 2 + 300, 168 + 36 + 10, 8, 6);
  check(track[0] > 40 && track[0] < 90 && track[1] < 70 && track[2] < 40, `the break bar track is drawn under the cast bar (${track.map(Math.round)})`);
  await page.screenshot({ path: path.join(world.artifacts, 'bossmech-break.png') });
  await endFights();

  // ---- 4. moving walls: a dashed warning, then red walls with a green gap ----------------------------------------------------
  await spawn('pink');
  const seen = new Set();
  for (let i = 0; i < 60 && seen.size < 3; i++) {
    for (const t of (await fights())[0]?.tele || []) seen.add(t.tele);
    await page.waitForTimeout(150);
  }
  check(seen.has('dashed line') && seen.has('green gap'), `the walls are announced with a dashed line and a green gap (${[...seen]})`);
  const wall = (await fights())[0].tele.find(t => t.tele === 'dashed line' || t.tele === 'red');
  check(wall && wall.shapes.length >= 1, 'the wall has a shape to draw');
  await page.screenshot({ path: path.join(world.artifacts, 'bossmech-walls.png') });
  await endFights();

  // ---- 5. a mark: the bearer is named -----------------------------------------------------------------------------------------
  await spawn('yellow');
  await page.waitForFunction(() => BossMech.fights.some(f => f.marked?.length), null, { timeout: 20000 });
  check(await page.evaluate(() => BossMech.fights.some(f => f.marked.includes(Online.id))), 'the marked player is the hero');
  await page.screenshot({ path: path.join(world.artifacts, 'bossmech-mark.png') });

  // ---- 6. a fixture for the blocks no plain monster can show: the shield counter and the stun ----------------------------------
  await page.evaluate(() => {
    const fixture = [{ boss: -1, clock: 0, cast: null, break: null, tele: [], marked: [], frozen: [Online.id],
      shield: { name: 'The Bound Chorus', tag: 'singer', adds: 4, alive: 3, healPerSecond: 0 }, stunned: 0, banner: 'Kill the singers!' }];
    BossMech.update = () => {}; BossMech.fights.splice(0); BossMech.fights.push(...fixture);
  });
  await page.waitForTimeout(300);
  const shield = await page.evaluate(() => { const cv = document.getElementById('fieldcv'), k = cv.width / 1600, g = cv.getContext('2d'); const d = g.getImageData(Math.round(560 * k), Math.round(168 * k), Math.round(480 * k), Math.round(60 * k)).data; let light = 0; for (let i = 0; i < d.length; i += 4) if (d[i + 2] > 200 && d[i + 1] > 180) light++; return light; });
  check(shield > 150, `the shield counter text is drawn (${shield} light pixels)`);
  await page.screenshot({ path: path.join(world.artifacts, 'bossmech-shield.png') });

  // ---- 6b. every shape and telegraph kind, with motion on: nothing throws and the half-arena is cut to its room --------------------
  const motion = await page.evaluate(async () => {
    window.matchMedia = () => ({ matches: false });                  // motion allowed: pulsing, dash crawl, the last-second flash
    const h = Field.hero, at = (dx, dy) => ({ x: h.x + dx, y: h.y + dy });
    const tele = (shapes, extra) => ({ id: 1, name: 'Fixture', tele: 'red', color: '#e0453b', dashed: false, echo: false, shapes, left: 0.6, total: 5, ...extra });
    BossMech.fights.splice(0); BossMech.fights.push({ boss: -1, clock: 0, cast: { name: 'Fixture', left: 0.6, total: 5 }, break: { name: 'Fixture', left: 3, total: 8, dealt: 40, needed: 100 }, marked: [Online.id], frozen: [], shield: null, stunned: 2, banner: 'Fixture banner',
      tele: [
        tele([{ t: 'circle', ...at(-5, 0), r: 3, inner: 1 }]), tele([{ t: 'cone', ...at(0, -5), dir: 1, half: .5, length: 6 }]), tele([{ t: 'lane', x1: h.x, y1: h.y + 4, x2: h.x + 6, y2: h.y + 4, half: 1 }]),
        tele([{ t: 'half', ...at(0, 0), nx: 1, ny: 0 }]), tele([{ t: 'rect', x0: h.x - 9, y0: h.y - 9, x1: h.x - 7, y1: h.y - 7 }]),
        tele([{ t: 'lane', x1: h.x, y1: h.y + 6, x2: h.x + 6, y2: h.y + 6, half: 1 }], { tele: 'dashed line', color: '#f1e3b4', dashed: true }),
        tele([{ t: 'lane', x1: h.x, y1: h.y + 8, x2: h.x + 6, y2: h.y + 8, half: 1 }], { tele: 'green gap', color: '#4fc26b', left: 0, total: 0 }),
        tele([{ t: 'circle', ...at(6, 6), r: 2, inner: 0 }], { tele: 'blue', color: '#3f9bea', lit: false, progress: .6, left: 0, total: 0 }),
        tele([{ t: 'circle', ...at(8, 2), r: .5, inner: 0 }], { gaze: true }), tele([{ t: 'circle', ...at(9, 3), r: 1, inner: 0 }], { tele: 'cover', hits: 1, standing: true, left: 0, total: 0 }),
        tele([{ t: 'circle', ...at(-7, 5), r: 4, inner: 0 }], { echo: true }),
      ] });
    const half = BossMech._polygons({ t: 'half', x: 10, y: 10, nx: 1, ny: 0 }, () => [4, 4, 20, 20])[0];
    await new Promise(r => setTimeout(r, 800));
    return half;
  });
  check(motion.length === 4 && motion.every(([x, y]) => x >= 10 && x <= 20 && y >= 4 && y <= 20), `a half-arena is cut to its room (${JSON.stringify(motion)})`);
  await page.screenshot({ path: path.join(world.artifacts, 'bossmech-shapes.png') });

  // ---- 7. Swedish, written by hand --------------------------------------------------------------------------------------------
  const sv = await browser.newPage({ viewport: { width: 1000, height: 700 } });
  await sv.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'sv', sound: false })));
  await sv.goto(world.url);
  const words = await sv.evaluate(() => ['Invulnerable', 'Stunned', 'Marked!', 'Frozen!', 'Deal damage to stop it!', '{0} of {1} left', 'Killed by Test Toll', 'Would have been killed by Test Toll', 'You were killed by Test Toll.'].map(s => Locale.translate(s)));
  assert.deepEqual(words, ['Osårbar', 'Bedövad', 'Märkt!', 'Fastfrusen!', 'Skada den för att stoppa den!', '{0} av {1} kvar', 'Dödad av Test Toll', 'Hade blivit dödad av Test Toll', 'Du dödades av Test Toll.']);
  checks += words.length;

  assert.deepEqual(errors, []);
  console.log(`bossmech-ui: ${checks} checks passed`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
  fs.rmSync(dir, { recursive: true, force: true });
});
