// Private browser flow: buy a horse from the real vendor, ride, fight, and resume ownership.
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
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.addInitScript(() => { if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })); });
    await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.locator('#cls-warrior').click(); await page.locator('#name').fill('Rider'); await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero.id);
    assert.equal(await page.locator('#mount-toggle').isDisabled(), true, 'a new character cannot mount');
    await page.evaluate(() => { Online.send({ type: 'debug', ref: 901, command: { op: 'set_level', level: 50 } }); Online.send({ type: 'debug', ref: 902, command: { op: 'set_gold', gold: 500000 } }); Online.send({ type: 'debug', ref: 903, command: { op: 'teleport', zone: 4, x: 126, y: 124.7 } }); });
    await page.waitForFunction(() => Field.zone === 4 && Field.hero.level === 50 && Field.hero.gold === 500000 && Math.hypot(Field.hero.x - 126, Field.hero.y - 124.7) < 2.8, null, { timeout: 10000 });
    await page.evaluate(() => Online.send({ type: 'interact', npc: 'city_stable', offer: 'buy_mount' }));
    await page.waitForFunction(() => Field.hero.mountOwned && Field.hero.gold === 0, null, { timeout: 10000 });
    if (await page.locator('#npc-dialogue').isVisible()) await page.locator('#npc-close').click();
    assert.equal(await page.locator('#mount-toggle').isEnabled(), true, 'the bought horse enables the control');
    await page.locator('#mount-toggle').click();
    await page.waitForFunction(() => Field.hero.mounted, null, { timeout: 10000 });
    assert.match(await page.locator('#mount-toggle').textContent(), /Dismount/, 'the UI shows riding state');
    await page.keyboard.press('h');
    await page.waitForFunction(() => !Field.hero.mounted, null, { timeout: 10000 });
    await page.keyboard.press('h');
    await page.waitForFunction(() => Field.hero.mounted, null, { timeout: 10000 });
    await page.evaluate(() => document.activeElement?.blur?.());
    await page.keyboard.press('Space');
    await page.waitForFunction(() => !Field.hero.mounted, null, { timeout: 10000 });
    // The Mounts list: five rows, the horse owned and selected, the rest greyed with their unlock hints.
    await page.keyboard.press('e');
    await page.waitForSelector('#character-mounts .mount-card');
    assert.equal(await page.locator('#character-mounts .mount-card').count(), 5, 'every mount is listed');
    assert.equal(await page.locator('.mount-card[data-mount="horse"]').getAttribute('data-selected'), 'true', 'the horse owner has it selected');
    const raptorCard = page.locator('.mount-card[data-mount="raptor"]');
    assert.equal(await raptorCard.getAttribute('data-owned'), 'false');
    assert.match(await raptorCard.textContent(), /Level 75.*Banyan Run/, 'an unowned mount shows its level and route');
    assert.equal(await raptorCard.locator('button').count(), 0, 'an unowned mount has no Select button');
    assert.match(await page.locator('.mount-card[data-mount="gryphon"]').textContent(), /3% per kill and 250,000 gold/, 'price and drop rate are shown');
    assert.ok(await page.evaluate(() => getComputedStyle(document.querySelector('.mount-card[data-mount="raptor"]')).opacity) < 1, 'unowned rows are greyed');
    assert.equal(await page.locator('.mount-card[data-mount="horse"] button').isDisabled(), true, 'the selected mount cannot be re-selected');
    // A second mount: it is owned but not selected until chosen, and the server refuses a mount that is not owned.
    await page.evaluate(() => Online.send({ type: 'debug', ref: 903, command: { op: 'give_mount', mount: 'raptor' } }));
    await page.waitForFunction(() => Field.hero.mounts?.length === 2, null, { timeout: 10000 });
    assert.equal(await page.evaluate(() => Field.hero.mount), 'horse', 'a new mount does not replace the selection');
    await page.waitForFunction(() => document.querySelector('.mount-card[data-mount="raptor"] button'));
    await page.evaluate(() => Online.send({ type: 'select_mount', mount: 'gryphon' }));
    await page.evaluate(() => Online.send({ type: 'ping', nonce: 1 }));
    await page.waitForTimeout(300);
    assert.equal(await page.evaluate(() => Field.hero.mount), 'horse', 'selecting an unowned mount changes nothing');
    await page.locator('.mount-card[data-mount="raptor"] button').click();
    await page.waitForFunction(() => Field.hero.mount === 'raptor', null, { timeout: 10000 });
    await page.waitForSelector('.mount-card[data-mount="raptor"][data-selected="true"]');
    assert.equal(await page.locator('.mount-card[data-mount="raptor"] button').textContent(), 'Selected');
    await page.keyboard.press('Escape');
    await page.waitForFunction(() => document.getElementById('equipment').hidden);
    assert.match(await page.locator('#mount-toggle').textContent(), /Raptor/, 'the HUD button names the selected mount');
    // A bound licence from a drop: below its level it waits, at level 95 a double-click grants the mount.
    await page.evaluate(() => { Online.send({ type: 'debug', ref: 905, command: { op: 'give_item', item: 'sabertooth_whistle', quantity: 1 } }); });
    await page.waitForFunction(() => Inventory.quantity('sabertooth_whistle') === 1, null, { timeout: 10000 });
    await page.keyboard.press('e');
    const whistle = page.locator('#inventory-list [data-item="sabertooth_whistle"]');
    await whistle.waitFor();
    await whistle.hover();
    assert.match(await page.locator('.item-tooltip').textContent(), /Grants the sabertooth mount.*cannot be traded or sold/, 'the tooltip explains the licence');
    await whistle.dblclick();
    await page.waitForTimeout(400);
    assert.equal(await page.evaluate(() => Field.hero.mounts.includes('sabertooth')), false, 'level 50 cannot use a level-95 whistle');
    await page.evaluate(() => { Online.send({ type: 'debug', ref: 906, command: { op: 'set_level', level: 95 } }); });
    await page.waitForFunction(() => Field.hero.level === 95, null, { timeout: 10000 });
    await page.locator('#inventory-list [data-item="sabertooth_whistle"]').dblclick();
    await page.waitForFunction(() => Field.hero.mounts.includes('sabertooth'), null, { timeout: 10000 });
    assert.equal(await page.evaluate(() => Inventory.quantity('sabertooth_whistle')), 0, 'the whistle is used up');
    assert.equal(await page.evaluate(() => Field.hero.mount), 'raptor', 'a later mount does not change the selection');
    await page.waitForSelector('.mount-card[data-mount="sabertooth"][data-owned="true"]');
    await page.keyboard.press('Escape');
    await page.waitForFunction(() => document.getElementById('equipment').hidden);
    // Another player sees the rider's selected mount in the snapshot.
    const watcher = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    watcher.on('pageerror', e => errors.push(e.message));
    await watcher.addInitScript(() => { if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })); });
    await watcher.goto(world.url); await watcher.locator('#start').click(); await watcher.locator('#login-guest').click();
    await watcher.locator('#cls-warrior').click(); await watcher.locator('#name').fill('Watcher'); await watcher.locator('#go').click({ timeout: 60000 });
    await watcher.waitForFunction(() => Online.connected && Field.hero.id);
    const spot = await watcher.evaluate(() => ({ zone: Field.zone, x: Field.hero.x, y: Field.hero.y }));
    await page.evaluate(spot => Online.send({ type: 'debug', ref: 904, command: { op: 'teleport', zone: spot.zone, x: spot.x + 2, y: spot.y } }), spot);
    await page.waitForFunction(zone => Field.zone === zone, spot.zone, { timeout: 10000 });
    await page.evaluate(() => { document.activeElement?.blur?.(); });
    await page.keyboard.press('h');
    await page.waitForFunction(() => Field.hero.mounted, null, { timeout: 10000 });
    await watcher.waitForFunction(() => Field.remotePlayers.some(p => p.mounted && p.mount === 'raptor'), null, { timeout: 10000 });
    await watcher.close();
    await page.evaluate(() => Online.stop());
    await world.waitFor(async () => (await (await fetch(world.url + 'health')).json()).online === 0, 10000, 'guest disconnect');
    await page.reload(); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.waitForFunction(() => Online.connected && Field.hero.mountOwned, null, { timeout: 60000 }).catch(async error => {
      console.error('Resume state', await page.evaluate(() => ({ scene: [...document.querySelectorAll('.scene')].filter(n => !n.hidden).map(n => n.id), connected: Online.connected, hasCharacter: !!valhalla.save?.char, level: Field.hero.level, mountOwned: Field.hero.mountOwned, status: document.getElementById('connection-text')?.textContent })));
      throw error;
    });
    assert.equal(await page.locator('#mount-toggle').isEnabled(), true, 'ownership survives reconnect');
    assert.deepEqual(await page.evaluate(() => [Field.hero.mounts, Field.hero.mount]), [['horse', 'raptor', 'sabertooth'], 'raptor'], 'the owned set and selection survive a reload');
    assert.deepEqual(errors, [], 'mount UI has no page errors');
    console.log('Mount purchase, mounts list, selection, remote view, control, combat dismount and browser resume checks passed');
  } finally {
    await browser?.close(); await world.stop();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
