// MINIMAP-CENTRED: the minimap is centred on the hero, zooms with the wheel and the [ ] keys (1 = the whole zone, up to 4), and
// shows the neighbour across a seam (Greenmeadow from the Crags). Pilot zones 0 and 1. Starts its own private world (test commands, own database) from
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
  const seam = zoneDef(0).portals.find(p => p.seam).seam, pts = seam.points, [shx, shy] = seam.shift;
  const seg = Math.floor(pts.length / 2), a = pts[seg], b = pts[seg + 1], len = Math.hypot(b[0] - a[0], b[1] - a[1]);
  const q = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2], nrm = [-(b[1] - a[1]) / len, (b[0] - a[0]) / len];
  const inward = onLand(0, q[0] + nrm[0] * 4, q[1] + nrm[1] * 4) ? nrm : [-nrm[0], -nrm[1]];
  const go = async (zone, x, y) => { await debug({ op: 'teleport', zone, x, y }); await page.waitForFunction(([z, px, py]) => Field.zone === z && Math.hypot(Field.hero.nx - px, Field.hero.ny - py) < 2, [zone, x, y], { timeout: 20000 }); await page.waitForTimeout(1500); };
  // [green pixels, water-blue pixels, white hero pixels at the centre] of the minimap canvas
  const pixels = () => page.evaluate(() => { const c = document.getElementById('minimap'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let green = 0, water = 0; for (let i = 0; i < d.length; i += 4) { const r = d[i], g = d[i + 1], bl = d[i + 2]; if (g > r + 25 && g > bl + 25) green++; else if (bl > r + 20 && bl > g - 5 && r < 60) water++; } const k = (c.height / 2 | 0) * c.width + (c.width / 2 | 0), h = [d[k * 4], d[k * 4 + 1], d[k * 4 + 2]]; return { green, water, hero: h }; });
  const shot = name => page.locator('#minimap').screenshot({ path: path.join(out, `minimap-${name}.png`) });
  await page.evaluate(() => Prefs.set({ minimapZoom: 2 }));
  // From the Crags, three tiles from the border: Greenmeadow's land shows on the minimap at the widest zoom, not at 4x far away.
  await go(1, q[0] + shx - inward[0] * 3, q[1] + shy - inward[1] * 3);
  await page.evaluate(() => { Field.minimapZoom(-9); });
  check(await page.evaluate(() => Field.minimapZoom(0)) === 1, 'zoom clamps at 1 (the widest view)');
  await page.waitForTimeout(400); const wide = await pixels(); await shot('crags-seam-zoom1');
  check(wide.green > 400, `Crags minimap at zoom 1 shows Greenmeadow's green land beyond the border (${wide.green} green px)`);
  check(wide.water > 300, `and open water around the land (${wide.water} px)`);
  check(wide.hero.every(v => v > 200), `the hero is drawn in the centre (${wide.hero})`);
  const box = await page.locator('#minimap').boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.wheel(0, -120); await page.mouse.wheel(0, -120); await page.mouse.wheel(0, -120); await page.mouse.wheel(0, -120);
  check(await page.evaluate(() => Field.minimapZoom(0)) === 4, 'the wheel over the minimap zooms in, and clamps at 4');
  check(await page.evaluate(() => Prefs.minimapZoom) === 4, 'the zoom level is saved in Prefs');
  await page.waitForTimeout(400); const close = await pixels(); await shot('crags-seam-zoom4');
  check(close.hero.every(v => v > 200), 'still centred on the hero at zoom 4');
  await page.keyboard.press('BracketLeft');
  check(await page.evaluate(() => Field.minimapZoom(0)) === 3, 'the [ key zooms out one step');
  await page.keyboard.press('BracketRight'); await page.keyboard.press('BracketRight');
  check(await page.evaluate(() => Field.minimapZoom(0)) === 4, 'the ] key zooms in, clamped');
  // Far from the border, at 4x, no Greenmeadow green is in view; the view moves with the hero.
  const farX = zoneDef(1).shape.offset[0] + 60, farY = zoneDef(1).shape.offset[1] + 80;
  await go(1, farX, farY); await page.waitForTimeout(400); const far = await pixels(); await shot('crags-deep-zoom4');
  check(far.green < 60, `deep in the Crags at zoom 4 there is no Greenmeadow on the minimap (${far.green} green px)`);
  // Greenmeadow side: the Crags' dark ground shows beyond the border.
  await page.evaluate(() => { Field.minimapZoom(-9); });
  await go(0, q[0] + inward[0] * 3, q[1] + inward[1] * 3); await page.waitForTimeout(400); await shot('meadow-seam-zoom1');
  const mw = await pixels(); check(mw.hero.every(v => v > 200) && mw.green > 400, `Greenmeadow minimap at zoom 1 is centred and green (${mw.green} px)`);
  await page.evaluate(() => { Field.minimapZoom(9); });
  assert.deepEqual(errors, [], 'no page errors'); console.log(`${checks} minimap checks passed`);
  await browser.close(); server.kill();
})().catch(e => { console.error(e); try { server.kill(); } catch (_) {} process.exit(1); });
