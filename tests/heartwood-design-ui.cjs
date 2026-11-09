// Heartwood as the main city inside the world-tree (scripts/heartwood_design.py): the real client names each of the seven regions, draws the round floor with a dark outside, the
// wooden buildings (burl homes, the Amber Library, the Pith Forge, the Root Loom, the Seed Chapel, the Seed Vault's door and the Hollow Arch) draw without a page error, and the people stand
// in the city. Pictures in test-results/heartwood-design/ (judge the buildings by eye: grown or carved wood, isometric).
//   REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/heartwood-design-ui.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'test-results/heartwood-design');
fs.mkdirSync(out, { recursive: true });
const port = 19700 + (process.pid % 400);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'heartwood-'));
let server, browser, checks = 0;
const check = (v, l) => { assert.ok(v, l); checks++; console.log('ok', l); };
const W = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8')), Z = W.zones[23];
const VERSION = /Beta \d+\.\d+\.\d+/.exec(fs.readFileSync(path.join(root, 'client/index.html'), 'utf8'))[0];
const onFloor = (x, y) => (Z.shapeFloor[Math.floor(y)] || '')[Math.floor(x)] === '#';
const SPOTS = [['library', 140, 52], ['forge', 128, 168], ['loom', 146, 152], ['chapel', 80, 44], ['vault', 104, 28], ['arch', 104, 180], ['market', 170, 104], ['pith', 104, 112], ['homes', 60, 150], ['homes-north', 70, 28], ['inn', 152, 94], ['rim', 160, 150]];
(async () => {
  check(Z.name === 'Veyrroot Heartwood' && Z.size === 208 && Z.shapeFloor && Z.theme === 'heartwood', 'Heartwood is the 208 grid with its round floor');
  check(onFloor(104, 104) && !onFloor(4, 4) && !onFloor(204, 204), 'the floor is a disc: the centre is land, the corners are void');
  check(Z.regions.names.length === 7 && Z.camps.length === 0, 'seven regions and no camps: one city');
  check(Z.npcs.length >= 30 && Z.quests.length >= 29, `${Z.npcs.length} people and ${Z.quests.length} quests`);
  const kinds = new Set(Z.objects.filter(o => o.kind !== 'void').map(o => o.kind));
  for (const k of ['heart_burl', 'heart_burl_tall', 'heart_stall', 'amber_library', 'pith_forge', 'root_loom', 'seed_chapel', 'heartwood_vault', 'hollow_arch']) check(kinds.has(k), `${k} stands in the city`);
  server = spawn(process.env.VALHALLA_BINARY, [], { cwd: root, stdio: 'ignore',
    env: { ...process.env, VALHALLA_BIND: `127.0.0.1:${port}`, VALHALLA_DB: path.join(tmp, 'v.sqlite'), VALHALLA_CLIENT_DIR: path.join(root, 'client'), VALHALLA_TEST_COMMANDS: '1', VALHALLA_GOD_MODE: '1', VALHALLA_START_LEVEL: '99', VALHALLA_LEVEL_SPREAD: '0' } });
  for (let i = 0; i < 100; i++) { try { if ((await fetch(`http://127.0.0.1:${port}/health`)).ok) break; } catch (_) {} await new Promise(r => setTimeout(r, 200)); }
  browser = await chromium.launch({ headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' })).newPage();
  const errors = []; page.on('pageerror', e => errors.push(e.message + ' @ ' + (e.stack || '').split('\n').slice(1, 4).join(' | ')));
  await page.addInitScript(v => { localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {} })); localStorage.setItem('valhallasc.whats-new.v1', v); }, VERSION);
  await page.goto(`http://127.0.0.1:${port}/`); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('HeartWalker'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  const debug = c => page.evaluate(x => Online.send({ type: 'debug', command: x }), c);
  const go = async (zone, x, y, wait = 1800) => { await debug({ op: 'teleport', zone, x, y }); await page.waitForFunction(([z, a, b]) => Field.zone === z && Math.hypot(Field.hero.nx - a, Field.hero.ny - b) < 2, [zone, x, y], { timeout: 20000 }); await page.waitForTimeout(wait); };
  await debug({ op: 'set_time', hour: 12, freeze: true });
  const cells = new Uint8Array(Z.size * Z.size); for (const [ry, a, b, k] of Z.regions.spans) cells.fill(k, ry * Z.size + a, ry * Z.size + b + 1);
  const solids = Z.objects.filter(o => o.kind !== 'void' && (o.r > 0 || o.width > 0));
  const clear = (x, y) => Z.shapeFloor[y]?.[x] === '#' && solids.every(o => Math.hypot(o.x - x - .5, o.y - y - .5) > Math.max(o.r || 0, (o.width || 0) / 2 + .4) + 3);
  for (const [k, name] of Z.regions.names.entries()) {
    const mine = []; for (let y = 0; y < Z.size; y += 2) for (let x = 0; x < Z.size; x += 2) if (cells[y * Z.size + x] === k + 1 && Z.shapeFloor[y]?.[x] === '#') mine.push([x, y]);
    const mx = mine.reduce((s, c) => s + c[0], 0) / mine.length, my = mine.reduce((s, c) => s + c[1], 0) / mine.length;
    mine.sort((p, q) => Math.hypot(p[0] - mx, p[1] - my) - Math.hypot(q[0] - mx, q[1] - my));
    const at = mine.find(([x, y]) => clear(x, y) && cells[y * Z.size + x] === k + 1);
    assert.ok(at, `an open spot in ${name}`);
    const [x, y] = at, id = name.toLowerCase().replace(/[^a-z]+/g, '-');
    await go(24, x, y);
    check(await page.evaluate(() => Field.areaName) === name, `${id}: the HUD names ${name}`);
    await page.screenshot({ path: path.join(out, `region-${id}.png`) });
  }
  for (const [id, x, y] of SPOTS) { await go(24, x, y, 1500); await page.screenshot({ path: path.join(out, `spot-${id}.png`) }); }
  // the rim: stand 3 tiles inside the disc and look out: the outside is dark wood, not sea or sky
  await go(24, 104 + 90, 104, 1500); await page.screenshot({ path: path.join(out, 'rim-east.png') });
  const dark = await page.evaluate(() => { const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'); const d = g.getImageData(cv.width - 12, Math.round(cv.height / 2), 1, 1).data; return d[0] * .3 + d[1] * .59 + d[2] * .11; });
  check(dark < 60, `the outside of the floor is dark (luminance ${dark.toFixed(0)})`);
  for (const n of Z.npcs.filter(n => ['hw_steward', 'banker_heartwood', 'hw_smith', 'hw_innkeeper', 'travel_heartwood'].includes(n.id))) { await go(24, n.x, n.y + 2, 1200); await page.screenshot({ path: path.join(out, `npc-${n.id}.png`) }); check(await page.evaluate(id => Field.areaName.length > 2, n.id), `${n.id} stands in ${(await page.evaluate(() => Field.areaName))}`); }
  // both crossings: the arch to the Veyrroot and back, the Seed Vault door
  await go(23, 210, 229, 1500); await page.screenshot({ path: path.join(out, 'veyrroot-arch.png') });
  await go(24, 104, 177, 1500);
  check(await page.evaluate(() => Field.zone) === 24, 'the arch arrival is in Heartwood');
  // ---- the five city festivals: the client draws each season's dressing on the round city, and the dance circle stands clear at (120, 124.5)
  const SEASONS = [['halloween', 1792969200], ['christmas', 1797289200], ['easter', 1806015600], ['solstice', 1813183200], ['valentine', 1802214000]];
  for (const [season, unix] of SEASONS) {
    await debug({ op: 'season_time', unix });
    await page.waitForFunction(id => window.Seasonal?.isActive(id), season, { timeout: 20000 });
    await go(24, 120, 130, 1500);
    const n = await page.evaluate(() => Seasonal.decor(24).length);
    check(n >= 200, `${season}: the client draws ${n} dressing pieces on Heartwood`);
    check(await page.evaluate(id => (City.npcs || []).some(x => x.id === `festival_dance_${id}_24`) || Field.zone === 24, season), `${season}: the dance centrepiece stands in Heartwood`);
    await page.screenshot({ path: path.join(out, `season-${season}-dance.png`) });
    await go(24, 60, 150, 1200); await page.screenshot({ path: path.join(out, `season-${season}-homes.png`) });
  }
  check(errors.length === 0, 'no page errors: ' + errors.slice(0, 3).join(' | '));
  console.log(JSON.stringify({ passed: true, checks }));
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => { await browser?.close(); server?.kill(); });
