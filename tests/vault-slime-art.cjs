process.env.REAL_SPRITES = '1';
require('./lib/touch.cjs').requireMemoryLimit();
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const w = new TestWorld();
const allKinds = ['thrall', 'archer', 'acolyte', 'gatewarden', 'choir', 'colossus', 'hollowking'];
const kinds = process.env.VAULT_ART_KINDS ? process.env.VAULT_ART_KINDS.split(',') : allKinds;
assert.ok(kinds.length && kinds.every(k => allKinds.includes(k)), 'Valid art selection');
// declared production frames: kind -> [w, h, anchorX, anchorY] (the zone-wide 96x96 frame stays in the manifest as the fallback)
const frames = { thrall: [114, 92, 43, 86], archer: [114, 88, 42, 82], acolyte: [116, 104, 37, 98], gatewarden: [124, 102, 47, 96],
  choir: [104, 96, 48, 90], colossus: [126, 114, 52, 108], hollowking: [114, 98, 39, 92] };
const sources = JSON.parse(fs.readFileSync(path.join(__dirname, '../scripts/vault_slime_sources.txt')));
let browser, checks = 0;
const errors = [];
function check(value, label) { assert.ok(value, label); console.log(++checks + ': ' + label); }
(async () => {
  try {
    w.startLevel = 25; w.godMode = true; await w.start();
    browser = await chromium.launch({ headless: true });
    const p = await browser.newPage({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
    p.on('pageerror', e => errors.push(e.message));
    // Mutation control: serve one kind's atlas replaced by a damaged copy (MUTATE_KIND + MUTATE_PNG); the checks must fail.
    if (process.env.MUTATE_PNG) await p.route(`**/assets/vault_${process.env.MUTATE_KIND}.png`, r => r.fulfill({ path: process.env.MUTATE_PNG, contentType: 'image/png' }));
    await p.addInitScript(() => {
      window.AudioContext = window.webkitAudioContext = undefined;
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false,
        dpsMeter: false, lowGraphics: true, lowGraphicsSet: true, touchGraphicsSuggested: true }));
    });
    await p.goto(w.url); await p.locator('#start').click(); await p.locator('#login-guest').click();
    await p.locator('#cls-warrior').click(); await p.locator('#name').fill('VaultArt');
    await p.locator('#go').click({ timeout: 60000 });
    await p.waitForFunction(() => Online.connected && Field.hero?.hp > 0);
    await p.evaluate(() => {
      Online.send({ type: 'debug', command: { op: 'teleport', zone: 5, x: 15, y: 111 } });
      Online.send({ type: 'debug', command: { op: 'set_time', hour: 12, freeze: true } });
    });
    await p.waitForFunction(() => Field.vaultSprites && Field.slimes.some(s => s.kind === 'thrall'), null, { timeout: 30000 });
    const result = await p.evaluate(() => {
      const src = Field.vaultSprites, { meta, img } = src;
      const data = {};
      const portraits = document.createElement('canvas'); portraits.width = 7*144; portraits.height = 170;
      const pg = portraits.getContext('2d'); pg.fillStyle = '#344b40'; pg.fillRect(0, 0, portraits.width, portraits.height);
      let col = 0;
      for (const kind of meta.kinds) {
        const fr = Field.frameOf(src, kind), kw = fr.w, kh = fr.h;       // the one production lookup of a kind's frame
        const im = img[kind], c = document.createElement('canvas'); c.width = im.width; c.height = im.height;
        const g = c.getContext('2d', { willReadFrequently: true }); g.drawImage(im, 0, 0);
        const rows = [];
        let idle0 = null;
        for (const [clip, spec] of Object.entries(meta.clips)) for (let n = 0; n < spec.n; n++) {
          const pixels = g.getImageData(n*kw, spec.row*kh, kw, kh).data;
          const mask = new Uint8Array(kw*kh);
          let opaque = 0, edge = 0, white = 0, hash = 7, low = -1, top = kh, left = kw, right = -1;
          for (let y = 0; y < kh; y++) for (let x = 0; x < kw; x++) {
            const i = (y*kw+x)*4;
            hash = (Math.imul(hash, 31)+pixels[i]+pixels[i+1]*3+pixels[i+2]*7+pixels[i+3]) >>> 0;
            if (!pixels[i+3]) continue;
            mask[y*kw+x] = 1; opaque++; if (y > low) low = y; if (y < top) top = y; if (x < left) left = x; if (x > right) right = x;
            if (x === 0 || x === kw-1 || y === 0 || y === kh-1) edge++;
            if (pixels[i] === 255 && pixels[i+1] === 251 && pixels[i+2] === 234) white++;   // colour-exact eye white #fffbea
          }
          if (clip === 'idle' && n === 0) idle0 = mask;
          let diff = 0; for (let k = 0; k < mask.length; k++) if (mask[k] !== idle0[k]) diff++;
          rows.push({ clip, n, opaque, edge, white, hash, low, top, left, right, diff });
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
    check(result.meta.kinds.join() === allKinds.join(), 'All seven production kind IDs preserved');
    check(JSON.stringify(Object.keys(result.meta.kindFrames).sort()) === JSON.stringify(Object.keys(frames).sort()), 'Every kind that needs another frame has a kindFrames entry');
    // wind-up / strike measures against the idle poses: [metric, attack frame, minimum px]; measured margins are 40-100% above these.
    //   rises: top of the art above the tallest idle pose; leans: left edge pulled back; reach: right edge beyond the widest idle pose
    const motion = {
      thrall: { wind: ['rises', 2, 6], strike: ['reach', 4, 20] },
      archer: { wind: ['leans', 2, 5], strike: ['reach', 5, 15] },
      acolyte: { wind: ['rises', 2, 8], strike: ['reach', 4, 18] },
      gatewarden: { wind: ['rises', 2, 4], strike: ['reach', 4, 20] },
      choir: { wind: ['leans', 2, 4], strike: ['reach', 5, 8] },
      colossus: { wind: ['rises', 2, 10], strike: ['reach', 4, 14] },
      hollowking: { wind: ['rises', 2, 3], strike: ['reach', 4, 20] },
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
      const idleTop = Math.min(...idle.map(r => r.top)), idleRight = Math.max(...idle.map(r => r.right)), idleLeft = Math.min(...idle.map(r => r.left));
      check(new Set(att.map(r => r.hash)).size === 8, `${kind}: all eight attack frames are distinct`);
      const m = motion[kind];
      const rises = idleTop-att[m.wind[1]].top, leans = idleLeft-att[m.wind[1]].left;
      const wind = m.wind[0] === 'rises' ? rises : leans;
      check(wind >= m.wind[2], `${kind}: wind-up frame ${m.wind[1]} ${m.wind[0]} ≥${m.wind[2]} px against idle (${wind})`);
      check(att[2].diff >= 400, `${kind}: wind-up frame 2 differs from the idle pose by ≥400 px (${att[2].diff})`);
      const reach = att[m.strike[1]].right-idleRight;
      check(reach >= m.strike[2], `${kind}: strike frame ${m.strike[1]} reaches ≥${m.strike[2]} px beyond the idle art (${reach})`);
      check(att[m.strike[1]].diff >= 150, `${kind}: strike frame ${m.strike[1]} differs from the idle pose by ≥150 px (${att[m.strike[1]].diff})`);
      const last = att[7];
      check(Math.abs(last.top-idle0.top) <= 3 && Math.abs(last.left-idle0.left) <= 3 && Math.abs(last.right-idle0.right) <= 3, `${kind}: attack recovery returns to the idle silhouette (frame 7 within 3 px of idle 0)`);
      check(new Set(die.map(r => r.hash)).size === 8, `${kind}: all eight death frames are distinct`);
      const living = d.rows.filter(r => r.clip !== 'die');
      check(living.every(r => r.low === kay), `${kind}: every living frame rests exactly on its anchor row ${kay} (rows ${[...new Set(living.map(r => r.low))]})`);
      check(die.every(r => r.low === kay), `${kind}: every death frame rests exactly on the ground (row ${kay}), never sunk or floating`);
      if (kind === 'choir') check(die[7].opaque < idle0.opaque*.5 && die[7].opaque > 60 && die[7].top > idleTop+30 && die.every((r, i) => !i || r.opaque <= die[i-1].opaque+30), `${kind}: the spirit dissipates upward and only the settled gown and diadem remain (${die[7].opaque} px)`);
      else check(die.every(r => r.opaque > idle0.opaque*.45), `${kind}: death keeps solid bones, armour or stone, with no puddle or dissolving corpse`);
      check(idle0.white > 12, `${kind}: large eye whites remain readable (${idle0.white} exact #fffbea pixels)`);
      check(result.meta.tops[kind] === kay-idleTop, `${kind}: health-bar top is derived from its tallest idle pose`);
      check(d.ready && d.portraitPixels > 80, `${kind}: production target portrait renders`);
    }
    check(new Set(kinds.map(k => result.data[k].rows.find(r => r.clip === 'die' && r.n === 7).hash)).size === kinds.length, 'Checked kinds retain distinct final corpse silhouettes');
    fs.writeFileSync(path.join(w.runDir, 'vault-slime-portraits.png'), Buffer.from(result.portraits.split(',')[1], 'base64'));
    for (const kind of kinds) {
      const spot = await p.evaluate(kind => {
        const s = Field.slimes.find(s => s.kind === kind);
        return s && { x: s.x, y: s.y, top: s.d.top };
      }, kind);
      check(spot && spot.top === result.meta.tops[kind], `${kind}: authoritative Undervault presence and production health-bar top`);
      await p.evaluate(spot => Online.send({ type: 'debug', command: { op: 'teleport', zone: 5, x: spot.x+3, y: spot.y+2 } }), spot);
      await p.waitForTimeout(400);
      await p.evaluate(() => { City.close(); ZoneJourney.clear(); Field._debug.drawFrame(3); });
      await p.screenshot({ path: path.join(w.runDir, `vault-slime-${kind}-game.png`) });
    }
    await p.setViewportSize({ width: 844, height: 390 });
    await p.screenshot({ path: path.join(w.runDir, 'vault-slime-phone.png') });
    check(errors.length === 0, 'No real-art browser errors: '+errors.join('; '));
    fs.writeFileSync(path.join(w.runDir, 'vault-slime-browser-proof.json'), JSON.stringify({ checks, meta: result.meta, data: result.data, errors }, null, 2));
    console.log(`vault-slime-art: ${checks} checks; ${w.runDir}`);
  } finally { await browser?.close(); await w.stop(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
