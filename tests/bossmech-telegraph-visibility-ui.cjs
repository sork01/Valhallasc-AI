// BOSSMECH-TELEGRAPH-VISIBILITY: can a player see where a dungeon boss's telegraph lands, at noon and at night? Dungeons and raids
// have no night (client/daynight.js isOutdoor is false for zones with players, copies, a template or an indoor theme), so the clock
// must not darken them: DayNight.nightMix stays 0 at 01:00. Two real final bosses from world/boss-mechanics.txt in their own
// dungeons, with the real tables: Thunder Heart's Static (blue rods, Thunderheart Gate, zone 35) and the Black Hour Foundry's
// Midnight Press (red lanes, zone 44).
// Contrast is measured on the canvas, same pixels, same frame time: the telegraph list is read as drawn, then held empty for two
// frames and read again (snapshots are held meanwhile). Ground, scenery and the night veil are identical in both reads, so the
// difference is the telegraph alone. The measure is the mean RGB distance between the two reads over the telegraph's own outline
// (a circle or a lane), per telegraph; the tint and luminance changes are printed too. Numbers go to the artifacts folder.
// MUTATE=outdoor serves daynight.js with every zone treated as outdoors: nightMix must then be above 0 at 01:00 and the check fails.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const release = path.join(root, 'target/release/valhalla-server');
const debug = path.join(root, 'target/debug/valhalla-server');
const newest = [release, debug].filter(f => fs.existsSync(f)).sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs)[0];
const binary = process.env.VALHALLA_BINARY || newest;
const minDist = Number(process.env.MIN_DIST || 8);   // mean RGB units a telegraph must change its own outline by
const viewport = process.env.VIEW === 'phone' ? { width: 844, height: 390 } : { width: 1440, height: 900 };
const client = new Client({ name: 'valhallasc-bossmech-telegraph-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
// The real dungeons: the hero stands at the arena centre (so the telegraphs are around the view), the boss is spawned beside them.
const CASES = [
  { label: 'static', boss: 'thunder_heart', zone: 35, theme: 'thunderheart_gate', at: { x: 70, y: 18 }, tele: 'blue', shape: 'circle' },
  { label: 'midnight_press', boss: 'null_hour', zone: 44, theme: 'blackhour', at: { x: 80, y: 27 }, tele: 'red', shape: 'lane', waitMs: 90000 },
];

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe',
    env: { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0', ...(binary ? { VALHALLA_BINARY: binary } : {}) } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  if (process.env.MUTATE === 'outdoor') {
    // the mutation: every zone counts as outdoors, so the night veil and the moonlight grade would darken dungeons too
    await page.route('**/daynight.js*', async route => {
      const src = fs.readFileSync(path.join(root, 'client/daynight.js'), 'utf8');
      const from = 'const isOutdoor = z => !!z && !(z.players > 0 || z.copies > 0 || z.template != null || indoorThemes.has(z.theme));';
      assert.ok(src.includes(from), 'daynight.js isOutdoor line changed: update the mutation');
      await route.fulfill({ contentType: 'text/javascript', body: src.replace(from, 'const isOutdoor = z => !!z;') });
    });
  }
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
  // __freezeT: every frame is drawn at one fixed time, so water, pulses and the camera's drift cannot differ between two reads
  await page.addInitScript(() => { const raf = window.requestAnimationFrame.bind(window); window.requestAnimationFrame = cb => raf(ts => cb(window.__freezeT ?? ts)); });
  await page.goto(world.url);
  // the login runs at the desktop size; a phone is then checked by resizing the same page once the hero is in the world
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('Lanternbearer'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.hero.x, null, { timeout: 60000 });
  const send = command => page.evaluate(command => { Online.send({ type: 'debug', ref: Math.floor(Math.random() * 1e9), command }); }, command).then(() => page.waitForTimeout(300));
  await send({ op: 'set_god_mode', enabled: true });
  if (process.env.VIEW === 'phone') { await page.setViewportSize(viewport); await page.waitForTimeout(1200); }

  // Reads every telegraph of the kind on the canvas. The footprint of each one is its own outline (a circle's arc, a lane's rectangle),
  // projected with the same w2s the client draws with, so only pixels the telegraph paints count. The list is read as drawn, then
  // emptied for two frames (BossMech.update([])) and read again; the list comes back afterwards. Same frame time (__freezeT) in both.
  const readAll = (kind, shape) => page.evaluate(async ({ kind, shape }) => {
    const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), k = cv.width / 1600;
    const frame = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
    const targets = BossMech.fights.flatMap(f => (f.tele || []).filter(t => t.tele === kind && t.shapes?.[0]?.t === shape).map(t => t.shapes[0]));
    const W = Field._debug.w2s;
    const outline = s => {
      if (s.t === 'lane') {
        const hw = s.half ?? (s.width || 3) / 2, dx = s.x2 - s.x1, dy = s.y2 - s.y1, len = Math.hypot(dx, dy) || 1, nx = -dy / len * hw, ny = dx / len * hw;
        return [[s.x1 + nx, s.y1 + ny], [s.x2 + nx, s.y2 + ny], [s.x2 - nx, s.y2 - ny], [s.x1 - nx, s.y1 - ny]].map(([x, y]) => W(x, y));
      }
      return Array.from({ length: 48 }, (_, i) => { const a = i / 48 * Math.PI * 2; return W(s.x + Math.cos(a) * (s.r || 1.8), s.y + Math.sin(a) * (s.r || 1.8)); });
    };
    const inside = (poly, px, py) => { let c = false; for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) { const [xi, yi] = poly[i], [xj, yj] = poly[j]; if ((yi > py) !== (yj > py) && px < (xj - xi) * (py - yi) / (yj - yi) + xi) c = !c; } return c; };
    // The snapshot feed also calls BossMech.update every tick: it is held while the telegraphs are off, so a late snapshot cannot put them back.
    const saved = BossMech.fights, origUpdate = window.__bmOrigUpdate || BossMech.update;
    window.__bmOrigUpdate = origUpdate; window.__bmHold = false;
    BossMech.update = list => { if (window.__bmHold) { window.__bmPending = list; return; } return origUpdate(list); };
    window.__freezeT = 600000; await frame();
    const withData = g.getImageData(0, 0, cv.width, cv.height).data.slice();
    window.__bmHold = true; origUpdate([]); await frame(); await frame();
    const withoutData = g.getImageData(0, 0, cv.width, cv.height).data;
    const emptyAtRead = BossMech.fights.length;
    window.__bmHold = false; origUpdate(window.__bmPending && window.__bmPending.length ? window.__bmPending : saved); window.__bmPending = null;
    BossMech.update = origUpdate;
    const pixelsOf = (poly) => {
      const pts = poly.map(([x, y]) => [x * k, y * k]);
      const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
      const x0 = Math.max(0, Math.floor(Math.min(...xs))), x1 = Math.min(cv.width - 1, Math.ceil(Math.max(...xs)));
      const y0 = Math.max(0, Math.floor(Math.min(...ys))), y1 = Math.min(cv.height - 1, Math.ceil(Math.max(...ys)));
      const out = []; for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) if (inside(pts, x + .5, y + .5)) out.push((y * cv.width + x) * 4);
      return out;
    };
    const tintOf = (d, i) => d[i + 2] - (d[i] + d[i + 1]) / 2, lumOf = (d, i) => .299 * d[i] + .587 * d[i + 1] + .114 * d[i + 2];
    const reads = targets.map(s => {
      const [cx, cy] = s.t === 'lane' ? [(s.x1 + s.x2) / 2, (s.y1 + s.y2) / 2] : [s.x, s.y];
      const idx = pixelsOf(outline(s));
      let dT = 0, dL = 0, floorT = 0, dist = 0, changed = 0;
      for (const i of idx) { const dr = withData[i] - withoutData[i], dg = withData[i + 1] - withoutData[i + 1], db = withData[i + 2] - withoutData[i + 2]; dist += Math.hypot(dr, dg, db); dT += tintOf(withData, i) - tintOf(withoutData, i); dL += lumOf(withData, i) - lumOf(withoutData, i); floorT += tintOf(withoutData, i); if (dr || dg || db) changed++; }
      const n = idx.length || 1;
      return { at: [cx, cy], screen: W(cx, cy).map(Math.round), pixels: idx.length, changed, floorTint: floorT / n, colourDelta: dist / n, tintDelta: dT / n, lumDelta: dL / n };
    });
    let changedAll = 0; for (let i = 0; i < withData.length; i += 4) if (withData[i] !== withoutData[i] || withData[i + 2] !== withoutData[i + 2]) changedAll++;
    return { reads, restored: BossMech.fights.length === saved.length, changedAll, hour: DayNight.hour, emptyAtRead, shape: targets[0] || null };
  }, { kind, shape });

  const results = {};
  for (const c of CASES) {
    await send({ op: 'teleport', zone: c.zone, x: c.at.x, y: c.at.y });
    await page.waitForFunction(([z, x, y]) => Field.zone === z && Math.hypot(Field.hero.x - x, Field.hero.y - y) < 3, [c.zone, c.at.x, c.at.y], { timeout: 30000 });
    check(await page.evaluate(() => Field.zoneTheme) === c.theme, `${c.label}: zone ${c.zone} is ${c.theme}`);
    await send({ op: 'spawn_enemy', kind: c.boss, x: c.at.x + 2, y: c.at.y, level: 99 });
    await page.waitForFunction(() => BossMech.active, null, { timeout: 30000 });
    await page.waitForFunction(([tele, shape]) => BossMech.fights.some(f => (f.tele || []).some(t => t.tele === tele && t.shapes?.[0]?.t === shape)), [c.tele, c.shape], { timeout: c.waitMs || 30000 }).catch(() => {});
    check(await page.evaluate(([tele, shape]) => BossMech.fights.some(f => (f.tele || []).some(t => t.tele === tele && t.shapes?.[0]?.t === shape)), [c.tele, c.shape]), `${c.label}: the real ${c.boss} shows a ${c.tele} ${c.shape} telegraph within the wait`);
    results[c.label] = {};
    for (const [label, hour] of [['noon', 12], ['night', 1]]) {
      await send({ op: 'set_time', hour, freeze: true });
      await page.waitForFunction(h => Math.abs(DayNight.hour - h) < 0.5, hour, { timeout: 10000 }).catch(() => {});
      await page.waitForTimeout(900);
      const env = await page.evaluate(() => ({ nightMix: DayNight.nightMix, outdoor: DayNight.isOutdoor(Field._debug.zones[Field.zone]) }));
      const r = await readAll(c.tele, c.shape);
      const reads = r.reads.map(q => ({ ...q, floorTint: +q.floorTint.toFixed(2), colourDelta: +q.colourDelta.toFixed(2), tintDelta: +q.tintDelta.toFixed(2), lumDelta: +q.lumDelta.toFixed(1) }));
      results[c.label][label] = { clientHour: +r.hour.toFixed(2), nightMix: +env.nightMix.toFixed(3), outdoor: env.outdoor, changedAll: r.changedAll, emptyAtRead: r.emptyAtRead, shape: r.shape, reads };
      console.log(c.label, label, JSON.stringify(results[c.label][label]));
      await page.screenshot({ path: path.join(world.artifacts, `telegraph-${c.label}-${label}-${viewport.width}.png`) });
      check(!env.outdoor, `${c.label} ${label}: a dungeon is not outdoors`);
      check(env.nightMix === 0, `${c.label} ${label}: the dungeon has no night (nightMix ${env.nightMix})`);
      check(r.restored, `${c.label} ${label}: the telegraph list came back after the control read`);
      check(reads.every(q => q.pixels > 0), `${c.label} ${label}: every telegraph has pixels on screen`);
      // the colour distance is the measure for both colours (blue and red move the tint in opposite directions); the mean over the telegraphs
      const mean = reads.reduce((a, q) => a + q.colourDelta, 0) / reads.length;
      check(mean > minDist, `${c.label} ${label}: the telegraph changes its own footprint by ${mean.toFixed(2)} RGB units on average (MIN_DIST ${minDist})`);
    }
    await send({ op: 'set_time', hour: 12, freeze: false });
  }
  fs.writeFileSync(path.join(world.artifacts, `telegraph-visibility-${viewport.width}.json`), JSON.stringify(results, null, 1));
  assert.deepEqual(errors, []);
  console.log(`bossmech-telegraph-visibility-ui: ${checks} checks passed; artifacts in ${world.artifacts}`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
});
