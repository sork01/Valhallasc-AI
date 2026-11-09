// The Veyrroot Canopy as an authored WILD map (scripts/veyrroot_design.py): the real client names each of the fourteen regions, draws its ground classes (pale pollen glade against deep
// fern shade), the five hubs name themselves, the three elites draw from their art, the Sunward gate and the Hollow Arch stand on the floor, and the two borders to the Tanglecrown and the
// Lapis Erg are seams: a held key walks over each and the hero ends up in the neighbour, and walks back. Pictures in test-results/veyrroot-design/.
//   REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/veyrroot-design-ui.cjs
//   MUTATE=1 serves the pilot's previous client/field.js (before the Veyrroot's ground classes): the ground-class check must fail.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn, execSync } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'test-results/veyrroot-design');
fs.mkdirSync(out, { recursive: true });
const port = 19700 + (process.pid % 400);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'veyrroot-'));
let server, browser, checks = 0;
const check = (v, l) => { assert.ok(v, l); checks++; console.log('ok', l); };
const W = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8')), Z = W.zones[22];
const onFloor = (z, x, y) => (z.shapeFloor[Math.floor(y)] || '')[Math.floor(x)] === '#';
const VERSION = /Beta \d+\.\d+\.\d+/.exec(fs.readFileSync(path.join(root, 'client/index.html'), 'utf8'))[0];
const HUBS = [['rootfoot', 210, 241, 'Rootfoot'], ['lookout', 252, 146, 'Sunleaf Lookout'], ['gladewatch', 100, 192, 'Gladewatch Post'], ['rootstair', 206, 98, 'Rootstair Post'], ['eastbark', 296, 198, 'Eastbark Post']];
const ELITES = [['lanternqueen', 132, 104, 'Lantern Queen'], ['barkcolossus', 312, 118, 'Heartbark Colossus'], ['ambergolem', 262, 266, 'Amber Sap Golem']];
// regions whose ground classes are compared: the pale pollen glade against the deep fern shade (the old client painted the whole zone one green)
const GROUND = ['The Sunlit Glade', 'The Fernbreak'], lums = {};
(async () => {
  check(Z.name === 'Veyrroot Canopy' && Z.size === 352 && Z.shapeFloor && Z.shape.neighbours.join() === '20,22,25', 'the Veyrroot is the 352 grid with its outline and three neighbours');
  const seams = Z.portals.filter(p => p.seam).map(p => p.to).sort();
  check(seams.join() === '22,25', 'the Tanglecrown and the Lapis Erg are seams');
  check(Z.portals.some(p => p.to === 20 && p.walk), 'Sunward Vale is a rim gate you walk through');
  check(Z.portals.some(p => p.id === 'canopy_hollow_gate' && p.to === 24), 'the Hollow Arch leads to Heartwood');
  for (const p of Z.portals) check(onFloor(Z, p.x, p.y) || p.seam, `${p.id} stands on the floor`);
  check(Z.regions.names.length === 14 && Z.camps.length === 4 && Z.quests.length === 25, 'fourteen regions, five hubs and 25 quests');
  server = spawn(process.env.VALHALLA_BINARY, [], { cwd: root, stdio: 'ignore',
    env: { ...process.env, VALHALLA_BIND: `127.0.0.1:${port}`, VALHALLA_DB: path.join(tmp, 'v.sqlite'), VALHALLA_CLIENT_DIR: path.join(root, 'client'), VALHALLA_TEST_COMMANDS: '1', VALHALLA_GOD_MODE: '1', VALHALLA_START_LEVEL: process.env.START_LEVEL || '99', VALHALLA_LEVEL_SPREAD: '0' } });
  for (let i = 0; i < 100; i++) { try { if ((await fetch(`http://127.0.0.1:${port}/health`)).ok) break; } catch (_) {} await new Promise(r => setTimeout(r, 200)); }
  browser = await chromium.launch({ headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' })).newPage();
  const errors = []; page.on('pageerror', e => errors.push(e.message + ' @ ' + (e.stack || '').split('\n').slice(1, 4).join(' | ')));
  if (process.env.MUTATE) {
    const old = execSync('git show b9c59c8:client/field.js', { cwd: root, maxBuffer: 1 << 28 });
    await page.route('**/field.js*', r => r.fulfill({ status: 200, contentType: 'application/javascript', body: old }));
  }
  await page.addInitScript(v => { localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {} })); localStorage.setItem('valhallasc.whats-new.v1', v); }, VERSION);
  await page.goto(`http://127.0.0.1:${port}/`); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('VeyrrootWalker'); await page.locator('#go').click({ timeout: 60000 });
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
    await go(23, x, y);
    check(await page.evaluate(() => Field.areaName) === name, `${id}: the HUD names ${name}`);
    if (GROUND.includes(name)) {
      const px = await page.evaluate(([a, b]) => { const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), L = [];
        for (const i of [-3, 0, 3]) for (const j of [-3, 0, 3]) { const [fx, fy] = Field.screenOf(a + i + .5, b + j + .5); const c = g.getImageData(Math.round(fx * cv.width), Math.round(fy * cv.height), 1, 1).data; L.push([c[0], c[1], c[2], c[0] * .3 + c[1] * .59 + c[2] * .11]); }
        L.sort((p, q) => p[3] - q[3]); return L[4].slice(0, 3); }, [x, y]);      // the median of nine points: a palm or a stone covers some of them, never most
      lums[name] = px[0] * .3 + px[1] * .59 + px[2] * .11; console.log(`${name}: luminance ${lums[name].toFixed(0)}`);
    }
    await page.screenshot({ path: path.join(out, `${id}.png`) });
  }
  check(lums['The Sunlit Glade'] - lums['The Fernbreak'] > 45, `the Sunlit Glade (${lums['The Sunlit Glade'].toFixed(0)}) is much paler than the Fernbreak (${lums['The Fernbreak'].toFixed(0)}): the ground classes are drawn`);
  for (const [id, x, y, name] of HUBS) {
    await go(23, x, y);
    check(await page.evaluate(n => Field.areaName === n && document.getElementById('area-title').textContent.includes(n), name), `${id}: the title says ${name}`);
    await page.screenshot({ path: path.join(out, `${id}.png`) });
  }
  for (const [kind, x, y, nm] of ELITES) {
    await go(23, x - 3, y + 3);
    await page.waitForFunction(k => Field.slimes.some(s => s.kind === k), kind, { timeout: 15000 });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(out, `elite-${kind}.png`) });
    check(await page.evaluate(k => Field.slimes.find(s => s.kind === k)?.d?.name, kind) === nm, `${kind} is on the map named ${nm}`);
  }
  for (const [id, x, y] of [['great-tree', 210, 232], ['arch', 210, 226], ['lookout-far', 252, 156], ['hive', 150, 118], ['twin-roots', 240, 90], ['east-roots', 304, 156], ['sap-flats', 204, 266]]) { await go(23, x, y); await page.screenshot({ path: path.join(out, `${id}.png`) }); }
  for (const g of Z.portals.filter(p => !p.seam)) { const wk = g.walk || [0, 1]; await go(23, g.x - wk[0] * 6, g.y - wk[1] * 6); await page.screenshot({ path: path.join(out, `gate-${g.id}.png`) }); }
  // ---- the two seams: stand three tiles inland of each crossing, hold the key toward the neighbour, end up there; then hold the key back and end up here again
  for (const [other, dy] of [[22, 1], [25, -1]]) {
    const p = Z.portals.find(q => q.to === other && q.seam);
    await go(23, p.x, p.y - dy * 3, 1500);
    await page.screenshot({ path: path.join(out, `seam-${other}-before.png`) });
    let keys = keysFor([0, dy]);
    for (const key of keys) await page.keyboard.down(key);
    await page.waitForFunction(z => Field.zone === z, other, { timeout: 20000 }).catch(() => {});
    for (const key of keys) await page.keyboard.up(key);
    await page.waitForTimeout(600);
    check((await where()).zone === other, `a held key walks over the seam into zone ${other}`);
    await page.screenshot({ path: path.join(out, `seam-${other}-after.png`) });
    keys = keysFor([0, -dy]);
    for (const key of keys) await page.keyboard.down(key);
    await page.waitForFunction(z => Field.zone === z, 23, { timeout: 20000 }).catch(() => {});
    for (const key of keys) await page.keyboard.up(key);
    await page.waitForTimeout(400);
    check((await where()).zone === 23, `a held key walks back over the seam from zone ${other}`);
  }
  check(errors.length === 0, 'no page errors: ' + errors.slice(0, 3).join(' | '));
  console.log(JSON.stringify({ passed: true, checks }));
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => { await browser?.close(); server?.kill(); });
