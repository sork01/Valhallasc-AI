// Emberwake Caldera as an authored map (scripts/ember_design.py): the real client names each of the fourteen regions, draws its ground classes and the molten river, the
// five hubs name themselves, the elites draw from their art, the two rim gates and the raid door stand on the floor, and the two seams (the Stormglass Flats on the north,
// the Moonspore Canopy on the west) are crossed anywhere without a banner, with the neighbour's scenery ready beyond the line and the same world point looking the same.
// Pictures in test-results/ember-design/.
//   REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/ember-design-ui.cjs
//   SEAM_ONLY=1 KS='[7]': only the seams, one point each (the bounded runner's memory and time caps).
//   PARTNERS='[19]' narrows the seam checks to one neighbour.
//   SEAMLESS_SOFT=1 reports instead of failing when the client's seamless flag is not set at the crossing.
//   MUTATE=1 serves the pilot's previous client/emberwakeart.js: the ground-class check must fail.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn, execSync } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'test-results/ember-design');
fs.mkdirSync(out, { recursive: true });
const port = 19600 + (process.pid % 400);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'ember-'));
let server, browser, checks = 0;
const check = (v, l) => { assert.ok(v, l); checks++; console.log('ok', l); };
const W = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8')), Z = W.zones[44];
const onFloor = (z, x, y) => (z.shapeFloor[Math.floor(y)] || '')[Math.floor(x)] === '#';
const VERSION = /Beta \d+\.\d+\.\d+/.exec(fs.readFileSync(path.join(root, 'client/index.html'), 'utf8'))[0];
const HUBS = [['chainrest', 228, 84, 'Chainrest'], ['door', 316, 90, 'Nine-Chain Hold'], ['craterwatch', 100, 128, 'Craterwatch'], ['cinderquay', 186, 312, 'Cinderquay'], ['glasshold', 292, 226, 'Glasshold']];
const ELITES = [['ew_chainmaw', 136, 206], ['ew_bellows', 163, 111], ['ew_crown', 253, 277]];
// regions whose ground classes are compared: pale ash against black sand (the old client painted both the same dark ash)
const GROUND = ['The Ash Verge', 'The Black Shore'], lums = {};
(async () => {
  check(Z.name === 'Emberwake Caldera' && Z.size === 400 && Z.shapeFloor && Z.shape.neighbours.join() === '15,16,19,21', 'Emberwake Caldera is the 400 grid with its outline and four neighbours');
  const seams = Z.portals.filter(p => p.seam);
  check(seams.map(p => p.to).sort().join() === '16,19', 'the only seams are the ones to the Canopy and the Flats');
  for (const to of [15, 21]) check(Z.portals.some(p => p.to === to && p.walk && !p.seam), `the way to zone ${to} is a rim gate you walk through`);
  check(Z.portals.some(p => p.id === 'ew_raid' && p.to === 46 && p.needs_quest === 'raid_key'), 'the raid door keeps its key');
  for (const p of Z.portals.filter(p => !p.seam)) check(onFloor(Z, p.x, p.y), `${p.id} stands on the floor`);
  check(Z.regions.names.length === 14 && Z.camps.length === 4 && Z.quests.length === 26, 'fourteen regions, five hubs and 26 quests');
  server = spawn(process.env.VALHALLA_BINARY, [], { cwd: root, stdio: 'ignore',
    env: { ...process.env, VALHALLA_BIND: `127.0.0.1:${port}`, VALHALLA_DB: path.join(tmp, 'v.sqlite'), VALHALLA_CLIENT_DIR: path.join(root, 'client'), VALHALLA_TEST_COMMANDS: '1', VALHALLA_GOD_MODE: '1', VALHALLA_START_LEVEL: process.env.START_LEVEL || '99', VALHALLA_LEVEL_SPREAD: '0' } });
  for (let i = 0; i < 100; i++) { try { if ((await fetch(`http://127.0.0.1:${port}/health`)).ok) break; } catch (_) {} await new Promise(r => setTimeout(r, 200)); }
  browser = await chromium.launch({ headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' })).newPage();
  const errors = []; page.on('pageerror', e => errors.push(e.message + ' @ ' + (e.stack || '').split('\n').slice(1, 4).join(' | ')));
  if (process.env.MUTATE) {
    const old = execSync('git show feat/zone-shapes-storm:client/emberwakeart.js', { cwd: root, maxBuffer: 1 << 26 });
    await page.route('**/emberwakeart.js*', r => r.fulfill({ status: 200, contentType: 'application/javascript', body: old }));
  }
  await page.addInitScript(v => { localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {} })); localStorage.setItem('valhallasc.whats-new.v1', v);
    const raf = window.requestAnimationFrame.bind(window); window.requestAnimationFrame = cb => raf(ts => cb(window.__freezeT ?? ts));     // __freezeT: draw every frame at one time
  }, VERSION);
  await page.goto(`http://127.0.0.1:${port}/`); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('EmberWalker'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  const debug = c => page.evaluate(x => Online.send({ type: 'debug', command: x }), c);
  const where = () => page.evaluate(() => ({ zone: Field.zone, x: Field.hero.nx, y: Field.hero.ny }));
  const go = async (zone, x, y, wait = 1800) => { await debug({ op: 'teleport', zone, x, y }); await page.waitForFunction(([z, a, b]) => Field.zone === z && Math.hypot(Field.hero.nx - a, Field.hero.ny - b) < 2, [zone, x, y], { timeout: 20000 }); await page.waitForTimeout(wait); };
  await debug({ op: 'set_time', hour: 12, freeze: true }); await debug({ op: 'set_weather', kind: 'clear' });
  // the ground is isometric: a world step (dx, dy) is the screen step (dx - dy, (dx + dy) / 2), so +x is Right+Down
  const keysFor = ([dx, dy]) => [Math.abs(dx - dy) > .35 ? (dx - dy > 0 ? 'ArrowRight' : 'ArrowLeft') : null, Math.abs(dx + dy) > .35 ? (dx + dy > 0 ? 'ArrowDown' : 'ArrowUp') : null].filter(Boolean);
  if (!process.env.SEAM_ONLY) {
    const cells = new Uint8Array(Z.size * Z.size); for (const [ry, a, b, k] of Z.regions.spans) cells.fill(k, ry * Z.size + a, ry * Z.size + b + 1);
    const solids = Z.objects.filter(o => o.kind !== 'void' && (o.r > 0 || o.width > 0));
    const towns = [Z.city, ...Z.camps].map(c => [c.x0 - 6, c.y0 - 6, c.x1 + 6, c.y1 + 6]);
    const clear = (x, y) => Z.shapeFloor[y]?.[x] === '#' && !towns.some(t => x >= t[0] && x <= t[2] && y >= t[1] && y <= t[3]) && solids.every(o => Math.hypot(o.x - x - .5, o.y - y - .5) > Math.max(o.r || 0, (o.width || 0) / 2 + .4) + 4);
    const lum = c => c[0] * .3 + c[1] * .59 + c[2] * .11;
    for (const [k, name] of Z.regions.names.entries()) {
            const mine = []; for (let y = 0; y < Z.size; y += 2) for (let x = 0; x < Z.size; x += 2) if (cells[y * Z.size + x] === k + 1 && Z.shapeFloor[y]?.[x] === '#') mine.push([x, y]);
      const mx = mine.reduce((s, c) => s + c[0], 0) / mine.length, my = mine.reduce((s, c) => s + c[1], 0) / mine.length;
      mine.sort((p, q) => Math.hypot(p[0] - mx, p[1] - my) - Math.hypot(q[0] - mx, q[1] - my));
      const at = mine.find(([x, y]) => clear(x, y) && cells[y * Z.size + x] === k + 1);
      assert.ok(at, `an open spot in ${name}`);
      const [x, y] = at, id = name.toLowerCase().replace(/[^a-z]+/g, '-');
      await go(45, x, y);
      check(await page.evaluate(() => Field.areaName) === name, `${id}: the HUD names ${name}`);
      if (GROUND.includes(name)) {
        const px = await page.evaluate(([a, b]) => { const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), L = [];
          for (const i of [-3, 0, 3]) for (const j of [-3, 0, 3]) { const [fx, fy] = Field.screenOf(a + i + .5, b + j + .5); const c = g.getImageData(Math.round(fx * cv.width), Math.round(fy * cv.height), 1, 1).data; L.push([c[0], c[1], c[2], c[0] * .3 + c[1] * .59 + c[2] * .11]); }
          L.sort((p, q) => p[3] - q[3]); return L[4].slice(0, 3); }, [x, y]);      // the median of nine points: a tree or a stone covers some of them, never most
        lums[name] = lum(px); console.log(`${name}: luminance ${lums[name].toFixed(0)}`);
      }
      await page.screenshot({ path: path.join(out, `${id}.png`) });
    }
    check(lums['The Ash Verge'] - lums['The Black Shore'] > 25, `the pale ash of the verge (${lums['The Ash Verge'].toFixed(0)}) is lighter than the black sand of the shore (${lums['The Black Shore'].toFixed(0)}): the ground classes are drawn`);
    for (const [id, x, y, name] of HUBS) {
      await go(45, x, y);
      check(await page.evaluate(n => Field.areaName === n && document.getElementById('area-title').textContent.includes(n), name), `${id}: the title says ${name}`);
      await page.screenshot({ path: path.join(out, `${id}.png`) });
    }
    for (const [kind, x, y] of ELITES) {
      await go(45, x - 3, y + 3);
      await page.waitForFunction(k => Field.slimes.some(s => s.kind === k), kind, { timeout: 15000 });
      await page.waitForTimeout(1500);
      await page.screenshot({ path: path.join(out, `elite-${kind}.png`) });
      check(await page.evaluate(k => Field.slimes.find(s => s.kind === k)?.d?.name?.length > 3, kind), `${kind} is on the map with a name`);
    }
        // the molten river and the crater's lava lake are painted orange over the ground; the causeway where the Chain Road crosses is plain floor
    const median9 = ([a, b]) => page.evaluate(([a, b]) => { const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), L = [];
      for (const i of [-1.5, 0, 1.5]) for (const j of [-1.5, 0, 1.5]) { const [fx, fy] = Field.screenOf(a + i, b + j); const c = g.getImageData(Math.round(fx * cv.width), Math.round(fy * cv.height), 1, 1).data; L.push([c[0], c[1], c[2], c[0] * .3 + c[1] * .59 + c[2] * .11]); }
      return L.filter(c => c[0] > 200 && c[2] < 90).length; }, [a, b]);      // how many of nine points are molten orange (the crust plates between the fissures are dark)
    for (const [id, x, y, hot] of [['river-west', 127, 230, true], ['river-east', 283, 198, true], ['lake', 163, 92, true], ['causeway', 190, 226.5, false]]) {
      await go(45, x, y + 8);
      const c = await median9([x, y]);
      await page.screenshot({ path: path.join(out, `${id}.png`) });
      check(hot ? c >= 2 : c === 0, `${id}: the ground at (${x},${y}) is ${hot ? 'molten' : 'not molten'} (${c} of 9 points orange)`);
      await page.screenshot({ path: path.join(out, `${id}.png`) });
    }
    for (const [id, x, y] of [['caldera', 163, 124], ['hot-crater', 253, 250], ['quenched-basin', 140, 296], ['door', 322, 92]]) { await go(45, x, y); await page.screenshot({ path: path.join(out, `${id}.png`) }); }
    for (const g of Z.portals.filter(p => !p.seam)) { const wk = g.walk || [0, -1]; await go(45, g.x - wk[0] * 6, g.y - wk[1] * 6); await page.screenshot({ path: path.join(out, `gate-${g.id}.png`) }); }
  }
  // ---- the two seams: crossed anywhere along the line, both ways, without a banner, nothing popping in, the same world point looking the same
  const diff = (a, b) => { let sum = 0, big = 0; const n = a.px.length / 4; for (let i = 0; i < a.px.length; i += 4) { const d = (Math.abs(a.px[i] - b.px[i]) + Math.abs(a.px[i + 1] - b.px[i + 1]) + Math.abs(a.px[i + 2] - b.px[i + 2])) / 3; sum += d; if (d > 40) big++; } return { mean: sum / n, big: big / n }; };
  const snap = async (zone, x, y, wx, wy) => { await go(zone, x, y, 2500); await page.evaluate(() => { window.__freezeT = 600000; }); await page.waitForTimeout(300); const shot = await page.evaluate(([wx, wy]) => { const cv = document.getElementById('fieldcv'), [fx, fy] = Field.screenOf(wx, wy), Wd = 256, H = 160, cw = cv.width * .26, chh = cv.height * .26, o = document.createElement('canvas'); o.width = Wd; o.height = H; const g = o.getContext('2d'); g.drawImage(cv, fx * cv.width - cw / 2, fy * cv.height - chh / 2, cw, chh, 0, 0, Wd, H); return { px: Array.from(g.getImageData(0, 0, Wd, H).data), png: o.toDataURL('image/png') }; }, [wx, wy]); await page.evaluate(() => { delete window.__freezeT; }); return shot; };
  const rows = [];
  for (const sp of seams.filter(p => !process.env.PARTNERS || JSON.parse(process.env.PARTNERS).includes(p.to))) {      // PARTNERS='[19]': one seam only
    const partner = sp.to, P = W.zones[partner - 1], pts = sp.seam.points, [shx, shy] = sp.seam.shift;
    for (const k of JSON.parse(process.env.KS || '[3, 7]')) {
      const a = pts[k], b = pts[k + 1], len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const q = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2], nrm = [-(b[1] - a[1]) / len, (b[0] - a[0]) / len];
      const inward = onFloor(Z, q[0] + nrm[0] * 4, q[1] + nrm[1] * 4) ? nrm : [-nrm[0], -nrm[1]];
      for (const [from, to, origin, dir] of [[45, partner, q, inward], [partner, 45, [q[0] + shx, q[1] + shy], [-inward[0], -inward[1]]]]) {
        const sx = origin[0] + dir[0] * 3, sy = origin[1] + dir[1] * 3;
        await go(from, sx, sy, 2500);
        const ahead = await page.evaluate(() => Field.ghosts.kinds), zt = to === 45 ? Z : P;
        const tp = from === 45 ? [origin[0] + shx, origin[1] + shy] : [origin[0] - shx, origin[1] - shy];     // the crossing point in the zone ahead's own frame
        const near = zt.objects.filter(o => o.kind !== 'void' && Math.hypot(o.x - tp[0], o.y - tp[1]) < 18).map(o => o.kind);
        const want = [...new Set(near)];
        check(want.every(x => ahead.includes(x)), `seam ${from} -> ${to} at ${k}: the zone ahead's scenery (${want.join(', ') || 'none near'}) is ready beyond the line; ghosts: ${ahead.join(', ')}`);
        const tilesBefore = await page.evaluate(() => Field.miniTiles);
        const entered0 = await page.evaluate(() => { document.getElementById('area-title').classList.remove('show'); return (document.body.innerText.match(/You enter/g) || []).length; });
        if (process.env.DEBUG_SEAM) console.log('frame ms', await page.evaluate(() => new Promise(res => { const t = []; let last = performance.now(); const f = () => { const n = performance.now(); t.push(n - last); last = n; t.length < 12 ? requestAnimationFrame(f) : res(Math.round(t.slice(2).reduce((a, b) => a + b, 0) / 10)); }; requestAnimationFrame(f); })));
        const keys = keysFor([-dir[0], -dir[1]]);
        const w0 = await where();
        for (const key of keys) await page.keyboard.down(key);
        await page.waitForFunction(z => Field.zone === z, to, { timeout: 15000 });
        const seamless = await page.evaluate(() => Field.seamless);       // read at the crossing: the flag lasts 2.5 s and the bounded software renderer is slow
        if (process.env.DEBUG_SEAM) console.log('crossing', from, '->', to, 'start', JSON.stringify(w0), 'keys', keys.join('+'), 'arrived', JSON.stringify(await where()), 'seamless', await page.evaluate(() => Field.seamless), 'shift', shx, shy);
        for (const key of keys) await page.keyboard.up(key);
        await page.waitForTimeout(500);
        const p = await where();
        check(onFloor(zt, p.x, p.y) || [[1, 0], [-1, 0], [0, 1], [0, -1]].some(([dx, dy]) => onFloor(zt, p.x + dx, p.y + dy)), `seam crossing ${from} -> ${to} arrived on the floor at (${p.x.toFixed(1)},${p.y.toFixed(1)})`);
        if (process.env.SEAMLESS_SOFT && !seamless) console.log(`NOTE seam crossing ${from} -> ${to} was not flagged seamless (SEAMLESS_SOFT: the flag fails the same way on the Stormglass baseline in the bounded headless runner, 2026-11-08)`);
        else check(seamless, `seam crossing ${from} -> ${to} was recognised as seamless`);
        check(await page.evaluate(n => !document.getElementById('area-title').classList.contains('show') && (document.body.innerText.match(/You enter/g) || []).length === n, entered0), `seam crossing ${from} -> ${to}: no zone banner and no new "You enter" line`);
        check(tilesBefore === await page.evaluate(() => Field.miniTiles), `seam crossing ${from} -> ${to}: the minimap keeps its scale`);
        if (k === 7) await page.screenshot({ path: path.join(out, `seam-${from}-to-${to}.png`) });
      }
      // the same world point (on the line), drawn from Emberwake and from its neighbour, looks the same (ground, scenery; people and decor are never within 20 tiles)
      const Pt = [q[0] + inward[0] * .5, q[1] + inward[1] * .5], B = [q[0] - inward[0] * .5 + shx, q[1] - inward[1] * .5 + shy], C = [q[0] + (b[0] - a[0]) / len * 7, q[1] + (b[1] - a[1]) / len * 7];
      const a1 = await snap(45, Pt[0], Pt[1], C[0], C[1]), a2 = await snap(45, Pt[0], Pt[1], C[0], C[1]), b1 = await snap(partner, B[0], B[1], C[0] + shx, C[1] + shy);
      const noise = diff(a1, a2), d = diff(a1, b1);
      fs.writeFileSync(path.join(out, `seam-same-${partner}-${k}-ember.png`), Buffer.from(a1.png.split(',')[1], 'base64')); fs.writeFileSync(path.join(out, `seam-same-${partner}-${k}-other.png`), Buffer.from(b1.png.split(',')[1], 'base64'));
      rows.push({ partner, k, noise, d });
      console.log(`seam point ${partner}/${k}: noise ${noise.mean.toFixed(2)}/${(noise.big * 100).toFixed(1)}%, across ${d.mean.toFixed(2)}/${(d.big * 100).toFixed(1)}%`);
    }
  }
  for (const r of rows) check(r.d.mean <= Math.max(10, r.noise.mean * 2 + 2) && r.d.big <= Math.max(.10, r.noise.big * 2 + .02), `seam ${r.partner} point ${r.k}: the same point looks the same from both frames (${r.d.mean.toFixed(1)}/${(r.d.big * 100).toFixed(1)}%)`);
  check(errors.length === 0, 'no page errors: ' + errors.slice(0, 3).join(' | '));
  console.log(JSON.stringify({ passed: true, checks }));
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => { await browser?.close(); server?.kill(); });
