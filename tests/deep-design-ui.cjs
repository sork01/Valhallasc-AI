// Rán's Deep as an authored map on its atlas outline (scripts/deep_design.py): the real client draws the Net, the Shallows, Keelhaven and the three
// outposts, the crossings stand on the rim, the elites draw, and beyond the outline lies black water (not the coast or border ground of a land zone).
// Pictures in test-results/deep-design/.
//   REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/deep-design-ui.cjs
//   MUTATE=1 serves the committed field.js (the Deep's outline drawn like a land zone's): the black-water check must fail.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn, execSync } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'test-results/deep-design');
fs.mkdirSync(out, { recursive: true });
const port = 19600 + (process.pid % 400);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'deep-'));
let server, browser, checks = 0;
const check = (v, l) => { assert.ok(v, l); checks++; console.log('ok', l); };
const W = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8')), Z = W.zones[7];
const onFloor = (x, y) => (Z.shapeFloor[Math.floor(y)] || '')[Math.floor(x)] === '#';
(async () => {
  check(Z.name === "Rán's Deep" && Z.size === 256, "Rán's Deep is the 256 grid");
  check(Z.shapeFloor && Z.shape.neighbours.join() === '7,9,13', 'it has its outline floor and borders Bifrost, Nacrehold and Astralhollow');
  check(!Z.portals.some(p => p.seam), 'no seam: every crossing is a portal (the Nacrehold seam comes after its reshape)');
  check(Z.camps.length === 3 && Z.camps.map(c => c.name).sort().join() === 'Drownwatch,Gatewatch,Lanternrest', 'three outposts');
  for (const p of Z.portals) check(onFloor(p.x, p.y), `${p.id} stands on the floor`);
  for (const p of Z.portals.filter(p => p.walk)) check(p.walk.some(v => v !== 0), `${p.id} is a walk-in gate`);
  const kinds = k => Z.slimes.filter(s => s.kind === k && !s.ambush).length;
  check(['kraken', 'hvitserk', 'ghostmaw'].every(k => kinds(k) === 1), 'the three elites stand once each');
  server = spawn(process.env.VALHALLA_BINARY, [], { cwd: root, stdio: 'ignore',
    env: { ...process.env, VALHALLA_BIND: `127.0.0.1:${port}`, VALHALLA_DB: path.join(tmp, 'v.sqlite'), VALHALLA_CLIENT_DIR: path.join(root, 'client'), VALHALLA_TEST_COMMANDS: '1', VALHALLA_GOD_MODE: '1', VALHALLA_START_LEVEL: '38', VALHALLA_LEVEL_SPREAD: '0' } });
  for (let i = 0; i < 100; i++) { try { if ((await fetch(`http://127.0.0.1:${port}/health`)).ok) break; } catch (_) {} await new Promise(r => setTimeout(r, 200)); }
  browser = await chromium.launch({ headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' })).newPage();
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  if (process.env.MUTATE) await page.route('**/field.js', route => route.fulfill({ contentType: 'text/javascript', body: execSync('git show HEAD:client/field.js', { cwd: root, maxBuffer: 1 << 28 }).toString() }));
  await page.addInitScript(() => { localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {} })); });
  await page.goto(`http://127.0.0.1:${port}/`); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('DeepWalker'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  const debug = c => page.evaluate(x => Online.send({ type: 'debug', command: x }), c);
  const go = async (x, y, wait = 1800) => { await debug({ op: 'teleport', zone: 8, x, y }); await page.waitForFunction(([a, b]) => Field.zone === 8 && Math.hypot(Field.hero.nx - a, Field.hero.ny - b) < 2, [x, y], { timeout: 20000 }); await page.waitForTimeout(wait); };
  await debug({ op: 'set_time', hour: 12, freeze: true }); await debug({ op: 'set_weather', kind: 'clear' });
  const plaza = Z.city.plaza;
  await go(plaza.x, plaza.y + 6);
  check(await page.evaluate(() => Field.zoneName) === "Rán's Deep", "the client is in Rán's Deep");
  check(await page.evaluate(() => Field.areaName.includes('Keelhaven')), 'the hub names itself Keelhaven');
  await page.screenshot({ path: path.join(out, 'keelhaven.png') });
  for (const c of Z.camps) {
    await go(c.plaza.x, c.plaza.y + 2);
    check(await page.evaluate(n => Field.areaName === n && document.getElementById('area-title').textContent.includes(n), c.name), `${c.name} names itself`);
    await page.screenshot({ path: path.join(out, `outpost-${c.name.toLowerCase()}.png`) });
  }
  // beyond the outline lies black water: a point 5 tiles outside the west rim is dark, not the coast or border ground of a land zone
  const gate = Z.portals.find(p => p.id === 'maelstrom_up');
  await go(gate.x + 6, gate.y);
  await page.screenshot({ path: path.join(out, 'rim-west.png') });
  const beyond = await page.evaluate(([x, y]) => {
    const [fx, fy] = Field.screenOf(x, y), c = document.getElementById('fieldcv'), px = Math.round(fx * c.width), py = Math.round(fy * c.height);
    const g = c.getContext('2d'), d = g.getImageData(px, py, 1, 1).data;
    return { px, py, rgba: [...d] };
  }, [gate.x - 7, gate.y]);
  check(!onFloor(gate.x - 7, gate.y), 'the probe point lies outside the outline');
  check(beyond.px > 0 && beyond.px < 1280 && beyond.py > 0 && beyond.py < 800, `the probe point is on screen (${beyond.px}, ${beyond.py})`);
  check(beyond.rgba[3] === 255 && beyond.rgba[0] < 40 && beyond.rgba[1] < 50 && beyond.rgba[2] < 60, `black water beyond the outline: pixel ${beyond.rgba.join(',')}`);
  for (const p of Z.portals.filter(p => p.walk)) {
    await go(p.x - p.walk[0] * 5, p.y - p.walk[1] * 5, 1500);
    await page.screenshot({ path: path.join(out, `gate-${p.id}.png`) });
  }
  for (const id of ['deep_pearlgate', 'deep_longship', 'deep_chapel', 'deep_lr_lamp', 'deep_gw_vents', 'deep_dw_stones', 'deep_garden', 'deep_courtdoor']) {
    const pl = Z.places.find(q => q.id === id);
    await go(pl.x, pl.y + 5, 1500);
    await page.screenshot({ path: path.join(out, `place-${id}.png`) });
  }
  for (const kind of ['kraken', 'hvitserk', 'ghostmaw']) {
    const sp = Z.slimes.find(s => s.kind === kind);
    await go(sp.x - 4, sp.y + 4, 1500);
    await page.waitForFunction(k => Field.slimes.some(s => s.kind === k), kind, { timeout: 15000 });
    await page.waitForTimeout(1200);
    await page.screenshot({ path: path.join(out, `elite-${kind}.png`) });
    check(await page.evaluate(k => Field.slimes.find(s => s.kind === k)?.d?.name?.length > 3, kind), `${kind} is on the map with a name`);
  }
  // the minimap spans the same 240 tiles as every pilot zone (120 at the default zoom 2)
  check(await page.evaluate(() => Field.miniTiles) === 120, 'the minimap spans 240 tiles at zoom 1 (120 at the default zoom 2)');
  check(errors.length === 0, 'no page errors: ' + errors.slice(0, 3).join(' | '));
  console.log(JSON.stringify({ passed: true, checks }));
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => { await browser?.close(); server?.kill(); });
