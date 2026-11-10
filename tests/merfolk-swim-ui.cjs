// MERFOLK-SWIM in a real browser (Nacrehold, the merfolk's city): `City.drawNpc` renders each merfolk from its saved PixelFlow frames with the swim
// treatment (npc-art.js): the figure floats about 25 px above the floor with the shadow left on it, leans along its heading (mirrored the other way
// for the other direction), waves its tail in an S while swimming, lets bubbles rise while moving, and shows none of the motion (only the lift and
// lean) under reduced motion; the nameplate sits 25 px higher; the dialogue portrait is lifted back so it frames the same; everybody else on the
// same street is unchanged. Real pixels of an offscreen canvas, drawn by the page's own `City.drawNpc`.
// Needs the bounded runner and a `--profile test` server binary. MUTATE=lift|lean|wave|bubbles|style serves an npc-art.js without that part and must fail.
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-merfolk-swim', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`); return result.structuredContent;
}
const errors = [];
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0', ...(process.env.VALHALLA_BINARY ? { VALHALLA_BINARY: process.env.VALHALLA_BINARY } : {}) } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true, args: ['--disable-gpu'] });
  const page = await browser.newPage({ viewport: { width: 960, height: 600 }, reducedMotion: 'reduce' });
  page.on('pageerror', e => errors.push(e.message));
  const mutations = { lift: ['const LIFT = 25', 'const LIFT = 0'], lean: ['LEAN = .5', 'LEAN = 0'], wave: ['amp: [6, 2.2]', 'amp: [0, 0]'], style: ["new Set(['merfolk'])", 'new Set([])'], bubbles: ['if (sw?.moving && !sw.still && !portrait)', 'if (false)'] };
  if (process.env.MUTATE) {
    const [from, to] = mutations[process.env.MUTATE] || mutations.lift, src = fs.readFileSync(path.join(root, 'client/npc-art.js'), 'utf8');
    assert.ok(src.includes(from), 'the mutation applies');
    await page.route('**/npc-art.js*', route => route.fulfill({ contentType: 'text/javascript', body: src.replace(from, to) }));
  }
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('Watcher'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.hero.x, null, { timeout: 60000 });
  await page.evaluate(() => Online.send({ type: 'debug', ref: 1, command: { op: 'teleport', zone: 9, x: 128, y: 217 } }));
  await page.waitForFunction(() => Field.zone === 9 && City.npcs.length > 5 && NpcArt.readyFor(City.npcs), null, { timeout: 30000 });
  await page.waitForTimeout(1500);

  // Offscreen renders of one person with the page's own drawNpc. The anchor is (100, 220) on a 200 x 260 canvas.
  // Nacrehold has only merfolk, so the comparison person is a stand-in built on an ordinary design's saved art (the baker's).
  const lab = await page.evaluate(async () => {
    const folk = City.npcs, merfolk = folk.filter(n => n.look?.species === 'merfolk' && NpcArt.frame(n, 0));
    const ids = Object.entries(NpcArt.manifest.npcs).filter(([, a]) => a.identity.species !== 'merfolk').map(([id]) => id);
    const id = ids.includes('baker') ? 'baker' : ids[0], base = merfolk[0];
    window.__plain = { ...base, id, look: { ...base.look, species: 'human', scale: 1 }, moving: false, fx: 1, fy: 0, route: null };
    for (let i = 0; i < 100 && !NpcArt.readyFor([window.__plain]); i++) { NpcArt.frame(window.__plain, 0); await new Promise(r => setTimeout(r, 100)); }
    return { merfolk: merfolk.length, other: NpcArt.frame(window.__plain, 0) ? id : null, first: merfolk[0]?.id };
  });
  const styles = await page.evaluate(([a, b]) => ({ merfolk: NpcArt.styleOf(City.npcs.find(x => x.id === a)), plain: NpcArt.styleOf(window.__plain) }), [lab.first, lab.other]);
  check(styles.merfolk === 'player', `The merfolk are drawn from the player-style atlases (${styles.merfolk})`);
  check(styles.plain === 'saved', `Everybody else keeps the saved art (${styles.plain})`);
  check(lab.merfolk >= 10, `Nacrehold shows many sprite-drawn merfolk (${lab.merfolk})`);
  check(lab.other, 'And a non-merfolk person with art to compare against');

  // Plate-free renders (see raw); the alpha plane is returned whole.
  const raw = (id, opts) => page.evaluate(([id, o]) => {
    const src = [...City.npcs, window.__plain].find(x => x.id === id);
    // A copy far from the hero with no work or wares: no nameplate over the figure (the plate would sit in the measured rows).
    const n = { ...src, x: -999, y: -999, key: false, offers: [], buys: null, moving: !!o.moving, fx: o.fx ?? 1, fy: o.fy ?? 0 };
    const c = document.createElement('canvas'); c.width = 200; c.height = 260; const g = c.getContext('2d', { willReadFrequently: true });
    City.drawNpc(g, n, 100, 220, o.t ?? 0.37, false, !!o.portrait);
    const d = g.getImageData(0, 0, 200, 260).data, a = new Array(200 * 260);
    for (let i = 0; i < a.length; i++) a[i] = d[i * 4 + 3];
    return a;
  }, [id, opts]);
  const SPRITE = 0;
  const measure = a => {
    let minY = 999, maxY = -1; const rows = [];
    for (let y = 0; y < 260; y++) {
      let k = 0, sx = 0; if (y >= SPRITE) for (let x = 0; x < 200; x++) if (a[y * 200 + x] >= 200) { k++; sx += x; }
      rows.push(k ? sx / k : null); if (k) { minY = Math.min(minY, y); maxY = Math.max(maxY, y); }
    }
    const head = rows.slice(minY, minY + 30).filter(v => v !== null);
    return { minY, maxY, rows, headX: head.reduce((p, q) => p + q, 0) / head.length };
  };
  // Pixels in the plate band (rows 24..82, where bubbles climb past the plate-free sides) that differ between two alpha planes.
  const bandDiff = (a, b) => { let k = 0; for (let y = 24; y < 130; y++) for (let x = 0; x < 200; x++) if (Math.abs(a[y * 200 + x] - b[y * 200 + x]) > 20) k++; return k; };
  const render = async (id, opts) => measure(await raw(id, opts));
  const key = render;

  // --- floating: the merfolk's lowest opaque pixel is well above the anchor (the shadow is translucent and does not count); others touch it ---
  const idle = await key(lab.first, { t: .37 }), plain = await key(lab.other, { t: .37 });
  check(plain.maxY >= 220 - 4, `A person who does not swim stands on the anchor row (lowest opaque row ${plain.maxY} of 220)`);
  check(idle.maxY <= 220 - 20, `A merfolk floats at least 20 px above it (lowest opaque row ${idle.maxY})`);
  check(idle.maxY >= 220 - 32, `But not more than about 32 px (${idle.maxY})`);

  // --- the shadow stays on the floor: translucent pixels at the anchor, none lifted ---
  const shadow = await page.evaluate(id => {
    const n = City.npcs.find(x => x.id === id), c = document.createElement('canvas'); c.width = 200; c.height = 260;
    const g = c.getContext('2d', { willReadFrequently: true }); City.drawNpc(g, n, 100, 220, .37, false, false);
    const px = g.getImageData(100 - 10, 220 - 3, 20, 8).data; let any = 0; for (let i = 3; i < px.length; i += 4) if (px[i] > 20) any++; return any;
  }, lab.first);
  check(shadow > 20, `The shadow is still drawn on the floor (${shadow} pixels)`);

  // --- the plate and the portrait ---
  const tops = await page.evaluate(([a, b]) => {
    const m = City.npcs.find(x => x.id === a), who = NpcArt.manifest.npcs[m.id], man = NpcArt.fresh, t = man.tops[who.art], s = man.scale;
    return { top: NpcArt.top(m), plain: (t * s + 3) * (m.look?.scale || 1), scale: m.look?.scale || 1, other: NpcArt.top(window.__plain) };
  }, [lab.first, lab.other]);
  check(Math.abs(tops.top - tops.plain - 25 * tops.scale) < 1e-6, `The nameplate sits 25 px higher (${tops.top.toFixed(1)} against ${tops.plain.toFixed(1)})`);
  const portrait = await key(lab.first, { t: 0, portrait: true });
  check(portrait.maxY <= 220 - 20, 'The dialogue portrait is drawn lifted by the same amount (it is placed from the nameplate height)');

  // --- leaning: heading right leans the head right, heading left the other way, standing still leans nowhere ---
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const still = await key(lab.first, { t: .37 });
  const right = await key(lab.first, { moving: true, fx: 1, fy: 0 }), left = await key(lab.first, { moving: true, fx: -1, fy: 0 });
  check(right.headX > still.headX + 8, `Swimming right, the head is carried to the right (${still.headX.toFixed(1)} -> ${right.headX.toFixed(1)})`);
  check(left.headX < still.headX - 8, `Swimming left, to the left (${left.headX.toFixed(1)})`);

  // --- tail wave and bubbles: with reduced motion the frame holds still between times, otherwise it moves ---
  const rows = r => r.rows;
  const calmA = await key(lab.first, { moving: true, t: .2 }), calmB = await key(lab.first, { moving: true, t: .55 });
  const tailRows = (a, b) => { let diff = 0; for (let y = 150; y <= 200; y++) if (rows(a)[y] !== null && rows(b)[y] !== null) diff += Math.abs(rows(a)[y] - rows(b)[y]); return diff; };
  // (Both frames of a walk cycle also change the sprite step, so compare the same step: times a whole second apart land on the same frame.)
  const calmC = await key(lab.first, { moving: true, t: .2 + 3 }), calmD = await key(lab.first, { moving: true, t: .2 });
  check(tailRows(calmC, calmD) < 1 && calmC.minY === calmD.minY, 'Under reduced motion the same walk frame is drawn identically at any time (no bob, no wave)');
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  // The wave shears the tail sideways, so the tail's centre drifts relative to the body's: measure that offset on the same walk frame (a whole
  // 0.8 s apart) at four times. The bob only moves the figure up and down, so it cannot fake a sideways range.
  const offsets = [];
  for (const t of [.2, 1.0, 1.8, 2.6]) {
    const m = await key(lab.first, { moving: true, t }), avg = (from, to) => { const v = m.rows.slice(from, to).filter(x => x !== null); return v.reduce((p, q) => p + q, 0) / v.length; };
    offsets.push(avg(m.maxY - 12, m.maxY + 1) - avg(m.minY + 40, m.minY + 70));
  }
  const range = Math.max(...offsets) - Math.min(...offsets);
  check(range > .8, `Without it the tail is waved: its sideways offset from the body swings through ${range.toFixed(1)} px`);
  const waveA = await key(lab.first, { moving: true, t: .2 }), waveB = await key(lab.first, { moving: true, t: .2 + 3 });
  check(waveA.minY !== waveB.minY || waveA.headX !== waveB.headX, 'And the figure drifts up and down');
  // Bubbles: the same moving frame with and without them, at a time when the bob is exactly zero (so only the wave and the bubbles differ),
  // compared above the tail (rows before the tail starts), where only the bubbles can differ.
  const zeroBob = await page.evaluate(id => { const phase = [...id].reduce((q, ch) => q + ch.charCodeAt(0), 0) % 628 / 100; return (Math.PI * 4 - phase) / 1.7; }, lab.first);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const noBubbles = await raw(lab.first, { moving: true, t: zeroBob });
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  const withBubbles = await raw(lab.first, { moving: true, t: zeroBob });
  const bubbleDiff = bandDiff(noBubbles, withBubbles);
  check(bubbleDiff > 8, `Bubbles rise beside the head of a swimming merfolk (${bubbleDiff} pixels differ above the tail)`);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const standCalm = await raw(lab.first, { t: zeroBob });
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  const standingBubbles = bandDiff(standCalm, await raw(lab.first, { t: zeroBob }));
  check(standingBubbles <= 0, `A standing merfolk lets none rise (${standingBubbles})`);
  const idleA = await key(lab.first, { t: .2 }), idleB = await key(lab.first, { t: .2 + 3 });
  check(tailRows(idleA, idleB) >= 0 && idleA.minY !== idleB.minY, 'A standing merfolk still bobs in place');

  // --- everybody else is unchanged: the same render is identical with and without time-based swim motion ---
  const p1 = await key(lab.other, { moving: true, t: .2 }), p2 = await key(lab.other, { moving: true, t: .2 + 3 });
  check(p1.maxY === p2.maxY && p1.minY === p2.minY, 'A non-merfolk keeps the same height at any time while walking');

  assert.deepEqual(errors, []);
  console.log(`merfolk-swim-ui: ${checks} checks passed`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
});
