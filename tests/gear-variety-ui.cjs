// Browser check for GEAR-VARIETY-3X: all three variants (base, _b, _c) of ordinary world-drop gear load,
// render valid bag icons and distinct character/piece art+tints, and translate cleanly in Swedish.
// Run via: bash scripts/test-touch-bounded.sh tests/gear-variety-ui.cjs
// MUTATE=1 replaces WORLD_ITEMS with HEAD:client/items.js (no _b/_c variants) and must fail.
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
      const old = execFileSync('git', ['show', 'HEAD:client/items.js'], { cwd: root, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 });
      await page.route('**/items.js*', route => route.fulfill({ contentType: 'text/javascript', body: old }));
    }
    await page.addInitScript(() => {
      window.AudioContext = undefined; window.webkitAudioContext = undefined;
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {}, char: null, draft: null }));
    });
    const t0 = Date.now();
    await page.goto(world.url);
    await page.locator('#start').click();
    await page.locator('#login-guest').click();
    await page.locator('#name').fill('Varietist');
    await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
    const loadMs = Date.now() - t0;
    if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
    await page.evaluate(() => { const tip = document.getElementById('tutorial-tip'); if (tip && !tip.hidden) document.getElementById('tutorial-disable')?.click(); });

    const trio = ['warrior_armor_azure_l30_purple', 'warrior_armor_azure_l30_purple_b', 'warrior_armor_azure_l30_purple_c'];
    const debug = command => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);
    await debug({ op: 'set_level', level: 30 });
    await page.waitForFunction(() => Field.hero.level >= 30);
    for (const id of trio) await debug({ op: 'give_item', item: id, quantity: 1 });
    await page.waitForFunction(ids => ids.every(id => Inventory.bagQuantity(id) === 1), trio, { timeout: 10000 });

    await page.evaluate(() => CharacterPane.open('stats'));
    await page.locator('#inventory-list').waitFor({ state: 'visible' });

    const summary = await page.evaluate(ids => {
      const drawable = new Set(['armor', 'headgear', 'shoulders', 'gloves', 'weapon', 'cloak']);
      const bag = ids.map(id => {
        const it = WORLD_ITEMS.find(x => x.id === id);
        const cell = document.querySelector(`#inventory-list .inventory-item[data-item="${id}"]`);
        const icon = cell?.querySelector('.item-icon, canvas, img') || cell?.querySelector('.item-tile');
        const iconBg = icon ? getComputedStyle(icon).backgroundImage : '';
        const sv = window.SV_TEXT?.[it?.name];
        return { id, name: it?.name, sv, art: it?.art, tint: it?.tint, hasCell: !!cell, hasIcon: !!(icon && (icon.tagName !== 'DIV' || (iconBg && iconBg !== 'none'))) };
      });
      const ord = WORLD_ITEMS.filter(i => ['armor','headgear','shoulders','gloves','weapon','pants','necklace','accessory','cloak'].includes(i.kind)
        && !i.source && !i.starter && ['common','uncommon','rare','epic'].includes(i.rarity));
      let missingSv = 0, missingIcon = 0, missingArt = 0;
      const at = window.ITEM_ICONS?.at || {};
      for (const i of ord) {
        if (!window.SV_TEXT?.[i.name]) missingSv++;
        const hasIcon = !!(at[i.id] || (i.art && WORLD_ITEMS.some(o => o.kind === i.kind && o.class === i.class && o.variant === i.art && at[o.id])));
        if (!hasIcon) missingIcon++;
        if (drawable.has(i.kind) && !i.art && !i.variant) missingArt++;
      }
      const l10 = ['warrior_armor_crimson_l10_gray', 'warrior_armor_crimson_l10_gray_b', 'warrior_armor_crimson_l10_gray_c']
        .map(id => WORLD_ITEMS.find(x => x.id === id));
      return { bag, ordCount: ord.length, missingSv, missingIcon, missingArt, l10Arts: l10.filter(Boolean).map(s => s.art) };
    }, trio);

    check(summary.ordCount === 5940, `browser loaded 5,940 ordinary gear items (got ${summary.ordCount})`);
    check(summary.missingSv === 0, `0 missing Swedish strings across 5,940 items (got ${summary.missingSv})`);
    check(summary.missingIcon === 0, `0 missing inventory icons across 5,940 items (got ${summary.missingIcon})`);
    check(summary.missingArt === 0, `0 missing art/variant keys across drawable items (got ${summary.missingArt})`);
    for (const row of summary.bag) {
      check(row.hasCell && row.hasIcon, `rendered bag tile and icon for ${row.id}`);
      check(Boolean(row.sv && row.sv !== row.name), `Swedish translation present for ${row.id} (${row.name} -> ${row.sv})`);
      check(Boolean(row.art && row.tint), `sprite art & tint present for ${row.id}`);
    }
    check(new Set(summary.bag.map(r => JSON.stringify(r.tint))).size === 3, 'L30 epic trio has 3 distinct tints');
    check(new Set(summary.l10Arts).size === 2, `L10 armor trio alternates base class drawing (${summary.l10Arts.join(', ')})`);

    // Equip _b and check the hero's live worn look switches to the _b variant.
    await page.locator(`#inventory-list .inventory-item[data-item="${trio[1]}"] .item-tile`).dblclick();
    await page.waitForFunction(() => Field.hero.look.warriorArmor === 'azure_l30_purple_b', null, { timeout: 10000 });
    check(true, 'equipping _b updates hero worn look to azure_l30_purple_b');

    assert.equal(errors.length, 0, `Page errors: ${errors.join('; ')}`);
    await ctx.close();
    console.log(`PASS gear-variety-ui (${checks} checks, startup ${loadMs}ms)`);
  } finally {
    await browser.close().catch(() => {});
    await world.stop().catch(() => {});
  }
})().catch(err => { console.error(err); process.exit(1); });
