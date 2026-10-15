// Display-only trader packets exercise bag tier presentation; Rust covers purchase and pickup.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-bag-tiers-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe' }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => { if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })); });
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-mage').click(); await page.locator('#name').fill('BagTierMage'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.mageSprites, null, { timeout: 60000 });
  const show = (level, gold, bags) => page.evaluate(({ level, gold, bags }) => {
    const npc = City.npcs.find(n => n.offers.some(o => o.bag));
    City.dialogue({ npc, level, gold, bags, inventory: [], equipment: {}, quests: [], notice: '' });
  }, { level, gold, bags });
  await show(1, 5000, []);
  await page.locator('#npc-offers [data-view="bags"]').click();
  check(await page.locator('#npc-offers [data-bag]').count() === 10, 'Trader lists all ten expansion bag tiers');
  check(await page.locator('#npc-offers .bag-shop-heading').textContent().then(t => t.includes('level 10') && t.includes('8 slots') && t.includes('1,500 gold')), 'Trader shows next tier, level, slots and price');
  check(await page.locator('#npc-offers [data-bag="adventurer_satchel"]').isDisabled() && await page.locator('#npc-offers [data-bag="linen_satchel"]').isEnabled(), 'Higher tiers are locked at level one');
  await show(20, 5000, ['linen_satchel']);
  check(await page.locator('#npc-offers [data-bag="linen_satchel"]').textContent().then(t => t.includes('Owned ×1') && t.includes('Adds 6 slots now')), 'Fitted tier is marked owned and shows its slot gain');
  check(await page.locator('#npc-offers [data-bag="trail_pack_l20"]').isEnabled() && await page.locator('#npc-offers [data-bag="ranger_pack_l30"]').isDisabled(), 'The level in the reply controls tier unlocks');
  await show(50, 100000, ['linen_satchel', 'adventurer_satchel', 'trail_pack_l20', 'ranger_pack_l30']);
  check(await page.locator('#npc-offers [data-bag="linen_satchel"]').isDisabled(), 'A full set of four refuses a same-size bag');
  check(await page.locator('#npc-offers [data-bag="traveler_pack"]').textContent().then(t => t.includes('Adds 10 slots now')), 'Upgrade preview subtracts the smallest fitted bag');
  check(await page.locator('#npc-offers [data-bag="traveler_pack"]').isEnabled(), 'A larger bag can replace the smallest fitted bag');
  await page.evaluate(() => City.close());
  check(await page.evaluate(() => SystemLog.lines({ kind:'itemPickup', actor:Online.id, item:'trail_pack_l20', name:'Trail Pack', quantity:1 }, Online.id)[0][0].includes('+10 bag slots')), 'Bag pickup message names the gained slots');
  await page.evaluate(() => Inventory.update([{ item:'trail_pack_l20', quantity:1 }], Field.hero.look, {}, [], []));
  await page.keyboard.press('i');
  await page.locator('#inventory-list [data-item="trail_pack_l20"] button').hover();
  check(await page.locator('#item-tooltip').textContent().then(t => t.includes('10 extra slots') && t.includes('Requires level 20')), 'Bag tooltip shows slot count and level');
  check(await page.locator('#inventory-list [data-item="trail_pack_l20"] svg').count() === 1, 'Bag has its tier icon in inventory');
  check(errors.length === 0, `No runtime errors: ${errors.join('; ')}`);
  console.log(`${checks} bag tier UI checks passed`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
});
