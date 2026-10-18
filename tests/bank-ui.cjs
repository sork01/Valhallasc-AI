// Private browser flow: talk to the real Alderhaven banker, deposit and withdraw by click, shift-click, the quantity box
// and drag, move gold, buy an expansion, pick one gear copy, see a refusal, walk away, reload and find the same bank.
const assert = require('node:assert/strict');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');

const BANKER = { id: 'banker_alderhaven', zone: 0, x: 39, y: 83.6 };
const seed = lang => `if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: '${lang}', sound: false, char: null, draft: null }));`;

(async () => {
  const world = new TestWorld();
  let browser;
  try {
    await world.start();
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.addInitScript(seed('en'));
    await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.locator('#cls-warrior').click(); await page.locator('#name').fill('Hoarder'); await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero.id);
    // The weapon the hero starts with is worn, so two more copies of it are two loose copies beside one worn one.
    const GEAR = await page.evaluate(() => WORLD_ITEMS.find(i => i.kind === 'weapon' && i.class === 'warrior' && i.variant === Field.hero.look.warriorWeapon)?.id);
    assert.ok(GEAR, 'the hero wears a weapon from the catalog');
    const debug = (ref, command) => page.evaluate(([ref, command]) => Online.send({ type: 'debug', ref, command }), [ref, command]);
    const gotoBanker = async () => {
      await debug(1, { op: 'teleport', zone: BANKER.zone, x: BANKER.x, y: BANKER.y });
      await page.waitForFunction(b => Field.zone === b.zone && Math.hypot(Field.hero.x - b.x, Field.hero.y - b.y) < 1, BANKER, { timeout: 10000 });
    };
    const openBank = async () => {
      await page.evaluate(id => Online.send({ type: 'interact', npc: id }), BANKER.id);
      await page.locator('#npc-dialogue [data-offer="bank"]').click({ timeout: 10000 });
      await page.locator('#bank-panel').waitFor({ state: 'visible', timeout: 10000 });
    };
    const bank = (item, side = 'bank') => page.locator(`#bank-panel .bank-cell[data-side="${side}"][data-item="${item}"]`);
    const count = async (item, side) => (await bank(item, side).count()) ? Number(await bank(item, side).locator('.item-stack').textContent()) : 0;
    const notice = () => page.locator('#bank-notice').textContent();
    await debug(2, { op: 'set_gold', gold: 20000 });
    await debug(3, { op: 'give_item', item: 'slime_gel', quantity: 30 });
    await debug(4, { op: 'give_item', item: GEAR, quantity: 2 });
    await page.waitForFunction(g => Inventory.quantity('slime_gel') === 30 && Inventory.quantity(g) >= 3 && Field.hero.gold === 20000, GEAR, { timeout: 10000 });
    await gotoBanker();

    // The banker's gossip has the bank row; it opens the window and the window shows the empty bank beside the bags.
    await page.evaluate(id => Online.send({ type: 'interact', npc: id }), BANKER.id);
    await page.locator('#npc-dialogue').waitFor({ state: 'visible' });
    assert.match(await page.locator('#npc-name').textContent(), /Brenna Coinwright/);
    assert.match(await page.locator('#npc-dialogue [data-offer="bank"]').textContent(), /Open the bank/);
    await page.locator('#npc-dialogue [data-offer="bank"]').click();
    await page.locator('#bank-panel').waitFor({ state: 'visible', timeout: 10000 });
    assert.equal(await page.locator('#npc-dialogue').isHidden(), true, 'the gossip window gives way to the bank');
    assert.equal(await page.evaluate(() => Field.canAct), false, 'the world is paused while the bank is open');
    assert.match(await page.locator('#bank-title').textContent(), /Brenna Coinwright/);
    assert.match(await page.locator('#bank-capacity').textContent(), /^0\/48 slots · 48 free$/);
    assert.equal(await page.locator('#bank-grid .bag-cell').count(), 48, 'one cell per bank slot');
    assert.equal(await count('slime_gel', 'bags'), 30);
    assert.match(await page.locator('#bank-gold').textContent(), /^0 gold$/);
    assert.match(await page.locator('#bank-purse').textContent(), /20,000 gold/);
    assert.match(await page.locator('#bank-expand').textContent(), /10,000 gold/);

    // Click moves the box quantity (1), the box moves part of a stack, shift-click moves the rest.
    await bank('slime_gel', 'bags').locator('button').click();
    await page.waitForFunction(() => document.querySelector('#bank-grid [data-item="slime_gel"] .item-stack')?.textContent === '1');
    assert.match(await notice(), /Stored 1 .* in the bank\./);
    assert.equal(await count('slime_gel', 'bags'), 29);
    await page.locator('#bank-quantity').fill('5');
    await bank('slime_gel', 'bags').locator('button').click();
    await page.waitForFunction(() => document.querySelector('#bank-grid [data-item="slime_gel"] .item-stack')?.textContent === '6');
    await bank('slime_gel', 'bags').locator('button').click({ modifiers: ['Shift'] });
    await page.waitForFunction(() => document.querySelector('#bank-grid [data-item="slime_gel"] .item-stack')?.textContent === '30');
    assert.equal(await bank('slime_gel', 'bags').count(), 0, 'the bags no longer show the stack');
    assert.match(await page.locator('#bank-capacity').textContent(), /^1\/48 slots · 47 free$/);
    // Nothing moved on the server's side other than what the window says: the bags agree.
    assert.equal(await page.evaluate(() => Inventory.quantity('slime_gel')), 0);

    // Drag a quantity back onto the bags' grid, and take a whole stack with shift-click on the bank side.
    await page.locator('#bank-quantity').fill('3');
    await bank('slime_gel').locator('button').dragTo(page.locator('#bank-bag-grid'));
    await page.waitForFunction(() => document.querySelector('#bank-bag-grid [data-item="slime_gel"] .item-stack')?.textContent === '3');
    assert.equal(await count('slime_gel', 'bank'), 27);
    await page.locator('#bank-quantity').fill('1');

    // The tooltip is the bags' tooltip, told where the stack is.
    await bank('slime_gel').locator('button').hover();
    const tip = page.locator('#item-tooltip');
    await tip.waitFor({ state: 'visible' });
    assert.match(await tip.textContent(), /Slime Gel[\s\S]*27 in the bank[\s\S]*Click to take/);
    assert.doesNotMatch(await tip.textContent(), /Sells for/, 'a banked stack has no sale line');
    await page.mouse.move(5, 5);

    // Refusals: a bad box value and gold you do not carry never leave the window; a request the server refuses
    // (more than you own) comes back as the server's own notice, and the bank is unchanged.
    await page.locator('#bank-quantity').fill('0');
    await bank('slime_gel', 'bags').locator('button').click();
    assert.match(await notice(), /Choose a quantity to store\./);
    await page.locator('#bank-quantity').fill('1');
    await page.locator('#bank-gold-amount').fill('999999');
    await page.locator('#bank-gold-deposit').click();
    assert.match(await notice(), /You do not carry that much gold\./);
    await page.evaluate(() => Online.send({ type: 'bank_deposit', npc: 'banker_alderhaven', item: 'slime_gel', quantity: 500 }));
    await page.waitForFunction(() => /only store items you own/.test(document.getElementById('bank-notice').textContent));
    assert.equal(await count('slime_gel', 'bank'), 27, 'a refused deposit changes nothing');
    assert.equal(await page.locator('#bank-notice').getAttribute('data-state'), 'error');

    // Gold has its own balance and never touches the services' purse.
    await page.locator('#bank-gold-amount').fill('5000');
    await page.locator('#bank-gold-deposit').click();
    await page.waitForFunction(() => /^5,000 gold$/.test(document.getElementById('bank-gold').textContent));
    assert.match(await page.locator('#bank-purse').textContent(), /15,000 gold/);
    await page.locator('#bank-gold-amount').fill('2000');
    await page.locator('#bank-gold-withdraw').click();
    await page.waitForFunction(() => /^3,000 gold$/.test(document.getElementById('bank-gold').textContent));
    assert.match(await page.locator('#bank-purse').textContent(), /17,000 gold/);

    // The expansion: 10,000 gold, +12 cells, and the next one costs more than the purse holds.
    await page.locator('#bank-expand').click();
    await page.waitForFunction(() => /\/60 slots/.test(document.getElementById('bank-capacity').textContent));
    assert.equal(await page.locator('#bank-grid .bag-cell').count(), 60);
    assert.match(await page.locator('#bank-purse').textContent(), /7,000 gold/);
    assert.match(await page.locator('#bank-expand-text').textContent(), /Expansion 2 of 4: \+12 cells for 40,000 gold/);
    assert.equal(await page.locator('#bank-expand').isDisabled(), true);
    assert.match(await page.locator('#bank-expand-short').textContent(), /You need 33,000 more gold\./);

    // Gear: two loose copies of one ID open a copy list, and one named copy goes in; the worn copy stays on the hero.
    const looseBefore = await page.evaluate(g => Inventory.looseCopies(g).length, GEAR);
    assert.ok(looseBefore >= 2, 'two loose copies');
    await bank(GEAR, 'bags').locator('button').click();
    await page.locator('#bank-details .bank-copy').first().waitFor();
    assert.equal(await page.locator('#bank-details .bank-copy').count(), looseBefore);
    const copyId = await page.locator('#bank-details .bank-copy').last().getAttribute('data-copy');
    await page.locator('#bank-details .bank-copy').last().locator('button').click();
    await page.waitForFunction(g => document.querySelector(`#bank-grid [data-item="${g}"]`), GEAR);
    assert.equal(await page.evaluate(g => Inventory.looseCopies(g).length, GEAR), looseBefore - 1, 'one copy left the bags');
    assert.equal(await page.evaluate(g => Inventory.quantity(g) - Inventory.bagQuantity(g), GEAR), 1, 'the worn copy stays on the hero');
    await bank(GEAR).locator('button').hover();
    assert.match(await tip.textContent(), new RegExp(`Copy #${copyId} `), 'the tooltip lists the banked copy');
    await page.mouse.move(5, 5);

    // Sorting keeps every stack and only changes the order.
    await page.locator('#bank-sort').click();
    assert.equal(await page.locator('#bank-sort').getAttribute('aria-pressed'), 'true');
    assert.equal(await page.locator('#bank-grid .bank-cell').count(), 2);
    await page.locator('#bank-sort').click();

    // Escape closes the window and gives the world back.
    await page.keyboard.press('Escape');
    await page.locator('#bank-panel').waitFor({ state: 'hidden' });
    await page.waitForFunction(() => Field.canAct);

    // Walking away closes it too (a teleport stands in for being carried off), with the world resumed.
    await openBank();
    await debug(5, { op: 'teleport', zone: BANKER.zone, x: BANKER.x - 12, y: BANKER.y });
    await page.locator('#bank-panel').waitFor({ state: 'hidden', timeout: 5000 });
    await page.waitForFunction(() => Field.canAct);

    // Reload: the same bank, gold and expansion come back from the server's save.
    await page.evaluate(() => Online.stop());
    await world.waitFor(async () => (await (await fetch(world.url + 'health')).json()).online === 0, 10000, 'guest disconnect');
    await page.reload(); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.waitForFunction(() => Online.connected && Field.hero.id, null, { timeout: 60000 });
    await gotoBanker();
    await openBank();
    assert.equal(await count('slime_gel', 'bank'), 27);
    assert.ok(await bank(GEAR).count(), 'the gear copy is still banked');
    assert.match(await page.locator('#bank-gold').textContent(), /^3,000 gold$/);
    assert.match(await page.locator('#bank-capacity').textContent(), /^2\/60 slots/);
    await page.keyboard.press('Escape');

    // Keyboard: cells are buttons (Enter moves the box quantity, Shift+Enter the whole stack), letter shortcuts of
    // the game stay out while the window is open, Tab never leaves it, Escape closes.
    await debug(6, { op: 'give_item', item: 'slime_gel', quantity: 8 });
    await page.waitForFunction(() => Inventory.quantity('slime_gel') === 11);   // the 3 taken back by the drag plus 8 more
    await openBank();
    await bank('slime_gel', 'bags').locator('button').focus();
    await page.keyboard.press('Enter');
    await page.waitForFunction(() => document.querySelector('#bank-grid [data-item="slime_gel"] .item-stack')?.textContent === '28');
    await bank('slime_gel', 'bags').locator('button').focus();
    await page.keyboard.press('Shift+Enter');
    await page.waitForFunction(() => document.querySelector('#bank-grid [data-item="slime_gel"] .item-stack')?.textContent === '38');
    await page.keyboard.press('e');
    assert.equal(await page.locator('#equipment').isHidden(), true, 'a game shortcut does not open another window behind the bank');
    for (let n = 0; n < 40; n++) { await page.keyboard.press('Tab'); assert.equal(await page.evaluate(() => !!document.activeElement.closest('#bank-panel')), true, 'Tab stays in the window'); }
    await page.keyboard.press('Escape');
    await page.locator('#bank-panel').waitFor({ state: 'hidden' });

    // Mounted, the bank refuses to open: the banker's own window says why and nothing else changes.
    await debug(7, { op: 'set_level', level: 50 }); await debug(8, { op: 'give_mount', mount: 'horse' });
    await page.waitForFunction(() => Field.hero.mountOwned && Field.hero.level === 50, null, { timeout: 10000 });
    await page.evaluate(() => Field.toggleMount());
    await page.waitForFunction(() => Field.hero.mounted, null, { timeout: 10000 });
    await page.evaluate(id => Online.send({ type: 'interact', npc: id }), BANKER.id);
    await page.locator('#npc-dialogue [data-offer="bank"]').click();
    await page.waitForFunction(() => /Dismount first\./.test(document.getElementById('npc-notice').textContent));
    assert.equal(await page.locator('#bank-panel').isHidden(), true, 'a refused bank stays shut');
    assert.equal(await page.locator('#npc-dialogue [data-offer="bank"]').isEnabled(), true, 'the banker can be asked again');
    await page.locator('#npc-close').click();
    await page.evaluate(() => Field.toggleMount());
    await page.waitForFunction(() => !Field.hero.mounted, null, { timeout: 10000 });

    // Swedish: every string of the window is translated, the server's notices included.
    const sv = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    sv.on('pageerror', e => errors.push(e.message));
    await sv.addInitScript(seed('sv'));
    await sv.goto(world.url); await sv.locator('#start').click(); await sv.locator('#login-guest').click();
    await sv.locator('#cls-warrior').click(); await sv.locator('#name').fill('Svensson'); await sv.locator('#go').click({ timeout: 60000 });
    await sv.waitForFunction(() => Online.connected && Field.hero.id);
    const svDebug = (ref, command) => sv.evaluate(([ref, command]) => Online.send({ type: 'debug', ref, command }), [ref, command]);
    await svDebug(1, { op: 'set_gold', gold: 20000 }); await svDebug(2, { op: 'give_item', item: 'slime_gel', quantity: 5 });
    await svDebug(3, { op: 'teleport', zone: BANKER.zone, x: BANKER.x, y: BANKER.y });
    await sv.waitForFunction(b => Field.zone === b.zone && Math.hypot(Field.hero.x - b.x, Field.hero.y - b.y) < 1 && Inventory.quantity('slime_gel') === 5, BANKER, { timeout: 10000 });
    await sv.evaluate(id => Online.send({ type: 'interact', npc: id }), BANKER.id);
    await sv.locator('#npc-dialogue [data-offer="bank"]').click();
    await sv.locator('#bank-panel').waitFor({ state: 'visible' });
    await sv.locator('#bank-panel .bank-cell[data-side="bags"][data-item="slime_gel"] button').click();
    await sv.waitForFunction(() => /Lade in 1 .* i banken\./.test(document.getElementById('bank-notice').textContent));
    await sv.locator('#bank-gold-amount').fill('999999'); await sv.locator('#bank-gold-deposit').click();
    assert.match(await sv.locator('#bank-notice').textContent(), /Du bär inte på så mycket guld\./);
    await sv.locator('#bank-panel .bank-cell[data-side="bank"] button').hover();
    await sv.locator('#item-tooltip').waitFor({ state: 'visible' });
    const svText = await sv.evaluate(() => document.getElementById('bank-panel').innerText + '\n' + document.getElementById('item-tooltip').innerText + '\n' + [...document.querySelectorAll('#bank-panel [aria-label]')].map(n => n.getAttribute('aria-label')).join('\n'));
    for (const english of ['Deposit gold', 'Withdraw gold', 'Gold in the bank', 'Sort by kind', 'Click an item', 'Expand the bank', 'Expansion 1', 'It is never refunded', 'in the bank', 'Empty bank slot', 'Click to take', 'Close the bank', 'Choose a quantity'])
      assert.ok(!svText.includes(english), `"${english}" is translated in Swedish`);
    for (const swedish of ['Sätt in guld', 'Ta ut guld', 'Guld i banken', 'Utökning 1 av 4', 'Stäng', 'Klicka för att ta ut', 'i banken'])
      assert.ok(svText.includes(swedish), `"${swedish}" is shown in Swedish`);
    await sv.close();

    // A phone held sideways (844x390, touch): the window stays inside the screen, nothing scrolls sideways, and every
    // button and box is at least 44px in both directions.
    const phoneContext = await browser.newContext({ viewport: { width: 844, height: 390 }, isMobile: true, hasTouch: true, reducedMotion: 'reduce' });
    const phone = await phoneContext.newPage();
    phone.on('pageerror', e => errors.push(e.message));
    await phone.addInitScript(seed('en'));
    await phone.goto(world.url); await phone.locator('#start').click(); await phone.locator('#login-guest').click();
    await phone.locator('#cls-warrior').click(); await phone.locator('#name').fill('Phoney'); await phone.locator('#go').click({ timeout: 60000 });
    await phone.waitForFunction(() => Online.connected && Field.hero.id);
    const phoneDebug = (ref, command) => phone.evaluate(([ref, command]) => Online.send({ type: 'debug', ref, command }), [ref, command]);
    await phoneDebug(1, { op: 'set_gold', gold: 20000 }); await phoneDebug(2, { op: 'give_item', item: 'slime_gel', quantity: 5 });
    await phoneDebug(3, { op: 'teleport', zone: BANKER.zone, x: BANKER.x, y: BANKER.y });
    await phone.waitForFunction(b => Field.zone === b.zone && Math.hypot(Field.hero.x - b.x, Field.hero.y - b.y) < 1 && Inventory.quantity('slime_gel') === 5, BANKER, { timeout: 10000 });
    await phone.evaluate(id => Online.send({ type: 'interact', npc: id }), BANKER.id);
    await phone.locator('#npc-dialogue [data-offer="bank"]').tap();
    await phone.locator('#bank-panel').waitFor({ state: 'visible' });
    await phone.locator('#bank-panel .bank-cell[data-side="bags"][data-item="slime_gel"] button').tap();
    await phone.waitForFunction(() => document.querySelector('#bank-grid [data-item="slime_gel"] .item-stack')?.textContent === '1');
    const fit = await phone.evaluate(() => {
      const r = document.querySelector('.bank-panel').getBoundingClientRect();
      const small = [...document.querySelectorAll('#bank-panel button:not([hidden]), #bank-panel input')].filter(n => n.offsetParent && !n.closest('.bank-grid'))
        .map(n => ({ id: n.id || n.textContent.trim(), w: n.getBoundingClientRect().width, h: n.getBoundingClientRect().height })).filter(n => n.w < 44 || n.h < 44);
      const wide = [...document.querySelectorAll('#bank-panel *')].filter(n => n.getBoundingClientRect().right > r.right + 1).map(n => n.tagName + '.' + n.className);
      return { left: r.left, top: r.top, right: r.right, bottom: r.bottom, w: innerWidth, h: innerHeight, scrollW: document.documentElement.scrollWidth, small, wide };
    });
    assert.ok(fit.left >= 0 && fit.top >= 0 && fit.right <= fit.w && fit.bottom <= fit.h, `the bank fits the phone screen: ${JSON.stringify(fit)}`);
    assert.ok(fit.scrollW <= fit.w, 'the page does not scroll sideways');
    assert.deepEqual(fit.small, [], 'every button and box is at least 44px');
    assert.deepEqual(fit.wide, [], 'nothing sticks out of the window sideways');
    await phone.locator('#bank-x').tap();
    await phone.locator('#bank-panel').waitFor({ state: 'hidden' });
    await phoneContext.close();

    // The character list tells what deleting a character would take with it: the items and gold in its bank.
    const acct = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    acct.on('pageerror', e => errors.push(e.message));
    await acct.addInitScript(seed('en'));
    await acct.goto(world.url); await acct.locator('#start').click(); await acct.locator('#login-title').waitFor({ state: 'visible' });
    await acct.locator('#login-user').fill('Bank_One'); await acct.locator('#login-pass').fill('hunter22x'); await acct.locator('#login-register').click();
    await acct.locator('#chars-new').click();
    await acct.locator('#cls-warrior').click(); await acct.locator('#name').fill('Vaulter'); await acct.locator('#go').click({ timeout: 60000 });
    await acct.waitForFunction(() => Online.connected && Field.hero.id);
    const acctDebug = (ref, command) => acct.evaluate(([ref, command]) => Online.send({ type: 'debug', ref, command }), [ref, command]);
    await acctDebug(1, { op: 'set_gold', gold: 3000 }); await acctDebug(2, { op: 'give_item', item: 'slime_gel', quantity: 9 });
    await acctDebug(3, { op: 'teleport', zone: BANKER.zone, x: BANKER.x, y: BANKER.y });
    await acct.waitForFunction(b => Field.zone === b.zone && Math.hypot(Field.hero.x - b.x, Field.hero.y - b.y) < 1 && Inventory.quantity('slime_gel') === 9, BANKER, { timeout: 10000 });
    await acct.evaluate(id => { Online.send({ type: 'bank_deposit', npc: id, item: 'slime_gel', quantity: 4 }); Online.send({ type: 'bank_gold', npc: id, deposit: true, amount: 1200 }); }, BANKER.id);
    await acct.waitForFunction(() => Inventory.quantity('slime_gel') === 5 && Field.hero.gold === 1800, null, { timeout: 10000 });
    await acct.keyboard.press('Escape'); await acct.locator('#p-title').click();
    await acct.locator('#start').click(); await acct.locator('#login-title').waitFor({ state: 'visible' });
    await acct.locator('#login-continue').click(); await acct.locator('.char-del').first().waitFor({ state: 'visible' });
    assert.equal(await acct.locator('#chars-msg').textContent(), '', 'no warning before the first click');
    await acct.locator('.char-del').first().click();
    assert.equal(await acct.locator('.char-del').first().textContent(), 'Really?');
    assert.match(await acct.locator('#chars-msg').textContent(), /Deleting Vaulter also deletes the bank\. Items in it: 4\. Gold in it: 1,200\./);
    await acct.close();

    assert.deepEqual(errors, [], 'bank UI has no page errors');
    console.log('Bank window: gossip row, click / shift-click / box / drag moves, tooltips, refusals, gold, expansion, gear copies, sort, Escape, walking away and reload checks passed');
  } finally {
    await browser?.close(); await world.stop();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
