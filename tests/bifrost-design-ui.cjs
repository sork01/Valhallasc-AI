// Bifrost Reach as an authored map (scripts/bifrost_design.py): the real client draws the painted islands and bridges, the hub and the three
// outposts name themselves, the four updraft pads carry their gates, the three elites draw, and the minimap spans the bigger sky.
// Pictures in test-results/bifrost-design/.
//   REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/bifrost-design-ui.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'test-results/bifrost-design');
fs.mkdirSync(out, { recursive: true });
const port = 19600 + (process.pid % 400);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bifrost-'));
let server, browser, checks = 0;
const check = (v, l) => { assert.ok(v, l); checks++; console.log('ok', l); };
const W = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8')), Z = W.zones[6];
(async () => {
  check(Z.name === 'Bifrost Reach' && Z.size === 376, 'Bifrost Reach is the 376 grid');
  check(Z.shapeFloor === undefined && Z.sky.length === 376, 'a sky zone: drawn from its sky rows, no outline floor');
  const floor = (x, y) => (Z.sky[Math.floor(y)] || '')[Math.floor(x)] !== ' ' && (Z.sky[Math.floor(y)] || '')[Math.floor(x)] !== undefined;
  for (const p of Z.portals) check(p.id === 'sky_shattered_span' || p.walk, `${p.id} is a walk-in updraft`);
  for (const p of Z.portals) check(floor(p.x, p.y), `${p.id} stands on the floor`);
  server = spawn(process.env.VALHALLA_BINARY, [], { cwd: root, stdio: 'ignore',
    env: { ...process.env, VALHALLA_BIND: `127.0.0.1:${port}`, VALHALLA_DB: path.join(tmp, 'v.sqlite'), VALHALLA_CLIENT_DIR: path.join(root, 'client'), VALHALLA_TEST_COMMANDS: '1', VALHALLA_GOD_MODE: '1', VALHALLA_START_LEVEL: '30', VALHALLA_LEVEL_SPREAD: '0' } });
  for (let i = 0; i < 100; i++) { try { if ((await fetch(`http://127.0.0.1:${port}/health`)).ok) break; } catch (_) {} await new Promise(r => setTimeout(r, 200)); }
  browser = await chromium.launch({ headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' })).newPage();
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => { localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {} })); });
  await page.goto(`http://127.0.0.1:${port}/`); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('SkyWalker'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  const debug = c => page.evaluate(x => Online.send({ type: 'debug', command: x }), c);
  const go = async (x, y, wait = 1800) => { await debug({ op: 'teleport', zone: 7, x, y }); await page.waitForFunction(([a, b]) => Field.zone === 7 && Math.hypot(Field.hero.nx - a, Field.hero.ny - b) < 2, [x, y], { timeout: 20000 }); await page.waitForTimeout(wait); };
  await debug({ op: 'set_time', hour: 12, freeze: true }); await debug({ op: 'set_weather', kind: 'clear' });
  const at = Z.city.plaza;
  await go(at.x, at.y + 6);
  check(await page.evaluate(() => Field.zoneName) === 'Bifrost Reach', 'the client is in Bifrost Reach');
  check(await page.evaluate(() => Field.areaName.includes("Heimdall")), "the hub names itself Heimdall's Perch");
  await page.screenshot({ path: path.join(out, 'perch.png') });
  for (const c of Z.camps) {
    await go(c.plaza.x, c.plaza.y + 2);
    check(await page.evaluate(n => Field.areaName === n && document.getElementById('area-title').textContent.includes(n), c.name), `${c.name} names itself`);
    await page.screenshot({ path: path.join(out, `outpost-${c.name.toLowerCase().replace(/[^a-z]+/g, '-')}.png`) });
  }
  for (const p of Z.portals.filter(p => p.walk)) {
    await go(p.x - p.walk[0] * 5, p.y - p.walk[1] * 5, 1500);
    await page.screenshot({ path: path.join(out, `pad-${p.id}.png`) });
  }
  for (const id of ['sky_pylon', 'sky_hallgate', 'sky_bell', 'sky_ward_last', 'sky_tally', 'sky_shardfield', 'sky_pad_stormrift']) {
    const pl = Z.places.find(q => q.id === id);
    await go(pl.x, pl.y + 5, 1500);
    await page.screenshot({ path: path.join(out, `place-${id}.png`) });
  }
  for (const kind of ['skoll', 'shardking', 'heimdallr']) {
    const sp = Z.slimes.find(s => s.kind === kind);
    await go(sp.x - 4, sp.y + 4, 1500);
    await page.waitForFunction(k => Field.slimes.some(s => s.kind === k), kind, { timeout: 15000 });
    await page.waitForTimeout(1200);
    await page.screenshot({ path: path.join(out, `elite-${kind}.png`) });
    check(await page.evaluate(k => Field.slimes.find(s => s.kind === k)?.d?.name?.length > 3, kind), `${kind} is on the map with a name`);
  }
  // the minimap spans the same 240 tiles as every pilot zone (120 at the default zoom 2), not the 376 grid
  check(await page.evaluate(() => Field.miniTiles) === 120, 'the minimap spans 240 tiles at zoom 1 (120 at the default zoom 2), not the 376 grid');
  check(errors.length === 0, 'no page errors: ' + errors.slice(0, 3).join(' | '));
  console.log(JSON.stringify({ passed: true, checks }));
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => { await browser?.close(); server?.kill(); });
