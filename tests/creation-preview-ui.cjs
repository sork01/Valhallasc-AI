const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
require('./lib/touch.cjs').requireMemoryLimit();
const classes = ['warrior', 'mage', 'assassin', 'priest', 'hunter'];
const output = path.resolve(__dirname, '../test-results/creation-preview');
let checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
(async () => {
  const world = new TestWorld(); world.startLevel = 1;
  let browser;
  try {
    await world.start(); browser = await chromium.launch({ headless: true });
    fs.mkdirSync(output, { recursive: true });
    for (const [width, height, touch, lang] of (process.argv.includes('--account-only') ? [] : [[1280, 800, false, 'en'], [844, 390, true, 'sv']])) {
      for (const cls of classes) {
        const context = await browser.newContext({ viewport: { width, height }, isMobile: touch, hasTouch: touch, reducedMotion: 'reduce' });
        const page = await context.newPage(), errors = [];
        page.on('pageerror', error => errors.push(error.message));
        await page.addInitScript(lang => {
          window.AudioContext = undefined; window.webkitAudioContext = undefined;
          if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang, sound: false, char: null, draft: null }));
        }, lang);
        await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
        await page.evaluate(() => {
          const draw = MageSprite.prototype.draw;
          MageSprite.prototype.draw = function(g, hero, ...args) {
            window.previewDirection = MageSprite.direction(hero.fx, hero.fy);
            return draw.call(this, g, hero, ...args);
          };
        });
        await page.locator('#cls-' + cls).click();
        for (const gender of ['male', 'female']) {
          await page.locator('#gender-' + gender).click();
          await page.waitForFunction(([cls, gender]) => valhalla.sprites[cls + (gender === 'female' ? 'F' : '')] && !document.querySelector('#go').disabled, [cls, gender]);
          for (const kind of ['Armor', 'Weapon']) check(await page.locator(`#create-${cls}${kind} option[value="none"]`).count() === 1, `${cls}/${gender}: empty ${kind} option`);
          await page.locator('#create-no-gear').click();
          check(await page.evaluate(([cls, gender]) => Object.values(valhalla.sprites[cls + (gender === 'female' ? 'F' : '')].equipment).every(value => value === 'none'), [cls, gender]), `${cls}/${gender}: No gear removes every layer`);
          check(await page.locator('#create-' + cls + 'Armor').inputValue() === 'none' && await page.locator('#create-' + cls + 'Weapon').inputValue() === 'none', 'selectors match the empty preview');
          const seen = new Set();
          for (let turn = 1; turn <= 8; turn++) {
            await page.locator('#create-turn-left').click();
            const dir = await page.evaluate(() => previewDirection);
            check(dir === turn % 8, `${cls}/${gender}: turn ${turn} reaches the rendered facing`); seen.add(dir);
          }
          check(seen.size === 8, 'rotation visits all eight directions and wraps');
          await page.locator('#create-turn-right').click();
          check(await page.evaluate(() => previewDirection) === 7, 'right turns in the opposite direction');
          await page.locator('#create-turn-left').focus(); await page.keyboard.press('Enter');
          check(await page.evaluate(() => previewDirection) === 0, 'keyboard activation turns the preview');
        }
        const left = page.locator('#create-turn-left'), right = page.locator('#create-turn-right');
        for (const control of [left, right, page.locator('#create-no-gear')]) {
          const box = await control.boundingBox();
          check(box.x >= 0 && box.y >= 0 && box.x + box.width <= width && box.y + box.height <= height, 'new controls fit the viewport');
          if (touch) check(box.width >= 44 && box.height >= 44, 'new touch targets are at least 44 pixels');
        }
        check(await left.getAttribute('aria-label') === (lang === 'sv' ? 'Vrid åt vänster' : 'Turn left'), 'rotation label is localized');
        check(await page.locator('#create-no-gear').textContent() === (lang === 'sv' ? 'Ingen utrustning' : 'No gear'), 'No gear is localized');
        if (cls === 'priest') await page.screenshot({ path: path.join(output, `creation-${width}x${height}.png`) });
        await page.locator('#name').fill('Bare' + cls);
        await page.locator('#go').click();
        await page.waitForFunction(cls => Online.connected && Field.hero?.equipment && Object.keys(Field.hero.equipment).length === 0 && Field.hero.look[cls + 'Armor'] === 'none' && Field.hero.look[cls + 'Weapon'] === 'none', cls);
        check(await page.evaluate(cls => Object.values(Field.hero.equipment).length === 0 && Field.hero.look[cls + 'Armor'] === 'none' && Field.hero.look[cls + 'Weapon'] === 'none', cls), `${cls}: server confirms nothing equipped`);
        const starter = await page.evaluate(cls => {
          const items = WORLD_ITEMS.filter(item => item.starter && item.class === cls);
          return { ids: items.map(item => item.id), owned: items.every(item => Inventory.bagQuantity(item.id) > 0), weapon: items.find(item => item.kind === 'weapon').id };
        }, cls);
        check(starter.ids.length >= 2 && starter.owned, `${cls}: starter items stay owned in the bag`);
        if (cls === 'priest') {
          await page.evaluate(item => Online.send({ type: 'equip', slots: { hands: item } }), starter.weapon);
          await page.waitForFunction(() => Field.hero.look.priestWeapon === 'mace');
          await page.reload(); await page.locator('#start').click(); await page.locator('#login-guest').click();
          await page.waitForFunction(() => Online.connected && Field.hero?.look?.priestWeapon === 'mace');
          check(await page.evaluate(() => Object.keys(localStorage).filter(key => key.startsWith('valhallasc.characters.v1:')).every(key => JSON.parse(localStorage.getItem(key)).characters.every(slot => !slot.initialEmptySlots))), 'confirmed creation choice is cleared and never reapplied on reconnect');
        }
        check(errors.length === 0, errors.join('; '));
        console.log(`${width}x${height}: ${cls} preview and unequipped start passed`);
        await context.close();
      }
    }
    // Account creation uses a different saved slot from guest creation. An
    // individual None choice must leave the other starter piece equipped.
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
    await context.addInitScript(() => {
      window.AudioContext = undefined; window.webkitAudioContext = undefined;
      if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null }));
    });
    const page = await context.newPage();
    await page.goto(world.url); await page.locator('#start').click();
    await page.locator('#login-user').fill('BareAccount'); await page.locator('#login-pass').fill('PrivateFixture123!');
    await page.locator('#login-register').click(); await page.locator('#chars-new').click();
    await page.locator('#cls-priest').click();
    await page.locator('#create-priestArmor').selectOption('none');
    await page.locator('#name').fill('BareAccountHero'); await page.locator('#go').click();
    await page.waitForFunction(() => Online.connected && Field.hero?.look?.priestArmor === 'none' && Field.hero.look.priestWeapon === 'mace');
    check(await page.evaluate(() => Field.hero.look.priestArmor === 'none' && Field.hero.look.priestWeapon === 'mace'), 'account creation honors individual None and preserves the other starter piece');
    check(await page.evaluate(() => Object.keys(localStorage).filter(key => key.startsWith('valhallasc.account.v1:')).every(key => Object.values(JSON.parse(localStorage.getItem(key)).slots).every(slot => !slot.initialEmptySlots))), 'account creation intent clears after authoritative confirmation');
    await context.close();
    console.log(`creation-preview: ${checks} checks passed`);
  } finally {
    await browser?.close(); await world.stop();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
