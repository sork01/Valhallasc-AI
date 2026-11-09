// The Lapis Erg as an authored map (scripts/lapis_design.py): the real client names each of the fourteen regions, draws its ground classes (blue salt crust against red crag rock),
// the five hubs name themselves, the three elites draw from their art, the two rim gates and the astrolabe door stand on the floor, and the Yearwheel border is a solid wall of
// isometric ramparts and towers: nothing crosses it from either side and a held key walks into it and stops. Pictures in test-results/lapis-design/.
//   REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/lapis-design-ui.cjs
//   MUTATE=1 serves the pilot's previous client/field.js (before the Lapis Erg's ground classes): the ground-class check must fail.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn, execSync } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'test-results/lapis-design');
fs.mkdirSync(out, { recursive: true });
const port = 19700 + (process.pid % 400);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'lapis-'));
let server, browser, checks = 0;
const check = (v, l) => { assert.ok(v, l); checks++; console.log('ok', l); };
const W = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8')), Z = W.zones[24];
const onFloor = (z, x, y) => (z.shapeFloor[Math.floor(y)] || '')[Math.floor(x)] === '#';
const VERSION = /Beta \d+\.\d+\.\d+/.exec(fs.readFileSync(path.join(root, 'client/index.html'), 'utf8'))[0];
const HUBS = [['wells', 60, 190, 'Azure Wells'], ['astro', 130, 78, 'Astrolabe Rest'], ['wallwatch', 95, 70, 'Wallwatch Post'], ['saltpan', 150, 205, 'Saltpan Post'], ['eastwell', 186, 172, 'Eastwell Post']];
const ELITES = [['dunecolossus', 58, 96], ['mirageroc', 203, 130], ['cobaltbasilisk', 246, 226]];
// regions whose ground classes are compared: pale blue-white salt crust against dark red crag rock (the old client painted everything the same ochre)
const GROUND = ['The Blue Salt Pans', 'The Roc Crag'], lums = {};
(async () => {
  check(Z.name === 'The Lapis Erg' && Z.size === 296 && Z.shapeFloor && Z.shape.neighbours.join() === '20,23,28', 'The Lapis Erg is the 296 grid with its outline and three neighbours');
  check(!Z.portals.some(p => p.seam), 'no seam anywhere: none of its neighbours is on the pilot yet');
  check(!Z.portals.some(p => p.to === 28) && !W.zones[27].portals.some(p => p.to === 25), 'the Yearwheel has no portal in either direction');
  for (const to of [20, 23]) check(Z.portals.some(p => p.to === to && p.walk), `the way to zone ${to} is a rim gate you walk through`);
  check(Z.portals.some(p => p.id === 'lapis_astrolabe_gate' && p.to === 34), 'the astrolabe door leads to the Sunken Astrolabe');
  for (const p of Z.portals) check(onFloor(Z, p.x, p.y), `${p.id} stands on the floor`);
  check(Z.regions.names.length === 14 && Z.camps.length === 4 && Z.quests.length === 29, 'fourteen regions, five hubs and 29 quests');
  const wall = Z.objects.filter(o => o.kind === 'rampart' || o.kind === 'tower');
  check(wall.filter(o => o.kind === 'rampart').length >= 50 && wall.filter(o => o.kind === 'tower').length >= 4, `the wall is ${wall.length} isometric rampart and tower objects`);
  server = spawn(process.env.VALHALLA_BINARY, [], { cwd: root, stdio: 'ignore',
    env: { ...process.env, VALHALLA_BIND: `127.0.0.1:${port}`, VALHALLA_DB: path.join(tmp, 'v.sqlite'), VALHALLA_CLIENT_DIR: path.join(root, 'client'), VALHALLA_TEST_COMMANDS: '1', VALHALLA_GOD_MODE: '1', VALHALLA_START_LEVEL: process.env.START_LEVEL || '99', VALHALLA_LEVEL_SPREAD: '0' } });
  for (let i = 0; i < 100; i++) { try { if ((await fetch(`http://127.0.0.1:${port}/health`)).ok) break; } catch (_) {} await new Promise(r => setTimeout(r, 200)); }
  browser = await chromium.launch({ headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' })).newPage();
  const errors = []; page.on('pageerror', e => errors.push(e.message + ' @ ' + (e.stack || '').split('\n').slice(1, 4).join(' | ')));
  if (process.env.MUTATE) {
    const old = execSync('git show e82c20a:client/field.js', { cwd: root, maxBuffer: 1 << 28 });
    await page.route('**/field.js*', r => r.fulfill({ status: 200, contentType: 'application/javascript', body: old }));
  }
  await page.addInitScript(v => { localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {} })); localStorage.setItem('valhallasc.whats-new.v1', v); }, VERSION);
  await page.goto(`http://127.0.0.1:${port}/`); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('LapisWalker'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  const debug = c => page.evaluate(x => Online.send({ type: 'debug', command: x }), c);
  const where = () => page.evaluate(() => ({ zone: Field.zone, x: Field.hero.nx, y: Field.hero.ny }));
  const go = async (zone, x, y, wait = 1800) => { await debug({ op: 'teleport', zone, x, y }); await page.waitForFunction(([z, a, b]) => Field.zone === z && Math.hypot(Field.hero.nx - a, Field.hero.ny - b) < 2, [zone, x, y], { timeout: 20000 }); await page.waitForTimeout(wait); };
  await debug({ op: 'set_time', hour: 12, freeze: true }); await debug({ op: 'set_weather', kind: 'clear' });
  // the ground is isometric: a world step (dx, dy) is the screen step (dx - dy, (dx + dy) / 2), so +x is Right+Down
  const keysFor = ([dx, dy]) => [Math.abs(dx - dy) > .35 ? (dx - dy > 0 ? 'ArrowRight' : 'ArrowLeft') : null, Math.abs(dx + dy) > .35 ? (dx + dy > 0 ? 'ArrowDown' : 'ArrowUp') : null].filter(Boolean);
  const cells = new Uint8Array(Z.size * Z.size); for (const [ry, a, b, k] of Z.regions.spans) cells.fill(k, ry * Z.size + a, ry * Z.size + b + 1);
  const solids = Z.objects.filter(o => o.kind !== 'void' && (o.r > 0 || o.width > 0));
  const towns = [Z.city, ...Z.camps].map(c => [c.x0 - 6, c.y0 - 6, c.x1 + 6, c.y1 + 6]);
  const clear = (x, y) => Z.shapeFloor[y]?.[x] === '#' && !towns.some(t => x >= t[0] && x <= t[2] && y >= t[1] && y <= t[3]) && solids.every(o => Math.hypot(o.x - x - .5, o.y - y - .5) > Math.max(o.r || 0, (o.width || 0) / 2 + .4) + 4);
  for (const [k, name] of Z.regions.names.entries()) {
    const mine = []; for (let y = 0; y < Z.size; y += 2) for (let x = 0; x < Z.size; x += 2) if (cells[y * Z.size + x] === k + 1 && Z.shapeFloor[y]?.[x] === '#') mine.push([x, y]);
    const mx = mine.reduce((s, c) => s + c[0], 0) / mine.length, my = mine.reduce((s, c) => s + c[1], 0) / mine.length;
    mine.sort((p, q) => Math.hypot(p[0] - mx, p[1] - my) - Math.hypot(q[0] - mx, q[1] - my));
    const at = mine.find(([x, y]) => clear(x, y) && cells[y * Z.size + x] === k + 1);
    assert.ok(at, `an open spot in ${name}`);
    const [x, y] = at, id = name.toLowerCase().replace(/[^a-z]+/g, '-');
    await go(25, x, y);
    check(await page.evaluate(() => Field.areaName) === name, `${id}: the HUD names ${name}`);
    if (GROUND.includes(name)) {
      const px = await page.evaluate(([a, b]) => { const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), L = [];
        for (const i of [-3, 0, 3]) for (const j of [-3, 0, 3]) { const [fx, fy] = Field.screenOf(a + i + .5, b + j + .5); const c = g.getImageData(Math.round(fx * cv.width), Math.round(fy * cv.height), 1, 1).data; L.push([c[0], c[1], c[2], c[0] * .3 + c[1] * .59 + c[2] * .11]); }
        L.sort((p, q) => p[3] - q[3]); return L[4].slice(0, 3); }, [x, y]);      // the median of nine points: a palm or a stone covers some of them, never most
      lums[name] = px[0] * .3 + px[1] * .59 + px[2] * .11; console.log(`${name}: luminance ${lums[name].toFixed(0)}`);
    }
    await page.screenshot({ path: path.join(out, `${id}.png`) });
  }
  check(lums['The Blue Salt Pans'] - lums['The Roc Crag'] > 45, `the Blue Salt Pans (${lums['The Blue Salt Pans'].toFixed(0)}) are much paler than the Roc Crag (${lums['The Roc Crag'].toFixed(0)}): the ground classes are drawn`);
  for (const [id, x, y, name] of HUBS) {
    await go(25, x, y);
    check(await page.evaluate(n => Field.areaName === n && document.getElementById('area-title').textContent.includes(n), name), `${id}: the title says ${name}`);
    await page.screenshot({ path: path.join(out, `${id}.png`) });
  }
  for (const [kind, x, y] of ELITES) {
    await go(25, x - 3, y + 3);
    await page.waitForFunction(k => Field.slimes.some(s => s.kind === k), kind, { timeout: 15000 });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(out, `elite-${kind}.png`) });
    check(await page.evaluate(k => Field.slimes.find(s => s.kind === k)?.d?.name?.length > 3, kind), `${kind} is on the map with a name`);
  }
  check(await page.evaluate(() => Field.slimes.find(s => s.kind === 'cobaltbasilisk')?.d?.name) === 'Cobalt Basilisk', 'the new elite is named the Cobalt Basilisk');
  for (const [id, x, y] of [['oasis-wells', 61, 188], ['mirrored-oasis', 118, 144], ['eastern-oasis', 209, 158], ['astrolabe', 130, 70], ['astrolabe-far', 142, 78], ['salt-arch', 100, 51]]) { await go(25, x, y); await page.screenshot({ path: path.join(out, `${id}.png`) }); }
  for (const g of Z.portals) { const wk = g.walk || [0, 1]; await go(25, g.x - wk[0] * 6, g.y - wk[1] * 6); await page.screenshot({ path: path.join(out, `gate-${g.id}.png`) }); }
  // ---- the Wheel Wall: stand 15 tiles inland of it at three places (past the occlusion fade) for the pictures, then hold the key toward it and stay inside
  const edge = Z.shape.edges.find(e => e.kind === 'shared' && e.other === 28).points;
  const distBorder = (x, y) => { let best = 1e9; for (let i = 0; i < edge.length - 1; i++) { const [ax, ay] = edge[i], [bx, by] = edge[i + 1], dx = bx - ax, dy = by - ay, t = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy))); best = Math.min(best, Math.hypot(x - ax - t * dx, y - ay - t * dy)); } return best; };
  let walked = 0;
  const spots = [];
  for (let k = 1; k < edge.length - 2; k++) for (const f of [.3, .7]) {
    const a = edge[k], b = edge[k + 1], len = Math.hypot(b[0] - a[0], b[1] - a[1]);
    const q = [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f];
    let nrm = [-(b[1] - a[1]) / len, (b[0] - a[0]) / len];
    if (!onFloor(Z, q[0] + nrm[0] * 8, q[1] + nrm[1] * 8)) nrm = [-nrm[0], -nrm[1]];
    const sx = q[0] + nrm[0] * 8, sy = q[1] + nrm[1] * 8;
    // a palm or a stone on the way would stop the walk, not the wall: the lane from the start to the border must hold only wall pieces
    const lane = [0, 2, 4, 6, 7].map(t => [q[0] + nrm[0] * (8 - t), q[1] + nrm[1] * (8 - t)]);
    if (onFloor(Z, sx, sy) && !solids.some(o => o.kind !== 'rampart' && o.kind !== 'tower' && lane.some(([x, y]) => Math.hypot(o.x - x, o.y - y) < Math.max(o.r || 0, (o.width || 0) / 2) + 1.6))) spots.push({ k, q, nrm, sx, sy });
  }
  check(spots.length >= 3, `${spots.length} clear lanes lead to the wall`);
  for (const sp of [spots[0], spots[Math.floor(spots.length / 2)], spots[spots.length - 1]]) {
    const { k, q, nrm, sx, sy } = sp;
    await go(25, q[0] + nrm[0] * 15, q[1] + nrm[1] * 15, 2500);
    await page.screenshot({ path: path.join(out, `wall-${k}-far.png`) });
    await go(25, sx, sy, 800);
    const keys = keysFor([-nrm[0], -nrm[1]]);
    for (const key of keys) await page.keyboard.down(key);
    await page.waitForTimeout(6000);
    for (const key of keys) await page.keyboard.up(key);
    await page.waitForTimeout(400);
    const p = await where(), d = distBorder(p.x, p.y);
    await page.screenshot({ path: path.join(out, `wall-${k}-pressed.png`) });
    check(p.zone === 25 && d > 1.2 && d < 8, `holding the key toward the Yearwheel at wall point ${k} stops the hero ${d.toFixed(1)} tiles from the border, still in the Lapis Erg`);
    walked++;
  }
  check(walked >= 2, `the wall was walked into at ${walked} places`);
  check(errors.length === 0, 'no page errors: ' + errors.slice(0, 3).join(' | '));
  console.log(JSON.stringify({ passed: true, checks }));
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => { await browser?.close(); server?.kill(); });
