const assert = require('node:assert/strict');
const { chromium } = require('./lib/playwright.cjs');
const { debug, requireMemoryLimit, replace } = require('./lib/touch.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');

requireMemoryLimit();
const world = new TestWorld();
world.startLevel = 20;
const mobile = process.env.TOUCH === '1';
const gnome = process.env.GNOME === '1';

(async () => {
  await world.start();
  const browser = await chromium.launch({ headless: true });
  try {
    const viewport = mobile ? { width: 844, height: 390 } : { width: 1280, height: 800 };
    const page = await browser.newPage({ viewport, isMobile: mobile, hasTouch: mobile, reducedMotion: 'reduce' });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    if (process.env.MUTATE === 'buy') {
      await replace(page, 'shop.js', 'quantity: input.valueAsNumber', 'quantity: 1');
    }
    if (process.env.MUTATE === 'quote') {
      await replace(page, 'shop.js', 'cost:quote ??', 'cost:null ??');
    }
    if (process.env.MUTATE === 'compare') {
      await replace(page, 'inventory.js', 'const candidate = value(candidateStats), equipped = value(wornStats);',
        'const candidate = value(wornStats), equipped = value(wornStats);');
    }
    await page.addInitScript(() => {
      window.AudioContext = window.webkitAudioContext = undefined;
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null }));
    });
    await page.goto(world.url);
    await page.locator('#start').click();
    await page.locator('#login-guest').click();
    await page.locator('#cls-warrior').click();
    if (gnome) await page.locator('#create-race').selectOption('gnome');
    await page.locator('#name').fill('ShopQuantity');
    await page.locator('#go').click();
    await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
    if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
    await page.evaluate(() => window.Tutorial?.disable?.());
    await debug(page, { op: 'set_gold', gold: 100000 });
    await page.waitForFunction(() => Field.hero.gold === 100000);

    async function visit(id) {
      await page.evaluate(() => City.close());
      const { x, y } = await page.evaluate(id => Field._debug.zones[0].npcs.find(n => n.id === id), id);
      await debug(page, { op: 'teleport', zone: 0, x, y: y + 1 });
      await page.waitForFunction(([x, y]) => Math.hypot(Field.hero.nx - x, Field.hero.ny - y) < 0.5, [x, y + 1]);
      await page.evaluate(id => Field.visitNpc(id), id);
      await page.locator('#npc-offers [data-view="buy"]').click();
      await page.waitForFunction(() => Shop.open && document.querySelector('.merchant-workspace[aria-busy="false"]'));
    }

    async function buy(offer, count) {
      const slot = page.locator(`#merchant-stock [data-offer="${offer}"]`);
      const id = await slot.getAttribute('data-item');
      const unitPrice = Number(await slot.locator('.money').getAttribute('data-copper'));
      if (gnome) {
        const catalogPrice = await page.evaluate(id => Inventory.definition(id).price, id);
        assert.equal(unitPrice, Math.round(catalogPrice * 0.9), 'Gnome stock shows a discounted quote');
      }
      const before = await page.evaluate(id => ({ count: Inventory.quantity(id), gold: Field.hero.gold }), id);
      const quantity = page.locator(`#merchant-stock [data-bulk-offer="${offer}"]`);
      if (mobile) assert.ok((await quantity.boundingBox()).width >= 43.5, 'Quantity has a touch-sized target');
      await quantity.click();
      const dialog = page.locator('#buy-quantity');
      const input = dialog.locator('input');
      const max = Number(await input.getAttribute('max'));
      await dialog.getByRole('button', { name: 'Max', exact: true }).click();
      assert.equal(await input.inputValue(), String(max));
      const submit = dialog.getByRole('button', { name: 'Buy', exact: true });
      await input.fill('0');
      assert.ok(await submit.isDisabled(), 'Zero quantity cannot be purchased');
      await input.fill(String(count));
      assert.equal(Number(await dialog.locator('.money').getAttribute('data-copper')), unitPrice * count);
      const bounds = await dialog.boundingBox();
      assert.ok(bounds.y >= 0 && bounds.y + bounds.height <= viewport.height, 'Purchase dialog fits vertically');
      await submit.click();
      await page.waitForFunction(() => !document.querySelector('.merchant-workspace[aria-busy="true"]'));
      assert.equal(await page.evaluate(id => Inventory.quantity(id), id), before.count + count, `Order adds exactly ${count} ${id}`);
      await page.waitForFunction(gold => Field.hero.gold === gold, before.gold - unitPrice * count);
      return id;
    }

    await visit('apothecary');
    await buy('buy_health_potion', 12);
    console.log('A seller-only shop accepts one order for twelve potions at the quoted total');
    await visit('smith');
    const weapon = await buy('buy_green_weapon_warrior', 2);
    const cells = page.locator(`#inventory-list [data-item="${weapon}"] .item-tile`);
    assert.equal(await cells.count(), 2, 'Each bought weapon occupies its own bag cell');
    await cells.first().hover();
    const comparison = page.locator('#item-tooltip .item-comparison');
    const attack = comparison.locator('[data-stat="attack"]');
    assert.ok(await attack.isVisible(), 'Hover opens the side-by-side stat table');
    const values = await attack.locator('td').allTextContents();
    const delta = Number(values[0].match(/\(([^)]+)\)/)[1]);
    assert.equal(delta, Number((parseFloat(values[0]) - Number(values[1])).toFixed(1)));
    assert.ok(delta > 0 && await attack.locator('.stat-gain').count() === 1, 'Weapon improvement shows a positive colored delta');

    const duplicate = await page.evaluate(() => {
      const look = { ...Field.hero.look, warriorWeapon: 'sword' };
      const worn = Inventory.legacyPiece('weapon', look);
      const original = { item: worn.id, rarity: worn.rarity, attack: 20, defense: 8, rank: 1 };
      const spare = { ...original, id: 102, attack: 25, defense: 4, rank: 2 };
      Inventory.update([{ item: worn.id, quantity: 2 }], look, {}, [], [{ ...original, id: 101 }, spare]);
      Inventory.render(document.getElementById('inventory-list'));
      const tile = document.querySelector('#inventory-list [data-key$="@102"] .item-tile');
      tile.dispatchEvent(new PointerEvent('pointerenter'));
      const cells = stat => [...document.querySelectorAll(`#item-tooltip [data-stat="${stat}"] td`)].map(cell => cell.textContent);
      return { attack: cells('attack'), defense: cells('defense'), loss: document.querySelector('#item-tooltip .stat-loss')?.textContent };
    });
    assert.deepEqual(duplicate, { attack: ['27 (+6.2)', '20.8'], defense: ['4.3 (-4)', '8.3'], loss: '(-4)' }, 'Same-ID pieces use their own ranks and show both gains and losses');
    assert.deepEqual(errors, []);
    console.log('Two physical weapons arrive, and hovering compares both exact copies with the worn item');
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
}).finally(() => world.stop());
