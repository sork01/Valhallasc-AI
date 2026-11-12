process.env.REAL_SPRITES = '1';
require('./lib/touch.cjs').requireMemoryLimit();
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const w = new TestWorld();
const allKinds = ["elder_thornling", "elder_moth", "elder_barkguard", "elder_gatekeeper", "elder_matron", "elder_heart"];
const kinds = process.env.ELDER_ART_KINDS ? process.env.ELDER_ART_KINDS.split(',') : allKinds;
assert.ok(kinds.length && kinds.every(k => allKinds.includes(k)), 'Valid art selection');
const currentVersion = JSON.parse(fs.readFileSync(path.join(__dirname, '../client/release-notes.txt')))[0].version;
const frames = Object.fromEntries(allKinds.map(k => [k, [176,172,88,164]]));
const registry = path.join(__dirname, '../scripts/elder_slime_sources.txt');
const sources = fs.existsSync(registry) ? JSON.parse(fs.readFileSync(registry)) : {};
let browser, checks = 0;
const errors = [];
const failed = [];
function check(value, label) { if (process.env.SOFT_CHECKS && !value) { failed.push(label); console.log('FAIL: ' + label); return; } assert.ok(value, label); console.log(++checks + ': ' + label); }
(async () => {
  try {
    w.startLevel = 70; w.godMode = true; await w.start();
    browser = await chromium.launch({ headless: true });
    const p = await browser.newPage({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
    p.on('pageerror', e => errors.push(e.message));
    if (process.env.MUTATE_PNG) {
      await p.route(`**/assets/cathedral_${process.env.MUTATE_KIND}.png*`, r => r.fulfill({ path: process.env.MUTATE_PNG, contentType: 'image/png' }));
    }
    await p.addInitScript(version => {
      localStorage.setItem('valhallasc.whats-new.v1', version);
      window.AudioContext = window.webkitAudioContext = undefined;
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false,
        dpsMeter: false, lowGraphics: true, lowGraphicsSet: true, touchGraphicsSuggested: true }));
    }, currentVersion);
    await p.goto(w.url); await p.locator('#start').click(); await p.locator('#login-guest').click();
    await p.locator('#cls-warrior').click(); await p.locator('#name').fill('ElderArt');
    await p.locator('#go').click({ timeout: 60000 });
    await p.waitForFunction(() => Online.connected && Field.hero?.hp > 0);
    // Look up the production zone by name; zone 29.
    const zoneInfo = await p.evaluate(all => { const i = WORLD_MAP.zones.findIndex(z => z.name === 'The Elder Hollow');
      return { index: i, spawns: WORLD_MAP.zones[i].slimes.filter(s => all.includes(s.kind)).map(s => ({ kind: s.kind, x: s.x, y: s.y })) }; }, allKinds);
    const spawns = zoneInfo.spawns;
    const first = spawns.find(s => s.kind === 'elder_thornling');
    check(first && zoneInfo.index === 29, 'Elder Hollow (index 29, zone 30) spawns its enemies');
    await p.evaluate(spot => {
      Online.send({ type: 'debug', command: { op: 'teleport', zone: 30, x: spot.x-3, y: spot.y-3 } });
      Online.send({ type: 'debug', command: { op: 'set_time', hour: 12, freeze: true } });
    }, first);
    await p.waitForFunction(() => Field.cathedralSprites && Field.slimes.some(s => s.kind === 'elder_thornling'), null, { timeout: 30000 }).catch(async e => {
      console.error('Diagnostics', await p.evaluate(() => ({ zone: Field.zone, hero: [Field.hero?.x, Field.hero?.y], sprites: !!Field.cathedralSprites,
        kinds: [...new Set(Field.slimes.map(s => s.kind))], text: document.body.innerText.slice(-300) })));
      throw e;
    });
    if (process.env.SCREENSHOTS) await p.addStyleTag({ content: '#toast, #levelup-banner, #achievement-toast { visibility: hidden !important; }' });
    const presence = {};
    for (const kind of kinds.filter(k => spawns.some(s => s.kind === k))) {
      const spot = spawns.find(s => s.kind === kind);
      await p.evaluate(spot => Online.send({ type: 'debug', command: { op: 'teleport', zone: 30, x: spot.x-3, y: spot.y-3 } }), spot);
      await p.waitForFunction(kind => Field.slimes.some(s => s.kind === kind) && Field.cathedralSprites?.img[kind]?.complete, kind, { timeout: 30000 });
      await p.waitForTimeout(300);
      await p.evaluate(() => { City.close(); ZoneJourney.clear(); Field._debug.drawFrame(3); });
      await p.screenshot({ path: path.join(w.runDir, `elder-slime-${kind}-game.png`) });
      presence[kind] = await p.evaluate(kind => ({
        top: Field.slimes.find(s => s.kind === kind).d.top,
        meta: (Field.cathedralSprites).meta.tops[kind],
        source: (Field.cathedralSprites).meta.sprites[kind],
        frame: Field.frameOf(Field.cathedralSprites, kind),
      }), kind);
    }
    if (process.env.BASELINE || process.env.SCREENSHOTS) { console.log('Review screenshots: '+w.runDir); return; }
    const result = await p.evaluate(all => {
      const data = {}, metaOut = {};
      const portraits = document.createElement('canvas'); portraits.width = 6*144; portraits.height = 170;
      const pg = portraits.getContext('2d'); pg.fillStyle = '#1e1a34'; pg.fillRect(0, 0, portraits.width, portraits.height);
      let col = 0;
      const runs = (arr, from, to) => { let r = 0, prev = 0; for (let x = from; x < to; x++) { if (arr[x] && !prev) r++; prev = arr[x]; } return r; };
      for (const kind of all) {
        const src = Field.cathedralSprites, { meta, img } = src;
        metaOut[kind] = { frame: meta.frame, anchor: meta.anchor, clips: meta.clips, source: meta.sprites[kind], top: meta.tops[kind], kindFrame: meta.kindFrames?.[kind], kinds: meta.kinds.length };
        const fr = Field.frameOf(src, kind), kw = fr.w, kh = fr.h;
        const im = img[kind], c = document.createElement('canvas'); c.width = im.width; c.height = im.height;
        const g = c.getContext('2d', { willReadFrequently: true }); g.drawImage(im, 0, 0);
        const rows = [];
        let idle0 = null;
        for (const [clip, spec] of Object.entries(meta.clips)) for (let n = 0; n < spec.n; n++) {
          const pixels = g.getImageData(n*kw, spec.row*kh, kw, kh).data;
          const mask = new Uint8Array(kw*kh);
          let opaque = 0, edge = 0, white = 0, hash = 7, low = -1, top = kh, left = kw, right = -1;
          const rowCount = Array(kh).fill(0), colors = new Set();
          for (let y = 0; y < kh; y++) for (let x = 0; x < kw; x++) {
            const i = (y*kw+x)*4;
            hash = (Math.imul(hash, 31)+pixels[i]+pixels[i+1]*3+pixels[i+2]*7+pixels[i+3]) >>> 0;
            if (!pixels[i+3]) continue;
            colors.add(`${pixels[i]},${pixels[i+1]},${pixels[i+2]}`); mask[y*kw+x] = 1; rowCount[y]++; opaque++; if (y > low) low = y; if (y < top) top = y; if (x < left) left = x; if (x > right) right = x;
            if (x === 0 || x === kw-1 || y === 0 || y === kh-1) edge++;
            if (pixels[i] === 255 && pixels[i+1] === 251 && pixels[i+2] === 234) white++;
          }
          if (clip === 'idle' && n === 0) idle0 = mask;
          let diff = 0; for (let k = 0; k < mask.length; k++) if (mask[k] !== idle0[k]) diff++;
          const rowAt = y => Array.from({ length: kw }, (_, x) => mask[y*kw+x]);
          const thick = rowCount.map((cnt, y) => cnt >= 5 ? y : -1).filter(y => y >= 0);
          rows.push({ colors: colors.size, clip, n, opaque, edge, white, hash, low, top, left, right, diff,
            solid: thick.length ? thick.at(-1)-thick[0] : 0,
            groundWidth: rowCount[fr.ay], groundRuns: runs(rowAt(fr.ay), 0, kw),
            hindX: (() => { let sum = 0, c = 0; for (let y = fr.ay-5; y <= fr.ay; y++) for (let x = 0; x < fr.ax-14; x++) if (mask[y*kw+x]) { sum += x; c++; } return c ? sum/c : 0; })(),
            frontX: (() => { let sum = 0, c = 0; for (let y = fr.ay-5; y <= fr.ay; y++) for (let x = fr.ax+12; x < kw; x++) if (mask[y*kw+x]) { sum += x; c++; } return c ? sum/c : 0; })(),
            legTracks: Math.max(...[4, 5, 6, 7, 8, 9, 10, 11, 12].map(k => runs(rowAt(fr.ay-k), 0, kw))) });
        }
        const portrait = document.createElement('canvas'); portrait.width = portrait.height = 128;
        const ready = Field.drawTargetPortrait({ kind }, portrait);
        const bytes = portrait.getContext('2d').getImageData(0, 0, 128, 128).data;
        pg.drawImage(portrait, col*144+8, 0); pg.fillStyle = '#fff2c8'; pg.font = '16px sans-serif';
        pg.fillText(Field.enemyName(kind), col*144+4, 150); col++;
        data[kind] = { frame: [fr.w, fr.h, fr.ax, fr.ay], size: [im.width, im.height], rows, ready,
          portraitPixels: Array.from(bytes).filter((v, i) => i%4 === 3 && v > 0).length };
      }
      return { meta: metaOut, data, portraits: portraits.toDataURL() };
    }, kinds);
    check(kinds.every(k => result.meta[k].frame.join() === '96,96' && result.meta[k].anchor.join() === '48,90'), '96×96 fallback frame and (48,90) anchor preserved in the shared manifest');
    check(result.meta[kinds[0]].kinds === 146, 'Shared Cathedral manifest retains all 146 kinds');
    for (const kind of kinds) {
      const d = result.data[kind], [kw, kh, kax, kay] = frames[kind];
      const kf = result.meta[kind].kindFrame, m = result.meta[kind];
      check(d.frame.join() === frames[kind].join() && kf && [...kf.frame, ...kf.anchor].join() === frames[kind].join(),
        `${kind}: production frame lookup returns its declared ${kw}×${kh}, anchor (${kax},${kay})`);
      check(m.source === sources[kind], `${kind}: production loader uses its new saved PixelFlow source`);
      check(d.size.join() === `${8*kw},${5*kh}` && d.rows.length === 34 && d.rows.every(r => r.opaque > 3 && r.edge === 0),
        `${kind}: all 34 atlas frames (${8*kw}×${5*kh}) nonempty and clear of every border`);
      const expected = { idle: [6,6], walk: [10,8], attack: [12,8], hurt: [10,4], die: [8,8] };
      for (const [clip, [fps, n]] of Object.entries(expected)) {
        const spec = m.clips[clip];
        check(spec.fps === fps && spec.n === n && new Set(d.rows.filter(r => r.clip === clip).map(r => r.hash)).size >= Math.min(3, n),
          `${kind}: ${clip} preserves timing and animates distinctly`);
      }
      const att = d.rows.filter(r => r.clip === 'attack'), die = d.rows.filter(r => r.clip === 'die');
      const idle = d.rows.filter(r => r.clip === 'idle'), idle0 = idle[0];
      const idleTop = Math.min(...idle.map(r => r.top)), idleRight = Math.max(...idle.map(r => r.right));
      check(new Set(att.map(r => r.hash)).size === 8, `${kind}: all eight attack frames are distinct`);
      check(Math.max(att[4].right - idle0.right, idle0.left - att[4].left, Math.abs(att[4].top - idle0.top)) >= 7 && att[2].diff >= 300 && att[4].diff >= 300, `${kind}: wind-up and strike make substantial silhouette changes and the strike reaches out`);
      check(Math.abs(att[7].top-idle0.top) <= 4 && Math.abs(att[7].left-idle0.left) <= 4 && Math.abs(att[7].right-idle0.right) <= 4,
        `${kind}: attack recovers to its initial silhouette`);
      check(new Set(die.map(r => r.hash)).size === 8, `${kind}: all eight death frames are distinct`);
      const living = d.rows.filter(r => r.clip !== 'die');
      if (['elder_moth'].includes(kind)) {
        check(living.every(r => r.low <= kay - 12), `${kind}: flying creature hovers in mid-air above anchor row ${kay} across all living clips (lows ${[...new Set(living.map(r => r.low))]})`);
        check(die.every(r => r.low <= kay) && die.at(-1).low === kay, `${kind}: death falls from mid-air and settles on the ground row ${kay} (lows ${die.map(r => r.low)})`);
      } else {
        check(living.every(r => r.low === kay), `${kind}: every living frame rests exactly on its anchor row ${kay} (rows ${[...new Set(living.map(r => r.low))]})`);
        check(die.every(r => r.low === kay), `${kind}: every death frame rests exactly on the ground (row ${kay}), never sunk or floating`);
      }
      console.log(`   ground ${kind} idle groundRuns=${idle.map(r => r.groundRuns)} legTracks=${idle.map(r => r.legTracks)} groundWidth=${idle.map(r => r.groundWidth)}`);
      if (['elder_thornling','elder_barkguard','elder_gatekeeper'].includes(kind)) {
        check(idle.every(r => r.groundRuns >= 2), `${kind}: separate feet or hooves stay planted in idle`);
        check(d.rows.filter(r => r.clip === 'walk').every(r => r.groundRuns >= 1), `${kind}: walking keeps at least one foot on the ground`);
      }
      check(die.at(-1).diff >= 100, `${kind}: death changes the visible silhouette`);
      check(idle0.opaque > 500 && idle0.colors >= 12, `${kind}: substantial shaded silhouette with at least twelve colors (${idle0.opaque} opaque pixels)`);
      check(m.top === kay-idleTop, `${kind}: health-bar top is derived from its tallest idle pose`);
      if (presence[kind]) {
        check(presence[kind].top === m.top && presence[kind].source === sources[kind] &&
          presence[kind].frame.w === kw && presence[kind].frame.h === kh,
          `${kind}: authoritative Elder Hollow presence uses the new source, ${kw}×${kh} frame and production health-bar top`);
      }
      check(d.ready && d.portraitPixels > 80, `${kind}: production target portrait renders`);
    }
    check(new Set(kinds.map(k => result.data[k].rows.find(r => r.clip === 'die' && r.n === 7).hash)).size === kinds.length, 'Checked kinds retain distinct final death silhouettes');
    fs.writeFileSync(path.join(w.runDir, 'elder-slime-portraits.png'), Buffer.from(result.portraits.split(',')[1], 'base64'));
    await p.setViewportSize({ width: 844, height: 390 });
    await p.screenshot({ path: path.join(w.runDir, 'elder-slime-phone.png') });
    check(errors.length === 0, 'No real-art browser errors: '+errors.join('; '));
    fs.writeFileSync(path.join(w.runDir, 'elder-slime-browser-proof.json'), JSON.stringify({ checks, meta: result.meta, data: result.data, errors }, null, 2));
    if (failed.length) { console.log('FAILED CHECKS:\n' + failed.join('\n')); process.exitCode = 1; }
    console.log(`elder-slime-art: ${checks} checks; ${w.runDir}`);
  } finally { await browser?.close(); await w.stop(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
