// Real vendor dialogue/purchases for every class, decade boundaries and Swedish.
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const { chromium } = require('./lib/playwright.cjs');
const world = new TestWorld(); let browser, checks = 0;
const items = JSON.parse(fs.readFileSync(path.join(__dirname, '../world/items.txt')));
const smith = JSON.parse(fs.readFileSync(path.join(__dirname, '../world/map.txt'))).npcs.find(n => n.id === 'smith');
const check = (ok, message) => { assert.ok(ok, message); checks++; };
(async () => {
  world.startLevel = 9; await world.start(); browser = await chromium.launch({ headless: true });
  for (const [cls, lang] of [['warrior','en'], ['mage','en'], ['assassin','en'], ['priest','en'], ['hunter','en'], ['hunter','sv']]) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } }), errors = [];
    page.on('pageerror', error => errors.push(error.message));
    if (process.env.MUTATE) await page.route('**/shop.js', route => {
      // Mutation: the stock shows other classes' weapons; the own-class count check must fail.
      const code = fs.readFileSync(path.join(__dirname, '../client/shop.js'), 'utf8');
      const guard = "(item.kind !== 'weapon' || !item.class || item.class === Field.hero.look.class)";
      assert.ok(code.includes(guard)); return route.fulfill({ contentType: 'application/javascript', body: code.replace(guard, 'true') });
    });
    await page.addInitScript(lang => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang, sound: false })), lang);
    await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.locator(`#cls-${cls}`).click(); await page.locator('#name').fill(`Shop${cls}${lang}`); await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero.level === 9, null, { timeout: 60000 });
    const debug = command => page.evaluate(command => Online.send({ type: 'debug', command }), command);
    await debug({ op: 'teleport', zone: 0, x: smith.x, y: smith.y + 1 });
    await page.waitForFunction(p => Math.hypot(Field.hero.x - p.x, Field.hero.y - p.y - 1) < .3, smith);
    for (const level of (lang === 'sv' ? [90] : [9,10,19,20,90,99])) {
      if (await page.locator('#npc-dialogue').isVisible()) await page.locator('#npc-x').click();
      await debug({ op: 'set_level', level }); await debug({ op: 'set_gold', gold: 100000 });
      await page.waitForFunction(level => Field.hero.level === level && Field.hero.gold === 100000, level);
      await page.waitForTimeout(650);
      await page.evaluate(() => Online.send({ type: 'interact', npc: 'smith' }));
      // The greeting opens with Buy and Sell; the weapon stock lives behind Buy.
      await page.locator('#npc-offers [data-view="buy"]').click();
      await page.waitForFunction(() => Shop.open && document.querySelector('.merchant-workspace[aria-busy="false"]'));
      const row = page.locator(`#merchant-stock [data-offer="buy_green_weapon_${cls}"]`);
      await row.waitFor({ state: 'visible' });
      check(await page.locator('#merchant-stock [data-offer^="buy_green_weapon_"]').count() === 1, `${cls}/${lang}/${level}: only own-class weapon is shown`);
      const step = Math.max(10, Math.min(90, Math.floor(level / 10) * 10));
      const item = items.find(i => i.family === `vendor_weapon_${cls}` && i.requiredLevel === step);
      // The row shows the tier's name (the client picks the best tier at or below the level, falling back to the first tier).
      const tierName = await page.evaluate(name => Locale.translate(name), item.name);
      check((await row.textContent()).includes(tierName), `${cls}/${level}: correct decade weapon`);
      check(await row.locator('.money').first().getAttribute('data-copper') === String(item.price) && item.price === 10 * step * step, `${cls}/${level}: correct catalog price`);
      check(await row.isDisabled() === (level < 10), `${cls}/${level}: level gate matches server`);
      check(!(await row.textContent()).includes('undefined'), `${cls}/${level}: weapon details do not use consumable text`);
      if (lang === 'sv') {
        await page.waitForFunction(() => document.querySelector('#merchant-stock [data-offer="buy_green_weapon_hunter"] .merchant-item-detail b')?.textContent.trim());
        check((await row.textContent()).includes(await page.evaluate(name => Locale.translate(name), item.name)), 'Swedish weapon name is translated in the shop row');
        check(await page.evaluate(() => Locale.translate('Requires level 10.')) === 'Kräver nivå 10.', 'Swedish level refusal is translated');
        check(await page.evaluate(() => Locale.translate('This weapon is for another class.')) === 'Det här vapnet är för en annan klass.', 'Swedish class refusal is translated');
      }
      if ([10,90].includes(level)) {
        check(await row.getAttribute('data-rarity') === 'uncommon' && item.rarity === 'uncommon', 'Green weapon rarity is recorded on the shop row');
        await row.hover(); await page.locator('#item-tooltip').waitFor({ state: 'visible' });
        const translatedName = await page.evaluate(name => Locale.translate(name), item.name);
        check((await page.locator('#item-tooltip').textContent()).includes(translatedName), 'Weapon tooltip opens without errors');
        await row.click();
        await page.waitForFunction(({ id, cost }) => Field.hero.gold === 100000 - cost && Inventory.quantity(id) >= 1, { id: item.id, cost: item.price });
        check(true, `${cls}/${lang}/${level}: actual purchase charged exactly and delivered weapon`);
      }
    }
    check(errors.length === 0, `${cls}/${lang}: no browser errors`); await page.close();
  }
  console.log(`${checks} green weapon vendor UI checks passed. Artifact: ${world.runDir}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => { await browser?.close(); await world.stop(); });
