// Sunward Vale as an authored river valley (scripts/sunward_design.py): the real client names each of the fifteen regions, draws its ground classes (the golden leas against the dark western
// oakwood), the four hubs name themselves, the three elites draw from their art, the six borders to the shaped neighbours are seams (a held key walks over each and the hero ends up in the
// neighbour, and walks back), the Yearwheel is a wall nobody walks through except under the one vault, and the same world point on a seam looks the same from both frames.
// Pictures in test-results/sunward-design/.
//   REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/sunward-design-ui.cjs     (PART=regions|rest splits the run under the memory cap; PARTNERS=19,26 picks the seams walked and compared; SEAM_ONLY=1 skips to the seam checks)
//   MUTATE=1 serves the pilot's committed client/field.js (before the Sunward ground classes): the ground-class check must fail.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn, execSync } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'test-results/sunward-design');
fs.mkdirSync(out, { recursive: true });
const port = 20150 + (process.pid % 400);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'sunward-'));
let server, browser, checks = 0;
const check = (v, l) => { assert.ok(v, l); checks++; console.log('ok', l); };
const W = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8')), Z = W.zones[19];
const onFloor = (z, x, y) => (z.shapeFloor[Math.floor(y)] || '')[Math.floor(x)] === '#';
const VERSION = /Beta \d+\.\d+\.\d+/.exec(fs.readFileSync(path.join(root, 'client/index.html'), 'utf8'))[0];
const HUBS = [['millbridge', 126, 201, 'Millbridge'], ['honeywood', 92, 72, 'Honeywood Steading'], ['wickerfield', 236, 94, 'Wickerfield Post'], ['elderroot', 176, 66, 'Elderroot Camp']];
const ELITES = [['honeyjaw', 62, 50, 'Old Honeyjaw'], ['wickerwarden', 290, 78, 'The Wicker Warden'], ['harrowox', 208, 282, 'Harrow Ox']];
// regions whose ground classes are compared: the golden leas against the dark oakwood floor
const GROUND = ['The Golden Leas', 'The Western Oakwood'], lums = {};
const PARTNERS = (process.env.PARTNERS || '26').split(',').map(Number);
(async () => {
  check(Z.name === 'Sunward Vale' && Z.size === 352 && Z.shapeFloor && Z.shape.neighbours.join() === '19,21,22,23,25,26,28', 'Sunward Vale is the 352 grid with its outline and seven neighbours');
  const seams = Z.portals.filter(p => p.seam).map(p => p.to).sort((a, b) => a - b);
  check(seams.join() === '19,21,22,23,25,26', 'the six shaped neighbours are all seams');
  check(Z.portals.filter(p => p.to === 28).length === 1 && Z.portals.some(p => p.to === 28 && p.walk) && Z.exitArches.some(a => a.portal === 'path_20_28'), 'the Yearwheel has one portal, the walked-through vault, with its arch');
  for (const p of Z.portals) check(onFloor(Z, p.x, p.y) || p.seam, `${p.id} stands on the floor`);
  check(Z.regions.names.length === 15 && Z.camps.length === 3 && Z.quests.length >= 28, 'fifteen regions, four hubs and the quests');
  server = spawn(process.env.VALHALLA_BINARY, [], { cwd: root, stdio: 'ignore',
    env: { ...process.env, VALHALLA_BIND: `127.0.0.1:${port}`, VALHALLA_DB: path.join(tmp, 'v.sqlite'), VALHALLA_CLIENT_DIR: path.join(root, 'client'), VALHALLA_TEST_COMMANDS: '1', VALHALLA_GOD_MODE: '1', VALHALLA_START_LEVEL: process.env.START_LEVEL || '99', VALHALLA_LEVEL_SPREAD: '0' } });
  for (let i = 0; i < 100; i++) { try { if ((await fetch(`http://127.0.0.1:${port}/health`)).ok) break; } catch (_) {} await new Promise(r => setTimeout(r, 200)); }
  browser = await chromium.launch({ headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' })).newPage();
  const errors = []; page.on('pageerror', e => console.log('PAGEERROR', e.message) || errors.push(e.message + ' @ ' + (e.stack || '').split('\n').slice(1, 4).join(' | ')));
  if (process.env.MUTATE) {
    const old = execSync(`git show ${process.env.MUTATE === 'seam' ? '6d6fbd3~1' : 'HEAD'}:client/field.js`, { cwd: root, maxBuffer: 1 << 28 });
    await page.route('**/field.js*', r => r.fulfill({ status: 200, contentType: 'application/javascript', body: old }));
  }
  await page.addInitScript(v => { localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {} })); localStorage.setItem('valhallasc.whats-new.v1', v);
    const raf = window.requestAnimationFrame.bind(window); window.requestAnimationFrame = cb => raf(ts => cb(window.__freezeT ?? ts));     // __freezeT: draw every frame at one time
  }, VERSION);
  await page.goto(`http://127.0.0.1:${port}/`); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('SunWalker'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  const debug = c => page.evaluate(x => Online.send({ type: 'debug', command: x }), c);
  const where = () => page.evaluate(() => ({ zone: Field.zone, x: Field.hero.nx, y: Field.hero.ny }));
  const go = async (zone, x, y, wait = 1800) => { await debug({ op: 'teleport', zone, x, y }); await page.waitForFunction(([z, a, b]) => Field.zone === z && Math.hypot(Field.hero.nx - a, Field.hero.ny - b) < 2, [zone, x, y], { timeout: 20000 }); await page.waitForTimeout(wait); };
  await debug({ op: 'set_time', hour: 12, freeze: true }); await debug({ op: 'set_weather', kind: 'clear' });
  // the ground is isometric: a world step (dx, dy) is the screen step (dx - dy, (dx + dy) / 2), so +x is Right+Down
  const keysFor = ([dx, dy]) => [Math.abs(dx - dy) > .35 ? (dx - dy > 0 ? 'ArrowRight' : 'ArrowLeft') : null, Math.abs(dx + dy) > .35 ? (dx + dy > 0 ? 'ArrowDown' : 'ArrowUp') : null].filter(Boolean);
  if (process.env.GATE_SHOT) { await go(20, 176, 50, 2500); await page.screenshot({ path: path.join(out, 'hollow-door.png') }); await go(20, 262, 20, 2500); await page.screenshot({ path: path.join(out, 'vault-wall.png') }); console.log('shots'); return; }
  const cells = new Uint8Array(Z.size * Z.size); for (const [ry, a, b, k] of Z.regions.spans) cells.fill(k, ry * Z.size + a, ry * Z.size + b + 1);
  const solids = Z.objects.filter(o => o.kind !== 'void' && (o.r > 0 || o.width > 0));
  const towns = [Z.city, ...Z.camps].map(c => [c.x0 - 6, c.y0 - 6, c.x1 + 6, c.y1 + 6]);
  const clear = (x, y) => Z.shapeFloor[y]?.[x] === '#' && !towns.some(t => x >= t[0] && x <= t[2] && y >= t[1] && y <= t[3]) && solids.every(o => Math.hypot(o.x - x - .5, o.y - y - .5) > Math.max(o.r || 0, (o.width || 0) / 2 + .4) + 4);
  if (!process.env.SEAM_ONLY) {      // SEAM_ONLY=1: skip straight to the same-point seam check (the bounded runner's time cap)
  if (process.env.PART !== 'rest') for (const [k, name] of Z.regions.names.entries()) {
    const mine = []; for (let y = 0; y < Z.size; y += 2) for (let x = 0; x < Z.size; x += 2) if (cells[y * Z.size + x] === k + 1 && Z.shapeFloor[y]?.[x] === '#') mine.push([x, y]);
    const mx = mine.reduce((s, c) => s + c[0], 0) / mine.length, my = mine.reduce((s, c) => s + c[1], 0) / mine.length;
    mine.sort((p, q) => Math.hypot(p[0] - mx, p[1] - my) - Math.hypot(q[0] - mx, q[1] - my));
    const at = mine.find(([x, y]) => clear(x, y) && cells[y * Z.size + x] === k + 1);
    assert.ok(at, `an open spot in ${name}`);
    const [x, y] = at, id = name.toLowerCase().replace(/[^a-z]+/g, '-');
    await go(20, x, y);
    check(await page.evaluate(() => Field.areaName) === name, `${id}: the HUD names ${name}`);
    if (GROUND.includes(name)) {
      const px = await page.evaluate(([a, b]) => { const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), L = [];
        for (const i of [-3, 0, 3]) for (const j of [-3, 0, 3]) { const [fx, fy] = Field.screenOf(a + i + .5, b + j + .5); const c = g.getImageData(Math.round(fx * cv.width), Math.round(fy * cv.height), 1, 1).data; L.push([c[0], c[1], c[2], c[0] * .3 + c[1] * .59 + c[2] * .11]); }
        L.sort((p, q) => p[3] - q[3]); return L[4].slice(0, 3); }, [x, y]);      // the median of nine points: a palm or a stone covers some of them, never most
      lums[name] = px[0] * .3 + px[1] * .59 + px[2] * .11; console.log(`${name}: luminance ${lums[name].toFixed(0)}`);
    }
    await page.screenshot({ path: path.join(out, `${id}.png`) });
  }
  if (process.env.PART !== 'rest') check(lums['The Golden Leas'] - lums['The Western Oakwood'] > 30, `the Golden Leas (${lums['The Golden Leas'].toFixed(0)}) are much brighter than the Western Oakwood (${lums['The Western Oakwood'].toFixed(0)}): the ground classes are drawn`);
  if (process.env.PART === 'regions') { check(errors.length === 0, 'no page errors'); console.log(JSON.stringify({ passed: true, checks })); return; }
  for (const [id, x, y, name] of HUBS) {
    await go(20, x, y);
    check(await page.evaluate(n => Field.areaName === n && document.getElementById('area-title').textContent.includes(n), name), `${id}: the title says ${name}`);
    await page.screenshot({ path: path.join(out, `${id}.png`) });
  }
  for (const [kind, x, y, nm] of ELITES) {
    await go(20, x - 3, y + 3);
    await page.waitForFunction(k => Field.slimes.some(s => s.kind === k), kind, { timeout: 15000 });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(out, `elite-${kind}.png`) });
    check(await page.evaluate(k => Field.slimes.find(s => s.kind === k)?.d?.name, kind) === nm, `${kind} is on the map named ${nm}`);
  }
  for (const [id, x, y] of [['hives', 62, 104], ['barrow', 274, 138], ['orchard', 138, 96], ['river-bridge', 151, 178], ['springs', 208, 96], ['pastures', 190, 262]]) { await go(20, x, y); await page.screenshot({ path: path.join(out, `${id}.png`) }); }
  for (const g of Z.portals.filter(p => !p.seam)) { const wk = g.walk || [0, 1]; await go(20, g.x - wk[0] * 6, g.y - wk[1] * 6); await page.screenshot({ path: path.join(out, `gate-${g.id}.png`) }); }
  // ---- the wall: the Yearwheel border is rampart and tower along its whole length but for the vault; a held key toward it at four places stops at the wall, never beyond it
  const vault = Z.portals.find(p => p.to === 28);
  {
    const wall = Z.objects.filter(o => o.kind === 'rampart' || o.kind === 'tower');
    check(wall.length > 35 && wall.filter(o => o.kind === 'tower').length >= 5, `the wall is ${wall.length} pieces with towers`);
    const far = wall.filter(o => Math.abs(o.x - vault.x) > 16).sort((p, q) => p.x - q.x);
    for (const frac of [.15, .4, .65, .9]) {
      const piece = far[Math.floor(far.length * frac)];
      await go(20, piece.x, piece.y + 7, 1500);
      const keys = keysFor([0, -1]);
      for (const key of keys) await page.keyboard.down(key);
      await page.waitForTimeout(3500);
      for (const key of keys) await page.keyboard.up(key);
      const at = await where();
      await page.screenshot({ path: path.join(out, `wall-${Math.round(frac * 100)}.png`) });
      check(at.zone === 20 && at.y > piece.y - .5, `at x ${Math.round(piece.x)} a held key toward the Yearwheel stops at the wall (y ${at.y.toFixed(1)} > ${piece.y.toFixed(1)})`);
    }
    // the vault: the same key under the arch leads into the Yearwheel
    await go(20, vault.x, vault.y + 5, 2000);
    await page.screenshot({ path: path.join(out, 'vault-before.png') });
    const keys = keysFor([0, -1]);
    for (const key of keys) await page.keyboard.down(key);
    await page.waitForFunction(() => Field.zone === 28, null, { timeout: 20000 }).catch(() => {});
    for (const key of keys) await page.keyboard.up(key);
    check((await where()).zone === 28, 'a held key under the vault walks into the Yearwheel');
    await page.screenshot({ path: path.join(out, 'vault-after.png') });
  }
  // ---- the seams: stand three tiles inland of each crossing, hold the key toward the neighbour, end up there; then hold the key back and end up here again
  const inwardOf = sp => { const pts = sp.seam.points; let k = 0, best = 1e9; for (let i = 0; i < pts.length - 1; i++) { const d = Math.hypot((pts[i][0] + pts[i + 1][0]) / 2 - sp.x, (pts[i][1] + pts[i + 1][1]) / 2 - sp.y); if (d < best) { best = d; k = i; } }
    const a = pts[k], b = pts[k + 1], len = Math.hypot(b[0] - a[0], b[1] - a[1]), n = [-(b[1] - a[1]) / len, (b[0] - a[0]) / len]; return onFloor(Z, sp.x + n[0] * 4, sp.y + n[1] * 4) ? n : [-n[0], -n[1]]; };
  for (const other of PARTNERS) {
    const p = Z.portals.find(q => q.to === other && q.seam), NRM = inwardOf(p);
    await go(20, p.x + NRM[0] * 3, p.y + NRM[1] * 3, 1500);
    await page.screenshot({ path: path.join(out, `seam-${other}-before.png`) });
    let keys = keysFor([-NRM[0], -NRM[1]]);
    for (const key of keys) await page.keyboard.down(key);
    await page.waitForFunction(z => Field.zone === z, other, { timeout: 20000 }).catch(() => {});
    for (const key of keys) await page.keyboard.up(key);
    await page.waitForTimeout(600);
    check((await where()).zone === other, `a held key walks over the seam into zone ${other}`);
    await page.screenshot({ path: path.join(out, `seam-${other}-after.png`), timeout: 120000 }).catch(() => {});
    keys = keysFor(NRM);
    for (const key of keys) await page.keyboard.down(key);
    await page.waitForFunction(z => Field.zone === z, 20, { timeout: 20000 }).catch(() => {});
    for (const key of keys) await page.keyboard.up(key);
    await page.waitForTimeout(400);
    check((await where()).zone === 20, `a held key walks back over the seam from zone ${other}`);
  }
  }
  // ---- the same world point on the line, drawn from the Sunward Vale and from its neighbour, looks the same (the ground blend toward a neighbour must be its real ground classes, not a generic tint)
  const diff = (a, b) => { let sum = 0, big = 0; const n = a.px.length / 4; for (let i = 0; i < a.px.length; i += 4) { const d = (Math.abs(a.px[i] - b.px[i]) + Math.abs(a.px[i + 1] - b.px[i + 1]) + Math.abs(a.px[i + 2] - b.px[i + 2])) / 3; sum += d; if (d > 40) big++; } return { mean: sum / n, big: big / n }; };
  const snap = async (zone, x, y, wx, wy) => { await go(zone, x, y, 2500); await page.evaluate(() => { window.__freezeT = 600000; }); await page.waitForTimeout(300); const shot = await page.evaluate(([wx, wy]) => { const cv = document.getElementById('fieldcv'), [fx, fy] = Field.screenOf(wx, wy), Wd = 256, H = 160, cw = cv.width * .26, chh = cv.height * .26, o = document.createElement('canvas'); o.width = Wd; o.height = H; const g = o.getContext('2d'); g.drawImage(cv, fx * cv.width - cw / 2, fy * cv.height - chh / 2, cw, chh, 0, 0, Wd, H); return { px: Array.from(g.getImageData(0, 0, Wd, H).data), png: o.toDataURL('image/png') }; }, [wx, wy]); await page.evaluate(() => { delete window.__freezeT; }); return shot; };
  for (const partner of PARTNERS) {
    const sp = Z.portals.find(q => q.seam && q.to === partner), pts = sp.seam.points, [shx, shy] = sp.seam.shift, rows = [];
    for (const k of JSON.parse(process.env.KS || '[3]')) {
      const a = pts[k], b = pts[k + 1], len = Math.hypot(b[0] - a[0], b[1] - a[1]), q = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2], nrm = [-(b[1] - a[1]) / len, (b[0] - a[0]) / len];
      const inward = onFloor(Z, q[0] + nrm[0] * 4, q[1] + nrm[1] * 4) ? nrm : [-nrm[0], -nrm[1]];
      const Pt = [q[0] + inward[0] * .5, q[1] + inward[1] * .5], B = [q[0] - inward[0] * .5 + shx, q[1] - inward[1] * .5 + shy], C = [q[0] + (b[0] - a[0]) / len * 7, q[1] + (b[1] - a[1]) / len * 7];
      await go(20, Pt[0], Pt[1], 9000);
      const a1 = await snap(20, Pt[0], Pt[1], C[0], C[1]), a2 = await snap(20, Pt[0], Pt[1], C[0], C[1]), b1 = await snap(partner, B[0], B[1], C[0] + shx, C[1] + shy);
      if (process.env.PROFILE) {     // colours along the line's normal, seen from each side (debug)
        const probe = async (zone, x, y, pts) => { await go(zone, x, y, 2500); await page.evaluate(() => { window.__freezeT = 600000; }); await page.waitForTimeout(300); const r = await page.evaluate(pts => { const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'); return pts.map(([wx, wy]) => { const [fx, fy] = Field.screenOf(wx, wy); return Array.from(g.getImageData(Math.round(fx * cv.width), Math.round(fy * cv.height), 1, 1).data.slice(0, 3)).join(','); }); }, pts); await page.evaluate(() => { delete window.__freezeT; }); return r; };
        const ts = [-10, -6, -3, -1, 1, 3, 6, 10], inv = ts.map(t => [C[0] + inward[0] * t, C[1] + inward[1] * t]);
        console.log('PROFILE t:', ts.join(' '));
        console.log('PROFILE vale view:', (await probe(20, Pt[0], Pt[1], inv)).join(' | '));
        console.log('PROFILE neighbour view:', (await probe(partner, B[0], B[1], inv.map(([x, y]) => [x + shx, y + shy]))).join(' | '));
      }
      const noise = diff(a1, a2), d = diff(a1, b1);
      fs.writeFileSync(path.join(out, `seam-same-${partner}-${k}-vale.png`), Buffer.from(a1.png.split(',')[1], 'base64')); fs.writeFileSync(path.join(out, `seam-same-${partner}-${k}-other.png`), Buffer.from(b1.png.split(',')[1], 'base64'));
      rows.push({ k, noise, d }); console.log(`seam ${partner} point ${k}: noise ${noise.mean.toFixed(2)}/${(noise.big * 100).toFixed(1)}%, across ${d.mean.toFixed(2)}/${(d.big * 100).toFixed(1)}%`);
    }
    for (const r of rows) check(r.d.mean <= Math.max(10, r.noise.mean * 2 + 2) && r.d.big <= Math.max(.10, r.noise.big * 2 + .02), `seam to zone ${partner}, point ${r.k}: the same point looks the same from both frames (${r.d.mean.toFixed(1)}/${(r.d.big * 100).toFixed(1)}%)`);
  }
  check(errors.length === 0, 'no page errors: ' + errors.slice(0, 3).join(' | '));
  console.log(JSON.stringify({ passed: true, checks }));
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => { await browser?.close(); server?.kill(); });
