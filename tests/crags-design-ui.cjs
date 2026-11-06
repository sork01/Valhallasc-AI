// The Emberfall Crags as an authored map (scripts/crags_design.py): the real client names each region, draws its ground, peaks and lava,
// the outposts are sanctuaries with their own title, the two new elites draw from their own art, and nothing pops in at the Crags' seams.
// Pictures in test-results/crags-design/.
//   REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/crags-design-ui.cjs            regions, outposts, elites
//   SEAMS=1 REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/crags-design-ui.cjs    the same point from both frames of every seam
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'test-results/crags-design');
fs.mkdirSync(out, { recursive: true });
const port = 19200 + (process.pid % 400);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'crags-'));
let server, browser, checks = 0;
const check = (v, l) => { assert.ok(v, l); checks++; console.log('ok', l); };
const SPOTS = [
  ['shelf', 186, 218, 'The Cinderwatch Shelf'], ['flats', 150, 268, 'The Sunpit Flats'], ['quarry', 112, 316, 'The Anvil Quarries'], ['wallfoot', 44, 262, 'The Wallfoot'],
  ['slopes', 262, 300, 'The Red Slopes'], ['reach', 322, 170, 'The Hearth Reach'], ['horned', 238, 176, 'The Horned Terrace'], ['steps', 140, 160, 'The Long Steps'],
  ['highfire', 138, 108, 'Highfire Ridge'], ['crown', 130, 44, 'The Ashen Crown'], ['spurs', 34, 128, 'The Steaming Spurs'], ['glass', 300, 116, 'The Glass Shore'],
];
const OUTPOSTS = [['anvilrest', 118, 293, 'Anvilrest'], ['ashford', 197, 155, 'Ashford'], ['lasthearth', 305, 207, 'Lasthearth']];
const ELITES = [['slagmaw', 214, 326], ['ashwing', 112, 32], ['cinderlord', 246, 160]];
(async () => {
  server = spawn(process.env.VALHALLA_BINARY, [], { cwd: root, stdio: 'ignore',
    env: { ...process.env, VALHALLA_BIND: `127.0.0.1:${port}`, VALHALLA_DB: path.join(tmp, 'v.sqlite'), VALHALLA_CLIENT_DIR: path.join(root, 'client'), VALHALLA_TEST_COMMANDS: '1', VALHALLA_GOD_MODE: '1', VALHALLA_START_LEVEL: '10', VALHALLA_LEVEL_SPREAD: '0' } });
  for (let i = 0; i < 100; i++) { try { if ((await fetch(`http://127.0.0.1:${port}/health`)).ok) break; } catch (_) {} await new Promise(r => setTimeout(r, 200)); }
  browser = await chromium.launch({ headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' })).newPage();
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => { localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {} })); });
  await page.goto(`http://127.0.0.1:${port}/`); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('CragWalker'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  const debug = c => page.evaluate(x => Online.send({ type: 'debug', command: x }), c);
  const go = async (x, y) => { await debug({ op: 'teleport', zone: 1, x, y }); await page.waitForFunction(([a, b]) => Field.zone === 1 && Math.hypot(Field.hero.nx - a, Field.hero.ny - b) < 2, [x, y], { timeout: 20000 }); await page.waitForTimeout(1800); };
  await debug({ op: 'set_time', hour: 12, freeze: true }); await debug({ op: 'set_weather', kind: 'clear' });
  if (!process.env.SEAMS) {
    for (const [id, x, y, name] of SPOTS) {
      await go(x, y);
      check(await page.evaluate(() => Field.areaName) === name, `${id}: the HUD names ${name}`);
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
      await page.waitForTimeout(1200);
      await page.screenshot({ path: path.join(out, `elite-${kind}.png`) });
      check(await page.evaluate(k => Field.slimes.find(s => s.kind === k)?.d?.name?.length > 3, kind), `${kind} is on the map with a name`);
    }
    for (const [id, x, y] of [['river', 130, 128], ['ford', 180, 239], ['sunpit', 186, 286], ['peak', 118, 234]]) { await go(x, y); await page.screenshot({ path: path.join(out, `${id}.png`) }); }
    await page.locator('#fieldcv').waitFor();
  } else {
    await page.evaluate(() => { if (window.DayNight) DayNight.draw = () => {}; if (window.Weather) for (const k of Object.keys(Weather)) if (/^draw/.test(k) && typeof Weather[k] === 'function') Weather[k] = () => {}; });
    const W = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8')), Z = W.zones[0], land = (x, y) => Z.shapeFloor[Math.floor(y)]?.[Math.floor(x)] === '#';
    for (const portal of Z.portals.filter(p => p.seam)) {
      const pts = portal.seam.points, [sx, sy] = portal.seam.shift, to = portal.to;
      for (const f of [.3, .5, .7]) {
        const k = Math.floor((pts.length - 1) * f), a = pts[k], b = pts[k + 1], len = Math.hypot(b[0] - a[0], b[1] - a[1]);
        const P = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]; let n = [-(b[1] - a[1]) / len, (b[0] - a[0]) / len];
        if (!land(P[0] + n[0] * 5, P[1] + n[1] * 5)) n = [-n[0], -n[1]];
        const grid = []; for (let i = -4; i <= 4; i++) for (let j = -4; j <= 4; j++) grid.push([i * 2.5, j * 2.5]);
        const look = async (zone, x, y, cx, cy) => {
          await debug({ op: 'teleport', zone, x, y });
          await page.waitForFunction(([z, p, q]) => Field.zone === z && Math.hypot(Field.hero.nx - p, Field.hero.ny - q) < 1.5, [zone, x, y], { timeout: 20000 });
          const sample = () => page.evaluate(([px, py, g2]) => { const cv = document.getElementById('fieldcv'), g = cv.getContext('2d');
            return { scene: Field.sceneAround(px, py, 18), px: g2.map(([i, j]) => { const [fx, fy] = Field.screenOf(px + i, py + j); return [...g.getImageData(Math.round(fx * cv.width), Math.round(fy * cv.height), 1, 1).data].slice(0, 3); }) }; }, [cx, cy, grid]);
          let last = null, cur = null;
          for (let q = 0; q < 20; q++) {
            await page.waitForTimeout(1500); cur = await sample();
            if (last && cur.px.filter((c, i) => Math.hypot(c[0] - last.px[i][0], c[1] - last.px[i][1], c[2] - last.px[i][2]) > 40).length <= 3) break;
            last = cur;
          }
          return cur;
        };
        const C = await look(1, P[0] + n[0] * 7.5, P[1] + n[1] * 7.5, P[0], P[1]);
        const A = await look(1, P[0] + n[0] * 2.5, P[1] + n[1] * 2.5, P[0], P[1]);
        await page.screenshot({ path: path.join(out, `seam-${to}-${f}-crags.png`) });
        const B = await look(to, P[0] + sx - n[0] * 2.5, P[1] + sy - n[1] * 2.5, P[0] + sx, P[1] + sy);
        await page.screenshot({ path: path.join(out, `seam-${to}-${f}-other.png`) });
        const near = (o, L, dx, dy) => L.some(q => q[0] === o[0] && Math.hypot(q[1] - o[1] - dx, q[2] - o[2] - dy) < .6);
        const onlyA = A.scene.filter(o => !near(o, B.scene, sx, sy)), onlyB = B.scene.filter(o => !near(o, A.scene, -sx, -sy));
        const d = A.px.map((c, i) => Math.hypot(c[0] - B.px[i][0], c[1] - B.px[i][1], c[2] - B.px[i][2])), off = d.filter(v => v > 40).length;
        const dc = A.px.map((c, i) => Math.hypot(c[0] - C.px[i][0], c[1] - C.px[i][1], c[2] - C.px[i][2])), offC = dc.filter(v => v > 40).length;
        console.log(`seam 1-${to} at ${f}: ${A.scene.length}/${B.scene.length} objects, only crags ${onlyA.map(o => o[0]).join(',') || '-'}, only other ${onlyB.map(o => o[0]).join(',') || '-'}; ${off}/${d.length} grid points off (control ${offC})`);
        check(onlyA.length + onlyB.length === 0, `seam 1-${to} at ${f}: same scenery from both frames`);
        check(off <= offC + 8, `seam 1-${to} at ${f}: no more pixels differ across the seam than for a camera move (${off} vs ${offC})`);
      }
    }
  }
  check(errors.length === 0, 'no page errors: ' + errors.slice(0, 3).join(' | '));
  console.log(JSON.stringify({ passed: true, checks }));
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => { await browser?.close(); server?.kill(); });
