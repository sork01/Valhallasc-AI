// Astralhollow as an authored basin (scripts/astral_design.py): the real client names each of the thirteen regions, draws its own ground class, the three
// outposts name themselves, and the three new elites draw from their art. Pictures in test-results/astral-design/.
//   REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/astral-design-ui.cjs
//   MUTATE=1 ... serves the pilot's previous client/field.js: the ground-class checks must fail.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn, execSync } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'test-results/astral-design');
fs.mkdirSync(out, { recursive: true });
const port = 19600 + (process.pid % 400);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'astral-'));
let server, browser, checks = 0;
const check = (v, l) => { assert.ok(v, l); checks++; console.log('ok', l); };
const VERSION = /Beta \d+\.\d+\.\d+/.exec(fs.readFileSync(path.join(root, 'client/index.html'), 'utf8'))[0];
const OUTPOSTS = [['court', 172, 296, 'Astralhollow'], ['choirrest', 120, 194, 'Choir Rest'], ['cometwatch', 222, 178, 'Cometwatch'], ['fallstone', 172, 50, 'Fallstone Hold']];
const ELITES = [['cometmaw', 246, 142], ['eclipsequeen', 112, 76], ['orbitwarden', 178, 150]];
// regions that paint their own ground class, and what the pixel beside the hero must be: [region name, darker than, lighter than] as luminance
const GROUND = { 'The Cometfield': [null, 130] };
(async () => {
  server = spawn(process.env.VALHALLA_BINARY, [], { cwd: root, stdio: 'ignore',
    env: { ...process.env, VALHALLA_BIND: `127.0.0.1:${port}`, VALHALLA_DB: path.join(tmp, 'v.sqlite'), VALHALLA_CLIENT_DIR: path.join(root, 'client'), VALHALLA_TEST_COMMANDS: '1', VALHALLA_GOD_MODE: '1', VALHALLA_START_LEVEL: '40', VALHALLA_LEVEL_SPREAD: '0' } });
  for (let i = 0; i < 100; i++) { try { if ((await fetch(`http://127.0.0.1:${port}/health`)).ok) break; } catch (_) {} await new Promise(r => setTimeout(r, 200)); }
  browser = await chromium.launch({ headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' })).newPage();
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  if (process.env.MUTATE) {
    const old = execSync('git show feat/zone-shapes:client/field.js', { cwd: root, maxBuffer: 1 << 26 });
    await page.route('**/field.js*', r => r.fulfill({ status: 200, contentType: 'application/javascript', body: old }));
  }
  await page.addInitScript(v => { localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {} })); localStorage.setItem('valhallasc.whats-new.v1', v); }, VERSION);
  await page.goto(`http://127.0.0.1:${port}/`); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('StarWalker'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  const debug = c => page.evaluate(x => Online.send({ type: 'debug', command: x }), c);
  const go = async (x, y) => { await debug({ op: 'teleport', zone: 13, x, y }); await page.waitForFunction(([a, b]) => Field.zone === 13 && Math.hypot(Field.hero.nx - a, Field.hero.ny - b) < 2, [x, y], { timeout: 20000 }); await page.waitForTimeout(1800); };
  await debug({ op: 'set_time', hour: 12, freeze: true }); await debug({ op: 'set_weather', kind: 'clear' });
  const W = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8')), Z = W.zones[12];
  const cells = new Uint8Array(Z.size * Z.size); for (const [ry, a, b, k] of Z.regions.spans) cells.fill(k, ry * Z.size + a, ry * Z.size + b + 1);
  check(Z.regions.names.length === 13, 'thirteen regions');
  const solids = Z.objects.filter(o => o.kind !== 'void' && (o.r > 0 || o.width > 0));
  const towns = [Z.city, ...Z.camps].map(c => [c.x0 - 6, c.y0 - 6, c.x1 + 6, c.y1 + 6]);
  const clear = (x, y) => Z.shapeFloor[y]?.[x] === '#' && !towns.some(t => x >= t[0] && x <= t[2] && y >= t[1] && y <= t[3]) && solids.every(o => Math.hypot(o.x - x - .5, o.y - y - .5) > Math.max(o.r || 0, (o.width || 0) / 2 + .4) + 4);
  const lum = c => c[0] * .3 + c[1] * .59 + c[2] * .11;
  for (const [k, name] of Z.regions.names.entries()) {
    if (name === 'The Observatory Court') continue;           // the court is the town: it names itself
    const mine = []; for (let y = 0; y < Z.size; y += 2) for (let x = 0; x < Z.size; x += 2) if (cells[y * Z.size + x] === k + 1 && Z.shapeFloor[y]?.[x] === '#') mine.push([x, y]);
    const mx = mine.reduce((s, c) => s + c[0], 0) / mine.length, my = mine.reduce((s, c) => s + c[1], 0) / mine.length;
    mine.sort((p, q) => Math.hypot(p[0] - mx, p[1] - my) - Math.hypot(q[0] - mx, q[1] - my));
    const at = mine.find(([x, y]) => clear(x, y) && cells[y * Z.size + x] === k + 1);
    assert.ok(at, `an open spot in ${name}`);
    const [x, y] = at, id = name.toLowerCase().replace(/[^a-z]+/g, '-');
    await go(x, y);
    check(await page.evaluate(() => Field.areaName) === name, `${id}: the HUD names ${name}`);
    if (GROUND[name]) {
      const px = await page.evaluate(([a, b]) => { const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), L = [];
        for (const i of [-3, 0, 3]) for (const j of [-3, 0, 3]) { const [fx, fy] = Field.screenOf(a + i + .5, b + j + .5); const c = g.getImageData(Math.round(fx * cv.width), Math.round(fy * cv.height), 1, 1).data; L.push([c[0], c[1], c[2], c[0] * .3 + c[1] * .59 + c[2] * .11]); }
        L.sort((p, q) => p[3] - q[3]); return L[4].slice(0, 3); }, [x, y]);      // the median of nine points: a tree or a stone covers some of them, never most
      const [dark, light] = GROUND[name];
      check((dark === null || lum(px) < dark) && (light === null || lum(px) > light), `${name}: the ground is its own class (luminance ${lum(px).toFixed(0)})`);
    }
    await page.screenshot({ path: path.join(out, `${id}.png`) });
  }
  for (const [id, x, y, name] of OUTPOSTS) {
    await go(x, y);
    check(await page.evaluate(n => Field.areaName === n && document.getElementById('area-title').textContent.includes(n), name), `${id}: the title says ${name}`);
    await page.screenshot({ path: path.join(out, `${id}.png`) });
  }
  for (const [kind, x, y] of ELITES) {
    await go(x - 3, y + 3);
    await page.waitForFunction(k => Field.slimes.some(s => s.kind === k), kind, { timeout: 15000 });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(out, `elite-${kind}.png`) });
    check(await page.evaluate(k => Field.slimes.find(s => s.kind === k)?.d?.name?.length > 3, kind), `${kind} is on the map with a name`);
  }
  check((await fetch(`http://127.0.0.1:${port}/assets/astralelites.txt`)).ok, 'the elites\' art is served');
  for (const g of Z.portals) { await go(g.x - g.walk[0] * 6, g.y - g.walk[1] * 6); await page.screenshot({ path: path.join(out, `gate-${g.id}.png`) }); }
  check(errors.length === 0, 'no page errors: ' + errors.slice(0, 3).join(' | '));
  console.log(JSON.stringify({ passed: true, checks }));
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => { await browser?.close(); server?.kill(); });
