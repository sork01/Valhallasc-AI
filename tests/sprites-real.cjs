// The real artwork, loaded for real. Every other browser suite runs on the client's stub sprites (tests/lib/playwright.cjs)
// to keep page loads fast, so this one checks what they skip: each class's layered atlases composite into real figures
// that change with equipment, the enemy atlases load at their documented sizes, and the stub itself behaves.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium } = require('playwright');   // the plain one: no stub
const root = path.resolve(__dirname, '..');
const timeout = (promise, ms, label) => Promise.race([promise, new Promise((_, reject) => { const t = setTimeout(() => reject(Error(label)), ms); t.unref(); })]);
let server, browser, url, logs = '', checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function startServer(db) {
  const binary = process.env.VALHALLA_BINARY || path.join(root, 'target/debug/valhalla-server');
  const env = { ...process.env, VALHALLA_BIND: '127.0.0.1:0', VALHALLA_DB: db, RUST_LOG: 'valhalla_server=info', VALHALLA_LEVEL_SPREAD: '0', VALHALLA_GOD_MODE: '1' };
  delete env.VALHALLA_ORIGIN;
  server = spawn(binary, [], { cwd: root, env, stdio: ['ignore', 'pipe', 'pipe'] });
  server.stderr.on('data', d => { logs += d; });
  await timeout(new Promise((resolve, reject) => {
    server.stdout.on('data', d => { logs += d.toString().replace(/\x1b\[[0-9;]*m/g, ''); const m = logs.match(/address=(127\.0\.0\.1:\d+)/); if (m) { url = 'http://' + m[1] + '/'; resolve(); } });
    server.once('error', reject); server.once('exit', code => reject(Error(`Server exited ${code}: ${logs}`)));
  }), 15000, 'Server did not start');
}
async function enter(stub, cls, name) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
  await context.addInitScript(stub => {
    if (stub) window.__valhallaTestSprites = true;
    if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null }));
  }, stub);
  const page = await context.newPage(); page.errors = []; page.on('pageerror', e => page.errors.push(e.message));
  await page.goto(url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-' + cls).click(); await page.locator('#name').fill(name); await page.locator('#go').click({ timeout: 90000 });
  await page.waitForFunction(cls => Online.connected && !!valhalla[cls] && !!Field.beetleSprites && !!Field.cragSprites, cls, { timeout: 90000 });
  return page;
}
// Visible pixels of the idle frame under the current equipment, and a fingerprint of them. `female` loads and uses the
// class's female atlases (the same equipment names, a separate set of files).
const figure = (page, cls, armor, weapon, extras = {}, female = false) => page.evaluate(async ([cls, armor, weapon, extras, female]) => {
  const C = { warrior: WarriorSprite, mage: MageSprite, assassin: AssassinSprite, priest: PriestSprite, hunter: HunterSprite }[cls];
  window.femaleSprites = window.femaleSprites || {};
  const sprite = female ? (window.femaleSprites[cls] = window.femaleSprites[cls] || await C.Female.load({ ...valhalla[cls].look, gender: 'female' })) : valhalla[cls];
  const look = { ...sprite.look, head: 'none', shoulders: 'none', gloves: 'none', pants: 'none', necklace: 'none', accessory: 'none', ...extras, [cls + 'Armor']: armor, [cls + 'Weapon']: weapon };
  sprite.set(look);
  // The class-independent layers are decoded on demand: wait for whatever this look wears, then rebuild the frames.
  await Promise.all(Object.entries(sprite.equipment).map(([slot, v]) => v !== 'none' && sprite.source.ensure(slot + '_' + v)));
  sprite.cache.clear();
  const canvas = sprite.frame('idle', 0, 0), data = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
  let visible = 0, hash = 0;
  for (let i = 0; i < data.length; i += 4) if (data[i + 3]) { visible++; hash = (hash * 31 + data[i] * 3 + data[i + 1] * 5 + data[i + 2] * 7 + i) >>> 0; }
  return { visible, hash, width: canvas.width };
}, [cls, armor, weapon, extras, female]);

