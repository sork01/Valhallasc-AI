process.env.REAL_SPRITES = '1';
require('./lib/touch.cjs').requireMemoryLimit();
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const w = new TestWorld();
const allKinds = ['draugr', 'angler', 'moray', 'siren', 'shellback', 'kraken', 'hvitserk', 'ghostmaw'];
const kinds = process.env.DEEP_ART_KINDS ? process.env.DEEP_ART_KINDS.split(',') : allKinds;
assert.ok(kinds.length && kinds.every(k => allKinds.includes(k)), 'Valid art selection');
const currentVersion = JSON.parse(fs.readFileSync(path.join(__dirname, '../client/release-notes.txt')))[0].version;
const sources = JSON.parse(fs.readFileSync(path.join(__dirname, '../scripts/deep_slime_sources.txt')));
let browser, checks = 0;
const errors = [];
function check(value, label) { assert.ok(value, label); console.log(++checks + ': ' + label); }
(async () => {
  try {
    w.startLevel = 38; w.godMode = true; await w.start();
    browser = await chromium.launch({ headless: true });
    const p = await browser.newPage({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
    p.on('pageerror', e => errors.push(e.message));
    await p.addInitScript(version => {
      localStorage.setItem('valhallasc.whats-new.v1', version);
      window.AudioContext = window.webkitAudioContext = undefined;
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false,
        dpsMeter: false, lowGraphics: true, lowGraphicsSet: true, touchGraphicsSuggested: true }));
    }, currentVersion);
    if (process.env.DEEP_MUTATED_ATLAS) {
      // Mutation control: serve a shellback atlas whose feet float; the grounding assertion must reject it.
      await p.route('**/assets/deep_shellback.png', route => route.fulfill({
        path: process.env.DEEP_MUTATED_ATLAS, contentType: 'image/png'
      }));
    }
    await p.goto(w.url); await p.locator('#start').click(); await p.locator('#login-guest').click();
    await p.locator('#cls-warrior').click(); await p.locator('#name').fill('DeepArt');
    await p.locator('#go').click({ timeout: 60000 });
    await p.waitForFunction(() => Online.connected && Field.hero?.hp > 0);
    await p.evaluate(() => {
      Online.send({ type: 'debug', command: { op: 'teleport', zone: 8, x: 80, y: 160 } });
      Online.send({ type: 'debug', command: { op: 'set_time', hour: 12, freeze: true } });
    });
    await p.waitForFunction(() => Field.deepSprites && Field.slimes.some(s => s.kind === 'draugr'), null, { timeout: 30000 });
    const result = await p.evaluate(() => {
      const { meta, img } = Field.deepSprites;
      const data = {};
      const portraits = document.createElement('canvas'); portraits.width = 8*144; portraits.height = 170;
      const pg = portraits.getContext('2d'); pg.fillStyle = '#344b40'; pg.fillRect(0, 0, portraits.width, portraits.height);
      let col = 0;
      for (const kind of meta.kinds) {
        const im = img[kind], c = document.createElement('canvas'); c.width = im.width; c.height = im.height;
        const g = c.getContext('2d', { willReadFrequently: true }); g.drawImage(im, 0, 0);
        const rows = [];
        for (const [clip, spec] of Object.entries(meta.clips)) for (let n = 0; n < spec.n; n++) {
          const pixels = g.getImageData(n*96, spec.row*96, 96, 96).data;
          let opaque = 0, edge = 0, white = 0, hash = 7, minY = 96, sumY = 0;
          for (let y = 0; y < 96; y++) for (let x = 0; x < 96; x++) {
            const i = (y*96+x)*4;
            hash = (Math.imul(hash, 31)+pixels[i]+pixels[i+1]*3+pixels[i+2]*7+pixels[i+3]) >>> 0;
            if (!pixels[i+3]) continue;
            opaque++; sumY += y; minY = Math.min(minY, y);
            if (x === 0 || x === 95 || y === 0 || y === 95) edge++;
            if (pixels[i] > 220 && pixels[i+1] > 225 && pixels[i+2] > 220) white++;
          }
          let maxY = -1;
          for (let y = 95; y >= 0 && maxY < 0; y--) for (let x = 0; x < 96; x++) if (pixels[(y*96+x)*4+3]) { maxY = y; break; }
          rows.push({ clip, n, opaque, edge, white, hash, minY, maxY, meanY: sumY/Math.max(1, opaque) });
        }
        const portrait = document.createElement('canvas'); portrait.width = portrait.height = 128;
        const ready = Field.drawTargetPortrait({ kind }, portrait);
        const bytes = portrait.getContext('2d').getImageData(0, 0, 128, 128).data;
        pg.drawImage(portrait, col*144+8, 0); pg.fillStyle = '#fff2c8'; pg.font = '16px sans-serif';
        pg.fillText(Field.enemyName(kind), col*144+4, 150); col++;
        data[kind] = { size: [im.width, im.height], rows, ready,
          portraitPixels: Array.from(bytes).filter((v, i) => i%4 === 3 && v > 0).length };
      }
      return { meta, data, portraits: portraits.toDataURL() };
    });
    check(result.meta.frame.join() === '96,96' && result.meta.anchor.join() === '48,90', '96×96 frame and (48,90) anchor preserved');
    check(result.meta.kinds.join() === allKinds.join(), 'All eight production kind IDs preserved');
    for (const kind of kinds) {
      const d = result.data[kind];
      check(result.meta.sprites[kind] === sources[kind], `${kind}: production loader uses its new saved PixelFlow source`);
      check(d.size.join() === '768,480' && d.rows.length === 34 && d.rows.every(r => r.opaque > 3 && r.edge === 0), `${kind}: all 34 atlas frames nonempty and clear of every border`);
      const expected = { idle: [6,6], walk: [10,8], attack: [12,8], hurt: [10,4], die: [8,8] };
      for (const [clip, [fps, n]] of Object.entries(expected)) {
        const spec = result.meta.clips[clip];
        check(spec.fps === fps && spec.n === n && new Set(d.rows.filter(r => r.clip === clip).map(r => r.hash)).size >= Math.min(4, n), `${kind}: ${clip} preserves timing and animates distinctly`);
      }
      check(d.rows.find(r => r.clip === 'idle' && r.n === 0).white > 12, `${kind}: large eye whites and highlights remain readable`);
      check(result.meta.tops[kind] === 90-Math.min(...d.rows.filter(r=>r.clip==='idle').map(r=>r.minY)), `${kind}: health-bar top is derived from its tallest idle pose`);
      const death=d.rows.filter(r=>r.clip==='die'),idle=d.rows.find(r=>r.clip==='idle'&&r.n===0);
      const living=d.rows.filter(r=>r.clip!=='die');
      // Grounding: walkers and crawlers rest their feet/belly on the anchor row (90) in every living frame;
      // hovering kinds must not float higher than the art they replace (original lowest idle rows 71-79 / 79-82).
      const floors = { draugr: 89, hvitserk: 89, shellback: 89, moray: 88, ghostmaw: 88, kraken: 87, angler: 70, siren: 78 };
      check(living.every(r=>r.maxY>=floors[kind] && r.maxY<=91), `${kind}: ${floors[kind]>=87?'feet/belly planted on the ground row':'hover height no higher than the old art'} in all ${living.length} living frames (lowest ${Math.min(...living.map(r=>r.maxY))})`);
      if (['draugr','hvitserk','shellback'].includes(kind)) check(d.rows.filter(r=>r.clip==='walk').every(r=>r.maxY>=89), `${kind}: a foot stays planted through every walk frame`);
      check(new Set(death.map(r=>r.hash)).size===8, `${kind}: all eight anatomy-specific death poses differ`);
      if (['siren','ghostmaw'].includes(kind)) {
        check(death.at(-1).opaque<idle.opaque*.45 && death[2].opaque<death[0].opaque, `${kind}: death dissolves its body instead of collapsing it`);
      } else {
        check(death.every(r=>r.opaque>idle.opaque*.3), `${kind}: death retains its solid body, shell or cloth`);
      }
      // Dissolving kinds shed rising foam/wisps that raise the centroid; they are judged by the dissolve check above.
      if (!['siren','ghostmaw'].includes(kind)) check(death.at(-1).meanY>idle.meanY+5, `${kind}: fallen pose settles visibly below its living pose (mean row ${idle.meanY.toFixed(1)} → ${death.at(-1).meanY.toFixed(1)})`);
      check(d.ready && d.portraitPixels > 80, `${kind}: production target portrait renders`);

    }
    check(new Set(kinds.map(k=>result.data[k].rows.find(r=>r.clip==='die'&&r.n===7).hash)).size===kinds.length,'Checked kinds retain distinct final corpse silhouettes');
    fs.writeFileSync(path.join(w.runDir, 'deep-slime-portraits.png'), Buffer.from(result.portraits.split(',')[1], 'base64'));
    for (const kind of kinds) {
      const spot = await p.evaluate(kind => {
        const s = Field.slimes.find(s => s.kind === kind);
        return s && { x: s.x, y: s.y, top:s.d.top };
      }, kind);
      check(spot&&spot.top===result.meta.tops[kind], `${kind}: authoritative Ran's Deep presence and production health-bar top`);
      await p.evaluate(spot => Online.send({ type: 'debug', command: { op: 'teleport', zone: 8, x: spot.x+3, y: spot.y+2 } }), spot);
      await p.waitForTimeout(400);
      await p.evaluate(() => { City.close(); ZoneJourney.clear(); Field._debug.drawFrame(3); });
      await p.screenshot({ path: path.join(w.runDir, `deep-slime-${kind}-game.png`) });
    }
    await p.setViewportSize({ width: 844, height: 390 });
    await p.screenshot({ path: path.join(w.runDir, 'deep-slime-phone.png') });
    check(errors.length === 0, 'No real-art browser errors: '+errors.join('; '));
    fs.writeFileSync(path.join(w.runDir, 'deep-slime-browser-proof.json'), JSON.stringify({ checks, meta: result.meta, data: result.data, errors }, null, 2));
    console.log(`deep-slime-art: ${checks} checks; ${w.runDir}`);
  } finally { await browser?.close(); await w.stop(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
