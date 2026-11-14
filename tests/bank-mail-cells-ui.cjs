// Browser check for the bank's per-copy cells (GEAR-NO-STACK) and the minimap mail icon at a real mailbox (MINIMAP-MAIL-ICON).
// Run via: bash scripts/test-touch-bounded.sh tests/bank-mail-cells-ui.cjs
// MUTATE=1 serves the previous bank.js (one cell per item with a count badge) and must fail.
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
      const old = execFileSync('git', ['show', '0106bebd:client/bank.js'], { cwd: root, encoding: 'utf8' });
      await page.route('**/bank.js*', route => route.fulfill({ contentType: 'text/javascript', body: old }));
    }
    await page.addInitScript(() => {
      window.AudioContext = undefined; window.webkitAudioContext = undefined;
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {}, char: null, draft: null }));
    });
    await page.goto(world.url);
    await page.locator('#start').click();
    await page.locator('#login-guest').click();
    await page.locator('#name').fill('Vaulter');
    await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
    if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
    await page.evaluate(() => { const tip = document.getElementById('tutorial-tip'); if (tip && !tip.hidden) document.getElementById('tutorial-disable')?.click(); });
    const debug = command => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);
    await debug({ op: 'set_level', level: 15 });
    await debug({ op: 'give_item', item: 'headgear_upgrade', quantity: 3 });
    await page.waitForFunction(() => Inventory.bagQuantity('headgear_upgrade') === 3);

    // The bank, beside the bags: three helms are three cells on the bag side.
    const banker = await page.evaluate(() => WORLD_MAP.npcs.find(n => n.id === 'banker_alderhaven'));
    await debug({ op: 'teleport', zone: 0, x: banker.x, y: banker.y + 1 });
    await page.waitForFunction(b => Math.hypot(Field.hero.x - b.x, Field.hero.y - b.y - 1) < 1, banker);
    await page.evaluate(id => Online.send({ type: 'interact', npc: id }), banker.id);
    await page.locator('#npc-dialogue [data-offer="bank"]').click({ timeout: 10000 });
    await page.locator('#bank-panel').waitFor({ state: 'visible', timeout: 10000 });
    const cells = side => page.locator(`#bank-panel .bank-cell[data-side="${side}"][data-item="headgear_upgrade"]`);
    check(await cells('bags').count() === 3, `three identical helms are three cells in the bag grid (${await cells('bags').count()})`);
    check(await cells('bags').locator('.item-stack').count() === 0, 'gear cells have no count badge');
    const chosen = Number(await cells('bags').nth(1).getAttribute('data-copy'));
    check(Number.isFinite(chosen) && chosen > 0, `each cell knows its copy (${chosen})`);
    await cells('bags').nth(1).locator('button').click();
    await page.waitForFunction(() => document.querySelectorAll('#bank-panel .bank-cell[data-side="bank"][data-item="headgear_upgrade"]').length === 1, null, { timeout: 10000 });
    check(await cells('bank').count() === 1 && await cells('bags').count() === 2, 'one click stores exactly that copy: one cell in the bank, two left in the bags');
    check(await page.evaluate(() => Number(document.querySelector('#bank-panel .bank-cell[data-side="bank"][data-item="headgear_upgrade"]').dataset.copy)) > 0, 'the banked cell is a single copy');
    check(/1\/48/.test(await page.locator('#bank-capacity').textContent()), `the bank counts one cell used (${await page.locator('#bank-capacity').textContent()})`);
    await page.locator('#bank-close').click();

    // The mail icon at a mailbox opens the mail window; away from one it only explains.
    const box = await page.evaluate(() => WORLD_MAP.npcs.find(n => (n.offers || []).some(o => o.id === 'mail')));
    await debug({ op: 'teleport', zone: 0, x: box.x, y: box.y + 1.2 });
    await page.waitForFunction(b => Math.hypot(Field.hero.x - b.x, Field.hero.y - b.y) < 2.5, box);
    await page.evaluate(() => { const real = Mail.onUnread; Mail.onUnread = (c, t) => real(c, Math.max(t ?? 0, 1)); Mail.onUnread(0, 1); });   // the icon only exists while you have mail: pretend one letter, the snapshots say none
    await page.locator('#mail-open').click();
    await page.locator('#mail-panel').waitFor({ state: 'visible', timeout: 10000 });
    check(await page.locator('#mail-panel').isVisible(), 'clicking the mail icon beside a mailbox opens the mail window');
    await page.locator('#mail-close').click();
    assert.equal(errors.length, 0, `Page errors: ${errors.join('; ')}`);
    await ctx.close();
    console.log(`PASS bank-mail-cells-ui (${checks} checks)`);
  } finally {
    await browser.close().catch(() => {});
    await world.stop().catch(() => {});
  }
})().catch(err => { console.error(err); process.exit(1); });