(async () => {
  const dir = fs.mkdtempSync(path.join(root, 'test-results/sprites-'));
  await startServer(path.join(dir, 'test.sqlite'));
  browser = await chromium.launch({ headless: true });
  try {
    for (const cls of ['warrior', 'mage', 'assassin', 'priest', 'hunter']) {
      const page = await enter(false, cls, 'Real' + cls);
      check(await page.evaluate(() => window.__valhallaTestSprites === undefined), `${cls}: the stub is off`);
      const gear = await page.evaluate(cls => { const C = { warrior: WarriorSprite, mage: MageSprite, assassin: AssassinSprite, priest: PriestSprite, hunter: HunterSprite }[cls]; return { armor: Object.keys(C.ARMOR).filter(k => k !== 'none'), weapon: Object.keys(C.WEAPON).filter(k => k !== 'none'), tiers: C.TIERS }; }, cls);
      const naked = await figure(page, cls, 'none', 'none'), dressed = await figure(page, cls, gear.armor[0], gear.weapon[0]), other = await figure(page, cls, gear.armor[1], gear.weapon[1]);
      check(naked.visible > 1500, `${cls}: the real body is a full figure (${naked.visible} visible pixels)`);
      check(dressed.visible > naked.visible && dressed.hash !== naked.hash, `${cls}: armour and a weapon add to the figure`);
      check(other.hash !== dressed.hash, `${cls}: the other armour and weapon look different`);
      // Shoulders, gloves and head are their own layers: each tier of each adds to the figure, differs from the
      // other tier, and goes away again with 'none'.
      for (const slot of ['head', 'shoulders', 'gloves']) {
        if (!gear.tiers.length) { check((await figure(page, cls, gear.armor[0], gear.weapon[0], { [slot]: 'crimson' })).hash === dressed.hash, `${cls}: no ${slot} layer, so a ${slot} piece changes nothing`); continue; }
        const worn = [];
        for (const tier of gear.tiers) worn.push(await figure(page, cls, gear.armor[0], gear.weapon[0], { [slot]: tier }));
        check(worn.every(w => w.hash !== dressed.hash && w.visible > 0), `${cls}: each ${slot} tier is drawn`);
        check(worn[0].hash !== worn[1].hash, `${cls}: the two ${slot} tiers look different`);
        check((await figure(page, cls, gear.armor[0], gear.weapon[0], { [slot]: 'none' })).hash === dressed.hash, `${cls}: ${slot} 'none' removes the layer`);
        check((await figure(page, cls, gear.armor[0], gear.weapon[0], { [slot]: 'azure_not_a_tier' })).hash === dressed.hash, `${cls}: an unknown ${slot} tier is ignored`);
      }
      if (gear.tiers.length) {
        const all = await figure(page, cls, gear.armor[0], gear.weapon[0], { head: gear.tiers[0], shoulders: gear.tiers[0], gloves: gear.tiers[0] });
        check(all.hash !== dressed.hash && all.visible > dressed.visible, `${cls}: head, shoulders and gloves worn together make a bigger figure`);
      }
      // The class-independent pieces (Ironhide Helm and Pauldrons, Duelist Gloves, Wayfarer Pants, Moonstone Necklace, Amber Ring):
      // the same art on every class, each its own layer, each adds to the figure, 'none' removes it, and a slot ignores a name it does not know.
      const generic = await page.evaluate(() => MageSprite.GENERIC), genericWorn = {};
      for (const [slot, variant] of Object.entries(generic)) {
        genericWorn[slot] = await figure(page, cls, gear.armor[0], gear.weapon[0], { [slot]: variant });
        check(genericWorn[slot].hash !== dressed.hash && genericWorn[slot].visible > 0, `${cls}: the generic ${slot} piece (${variant}) is drawn`);
        check((await figure(page, cls, gear.armor[0], gear.weapon[0], { [slot]: 'none' })).hash === dressed.hash, `${cls}: generic ${slot} 'none' removes the layer`);
      }
      check(new Set(Object.values(genericWorn).map(w => w.hash)).size === Object.keys(generic).length, `${cls}: the six generic pieces are six different pictures`);
      check((await figure(page, cls, gear.armor[0], gear.weapon[0], { pants: 'ironhide' })).hash === dressed.hash && (await figure(page, cls, gear.armor[0], gear.weapon[0], { necklace: 'amber' })).hash === dressed.hash, `${cls}: pants and necklace ignore names they do not know`);
      const everything = await figure(page, cls, gear.armor[0], gear.weapon[0], generic);
      check(everything.visible > dressed.visible && everything.hash !== dressed.hash, `${cls}: all six generic pieces worn together make a bigger figure`);
      check(await page.evaluate(cls => valhalla[cls].portrait().length > 2000, cls), `${cls}: the portrait renders`);
      // The female set: its own atlases, the same equipment, a body that is not the male one.
      const f = (armor, weapon, extras) => figure(page, cls, armor, weapon, extras, true);
      const fNaked = await f('none', 'none'), fDressed = await f(gear.armor[0], gear.weapon[0]), fOther = await f(gear.armor[1], gear.weapon[1]);
      check(fNaked.visible > 1500, `${cls} (female): the real body is a full figure (${fNaked.visible} visible pixels)`);
      check(fNaked.hash !== naked.hash && fDressed.hash !== dressed.hash && fOther.hash !== other.hash, `${cls} (female): a different body from the male one, bare and dressed`);
      if (cls === 'mage' || cls === 'priest') check(fNaked.visible > naked.visible, `${cls}: the man has short hair and the woman long hair (${naked.visible} against ${fNaked.visible} visible pixels bare)`);
      check(fDressed.visible > fNaked.visible && fDressed.hash !== fNaked.hash && fOther.hash !== fDressed.hash, `${cls} (female): armour and weapons add to the figure and differ from each other`);
      for (const slot of ['head', 'shoulders', 'gloves']) {
        if (!gear.tiers.length) continue;
        const worn = [];
        for (const tier of gear.tiers) worn.push(await f(gear.armor[0], gear.weapon[0], { [slot]: tier }));
        check(worn.every(w => w.hash !== fDressed.hash && w.visible > 0) && worn[0].hash !== worn[1].hash, `${cls} (female): each ${slot} tier is drawn and they differ`);
        check((await f(gear.armor[0], gear.weapon[0], { [slot]: 'none' })).hash === fDressed.hash, `${cls} (female): ${slot} 'none' removes the layer`);
      }
      for (const [slot, variant] of Object.entries(generic)) {
        const w = await f(gear.armor[0], gear.weapon[0], { [slot]: variant });
        check(w.hash !== fDressed.hash && w.visible > 0 && (await f(gear.armor[0], gear.weapon[0], { [slot]: 'none' })).hash === fDressed.hash, `${cls} (female): the generic ${slot} piece is drawn and 'none' removes it`);
      }
      check(await page.evaluate(cls => { const s = femaleSprites[cls]; return s.meta.gender === 'female' && s.portrait().length > 2000 && ['idle', 'walk', 'attack', 'hurt', 'die'].every(c => s.frame(c, 5, 0).width > 0); }, cls), `${cls} (female): metadata, portrait and every clip render`);
      // Animation: the walk and the attack are different pictures from standing still, in the female set too.
      check(await page.evaluate(cls => { const hash = (clip, i) => { const c = femaleSprites[cls].frame(clip, 3, i), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let h = 0; for (let k = 3; k < d.length; k += 4) h = (h * 31 + d[k - 3] + d[k - 2] * 3) >>> 0; return h; }; return new Set([hash('idle', 0), hash('walk', 2), hash('attack', 4), hash('die', 7)]).size === 4; }, cls), `${cls} (female): idle, walk, attack and die are four different pictures`);
      if (cls === 'mage') {
        const sizes = await page.evaluate(() => ({
          beetle: [Field.beetleSprites.img.beetle.naturalWidth, Field.beetleSprites.img.beetle.naturalHeight],
          crags: Object.fromEntries(Field.cragSprites.meta.kinds.map(k => [k, [Field.cragSprites.img[k].naturalWidth, Field.cragSprites.img[k].naturalHeight]])),
        }));
        check(sizes.beetle.join() === '576,320', 'the Ironhide atlas is 576x320');
        check(Object.values(sizes.crags).length === 4 && Object.values(sizes.crags).every(s => s.join() === '768,480'), 'all four Crags monster atlases are 768x480');
        check(await page.evaluate(() => Field.slimes.length > 0 && Field.cragSprites.meta.kinds.join() === 'wisp,spider,wraith,golem'), 'the world lists its monsters');
      }
      check(page.errors.length === 0, `${cls}: no page errors ${page.errors.join('; ')}`);
      await page.context().close();
    }
    // The stub: tiny, still, and different for each choice, so tests can still see an equipment change.
    const stub = await enter(true, 'mage', 'StubMage');
    const bare = await figure(stub, 'mage', 'none', 'none'), robed = await figure(stub, 'mage', 'apprentice', 'ash'), other = await figure(stub, 'mage', 'runic', 'crystal');
    check(bare.visible > 0 && bare.visible < 200, `the stub figure is tiny (${bare.visible} pixels)`);
    check(robed.hash !== bare.hash && other.hash !== robed.hash, 'each armour and weapon still changes the stub pixels');
    const still = await stub.evaluate(() => { const s = valhalla.mage, sum = c => { const d = s.frame(c, 3, 2).getContext('2d').getImageData(0, 0, 256, 256).data; let h = 0; for (let i = 3; i < d.length; i += 4) h = (h * 31 + d[i]) >>> 0; return h; }; return new Set(['idle', 'walk', 'attack', 'hurt', 'die'].map(sum)).size; });
    check(still === 1, 'the stub has no animation: every clip is the same picture');
    check(await stub.evaluate(() => Field.beetleSprites.meta.kinds.join() === 'beetle' && Field.slimes.length > 0), 'enemy stubs keep the real kind lists');
    check(stub.errors.length === 0, 'the stub run has no page errors: ' + stub.errors.join('; '));
    console.log(`real sprites: ${checks} checks passed`);
  } finally {
    await browser.close().catch(() => {});
    if (server && server.exitCode === null) { const exited = new Promise(r => server.once('exit', r)); server.kill('SIGTERM'); await timeout(exited, 7000, 'shutdown').catch(() => server.kill('SIGKILL')); }
    fs.rmSync(dir, { recursive: true, force: true });
  }
})().catch(error => { console.error(error); console.error(logs.slice(-1500)); process.exit(1); });
