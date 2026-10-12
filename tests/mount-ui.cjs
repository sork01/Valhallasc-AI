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
    await page.evaluate(() => { Online.send({ type: 'debug', ref: 901, command: { op: 'set_level', level: 50 } }); Online.send({ type: 'debug', ref: 902, command: { op: 'set_gold', gold: 50000 } }); Online.send({ type: 'debug', ref: 903, command: { op: 'teleport', zone: 4, x: 126, y: 124.7 } }); });
    await page.waitForFunction(() => Field.zone === 4 && Field.hero.level === 50 && Field.hero.gold === 50000 && Math.hypot(Field.hero.x - 126, Field.hero.y - 124.7) < 2.8, null, { timeout: 10000 });
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
    await page.evaluate(() => Online.stop());
    await world.waitFor(async () => (await (await fetch(world.url + 'health')).json()).online === 0, 10000, 'guest disconnect');
    await page.reload(); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.waitForFunction(() => Online.connected && Field.hero.mountOwned, null, { timeout: 60000 }).catch(async error => {
      console.error('Resume state', await page.evaluate(() => ({ scene: [...document.querySelectorAll('.scene')].filter(n => !n.hidden).map(n => n.id), connected: Online.connected, hasCharacter: !!valhalla.save?.char, level: Field.hero.level, mountOwned: Field.hero.mountOwned, status: document.getElementById('connection-text')?.textContent })));
      throw error;
    });
    assert.equal(await page.locator('#mount-toggle').isEnabled(), true, 'ownership survives reconnect');
    assert.deepEqual(errors, [], 'mount UI has no page errors');
    console.log('Mount purchase, control, combat dismount and browser resume checks passed');
  } finally {
    await browser?.close(); await world.stop();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
