// Greenmeadow as an authored map (scripts/greenmeadow_design.py): the real client names each region, draws its ground and scenery,
// the hamlets are sanctuaries with their own title, the three elites draw from their own art. Pictures in test-results/greenmeadow/.
//   REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/greenmeadow-ui.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'test-results/greenmeadow');
fs.mkdirSync(out, { recursive: true });
const port = 18800 + (process.pid % 400);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'meadow-'));
let server, browser, checks = 0;
const check = (v, l) => { assert.ok(v, l); checks++; console.log('ok', l); };
const SPOTS = [
  ['fields', 248, 214, 'Alderhaven Fields'], ['oldgrove', 150, 182, 'The Oldgrove'], ['pasture', 124, 150, 'The Wallside Pasture'], ['downs', 62, 214, 'The Westerling Downs'],
  ['strand', 130, 270, 'The Saltgrass Strand'], ['scarp', 300, 126, 'The Ironhide Scarp'], ['meres', 352, 166, 'The Three Meres'], ['orchard', 318, 214, 'The Applewick Orchards'],
  ['hollowend', 352, 298, 'Hollowend'],
];
const HAMLETS = [['stonefold', 92, 227, 'Stonefold'], ['saltby', 190, 275, 'Saltby'], ['applewick', 345, 235, 'Applewick']];
const ELITES = [['oldtusker', 128, 172], ['tidecrusher', 232, 278], ['orchardqueen', 392, 226]];
(async () => {
  server = spawn(process.env.VALHALLA_BINARY, [], { cwd: root, stdio: 'ignore',
    env: { ...process.env, VALHALLA_BIND: `127.0.0.1:${port}`, VALHALLA_DB: path.join(tmp, 'v.sqlite'), VALHALLA_CLIENT_DIR: path.join(root, 'client'), VALHALLA_TEST_COMMANDS: '1', VALHALLA_GOD_MODE: '1' } });
  for (let i = 0; i < 100; i++) { try { if ((await fetch(`http://127.0.0.1:${port}/health`)).ok) break; } catch (_) {} await new Promise(r => setTimeout(r, 200)); }
  browser = await chromium.launch({ headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' })).newPage();
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => { localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {} })); });
  await page.goto(`http://127.0.0.1:${port}/`); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('MeadowWalker'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  const debug = c => page.evaluate(x => Online.send({ type: 'debug', command: x }), c);
  const go = async (x, y) => { await debug({ op: 'teleport', zone: 0, x, y }); await page.waitForFunction(([a, b]) => Field.zone === 0 && Math.hypot(Field.hero.nx - a, Field.hero.ny - b) < 2, [x, y], { timeout: 20000 }); await page.waitForTimeout(1400); };
  if (process.env.SEAMS) { SPOTS.length = 0; HAMLETS.length = 0; ELITES.length = 0; }
  for (const [id, x, y, name] of SPOTS) {
    await go(x, y);
    check(await page.evaluate(() => Field.areaName) === name, `${id}: the HUD names ${name}`);
    await page.screenshot({ path: path.join(out, `${id}.png`) });
  }
  for (const [id, x, y, name] of HAMLETS) {
    await go(x, y);
    check(await page.evaluate(n => document.getElementById('area-title').textContent.includes(n) && Field.areaName === n, name), `${id}: the title says ${name}`);
    await page.screenshot({ path: path.join(out, `${id}.png`) });
  }
  for (const [kind, x, y] of ELITES) {
    await go(x - 3, y + 3);
    await page.waitForFunction(k => Field.slimes.some(s => s.kind === k), kind, { timeout: 15000 });
    await page.waitForTimeout(1200);
    await page.screenshot({ path: path.join(out, `elite-${kind}.png`) });
    check(await page.evaluate(k => Field.slimes.find(s => s.kind === k)?.d?.name?.length > 3, kind), `${kind} is on the map with a name`);
  }
  // Nothing pops in on crossing: from the Canopy, the meadow's art-drawn scenery already stands beyond the seam.
  const seam = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8')).zones[15].portals.find(p => p.to === 0 && p.seam);
  await debug({ op: 'teleport', zone: 16, x: seam.x + 5, y: seam.y }); await page.waitForFunction(() => Field.zone === 16, null, { timeout: 20000 }); await page.waitForTimeout(2500);
  const kinds = await page.evaluate(() => Field.ghostKinds);
  check(await page.evaluate(() => Field.ghostWater) > 10, 'the meadow ponds show across the seam');
  check(['oak_tree', 'birch_tree', 'hawthorn_bush', 'wildflowers'].filter(k => kinds[k]).length >= 2, `meadow art scenery ghosts across the seam: ${JSON.stringify(kinds)}`);
  // The same world point from both frames of every meadow seam: object by object, and pixel by pixel on a grid (owner: seamless means measured).
  // Light and weather change with time and differ per zone (not handled at a crossing, docs/zone-shapes-pilot.md): ground and scenery are what is compared.
  await page.evaluate(() => { if (window.DayNight) DayNight.draw = () => {}; if (window.Weather) for (const k of Object.keys(Weather)) if (/^draw/.test(k) && typeof Weather[k] === 'function') Weather[k] = () => {}; });
  const W = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8')), land = (x, y) => W.shapeFloor[Math.floor(y)]?.[Math.floor(x)] === '#';
  for (const portal of W.portals.filter(p => p.seam)) {
    const pts = portal.seam.points, [sx, sy] = portal.seam.shift, to = portal.to;
    for (const f of [.3, .5, .7]) {
      const k = Math.floor((pts.length - 1) * f), a = pts[k], b = pts[k + 1], len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const P = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]; let n = [-(b[1] - a[1]) / len, (b[0] - a[0]) / len];
      if (!land(P[0] + n[0] * 5, P[1] + n[1] * 5)) n = [-n[0], -n[1]];
      const grid = []; for (let i = -4; i <= 4; i++) for (let j = -4; j <= 4; j++) grid.push([i * 2.5, j * 2.5]);
      const look = async (zone, x, y, cx, cy) => {
        await debug({ op: 'teleport', zone, x, y });
        await page.waitForFunction(([z, a, b]) => Field.zone === z && Math.hypot(Field.hero.nx - a, Field.hero.ny - b) < 1.5, [zone, x, y], { timeout: 20000 });
        // Ground chunks build a few per frame after a long jump: sample until the picture stops changing.
        const sample = () => page.evaluate(([cx, cy, grid]) => { const cv = document.getElementById('fieldcv'), g = cv.getContext('2d');
          return { scene: Field.sceneAround(cx, cy, 18), px: grid.map(([i, j]) => { const [fx, fy] = Field.screenOf(cx + i, cy + j); return [...g.getImageData(Math.round(fx * cv.width), Math.round(fy * cv.height), 1, 1).data].slice(0, 3); }) }; }, [cx, cy, grid]);
        let last = null, cur = null;
        for (let k = 0; k < 20; k++) {
          await page.waitForTimeout(1500); cur = await sample();
          if (last && cur.px.filter((c, i) => Math.hypot(c[0] - last.px[i][0], c[1] - last.px[i][1], c[2] - last.px[i][2]) > 40).length <= 3) break;
          last = cur;
        }
        return cur;
      };
      // Control: the same points in the same zone, seen from five tiles further in. No seam at all: this is what the probe reads for a camera move alone.
      const C = await look(0, P[0] + n[0] * 7.5, P[1] + n[1] * 7.5, P[0], P[1]);
      const A = await look(0, P[0] + n[0] * 2.5, P[1] + n[1] * 2.5, P[0], P[1]);
      await page.screenshot({ path: path.join(out, `seam-${to}-${f}-meadow.png`) });
      const B = await look(to, P[0] + sx - n[0] * 2.5, P[1] + sy - n[1] * 2.5, P[0] + sx, P[1] + sy);
      await page.screenshot({ path: path.join(out, `seam-${to}-${f}-other.png`) });
      const near = (o, L, dx, dy) => L.some(q => q[0] === o[0] && Math.hypot(q[1] - o[1] - dx, q[2] - o[2] - dy) < .6);
      const onlyA = A.scene.filter(o => !near(o, B.scene, sx, sy)), onlyB = B.scene.filter(o => !near(o, A.scene, -sx, -sy));
      const d = A.px.map((c, i) => Math.hypot(c[0] - B.px[i][0], c[1] - B.px[i][1], c[2] - B.px[i][2])), off = d.filter(v => v > 40).length;
      const dc = A.px.map((c, i) => Math.hypot(c[0] - C.px[i][0], c[1] - C.px[i][1], c[2] - C.px[i][2])), offC = dc.filter(v => v > 40).length;
      console.log(`control ${offC}/${dc.length} points off, mean ${(dc.reduce((p, c) => p + c, 0) / dc.length).toFixed(1)}`);
      console.log(`seam 0-${to} at ${f}: ${A.scene.length}/${B.scene.length} objects, only meadow ${onlyA.map(o => o[0]).join(',') || '-'}, only other ${onlyB.map(o => o[0]).join(',') || '-'}; mean colour diff ${(d.reduce((p, c) => p + c, 0) / d.length).toFixed(1)}, ${off}/${d.length} grid points off`);
      check(onlyA.length + onlyB.length === 0, `seam 0-${to} at ${f}: same scenery from both frames`);
      check(off <= offC + 8, `seam 0-${to} at ${f}: no more pixels differ across the seam than for a camera move inside the zone (${off} vs ${offC})`);
    }
  }
  check(errors.length === 0, 'no page errors: ' + errors.join(' | '));
  console.log(`greenmeadow-ui: ${checks} checks passed`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => { await browser?.close(); server?.kill(); fs.rmSync(tmp, { recursive: true, force: true }); });
