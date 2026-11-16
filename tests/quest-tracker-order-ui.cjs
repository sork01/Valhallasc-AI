// The quest tracker on the left of the screen shows each quest's level ("[3] Title") and lists the quests by level, lowest first,
// whatever order they were taken in. MUTATE=order puts the old sort back (ready last, tracked first, else catalogue order),
// MUTATE=level drops the level from the title; each must fail.
// Run: bash scripts/test-touch-bounded.sh tests/quest-tracker-order-ui.cjs
const assert = require('node:assert/strict');
const path = require('node:path');
const { requireMemoryLimit } = require('./lib/touch.cjs'); requireMemoryLimit();
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const root = path.resolve(__dirname, '..');

(async () => {
  const world = new TestWorld(root, { env: { VALHALLA_LEVEL_SPREAD: '0' } });
  await world.start();
  const browser = await chromium.launch({ headless: true });
  const errors = [];
  let checks = 0;
  const check = (cond, msg) => { assert.ok(cond, msg); checks++; };
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    page.on('pageerror', e => errors.push(e.message));
    if (process.env.MUTATE) {
      await page.route('**/quests.js*', async route => {
        const response = await route.fetch(); let text = await response.text(); const before = text;
        if (process.env.MUTATE === 'order') text = text.replace("(a.level || 0) - (b.level || 0) || definitions.indexOf(a) - definitions.indexOf(b)", "Number(status(a) === 'ready') - Number(status(b) === 'ready') || Number(b.id === tracked) - Number(a.id === tracked)");
        if (process.env.MUTATE === 'level') text = text.replace("button(`[${quest.level}] ${quest.title}`,", "button(quest.title,");
        assert.notEqual(text, before, 'mutation target exists');
        await route.fulfill({ response, body: text });
      });
    }
    await page.addInitScript(() => {
      window.AudioContext = undefined; window.webkitAudioContext = undefined;
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {}, char: null, draft: null }));
    });
    await page.goto(world.url);
    await page.locator('#start').click();
    await page.locator('#login-guest').click();
    await page.locator('#name').fill('Tracker');
    await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
    if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
    await page.evaluate(() => { const tip = document.getElementById('tutorial-tip'); if (tip && !tip.hidden) document.getElementById('tutorial-disable')?.click(); });

    // Three ordinary Greenmeadow quests of different levels, taken from the highest level down.
    const picks = await page.evaluate(() => {
      const ok = WORLD_MAP.quests.filter(q => !q.autoLevel && !q.requires && !q.handoffTo && !q.landing && !q.min_level && !q.minLevel && Number.isFinite(q.level) && !/^(es_|halloween_|christmas_|easter_|solstice_|newyear_|valentine_)/.test(q.id));
      const byLevel = new Map(); for (const q of ok) if (!byLevel.has(q.level)) byLevel.set(q.level, q);
      return [...byLevel.values()].sort((a, b) => b.level - a.level).slice(0, 3).map(q => ({ id: q.id, title: q.title, level: q.level }));
    });
    check(picks.length === 3 && new Set(picks.map(p => p.level)).size === 3, `the fixture has three quests of different levels: ${JSON.stringify(picks)}`);
    for (const q of picks) {
      await page.evaluate(id => Online.send({ type: 'debug', command: { op: 'quest', id, action: 'accept' } }), q.id);
      await page.waitForTimeout(400);
    }
    await page.waitForFunction(ids => ids.every(id => document.querySelector(`#quest-tracker [data-quest="${id}"]`)), picks.map(q => q.id), { timeout: 15000 });
    // Track the highest-level quest: the old sort put the tracked quest first, so the new order must not depend on it.
    const highest = picks[0];
    const trackButton = page.locator(`#quest-tracker [data-quest="${highest.id}"] .tracker-track`);
    if (await trackButton.getAttribute('aria-pressed') !== 'true') await trackButton.click();
    await page.waitForFunction(id => document.querySelector(`#quest-tracker [data-quest="${id}"] .tracker-track`)?.getAttribute('aria-pressed') === 'true', highest.id, { timeout: 5000 });
    const rows = await page.evaluate(() => [...document.querySelectorAll('#quest-tracker .tracker-quest')].map(r => ({ id: r.dataset.quest, title: r.querySelector('.tracker-title')?.textContent.trim() })));
    const mine = rows.filter(r => picks.some(p => p.id === r.id));
    const expected = [...picks].sort((a, b) => a.level - b.level);
    check(JSON.stringify(mine.map(r => r.id)) === JSON.stringify(expected.map(p => p.id)), `the tracker lists the quests by level, lowest first: ${JSON.stringify(mine.map(r => r.title))}`);
    for (const p of expected) check(mine.find(r => r.id === p.id)?.title === `[${p.level}] ${p.title}`, `${p.id} shows its level in the tracker`);
    // Every row of the tracker (the three and any automatic quests) is in ascending level order overall.
    const levels = await page.evaluate(() => [...document.querySelectorAll('#quest-tracker .tracker-title')].map(b => Number((/^\[(\d+)\]/.exec(b.textContent.trim()) || [])[1])));
    check(levels.every(Number.isFinite) && levels.every((l, i) => i === 0 || levels[i - 1] <= l), `the whole tracker is in level order: ${JSON.stringify(levels)}`);
    assert.equal(errors.length, 0, `Page errors: ${errors.join('; ')}`);
    console.log(`PASS quest-tracker-order-ui (${checks} checks)`);
  } finally {
    await browser.close().catch(() => {});
    await world.stop().catch(() => {});
  }
})().catch(err => { console.error(err); process.exit(1); });
