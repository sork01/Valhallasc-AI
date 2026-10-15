'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const root = path.resolve(__dirname, '..');
(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    await page.setContent('<div id="inventory-list"></div><div id="bag-details"></div><div id="npc-inventory"></div><div id="equipped"></div><div id="loot-rolls"></div>');
    await page.addStyleTag({ path: path.join(root, 'client/online.css') });
    await page.addScriptTag({ path: path.join(root, 'client/items.js') });
    await page.evaluate(() => {
      window.Field = { hero: { level: 100 }, setPaused() {} };
      window.Online = { connected: true, send() { return true; } };
    });
    await page.addScriptTag({ path: path.join(root, 'client/inventory.js') });
    await page.addScriptTag({ path: path.join(root, 'client/rolls.js') });
    const data = await page.evaluate(() => {
      const piece = WORLD_ITEMS.find(i => i.source === 'undervault' && i.class === 'mage' && i.kind === 'weapon');
      const copy = { id: 42, item: piece.id, rarity: 'epic', attack: 30, defense: 5, bonusStats: piece.bonusStats, rolledStats: {stamina: 7}, rank: 0 };
      Inventory.update([{item:piece.id,quantity:1}], {class:'mage',mageArmor:'none',mageWeapon:'none'}, {}, [], [copy]);
      Inventory.render(document.getElementById('inventory-list'));
      Inventory.renderShop({id:'merchant',buys:['gear']}, document.getElementById('npc-inventory'));
      Rolls.onPacket({op:'start',id:13,item:piece.id,gear:copy,seconds:10,need:true});
      return {piece:piece.id, sell:piece.sell};
    });
    const bag = page.locator(`#inventory-list [data-item="${data.piece}"]`);
    assert.equal(await bag.getAttribute('data-rarity'), 'epic');
    assert.match(await bag.textContent(), /Epic/);
    await bag.locator('button').hover();
    assert.equal(await page.locator('#item-tooltip').getAttribute('data-rarity'), 'epic');
    assert.match(await page.locator('#item-tooltip').textContent(), /Epic/);
    assert.match(await page.locator('#npc-inventory [data-sell="one"]').textContent(), new RegExp(`${data.sell * 2} gold`));
    assert.equal(await page.locator('#loot-rolls [data-roll="13"]').getAttribute('data-rarity'), 'epic');
    await page.evaluate(id => {
      const piece = WORLD_ITEMS.find(i => i.id === id);
      const copy = { id: 42, item: id, rarity: 'epic', attack: 30, defense: 5, bonusStats: piece.bonusStats, rolledStats: {stamina: 7}, rank: 0 };
      Inventory.update([{item:id,quantity:1}], {class:'mage',mageArmor:'none',mageWeapon:piece.variant}, {}, [], [copy]);
      Inventory.renderEquipped(document.getElementById('equipped'));
    }, data.piece);
    assert.equal(await page.locator('#equipped [data-slot="hands"]').getAttribute('data-rarity'), 'epic');
    assert.match(await page.locator('#equipped [data-slot="hands"] .gear-icon').getAttribute('aria-label'), /Epic copy #42/);
    console.log('epic drop UI: 6 checks passed');
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
