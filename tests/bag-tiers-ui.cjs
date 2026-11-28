// Display-only trader packets exercise bag tier presentation; Rust covers purchase and pickup.
// The bag tiers are sold on the merchant's Buy tab (stock grid, ten per page), so each check opens that tab
// and walks the pages to find the offer it needs.
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
  // The merchant window closes when the hero walks away (Shop.onSnapshot), so stand the hero beside the bag trader first.
  const trader = await page.evaluate(() => { const n = City.npcs.find(x => x.offers.some(o => o.bag)); return { id: n.id, zone: Field.zone || 0, x: n.x, y: n.y }; });
  await page.evaluate(t => Online.send({ type: 'debug', command: { op: 'teleport', zone: t.zone, x: t.x, y: t.y + 1.1 } }), trader);
  await page.waitForFunction(t => Field.zone === t.zone && Math.hypot(Field.hero.nx - t.x, Field.hero.ny - t.y - 1.1) < 1.5, trader, { timeout: 20000 });
  // Shop buyability uses the server's gold (Shop.onPacket), so the real hero needs the purse as well as the fake packet.
  await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'set_gold', gold: 100000 } }));
  await page.waitForTimeout(500);
  const show = (level, gold, bags) => page.evaluate(({ level, gold, bags }) => {
    const npc = City.npcs.find(n => n.offers.some(o => o.bag));
    City.close();   // back to the greeting, so the Buy row is offered again
    City.dialogue({ npc, level, gold, bags, inventory: [], equipment: {}, quests: [], notice: '' });
  }, { level, gold, bags });
  // Open the Buy tab and return the offer slot for `offer`, paging through the stock grid if needed.
  const openBuy = async () => {
    await page.locator('#npc-offers [data-view="buy"]').click();
    await page.waitForFunction(() => Shop.open && !!document.querySelector('#merchant-stock'), null, { timeout: 15000 }).catch(async e => { throw new Error(`${e.message}; page errors: ${errors.join(' | ')}; dialogue: ${(await page.locator('#npc-dialogue').innerText().catch(() => '')).slice(0, 300)}`); });
  };
  const slot = async offer => {
    for (let guard = 0; guard < 10; guard++) {
      const loc = page.locator(`#merchant-stock [data-offer="${offer}"]`);
      if (await loc.count()) return loc;
      const next = page.locator('.merchant-pages button[aria-label="Next page"]');
      if (await next.isDisabled()) break;
      await next.click();
    }
    throw new Error(`no stock slot for ${offer}`);
  };
  const bagOffers = ['satchel', 'bag_l10', 'bag_l20', 'bag_l30', 'bag_l40', 'bag_l50', 'bag_l60', 'bag_l70', 'bag_l80', 'bag_l90'];

  await show(1, 5000, []);
  await openBuy();
  const seen = [];
  for (const offer of bagOffers) seen.push(await (await slot(offer)).count());
  check(seen.every(n => n === 1), 'Merchant lists all ten expansion bag tiers');
  check(await (await slot('satchel')).isEnabled() && await (await slot('bag_l10')).isDisabled(), 'Higher tiers are locked at level one');
  check(await (await slot('satchel')).textContent().then(t => t.includes('+6 slots') && t.includes('Lv 1')), 'Linen Satchel shows its slot gain and level');
  await show(20, 5000, ['linen_satchel']);
  await openBuy();
  check(await (await slot('bag_l20')).isEnabled() && await (await slot('bag_l30')).isDisabled(), 'The level in the reply controls tier unlocks');
  check(await (await slot('bag_l20')).textContent().then(t => t.includes('+10 slots') && t.includes('Lv 20')), 'Trail Pack shows +10 slots at level 20');
  // The shop trusts the fitted bags in the server's reply, so really fill all four slots.
  await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'set_level', level: 50 } }));
  for (const offer of ['satchel', 'bag_l10', 'bag_l20', 'bag_l30']) {
    await page.waitForTimeout(600);
    await page.evaluate(([npc, offer]) => Online.send({ type: 'interact', npc, offer }), [trader.id, offer]);
  }
  await page.waitForFunction(() => Field.hero.bags?.length === 4, null, { timeout: 15000 });
  await show(50, 100000, ['linen_satchel', 'adventurer_satchel', 'trail_pack_l20', 'ranger_pack_l30']);
  await openBuy();
  check(await (await slot('satchel')).isDisabled(), 'A full set of four refuses a same-size bag');
  check(await (await slot('bag_l50')).textContent().then(t => t.includes('+16 slots')), 'Traveler Pack shows its full slot gain');
  check(await (await slot('bag_l50')).isEnabled(), 'A larger bag can replace the smallest fitted bag');
  await page.evaluate(() => City.close());
  check(await page.evaluate(() => SystemLog.lines({ kind:'itemPickup', actor:Online.id, item:'trail_pack_l20', name:'Trail Pack', quantity:1 }, Online.id)[0][0] === 'You pick up Trail Pack.'), 'Bag pickup reports the loose item');
  check(errors.length === 0, `No runtime errors: ${errors.join('; ')}`);
  console.log(`${checks} bag tier UI checks passed`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
});
