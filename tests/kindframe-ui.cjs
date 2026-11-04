// KINDFRAME-CHECK: per-kind enemy frame sizes (docs/kind-frames.md). Bounded: scripts/test-touch-bounded.sh tests/kindframe-ui.cjs
// A scratch Crags manifest holds kinds at 64x64, 96x96, 128x112 and the 192x192 maximum, plus a 193 px entry the client must refuse.
// MUTATE=hitbox|draw|portrait|shadow serves field.js with that one reader reverted to the zone-wide frame: the run must fail.
process.env.REAL_SPRITES = '1';
require('./lib/touch.cjs').requireMemoryLimit();
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const root = path.resolve(__dirname, '..');
const w = new TestWorld();
let browser, checks = 0;
const errors = [], warnings = [];
const check = (value, label) => { assert.ok(value, label); console.log(++checks + ': ' + label); };
// kind -> frame, anchor and the solid body rectangle drawn in every cell of its scratch atlas
const SPEC = {
  wisp:       { frame: [64, 64],   anchor: [32, 58],   rgb: [250, 40, 200] },
  spider:     null,                                                              // zone-wide 96x96 / (48,90)
  wraith:     { frame: [128, 112], anchor: [64, 104],  rgb: [40, 220, 250] },
  golem:      { frame: [192, 192], anchor: [96, 186],  rgb: [250, 220, 40] },
  cinderlord: { frame: [193, 96],  anchor: [96, 90],   rgb: [40, 250, 80] },     // 193 px: refused, falls back to the zone-wide frame
};
const ZONE = { frame: [96, 96], anchor: [48, 90] };
const body = (f, a) => { const bx0 = Math.round(f[0] * .15), by0 = Math.round(f[1] * .12); return { bx0, bx1: f[0] - bx0, by0, by1: a[1] + 1 }; };
const LIVE = JSON.parse(fs.readFileSync(path.join(root, 'client/assets/crags.txt'), 'utf8'));
const COUNTS = Object.values(LIVE.clips).map(c => c.n);                          // 6, 8, 8, 4, 8 = 34 frames

