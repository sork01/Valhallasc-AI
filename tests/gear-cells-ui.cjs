// Browser check for GEAR-NO-STACK: identical gear takes one bag cell per copy with no count badge, materials still stack, and equipping a
// chosen cell wears that very copy. Run via: bash scripts/test-touch-bounded.sh tests/gear-cells-ui.cjs
// MUTATE=1 serves the previous inventory.js (one cell per item, a count badge) and must fail.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const root = path.resolve(__dirname, '..');

function requireMemoryLimit() {
  const entry = fs.readFileSync('/proc/self/cgroup', 'utf8').split('\n').find(s => s.startsWith('0::'));
  if (!entry) throw Error('Use scripts/test-touch-bounded.sh (1536M cap).');
  let dir = path.join('/sys/fs/cgroup', entry.slice(3));
  while (dir.startsWith('/sys/fs/cgroup')) {
    try { const limit = fs.readFileSync(path.join(dir, 'memory.max'), 'utf8').trim(); if (/^\d+$/.test(limit) && BigInt(limit) <= 1536n * 1024n ** 2n) return; } catch (_) {}
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
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    const page = await ctx.newPage();
    page.on('pageerror', e => errors.push(e.message));
    if (process.env.MUTATE === '1') {
      const old = execFileSync('git', ['show', '0106bebd:client/inventory.js'], { cwd: root, encoding: 'utf8' });
      await page.route('**/inventory.js*', route => route.fulfill({ contentType: 'text/javascript', body: old }));
    }
    await page.addInitScript(() => {
      window.AudioContext = undefined; window.webkitAudioContext = undefined;
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {}, char: null, draft: null }));
    });
    await page.goto(world.url);
    await page.locator('#start').click();
    await page.locator('#login-guest').click();
    await page.locator('#name').fill('Cellar');
    await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
    if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
    await page.evaluate(() => { const tip = document.getElementById('tutorial-tip'); if (tip && !tip.hidden) document.getElementById('tutorial-disable')?.click(); });
    const debug = command => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);
    await debug({ op: 'set_level', level: 15 });
    await page.waitForFunction(() => Field.hero.level >= 15);
    await debug({ op: 'give_item', item: 'headgear_upgrade', quantity: 3 });
    await debug({ op: 'give_item', item: 'slime_gel', quantity: 7 });
    await page.waitForFunction(() => Inventory.bagQuantity('headgear_upgrade') === 3 && Inventory.bagQuantity('slime_gel') === 7);
    await page.evaluate(() => CharacterPane.open('stats'));
    await page.locator('#inventory-list').waitFor({ state: 'visible' });
    const cells = await page.evaluate(() => ({
      helms: [...document.querySelectorAll('#inventory-list .inventory-item[data-item="headgear_upgrade"]')].map(c => ({ key: c.dataset.key, badge: !!c.querySelector('.item-stack') })),
      gel: [...document.querySelectorAll('#inventory-list .inventory-item[data-item="slime_gel"]')].map(c => c.querySelector('.item-stack')?.textContent),
      used: Field.hero.bagUsed,
    }));
    check(cells.helms.length === 3, `three identical helms fill three cells (${cells.helms.length})`);
    check(cells.helms.every(h => !h.badge), 'gear cells carry no count badge');
    check(cells.gel.length === 1 && cells.gel[0] === '7', `slime gel still stacks in one cell with its count (${JSON.stringify(cells.gel)})`);
    // Equip the third cell: that very copy is the one worn.
    const keys = cells.helms.map(h => h.key);
    const chosen = Number(keys[2].split('@')[1]);
    await page.locator(`#inventory-list [data-key="${keys[2]}"] .item-tile`).dblclick();
    await page.waitForFunction(() => Inventory.bagQuantity('headgear_upgrade') === 2, null, { timeout: 10000 });
    const worn = await page.evaluate(() => Field.hero.gearInstances.filter(g => g.item === 'headgear_upgrade')[0].id);
    check(worn === chosen, `equipping the chosen cell wears that copy (${worn} vs ${chosen})`);
    const after = await page.evaluate(() => [...document.querySelectorAll('#inventory-list .inventory-item[data-item="headgear_upgrade"]')].length);
    check(after === 2, `two loose helms remain, in two cells (${after})`);
    assert.equal(errors.length, 0, `Page errors: ${errors.join('; ')}`);
    await ctx.close();
    console.log(`PASS gear-cells-ui (${checks} checks)`);
  } finally {
    await browser.close().catch(() => {});
    await world.stop().catch(() => {});
  }
})().catch(err => { console.error(err); process.exit(1); });
