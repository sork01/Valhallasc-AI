// The quest tracker on the left of the screen shows each quest's level ("[3] Title") and lists the quests by level, lowest first,
// within each zone until objective progress promotes them. Current zone and its dungeons come first. MUTATE=order puts the old sort back (ready last, tracked first, else catalogue order),
// MUTATE=level drops the level from the title; each must fail.
// Run: bash scripts/test-touch-bounded.sh tests/quest-tracker-order-ui.cjs
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
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
    const page = await browser.newPage({ viewport: process.env.TOUCH ? { width: 844, height: 390 } : { width: 1440, height: 900 }, hasTouch: !!process.env.TOUCH, isMobile: !!process.env.TOUCH, reducedMotion: 'reduce' });
    page.on('pageerror', e => errors.push(e.message));
    if (process.env.MUTATE) {
      await page.route('**/quests.js*', async route => {
        const response = await route.fetch(); let text = await response.text(); const before = text;
        if (process.env.MUTATE === 'order') text = text.replace("(a.level || 0) - (b.level || 0) || definitions.indexOf(a) - definitions.indexOf(b)", "Number(status(a) === 'ready') - Number(status(b) === 'ready') || Number(b.id === tracked) - Number(a.id === tracked)");
        if (process.env.MUTATE === 'dungeon') text = text.replace('areas[destination]?.copies ? destination : q.zone', 'q.zone');
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
    await page.evaluate(() => Online.send({ type: 'tutorial', command: { op: 'disable' } }));
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
    // Before progress, all these Greenmeadow quests still use ascending level order.
    const levels = await page.evaluate(() => [...document.querySelectorAll('#quest-tracker .tracker-title')].map(b => Number((/^\[(\d+)\]/.exec(b.textContent.trim()) || [])[1])));
    check(levels.every(Number.isFinite) && levels.every((l, i) => i === 0 || levels[i - 1] <= l), `the whole tracker is in level order: ${JSON.stringify(levels)}`);

    console.log('Baseline tracker levels passed; checking real collection progress');
    const debug = command => page.evaluate(command => Online.send({ type: 'debug', command }), command);
    await debug({ op: 'quest', id: 'fields_flour', action: 'accept' });
    await page.waitForSelector('#quest-tracker [data-quest="fields_flour"]');
    check(await page.locator('#quest-progress p').count() === 0, 'accepting quests is quiet');
    await debug({ op: 'give_item', item: 'slime_gel', quantity: 1 });
    await page.waitForFunction(() => document.querySelector('#quest-progress p')?.textContent === 'Slime Gel 1/4 (Quest)', null, { timeout: 10000 });
    check(await page.locator('.tracker-zone[data-zone="0"] .tracker-quest').first().getAttribute('data-quest') === 'fields_flour', 'a real material gain moves that quest first');
    const geo = await page.evaluate(() => {
      const stage = document.getElementById('stage').getBoundingClientRect(), line = document.querySelector('#quest-progress p'), r = line.getBoundingClientRect(), css = getComputedStyle(line);
      return { height: r.height, top: (r.top - stage.top) / stage.height, centre: (r.left + r.width / 2 - stage.left) / stage.width, color: css.color, border: css.borderTopWidth, background: css.backgroundColor, pe: getComputedStyle(line.parentElement).pointerEvents };
    });
    check(Math.abs(geo.top - .2) < .025 && Math.abs(geo.centre - .5) < .01, `progress is centered 20% down: ${JSON.stringify(geo)}`);
    check(geo.height >= 17 && geo.color === 'rgb(255, 210, 74)' && geo.border === '0px' && geo.background === 'rgba(0, 0, 0, 0)' && geo.pe === 'none', 'progress is plain yellow text that lets clicks through');
    fs.mkdirSync(world.runDir, { recursive: true });
    await page.screenshot({ path: path.join(world.runDir, `quest-progress${process.env.TOUCH ? '-touch' : ''}.png`) });
    await page.waitForTimeout(300);
    check(await page.locator('#quest-progress p').count() === 1, 'unchanged authoritative snapshots do not duplicate the notice');
    await page.waitForFunction(() => !document.querySelector('#quest-progress p'), null, { timeout: 5000 });
    check(true, 'progress expires');
    await page.evaluate(() => Prefs.set({ floatingText: { notices: false } }));
    await debug({ op: 'give_item', item: 'slime_gel', quantity: 1 });
    await page.waitForFunction(() => document.querySelector('[data-quest="fields_flour"] .tracker-objective')?.textContent.includes('2/4'));
    check(await page.locator('#quest-progress p').count() === 0, 'Other floating notices can hide quest text');
    await page.evaluate(() => Prefs.set({ floatingText: { notices: true } }));
    // Skip only prerequisite time in this disposable world; no encounter grinding.
    await debug({ op: 'set_level', level: 40 });
    for (const id of ['sky_welcome', 'deep_welcome']) await debug({ op: 'quest', id, action: 'finish' });
    for (const id of ['sky_hounds', 'sky_golems', 'span_toll', 'span_spectrum', 'deep_draugr']) {
      console.log(`Accepting ${id}`);
      await debug({ op: 'quest', id, action: 'accept' });
      await page.waitForSelector(`#quest-tracker [data-quest="${id}"]`);
    }
    await debug({ op: 'teleport', zone: 7, x: 187, y: 204 });
    await page.waitForFunction(() => Field.zone === 7 && document.querySelector('.tracker-zone')?.dataset.zone === '7', null, { timeout: 15000 });
    const groups = await page.evaluate(() => [...document.querySelectorAll('.tracker-zone')].map(g => ({ zone: +g.dataset.zone, title: g.querySelector('h3').textContent, quests: [...g.querySelectorAll('.tracker-quest')].map(q => q.dataset.quest) })));
    check(groups[0].title === 'Bifrost Reach' && groups[0].quests.includes('sky_hounds') && !groups[0].quests.includes('span_toll'), 'regular Bifrost quests are first');
    check(groups[1].title === 'The Shattered Span' && groups[1].quests.includes('span_toll') && groups[1].quests.includes('span_spectrum'), 'Span quests have their own category directly below Bifrost');
    check(groups.find(g => g.zone === 8)?.title === "Rán's Deep" && groups.find(g => g.zone === 8)?.quests.includes('deep_draugr'), "Rán's Deep quests have their own category");
    await debug({ op: 'quest', id: 'sky_golems', action: 'complete' });
    await page.waitForFunction(() => document.querySelector('.tracker-zone[data-zone="7"] .tracker-quest')?.dataset.quest === 'sky_golems');
    check(await page.locator('.tracker-zone[data-zone="7"] .tracker-quest').first().getAttribute('data-status') === 'ready', 'updated ready quest rises within its zone');
    await page.screenshot({ path: path.join(world.runDir, `quest-zones${process.env.TOUCH ? '-touch' : ''}.png`) });
    await debug({ op: 'quest', id: 'deep_draugr', action: 'complete' });
    await page.waitForFunction(() => document.querySelector('[data-quest="deep_draugr"]')?.dataset.status === 'ready');
    check(await page.locator('.tracker-zone').first().getAttribute('data-zone') === '7', 'remote progress keeps Bifrost first');
    await debug({ op: 'teleport', zone: 8, x: 200, y: 200 });
    await page.waitForFunction(() => Field.zone === 8 && document.querySelector('.tracker-zone')?.dataset.zone === '8', null, { timeout: 15000 });
    check(true, 'entering a new zone immediately puts its category first');
    await page.evaluate(() => { Announce.show('one', 'quest-progress'); Announce.show('two', 'quest-progress'); Announce.show('three', 'quest-progress'); Announce.show('four', 'quest-progress'); });
    check(await page.locator('#quest-progress p').count() === 3, 'rapid progress keeps a bounded stack');
    await page.evaluate(() => Quests.reset());
    check(await page.locator('#quest-progress p').count() === 0, 'character reset clears quest notices');
    console.log(`Screenshots: ${world.runDir}`);

    assert.equal(errors.length, 0, `Page errors: ${errors.join('; ')}`);
    console.log(`PASS quest-tracker-order-ui (${checks} checks)`);
  } finally {
    await browser.close().catch(() => {});
    await world.stop().catch(() => {});
  }
})().catch(err => { console.error(err); process.exit(1); });
