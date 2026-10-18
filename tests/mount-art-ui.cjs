// Real art for the five mounts (MOUNT-HORSE redesign, MOUNT-GRYPHON/LIZARD/RAPTOR/SABERTOOTH): every mount is drawn from
// its atlas under a rider of each class, in every facing and both gaits, and the rider sits in the saddle. Run with
// REAL_SPRITES=1 PLAYWRIGHT_BROWSERS_PATH=<dir with chromium-headless-shell>; SHOTS=<dir> also writes screenshots.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');

const MOUNTS = ['horse', 'raptor', 'lizard', 'sabertooth', 'gryphon'];
const CLASSES = (process.env.CLASSES || 'warrior,mage').split(',');
const SHOTS = process.env.SHOTS;

(async () => {
  assert.equal(process.env.REAL_SPRITES, '1', 'this suite needs the real artwork: REAL_SPRITES=1');
  if (SHOTS) fs.mkdirSync(SHOTS, { recursive: true });
  const world = new TestWorld();
  let browser;
  try {
    await world.start();
    browser = await chromium.launch({ headless: true });
    const errors = [];
    for (const cls of CLASSES) {
      const page = await browser.newPage({ viewport: { width: 900, height: 600 }, reducedMotion: 'reduce' });
      page.on('pageerror', e => errors.push(e.message));
      await page.addInitScript(() => { if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })); });
      await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
      await page.locator(`#cls-${cls}`).click(); await page.locator('#name').fill('Rider' + cls.slice(0, 3)); await page.locator('#go').click({ timeout: 90000 });
      await page.waitForFunction(() => Online.connected && Field.hero.id, null, { timeout: 90000 });
      await page.evaluate(() => { Online.send({ type: 'debug', ref: 1, command: { op: 'set_level', level: 99 } }); for (const [i, m] of ['horse', 'raptor', 'lizard', 'sabertooth', 'gryphon'].entries()) Online.send({ type: 'debug', ref: 10 + i, command: { op: 'give_mount', mount: m } }); });
      await page.waitForFunction(() => Field.hero.mounts?.length === 5, null, { timeout: 15000 });
      const meta = await page.evaluate(async () => (await (await fetch('assets/mounts_sprites.txt')).text()));
      const info = JSON.parse(meta);
      assert.deepEqual(Object.keys(info.mounts).sort(), [...MOUNTS].sort(), 'the atlas lists every mount');
      for (const id of MOUNTS) {
        const m = info.mounts[id];
        assert.equal(m.clips.idle.n, 4); assert.equal(m.clips.run.n, 8); assert.equal(m.bob.run.length, 8);
        assert.ok(Object.keys(m.sprites).length === 16, `${id}: sixteen PixelFlow sprites (2 clips x 8 facings)`);
        await page.evaluate(id => Online.send({ type: 'select_mount', mount: id }), id);
        await page.waitForFunction(id => Field.hero.mount === id, id, { timeout: 10000 });
        await page.evaluate(() => { if (!Field.hero.mounted) Online.send({ type: 'mount', mounted: true }); });
        await page.waitForFunction(id => Field.hero.mounted && Field.hero.mount === id, id, { timeout: 10000 });
        await page.waitForFunction(id => MountArt.ready(id), id, { timeout: 15000 });
        // every facing and both gaits, drawn through the class sprite itself: eight different pictures for the eight facings, and
        // the gait and the mount both change the picture against the same figure on foot
        const sheet = await page.evaluate(async ([id, cls]) => {
          const Sprite = { warrior: window.WarriorSprite, mage: window.MageSprite, assassin: window.AssassinSprite, priest: window.PriestSprite, hunter: window.HunterSprite }[cls];
          const sprite = await Sprite.load({ gender: 'male' });
          const canvas = document.createElement('canvas'); canvas.width = 8 * 220; canvas.height = 3 * 260;
          const g = canvas.getContext('2d'); g.fillStyle = '#486c48'; g.fillRect(0, 0, canvas.width, canvas.height);
          const vec = [0, 1, 2, 3, 4, 5, 6, 7].map(d => { const t = -d * Math.PI / 4; return [(Math.cos(t) + Math.sin(t)) / 2, (Math.cos(t) - Math.sin(t)) / 2]; });   // fx, fy that MageSprite.direction maps to facing d
          const hashes = [];
          for (const [row, state] of [[0, { mounted: true, moving: false }], [1, { mounted: true, moving: true }], [2, { mounted: false, moving: false }]]) {
            for (let d = 0; d < 8; d++) {
              g.save(); g.translate(d * 220 + 110, row * 260 + 190);
              sprite.draw(g, { ...state, mount: id, mountTint: 0, walk: 3, fx: vec[d][0], fy: vec[d][1], x: 0, y: 0 }, 1.1, 1.3);
              g.restore();
              hashes.push(Array.from(g.getImageData(d * 220, row * 260, 220, 260).data).reduce((h, v, i) => (h * 31 + v + i) >>> 0, 7));
            }
          }
          return { url: canvas.toDataURL('image/png'), hashes, facings: [0, 1, 2, 3, 4, 5, 6, 7].map(d => sprite.constructor.direction(vec[d][0], vec[d][1])) };
        }, [id, cls]);
        assert.deepEqual(sheet.facings, [0, 1, 2, 3, 4, 5, 6, 7], 'the test vectors cover the eight facings in order');
        const [idle, run, bare] = [0, 1, 2].map(r => sheet.hashes.slice(r * 8, r * 8 + 8));
        assert.equal(new Set(idle).size, 8, `${id}: eight different idle facings`);
        assert.equal(new Set(run).size, 8, `${id}: eight different run facings`);
        assert.ok(idle.every((h, i) => h !== run[i] && h !== bare[i]), `${id}: gait and mount both change the picture`);
        if (SHOTS) fs.writeFileSync(path.join(SHOTS, `sheet_${cls}_${id}.png`), Buffer.from(sheet.url.split(',')[1], 'base64'));
        if (SHOTS) {
          for (const [name, fx, fy, moving] of [['S', -1, 1, false], ['E', 1, 1, true], ['N', 1, -1, true], ['W', -1, -1, false]]) {
            await page.evaluate(([fx, fy, moving]) => { Field.hero.fx = fx; Field.hero.fy = fy; Field.hero.moving = moving; Field.hero.walk = 2; }, [fx, fy, moving]);
            await page.waitForTimeout(120);
            await page.screenshot({ path: path.join(SHOTS, `${cls}_${id}_${name}.png`), clip: { x: 350, y: 180, width: 200, height: 240 } });
          }
        }
        await page.evaluate(() => Online.send({ type: 'mount', mounted: false }));
        await page.waitForFunction(() => !Field.hero.mounted, null, { timeout: 10000 });
      }
      await page.close();
    }
    assert.deepEqual(errors, [], 'no page errors while riding every mount');
    console.log('All five mounts load their art and draw under', CLASSES.join(' and '), 'riders');
  } finally {
    await browser?.close(); await world.stop();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
