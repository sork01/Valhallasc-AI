// Bounded, focused private-world views for the 2026-10-26 TODOs.
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const { chromium } = require('./lib/playwright.cjs');
const world = new TestWorld(), root = path.resolve(__dirname, '..'), out = path.join(root, 'test-results/todo-art');
let browser, checks = 0;
const check = (value, label) => { assert.ok(value, label); checks++; };
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  require('./lib/touch.cjs').requireMemoryLimit();
  fs.mkdirSync(out, { recursive: true }); world.startLevel = 99; world.godMode = true; await world.start();
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  const mutation = process.env.MUTATE || (process.env.TODO_BADGER_ONLY ? 'badger-live' : undefined);
  const replacements = {
    portal: ['worldheartart.js', 'depthOffset:-2.5', 'depthOffset:0'],
    stone: ['world.js', '"kind":"meetingstone","x":66.3', '"kind":"missing_stone","x":66.3'],
    oasis: ['lapisart.js', 'ground:true', 'ground:false'],
    crack: ['frostwakeart.js', 'ground:true', 'ground:false'],
    cairn: ['cairnart.js', 'box:[620,570,310,480]', 'box:[620,520,310,480]'],
    yearhouse: ['yearwheelart.js', 'box:[460,470,230,390]', 'box:[460,430,230,390]'],
    puddle: ['yearwheelart.js', 'ground:true', 'ground:false'],
    npc: ['city.js', 'else if(window.NpcArt?.draw(g,n,t,current?.id===n.id)){}', 'else if(false){}'],
  };
  if (replacements[mutation]) {
    const [file, before, after] = replacements[mutation], source = fs.readFileSync(path.join(root, 'client', file), 'utf8');
    assert.ok(source.includes(before), 'mutation target exists');
    await page.route('**/' + file, route => route.fulfill({ contentType: 'text/javascript', body: source.replace(before, after) }));
  }
  if (mutation === 'badger') {
    const body = require('node:child_process').execFileSync('git', ['show', '476a52055485dae8b9178598b75164eda2bea17a:client/assets/sunward_spadebadger.png'], { cwd: root });
    await page.route('**/sunward_spadebadger.png', route => route.fulfill({ contentType: 'image/png', body }));
  }
  await page.addInitScript(() => {
    window.AudioContext = window.webkitAudioContext = undefined;
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, lowGraphics: true, lowGraphicsSet: true }));
  });
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('TodoArt'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.warriorSprites && NpcArt.manifest, null, { timeout: 60000 });
  async function at(zone, x, y) {
    await page.evaluate(command => Online.send({ type: 'debug', command }), { op: 'teleport', zone, x, y });
    await page.waitForFunction(({ zone, x, y }) => Field.zone === zone && Math.hypot(Field.hero.nx - x, Field.hero.ny - y) < 1, { zone, x, y }, { timeout: 15000 });
    await sleep(450);
  }
  async function around(zone, kind, side = 1) {
    const o = await page.evaluate(({ zone, kind }) => WORLD_MAP.zones[zone - 1].objects.find(o => o.kind === kind), { zone, kind });
    assert.ok(o, kind + ' exists'); const offset = kind === 'lapis_oasis' ? 4.5 : 3;
    await at(zone, o.x + side * offset, o.y + side * offset); return o;
  }
  async function trace() {
    return page.evaluate(() => {
      const order = [], object = City.drawObject, spr = Field.warriorSprites, actor = spr.draw;
      const g = document.querySelector('#fieldcv').getContext('2d'), fill = g.fillText;
      City.drawObject = function(ctx, o, x, y, fade) { order.push({ kind: o.kind, fade: fade ?? 1 }); return object.apply(this, arguments); };
      spr.draw = function() { order.push({ kind: 'hero' }); return actor.apply(this, arguments); };
      g.fillText = function(value) { if (String(value).startsWith('Veyrroot Heartwood')) order.push({ kind: 'hollowPortal' }); return fill.apply(this, arguments); };
      try { Field._debug.drawFrame(1); return order; } finally { City.drawObject = object; spr.draw = actor; g.fillText = fill; }
    });
  }
  async function ground(zone, kind) {
    for (const side of [-1, 1]) {
      await around(zone, kind, side); const order = await trace(), terrain = order.findIndex(i => i.kind === kind), hero = order.findIndex(i => i.kind === 'hero');
      check(terrain >= 0 && hero > terrain, `${kind}: real zone terrain draws below the hero from side ${side}`);
      await page.screenshot({ path: path.join(out, `${kind}-${side}.png`) });
    }
  }
  if (!mutation || mutation === 'portal') {
    await at(23, 58, 73); const order = await trace();
    check(order.findIndex(x => x.kind === 'hollowPortal') > order.findIndex(x => x.kind === 'hollow_arch'), 'Hollow Arch portal draws above its obstructing arch');
    await page.screenshot({ path: path.join(out, 'canopy-portal.png') });
    // Use the actual gate and verify the reciprocal safe arrival.
    await page.evaluate(() => Field.setTouchDirection(-1, -3)); await page.waitForFunction(() => Field.zone === 24, null, { timeout: 12000 });
    await page.evaluate(() => Field.setTouchDirection(0, 0));
    check(await page.evaluate(() => Math.hypot(Field.hero.nx - 48, Field.hero.ny - 80) < 3), 'Hollow Arch portal reaches its original safe destination');
  }
  if (!mutation || mutation === 'stone') {
    await at(23, 68, 77); const order = await trace();
    check(order.some(x => x.kind === 'meetingstone'), 'Crown Meeting Stone is drawn in its actual zone');
    await page.evaluate(() => Field.visitNpc('heart_stone')); await page.waitForFunction(() => !document.querySelector('#npc-dialogue').hidden);
    check((await page.locator('#npc-dialogue').textContent()).includes('Hire a Warrior'), 'visible Crown Meeting Stone keeps hiring interactions');
    await page.screenshot({ path: path.join(out, 'canopy-stone.png') }); await page.evaluate(() => City.close());
  }
  if (!mutation || mutation === 'oasis') await ground(25, 'lapis_oasis');
  if (!mutation || mutation === 'crack') await ground(26, 'frostwake_crevasse');
  if (!mutation || mutation === 'puddle') await ground(28, 'year_spring_pool');
  for (const [zone, kind, tag] of [[27, 'cairn_watchhall', 'cairn'], [28, 'year_lodge', 'yearhouse']]) {
    if (mutation && mutation !== tag) continue;
    await around(zone, kind);
    const fit = await page.evaluate(kind => {
      const o = Field._debug.objects.find(o => o.kind === kind), def = City.art[kind], [w, h, x, y] = def.box;
      // Compare cached production output to the full drawing on a padded canvas.
      const canvas = document.createElement('canvas'); canvas.width = w + 240; canvas.height = h + 240;
      const g = canvas.getContext('2d'); g.translate(x + 120, y + 120); def.draw(g, o, City.kit);
      const p = g.getImageData(0, 0, canvas.width, canvas.height).data; let outside = 0, base = 0;
      for (let yy = 0; yy < canvas.height; yy++) for (let xx = 0; xx < canvas.width; xx++) if (p[(yy * canvas.width + xx) * 4 + 3]) { if (xx < 120 || yy < 120 || xx >= w + 120 || yy >= h + 120) outside++; if (yy > y + 120 + 45) base++; }
      return { outside, base };
    }, kind);
    check(fit.outside === 0 && fit.base > 10, kind + ' retains every source-art pixel including its foundation');
    await page.screenshot({ path: path.join(out, kind + '.png') });
  }
  if ((!mutation && !process.env.TODO_VISIBILITY_ONLY) || mutation === 'badger' || mutation === 'badger-live') {
    // Decode the real Sunward sheets even when unrelated classes/enemies use the fast test stubs.
    await page.evaluate(async () => {
      const meta = await (await fetch('assets/sunward.txt')).json(), images = {};
      await Promise.all(meta.kinds.map(k => new Promise((resolve, reject) => { const img = new Image(); img.onload = () => { images[k] = img; resolve(); }; img.onerror = reject; img.src = `assets/sunward_${k}.png`; })));
      Field.sunwardSprites.meta = meta; Field.sunwardSprites.img = images;
    });
    const clawPoses = await page.evaluate(() => {
      const img = Field.sunwardSprites.img.spadebadger, canvas = document.createElement('canvas'); canvas.width = 96; canvas.height = 96;
      const g = canvas.getContext('2d'), poses = [];
      for (let n = 0; n < 8; n++) { g.clearRect(0, 0, 96, 96); g.drawImage(img, n * 96, 96, 96, 96, 0, 0, 96, 96); const pixels = g.getImageData(48, 76, 42, 16).data;
        // The light ivory claws are separate from gray fur; a fixed forefoot yields an identical mask.
        let mask = ''; for (let i = 0; i < pixels.length; i += 4) mask += pixels[i + 3] && pixels[i] > 190 && pixels[i + 1] > 175 && pixels[i + 2] < pixels[i + 1] ? '1' : '0'; poses.push(mask);
      }
      return new Set(poses).size;
    });
    check(clawPoses >= 5, 'actual Badger atlas animates the front spade claws');
    const spawn = await page.evaluate(() => WORLD_MAP.zones[19].slimes.find(s => s.kind === 'spadebadger'));
    await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'set_level', level: 65 } }));
    await at(20, spawn.x + 5, spawn.y + 3);
    const frames = new Set();
    for (let i = 0; i < 35; i++) {
      const pose = await page.evaluate(() => { const s = Field.slimes.find(s => s.kind === 'spadebadger' && !s.dead); return s ? Field._debug.enemyFrame(s) : null; });
      if (pose?.[0] === 'walk') frames.add(pose[1]);
      if (frames.size >= 2) break;
      await sleep(80);
    }
    check(frames.size >= 2, 'live Sunward Badger uses changing walk frames during its actual movement');
    await page.screenshot({ path: path.join(out, 'spadeclaw-walk.png') });
  }
  if ((!mutation && !process.env.TODO_VISIBILITY_ONLY) || mutation === 'npc') {
    const catalog = await page.evaluate(() => NpcArt.manifest);
    check(Object.keys(catalog.designs).filter(k => catalog.designs[k].general).length >= 24, '24 distinct general designs');
    check(Object.keys(catalog.npcs).length === 298, 'every speaking person has an explicit assignment');
    for (const zone of [0, 4, 9, 17, 20, 21, 22, 23, 24, 25, 26, 27, 28, 45]) {
      const npc = await page.evaluate(zone => (zone ? WORLD_MAP.zones[zone - 1] : WORLD_MAP).npcs.find(n => n.art !== 'stone' && n.art !== 'scenery'), zone);
      await at(zone, npc.x + 1.7, npc.y + 1.7); await page.waitForFunction(() => NpcArt.readyFor(City.npcs), null, { timeout: 20000 });
      const shown = await page.evaluate(id => {
        const n = City.npcs.find(n => n.id === id), canvas = document.createElement('canvas'); canvas.width = canvas.height = 260; const g = canvas.getContext('2d');
        let used = false; const draw = NpcArt.draw; NpcArt.draw = function() { const result = draw.apply(this, arguments); used ||= result; return result; };
        try { City.drawNpc(g, n, 130, 190, 1, false, true); } finally { NpcArt.draw = draw; }
        const a = g.getImageData(0, 0, 260, 260).data; let pixels = 0; for (let i = 3; i < a.length; i += 4) if (a[i]) pixels++;
        return { used, pixels, top: City.nameplateTop(n), cache: NpcArt.cacheSize, limit: NpcArt.cacheLimit, people: City.npcs.length };
      }, npc.id);
      check(shown.used && shown.pixels > 500 && shown.top > 70 && shown.cache <= shown.limit && shown.limit >= shown.people, `zone ${zone}: actual NPC and portrait use the new artwork with fitted nameplates and a stable canvas working set`);
      await page.screenshot({ path: path.join(out, `npc-zone-${zone}.png`) });
    }
    const animated = await page.evaluate(() => {
      const n = City.npcs.find(n => NpcArt.manifest.npcs[n.id]);
      return [false, true].map(moving => { const actor = { ...n, moving, fx: -1, fy: 0 }; return [0, .14, .28, .42].map(t => NpcArt.frame(actor, t)); });
    });
    check(animated.every(rows => new Set(rows.map(r => r.step)).size > 1) && animated[1].every(r => r.clip === 'walk' && r.mirrored), 'idle and walking frames advance and mirror with travel direction');
    check(await page.evaluate(() => { const n = City.npcs[0]; return NpcArt.frame(n, 1, true).clip === 'talk'; }), 'conversation has its own animation');
    const smith = await page.evaluate(() => WORLD_MAP.npcs.find(n => n.id === 'smith'));
    await at(0, smith.x + 1.7, smith.y + 1.7); await page.waitForFunction(() => NpcArt.readyFor(City.npcs));
    await page.evaluate(() => Field.visitNpc('smith')); await page.waitForFunction(() => !document.querySelector('#merchant-portrait').hidden);
    const portraitPixels = await page.locator('#merchant-portrait').evaluate(canvas => {
      const p = canvas.getContext('2d').getImageData(0,0,128,128).data; let painted = 0;
      for (let i=0;i<p.length;i+=4) if(p[i+3] && (p[i]!==38 || p[i+1]!==53 || p[i+2]!==70)) painted++;
      return painted;
    });
    check(portraitPixels > 1000, 'real merchant portrait contains the NPC artwork inside its circular crop');
    await page.screenshot({path:path.join(out,'npc-merchant-portrait.png')}); await page.evaluate(()=>City.close());
  }
  check(errors.length === 0, 'no browser errors: ' + errors.join('; '));
  console.log(`TODO art: ${checks} focused checks passed; screenshots ${out}`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  if (browser) await browser.close(); await world.stop();
  try { const cgroup = fs.readFileSync('/proc/self/cgroup', 'utf8').trim().split('::')[1]; console.log('Peak memory MiB:', Math.round(+fs.readFileSync('/sys/fs/cgroup' + cgroup + '/memory.peak', 'utf8') / 1048576)); } catch (_) {}
});