(async () => {
  try {
    // ---- backward compatibility, part 1: no live manifest or atlas changed, none carries kindFrames
    const manifests = fs.readdirSync(path.join(root, 'client/assets')).filter(f => f.endsWith('.txt')).map(f => [f, (() => { try { return JSON.parse(fs.readFileSync(path.join(root, 'client/assets', f), 'utf8')); } catch (_) { return null; } })()])
      .filter(([, d]) => d && typeof d === 'object' && d.kinds && d.clips && d.frame && d.anchor);
    check(manifests.length >= 25, `${manifests.length} live enemy manifests found (floor 25)`);
    check(manifests.every(([, d]) => !('kindFrames' in d)), 'no live manifest carries kindFrames: every live kind keeps its zone-wide frame');
    const dirty = execFileSync('git', ['status', '--porcelain', '--', 'client/assets'], { cwd: root, encoding: 'utf8' }).trim();
    check(dirty === '', 'client/assets (every live manifest and atlas) is byte-identical to HEAD' + (dirty ? ': ' + dirty : ''));

    // ---- scratch assets: one atlas per kind at its own size, drawn in a throwaway page
    browser = await chromium.launch({ headless: true });
    const maker = await browser.newPage();
    const atlases = await maker.evaluate(({ spec, zone, counts }) => {
      const out = {};
      for (const [kind, s] of Object.entries(spec)) {
        const f = s ? s.frame : zone.frame, a = s ? s.anchor : zone.anchor, rgb = s ? s.rgb : [250, 120, 40];
        const bx0 = Math.round(f[0] * .15), by0 = Math.round(f[1] * .12), c = document.createElement('canvas'); c.width = 8 * f[0]; c.height = 5 * f[1];
        const g = c.getContext('2d'); g.fillStyle = `rgb(${rgb})`;
        counts.forEach((n, row) => { for (let i = 0; i < n; i++) g.fillRect(i * f[0] + bx0, row * f[1] + by0, f[0] - 2 * bx0, a[1] + 1 - by0); });
        out[kind] = c.toDataURL('image/png').split(',')[1];
      }
      return out;
    }, { spec: SPEC, zone: ZONE, counts: COUNTS });
    await maker.close();
    const scratch = JSON.parse(JSON.stringify(LIVE));
    scratch.kindFrames = {};
    for (const [kind, s] of Object.entries(SPEC)) {
      const f = s ? s.frame : ZONE.frame, a = s ? s.anchor : ZONE.anchor;
      if (s) scratch.kindFrames[kind] = { frame: s.frame, anchor: s.anchor };
      scratch.tops[kind] = a[1] - body(f, a).by0;
    }

    w.startLevel = 20; w.godMode = true; await w.start();
    const setup = async (page, mutate, name) => {
      page.on('pageerror', e => errors.push(e.message)); page.on('console', m => { if (m.type() === 'warning') warnings.push(m.text()); });
      await page.addInitScript(() => { window.AudioContext = window.webkitAudioContext = undefined; localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, dpsMeter: false, lowGraphics: true, lowGraphicsSet: true, touchGraphicsSuggested: true })); });
      if (mutate) await page.route(/\/field\.js(\?.*)?$/, async r => {
        const text = await (await r.fetch()).text();
        const edits = {
          hitbox: ['const { w: fw, h: fh, ax, ay } = frameOf(src, s.kind), row =', 'const [fw, fh] = src.meta.frame, [ax, ay] = src.meta.anchor, row ='],
          draw: ['{ w: fw, h: fh, ax, ay } = frameOf(src, s.kind), [clip, n] = slimeFrame', '{ w: fw, h: fh, ax, ay } = { w: m.frame[0], h: m.frame[1], ax: m.anchor[0], ay: m.anchor[1] }, [clip, n] = slimeFrame'],
          portrait: ['{ w: fw, h: fh, ax, ay } = frameOf(src, target.kind);', '{ w: fw, h: fh, ax, ay } = { w: src.meta.frame[0], h: src.meta.frame[1], ax: src.meta.anchor[0], ay: src.meta.anchor[1] };'],
          shadow: ['return src ? frameOf(src, s.kind).shadow : 1;', 'return 1;'],
        }[mutate];
        assert.ok(edits && text.includes(edits[0]), 'mutation target missing: ' + mutate);
        await r.fulfill({ body: text.replace(edits[0], edits[1]), contentType: 'application/javascript' });
      });
      await page.goto(w.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
      await page.locator('#cls-warrior').click(); await page.locator('#name').fill(name);
      await page.locator('#go').click({ timeout: 60000 });
      await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0);
    };

    // ---- backward compatibility, part 2: real unmodified art in two live zones renders pixel-identically to the old formula
    const live = await browser.newPage({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
    await setup(live, null, 'KindLive');
    await live.waitForFunction(() => Field.slimes.some(s => !s.dead && Field._debug.enemySource(s)), null, { timeout: 30000 });
    const exhaustive = await live.evaluate(async list => {      // frameOf for EVERY kind of EVERY live manifest equals the zone-wide frame
      let kinds = 0, bad = [];
      for (const [name, meta] of list) for (const kind of meta.kinds) {
        const f = Field.frameOf({ meta, img: {} }, kind); kinds++;
        if (f.w !== meta.frame[0] || f.h !== meta.frame[1] || f.ax !== meta.anchor[0] || f.ay !== meta.anchor[1] || f.own || f.shadow !== 1) bad.push(name + ':' + kind);
      }
      return { kinds, bad };
    }, manifests);
    check(exhaustive.kinds >= 300 && exhaustive.bad.length === 0, `frameOf equals the zone-wide frame, own=false, shadow 1 for all ${exhaustive.kinds} kinds of all ${manifests.length} live manifests` + (exhaustive.bad.length ? ': ' + exhaustive.bad.slice(0, 5) : ''));
    const compat = await live.evaluate(() => {
      const results = [], seen = new Set();
      for (const actor of Field.slimes) {
        const src = Field._debug.enemySource(actor);
        if (!src || seen.has(src.meta)) continue;
        seen.add(src.meta);
        const [fw, fh] = src.meta.frame, [ax, ay] = src.meta.anchor, K = 2.1 * actor.d.scale;
        for (const [state, clip, n] of [['idle', 'idle', 0], ['lunge', 'attack', 4]]) {
          const s = { ...actor, dead: false, dir: 1, hurtT: 0, state, st: .15, recT: 0, hop: 0, hopV: 0, landT: 0, blink: 0, seed: 0 };
          const mk = () => { const c = document.createElement('canvas'); c.width = 700; c.height = 700; return c; };
          const a = mk(), b = mk(), ga = a.getContext('2d'), gb = b.getContext('2d');
          ga.save(); ga.translate(350, 520); Field._debug.drawSlimeSprite(ga, s, 0); ga.restore();
          gb.save(); gb.translate(350, 520); gb.imageSmoothingEnabled = false; gb.scale(K, K);      // the pre-change formula, written out
          gb.drawImage(src.img[actor.kind], n * fw, src.meta.clips[clip].row * fh, fw, fh, -ax, -ay, fw, fh); gb.restore();
          const da = ga.getImageData(0, 0, 700, 700).data, db = gb.getImageData(0, 0, 700, 700).data;
          let diff = 0, opaque = 0; for (let i = 0; i < da.length; i++) { if (da[i] !== db[i]) diff++; if (i % 4 === 3 && da[i]) opaque++; }
          results.push({ kind: actor.kind, state, diff, opaque, frame: [fw, fh] });
        }
      }
      return results;
    });
    check(compat.length >= 4 && compat.every(r => r.diff === 0 && r.opaque > 100), `pixel-identical to the old formula for ${compat.length / 2} live zone sources (${[...new Set(compat.map(r => r.kind + ' ' + r.frame.join('x')))].join(', ')}), idle and attack frames`);
    await live.evaluate(() => { Online.send({ type: 'debug', command: { op: 'teleport', zone: 1, x: 50, y: 50 } }); });
    await live.waitForFunction(() => Field.slimes.some(s => s.kind === 'wisp') && Field._debug.enemySource(Field.slimes.find(s => s.kind === 'wisp')), null, { timeout: 30000 });
    const crags = await live.evaluate(() => {
      const actor = Field.slimes.find(s => s.kind === 'wisp'), src = Field._debug.enemySource(actor), [fw, fh] = src.meta.frame, [ax, ay] = src.meta.anchor, K = 2.1 * actor.d.scale;
      const s = { ...actor, dead: false, dir: 1, hurtT: 0, state: 'idle', st: 0, recT: 0, hop: 0, hopV: 0, landT: 0, blink: 0, seed: 0 };
      const mk = () => { const c = document.createElement('canvas'); c.width = 700; c.height = 700; return c; };
      const a = mk(), b = mk(), ga = a.getContext('2d'), gb = b.getContext('2d');
      ga.save(); ga.translate(350, 520); Field._debug.drawSlimeSprite(ga, s, 0); ga.restore();
      gb.save(); gb.translate(350, 520); gb.imageSmoothingEnabled = false; gb.scale(K, K); gb.drawImage(src.img.wisp, 0, 0, fw, fh, -ax, -ay, fw, fh); gb.restore();
      const da = ga.getImageData(0, 0, 700, 700).data, db = gb.getImageData(0, 0, 700, 700).data; let diff = 0, opaque = 0;
      for (let i = 0; i < da.length; i++) { if (da[i] !== db[i]) diff++; if (i % 4 === 3 && da[i]) opaque++; }
      return { diff, opaque };
    });
    check(crags.diff === 0 && crags.opaque > 100, 'pixel-identical to the old formula for the real Crags wisp (96x96)');
    // borrowed art: a kind with artFrom draws the borrowed atlas, so it must take the borrowed kind's frame (fake source, pure lookup)
    const borrowed = JSON.parse(fs.readFileSync(path.join(root, 'world/empty-seat-enemies.txt'), 'utf8')).filter(e => e.artFrom === 'cf_eldmarr').map(e => e.kind);
    check(borrowed.length >= 1, `${borrowed.length} Empty Seat kinds borrow cf_eldmarr art`);
    const alias = await live.evaluate(kind => {
      const meta = { frame: [96, 96], anchor: [48, 90], kinds: [], clips: {}, kindFrames: { cf_eldmarr: { frame: [192, 192], anchor: [96, 186] } } };
      const f = Field.frameOf({ meta, img: {} }, kind), z = Field.frameOf({ meta, img: {} }, 'cf_brute');
      return { f: [f.w, f.h, f.ax, f.ay, f.own, f.shadow], z: [z.w, z.h, z.own] };
    }, borrowed[0]);
    check(alias.f.join() === '192,192,96,186,true,2' && alias.z.join() === '96,96,false', `${borrowed[0]} (artFrom cf_eldmarr) takes the 192 px frame of the kind it borrows; an unrelated kind keeps 96`);
    await live.close();

    // ---- the scratch manifest through the production Crags loader
    const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
    await page.route('**/assets/crags.txt', r => r.fulfill({ body: JSON.stringify(scratch), contentType: 'text/plain' }));
    for (const [kind, data] of Object.entries(atlases)) await page.route(`**/assets/crags_${kind}.png`, r => r.fulfill({ body: Buffer.from(data, 'base64'), contentType: 'image/png' }));
    await setup(page, process.env.MUTATE || null, 'KindScratch');
    await page.evaluate(() => { Online.send({ type: 'debug', command: { op: 'teleport', zone: 1, x: 50, y: 50 } }); });
    await page.waitForFunction(() => Field.cragSprites && ['wisp', 'spider', 'wraith', 'golem', 'cinderlord'].every(k => Field.slimes.some(s => s.kind === k)), null, { timeout: 30000 });
    const kinds = Object.keys(SPEC);
    const R = await page.evaluate(({ kinds, spec, zone }) => {
      const out = {};
      for (const kind of kinds) {
        const src = Field.cragSprites, actor = Field.slimes.find(s => s.kind === kind), img = src.img[kind], F = Field.frameOf(src, kind);
        const e = { frameOf: F, atlas: [img.naturalWidth, img.naturalHeight], top: actor.d.top, shadow: Field._debug.enemyShadowK(actor), cull: Field._debug.enemyCullMargin(actor), scale: actor.d.scale };
        // 34 non-empty frames at this kind's own cell size
        const c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = img.naturalHeight; const g = c.getContext('2d', { willReadFrequently: true }); g.drawImage(img, 0, 0);
        let cells = 0;
        Object.values(src.meta.clips).forEach(clip => { for (let n = 0; n < clip.n; n++) if (g.getImageData(n * F.w, clip.row * F.h, F.w, F.h).data.some((v, i) => i % 4 === 3 && v)) cells++; });
        e.cells = cells;
        e.hitbox = { ...Field._debug.enemyHitbox({ kind, d: actor.d }) };
        // draw: the real drawSlimeSprite at the actor's scale; opaque bounding box in screen px relative to the anchor point
        const K = 2.1 * actor.d.scale, cv = document.createElement('canvas'); cv.width = cv.height = 1400; const dg = cv.getContext('2d', { willReadFrequently: true });
        const s = { ...actor, dead: false, dir: 1, hurtT: 0, state: 'idle', st: 0, recT: 0, hop: 0, hopV: 0, landT: 0, blink: 0, seed: 0 };
        dg.save(); dg.translate(700, 1000); Field._debug.drawSlimeSprite(dg, s, 0); dg.restore();
        const d = dg.getImageData(0, 0, 1400, 1400).data; let x0 = 1e9, y0 = 1e9, x1 = -1, y1 = -1;
        for (let y = 0; y < 1400; y++) for (let x = 0; x < 1400; x++) if (d[(y * 1400 + x) * 4 + 3]) { x0 = Math.min(x0, x); x1 = Math.max(x1, x + 1); y0 = Math.min(y0, y); y1 = Math.max(y1, y + 1); }
        e.draw = { x0: x0 - 700, x1: x1 - 700, y0: y0 - 1000, y1: y1 - 1000, K };
        // portrait
        const pc = document.createElement('canvas'); pc.width = pc.height = 96; e.ready = Field.drawTargetPortrait({ kind }, pc);
        const pd = pc.getContext('2d').getImageData(0, 0, 96, 96).data; let px0 = 96, py0 = 96, px1 = -1, py1 = -1;
        for (let y = 0; y < 96; y++) for (let x = 0; x < 96; x++) if (pd[(y * 96 + x) * 4 + 3]) { px0 = Math.min(px0, x); px1 = Math.max(px1, x + 1); py0 = Math.min(py0, y); py1 = Math.max(py1, y + 1); }
        e.portrait = { x0: px0, x1: px1, y0: py0, y1: py1 };
        out[kind] = e;
      }
      // a real frame with the large sprites on screen must not throw
      Field._debug.drawFrame(3);
      return out;
    }, { kinds, spec: SPEC, zone: ZONE });
    for (const kind of kinds) {
      const r = R[kind], s = SPEC[kind], refused = kind === 'cinderlord';
      const f = s && !refused ? s.frame : ZONE.frame, a = s && !refused ? s.anchor : ZONE.anchor, B = body(f, a), own = !!s && !refused;
      check(r.frameOf.w === f[0] && r.frameOf.h === f[1] && r.frameOf.ax === a[0] && r.frameOf.ay === a[1] && r.frameOf.own === own, `${kind}: frameOf ${f.join('x')} anchor ${a.join(',')}${refused ? ' (193 px entry refused, zone-wide frame used)' : ''}`);
      if (refused) { check(warnings.some(m => m.includes('kindFrames rejected') && m.includes('cinderlord')), 'cinderlord: the 193 px entry logs a rejection warning'); continue; }
      check(r.atlas[0] === 8 * f[0] && r.atlas[1] === 5 * f[1], `${kind}: atlas is 8x5 cells of ${f.join('x')} (${r.atlas.join('x')})`);
      check(r.cells === 34, `${kind}: 34 non-empty frames at its own cell size (${r.cells})`);
      check(r.hitbox.x0 === B.bx0 - a[0] && r.hitbox.x1 === B.bx1 - a[0] && r.hitbox.y0 === B.by0 - a[1] && r.hitbox.y1 === B.by1 - a[1], `${kind}: click hitbox ${JSON.stringify(r.hitbox)} is the art relative to its own anchor`);
      const K = r.draw.K, near = (v, e) => Math.abs(v - e) <= 1.01;
      check(near(r.draw.x0, (B.bx0 - a[0]) * K) && near(r.draw.x1, (B.bx1 - a[0]) * K) && near(r.draw.y0, (B.by0 - a[1]) * K) && near(r.draw.y1, (B.by1 - a[1]) * K), `${kind}: drawn art spans x ${r.draw.x0}..${r.draw.x1}, y ${r.draw.y0}..${r.draw.y1} (feet land on the anchor, same pixel scale K=${K.toFixed(2)})`);
      check(r.draw.y1 <= Math.ceil(K) + 1 && r.draw.y1 >= Math.floor(K) - 1, `${kind}: feet row sits on the ground point`);
      check(r.top === a[1] - B.by0, `${kind}: health-bar top ${r.top} derives from its own anchor`);
      check(Math.abs(r.shadow - f[0] / 96) < 1e-9, `${kind}: shadow factor ${r.shadow.toFixed(3)} follows the frame width`);
      check(r.cull === (own ? Math.max(100, Math.ceil(f[1] * 2.1 * r.scale)) : 100), `${kind}: cull margin ${r.cull} covers the whole sprite`);
      const bw = B.bx1 - B.bx0, bh = B.by1 - B.by0, sc = Math.min(78 / bw, 78 / bh), pw = r.portrait.x1 - r.portrait.x0, ph = r.portrait.y1 - r.portrait.y0;
      check(r.ready && Math.abs(pw - bw * sc) <= 2 && Math.abs(ph - bh * sc) <= 2, `${kind}: portrait shows the whole art (${pw}x${ph}, expected ${(bw * sc).toFixed(1)}x${(bh * sc).toFixed(1)}), nothing clipped`);
      check(Math.abs((r.portrait.x0 + r.portrait.x1) / 2 - 48) <= 2 && Math.abs((r.portrait.y0 + r.portrait.y1) / 2 - 48) <= 2, `${kind}: portrait is centred`);
    }
    check((R.golem.draw.x1 - R.golem.draw.x0) / R.golem.draw.K > 1.5 * (R.spider.draw.x1 - R.spider.draw.x0) / R.spider.draw.K, '192 px kind is drawn larger than the 96 px kind at the same art pixel scale');
    check(R.golem.hitbox.x1 - R.golem.hitbox.x0 > R.wisp.hitbox.x1 - R.wisp.hitbox.x0, 'hitbox of the 192 px kind is larger than the 64 px kind');
    check(errors.length === 0, 'no page errors: ' + errors.join('; '));
    await page.screenshot({ path: path.join(w.runDir, 'kindframe-game.png') });
    console.log(`kindframe-ui: ${checks} checks; ${w.runDir}`);
  } finally { await browser?.close(); await w.stop(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
