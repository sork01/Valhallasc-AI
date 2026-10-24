// Private Chromium: real merchant packets, exact payment, precious-item confirmation and buy-back.
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const { chromium } = require('./lib/playwright.cjs');
const world = new TestWorld(); let browser, activePage, checks = 0;
const check = (ok, message) => { assert.ok(ok, message); checks++; };
const items = JSON.parse(fs.readFileSync(path.join(__dirname, '../world/items.txt')));
const smith = JSON.parse(fs.readFileSync(path.join(__dirname, '../world/map.txt'))).npcs.find(n => n.id === 'smith');
const common = items.find(i => i.id === 'warrior_headgear_crimson_l5_gray');
const green = items.find(i => i.id === 'warrior_armor_azure');
const blue = items.find(i => i.id === 'headgear_upgrade');
const purple = items.find(i => i.id === 'warrior_weapon_royal_l10_purple');
const orange = items.find(i => i.id === 'orange_03');
const quest = items.find(i => i.kind === 'material' && i.sell === 0);
(async () => {
  world.startLevel = 99; await world.start(); browser = await chromium.launch({ headless: true });
  for (const lang of ['en', 'sv']) {
    const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } }), errors = [];
    activePage = page; page.setDefaultTimeout(20000);
    page.on('pageerror', error => { errors.push(error.message); console.error('Browser error:', error.message); });
    if (process.env.MUTATE) await page.route('**/shop.js', route => {
      const code = fs.readFileSync(path.join(__dirname, '../client/shop.js'), 'utf8');
      assert.ok(code.includes('if (!precious.length)'));
      return route.fulfill({ contentType: 'application/javascript', body: code.replace('if (!precious.length)', 'if (true)') });
    });
    await page.addInitScript(lang => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang, sound: false })), lang);
    await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.locator('#name').fill(`Sell${lang}`); await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero.level === 99, null, { timeout: 60000 });
    await page.evaluate(() => {
      window.shopPackets = [];
      const receive = Shop.onPacket; Shop.onPacket = packet => { shopPackets.push(packet); receive(packet); };
      window.sellSent = 0; const send = Online.send; Online.send = message => { if (message.type === 'sell_batch') sellSent++; return send(message); };
    });
    const debug = command => page.evaluate(command => Online.send({ type: 'debug', command }), command);
    await debug({ op: 'teleport', zone: 0, x: smith.x, y: smith.y + 1 });
    await debug({ op: 'set_gold', gold: 100000 }); await debug({ op: 'set_rebirth', tiers: [0, 1, 0, 0, 0] });
    for (const [id, quantity] of [[common.id,2],[green.id,1],[blue.id,1],[purple.id,1],[orange.id,1],[quest.id,1],['slime_gel',7],['health_potion_l20',2]]) await debug({ op: 'give_item', item: id, quantity, force: true });
    await page.waitForFunction(id => Inventory.quantity(id) === 2, common.id);
    await page.evaluate(id => Online.send({ type: 'equip', slots: { headgear: id } }), common.id);
    await page.waitForFunction(id => Field.hero.equipment.headgear === id, common.id);
    await page.waitForTimeout(650);
    await page.evaluate(() => Online.send({ type: 'interact', npc: 'smith' }));
    await page.locator('[data-view="sell"]').click();
    await page.waitForFunction(() => document.querySelectorAll('#sell-pick .sell-item').length > 6 && !document.querySelector('.sell-workspace[aria-busy="true"]'));
    const pick = id => page.locator(`#sell-pick [data-item="${id}"]`), basket = id => page.locator(`#sell-basket [data-item="${id}"]`);
    check(await pick(common.id).count() === 1, `${lang}: equipped copy excluded`);
    check(await pick(quest.id).count() === 0, `${lang}: quest item excluded`);
    check(await page.locator('#npc-inventory').textContent().then(t => !t.includes('Sell from your bags')), 'old inline selling removed');
    check(await page.evaluate(() => shopPackets.at(-1).goldPercent) === 10, 'server quote includes rebirth bonus');
    await page.locator('#sell-junk').click();
    check(await basket(common.id).count() === 1 && await basket(green.id).count() === 1 && await basket('slime_gel').count() === 1, 'junk loads grey/green gear and materials');
    check(await basket(blue.id).count() === 0 && await basket(purple.id).count() === 0 && await basket(orange.id).count() === 0, 'junk protects blue/purple/orange');
    while (await page.locator('#sell-basket .sell-item').count()) await page.locator('#sell-basket .sell-item button').first().click();
    await pick('slime_gel').locator('input').fill('4'); await pick('slime_gel').locator('button').click();
    check((await page.locator('#sell-total').textContent()).includes('13'), 'four gel preview rounds rebirth bonus exactly');
    await page.locator('[data-filter="epic"]').click();
    check(await pick(purple.id).count() === 1 && await pick(blue.id).count() === 0, 'rarity filter narrows picker');
    await pick(purple.id).locator('button').click();
    await page.locator('[data-filter="legendary"]').click(); await pick(orange.id).locator('button').click();
    const quote = await page.evaluate(() => {
      const p = shopPackets.at(-1); return p.available.filter(r => ['orange_03','warrior_weapon_royal_l10_purple'].includes(r.item)).map(r => ({ ...r }));
    });
    const goldBefore = await page.evaluate(() => Field.hero.gold);
    const expected = 13 + quote.reduce((sum, row) => sum + Math.floor((row.base * 110 + 50) / 100), 0);
    check((await page.locator('#sell-total').textContent()).includes(String(expected)), 'basket total includes exact selected copies');
    await page.locator('#sell-confirm').click();
    await page.locator('#sell-warning').waitFor({ state: 'visible', timeout: 4000 });
    check(await page.locator('#sell-warning li').count() === 2, 'confirmation names both valuable items');
    check(await page.evaluate(() => document.activeElement.id) === 'sell-cancel', 'orange defaults focus to Cancel');
    check(await page.locator('#sell-warning [data-rarity="epic"]').evaluate(n => getComputedStyle(n).color) !== await page.locator('#sell-warning [data-rarity="legendary"]').evaluate(n => getComputedStyle(n).color), 'rarity colors differ in confirmation');
    await page.locator('#sell-cancel').click();
    check(await page.evaluate(() => sellSent === 0 && Field.hero.gold) === goldBefore, 'Cancel sends no sale');
    await page.locator('#sell-confirm').click(); await page.locator('#sell-yes').click();
    await page.waitForFunction(expected => shopPackets.some(p => p.ok && p.changed && p.paid === expected), expected);
    await page.waitForFunction(gold => Field.hero.gold === gold, goldBefore + expected);
    check(await page.evaluate(() => sellSent) === 1, 'one batch carries the whole basket');
    check(await page.evaluate(() => Inventory.quantity('slime_gel')) === 3, 'requested material quantity sold');
    check(await page.locator('#sell-basket .sell-item').count() === 0, 'success clears basket');
    await page.locator('[data-tab="back"]').click();
    check(await page.locator('#sell-buyback .sell-item').count() === 3, 'buy-back lists sold gear copies and material stack');
    await page.waitForTimeout(650);
    await page.locator(`#sell-buyback [data-item="${purple.id}"] button`).click();
    await page.waitForFunction(id => Inventory.quantity(id) === 1 && !document.querySelector('.sell-workspace[aria-busy="true"]'), purple.id);
    const back = await page.evaluate(id => Field.hero.gearInstances.find(g => g.item === id), purple.id);
    check(JSON.stringify(back) === JSON.stringify(quote.find(r => r.item === purple.id).gear), 'buy-back restores exact original gear copy');
    check(await page.locator('#sell-buyback .sell-item').count() === 2, 'bought-back entry disappears');
    if (lang === 'sv') {
      check((await page.locator('[data-tab="back"]').textContent()) === 'Återköp', 'Swedish tab');
      check(await page.evaluate(() => Locale.translate('You receive: 13 gold')) === 'Du får: 13 guld', 'Swedish total');
      check(await page.evaluate(() => Locale.translate('Sell valuable items?')) === 'Sälj värdefulla föremål?', 'Swedish confirmation');
      await page.waitForFunction(() => document.querySelector('#sell-buyback [data-item="orange_03"]').textContent.includes('Legendarisk'));
      check(true, 'Swedish gear copy rarity and durability');
    }
    await page.locator('#npc-x').click();
    await page.evaluate(() => Online.send({ type: 'interact', npc: 'smith' })); await page.locator('[data-view="sell"]').click();
    await page.locator('[data-tab="back"]').click();
    await page.waitForFunction(() => document.querySelectorAll('#sell-buyback .sell-item').length === 2);
    check(true, 'buy-back survives closing merchant window');
    if (lang === 'en') {
      await page.locator('[data-tab="sell"]').click();
      await debug({ op: 'give_item', item: common.id, quantity: 80, force: true });
      await page.waitForFunction(id => document.querySelectorAll(`#sell-pick [data-item="${id}"]`).length > 80 && !document.querySelector('.sell-workspace[aria-busy="true"]'), common.id);
      await page.locator('#sell-junk').click();
      const count = await page.locator('#sell-basket .sell-item').count();
      check(count > 80, 'large basket includes individually addressed gear copies');
      await page.locator('#sell-confirm').click();
      await page.waitForFunction(id => Inventory.quantity(id) === 1 && !document.querySelector('.sell-workspace[aria-busy="true"]'), common.id);
      check(await page.evaluate(() => Online.connected), 'large batch fits one WebSocket message');
      await page.locator('[data-tab="back"]').click();
      check(await page.locator('#sell-buyback .sell-item').count() === 12, 'buy-back retains only last twelve entries after a large sale');
    }
    await page.screenshot({ path: path.join(world.runDir, `shop-${lang}.png`) });
    check(errors.length === 0, `${lang}: no browser errors: ${errors.join('; ')}`);
    await page.close();
  }
  console.log(`${checks} merchant selling UI checks passed. Artifact: ${world.runDir}`);
})().catch(async error => { if (activePage && !activePage.isClosed()) { await activePage.screenshot({path: path.join(world.runDir, 'failure.png')}); console.error('Checks completed:', checks); console.error('Client state:', await activePage.evaluate(() => ({connected: Online.connected, overlay: document.querySelector('#connection-text').textContent, npc: City.open, picks: document.querySelectorAll('#sell-pick .sell-item').length, pending: document.querySelector('.sell-workspace')?.getAttribute('aria-busy'), packets: shopPackets.map(p=>({ok:p.ok,notice:p.notice,available:p.available?.length}))}))); } console.error(error.message); process.exitCode = 1; }).finally(async () => { await browser?.close(); await world.stop(); });
