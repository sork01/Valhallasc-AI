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
// Visible pixels of the idle frame under the current equipment, and a fingerprint of them.
const figure = (page, cls, armor, weapon, extras = {}) => page.evaluate(([cls, armor, weapon, extras]) => {
  const sprite = valhalla[cls], look = { ...sprite.look, head: 'none', shoulders: 'none', gloves: 'none', ...extras, [cls + 'Armor']: armor, [cls + 'Weapon']: weapon };
  sprite.set(look);
  const canvas = sprite.frame('idle', 0, 0), data = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
  let visible = 0, hash = 0;
  for (let i = 0; i < data.length; i += 4) if (data[i + 3]) { visible++; hash = (hash * 31 + data[i] * 3 + data[i + 1] * 5 + data[i + 2] * 7 + i) >>> 0; }
  return { visible, hash, width: canvas.width };
}, [cls, armor, weapon, extras]);

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
      // other tier, and goes away again with 'none'. The Priest has none yet and must ignore them.
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
      check(await page.evaluate(cls => valhalla[cls].portrait().length > 2000, cls), `${cls}: the portrait renders`);
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
