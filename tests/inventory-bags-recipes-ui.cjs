const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');

const client = process.env.INVENTORY_CANDIDATE || path.join(__dirname, '../client');
const recipes = [
  'enchant_recipe_double_tap',
  'smith_plan_meadowguard_gloves',
  'alchemy_trailwind_potion_formula',
];
const bag = 'trail_pack_l20';

(async () => {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    await page.setContent('<div id="inventory-list"></div><div id="bag-details"></div><button id="enchanting-toggle"></button><div id="enchanting-panel" hidden></div>');
    await page.addStyleTag({ path: path.join(client, 'online.css') });
    await page.evaluate(() => {
      window.used = [];
      window.Field = { hero: { level: 20 }, useItem: (...args) => window.used.push(args) };
      window.Online = { connected: true };
    });
    for (const file of ['items.js', 'money.js', 'blacksmithing-data.js', 'alchemy-data.js', 'enchanting-data.js', 'enchanting.js', 'inventory.js']) {
      await page.addScriptTag({ path: path.join(client, file) });
    }
    await page.evaluate(ids => {
      const stacks = ids.map(item => ({ item, quantity: 1 }));
      window.showBags = bags => {
        Inventory.update(stacks, { class: 'warrior' }, {}, bags);
        Inventory.render(document.getElementById('inventory-list'));
      };
      window.showBags([]);
    }, [...recipes, 'enchant_scroll_double_tap', bag]);

    const tile = id => page.locator(`[data-item="${id}"] .item-tile`);
    const mark = page.locator('#item-tooltip .item-restriction').filter({ hasText: 'Already learned' });
    await tile(recipes[0]).hover();
    assert.equal(await mark.count(), 0, 'an unlearned recipe has no learned label');
    await page.evaluate(() => {
      Field.hero.learnedRecipes = {
        enchanting: ['double_tap'],
        blacksmithing: ['smith_gear_meadowguard_gloves'],
        alchemy: ['alchemy_trailwind_potion'],
      };
    });
    for (const id of [...recipes.slice(1), recipes[0]]) {
      await tile(id).hover();
      assert.equal(await mark.textContent({ timeout: 4000 }), 'Already learned');
      assert.equal(await mark.evaluate(node => getComputedStyle(node).color), 'rgb(224, 135, 125)');
    }
    await tile('enchant_scroll_double_tap').hover();
    assert.equal(await mark.count(), 0, 'a consumable scroll is still usable after learning the recipe');

    await tile(bag).click();
    await page.getByRole('button', { name: 'Fit Bag', exact: true }).click();
    assert.deepEqual(await page.evaluate(() => window.used), [[bag, undefined]], 'fit uses the loose bag in an empty slot');
    await page.evaluate(() => window.showBags(['linen_satchel', 'adventurer_satchel', 'linen_satchel', 'linen_satchel']));
    await tile(bag).click();
    assert.equal(await page.getByRole('button', { name: 'Fit Bag', exact: true }).count(), 0);
    const replace = page.getByRole('button', { name: 'Replace Bag', exact: true });
    assert(await replace.isDisabled(), 'replacement waits for a slot choice');
    await page.getByRole('combobox', { name: 'Choose a bag to replace' }).selectOption('1');
    await replace.click();
    assert.deepEqual(await page.evaluate(() => window.used.at(-1)), [bag, 1], 'replacement names the selected bag slot');
    console.log('Inventory UI checks passed for bag fitting, bag replacement and learned recipe tooltips.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
