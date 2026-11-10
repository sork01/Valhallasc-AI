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
  // FIELD_JS=<file> serves that file as client/field.js (a candidate or the old version for a mutation check) without touching the live client.
  if (process.env.FIELD_JS) await page.route('**/field.js*', r => r.fulfill({ path: process.env.FIELD_JS, contentType: 'application/javascript' }));
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
  // Fog is its own thing (a fresh guest has explored one meadow cell): explore everything so the ground comparisons below read land, not mist.
  await debug({ op: 'explore_all' }); await page.waitForTimeout(600);
  // From the Crags, three tiles from the border: Greenmeadow's land shows on the minimap at the widest zoom, not at 4x far away.
  await go(1, q[0] + shx - inward[0] * 3, q[1] + shy - inward[1] * 3);
  await page.evaluate(() => { Field.minimapZoom(-9); });
  check(await page.evaluate(() => Field.minimapZoom(0)) === 1, 'zoom clamps at 1 (the widest view)');
  await page.waitForTimeout(400); const wide = await pixels(); await shot('crags-seam-zoom1');
  check(wide.green > 400, `Crags minimap at zoom 1 shows Greenmeadow's green land beyond the border (${wide.green} green px)`);
  // The Crags are landlocked: past their east border (the Orrery, a seam since 2026-11-08) the minimap shows the Orrery's land, no foam line, no shallows, no sea, on and past the grid.
  const east = q2 => page.evaluate(([hx, hy, xs]) => { const c = document.getElementById('minimap'), g = c.getContext('2d'), s = c.width / 240; return xs.map(x => [...g.getImageData(Math.round(c.width / 2 + (x - hx) * s), Math.round(c.height / 2), 1, 1).data].slice(0, 3)); }, q2);
  await go(1, 335, 170); await page.waitForTimeout(600);
  const beyond = await east([335, 170, [346.5, 347.5, 349, 352, 358, 380, 420]]); await shot('crags-east-landlocked');
  check(beyond.slice(2).every(([r, g, b]) => b <= r + 60), `past the Crags' east border there is no water (shallows are 70,184,200; the Orrery's own ground is a bluish grey): ${JSON.stringify(beyond)}`);
  // MINIMAP-WORLD: a border with NO seam shows the neighbour's land too (the Stormglass Flats and Frostwake Shelf are a gate, not a seam).
  // Pick, from the real outlines, a Frostwake tile as near as possible to a Stormglass tile; from that Stormglass tile the Frostwake tile is on the minimap, past Stormglass' own land.
  const land = z => { const f = zoneDef(z).shapeFloor, out = []; for (let y = 0; y < f.length; y++) for (let x = 0; x < f[y].length; x++) if (f[y][x] === '#') out.push([x, y]); return out; };
  const dT = [zoneDef(26).shape.T[0] - zoneDef(19).shape.T[0], zoneDef(26).shape.T[1] - zoneDef(19).shape.T[1]];
  const inland = (z, x, y) => [[3, 0], [-3, 0], [0, 3], [0, -3], [0, 0]].every(([i, j]) => zoneDef(z).shapeFloor[y + j]?.[x + i] === '#');   // not the cliff line along the border
  const fw = land(19).filter(([x, y]) => inland(19, x, y)), sv = land(26).filter(([x, y], i) => i % 7 === 0 && inland(26, x, y)).map(([x, y]) => [x + dT[0], y + dT[1]]);
  let best = null; for (const [fx, fy] of fw.filter((_, i) => i % 5 === 0)) for (const [sx, sy] of sv) { const d = Math.hypot(fx - sx, fy - sy); if (d > 16 && (!best || d < best.d)) best = { d, f: [fx, fy], s: [sx, sy] }; }
  check(best && best.d < 60, `the Stormglass Flats and Frostwake Shelf lie within sight of each other on the atlas (${best && best.d.toFixed(1)} tiles)`);
  await go(19, best.f[0] + .5, best.f[1] + .5);
  await page.waitForFunction(() => (Field.miniZones || []).includes(26), null, { timeout: 15000 }).catch(() => {}); await page.waitForTimeout(500);   // the neighbour's canvas is built one zone per timer tick
  await shot('stormglass-frostwake-gate');
  const px = await page.evaluate(([hx, hy, tx, ty]) => { const c = document.getElementById('minimap'), g = c.getContext('2d'), s = c.width / 240; return [...g.getImageData(Math.round(c.width / 2 + (tx - hx) * s), Math.round(c.height / 2 + (ty - hy) * s), 1, 1).data].slice(0, 3); }, [best.f[0] + .5, best.f[1] + .5, best.s[0] + .5, best.s[1] + .5]);
  check(Math.hypot(px[0] - 43, px[1] - 36, px[2] - 33) > 25, `Frostwake's ground shows from the Stormglass Flats across a gate border with no seam (pixel ${px}; the old client drew the plain sea colour 22,47,60)`);
  check(((await page.evaluate(() => Field.miniZones)) || []).includes(26), 'Frostwake (zone 26) is in the minimap cache from the Stormglass Flats');
  // The open sea is the game's own water colour (hsl 200 46% 16% = 22,47,60), not a black, and a coast at the edge of a zone's grid (Astralhollow's north, the edge of the atlas) gets its full 14 tiles of shallows like a coast with room to spare.
  const fl = zoneDef(13).shapeFloor; let top = null; for (let y = 0; y < fl.length && !top; y++) for (let x = 40; x < fl[y].length - 40; x++) if (fl[y][x] === '#' && [-8, -4, 0, 4, 8].every(i => fl[y + 6]?.[x + i] === '#') && [-8, -4, 0, 4, 8].every(i => fl[y][x + i] === '#')) { top = [x, y]; break; }
  await go(13, top[0] + .5, top[1] + 6.5); await page.evaluate(() => { Field.minimapZoom(-9); }); await page.waitForTimeout(1200); await shot('astralhollow-north-coast');
  const sea = dy => page.evaluate(dyy => { const c = document.getElementById('minimap'), g = c.getContext('2d'), s = c.width / 240, out = []; for (const dx of [-24, -16, -8, 8, 16, 24]) { const d = g.getImageData(Math.round(c.width / 2 + dx * s), Math.round(c.height / 2 + dyy * s), 1, 1).data; out.push([d[0], d[1], d[2]]); } return out.sort((a, b) => a[1] - b[1])[3]; }, dy);
  const shallow = await sea(-6 - 5), deepSea = await sea(-6 - 42);
  check(shallow[1] > 85 && shallow[2] > shallow[0] + 50, `five tiles off Astralhollow's north coast the shallows show (${shallow}); the old grid edge clipped them`);
  check(Math.hypot(deepSea[0] - 22, deepSea[1] - 47, deepSea[2] - 60) < 12, `the open sea beyond is the game's water colour 22,47,60, not black (${deepSea})`);
  // The base fill covered only 144 x 144 units of a canvas that is bigger for a big zone: Rimeveil's east strip (here) and Gloamfen's right and bottom were black on the minimap.
  await go(2, 290, 215); await page.waitForTimeout(1500);
  const rime = await page.evaluate(() => { const c = document.getElementById('minimap'), g = c.getContext('2d'), s = c.width / 240, out = []; for (const dx of [10, 14, 18, 22]) for (const dy of [-16, -8, 8, 16]) { const d = g.getImageData(Math.round(c.width / 2 + dx * s), Math.round(c.height / 2 + dy * s), 1, 1).data; out.push(d[0] + d[1] + d[2]); } return out.sort((a, b) => a - b); });
  await shot('rimeveil-east-strip');
  check(rime[rime.length >> 1] > 450, `Rimeveil's east strip is snow on the minimap, not black (median brightness of ${rime.length} points ${rime[rime.length >> 1]} of 765): ${JSON.stringify(rime)}`);
  // A crossing changes nothing: the same world points on the minimap, from each side of the Crags-meadow border (owner: blue from the meadow, black from the Crags).
  const grid = []; for (let i = -5; i <= 5; i++) for (let j = -5; j <= 5; j++) grid.push([i * 20, j * 20]);
  const world = ([cx, cy]) => page.evaluate(([hx, hy, px, py, g2]) => { const c = document.getElementById('minimap'), g = c.getContext('2d'), s = c.width / 240; return g2.map(([i, j]) => { const d = g.getImageData(Math.round(c.width / 2 + (px + i - hx) * s) - 4, Math.round(c.height / 2 + (py + j - hy) * s) - 4, 9, 9).data, m = [0, 0, 0, 0]; for (let k = 0; k < d.length; k += 4) { for (let q = 0; q < 3; q++) m[q] += d[k + q] / 81; const [r, gg, bb] = [d[k], d[k + 1], d[k + 2]]; if (r >= 235 && gg <= 125 && bb >= 120 && bb <= 160 || bb >= 245 && r >= 190 && gg >= 170 && r <= 215 || r >= 240 && gg >= 200 && bb <= 135 || r >= 170 && gg >= 215 && bb >= 245 || r >= 250 && gg >= 250 && bb >= 250) m[3] = 1; } return m; }); }, [cx[0], cx[1], cy[0], cy[1], grid]);
  await go(0, q[0] + inward[0] * 3, q[1] + inward[1] * 3); await page.waitForTimeout(600);
  const fromMeadow = await world([[q[0] + inward[0] * 3, q[1] + inward[1] * 3], [q[0], q[1]]]); await shot('seam-from-meadow');
  await go(1, q[0] + shx - inward[0] * 3, q[1] + shy - inward[1] * 3); await page.waitForTimeout(600);
  const fromCrags = await world([[q[0] + shx - inward[0] * 3, q[1] + shy - inward[1] * 3], [q[0] + shx, q[1] + shy]]); await shot('seam-from-crags');
  await go(0, q[0] + inward[0] * 3, q[1] + inward[1] * 3); await page.waitForTimeout(600);
  const again = await world([[q[0] + inward[0] * 3, q[1] + inward[1] * 3], [q[0], q[1]]]);
  // Markers still belong to the zone you stand in (MINIMAP-WORLD): a pink, red or gold dot on either side is not the ground.
  const marker = ([r, g, b]) => r > 170 && g < 170 && b > 60 || r > 200 && g > 150 && b < 130;
  const apart = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]) > 30;
  // A point whose window holds an enemy, player or travel dot (pink, purple, light blue, gold, white) is skipped: those belong to the zone you stand in and come from the server's view of you.
  const differ = grid.map((p, i) => [p, again[i], fromCrags[i]]).filter(([, a, b]) => !a[3] && !b[3] && !marker(a) && !marker(b) && apart(a, b));
  console.log('minimap diff', JSON.stringify(differ.map(([p, a, c]) => [p, a.map(Math.round), c.map(Math.round)])));
  // What is left is the enemy dots of the zone you stand in, blurred into the 7 px mean, and speckled fog edges; the client before the shared background gives 26.
  check(differ.length <= 10, `the ground on the minimap is the same from both sides of the border: ${differ.length} of ${grid.length} points differ`);
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
  // Touch: the zoom buttons exist only on a coarse pointer (hidden with a mouse), and tapping them zooms.
  check(await page.evaluate(() => ['mini-zoom-in', 'mini-zoom-out'].every(id => getComputedStyle(document.getElementById(id)).display === 'none')), 'no zoom buttons with a mouse');
  // Two full clients do not fit the 1.5 GiB cap of the bounded runner (the first one died with oom-kill, with the old client too): close the desktop one first.
  assert.deepEqual(errors, [], 'no page errors'); await context.close();
  const tctx = await browser.newContext({ viewport: { width: 844, height: 390 }, isMobile: true, hasTouch: true, reducedMotion: 'reduce' });
  const tp = await tctx.newPage(); const terrors = [];
  tp.on('pageerror', e => terrors.push(e.message));
  await tp.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {}, minimapZoom: 2 })));
  await tp.goto(`http://127.0.0.1:${port}/`); await tp.locator('#start').click(); await tp.locator('#login-guest').click();
  await tp.locator('#name').fill('TouchZoom'); await tp.locator('#go').click({ timeout: 60000 });
  await tp.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  const zoomIn = tp.locator('#mini-zoom-in'), zoomOut = tp.locator('#mini-zoom-out');
  check(await zoomIn.isVisible() && await zoomOut.isVisible(), 'zoom buttons show on a touch device');
  const mb = await tp.locator('#minimap').boundingBox(), bi = await zoomIn.boundingBox(), bo = await zoomOut.boundingBox();
  console.log('touch minimap', JSON.stringify(mb), 'in', JSON.stringify(bi), 'out', JSON.stringify(bo));
  check(bi.x + bi.width <= mb.x + 1 && bo.x + bo.width <= mb.x + 1 && bo.y >= bi.y + bi.height, 'the buttons sit left of the minimap, stacked, not on top of it');
  check(Math.min(bi.width, bi.height, bo.width, bo.height) >= 44, `touch targets are at least 44 px on screen (${bi.width.toFixed(0)} x ${bi.height.toFixed(0)})`);
  check(bi.x >= 0 && bi.y >= 0 && bo.y + bo.height <= 390, 'both buttons are on screen');
  await zoomIn.tap(); check(await tp.evaluate(() => Field.minimapZoom(0)) === 3, 'tapping + zooms in');
  await zoomIn.tap(); check(await tp.evaluate(() => Field.minimapZoom(0)) === 4 && await zoomIn.isDisabled(), 'zoom in stops at 4 and + greys out');
  await zoomOut.tap(); await zoomOut.tap(); await zoomOut.tap(); check(await tp.evaluate(() => Field.minimapZoom(0)) === 1 && await zoomOut.isDisabled(), 'zoom out stops at 1 and \u2212 greys out');
  await tp.screenshot({ path: path.join(out, 'minimap-touch.png') });
  assert.deepEqual(terrors, [], 'no touch page errors');
  assert.deepEqual(errors, [], 'no page errors'); console.log(`${checks} minimap checks passed`);
  await browser.close(); server.kill();
})().catch(e => { console.error(e); try { server.kill(); } catch (_) {} process.exit(1); });
