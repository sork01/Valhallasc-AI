// Private browser check of authoritative set counts and display-only cast effects.
const assert = require('node:assert/strict');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');

(async () => {
  const world = new TestWorld();
  let browser;
  try {
    await world.start();
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
    await page.goto(world.url);
    await page.locator('#start').click();
    await page.locator('#login-guest').click();
    await page.locator('#cls-warrior').click();
    await page.locator('#name').fill('SetTester');
    await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero.id && Field.warriorSprites, null, { timeout: 60000 });
    await page.evaluate(() => Online.send({ type: 'debug', ref: 1, command: { op: 'set_level', level: 99 } }));
    await page.waitForFunction(() => Field.hero.level === 99);

    const pieces = await page.evaluate(() => ['armor', 'weapon', 'headgear', 'shoulders', 'gloves', 'pants', 'necklace', 'accessory'].map(kind => {
      const item = WORLD_ITEMS.find(i => i.source === 'undervault' && i.kind === kind && (!i.class || i.class === 'warrior'));
      if (!item) throw Error(`Undervault has no ${kind}`);
      return { id: item.id, slot: { armor: 'chest', weapon: 'hands', accessory: 'accessory1' }[kind] || kind };
    }));
    for (const [index, piece] of pieces.entries()) {
      await page.evaluate(({ index, piece }) => Online.send({ type: 'debug', ref: index + 2, command: { op: 'give_item', item: piece.id, quantity: 1 } }), { index, piece });
      await page.waitForFunction(id => Field.hero.inventory?.some(stack => stack.item === id), piece.id);
    }
    await page.evaluate(pieces => Online.send({ type: 'equip', slots: Object.fromEntries(pieces.map(piece => [piece.slot, piece.id])) }), pieces);
    await page.waitForFunction(() => Field.hero.setCounts?.undervault === 8, null, { timeout: 10000 });
    await page.keyboard.press('e');
    const panel = page.locator('#character-sets');
    assert.match(await panel.textContent(), /Undervault · 8\/8/);
    assert.equal(await panel.locator('.set-tier[data-active="true"]').count(), 4);
    assert.match(await page.locator('#toast').textContent(), /8-piece bonus active/);

    // These events are display fixtures: combat and set eligibility are checked in Rust.
    const visuals = await page.evaluate(() => {
      const event = { kind: 'skill', actor: Field.hero.id, x: Field.hero.x, y: Field.hero.y, fx: 1, fy: 0, value: 1, points: [] };
      let n = Field._debug.effects.length;
      Field._debug.event({ ...event, skill: 'cleave', setDouble: true });
      const doubled = Field._debug.effects.slice(n).some(fx => fx.kind === 'skNova' && fx.r === 2.2);
      n = Field._debug.effects.length;
      Field._debug.event({ ...event, skill: 'charge', setSignature: 'undervault' });
      const signature = Field._debug.effects.slice(n).some(fx => fx.kind === 'skAura');
      return { doubled, signature };
    });
    assert.deepEqual(visuals, { doubled: true, signature: true });

    await page.evaluate(() => Online.send({ type: 'equip', slots: { necklace: 'none' } }));
    await page.waitForFunction(() => Field.hero.setCounts?.undervault === 7);
    assert.equal(await panel.locator('.set-tier[data-active="true"]').count(), 3);
    assert.equal(await panel.locator('.set-tier[data-active="false"]').count(), 1);
    assert.match(await page.locator('#toast').textContent(), /8-piece bonus lost/);
    const necklace = page.locator(`#inventory-list [data-item="${pieces.find(p => p.slot === 'necklace').id}"] button`);
    await necklace.hover();
    assert.match(await page.locator('#item-tooltip').textContent(), /Undervault · 7\/8/);
    assert.deepEqual(errors, []);
    console.log('Set UI: 9 private browser checks passed');
  } finally {
    await browser?.close();
    await world.stop();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
