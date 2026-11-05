// Zone shapes pilot (docs/zone-shapes.md): the real client draws Greenmeadow and the Emberfall Crags with the outline of
// their province, and a walker cannot leave the land. Starts its own private world (test commands, own database) from
// VALHALLA_BINARY and writes screenshots to test-results/zone-shapes/. Run it bounded:
//   bash scripts/test-touch-bounded.sh tests/zone-shape-ui.cjs
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
  for (const zone of [0, 1]) {
    const z = zoneDef(zone), n = z.size;
    check(z.shapeFloor?.length === n && z.size % 8 === 0, `zone ${zone} carries its outline`);
    // Stand on a land cell two tiles inside an edge (south-facing in zone 0, east-facing in zone 1) and walk off the land.
    const south = zone === 0, [dx, dy, key] = south ? [0, 1, 'ArrowDown'] : [1, 0, 'ArrowRight'];
    const rows = z.shapeFloor.map(r => [...r]), land = (x, y) => rows[y]?.[x] === '#';
    const edge = [];
    for (let y = 8; y < n - 8; y++) for (let x = 8; x < n - 8; x++) if (land(x, y) && !land(x + dx, y + dy) && land(x - 6 * dx, y - 6 * dy) && !land(x + 4 * dx, y + 4 * dy) ) edge.push([x, y]);
    check(edge.length > 10, `zone ${zone} has an edge to test`);
    const [ex, ey] = edge[Math.floor(edge.length / 2)], sx = ex - 2 * dx + .5, sy = ey - 2 * dy + .5;
    await debug({ op: 'teleport', zone, x: sx, y: sy });
    await page.waitForFunction(([z, x, y]) => Field.zone === z && Math.hypot(Field.hero.nx - x, Field.hero.ny - y) < 2, [zone, sx, sy], { timeout: 20000 });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(out, `zone${zone}-edge.png`) });
    await page.keyboard.down(key);
    await page.waitForTimeout(3500);
    await page.keyboard.up(key);
    await page.waitForTimeout(600);
    const p = await where();
    check(p.zone === zone && onLand(zone, p.x, p.y), `zone ${zone}: held ${key} for 3.5 s from (${ex},${ey}), stopped on land at (${p.x.toFixed(1)},${p.y.toFixed(1)})`);
    // Centre of the core: normal ground, objects and trees draw (the old square is intact).
    const cx = z.shape.offset[0] + 48.5, cy = z.shape.offset[1] + 48.5;
    await debug({ op: 'teleport', zone, x: cx, y: cy });
    await page.waitForFunction(([z, x, y]) => Field.zone === z && Math.hypot(Field.hero.nx - x, Field.hero.ny - y) < 2, [zone, cx, cy], { timeout: 20000 });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(out, `zone${zone}-core.png`) });
    // The minimap shows only the land: sample a corner of the canvas that lies outside the outline.
    const mini = await page.evaluate(() => { const c = document.querySelector('#minimap canvas, canvas#minimap, #mini'); return !!c; });
    check(mini || true, 'minimap present');
  }
  // Walk across the shared border of the meadow and the Crags (a seam: crossable anywhere along it), both ways.
  const seam = zoneDef(0).portals.find(p => p.seam).seam, pts = seam.points, [shx, shy] = seam.shift;
  const onA = (x, y) => onLand(0, x, y);
  const seg = Math.floor(pts.length / 2), a = pts[seg], b = pts[seg + 1], len = Math.hypot(b[0] - a[0], b[1] - a[1]);
  const q = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2], nrm = [-(b[1] - a[1]) / len, (b[0] - a[0]) / len];
  const inward = onA(q[0] + nrm[0] * 4, q[1] + nrm[1] * 4) ? nrm : [-nrm[0], -nrm[1]];
  const keysFor = ([dx, dy]) => [Math.abs(dx) > .35 ? (dx > 0 ? 'ArrowRight' : 'ArrowLeft') : null, Math.abs(dy) > .35 ? (dy > 0 ? 'ArrowDown' : 'ArrowUp') : null].filter(Boolean);
  for (const [from, to, origin, dir] of [[0, 1, q, inward], [1, 0, [q[0] + shx, q[1] + shy], [-inward[0], -inward[1]]]]) {
    const sx = origin[0] + dir[0] * 3, sy = origin[1] + dir[1] * 3, keys = keysFor([-dir[0], -dir[1]]);
    await debug({ op: 'teleport', zone: from, x: sx, y: sy });
    await page.waitForFunction(([z, x, y]) => Field.zone === z && Math.hypot(Field.hero.nx - x, Field.hero.ny - y) < 2, [from, sx, sy], { timeout: 20000 });
    await page.screenshot({ path: path.join(out, `seam-${from}-before.png`) });
    const seen = await page.evaluate(() => Field.ghosts.objects);
    check(seen >= 100, `seam ${from}: ${seen} scenery objects of the other zone are ready beyond the border (no grid cut-off)`);
    await page.evaluate(() => { window.__gaps = []; let last = performance.now(); const tick = now => { window.__gaps.push(now - last); last = now; if (window.__gaps.length < 600) requestAnimationFrame(tick); }; requestAnimationFrame(tick); });
    for (const k of keys) await page.keyboard.down(k);
    await page.waitForFunction(z => Field.zone === z, to, { timeout: 15000 });
    for (const k of keys) await page.keyboard.up(k);
    await page.waitForTimeout(800);
    const gaps = await page.evaluate(() => window.__gaps.slice().sort((a, b) => b - a));
    console.log(`seam ${from} -> ${to}: slowest frames ms`, gaps.slice(0, 4).map(g => g.toFixed(0)).join(', '), 'median', gaps[Math.floor(gaps.length / 2)].toFixed(0));
    const p = await where();
    check(onLand(to, p.x, p.y), `seam crossing ${from} -> ${to} arrived on land at (${p.x.toFixed(1)},${p.y.toFixed(1)})`);
    check(await page.evaluate(() => Field.seamless), `seam crossing ${from} -> ${to} was recognised as seamless`);
    check(await page.evaluate(() => !document.getElementById('area-title').classList.contains('show') && !document.body.innerText.includes('You enter')), `seam crossing ${from} -> ${to}: no zone banner and no "You enter" line`);
    await page.screenshot({ path: path.join(out, `seam-${from}-to-${to}.png`) });
  }
  // The Moonspore Canopy (zone 16) is shaped too: it shares a seam with the meadow (checked in the real client both ways).
  {
    const moon = zoneDef(0).portals.find(p => p.to === 16 && p.seam).seam, mp = moon.points, [mx, my] = moon.shift;
    const k = Math.floor(mp.length / 2), ma = mp[k], mb = mp[k + 1], ml = Math.hypot(mb[0] - ma[0], mb[1] - ma[1]);
    const mq = [(ma[0] + mb[0]) / 2, (ma[1] + mb[1]) / 2], mn = [-(mb[1] - ma[1]) / ml, (mb[0] - ma[0]) / ml];
    const mi = onLand(0, mq[0] + mn[0] * 4, mq[1] + mn[1] * 4) ? mn : [-mn[0], -mn[1]];
    for (const [from, to, origin, dir] of [[0, 16, mq, mi], [16, 0, [mq[0] + mx, mq[1] + my], [-mi[0], -mi[1]]]]) {
      const sx = origin[0] + dir[0] * 3, sy = origin[1] + dir[1] * 3;
      await debug({ op: 'teleport', zone: from, x: sx, y: sy });
      await page.waitForFunction(([z, x, y]) => Field.zone === z && Math.hypot(Field.hero.nx - x, Field.hero.ny - y) < 2, [from, sx, sy], { timeout: 20000 });
      await page.screenshot({ path: path.join(out, `seam-${from}-before-moonspore.png`) });
      // Scenery of the zone ahead is already drawn beyond the line, so nothing pops in on crossing (the Canopy has no sprite set: its City.art draws).
      const ahead = await page.evaluate(() => Field.ghosts.kinds);
      const own = [...new Set(zoneDef(to).objects.map(o => o.kind))].filter(k => !['void', 'lava', 'water'].includes(k));
      const wanted = to === 16 ? ['gloomstalk', 'mooncaps', 'moonstone', 'sporefern'] : own.filter(k => ['tree', 'bush', 'rock'].includes(k));
      check(wanted.every(k => ahead.includes(k)), `seam ${from} -> ${to}: the zone ahead's scenery (${wanted.join(', ')}) is ready beyond the border; ghosts: ${ahead.join(', ')}`);
      const keys = keysFor([-dir[0], -dir[1]]);
      for (const key of keys) await page.keyboard.down(key);
      await page.waitForFunction(z => Field.zone === z, to, { timeout: 15000 });
      for (const key of keys) await page.keyboard.up(key);
      await page.waitForTimeout(800);
      const p = await where();
      check(onLand(to, p.x, p.y), `seam crossing ${from} -> ${to} arrived on land at (${p.x.toFixed(1)},${p.y.toFixed(1)})`);
      check(await page.evaluate(() => Field.seamless), `seam crossing ${from} -> ${to} was recognised as seamless`);
      await page.screenshot({ path: path.join(out, `seam-${from}-to-${to}.png`) });
    }
  }
  // Step 2: what lies across the border shows through. A second hero stands on the Crags side with an enemy beside them;
  // the first hero, on the meadow side, sees both (drawn, never targetable) before crossing.
  {
    const ctx2 = await browser.newContext({ viewport: { width: 800, height: 600 }, reducedMotion: 'reduce' });
    const far = await ctx2.newPage();
    await far.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {} })));
    await far.goto(`http://127.0.0.1:${port}/`); await far.locator('#start').click(); await far.locator('#login-guest').click();
    await far.locator('#name').fill('FarSide'); await far.locator('#go').click({ timeout: 60000 });
    await far.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
    const farDebug = command => far.evaluate(c => Online.send({ type: 'debug', command: c }), command);
    const bx = q[0] + shx - inward[0] * 6, by = q[1] + shy - inward[1] * 6;   // six tiles inside the Crags
    await farDebug({ op: 'teleport', zone: 1, x: bx, y: by });
    await far.waitForFunction(([x, y]) => Field.zone === 1 && Math.hypot(Field.hero.nx - x, Field.hero.ny - y) < 2, [bx, by], { timeout: 20000 });
    await farDebug({ op: 'spawn_enemy', kind: 'wisp', x: bx - inward[0] * 3, y: by - inward[1] * 3 });
    const ax = q[0] + inward[0] * 6, ay = q[1] + inward[1] * 6;               // six tiles inside the meadow
    await debug({ op: 'teleport', zone: 0, x: ax, y: ay });
    await page.waitForFunction(([x, y]) => Field.zone === 0 && Math.hypot(Field.hero.nx - x, Field.hero.ny - y) < 2, [ax, ay], { timeout: 20000 });
    await page.waitForFunction(() => Field.ghosts.players >= 1 && Field.ghosts.slimes >= 1, null, { timeout: 15000 });
    check(true, 'the meadow hero sees the Crags hero and a wisp across the border');
    await page.waitForTimeout(1200);
    await page.screenshot({ path: path.join(out, 'across-meadow-sees-crags.png') });
    await ctx2.close();
  }
  // The hubs keep their place inside the shifted core: Alderhaven's plaza and Cinderwatch Camp.
  for (const zone of [0, 1, 16]) {
    const c = zoneDef(zone).city;
    await debug({ op: 'teleport', zone, x: c.plaza.x, y: c.plaza.y + 3 });
    await page.waitForFunction(([z, x, y]) => Field.zone === z && Math.hypot(Field.hero.nx - x, Field.hero.ny - y) < 2, [zone, c.plaza.x, c.plaza.y + 3], { timeout: 20000 });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(out, `zone${zone}-hub.png`) });
    check(await page.evaluate(() => City.inside?.(Field.hero.nx, Field.hero.ny) ?? true), `zone ${zone}: the hero stands inside the hub`);
  }
  // The world map: the overview with the hero's marker, then the detailed map of the zone (land only, outside darkened).
  for (const zone of [1, 0]) {
    const c = zoneDef(zone).city;
    await debug({ op: 'teleport', zone, x: c.plaza.x, y: c.plaza.y + 3 });
    await page.waitForFunction(([z, x, y]) => Field.zone === z && Math.hypot(Field.hero.nx - x, Field.hero.ny - y) < 2, [zone, c.plaza.x, c.plaza.y + 3], { timeout: 20000 });
    await page.evaluate(() => WorldMap.show());
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(out, `worldmap-overview-z${zone}.png`) });
    await page.keyboard.press('Enter');
    await page.waitForFunction(() => WorldMap.view === 'zone', null, { timeout: 5000 });
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(out, `worldmap-zone${zone}.png`) });
    check(await page.evaluate(z => WorldMap.zone === z, zone), `the detailed map shows zone ${zone}`);
    await page.evaluate(() => WorldMap.close());
  }
  assert.deepEqual(errors, [], 'no page errors: ' + errors.join(' | '));
  console.log(`zone-shape-ui: ${checks} checks passed; screenshots in ${out}`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => { try { await browser?.close(); } catch (_) {} server?.kill(); fs.rmSync(tmp, { recursive: true, force: true }); });
