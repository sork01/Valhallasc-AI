// Bounded private client/server check. No encounter farming or production accounts.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const pieces = ['hierloom_dawn_ring', 'hierloom_ember_ring', 'hierloom_necklace', 'hierloom_cloak'];
const slots = ['accessory1', 'accessory2', 'necklace', 'cloak'];
const world = new TestWorld();
world.startLevel = 1;
let browser;
(async () => {
  require('./lib/touch.cjs').requireMemoryLimit();
  const started = await world.start();
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => {
    window.AudioContext = undefined; window.webkitAudioContext = undefined;
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null }));
  });
  await page.goto(started.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('HierloomUI');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0);
  const debug = command => page.evaluate(command => Online.send({ type: 'debug', ref: Math.floor(Math.random() * 1e9), command }), command);
  for (const item of pieces) await debug({ op: 'give_item', item, quantity: 1 });
  await page.waitForFunction(pieces => pieces.every(id => Inventory.quantity(id) === 1), pieces);
  for (let at = 0; at < slots.length; at++) {
    await page.evaluate(({ slot, id }) => Field.equipSlot(slot, id), { slot: slots[at], id: pieces[at] });
  }
  await page.waitForFunction(({ pieces, slots }) => slots.every((s, n) => Field.hero.equipment?.[s] === pieces[n]), { pieces, slots });
  await page.keyboard.press('e');
  const necklace = page.locator('.equipped-slot[data-slot="necklace"]');
  await necklace.waitFor({ state: 'visible' });
  for (const slot of slots) {
    const card = page.locator(`.equipped-slot[data-slot="${slot}"]`);
    assert.equal(await card.getAttribute('data-rarity'), 'hierloom');
    assert.equal(await card.locator('.gear-icon').evaluate(el => getComputedStyle(el).borderTopColor), 'rgb(255, 210, 74)');
    assert.match(await card.locator('.gear-icon').innerHTML(), /#ffd24a/);
  }
  await page.mouse.move(0, 0); await necklace.locator('.gear-icon').hover();
  await page.waitForFunction(() => /Never loses durability/.test(document.querySelector('#item-tooltip')?.textContent || ''));
  let tip = await page.locator('#item-tooltip').innerText();
  assert.match(tip, /Hierloom/); assert.match(tip, /\+100% XP/);
  assert.match(tip, /\+2 stamina/);
  await debug({ op: 'give_item', item: 'hierloom_necklace', quantity: 1 });
  await page.waitForFunction(() => Inventory.bagQuantity('hierloom_necklace') === 1);
  await page.locator('#inventory-list [data-item="hierloom_necklace"]').click();
  await page.waitForFunction(() => /Never loses durability/.test(document.querySelector('.bag-details')?.textContent || ''));
  await debug({ op: 'set_level', level: 50 });
  await page.waitForFunction(() => Field.hero.level === 50);
  await page.mouse.move(0, 0); await necklace.locator('.gear-icon').hover();
  await page.waitForFunction(() => /\+100 stamina/.test(document.querySelector('#item-tooltip')?.textContent || ''));
  await debug({ op: 'die' });
  await page.waitForFunction(() => Field.hero.dead || Field.hero.hp <= 0);
  await debug({ op: 'set_hp', hp: 1e9 });
  await page.waitForFunction(() => Field.hero.hp > 0 && !Field.hero.dead);
  assert.equal(await necklace.getAttribute('data-condition'), 'new');
  assert.equal(await necklace.locator('.item-break').count(), 0);
  // Exercise the actual preview/nonce/confirm protocol and keep the four level-1 pieces worn.
  await page.evaluate(() => Online.send({ type: 'rebirth_preview' }));
  await page.locator('#rebirth-dialog').waitFor({ state: 'visible' });
  await page.locator('#rebirth-dialog input').fill('REBIRTH');
  await page.locator('#rebirth-confirm').click();
  await page.waitForFunction(() => Field.hero.level === 1);
  assert.equal(await necklace.getAttribute('data-value'), 'hierloom_necklace');
  await page.mouse.move(0, 0); await necklace.locator('.gear-icon').hover();
  await page.waitForFunction(() => /\+2 stamina/.test(document.querySelector('#item-tooltip')?.textContent || ''));
  await page.screenshot({ path: path.join(world.runDir, 'hierloom-equipment.png') });
  assert.deepEqual(errors, []);
  console.log('Hierloom UI: gold icons/borders, XP tooltip, live scaling, death immunity and rebirth passed.');
  console.log(`Screenshot: ${world.runDir}/hierloom-equipment.png`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); await world.stop();
});
