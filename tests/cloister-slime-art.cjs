process.env.REAL_SPRITES = '1';
require('./lib/touch.cjs').requireMemoryLimit();
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const w = new TestWorld();
const allKinds = ['tidetemplar', 'tidecantor', 'tideleech', 'bellkeeper', 'mournsister', 'rootabbot', 'choirmother', 'choirsinger'];
const kinds = process.env.CLOISTER_ART_KINDS ? process.env.CLOISTER_ART_KINDS.split(',') : allKinds;
assert.ok(kinds.length && kinds.every(k => allKinds.includes(k)), 'Valid art selection');
const currentVersion = JSON.parse(fs.readFileSync(path.join(__dirname, '../client/release-notes.txt')))[0].version;
const sources = JSON.parse(fs.readFileSync(path.join(__dirname, '../scripts/cloister_slime_sources.txt')));
let browser, checks = 0;
const errors = [];
function check(value, label) { assert.ok(value, label); console.log(++checks + ': ' + label); }
(async () => {
  try {
    w.startLevel = 50; w.godMode = true; await w.start();
    browser = await chromium.launch({ headless: true });
    const p = await browser.newPage({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
    p.on('pageerror', e => errors.push(e.message));
    await p.addInitScript(version => {
      localStorage.setItem('valhallasc.whats-new.v1', version);
      window.AudioContext = window.webkitAudioContext = undefined;
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false,
        dpsMeter: false, lowGraphics: true, lowGraphicsSet: true, touchGraphicsSuggested: true }));
    }, currentVersion);
    if (process.env.CLOISTER_MUTATED_ATLAS) {
      // Mutation control: serve a templar atlas whose feet float; the grounding assertion must reject it.
      await p.route('**/assets/cathedral_tidetemplar.png', route => route.fulfill({
        path: process.env.CLOISTER_MUTATED_ATLAS, contentType: 'image/png'
      }));
    }
    await p.goto(w.url); await p.locator('#start').click(); await p.locator('#login-guest').click();
    await p.locator('#cls-warrior').click(); await p.locator('#name').fill('CloisterArt');
    await p.locator('#go').click({ timeout: 60000 });
    await p.waitForFunction(() => Online.connected && Field.hero?.hp > 0);
    const spawns = await p.evaluate(all => WORLD_MAP.zones[9].slimes.filter(s => all.includes(s.kind)).map(s => ({ kind: s.kind, x: s.x, y: s.y })), allKinds);
    const first = spawns.find(s => s.kind === 'tidetemplar');
    check(first, 'Flooded Cloister (zone 10) spawns the Tide Templar');
    await p.evaluate(spot => {
      Online.send({ type: 'debug', command: { op: 'teleport', zone: 10, x: spot.x+3, y: spot.y+3 } });
      Online.send({ type: 'debug', command: { op: 'set_time', hour: 12, freeze: true } });
    }, first);
    await p.waitForFunction(() => Field.zone === 10 && Field.cathedralSprites && Field.slimes.some(s => s.kind === 'tidetemplar'), null, { timeout: 30000 }).catch(async e => {
      console.error('Diagnostics', await p.evaluate(() => ({ zone: Field.zone, hero: [Field.hero?.x, Field.hero?.y], sprites: !!Field.cathedralSprites,
        kinds: [...new Set(Field.slimes.map(s => s.kind))], text: document.body.innerText.slice(-300) })));
      throw e;
    });
    const presence = {};
    // The Bound Singer is a raid-helper add that sleeps until the boss mechanic wakes it; sleepers are never drawn or loaded.
    for (const kind of kinds.filter(k => k !== 'choirsinger' && spawns.some(s => s.kind === k))) {
      const spot = spawns.find(s => s.kind === kind);
      await p.evaluate(spot => Online.send({ type: 'debug', command: { op: 'teleport', zone: 10, x: spot.x+3, y: spot.y+3 } }), spot);
      await p.waitForFunction(kind => Field.zone === 10 && Field.slimes.some(s => s.kind === kind) && Field.cathedralSprites?.img[kind]?.complete, kind, { timeout: 30000 });
      await p.waitForTimeout(300);
      await p.evaluate(() => { City.close(); ZoneJourney.clear(); Field._debug.drawFrame(3); });
      await p.screenshot({ path: path.join(w.runDir, `cloister-slime-${kind}-game.png`) });
      presence[kind] = await p.evaluate(kind => ({ top: Field.slimes.find(s => s.kind === kind).d.top, meta: Field.cathedralSprites.meta.tops[kind], source: Field.cathedralSprites.meta.sprites[kind] }), kind);
    }
    // The shared bank loads a kind only when an actor of it is present: raid-helper adds such as the Bound Singer are asleep
    // here, so load any atlas the zone did not request exactly as the production loader does (same URL, same image object).
    const manual = await p.evaluate(async all => {
      const { img } = Field.cathedralSprites, loaded = [];
      for (const kind of all) if (!img[kind]) {
        const image = new Image(); image.src = `assets/cathedral_${kind}.png`;
        await image.decode(); img[kind] = image; loaded.push(kind);
      }
      return loaded;
    }, allKinds);
    check(manual.every(k => k === 'choirsinger'), `Only the sleeping helper add had to be loaded by hand: [${manual.join()}]`);
    const result = await p.evaluate(all => {
      const { meta, img } = Field.cathedralSprites;
      const data = {};
      const portraits = document.createElement('canvas'); portraits.width = 8*144; portraits.height = 170;
      const pg = portraits.getContext('2d'); pg.fillStyle = '#244047'; pg.fillRect(0, 0, portraits.width, portraits.height);
      let col = 0;
      for (const kind of all) {
        const im = img[kind], c = document.createElement('canvas'); c.width = im.width; c.height = im.height;
        const g = c.getContext('2d', { willReadFrequently: true }); g.drawImage(im, 0, 0);
        const rows = [];
        for (const [clip, spec] of Object.entries(meta.clips)) for (let n = 0; n < spec.n; n++) {
          const pixels = g.getImageData(n*96, spec.row*96, 96, 96).data;
          let opaque = 0, edge = 0, white = 0, hash = 7, minY = 96, sumY = 0;
          const perRow = new Array(96).fill(0);
          for (let y = 0; y < 96; y++) for (let x = 0; x < 96; x++) {
            const i = (y*96+x)*4;
            hash = (Math.imul(hash, 31)+pixels[i]+pixels[i+1]*3+pixels[i+2]*7+pixels[i+3]) >>> 0;
            if (!pixels[i+3]) continue;
            opaque++; sumY += y; minY = Math.min(minY, y); perRow[y]++;
            if (x === 0 || x === 95 || y === 0 || y === 95) edge++;
            if (pixels[i] > 220 && pixels[i+1] > 225 && pixels[i+2] > 220) white++;
          }
          let maxY = -1;
          for (let y = 95; y >= 0 && maxY < 0; y--) for (let x = 0; x < 96; x++) if (pixels[(y*96+x)*4+3]) { maxY = y; break; }
          const thick = perRow.map((c, y) => c >= 5 ? y : -1).filter(y => y >= 0);          // rows with real mass: stray motes and sparkles do not count
          rows.push({ clip, n, opaque, edge, white, hash, minY, maxY, meanY: sumY/Math.max(1, opaque), solid: thick.length ? thick.at(-1)-thick[0] : 0 });
        }
        const portrait = document.createElement('canvas'); portrait.width = portrait.height = 128;
        const ready = Field.drawTargetPortrait({ kind }, portrait);
        const bytes = portrait.getContext('2d').getImageData(0, 0, 128, 128).data;
        pg.drawImage(portrait, col*144+8, 0); pg.fillStyle = '#fff2c8'; pg.font = '16px sans-serif';
        pg.fillText(Field.enemyName(kind), col*144+4, 150); col++;
        data[kind] = { size: [im.width, im.height], rows, ready,
          portraitPixels: Array.from(bytes).filter((v, i) => i%4 === 3 && v > 0).length };
      }
      return { meta: { frame: meta.frame, anchor: meta.anchor, clips: meta.clips, sprites: Object.fromEntries(all.map(k => [k, meta.sprites[k]])),
                       tops: Object.fromEntries(all.map(k => [k, meta.tops[k]])), kinds: meta.kinds.length }, data, portraits: portraits.toDataURL() };
    }, allKinds);
    check(result.meta.frame.join() === '96,96' && result.meta.anchor.join() === '48,90', '96×96 frame and (48,90) anchor preserved');
    check(result.meta.kinds >= 146, `The shared Cathedral manifest still lists all ${result.meta.kinds} kinds`);
    for (const kind of kinds) {
      const d = result.data[kind];
      check(result.meta.sprites[kind] === sources[kind], `${kind}: production loader uses its new saved PixelFlow source`);
      check(d.size.join() === '768,480' && d.rows.length === 34 && d.rows.every(r => r.opaque > 3 && r.edge === 0), `${kind}: all 34 atlas frames nonempty and clear of every border`);
      const expected = { idle: [6,6], walk: [10,8], attack: [12,8], hurt: [10,4], die: [8,8] };
      for (const [clip, [fps, n]] of Object.entries(expected)) {
        const spec = result.meta.clips[clip];
        check(spec.fps === fps && spec.n === n && new Set(d.rows.filter(r => r.clip === clip).map(r => r.hash)).size >= Math.min(4, n), `${kind}: ${clip} preserves timing and animates distinctly`);
      }
      check(d.rows.find(r => r.clip === 'idle' && r.n === 0).white > 8, `${kind}: large eye whites and highlights remain readable`);
      check(result.meta.tops[kind] === 90-Math.min(...d.rows.filter(r => r.clip === 'idle').map(r => r.minY)), `${kind}: health-bar top is derived from its tallest idle pose`);
      const death = d.rows.filter(r => r.clip === 'die'), idle = d.rows.find(r => r.clip === 'idle' && r.n === 0);
      const living = d.rows.filter(r => r.clip !== 'die');
      const height = r => r.solid;
      // Grounding: every hem, foot, base or belly rests on the anchor row (90) in every living frame, so nothing floats.
      check(living.every(r => r.maxY === 90), `${kind}: rests exactly on the ground row in all ${living.length} living frames (lowest ${Math.max(...living.map(r => r.maxY))})`);
      if (['tidetemplar', 'bellkeeper', 'rootabbot'].includes(kind)) check(d.rows.filter(r => r.clip === 'walk').every(r => r.maxY === 90), `${kind}: a foot stays planted through every walk frame`);
      check(new Set(death.map(r => r.hash)).size === 8, `${kind}: all eight death poses differ`);
      if (['mournsister', 'choirsinger'].includes(kind)) {
        check(death.at(-1).opaque < idle.opaque*.2 && death[4].opaque < death[0].opaque*.65 && death[5].opaque < death[4].opaque, `${kind}: death dissolves its body (${idle.opaque} → ${death.at(-1).opaque} px)`);
      } else {
        check(death.every(r => r.opaque > idle.opaque*.3), `${kind}: death retains its solid body, cloth or wood`);
      }
      const lower = { tidetemplar: .7, tidecantor: .4, tideleech: .7, bellkeeper: .7, rootabbot: .65, choirmother: .6 }[kind];
      if (lower) check(height(death.at(-1)) < height(idle)*lower, `${kind}: fallen pose is much lower than the living pose (${height(idle)} → ${height(death.at(-1))} px tall)`);
      if (presence[kind]) check(presence[kind].top === result.meta.tops[kind] && presence[kind].source === sources[kind], `${kind}: authoritative Flooded Cloister presence uses the new source and production health-bar top`);
      check(d.ready && d.portraitPixels > 80, `${kind}: production target portrait renders`);
    }
    check(new Set(kinds.map(k => result.data[k].rows.find(r => r.clip === 'die' && r.n === 7).hash)).size === kinds.length, 'Checked kinds retain distinct final death silhouettes');
    fs.writeFileSync(path.join(w.runDir, 'cloister-slime-portraits.png'), Buffer.from(result.portraits.split(',')[1], 'base64'));
    // The Coral Reliquary spawns the same two kinds, so it inherits the new art.
    const reliquary = await p.evaluate(() => ['tidetemplar', 'tidecantor'].map(k => WORLD_MAP.zones[10].slimes.find(s => s.kind === k)).filter(Boolean).map(s => ({ kind: s.kind, x: s.x, y: s.y })));
    check(reliquary.length === 2, 'The Coral Reliquary (zone 11) also spawns Tide Templar and Tide Cantor');
    for (const spot of reliquary) {
      await p.evaluate(spot => Online.send({ type: 'debug', command: { op: 'teleport', zone: 11, x: spot.x+3, y: spot.y+3 } }), spot);
      await p.waitForFunction(kind => Field.zone === 11 && Field.slimes.some(s => s.kind === kind), spot.kind, { timeout: 20000 });
      const top = await p.evaluate(kind => Field.slimes.find(s => s.kind === kind).d.top, spot.kind);
      check(top === result.meta.tops[spot.kind], `${spot.kind}: the Reliquary uses the same new atlas and health-bar top`);
    }
    await p.setViewportSize({ width: 844, height: 390 });
    await p.screenshot({ path: path.join(w.runDir, 'cloister-slime-phone.png') });
    check(errors.length === 0, 'No real-art browser errors: '+errors.join('; '));
    fs.writeFileSync(path.join(w.runDir, 'cloister-slime-browser-proof.json'), JSON.stringify({ checks, meta: result.meta, data: result.data, errors }, null, 2));
    console.log(`cloister-slime-art: ${checks} checks; ${w.runDir}`);
  } finally { await browser?.close(); await w.stop(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
