process.env.REAL_SPRITES = '1';
require('./lib/touch.cjs').requireMemoryLimit();
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const w = new TestWorld();
const kinds = ['crab', 'wolf', 'yeti', 'wyrm'];
// declared production frames: kind -> [w, h, anchorX, anchorY] (the zone-wide 96x96 frame stays in the manifest as the fallback)
const frames = { crab: [112, 96, 52, 90], wolf: [112, 96, 52, 90], yeti: [112, 112, 56, 106], wyrm: [144, 96, 56, 90] };
const sources = JSON.parse(fs.readFileSync(path.join(__dirname, '../scripts/rime_slime_sources.txt')));
let browser, checks = 0;
const errors = [];
function check(value, label) { assert.ok(value, label); console.log(++checks + ': ' + label); }
(async () => {
  try {
    w.startLevel = 20; w.godMode = true; await w.start();
    browser = await chromium.launch({ headless: true });
    const p = await browser.newPage({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
    p.on('pageerror', e => errors.push(e.message));
    // Mutation control: serve one kind's atlas shifted up a row (MUTATE_KIND + MUTATE_PNG); the grounding checks must fail.
    if (process.env.MUTATE_PNG) await p.route(`**/assets/rime_${process.env.MUTATE_KIND}.png`, r => r.fulfill({ path: process.env.MUTATE_PNG, contentType: 'image/png' }));
    await p.addInitScript(() => {
      window.AudioContext = window.webkitAudioContext = undefined;
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false,
        dpsMeter: false, lowGraphics: true, lowGraphicsSet: true, touchGraphicsSuggested: true }));
    });
    await p.goto(w.url); await p.locator('#start').click(); await p.locator('#login-guest').click();
    await p.locator('#cls-warrior').click(); await p.locator('#name').fill('RimeArt');
    await p.locator('#go').click({ timeout: 60000 });
    await p.waitForFunction(() => Online.connected && Field.hero?.hp > 0);
    await p.evaluate(() => {
      Online.send({ type: 'debug', command: { op: 'teleport', zone: 2, x: 50, y: 50 } });
      Online.send({ type: 'debug', command: { op: 'set_time', hour: 12, freeze: true } });
    });
    await p.waitForFunction(() => Field.rimeSprites && Field.slimes.some(s => s.kind === 'crab'), null, { timeout: 30000 });
    const result = await p.evaluate(() => {
      const src = Field.rimeSprites, { meta, img } = src;
      const data = {};
      const portraits = document.createElement('canvas'); portraits.width = 4*144; portraits.height = 170;
      const pg = portraits.getContext('2d'); pg.fillStyle = '#344b40'; pg.fillRect(0, 0, portraits.width, portraits.height);
      let col = 0;
      for (const kind of meta.kinds) {
        const fr = Field.frameOf(src, kind), kw = fr.w, kh = fr.h;       // the one production lookup of a kind's frame
        const im = img[kind], c = document.createElement('canvas'); c.width = im.width; c.height = im.height;
        const g = c.getContext('2d', { willReadFrequently: true }); g.drawImage(im, 0, 0);
        const rows = [];
        for (const [clip, spec] of Object.entries(meta.clips)) for (let n = 0; n < spec.n; n++) {
          const pixels = g.getImageData(n*kw, spec.row*kh, kw, kh).data;
          let opaque = 0, edge = 0, white = 0, hash = 7, low = -1, top = kh, left = kw, right = -1, upRight = -1;
          for (let y = 0; y < kh; y++) for (let x = 0; x < kw; x++) {
            const i = (y*kw+x)*4;
            hash = (Math.imul(hash, 31)+pixels[i]+pixels[i+1]*3+pixels[i+2]*7+pixels[i+3]) >>> 0;
            if (!pixels[i+3]) continue;
            opaque++; if (y > low) low = y; if (y < 40 && x > upRight) upRight = x; if (y < top) top = y; if (x < left) left = x; if (x > right) right = x;
            if (x === 0 || x === kw-1 || y === 0 || y === kh-1) edge++;
            if (pixels[i] === 237 && pixels[i+1] === 246 && pixels[i+2] === 247) white++;   // colour-exact eye white #edf6f7
          }
          rows.push({ clip, n, opaque, edge, white, hash, low, top, left, right, upRight });
        }
        const portrait = document.createElement('canvas'); portrait.width = portrait.height = 128;
        const ready = Field.drawTargetPortrait({ kind }, portrait);
        const bytes = portrait.getContext('2d').getImageData(0, 0, 128, 128).data;
        pg.drawImage(portrait, col*144+8, 0); pg.fillStyle = '#fff2c8'; pg.font = '16px sans-serif';
        pg.fillText(Field.enemyName(kind), col*144+4, 150); col++;
        data[kind] = { frame: [fr.w, fr.h, fr.ax, fr.ay], size: [im.width, im.height], rows, ready,
          portraitPixels: Array.from(bytes).filter((v, i) => i%4 === 3 && v > 0).length };
      }
      return { meta, data, portraits: portraits.toDataURL() };
    });
    check(result.meta.frame.join() === '96,96' && result.meta.anchor.join() === '48,90', '96×96 zone-wide frame and (48,90) anchor preserved');
    check(result.meta.kinds.join() === kinds.join(), 'All four production kind IDs preserved');
    check(JSON.stringify(Object.keys(result.meta.kindFrames).sort()) === JSON.stringify(Object.keys(frames).sort()), 'Only the kinds that need another frame have a kindFrames entry');
    // wind-up / strike measures against the idle pose: [clip frame, metric, minimum] (measured margins are 30-100% above these)
    const motion = {
      crab: { wind: ['rises', 2, 12], strike: ['reaches', 4, 8] },
      wolf: { wind: ['drops', 2, 6], strike: ['reaches', 4, 12] },
      yeti: { wind: ['rises', 2, 10], strike: ['drops', 4, 8] },
      wyrm: { wind: ['rises', 2, 2], strike: ['drops', 4, 20] },
    };
    for (const kind of kinds) {
      const d = result.data[kind], [kw, kh, kax, kay] = frames[kind];
      check(d.frame.join() === frames[kind].join(), `${kind}: production frame lookup returns its declared ${kw}×${kh}, anchor (${kax},${kay})`);
      check(result.meta.sprites[kind] === sources[kind], `${kind}: production loader uses its new saved PixelFlow source`);
      check(d.size.join() === `${8*kw},${5*kh}` && d.rows.length === 34 && d.rows.every(r => r.opaque > 3 && r.edge === 0), `${kind}: all 34 atlas frames (${8*kw}×${5*kh}) nonempty and clear of every border`);
      const expected = { idle: [6,6], walk: [10,8], attack: [12,8], hurt: [10,4], die: [8,8] };
      for (const [clip, [fps, n]] of Object.entries(expected)) {
        const spec = result.meta.clips[clip];
        check(spec.fps === fps && spec.n === n && new Set(d.rows.filter(r => r.clip === clip).map(r => r.hash)).size >= Math.min(4, n), `${kind}: ${clip} preserves timing and animates distinctly`);
      }
      const att = d.rows.filter(r => r.clip === 'attack'), die = d.rows.filter(r => r.clip === 'die');
      const idle = d.rows.filter(r => r.clip === 'idle'), idle0 = idle[0];
      const idleTop = Math.min(...idle.map(r => r.top)), idleRight = Math.max(...idle.map(r => r.right));
      check(new Set(att.map(r => r.hash)).size === 8, `${kind}: all eight attack frames are distinct`);
      const m = motion[kind];
      const rises = idleTop-att[m.wind[1]].top, drops = att[m.wind[1]].top-idleTop;
      check((m.wind[0] === 'rises' ? rises : drops) >= m.wind[2], `${kind}: wind-up frame ${m.wind[1]} ${m.wind[0]} ≥${m.wind[2]} px against idle (${m.wind[0] === 'rises' ? rises : drops})`);
      const reach = att[m.strike[1]].right-idleRight, sdrop = att[m.strike[1]].top-idleTop;
      check(m.strike[0] === 'reaches' ? reach >= m.strike[2] : sdrop >= m.strike[2], `${kind}: strike frame ${m.strike[1]} ${m.strike[0]} ≥${m.strike[2]} px (${m.strike[0] === 'reaches' ? reach : sdrop})`);
      const last = att[7];
      if (kind === 'wyrm') {   // the real wind-up: the head and neck (rows above the top coil) pull back to the left
        const idleUp = Math.min(...idle.map(r => r.upRight)), pull = idleUp-att[2].upRight;
        check(pull >= 10, `wyrm: wind-up frame 2 pulls the head back ≥10 px against idle (${pull})`);
      }
      check(Math.abs(last.top-idle0.top) <= 3 && Math.abs(last.left-idle0.left) <= 3 && Math.abs(last.right-idle0.right) <= 3, `${kind}: attack recovery returns to the idle silhouette (frame 7 within 3 px of idle 0)`);
      check(new Set(die.map(r => r.hash)).size === 8, `${kind}: all eight death frames are distinct`);
      const living = d.rows.filter(r => r.clip !== 'die');
      check(living.every(r => r.low === kay), `${kind}: every living frame rests exactly on its anchor row ${kay} (rows ${[...new Set(living.map(r => r.low))]})`);
      check(die.every(r => r.low === kay), `${kind}: every death frame rests exactly on the ground (row ${kay}), never sunk or floating`);
      check(die.every(r => r.opaque > idle0.opaque*.4), `${kind}: death keeps a solid body, with no puddle or dissolving corpse`);
      check(idle0.white > 12, `${kind}: large eye whites remain readable (${idle0.white} exact #edf6f7 pixels)`);
      check(result.meta.tops[kind] === kay-idleTop, `${kind}: health-bar top is derived from its tallest idle pose`);
      check(d.ready && d.portraitPixels > 80, `${kind}: production target portrait renders`);
    }
    check(new Set(kinds.map(k => result.data[k].rows.find(r => r.clip === 'die' && r.n === 7).hash)).size === 4, 'All four kinds retain distinct final corpse silhouettes');
    // material checks: the crab shell and the wyrm coils keep their thickness through the death sequence
    const crabDie = result.data.crab.rows.filter(r => r.clip === 'die'), wyrmIdle = result.data.wyrm.rows.find(r => r.clip === 'idle');
    check(crabDie[7].opaque > crabDie[0].opaque*.75, 'crab: the rigid shell is not squashed away in the death sequence');
    check(result.data.wyrm.rows.filter(r => r.clip === 'die')[7].right-result.data.wyrm.rows.filter(r => r.clip === 'die')[7].left > 70, 'wyrm: the coils lie sprawled across the ice (wide corpse)');
    check(wyrmIdle.top < 12, 'wyrm: idle crest stays clear of the top border');
    fs.writeFileSync(path.join(w.runDir, 'rime-slime-portraits.png'), Buffer.from(result.portraits.split(',')[1], 'base64'));
    for (const kind of kinds) {
      const spot = await p.evaluate(kind => {
        const s = Field.slimes.find(s => s.kind === kind && !s.dead);
        return s && { x: s.x, y: s.y, top:s.d.top };
      }, kind);
      check(spot&&spot.top===result.meta.tops[kind], `${kind}: authoritative Rimeveil presence and production health-bar top`);
      await p.evaluate(spot => Online.send({ type: 'debug', command: { op: 'teleport', zone: 2, x: spot.x+3, y: spot.y+2 } }), spot);
      await p.waitForTimeout(400);
      await p.evaluate(() => { City.close(); ZoneJourney.clear(); Field._debug.drawFrame(3); });
      await p.screenshot({ path: path.join(w.runDir, `rime-slime-${kind}-game.png`) });
    }
    await p.setViewportSize({ width: 844, height: 390 });
    await p.screenshot({ path: path.join(w.runDir, 'rime-slime-phone.png') });
    check(errors.length === 0, 'No real-art browser errors: '+errors.join('; '));
    fs.writeFileSync(path.join(w.runDir, 'rime-slime-browser-proof.json'), JSON.stringify({ checks, meta: result.meta, data: result.data, errors }, null, 2));
    console.log(`rime-slime-art: ${checks} checks; ${w.runDir}`);
  } finally { await browser?.close(); await w.stop(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
