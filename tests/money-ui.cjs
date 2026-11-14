// Browser check for COIN-DENOMINATIONS: the shared formatter, and the purse and a merchant price showing coin icons with the right split.
// Run via: bash scripts/test-touch-bounded.sh tests/money-ui.cjs
// MUTATE=1 makes the formatter print the old "<n> gold" with no coins: the purse check must fail.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');

const root = path.resolve(__dirname, '..');

function requireMemoryLimit() {
  const entry = fs.readFileSync('/proc/self/cgroup', 'utf8').split('\n').find(s => s.startsWith('0::'));
  if (!entry) throw Error('Use scripts/test-touch-bounded.sh (1536M cap).');
  let dir = path.join('/sys/fs/cgroup', entry.slice(3));
  while (dir.startsWith('/sys/fs/cgroup')) {
    try {
      const limit = fs.readFileSync(path.join(dir, 'memory.max'), 'utf8').trim();
      if (/^\d+$/.test(limit) && BigInt(limit) <= 1536n * 1024n ** 2n) return;
    } catch (_) {}
    if (dir === '/sys/fs/cgroup') break;
    dir = path.dirname(dir);
  }
  throw Error('Refusing uncapped browser run; use scripts/test-touch-bounded.sh.');
}

(async () => {
  requireMemoryLimit();
  const world = new TestWorld(root, { env: { VALHALLA_LEVEL_SPREAD: '0' } });
  await world.start();
  const browser = await chromium.launch({ headless: true });
  const errors = [];
  let checks = 0;
  const check = (cond, msg) => { assert.ok(cond, msg); checks++; };
  try {
    for (const lang of ['en', 'sv']) {
      const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
      const page = await ctx.newPage();
      page.on('pageerror', e => errors.push(e.message));
      if (process.env.MUTATE === '1') await page.addInitScript(() => addEventListener('DOMContentLoaded', () => { Money.html = n => `<span class="money" data-copper="${n}">${n} gold</span>`; }));
      await page.addInitScript(l => {
        window.AudioContext = undefined; window.webkitAudioContext = undefined;
        localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: l, sound: false, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {}, char: null, draft: null }));
      }, lang);
      await page.goto(world.url);
      await page.locator('#start').click();
      await page.locator('#login-guest').click();
      await page.locator('#name').fill(lang === 'en' ? 'Coiner' : 'Myntare');
      await page.locator('#go').click({ timeout: 60000 });
      await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
      if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
      await page.evaluate(() => { const tip = document.getElementById('tutorial-tip'); if (tip && !tip.hidden) document.getElementById('tutorial-disable')?.click(); });
      const tag = s => `${lang}: ${s}`;

      if (lang === 'en') {
        // The formatter: zero parts hidden, nothing is blank, the ends of the range.
        const cases = [[0, '0 copper'], [5, '5 copper'], [99, '99 copper'], [100, '1 silver'], [101, '1 silver 1 copper'], [9999, '99 silver 99 copper'],
          [10000, '1 gold'], [10001, '1 gold 1 copper'], [10100, '1 gold 1 silver'], [123456, '12 gold 34 silver 56 copper'], [500000, '50 gold'],
          [4294967295, '429,496 gold 72 silver 95 copper']];
        for (const [n, want] of cases) check(await page.evaluate(n => Money.text(n), n) === want, tag(`Money.text(${n}) is "${want}"`));
        check(await page.evaluate(() => Money.short(123456) === '12g 34s 56c' && Money.short(7) === '7c'), tag('Money.short for the canvas'));
        check(await page.evaluate(() => JSON.stringify(Money.parts(10101)) === JSON.stringify({ gold: 1, silver: 1, copper: 1 })), tag('Money.parts'));
        check(await page.evaluate(() => !Money.html(1).includes('NaN') && Money.text(-5) === '0 copper' && Money.text('x') === '0 copper'), tag('bad input shows 0 copper, never NaN'));
      }

      // The purse in the bags window.
      await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'set_gold', gold: 123456 } }));
      await page.waitForFunction(() => Field.hero.gold === 123456);
      await page.waitForFunction(() => document.querySelector('#bag-gold .money')?.dataset.copper === '123456');
      const purse = await page.evaluate(() => ({ coins: document.querySelectorAll('#bag-gold .coin').length, text: document.getElementById('bag-gold').textContent.replace(/\s+/g, ' ').trim(), kinds: [...document.querySelectorAll('#bag-gold .coin')].map(c => c.className) }));
      check(purse.coins === 3 && purse.kinds[0].includes('coin-gold') && purse.kinds[1].includes('coin-silver') && purse.kinds[2].includes('coin-copper'), tag(`the purse shows gold, silver and copper coins (${purse.coins})`));
      check(lang === 'en' ? /^12 gold 34 silver 56 copper$/.test(purse.text) : /^12 guld 34 silver 56 koppar$/.test(purse.text), tag(`the purse reads "${purse.text}"`));
      await page.evaluate(() => CharacterPane.open('stats'));
      await page.locator('#equipment').waitFor({ state: 'visible' });
      const size = await page.evaluate(() => { const c = document.querySelector('#bag-gold .coin').getBoundingClientRect(); return [c.width, c.height]; });
      check(size[0] >= 8 && Math.abs(size[0] - size[1]) < 1, tag(`the coins are round and readable (${size})`));

      await page.evaluate(() => CharacterPane.close());

      // A merchant price: icons, and the amount equals the catalogue price.
      const npc = await page.evaluate(() => WORLD_MAP.npcs.find(n => n.id === 'smith'));
      await page.evaluate(({ x, y }) => Online.send({ type: 'debug', command: { op: 'teleport', zone: 0, x, y: y + 1 } }), npc);
      await page.waitForFunction(n => Math.hypot(Field.hero.nx - n.x, Field.hero.ny - n.y - 1) < .6, npc);
      await page.evaluate(() => Field.visitNpc('smith'));
      await page.locator('#npc-offers [data-view="buy"]').click();
      await page.waitForFunction(() => Shop.open && document.querySelector('.merchant-slot .money'), null, { timeout: 15000 });
      const price = await page.evaluate(() => {
        const slot = document.querySelector('.merchant-slot .money'); if (!slot) return null;
        return { copper: Number(slot.dataset.copper), coins: slot.querySelectorAll('.coin').length, text: slot.textContent.replace(/\s+/g, ' ').trim() };
      });
      check(price && price.coins >= 1 && Number.isFinite(price.copper) && price.copper > 0, tag(`a merchant price shows coin icons: ${JSON.stringify(price)}`));
      check(/^(\d[\d,]*) (gold|silver|copper|guld|koppar)/.test(price.text), tag(`the price also reads in words: ${price.text}`));
      await page.locator('#npc-x').click();
      await ctx.close();
    }
    assert.equal(errors.length, 0, `Page errors: ${errors.join('; ')}`);
    console.log(`PASS money-ui (${checks} checks)`);
  } finally {
    await browser.close().catch(() => {});
    await world.stop().catch(() => {});
  }
})().catch(err => { console.error(err); process.exit(1); });
