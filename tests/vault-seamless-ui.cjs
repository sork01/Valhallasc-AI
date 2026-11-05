// Vault seamlessness (Skaldholm's wall): the SAME world point drawn from both sides of the vault must look the same. Derived from zone-shape-ui.cjs.
// Zone shapes pilot (docs/zone-shapes.md): the real client draws Greenmeadow and the Emberfall Crags with the outline of
// their province, and a walker cannot leave the land. Starts its own private world (test commands, own database) from
// VALHALLA_BINARY and writes screenshots to test-results/zone-shapes/. Run it bounded:
//   PART=seams bash scripts/test-touch-bounded.sh tests/zone-shape-ui.cjs   (then PART=rest, then PART=walls)
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'test-results/zone-shapes');
fs.mkdirSync(out, { recursive: true });
const port = 18400 + (process.pid % 400);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'zone-shape-'));
let server, browser, checks = 0;
const check = (value, label) => { assert.ok(value, label); checks++; };
const world = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8'));
const zoneDef = z => (z === 0 ? world : world.zones[z - 1]);
const onLand = (z, x, y) => zoneDef(z).shapeFloor[Math.floor(y)]?.[Math.floor(x)] === '#';
(async () => {
  server = spawn(process.env.VALHALLA_BINARY, [], {
    cwd: root, stdio: 'ignore',
    env: { ...process.env, VALHALLA_BIND: `127.0.0.1:${port}`, VALHALLA_DB: path.join(tmp, 'v.sqlite'), VALHALLA_CLIENT_DIR: path.join(root, 'client'), VALHALLA_TEST_COMMANDS: '1', VALHALLA_GOD_MODE: '1', VALHALLA_LEVEL_SPREAD: '0' },
  });
  for (let i = 0; i < 100; i++) { try { if ((await fetch(`http://127.0.0.1:${port}/health`)).ok) break; } catch (_) {} await new Promise(r => setTimeout(r, 200)); }
  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {} })));
  await page.goto(`http://127.0.0.1:${port}/`); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('ShapeWalker'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  const debug = command => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);
  const where = () => page.evaluate(() => ({ zone: Field.zone, x: Field.hero.nx, y: Field.hero.ny }));
  // The meadow/Crags border geometry, shared by both parts.

  // SHOTS=zone:x:y,... only takes screenshots at those places (for looking at walls), then stops.
  if (process.env.SHOTS) {
    for (const [zone, x, y] of process.env.SHOTS.split(',').map(v => v.split(':').map(Number))) {
      await debug({ op: 'teleport', zone, x, y });
      await page.waitForFunction(([z, x, y]) => Field.zone === z && Math.hypot(Field.hero.nx - x, Field.hero.ny - y) < 3, [zone, x, y], { timeout: 20000 }).catch(() => console.log('no arrival', zone, x, y));
      await page.waitForTimeout(2500);
      await page.addStyleTag({ content: '#dps-meter,.dps-meter{display:none!important}' });
      await page.screenshot({ path: path.join(out, `shot-${zone}-${x}-${y}.png`) });
    }
    return;
  }
  const snap = async (zone, x, y) => {
    await debug({ op: 'teleport', zone, x, y });
    await page.waitForFunction(([z, x, y]) => Field.zone === z && Math.hypot(Field.hero.nx - x, Field.hero.ny - y) < 1.5, [zone, x, y], { timeout: 20000 });
    await page.waitForTimeout(2500);     // neighbour contexts are built one per timer tick after a zone change
    const at = await where();
    if (process.env.DEBUG === 'walls') console.log('wallGhosts', zone, JSON.stringify(await page.evaluate(() => Field.wallGhosts.filter(o => o[1] < 30 && o[2] > 20 && o[2] < 140))));
    if (process.env.DEBUG) console.log('regions', zone, JSON.stringify(await page.evaluate(() => Field.vaultRegions.map(r => ({ to: r.to, shift: r.shift, other: r.other.map(v => Math.round(v)), strip: r.strip && r.strip.map(v => Math.round(v)) })))), 'hero', JSON.stringify(at), JSON.stringify(await page.evaluate(() => Field.ghostKinds)), JSON.stringify(await page.evaluate(() => Field.ghostNpcIds)));
    if (process.env.FULL) await page.screenshot({ path: path.join(out, `vault-full-${zone}-${x.toFixed(0)}-${y.toFixed(0)}.png`) });
    const data = await page.evaluate(() => {
      const cv = document.getElementById('fieldcv'), W = 256, H = 160, o = document.createElement('canvas'); o.width = W; o.height = H;
      const g = o.getContext('2d'); g.drawImage(cv, cv.width * .2, cv.height * .12, cv.width * .6, cv.height * .6, 0, 0, W, H);   // the middle of the field, clear of the HUD
      return { px: Array.from(g.getImageData(0, 0, W, H).data), png: o.toDataURL('image/png') };
    });
    return { at, ...data };
  };
  const diff = (a, b) => { let sum = 0, big = 0, n = a.px.length / 4; for (let i = 0; i < a.px.length; i += 4) { const d = (Math.abs(a.px[i] - b.px[i]) + Math.abs(a.px[i + 1] - b.px[i + 1]) + Math.abs(a.px[i + 2] - b.px[i + 2])) / 3; sum += d; if (d > 40) big++; } return { mean: sum / n, big: big / n }; };
  const save = (name, im) => fs.writeFileSync(path.join(out, name), Buffer.from(im.png.split(',')[1], 'base64'));
  const rows = [];
  for (const zone of (process.env.ZONES || '3,0,1').split(',').map(Number)) {
    const z = zoneDef(zone), arch = z.exitArches.find(a => a.name === 'Skaldholm'), gate = z.portals.find(p => p.id === arch.portal);
    const [wx, wy] = gate.walk, [vx, vy] = gate.vault;
    for (const [s, t] of (process.env.SS || '0:0,-4:14').split(',').map(x => x.split(':').map(Number))) {
      const px = arch.x + wx * s - wy * t, py = arch.y + wy * s + wx * t;       // one world point (t = along the wall), in the zone's frame...
      if (!onLand(zone, px, py)) continue;                      // (the Crags' wall ends at the arch: nothing to stand on beyond it)
      const a = await snap(zone, px, py);                      // ...drawn from this zone,
      const a2 = await snap(zone, px, py);                     // again (the noise floor: animation, timers)
      const b = await snap(4, px + vx, py + vy);               // ...and from Skaldholm (arrival = here + vault)
      const noise = diff(a, a2), d = diff(a, b);
      save(`vault-z${zone}-s${s}-t${t}-zone.png`, a); save(`vault-z${zone}-s${s}-t${t}-city.png`, b);
      rows.push({ zone, s: `${s}/${t}`, noise, d });
      if (process.env.DEBUG) console.log('hero at', JSON.stringify([a.at, b.at]), 'wanted', JSON.stringify([[px, py], [px + vx, py + vy]]));
      console.log(`zone ${zone} s ${s} t ${t}: noise ${noise.mean.toFixed(2)}/${(noise.big * 100).toFixed(1)}%  across the vault ${d.mean.toFixed(2)}/${(d.big * 100).toFixed(1)}% (mean abs diff / % of pixels off by >40)`);
    }
  }
  // Skaldholm's own square is never touched by a neighbour's region (the borders lean across it: the Crags' region once covered its north-east corner).
  await debug({ op: 'teleport', zone: 4, x: 120, y: 30 });
  await page.waitForFunction(() => Field.zone === 4, null, { timeout: 20000 });
  await page.waitForTimeout(2500);
  const intr = await page.evaluate(() => Field.cityIntrusion);
  check(intr && intr.hidden === 0 && intr.ghosts === 0 && intr.season === 0, `no neighbour region hides or replaces anything inside Skaldholm's walls (${JSON.stringify(intr)})`);
  await page.screenshot({ path: path.join(out, 'skaldholm-north-east.png') });
  // A real walk through the vault, both ways: sample the canvas while walking; the step at the zone change must be no bigger than the
  // steps of ordinary walking (a pop shows as a spike).
  const isoKeys = (dx, dy) => [dx - dy > .35 ? 'ArrowRight' : dx - dy < -.35 ? 'ArrowLeft' : null, dx + dy > .35 ? 'ArrowDown' : dx + dy < -.35 ? 'ArrowUp' : null].filter(Boolean);
  const grab = () => page.evaluate(() => {
    const cv = document.getElementById('fieldcv'), W = 128, H = 80, o = document.createElement('canvas'); o.width = W; o.height = H;
    const g = o.getContext('2d'); g.drawImage(cv, cv.width * .2, cv.height * .12, cv.width * .6, cv.height * .6, 0, 0, W, H);
    return { zone: Field.zone, px: Array.from(g.getImageData(0, 0, W, H).data) };
  });
  const walkSpikes = [];
  for (const zone of (process.env.ZONES || '3,0,1').split(',').map(Number)) {
    const z = zoneDef(zone), arch = z.exitArches.find(a => a.name === 'Skaldholm'), gate = z.portals.find(p => p.id === arch.portal);
    const [wx, wy] = gate.walk;
    for (const dir of [1, -1]) {                         // 1 = into Skaldholm, -1 = back out
      const from = dir === 1 ? [zone, arch.x - wx * 9, arch.y - wy * 9] : [4, arch.x - wx * 9 * -1 * 0 + gate.vault[0] + wx * 9, arch.y + gate.vault[1] + wy * 9];
      await snap(from[0], from[1], from[2]);
      const keys = isoKeys(wx * dir, wy * dir);
      for (const k of keys) await page.keyboard.down(k);
      // sample the canvas on every animation frame inside the page (polling from outside is far too slow)
      await page.evaluate(() => {
        const cv = document.getElementById('fieldcv'), W = 64, H = 40, o = document.createElement('canvas'); o.width = W; o.height = H;
        const g = o.getContext('2d', { willReadFrequently: true }); window.__frames = []; window.__rec = true;
        const tick = () => { if (!window.__rec) return; g.drawImage(cv, cv.width * .2, cv.height * .12, cv.width * .6, cv.height * .6, 0, 0, W, H); window.__frames.push({ zone: Field.zone, px: Array.from(g.getImageData(0, 0, W, H).data) }); requestAnimationFrame(tick); };
        requestAnimationFrame(tick);
      });
      const t0 = Date.now();
      while (Date.now() - t0 < 9000) { await page.waitForTimeout(250); const z = await page.evaluate(() => Field.zone); if (z !== zone && dir === 1 || z === zone && dir === -1) { await page.waitForTimeout(1200); break; } }
      for (const k of keys) await page.keyboard.up(k);
      const frames = await page.evaluate(() => { window.__rec = false; return window.__frames; });
      const steps = frames.slice(1).map((f, i) => ({ zone: f.zone, change: f.zone !== frames[i].zone, d: diff({ px: frames[i].px }, { px: f.px }).mean }));
      const at0 = steps.findIndex(x => x.change);          // the frame the zone changes in, and the one drawn after it
      const ordinary = steps.filter((x, i) => !(i === at0 || i === at0 + 1)).map(x => x.d).sort((p, q) => p - q);
      const cross = steps.filter(x => x.change).length === 1 ? [Math.max(steps[at0].d, steps[at0 + 1]?.d || 0)] : steps.filter(x => x.change).map(x => x.d);
      const p90 = ordinary[Math.floor(ordinary.length * .9)] || 0;
      console.log(`zone ${zone} ${dir === 1 ? 'in' : 'out'}: ${frames.length} frames, crossing step ${cross.map(c => c.toFixed(1)).join(',') || 'none'}, ordinary 90th percentile ${p90.toFixed(1)}`);
      check(cross.length === 1, `zone ${zone} ${dir === 1 ? 'in' : 'out'}: the walk crossed the vault once`);
      check(cross[0] <= Math.max(p90 * 1.5, 6), `zone ${zone} ${dir === 1 ? 'in' : 'out'}: no spike at the crossing (${cross[0]?.toFixed(1)} vs ordinary ${p90.toFixed(1)})`);
    }
  }
  // (10 percent: the walls differ in style, the city's long pieces against the zone's ramparts; the missing-neighbour bug was 20)
  for (const r of rows) check(r.d.mean <= Math.max(10, r.noise.mean * 2 + 2) && r.d.big <= Math.max(.10, r.noise.big * 2 + .02), `zone ${r.zone} s ${r.s}: the same point looks the same from both sides of the vault (diff ${r.d.mean.toFixed(1)}, ${(r.d.big * 100).toFixed(1)}% off)`);
  assert.deepEqual(errors, [], 'no page errors: ' + errors.join(' | '));
  console.log(`vault-seamless-ui: ${checks} checks passed; screenshots in ${out}`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => { try { await browser?.close(); } catch (_) {} server?.kill(); fs.rmSync(tmp, { recursive: true, force: true }); });
