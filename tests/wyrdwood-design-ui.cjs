// The Wyrdwood as an authored map (scripts/wyrdwood_design.py): the real client names each region, draws its ground, the River Skuld as water,
// the hubs are sanctuaries with their own title, the three elites draw from art, and nothing pops in at the Wyrdwood's seams.
// Pictures in test-results/wyrdwood-design/.
//   REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/wyrdwood-design-ui.cjs            regions, hubs, elites, river
//   SEAMS=1 REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/wyrdwood-design-ui.cjs    the same point from both frames of both seams
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'test-results/wyrdwood-design');
fs.mkdirSync(out, { recursive: true });
const port = 19200 + (process.pid % 400);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'wyrdwood-'));
let server, browser, checks = 0;
const check = (v, l) => { assert.ok(v, l); checks++; console.log('ok', l); };
const OUTPOSTS = [['hollowmoot', 78, 288, 'Hollowmoot'], ['skuldwatch', 166, 209, 'Skuldwatch'], ['gallowsfoot', 255, 300, 'Gallowsfoot'], ['ridgewatch', 180, 146, 'Ridgewatch'], ['highmoor', 150, 115, 'Highmoor Hold']];
const ELITES = [['oakhorn', 248, 262], ['hrungnir', 152, 78], ['hangedking', 308, 318]];
const WATER = [[90, 236, 90, 226], [220, 235, 220, 227], [60, 236, 60, 227]];   // [stand x, y, water x, y]: the River Skuld, from the south bank, west and east of the bridge
(async () => {
  server = spawn(process.env.VALHALLA_BINARY, [], { cwd: root, stdio: 'ignore',
    env: { ...process.env, VALHALLA_BIND: `127.0.0.1:${port}`, VALHALLA_DB: path.join(tmp, 'v.sqlite'), VALHALLA_CLIENT_DIR: path.join(root, 'client'), VALHALLA_TEST_COMMANDS: '1', VALHALLA_GOD_MODE: '1', VALHALLA_START_LEVEL: '10', VALHALLA_LEVEL_SPREAD: '0' } });
  for (let i = 0; i < 100; i++) { try { if ((await fetch(`http://127.0.0.1:${port}/health`)).ok) break; } catch (_) {} await new Promise(r => setTimeout(r, 200)); }
  browser = await chromium.launch({ headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' })).newPage();
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => { localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {} })); });
  await page.goto(`http://127.0.0.1:${port}/`); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('WyrdWalker'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  const debug = c => page.evaluate(x => Online.send({ type: 'debug', command: x }), c);
  const go = async (x, y) => { await debug({ op: 'teleport', zone: 6, x, y }); await page.waitForFunction(([a, b]) => Field.zone === 6 && Math.hypot(Field.hero.nx - a, Field.hero.ny - b) < 2, [x, y], { timeout: 20000 }); await page.waitForTimeout(1800); };
  await debug({ op: 'set_time', hour: 12, freeze: true }); await debug({ op: 'set_weather', kind: 'clear' });
  if (!process.env.SEAMS) {
    const W = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8')), Z = W.zones[5];
    const cells = new Uint8Array(Z.size * Z.size); for (const [ry, a, b, k] of Z.regions.spans) cells.fill(k, ry * Z.size + a, ry * Z.size + b + 1);
    check(Z.regions.names.length === 15, 'fifteen regions');
    // one open spot per region: the land cell nearest the region's middle that stands clear of every object
    const solids = Z.objects.filter(o => o.kind !== 'void' && (o.r > 0 || o.width > 0));
    const towns = [Z.city, ...Z.camps].map(c => [c.x0 - 6, c.y0 - 6, c.x1 + 6, c.y1 + 6]);     // a town names itself, not its region
    const clear = (x, y) => Z.shapeFloor[y]?.[x] === '#' && !towns.some(t => x >= t[0] && x <= t[2] && y >= t[1] && y <= t[3]) && solids.every(o => Math.hypot(o.x - x - .5, o.y - y - .5) > Math.max(o.r || 0, (o.width || 0) / 2 + .4) + 3);
    const SPOTS = Z.regions.names.map((name, k) => {
      const mine = []; for (let y = 0; y < Z.size; y += 2) for (let x = 0; x < Z.size; x += 2) if (cells[y * Z.size + x] === k + 1 && (Z.shapeFloor[y]?.[x] === '#')) mine.push([x, y]);
      const mx = mine.reduce((s, c) => s + c[0], 0) / mine.length, my = mine.reduce((s, c) => s + c[1], 0) / mine.length;
      mine.sort((p, q) => Math.hypot(p[0] - mx, p[1] - my) - Math.hypot(q[0] - mx, q[1] - my));
      const at = mine.find(([x, y]) => clear(x, y) && cells[y * Z.size + x] === k + 1);
      assert.ok(at, `an open spot in ${name}`);
      return [name.toLowerCase().replace(/[^a-z]+/g, '-'), at[0], at[1], name];
    });
    const PLACE_REGION = { wyrd_mill: ['The Ruined Mill'], wyrd_gallows_rock: ['Gallows Hill'], wyrd_hrung_ring: ["Hrungnir's Summit", 'The Highmoor'], wyrd_east_gap: ['The Norn Terrace', 'The Storm Terrace'] };    // the gap and the ring stand on a region border
    for (const p of Z.places.filter(p => PLACE_REGION[p.id])) check(PLACE_REGION[p.id].includes(Z.regions.names[cells[Math.floor(p.y) * Z.size + Math.floor(p.x)] - 1]), `the place ${p.id} lies in the region it is named for`);
    for (const [id, x, y, name] of SPOTS) {
      check(Z.regions.names[cells[y * Z.size + x] - 1] === name, `${id}: the data puts (${x},${y}) in ${name}`);
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
    // the Mere, its side channel and the stream are drawn as water, not as ground: the pixel over them is far darker than the bank beside it
    for (const [sx, sy, x, y] of WATER) {
      await go(sx, sy);
      const px = await page.evaluate(([a, b, p0, q0]) => { const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), at = (p, q) => { const [fx, fy] = Field.screenOf(p, q); return [...g.getImageData(Math.round(fx * cv.width), Math.round(fy * cv.height), 1, 1).data].slice(0, 3); }; return { water: at(a, b), bank: at(p0 + (p0 - a) * .3, q0 + (q0 - b) * .3) }; }, [x, y, sx, sy]);
      const lum = c => c[0] * .3 + c[1] * .59 + c[2] * .11;
      check(px.water[2] > px.water[0] + 12 && lum(px.water) < lum(px.bank) - 6, `the river at (${x},${y}) is blue water (${px.water} against the bank ${px.bank})`);
      await page.screenshot({ path: path.join(out, `water-${x}.png`) });
    }
    for (const [id, x, y] of [['bridge', 166, 232], ['norn', 160, 180], ['east-gap', 222, 163], ['west-gap', 113, 131], ['mill', 316, 322], ['gallows', 302, 318], ['glade', 150, 298], ['cross', 114, 285]]) { await go(x, y); await page.screenshot({ path: path.join(out, `${id}.png`) }); }
    check((await fetch(`http://127.0.0.1:${port}/assets/wyrdelites.txt`)).ok, "the Hanged King's art is served");
    await page.locator('#fieldcv').waitFor();
  } else {
    await page.evaluate(() => { if (window.DayNight) DayNight.draw = () => {}; if (window.Weather) for (const k of Object.keys(Weather)) if (/^draw/.test(k) && typeof Weather[k] === 'function') Weather[k] = () => {}; });
    const W = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8')), Z = W.zones[5], land = (x, y) => Z.shapeFloor[Math.floor(y)]?.[Math.floor(x)] === '#';
    for (const portal of Z.portals.filter(p => p.seam)) {
      const pts = portal.seam.points, [sx, sy] = portal.seam.shift, to = portal.to;
      for (const f of (process.env.FRACS ? process.env.FRACS.split(',').map(Number) : [.3, .5, .7])) {
        const k = Math.floor((pts.length - 1) * f), a = pts[k], b = pts[k + 1], len = Math.hypot(b[0] - a[0], b[1] - a[1]);
        const P = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]; let n = [-(b[1] - a[1]) / len, (b[0] - a[0]) / len];
        if (!land(P[0] + n[0] * 5, P[1] + n[1] * 5)) n = [-n[0], -n[1]];
        const grid = []; for (let i = -4; i <= 4; i++) for (let j = -4; j <= 4; j++) grid.push([i * 2.5, j * 2.5]);
        const look = async (zone, x, y, cx, cy) => {
          await debug({ op: 'teleport', zone, x, y });
          await page.waitForFunction(([z, p, q]) => Field.zone === z && Math.hypot(Field.hero.nx - p, Field.hero.ny - q) < 1.5, [zone, x, y], { timeout: 20000 });
          const sample = () => page.evaluate(([px, py, g2]) => { const cv = document.getElementById('fieldcv'), g = cv.getContext('2d');
            return { scene: Field.sceneAround(px, py, 18), px: g2.map(([i, j]) => { const [fx, fy] = Field.screenOf(px + i, py + j); return [...g.getImageData(Math.round(fx * cv.width), Math.round(fy * cv.height), 1, 1).data].slice(0, 3); }) }; }, [cx, cy, grid]);
          let last = null, cur = null, calm = 0;
          await page.waitForTimeout(+process.env.SETTLE || 1500);                  // a zone entered by teleport builds its neighbours one per tick: wait before the first sample
          for (let q = 0; q < 24; q++) {
            await page.waitForTimeout(1500); cur = await sample();
            if (last && cur.px.filter((c, i) => Math.hypot(c[0] - last.px[i][0], c[1] - last.px[i][1], c[2] - last.px[i][2]) > 40).length <= 3) { if (++calm >= 2) break; } else calm = 0;
            last = cur;
          }
          return cur;
        };
        const C = await look(6, P[0] + n[0] * 7.5, P[1] + n[1] * 7.5, P[0], P[1]);
        const A = await look(6, P[0] + n[0] * 2.5, P[1] + n[1] * 2.5, P[0], P[1]);
        await page.screenshot({ path: path.join(out, `seam-${to}-${f}-wyrd.png`) });
        const B = await look(to, P[0] + sx - n[0] * 2.5, P[1] + sy - n[1] * 2.5, P[0] + sx, P[1] + sy);
        await page.screenshot({ path: path.join(out, `seam-${to}-${f}-other.png`) });
        const near = (o, L, dx, dy) => L.some(q => q[0] === o[0] && Math.hypot(q[1] - o[1] - dx, q[2] - o[2] - dy) < .6);
        const onlyA = A.scene.filter(o => !near(o, B.scene, sx, sy)), onlyB = B.scene.filter(o => !near(o, A.scene, -sx, -sy));
        const d = A.px.map((c, i) => Math.hypot(c[0] - B.px[i][0], c[1] - B.px[i][1], c[2] - B.px[i][2])), off = d.filter(v => v > 40).length;
        const dc = A.px.map((c, i) => Math.hypot(c[0] - C.px[i][0], c[1] - C.px[i][1], c[2] - C.px[i][2])), offC = dc.filter(v => v > 40).length;
        console.log(`seam 6-${to} at ${f}: ${A.scene.length}/${B.scene.length} objects, only wyrdwood ${onlyA.map(o => o[0]).join(',') || '-'}, only other ${onlyB.map(o => o[0]).join(',') || '-'}; ${off}/${d.length} grid points off (control ${offC})`);
        if (off > offC + 8) console.log('mismatch', JSON.stringify(d.map((v, i) => v > 40 ? [grid[i], A.px[i], B.px[i], C.px[i]] : null).filter(Boolean).slice(0, 14)));
        check(onlyA.length + onlyB.length === 0, `seam 6-${to} at ${f}: same scenery from both frames`);
        check(off <= offC + 8, `seam 6-${to} at ${f}: no more pixels differ across the seam than for a camera move (${off} vs ${offC})`);
      }
    }
  }
  check(errors.length === 0, 'no page errors: ' + errors.slice(0, 3).join(' | '));
  console.log(JSON.stringify({ passed: true, checks }));
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => { await browser?.close(); server?.kill(); });
