// Browser check for SYSLOG-PICKUP-RARITY: item names on the System tab are drawn in their rarity colour.
// Run via: bash scripts/test-touch-bounded.sh tests/syslog-rarity-ui.cjs
// MUTATE=1 puts the plain-text line back (no mark): the run must fail.
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

async function openHero(context, world, { lang = 'en', name = 'MenuHero' } = {}) {
  const page = await context.newPage();
  await page.addInitScript(l => {
    window.AudioContext = undefined; window.webkitAudioContext = undefined;
    if (!localStorage.getItem('valhallasc.save.v1')) {
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: l, sound: false, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {}, char: null, draft: null }));
    }
  }, lang);
  await page.goto(world.url);
  await page.locator('#start').click();
  await page.locator('#login-guest').click();
  await page.locator('#name').fill(name);
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
  await page.evaluate(() => { const tip = document.getElementById('tutorial-tip'); if (tip && !tip.hidden) document.getElementById('tutorial-disable')?.click(); });
  return page;
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
      const page = await openHero(ctx, world, { lang, name: `Rarity${lang}` });
      page.on('pageerror', e => errors.push(e.message));
      const tag = s => `${lang}: ${s}`;
      if (process.env.MUTATE === '1') await page.evaluate(() => { const lines = SystemLog.lines; SystemLog.event = (p, me) => { for (const [t, c] of lines(p, me)) SystemLog.add(t, c); }; });
      const me = await page.evaluate(() => Online.id);
      const run = (event) => page.evaluate(([e, id]) => { document.getElementById('system-log').innerHTML = ''; SystemLog.event({ type: 'event', actor: id, ...e }, id); const p = document.querySelector('#system-log p:last-child'); const s = p.querySelector('.sys-rarity'); return { text: p.textContent, html: p.innerHTML, span: s?.textContent || null, rarity: s?.dataset.rarity || null, color: s ? getComputedStyle(s).color : null, base: getComputedStyle(p).color, cls: p.className }; }, [event, me]);
      const gear = await page.evaluate(() => { const rank = r => (window.WORLD_ITEMS.find(i => i.rarity === r && i.kind !== 'bag' && i.kind !== 'material' && i.sell > 0)); return { rare: rank('rare')?.id, epic: rank('epic')?.id, common: rank('common')?.id }; });
      check(gear.rare && gear.epic && gear.common, tag('the catalogue has common, rare and epic items'));
      const rare = await run({ kind: 'itemPickup', item: gear.rare, quantity: 1, name: 'Probe <b>Piece</b>', rarity: 'rare' });
      check(rare.span && /Probe/.test(rare.span) && rare.rarity === 'rare', tag(`a blue piece shows its name in a rare span (${JSON.stringify(rare)})`));
      check(rare.color === 'rgb(77, 163, 255)', tag(`the rare span is blue (${rare.color})`));
      check(rare.base !== rare.color, tag('the sentence itself is not the item colour'));
      check(!/<b>/.test(rare.html), tag('the item name is data, never HTML'));
      const epic = await run({ kind: 'itemPickup', item: gear.epic, quantity: 2, name: 'Twin', rarity: 'epic' });
      check(epic.rarity === 'epic' && epic.color === 'rgb(194, 125, 255)', tag(`a purple piece is purple (${epic.color})`));
      check(lang === 'sv' ? /^Du plockar upp 2 × .*\.$/.test(epic.text) : epic.text === 'You pick up 2 × Twin.', tag(`the sentence stays plain, hand-written text (${epic.text})`));
      const copy = await run({ kind: 'itemPickup', item: gear.common, quantity: 1, name: 'Copy', rarity: 'epic' });
      check(copy.rarity === 'epic', tag('a rolled copy rarity wins over the catalogue base rarity'));
      const fallback = await run({ kind: 'itemPickup', item: gear.common, quantity: 1, name: 'Plain' });
      check(fallback.rarity === 'common' && fallback.color === 'rgb(196, 196, 196)', tag('with no rarity in the event the catalogue rarity is used'));
      const gold = await run({ kind: 'pickup', value: 250 });
      check(gold.span === null && gold.cls === 'sys-loot', tag(`gold lines stay plain (${gold.text})`));
      const xp = await run({ kind: 'slimeDie', enemy: 'green', level: 1, xp: 7 });
      check(xp.span === null && xp.cls === 'sys-xp', tag('XP lines stay plain'));
      const bad = await run({ kind: 'itemPickup', item: gear.rare, quantity: 1, name: 'Weird', rarity: 'x"><img src=x>' });
      check(bad.span === null && !/<img/.test(bad.html), tag('an unknown rarity falls back to the plain line'));
      const use = await page.evaluate(([id, me]) => { const pot = WORLD_ITEMS.find(i => i.kind === 'potion' && i.rarity && i.rarity !== 'common') || WORLD_ITEMS.find(i => i.kind === 'potion'); document.getElementById('system-log').innerHTML = ''; SystemLog.event({ type: 'event', actor: me, kind: 'consume', item: pot.id, value: 30 }, me); const s = document.querySelector('#system-log p .sys-rarity'); return { rarity: s?.dataset.rarity, want: pot.rarity }; }, [0, me]);
      check(use.rarity === use.want, tag(`a used potion is coloured too (${JSON.stringify(use)})`));
      await ctx.close();
    }
    assert.equal(errors.length, 0, `Page errors: ${errors.join('; ')}`);
    console.log(`PASS syslog-rarity-ui (${checks} checks)`);
  } finally {
    await browser.close().catch(() => {});
    await world.stop().catch(() => {});
  }
})().catch(err => { console.error(err); process.exit(1); });
