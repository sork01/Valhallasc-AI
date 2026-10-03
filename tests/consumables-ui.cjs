// Food and potions in a real browser: buying from the baker and the apothecary, the Z / X quick slots, the bag's Use
// button, the buff chip and the timing of the healing. Only the starting purse and health are set with test commands
// (they skip farming gold and getting hurt); buying, using and healing all run through the real rules.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium, STUB } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-consumables-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`); return result.structuredContent;
}
const rect = (page, selector) => page.locator(selector).evaluate(n => { const r = n.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom }; });
const overlap = (a, b) => a.l < b.r && b.l < a.r && a.t < b.b && b.t < a.b;
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0' } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => { if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })); });
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('Eater'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites, null, { timeout: 60000 });
  const debug = command => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);
  const hp = () => page.evaluate(() => Field.hero.hp);
  const chat = () => page.locator('#chat-log').innerText();
  await debug({ op: 'set_gold', gold: 100 });
  await page.waitForFunction(() => Field.hero.gold === 100);

  // --- empty slots ---
  const slot = kind => page.locator(`#quickuse [data-kind="${kind}"]`);
  check(await slot('food').count() === 1 && await slot('potion').count() === 1, 'The HUD has a food slot and a potion slot');
  check(await slot('food').getAttribute('data-item') === '' && await slot('food').getAttribute('title').then(t => t.includes('Pip')), 'An empty food slot says where to buy food');
  check(await slot('potion').getAttribute('title').then(t => t.includes('Mira')), 'An empty potion slot says where to buy potions');
  const bar = await rect(page, '#skillbar'), quick = await rect(page, '#quickuse'), tracker = await rect(page, '.chat'), social = await rect(page, '#social-open');
  check(!overlap(quick, bar) && !overlap(quick, tracker) && !overlap(quick, social), `Quick slots overlap no other HUD piece (${JSON.stringify({ quick, bar, tracker })})`);
  check(quick.l >= 0 && quick.b <= 900, 'Quick slots sit inside the stage');

  // --- buying: the baker sells food, the apothecary potions ---
  await page.evaluate(() => Field.visitNpc('baker'));
  await page.locator('#npc-dialogue').waitFor({ state: 'visible', timeout: 60000 });
  check(await page.locator('#npc-offers [data-offer="buy_traveler_stew"]').textContent().then(t => t.includes('100 HP and mana over 8 s') && t.includes('12 gold')), 'The baker lists Traveler\'s Stew with its effect and price');
  check(await page.locator('#npc-offers [data-offer="buy_health_potion"]').count() === 0, 'The baker does not list potions');
  await page.waitForTimeout(600);
  await page.locator('#npc-offers [data-offer="buy_traveler_stew"]').click();
  await page.waitForFunction(() => Inventory.quantity('traveler_stew') === 1 && Field.hero.gold === 88);
  check(await page.locator('#npc-notice').textContent().then(t => t.includes('Bought Traveler')), 'The purchase is confirmed in the dialogue');
  await page.waitForTimeout(600);
  await page.locator('#npc-offers [data-offer="buy_traveler_stew"]').click();
  await page.waitForFunction(() => Inventory.quantity('traveler_stew') === 2 && Field.hero.gold === 76);
  check(await page.locator('#npc-inventory [data-item]').count() === 0, 'The baker sells but does not buy');
  await page.locator('#npc-close').click();
  await page.evaluate(() => Field.visitNpc('apothecary'));
  await page.locator('#npc-dialogue').waitFor({ state: 'visible', timeout: 60000 });
  check(await page.locator('#npc-offers [data-offer="buy_health_potion"]').textContent().then(t => t.includes('100 HP instantly') && t.includes('30 gold')), 'The apothecary lists Health Potion');
  await page.waitForTimeout(600);
  await page.locator('#npc-offers [data-offer="buy_health_potion"]').click();
  await page.waitForFunction(() => Inventory.quantity('health_potion') === 1 && Field.hero.gold === 46);
  await page.waitForTimeout(600);
  await page.locator('#npc-offers [data-offer="buy_health_potion"]').click();
  await page.waitForFunction(() => Inventory.quantity('health_potion') === 2 && Field.hero.gold === 16);
  check(await page.locator('#npc-offers [data-offer="buy_health_potion"]').isDisabled(), 'Without the gold for another, the buy button is disabled');
  await page.locator('#npc-close').click();
  check(await slot('food').textContent().then(t => t.includes('2')) && await slot('potion').textContent().then(t => t.includes('2')), 'The slots show how many of each you carry');
  check(await slot('food').isEnabled() && await slot('potion').isEnabled(), 'Owned items make the slots usable');
  await page.screenshot({ path: path.join(world.artifacts, 'consumables-hud.png') });

  // --- full health: nothing is wasted ---
  await page.keyboard.press('x');
  await page.waitForFunction(() => document.querySelector('#chat-log').innerText.includes('already at full health'));
  check(await page.evaluate(() => Inventory.quantity('health_potion')) === 2, 'A potion is not drunk at full health');

  // --- the potion: instant, then a 60 second cooldown ---
  await debug({ op: 'set_hp', hp: 1 });
  await page.waitForFunction(() => Field.hero.hp <= 3);
  await page.keyboard.press('x');
  await page.waitForFunction(() => Inventory.quantity('health_potion') === 1 && Field.hero.hp >= 100, null, { timeout: 3000 });
  check(await hp() >= 100 && await hp() <= 105, `The potion heals about 100 at once (${await hp()})`);
  check(await slot('potion').isDisabled() && await slot('potion').locator('.skill-cooldown').textContent().then(t => +t >= 58 && +t <= 60), 'The potion slot counts down from about 60');
  check(await page.evaluate(() => Field.hero.potionCd) > 55, 'The server reports the potion cooldown');
  await page.keyboard.press('x');
  check(await page.evaluate(() => Inventory.quantity('health_potion')) === 1, 'A second potion during the cooldown is not drunk');

  // --- the meal: gradual, one at a time ---
  await debug({ op: 'set_hp', hp: 1 });
  await page.waitForFunction(() => Field.hero.hp <= 3);
  await page.keyboard.press('z');
  await page.waitForFunction(() => Inventory.quantity('traveler_stew') === 1);
  const ateAt = Date.now(), early = await hp();
  check(early < 30, `Nothing arrives at once (${early})`);
  await page.waitForFunction(() => Field.hero.buffs.some(b => b.id === 'traveler_stew' && b.kind === 'regen'));
  check(await page.locator('#buff-bar [data-buff="traveler_stew"]').count() === 1 && await page.locator('#buff-bar [data-buff="traveler_stew"]').getAttribute('title').then(t => t.includes('Traveler') && t.includes('100 HP and 100 mana over 8 s')), 'The meal shows in the active effects bar');
  check(await slot('food').isDisabled() && await slot('food').locator('.skill-cooldown').textContent().then(t => +t >= 1 && +t <= 8), 'The food slot counts the meal down');
  await page.keyboard.press('z');
  await page.waitForFunction(() => document.querySelector('#chat-log').innerText.includes('still eating'), null, { timeout: 3000 });
  check(await page.evaluate(() => Inventory.quantity('traveler_stew')) === 1, 'A second meal is refused and kept');
  await page.waitForTimeout(Math.max(0, 4000 - (Date.now() - ateAt)));
  const middle = await hp();
  check(middle > 30 && middle < 80, `About half has arrived after four seconds (${middle})`);
  await page.waitForFunction(() => !Field.hero.buffs.some(b => b.kind === 'regen'), null, { timeout: 8000 });
  const spent = (Date.now() - ateAt) / 1000;
  // Natural regeneration also runs after five quiet seconds, so the exact 100 is pinned by the Rust tests; here it must be at least that.
  check(await hp() >= 98, `The whole 100 HP arrived (${await hp()})`);
  check(spent > 7 && spent < 10.5, `It took about eight seconds (${spent.toFixed(1)})`);
  check(await page.locator('#buff-bar [data-buff="traveler_stew"]').count() === 0, 'The chip leaves when the meal ends');
  check(await slot('food').isEnabled(), 'The food slot is ready again');

  // --- the bag: Use button, right-click, and refusal text ---
  await page.keyboard.press('b');
  check(await page.locator('#equipment').isVisible(), 'B opens the bags');
  await page.locator('#inventory-list [data-item="traveler_stew"] button').click();
  check(await page.locator('#bag-details [data-action="use"]').isVisible() && await page.locator('#bag-details [data-action="equip"]').count() === 0, 'Food offers Use and no Equip');
  check(await page.locator('#bag-details').textContent().then(t => t.includes('100 HP and 100 mana over 8 s')), 'The bag explains the effect');
  await page.locator('#inventory-list [data-item="traveler_stew"] button').hover();
  check(await page.locator('#item-tooltip').textContent().then(t => t.includes('Restores 100 HP and 100 mana over 8 s') && t.includes('double-click to use')), 'The tooltip explains the effect and how to use it');
  await debug({ op: 'set_hp', hp: 1 });
  await page.waitForFunction(() => Field.hero.hp <= 3);
  await page.locator('#bag-details [data-action="use"]').click();
  await page.waitForFunction(() => Inventory.quantity('traveler_stew') === 0 && Field.hero.buffs.some(b => b.kind === 'regen'));
  check(await page.locator('#bag-details [data-action="use"]').count() === 0, 'A used-up stack leaves the bag');
  check(await page.locator('#inventory-list [data-item="traveler_stew"]').count() === 0, 'The empty stack is gone from the grid');
  await page.screenshot({ path: path.join(world.artifacts, 'consumables-bag.png') });
  await page.keyboard.press('Escape');
  await page.waitForFunction(() => !Field.hero.buffs.some(b => b.kind === 'regen'), null, { timeout: 12000 });

  // --- nothing owned: the press is answered, not ignored ---
  await page.keyboard.press('z');
  check(await slot('food').getAttribute('data-item') === '' && await slot('potion').getAttribute('data-item') === 'health_potion', 'The food slot empties when the food is gone; the spare potion stays');
  check(errors.length === 0, `No browser runtime errors: ${errors.join('; ')}`);
  console.log(`${checks} food and potion UI checks passed; screenshots: ${world.artifacts}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
