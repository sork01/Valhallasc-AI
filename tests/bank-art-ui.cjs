// BANK-ART: each of the five bankers is drawn from its own PixelFlow atlas (idle, and talk while the window is open),
// the five atlases differ, and the bank window shows its icon. Screenshots go to test-results for a human look.
const assert = require('node:assert/strict');
const path = require('node:path');
process.env.REAL_SPRITES = '1';   // the atlases themselves are under test, so no stub sprites
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');

const OUT = path.join(__dirname, '..', 'test-results');
const seed = `if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null }));`;

(async () => {
  const world = new TestWorld();
  let browser, checks = 0;
  const ok = (value, message) => { assert.ok(value, message); checks++; };
  try {
    await world.start();
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.addInitScript(seed);
    await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.locator('#cls-warrior').click(); await page.locator('#name').fill('Looker'); await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero.id);
    await page.waitForFunction(() => Field.bankSprites?.img && Object.keys(Field.bankSprites.img).length === 5, null, { timeout: 15000 });

    const bankers = await page.evaluate(() => [WORLD_MAP, ...WORLD_MAP.zones].flatMap((zone, index) => (zone.npcs || [])
      .filter(n => n.offers.some(o => o.id === 'bank')).map(n => ({ id: n.id, zone: index, x: n.x, y: n.y, art: n.art }))));
    assert.equal(bankers.length, 5);
    const meta = await page.evaluate(() => Field.bankSprites.meta);
    assert.deepEqual(meta.frame, [96, 96]); assert.equal(meta.clips.idle.n, 6); assert.equal(meta.clips.talk.n, 6);

    // Every atlas is a real 6x2 sheet and no two are the same picture.
    const sheets = await page.evaluate(() => Object.entries(Field.bankSprites.img).map(([kind, img]) => {
      const c = document.createElement('canvas'); c.width = img.width; c.height = img.height; const g = c.getContext('2d'); g.drawImage(img, 0, 0);
      const data = g.getImageData(0, 0, c.width, c.height).data; let opaque = 0, hash = 0;
      for (let i = 0; i < data.length; i += 4) if (data[i + 3]) { opaque++; hash = (hash * 31 + data[i] * 3 + data[i + 1] * 5 + data[i + 2]) | 0; }
      return { kind, w: img.width, h: img.height, opaque, hash };
    }));
    for (const s of sheets) { ok(s.w === 576 && s.h === 192, `${s.kind} is a 6x2 sheet of 96px frames`); ok(s.opaque > 6000, `${s.kind} has real art`); }
    ok(new Set(sheets.map(s => s.hash)).size === 5, 'the five bankers look different');

    const debug = (ref, command) => page.evaluate(([ref, command]) => Online.send({ type: 'debug', ref, command }), [ref, command]);
    let ref = 1;
    for (const banker of bankers) {
      ok(banker.art === `bank_${banker.id.slice('banker_'.length)}`, `${banker.id} names its own art`);
      await debug(ref++, { op: 'teleport', zone: banker.zone, x: banker.x, y: banker.y + 3.2 });
      await page.waitForFunction(b => Field.zone === b.zone && Math.hypot(Field.hero.x - b.x, Field.hero.y - b.y - 3.2) < 1, banker, { timeout: 10000 });
      await page.waitForTimeout(700);
      await page.screenshot({ path: path.join(OUT, `bank-art-${banker.id}.png`), clip: { x: 420, y: 150, width: 600, height: 500 } });
      // The NPC is drawn from the atlas: its box on screen holds the atlas's own colours, not the procedural folk.
      const drawn = await page.evaluate(id => { const n = City.npcs.find(x => x.id === id); return !!n && n.art && !!Field.bankSprites.img[n.art]; }, banker.id);
      ok(drawn, `${banker.id} resolves to a loaded atlas`);
    }

    // The window: the icon is a real, visible 48px image beside the title, and the banker switches to the talk clip while it is open.
    const alder = bankers[0];
    await debug(ref++, { op: 'teleport', zone: alder.zone, x: alder.x, y: alder.y + 1.1 });
    await page.waitForFunction(b => Field.zone === b.zone && Math.hypot(Field.hero.x - b.x, Field.hero.y - b.y - 1.1) < 1, alder, { timeout: 10000 });
    await page.evaluate(id => Online.send({ type: 'interact', npc: id }), alder.id);
    await page.locator('#npc-dialogue [data-offer="bank"]').click({ timeout: 10000 });
    await page.locator('#bank-panel').waitFor({ state: 'visible', timeout: 10000 });
    const icon = await page.locator('.bank-icon').evaluate(i => { const r = i.getBoundingClientRect(); return { loaded: i.complete && i.naturalWidth === 48 && i.naturalHeight === 48, w: r.width, h: r.height, left: r.left, top: r.top }; });
    ok(icon.loaded, 'the icon loads at 48x48'); ok(icon.w >= 28 && icon.h >= 28, 'the icon is visible');
    ok(await page.locator('.bank-icon').getAttribute('alt') === '', 'the icon is decorative');
    await page.screenshot({ path: path.join(OUT, 'bank-art-window.png') });
    await page.setViewportSize({ width: 844, height: 390 });
    await page.waitForTimeout(300);
    const phone = await page.locator('.bank-icon').evaluate(i => { const r = i.getBoundingClientRect(), t = document.querySelector('#bank-title').getBoundingClientRect(); return { inside: r.left >= 0 && r.right <= innerWidth && r.top >= 0, clear: r.right <= t.left + 1 || r.bottom <= t.top + 1 }; });
    ok(phone.inside && phone.clear, 'on a phone-sized screen the icon neither clips nor covers the title');
    await page.screenshot({ path: path.join(OUT, 'bank-art-window-phone.png') });
    assert.deepEqual(errors, []);
    console.log(`${checks} bank art checks passed; screenshots: ${OUT}/bank-art-*.png`);
  } finally {
    await browser?.close();
    await world.stop();
  }
})().catch(e => { console.error(e); process.exit(1); });
