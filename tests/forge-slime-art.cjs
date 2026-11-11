process.env.REAL_SPRITES = '1';
require('./lib/touch.cjs').requireMemoryLimit();
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const w = new TestWorld();
const allKinds = ["cf_brute", "cf_sentry", "cf_crawler", "cf_caster", "cf_kettil", "cf_ysolt", "cf_hallgrim", "cf_sigrun", "cf_dagfinn", "cf_thorbjorg", "cf_ragnhild", "cf_orm", "cf_hildr", "cf_eldmarr", "cf_ingot"];
const kinds = process.env.FORGE_ART_KINDS ? process.env.FORGE_ART_KINDS.split(',') : allKinds;
assert.ok(kinds.length && kinds.every(k => allKinds.includes(k)), 'Valid art selection');
const mutateKind = process.env.MUTATE_KIND || '';
const currentVersion = JSON.parse(fs.readFileSync(path.join(__dirname, '../client/release-notes.txt')))[0].version;
const frames = Object.fromEntries(allKinds.map(k => [k, [176, 172, 72, 164]]));



const registry = path.join(__dirname, '../scripts/forge_slime_sources.txt');
const sources = fs.existsSync(registry) ? JSON.parse(fs.readFileSync(registry)) : {};
const outDir = path.join(__dirname, '../test-results/forge-slime');
fs.mkdirSync(outDir, { recursive: true });
let browser, checks = 0;
const errors = [];
const failed = [];
function check(value, label) {
  if (process.env.SOFT_CHECKS && !value) { failed.push(label); console.log('FAIL: ' + label); return; }
  assert.ok(value, label);
  console.log(++checks + ': ' + label);
}
(async () => {
  try {
    w.startLevel = 98; w.godMode = true; await w.start();
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
    await p.locator('#cls-warrior').click(); await p.locator('#name').fill('ForgeArt');
    await p.locator('#go').click({ timeout: 60000 });
    await p.waitForFunction(() => Online.connected && Field.hero?.hp > 0);
    // Zone numbers are one greater than indices in WORLD_MAP.zones.
    const zoneInfo = await p.evaluate(all => {
      const i = WORLD_MAP.zones.findIndex(z => z.name === 'The Chained Forge');
      return { index: i, spawns: WORLD_MAP.zones[i].slimes.filter(s => all.includes(s.kind)).map(s => ({ kind: s.kind, x: s.x, y: s.y })) };
    }, allKinds);
    const spawns = zoneInfo.spawns;
    const first = spawns.find(s => s.kind === 'cf_brute');
    check(first && zoneInfo.index === 45, 'The Chained Forge (index 45, zone 46) spawns its enemies');
    await p.evaluate(spot => {
      Online.send({ type: 'debug', command: { op: 'teleport', zone: 46, x: spot.x - 3, y: spot.y - 3 } });
      Online.send({ type: 'debug', command: { op: 'set_time', hour: 12, freeze: true } });
    }, first);
    await p.waitForFunction(() => Field.cathedralSprites && Field.slimes.some(s => s.kind === 'cf_brute'), null, { timeout: 30000 }).catch(async e => {
      console.error('Diagnostics', await p.evaluate(() => ({ zone: Field.zone, hero: [Field.hero?.x, Field.hero?.y], sprites: !!Field.cathedralSprites,
        kinds: [...new Set(Field.slimes.map(s => s.kind))], text: document.body.innerText.slice(-300) })));
      throw e;
    });
    await p.addStyleTag({ content: '#announce, #toast, #levelup-banner, #achievement-toast { visibility: hidden !important; }' });
    const presence = {};
    for (const kind of kinds.filter(k => k !== 'cf_ingot' && spawns.some(s => s.kind === k))) {
      const spot = spawns.find(s => s.kind === kind);
      await p.evaluate(spot => Online.send({ type: 'debug', command: { op: 'teleport', zone: 46, x: spot.x - 3, y: spot.y - 3 } }), spot);
      // Enemy assets may already be loaded elsewhere in the room; wait for the authoritative arrival before a screenshot.
      await p.waitForFunction(spot => Math.hypot(Field.hero.x - (spot.x - 3), Field.hero.y - (spot.y - 3)) < 2, spot, { timeout: 30000 });

      await p.waitForFunction(kind => Field.slimes.some(s => s.kind === kind) && Field.cathedralSprites?.img[kind]?.complete, kind, { timeout: 30000 });
      await p.waitForTimeout(300);
      await p.evaluate(() => { City.close(); ZoneJourney.clear(); Field._debug.drawFrame(3); });
      presence[kind] = await p.evaluate(kind => ({
        top: Field.slimes.find(s => s.kind === kind)?.d?.top ?? (Field.cathedralSprites).meta.tops[kind],
        meta: (Field.cathedralSprites).meta.tops[kind],
        source: (Field.cathedralSprites).meta.sprites[kind],
        frame: Field.frameOf(Field.cathedralSprites, kind),
      }), kind);
      const shotPath = path.join(w.runDir, `forge-slime-${kind}-game.png`);
      await p.screenshot({ path: shotPath });
      if (!mutateKind) fs.copyFileSync(shotPath, path.join(outDir, `forge-slime-${kind}-game.png`));
    }
    if (process.env.BASELINE || process.env.SCREENSHOTS) { console.log('Review screenshots: ' + w.runDir); return; }
    if (process.env.CAPTURE_ONLY) { console.log('In-game size captures: ' + w.runDir); return; }
    await p.evaluate(async all => { const src=Field.cathedralSprites; for (const k of all) if (!src.img[k]?.complete) { const im=new Image(); im.src='assets/cathedral_'+k+'.png'; await im.decode(); src.img[k]=im; } }, kinds);
    const result = await p.evaluate(all => {
      const data = {}, metaOut = {};
      const portraits = document.createElement('canvas'); portraits.width = all.length * 144; portraits.height = 170;
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
          const pixels = g.getImageData(n * kw, spec.row * kh, kw, kh).data;
          const mask = new Uint8Array(kw * kh);
          let opaque = 0, edge = 0, white = 0, hash = 7, low = -1, top = kh, left = kw, right = -1;
          const rowCount = Array(kh).fill(0), colors = new Set();
          for (let y = 0; y < kh; y++) for (let x = 0; x < kw; x++) {
            const i = (y * kw + x) * 4;
            hash = (Math.imul(hash, 31) + pixels[i] + pixels[i + 1] * 3 + pixels[i + 2] * 7 + pixels[i + 3]) >>> 0;
            if (!pixels[i + 3]) continue;
            colors.add(`${pixels[i]},${pixels[i + 1]},${pixels[i + 2]}`); mask[y * kw + x] = 1; rowCount[y]++; opaque++;
            if (y > low) low = y; if (y < top) top = y; if (x < left) left = x; if (x > right) right = x;
            if (x === 0 || x === kw - 1 || y === 0 || y === kh - 1) edge++;
            if (pixels[i] === 255 && pixels[i + 1] === 251 && pixels[i + 2] === 234) white++;
          }
          if (clip === 'idle' && n === 0) idle0 = mask;
          let diff = 0; for (let k = 0; k < mask.length; k++) if (mask[k] !== idle0[k]) diff++;
          const rowAt = y => Array.from({ length: kw }, (_, x) => mask[y * kw + x]);
          const thick = rowCount.map((cnt, y) => cnt >= 5 ? y : -1).filter(y => y >= 0);
          rows.push({ colors: colors.size, clip, n, opaque, edge, white, hash, low, top, left, right, diff,
            solid: thick.length ? thick.at(-1) - thick[0] : 0,
            groundWidth: rowCount[fr.ay], groundRuns: runs(rowAt(fr.ay), 0, kw),
            legTracks: Math.max(...[4, 5, 6, 7, 8, 9, 10, 11, 12].map(k => runs(rowAt(fr.ay - k), 0, kw))) });
        }
        const portrait = document.createElement('canvas'); portrait.width = portrait.height = 128;
        const ready = Field.drawTargetPortrait({ kind }, portrait);
        const bytes = portrait.getContext('2d').getImageData(0, 0, 128, 128).data;
        pg.drawImage(portrait, col * 144 + 8, 0); pg.fillStyle = '#fff2c8'; pg.font = '14px sans-serif';
        pg.fillText(Field.enemyName(kind), col * 144 + 4, 150); col++;
        // Exercise the actual compositor and animation state machine, including the sleeping ingot.
        const drawCv=document.createElement('canvas');drawCv.width=kw;drawCv.height=kh;
        const dg=drawCv.getContext('2d',{willReadFrequently:true}), drawn=[];
        const requests=[['idle',0],...Array.from({length:8},(_,n)=>['attack',n]),...Array.from({length:8},(_,n)=>['die',n])];
        for(const [clip,n] of requests) {
          const actor={kind,d:{scale:1/2.1},dir:1,seed:0,dead:false,hurtT:0,recT:0,hop:0,hopV:0,landT:0,blink:0,state:'idle',st:0};
          if(clip==='die'){actor.dead=true;actor.dieT=(n+.05)/meta.clips.die.fps;}
          if(clip==='attack') {
            if(n<3){actor.state='windup';actor.windupTime=.45;actor.st=.45*(1-(n+.05)/3);}
            else if(n<6){actor.state='lunge';actor.st=.3*(1-(n-3+.05)/3);}
            else actor.recT=.22*(1-(n-6+.05)/2);
          }
          dg.clearRect(0,0,kw,kh);dg.save();dg.translate(fr.ax,fr.ay);Field._debug.drawSlimeSprite(dg,actor,0);dg.restore();
          const actual=dg.getImageData(0,0,kw,kh).data;
          const expected=g.getImageData(n*kw,meta.clips[clip].row*kh,kw,kh).data;
          drawn.push({clip,n,same:actual.every((v,i)=>v===expected[i]),opaque:actual.filter((v,i)=>i%4===3&&v>0).length});
        }
        data[kind] = { frame: [fr.w, fr.h, fr.ax, fr.ay], size: [im.width, im.height], rows, ready,
          drawn, portraitPixels: Array.from(bytes).filter((v, i) => i % 4 === 3 && v > 0).length };
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
      check(d.size.join() === `${8 * kw},${5 * kh}` && d.rows.length === 34 && d.rows.every(r => r.opaque > 3 && r.edge === 0),
        `${kind}: all 34 atlas frames (${8 * kw}×${5 * kh}) nonempty and clear of every border`);
      const expected = { idle: [6, 6], walk: [10, 8], attack: [12, 8], hurt: [10, 4], die: [8, 8] };
      for (const [clip, [fps, n]] of Object.entries(expected)) {
        const spec = m.clips[clip];
        check(spec.fps === fps && spec.n === n && new Set(d.rows.filter(r => r.clip === clip).map(r => r.hash)).size >= Math.min(3, n),
          `${kind}: ${clip} preserves timing and animates distinctly`);
      }
      const att = d.rows.filter(r => r.clip === 'attack'), die = d.rows.filter(r => r.clip === 'die');
      const idle = d.rows.filter(r => r.clip === 'idle'), idle0 = idle[0];
      const idleTop = Math.min(...idle.map(r => r.top));
      check(new Set(att.map(r => r.hash)).size === 8, `${kind}: all eight attack frames are distinct`);
      check(Math.max(att[4].right - idle0.right, idle0.left - att[4].left, Math.abs(att[4].top - idle0.top)) >= 7 && att[2].diff >= 200 && att[4].diff >= 200,
        `${kind}: wind-up and strike make substantial silhouette changes and the strike reaches out`);
      check(Math.abs(att[7].top - idle0.top) <= 4 && Math.abs(att[7].left - idle0.left) <= 4 && Math.abs(att[7].right - idle0.right) <= 4,
        `${kind}: attack recovers to its initial silhouette`);
      check(new Set(die.map(r => r.hash)).size === 8, `${kind}: all eight death frames are distinct`);
      const living = d.rows.filter(r => r.clip !== 'die');
      if (['cf_caster'].includes(kind)) {
        check(living.every(r => r.low <= kay - 12), `${kind}: flying creature hovers in mid-air above anchor row ${kay} across all living clips`);
        check(die.every(r => r.low <= kay) && die.at(-1).low === kay, `${kind}: death falls from mid-air and settles on the ground row ${kay}`);
      } else {
        check(living.every(r => r.low === kay), `${kind}: every living frame rests exactly on its anchor row ${kay}`);
        check(die.every(r => r.low === kay), `${kind}: every death frame rests exactly on the ground (row ${kay}), never sunk or floating`);
      }
      check(die.at(-1).diff >= 100, `${kind}: death changes the visible silhouette`);
      check(idle0.opaque > 450 && idle0.colors >= 10, `${kind}: substantial shaded silhouette (${idle0.opaque} opaque pixels, ${idle0.colors} colors)`);
      check(m.top === kay - idleTop, `${kind}: health-bar top is derived from its tallest idle pose`);
      if (presence[kind]) {
        check(presence[kind].top === m.top && presence[kind].source === sources[kind] &&
          presence[kind].frame.w === kw && presence[kind].frame.h === kh,
          `${kind}: The Chained Forge presence uses the new source, ${kw}×${kh} frame and production health-bar top`);
      }
      check(d.drawn.length===17&&d.drawn.every(f=>f.same&&f.opaque>3),`${kind}: production compositor and state machine render idle plus all eight attack/death source cells exactly`);
      check(d.ready && d.portraitPixels > 80, `${kind}: production target portrait renders`);
    }
    check(new Set(kinds.map(k => result.data[k].rows.find(r => r.clip === 'die' && r.n === 7).hash)).size === kinds.length, 'Checked kinds retain distinct final death silhouettes');
    const borrowed = await p.evaluate(async all => {
      const src=Field.cathedralSprites;
      const aliases=CATHEDRAL_ENEMIES.filter(e=>all.includes(e.artFrom));
      for(const e of aliases) if(!src.img[e.kind]?.complete) {const im=new Image();im.src='assets/cathedral_'+e.artFrom+'.png';await im.decode();src.img[e.kind]=im;}
      return aliases.map(e=>{
        const k=e.kind, base=e.artFrom, fr=Field.frameOf(src,k), bf=Field.frameOf(src,base);
        const cv=document.createElement('canvas');cv.width=cv.height=128;
        const ready=Field.drawTargetPortrait({kind:k},cv);
        const pixels=cv.getContext('2d').getImageData(0,0,128,128).data;
        return {kind:k,base,frame:[fr.w,fr.h,fr.ax,fr.ay],sameFrame:fr.w===bf.w&&fr.h===bf.h&&fr.ax===bf.ax&&fr.ay===bf.ay,
          sameSource:src.meta.sprites[k]===src.meta.sprites[base],sameTop:src.meta.tops[k]===src.meta.tops[base],ready,
          opaque:pixels.filter((v,i)=>i%4===3&&v>0).length};
      });
    }, kinds);
    for(const e of borrowed) check(e.sameFrame&&e.sameSource&&e.sameTop&&e.ready&&e.opaque>80,
      e.kind+': borrowed Forge art follows '+e.base+' source, frame, top and portrait');
    const portraitBuf = Buffer.from(result.portraits.split(',')[1], 'base64');
    fs.writeFileSync(path.join(w.runDir, 'forge-slime-portraits.png'), portraitBuf);
    if (!mutateKind) fs.writeFileSync(path.join(outDir, 'forge-slime-portraits.png'), portraitBuf);
    check(errors.length === 0, 'No real-art browser errors: ' + errors.join('; '));
    fs.writeFileSync(path.join(w.runDir, 'forge-slime-browser-proof.json'), JSON.stringify({ checks, meta: result.meta, data: result.data, errors }, null, 2));
    if (failed.length) { console.log('FAILED CHECKS:\n' + failed.join('\n')); process.exitCode = 1; }
    console.log(`forge-slime-art: ${checks} checks; ${w.runDir}`);
  } finally { await browser?.close(); await w.stop(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
