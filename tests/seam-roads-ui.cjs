// Roads across the seams of the zone-shapes pilot (scripts/seam_roads.py; the data check is tests/seam-roads.py): the real client stands a hero
// on each side of a border at the point where the road crosses it and draws the picture from BOTH frames, so the dirt can be seen to run on.
// Starts its own private world from VALHALLA_BINARY, writes pictures to test-results/seam-roads/. Run it bounded:
//   PAIR=0-3 bash scripts/test-touch-bounded.sh tests/seam-roads-ui.cjs     (PAIR=a-b narrows it; the default is every pair)
// It asserts that the hero arrives on the crossing point in both zones, that every pair has a picture from both frames and that the page stays free of errors;
// the dirt itself is judged by eye on the pictures (the data check tests/seam-roads.py asserts the roads meet).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'test-results/seam-roads');
fs.mkdirSync(out, { recursive: true });
const port = 18800 + (process.pid % 400);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'seam-roads-'));
let server, browser, checks = 0;
const check = (value, label) => { assert.ok(value, label); checks++; };
const world = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8'));
const zoneDef = z => (z === 0 ? world : world.zones[z - 1]);
const ROAD_ZONES = [0, 1, 2, 3, 6, 16];
const segDist = (px, py, a, b) => { const dx = b[0] - a[0], dy = b[1] - a[1], L = dx * dx + dy * dy, t = L ? Math.max(0, Math.min(1, ((px - a[0]) * dx + (py - a[1]) * dy) / L)) : 0; return Math.hypot(px - a[0] - t * dx, py - a[1] - t * dy); };
const polyDist = (px, py, poly) => { let d = 1e9; for (let i = 0; i + 1 < poly.length; i++) d = Math.min(d, segDist(px, py, poly[i], poly[i + 1])); return d; };
// every seam pair and the point of the border where the two roads meet
const pairs = [];
for (const a of ROAD_ZONES) for (const p of zoneDef(a).portals || []) {
  if (!p.seam || !ROAD_ZONES.includes(p.to) || p.to < a) continue;
  const b = p.to, [sx, sy] = p.seam.shift, border = p.seam.points;
  let best = null;
  for (const road of zoneDef(a).paths) for (const v of road) {
    const d = polyDist(v[0], v[1], border), db = Math.min(...zoneDef(b).paths.map(r => polyDist(v[0] + sx, v[1] + sy, r)));
    if (!best || d + db < best.d) best = { d: d + db, at: v };
  }
  pairs.push({ a, b, shift: [sx, sy], at: best.at, border });
}
const only = process.env.PAIR;
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
  await page.addInitScript(() => localStorage.setItem('valhallasc.whats-new.v1', 'Beta 1.39.30'));
  await page.goto(`http://127.0.0.1:${port}/`); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('RoadWalker'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  const debug = command => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);
  check(pairs.length >= 6, `${pairs.length} seam pairs`);
  for (const pr of pairs) {
    if (only && only !== `${pr.a}-${pr.b}`) continue;
    for (const [zone, x, y] of [[pr.a, pr.at[0], pr.at[1]], [pr.b, pr.at[0] + pr.shift[0], pr.at[1] + pr.shift[1]]]) {
      // stand a few tiles back from the line on this side so the crossing is in view with the road leading up to it
      const z = zoneDef(zone), road = z.paths.filter(r => polyDist(x, y, r) < 1).pop();
      const k = road.findIndex(v => Math.hypot(v[0] - x, v[1] - y) < 1.5), back = road[Math.max(k - 1, 0)];
      const dir = [back[0] - x, back[1] - y], L = Math.hypot(dir[0], dir[1]) || 1;
      const sx = x + dir[0] / L * 3, sy = y + dir[1] / L * 3;
      await debug({ op: 'teleport', zone, x: sx, y: sy });
      await page.waitForFunction(([zn, tx, ty]) => Field.zone === zn && Math.hypot(Field.hero.nx - tx, Field.hero.ny - ty) < 2, [zone, sx, sy], { timeout: 30000 });
      await page.waitForTimeout(1500);
      await page.screenshot({ path: path.join(out, `pair-${pr.a}-${pr.b}-from-${zone}.png`) });
      check(true, `pair ${pr.a}-${pr.b}: picture from zone ${zone} at (${sx.toFixed(1)},${sy.toFixed(1)}), road meets the border at (${x.toFixed(1)},${y.toFixed(1)})`);
    }
  }
  check(errors.length === 0, `no page errors: ${errors.join('; ')}`);
  console.log(`seam-roads-ui: ${checks} checks passed`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => { try { await browser?.close(); } catch (_) {} server?.kill(); });
