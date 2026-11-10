// The Yearwheel's vault to Sunward Vale (zone shapes pilot): ONE doorway seen from two frames (Sunward Vale and the reshaped Yearwheel at k = 2.8, a whole-tile shift apart).
// The SAME world point drawn from both sides must look the same, both frames must draw the same scenery around the arch (nothing pops in), and a real walk through the arch,
// both ways, must change nothing on screen. Derived from vault-seamless-ui.cjs. Starts its own private world from VALHALLA_BINARY. Run it bounded:
//   REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/year-vault-ui.cjs            (MUTATE=1 must fail: the vault drawing is switched off)
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn, execSync } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'test-results/year-vault');
fs.mkdirSync(out, { recursive: true });
const port = 18800 + (process.pid % 400);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'year-vault-'));
let server, browser, checks = 0;
const check = (value, label) => { assert.ok(value, label); checks++; };
const world = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8'));
const zoneDef = z => (z === 0 ? world : world.zones[z - 1]);
const VALE = 20, YEAR = 28;
const gateV = zoneDef(VALE).portals.find(p => p.id === 'path_20_28'), gateY = zoneDef(YEAR).portals.find(p => p.id === 'path_28_20');
const archV = zoneDef(VALE).exitArches.find(a => a.portal === 'path_20_28');
const [sx, sy] = gateV.vault;
const onLand = (z, x, y) => zoneDef(z).shapeFloor[Math.floor(y)]?.[Math.floor(x)] === '#';
(async () => {
  server = spawn(process.env.VALHALLA_BINARY, [], {
    cwd: root, stdio: 'ignore',
    env: { ...process.env, VALHALLA_BIND: `127.0.0.1:${port}`, VALHALLA_DB: path.join(tmp, 'v.sqlite'), VALHALLA_CLIENT_DIR: path.join(root, 'client'), VALHALLA_TEST_COMMANDS: '1', VALHALLA_GOD_MODE: '1', VALHALLA_LEVEL_SPREAD: '0', VALHALLA_START_LEVEL: '99' },
  });
  for (let i = 0; i < 150; i++) { try { if ((await fetch(`http://127.0.0.1:${port}/health`)).ok) break; } catch (_) {} await new Promise(r => setTimeout(r, 200)); }
  browser = await chromium.launch({ headless: true, args: ['--disable-gpu', '--disable-dev-shm-usage'] });
  const context = await browser.newContext({ viewport: { width: +process.env.VW || 1280, height: +process.env.VH || 800 }, reducedMotion: 'reduce' });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.route(/\.(mp3|ogg|wav)(\?.*)?$/, route => route.abort());      // the pilot client is at the memory cap: decoded music is the biggest thing a test never listens to
  if (process.env.MUTATE) {      // the vault drawing is switched off: both frames then draw only their own side of the arch
    await page.route(/\/field\.js(\?.*)?$/, async route => {
      const src = fs.readFileSync(path.join(root, 'client/field.js'), 'utf8').replace('map.ghosts = map.ghosts || []; map.vregs = vaultRegions();', 'map.ghosts = map.ghosts || []; map.vregs = [];');
      await route.fulfill({ contentType: 'application/javascript', body: src });
    });
  }
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {}, 'whatsNew': 1 })));
  await page.goto(`http://127.0.0.1:${port}/`); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('VaultWalker'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  const mem = label => { if (!process.env.DEBUG_MEM) return; const kb = cmd => Number(execSync(cmd).toString().trim() || 0); console.log(`mem ${label}: chrome ${(kb("ps -eo rss,args | grep -E 'chrome-headless' | grep -v grep | awk '{s+=$1} END {print s}'") / 1024).toFixed(0)} MB, server ${(kb("ps -eo rss,args | grep -E 'valhalla-server' | grep -v grep | awk '{s+=$1} END {print s}'") / 1024).toFixed(0)} MB`); };
  mem('after login');
  const debug = command => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);
  const where = () => page.evaluate(() => ({ zone: Field.zone, x: Field.hero.nx, y: Field.hero.ny }));
  const snap = async (zone, x, y) => {
    await debug({ op: 'teleport', zone, x, y });
    await page.waitForFunction(([z, x, y]) => Field.zone === z && Math.hypot(Field.hero.nx - x, Field.hero.ny - y) < 1.5, [zone, x, y], { timeout: 30000 });
    await page.waitForTimeout(3500);     // neighbour contexts are built one per timer tick after a zone change (the Yearwheel's is 888 tiles wide)
    mem(`zone ${zone} ${x.toFixed(0)},${y.toFixed(0)}`);
    await page.addStyleTag({ content: '#dps-meter,.dps-meter{display:none!important}' });
    const data = await page.evaluate(() => {
      const cv = document.getElementById('fieldcv'), W = 256, H = 160, o = document.createElement('canvas'); o.width = W; o.height = H;
      const g = o.getContext('2d'); g.drawImage(cv, cv.width * .2, cv.height * .12, cv.width * .6, cv.height * .6, 0, 0, W, H);
      return { px: Array.from(g.getImageData(0, 0, W, H).data), png: o.toDataURL('image/png') };
    });
    return { at: await where(), ...data };
  };
  const diff = (a, b) => { let sum = 0, big = 0; const n = a.px.length / 4; for (let i = 0; i < a.px.length; i += 4) { const d = (Math.abs(a.px[i] - b.px[i]) + Math.abs(a.px[i + 1] - b.px[i + 1]) + Math.abs(a.px[i + 2] - b.px[i + 2])) / 3; sum += d; if (d > 40) big++; } return { mean: sum / n, big: big / n }; };
  const save = (name, im) => fs.writeFileSync(path.join(out, name), Buffer.from(im.png.split(',')[1], 'base64'));

  // PART=stag: the Equinox Stag (and for scale a Snow Giant from the old art) in the real client, one picture each (the art's size is judged from an in-game screenshot)
  if (process.env.PART === 'stag') {
    page.on('response', r => { if (/yearwheelelites|sunwardelites/.test(r.url())) console.log('response', r.status(), r.url()); });
    page.on('requestfailed', r => console.log('requestfailed', r.url()));
    page.on('console', m => { if (m.type() === 'error') console.log('console error', m.text().slice(0, 200)); });
    for (const [kind, dx, dy] of (process.env.STAGS || 'equinoxstag:-7:7,snowgiant:-7:7').split(',').map(v => v.split(':')).map(([k, a, b]) => [k, +a, +b])) {
      const e = zoneDef(YEAR).slimes.find(t => t.kind === kind);
      await debug({ op: 'teleport', zone: YEAR, x: e.x + dx, y: e.y + dy });
      await page.waitForFunction(([z, x, y]) => Field.zone === z && Math.hypot(Field.hero.nx - x, Field.hero.ny - y) < 3, [YEAR, e.x + dx, e.y + dy], { timeout: 30000 });
      await page.waitForTimeout(5000);
      await page.addStyleTag({ content: '#dps-meter,.dps-meter{display:none!important}' });
      await page.screenshot({ path: path.join(out, `stag-${kind}-${dx}-${dy}.png`) });
      console.log(kind, 'at', e.x, e.y, 'from', dx, dy);
    }
    assert.deepEqual(errors, [], 'no page errors: ' + errors.join(' | '));
    return;
  }
  // 1. the frames line up and the data is what the design promises
  const yarch = zoneDef(YEAR).exitArches.find(a => a.portal === 'path_28_20');
  check(Math.abs(archV.x + sx - yarch.x) < .02 && Math.abs(archV.y + sy - yarch.y) < .02, 'the two arches are one place in the two frames');
  check(Math.abs(gateV.vault[0] + gateY.vault[0]) < 1e-9 && Math.abs(gateV.vault[1] + gateY.vault[1]) < 1e-9, 'the shifts cancel');
  const regions = await page.evaluate(([v, y]) => { /* regions exist after the hero stands in the zone */ return [Field.vaultZones]; }, [VALE, YEAR]);
  void regions;

  const PART = process.env.PART || '';      // 'pair' | 'scene' | 'walk' (DIR=1|-1): the pilot's client is close to the 1.5 GiB cap, so every part is its own bounded run
  // 2. the same world point, from both sides: s tiles south of Sunward's arch (inside both lands: Sunward's, and the Yearwheel's pocket), t tiles along the wall
  const rows = [];
  if (!PART || PART === 'pair') for (const [s, t] of (process.env.SS || '0.6:0,1.2:-3,1.2:3,2.4:0').split(',').map(x => x.split(':').map(Number))) {
    const px = archV.x + t, py = archV.y + s;
    check(onLand(VALE, px, py), `Sunward's point ${s}/${t} is land`);
    const a = await snap(VALE, px, py), a2 = process.env.MUTATE || process.env.NONOISE ? a : await snap(VALE, px, py), b = await snap(YEAR, px + sx, py + sy);      // (the mutated run skips the noise snap: it is the memory-hungry one)
    const noise = diff(a, a2), d = diff(a, b);
    save(`vault-vale-s${s}-t${t}.png`, a); save(`vault-year-s${s}-t${t}.png`, b);
    rows.push({ s: `${s}/${t}`, noise, d });
    console.log(`s ${s} t ${t}: noise ${noise.mean.toFixed(2)}/${(noise.big * 100).toFixed(1)}%  across the vault ${d.mean.toFixed(2)}/${(d.big * 100).toFixed(1)}% (mean abs diff / % of pixels off by >40)`);
  }

  if (!PART || PART === 'scene') {
  // 3. nothing pops in: around the arch both frames draw the same scenery, object by object (the wall, Sunward's verge, the Yearwheel's trees)
  await debug({ op: 'teleport', zone: VALE, x: archV.x, y: archV.y + 3 });
  await page.waitForFunction(z => Field.zone === z, VALE, { timeout: 20000 }); await page.waitForTimeout(3500);
  const A = await page.evaluate(([x, y, R]) => Field.sceneAround(x, y, R), [archV.x, archV.y, +process.env.SCENE_R || 30]);
  await debug({ op: 'teleport', zone: YEAR, x: archV.x + sx, y: archV.y + sy - 3 });
  await page.waitForFunction(z => Field.zone === z, YEAR, { timeout: 20000 }); await page.waitForTimeout(3500);
  const B = await page.evaluate(([x, y, R]) => Field.sceneAround(x, y, R), [archV.x + sx, archV.y + sy, +process.env.SCENE_R || 30]);
  const near = (o, L, dx, dy) => L.some(q => q[0] === o[0] && Math.hypot(q[1] - o[1] - dx, q[2] - o[2] - dy) < .6);
  const onlyV = A.filter(o => !near(o, B, sx, sy)), onlyY = B.filter(o => !near(o, A, -sx, -sy));
  const fmt = (L, dx, dy) => L.slice(0, 12).map(o => `${o[0]}@${(o[1] + dx).toFixed(1)},${(o[2] + dy).toFixed(1)}`).join(' ');
  console.log(`${A.length} / ${B.length} objects near the arch; only in Sunward's frame: ${fmt(onlyV, 0, 0) || '-'}; only in the Yearwheel's (Sunward coords): ${fmt(onlyY, -sx, -sy) || '-'}`);
  check(onlyV.length + onlyY.length === 0, 'the same scenery around the arch from both sides');
  }

  // 4. a real walk through the arch, both ways: the step at the zone change is no bigger than the steps of ordinary walking
  const isoKeys = (dx, dy) => [dx - dy > .35 ? 'ArrowRight' : dx - dy < -.35 ? 'ArrowLeft' : null, dx + dy > .35 ? 'ArrowDown' : dx + dy < -.35 ? 'ArrowUp' : null].filter(Boolean);
  if (!PART || PART === 'walk') for (const dir of (process.env.DIR ? [+process.env.DIR] : [1, -1])) {         // 1 = into the Yearwheel (north), -1 = back out (south)
    const from = dir === 1 ? [VALE, archV.x, archV.y + 3.5] : [YEAR, archV.x + sx, archV.y + sy - 3.5];
    await snap(...from);
    const keys = isoKeys(0, -dir);
    for (const k of keys) await page.keyboard.down(k);
    await page.evaluate(() => {      // the step between consecutive frames is measured inside the page (storing the pixels of every frame would hold hundreds of megabytes)
      const cv = document.getElementById('fieldcv'), W = 64, H = 40, o = document.createElement('canvas'); o.width = W; o.height = H;
      const g = o.getContext('2d', { willReadFrequently: true }); window.__steps = []; window.__rec = true; let last = null, lastZone = null;
      const tick = () => {
        if (!window.__rec) return;
        g.drawImage(cv, cv.width * .2, cv.height * .12, cv.width * .6, cv.height * .6, 0, 0, W, H);
        const px = g.getImageData(0, 0, W, H).data;
        if (last) { let sum = 0; for (let i = 0; i < px.length; i += 4) sum += (Math.abs(px[i] - last[i]) + Math.abs(px[i + 1] - last[i + 1]) + Math.abs(px[i + 2] - last[i + 2])) / 3; window.__steps.push({ change: Field.zone !== lastZone, d: sum / (px.length / 4) }); }
        last = new Uint8ClampedArray(px); lastZone = Field.zone;
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
    const t0 = Date.now();
    while (Date.now() - t0 < 30000) { await page.waitForTimeout(250); const z = await page.evaluate(() => Field.zone); if (process.env.DEBUG_MEM) console.log('walk', Date.now() - t0, JSON.stringify(await where())); if (dir === 1 ? z === YEAR : z === VALE) { await page.waitForTimeout(1500); break; } }
    for (const k of keys) await page.keyboard.up(k);
    if (process.env.DEBUG_MEM) console.log('walk ended at', JSON.stringify(await where()), 'wanted from', JSON.stringify(from));
    const steps = await page.evaluate(() => { window.__rec = false; return window.__steps; });
    const frames = steps;
    const at0 = steps.findIndex(x => x.change);
    const ordinary = steps.filter((x, i) => !(i === at0 || i === at0 + 1)).map(x => x.d).sort((p, q) => p - q);
    const cross = steps.filter(x => x.change).length === 1 ? [Math.max(steps[at0].d, steps[at0 + 1]?.d || 0)] : steps.filter(x => x.change).map(x => x.d);
    const p90 = ordinary[Math.floor(ordinary.length * .9)] || 0;
    console.log(`${dir === 1 ? 'into the Yearwheel' : 'back to Sunward'}: ${frames.length} frames, crossing step ${cross.map(c => c.toFixed(1)).join(',') || 'none'}, ordinary 90th percentile ${p90.toFixed(1)}`);
    check(cross.length === 1, `${dir === 1 ? 'in' : 'out'}: the walk crossed the vault once`);
    check(cross[0] <= Math.max(p90 * 1.5, 6), `${dir === 1 ? 'in' : 'out'}: no spike at the crossing (${cross[0]?.toFixed(1)} vs ordinary ${p90.toFixed(1)})`);
  }
  // 5. the verdict on the same-point pictures (10 percent: the missing-neighbour bug was 20)
  for (const r of rows) check(r.d.mean <= Math.max(10, r.noise.mean * 2 + 2) && r.d.big <= Math.max(.10, r.noise.big * 2 + .02), `s ${r.s}: the same point looks the same from both sides of the vault (diff ${r.d.mean.toFixed(1)}, ${(r.d.big * 100).toFixed(1)}% off)`);
  assert.deepEqual(errors, [], 'no page errors: ' + errors.join(' | '));
  console.log(`year-vault-ui: ${checks} checks passed; screenshots in ${out}`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => { try { await browser?.close(); } catch (_) {} server?.kill(); fs.rmSync(tmp, { recursive: true, force: true }); });
