// Focused private browser check for the Character pane tabs (desktop + touch + keyboard + Swedish).
const assert = require('node:assert/strict');
const { replace, debug, requireMemoryLimit } = require('./lib/touch.cjs');
requireMemoryLimit();
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');

const TABS = [
  ['stats', 'Character & stats', '#character-pane-stats', 'Karaktär & attribut'],
  ['sets', 'Dungeon sets', '#character-sets', 'Dungeon-set'],
  ['achievements', 'Achievements', '#character-achievements', 'Prestationer'],
  ['professions', 'Professions', '#character-professions', 'Yrken'],
  ['mounts', 'Mounts', '#character-mounts', 'Riddjur'],
  ['rebirth', 'Rebirth', '#character-rebirth', 'Pånyttfödelse'],
];

async function enter(browser, world, { lang = 'en', touch = false, name = 'TabTesterEn' } = {}, errors) {
  const opts = touch
    ? { viewport: { width: 844, height: 390 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true, reducedMotion: 'reduce' }
    : { viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' };
  const page = await browser.newPage(opts);
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(l => {
    window.AudioContext = undefined;
    window.webkitAudioContext = undefined;
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: l, sound: false, touchGraphicsSuggested: true, char: null, draft: null }));
  }, lang);
  if (process.env.MUTATE === 'stale-skills') {
    await replace(page, 'field.js', 'window.CharacterPane?.updateProfessions?.(own.professions);', '');
  }
  await page.goto(world.url);
  await page.locator('#start').click();
  await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click();
  await page.locator('#name').fill(name);
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  await page.evaluate(() => window.Tutorial?.disable?.());
  return page;
}

(async () => {
  const world = new TestWorld();
  let browser;
  let checks = 0;
  const check = (cond, msg) => { assert.ok(cond, msg); checks++; };
  try {
    await world.start();
    browser = await chromium.launch({ headless: true });
    const errors = [];

    // 1. Desktop English: tab order, exclusivity, keyboard navigation, World Menu Achievements, bag toggle.
    const page = await enter(browser, world, { lang: 'en', touch: false }, errors);
    const smith = await page.evaluate(() => WORLD_MAP.npcs.find(npc => npc.id === 'smith'));
    await debug(page, { op: 'teleport', zone: 0, x: smith.x, y: smith.y });
    await page.waitForFunction(({x,y}) => Math.hypot(Field.hero.nx-x, Field.hero.ny-y) < 1, smith);
    await page.keyboard.press('e');
    await page.locator('#equipment').waitFor({ state: 'visible' });

    const tabLabels = await page.locator('#equipment .character-tab').allTextContents();
    check(JSON.stringify(tabLabels) === JSON.stringify(TABS.map(t => t[1])), `six character tabs in order: ${tabLabels.join(', ')}`);

    for (const [id, , selector] of TABS) {
      await page.locator(`#character-tab-${id}`).click();
      for (const [otherId, , otherSelector] of TABS) {
        const expected = id === otherId;
        check((await page.locator(`#character-tab-${otherId}`).getAttribute('aria-selected')) === String(expected), `${id}: tab ${otherId} aria-selected=${expected}`);
        check((await page.locator(otherSelector).isVisible()) === expected, `${id}: panel ${otherSelector} visible=${expected}`);
      }
      if (id === 'achievements') await page.waitForSelector('#character-achievements .achievement-card');
      check(await page.locator('.character-tabs').evaluate(n => n.scrollWidth <= n.clientWidth + 1), `${id}: tab strip does not overflow horizontally`);
    }

    // Keyboard tablist navigation (ArrowRight, ArrowLeft, End, Home).
    await page.locator('#character-tab-stats').click();
    await page.locator('#character-tab-stats').focus();
    await page.keyboard.press('ArrowRight');
    check(await page.evaluate(() => document.activeElement.id === 'character-tab-sets' && !document.getElementById('character-sets').hidden), 'ArrowRight moves to Dungeon sets');
    await page.keyboard.press('ArrowRight');
    check(await page.evaluate(() => document.activeElement.id === 'character-tab-achievements' && !document.getElementById('character-achievements').hidden), 'ArrowRight moves to Achievements');
    await page.keyboard.press('ArrowRight');
    check(await page.evaluate(() => document.activeElement.id === 'character-tab-professions' && !document.getElementById('character-professions').hidden), 'ArrowRight moves to Professions');
    const values = await page.locator('#profession-skills li').evaluateAll(rows => rows.map(row => [
      row.querySelector('span').textContent, row.querySelector('b').textContent, row.querySelector('progress').max, row.querySelector('progress').position,
    ]));
    check(JSON.stringify(values) === JSON.stringify([
      ['Fishing', '1 / 600', 600, 1/600], ['Blacksmithing and Mining', '0 / 600', 600, 0],
      ['Enchanting', '0 / 600', 600, 0], ['Alchemy', '0 / 600', 600, 0],
    ]), 'all four fresh skills show the correct caps');
    await page.evaluate(() => Online.send({ type: 'blacksmithing', request: { op: 'train', npc: 'smith' } }));
    await page.waitForFunction(() => Field.hero.professions?.blacksmithing?.skill === 1);
    const mining = page.locator('#profession-skills [data-profession="blacksmithing"]');
    check(await mining.locator('b').textContent() === '1 / 600' && await mining.locator('progress').evaluate(node => node.value === 1),
      'learning Blacksmithing updates the open tab from the next snapshot');
    await page.keyboard.press('End');
    check(await page.evaluate(() => document.activeElement.id === 'character-tab-rebirth' && !document.getElementById('character-rebirth').hidden), 'End moves to Rebirth');
    await page.keyboard.press('ArrowLeft');
    check(await page.evaluate(() => document.activeElement.id === 'character-tab-mounts' && !document.getElementById('character-mounts').hidden), 'ArrowLeft moves to Mounts');
    await page.keyboard.press('Home');
    check(await page.evaluate(() => document.activeElement.id === 'character-tab-stats' && !document.getElementById('character-pane-stats').hidden), 'Home moves to Character & stats');

    // Bag toggle preserves the active non-default tab.
    await page.locator('#character-tab-mounts').click();
    await page.locator('#bag-character').click();
    check(await page.locator('.character-window').isHidden(), 'Character button in bags hides character pane');
    await page.locator('#bag-character').click();
    check(await page.locator('#character-mounts').isVisible(), 'Re-showing character pane preserves active Mounts tab');

    // Reopening via E resets to Character & stats; World Menu -> Achievements opens Achievements tab.
    await page.keyboard.press('Escape');
    await page.locator('#equipment').waitFor({ state: 'hidden' });
    await page.keyboard.press('e');
    check(await page.locator('#character-pane-stats').isVisible() && await page.locator('#character-mounts').isHidden(), 'E opens Character & stats by default');
    await page.keyboard.press('Escape');
    await page.keyboard.press('Escape');
    await page.keyboard.press('e'); await page.locator('#character-tab-achievements').click();
    await page.waitForSelector('#character-achievements .achievement-card');
    check(await page.locator('#character-achievements').isVisible() && await page.locator('#character-pane-stats').isHidden(), 'the Achievements tab of the Character pane opens the achievements list');
    await page.locator('#equipment-close').click();
    await page.context().close();

    // 2. Touch Swedish (844x390): all six Swedish tab labels translate cleanly, hit >=44px touch targets, and never overflow.
    const svTouch = await enter(browser, world, { lang: 'sv', touch: true, name: 'TabTesterSv' }, errors);
    await svTouch.keyboard.press('e');
    await svTouch.locator('#equipment').waitFor({ state: 'visible' });
    const svLabels = await svTouch.locator('#equipment .character-tab').allTextContents();
    check(JSON.stringify(svLabels) === JSON.stringify(TABS.map(t => t[3])), `Swedish tabs: ${svLabels.join(', ')}`);
    const touchLayout = await svTouch.evaluate(() => [...document.querySelectorAll('#equipment .character-tab')].map(btn => {
      const r = btn.getBoundingClientRect();
      return { id: btn.id, w: r.width, h: r.height, overflow: btn.scrollWidth > btn.clientWidth + 1 };
    }));
    for (const t of touchLayout) {
      check(t.w >= 43.8 && t.h >= 43.8, `touch ${t.id} target ${t.w.toFixed(1)}x${t.h.toFixed(1)} >= 44px`);
      check(!t.overflow, `touch ${t.id} Swedish text fits without horizontal overflow`);
    }
    for (const [id, , selector] of TABS) {
      await svTouch.locator(`#character-tab-${id}`).click();
      if (id === 'achievements') await svTouch.waitForSelector('#character-achievements .achievement-card');
      const winFit = await svTouch.evaluate(sel => {
        const w = document.querySelector('#equipment .character-window');
        const p = document.querySelector(sel);
        return w.scrollWidth <= w.clientWidth + 1 && p.scrollWidth <= p.clientWidth + 1;
      }, selector);
      check(winFit, `touch ${id}: character pane and panel fit horizontally without overflow`);
    }
    await svTouch.setViewportSize({width:600, height:390});
    await svTouch.locator('#character-tab-professions').tap();
    check(await svTouch.locator('#profession-skills').isVisible(), 'Professions opens on a small landscape phone');
    const names = await svTouch.locator('#profession-skills li span').allTextContents();
    check(names.join(', ') === 'Fiske, Smide och gruvdrift, Förtrollning, Alkemi', 'all profession names translate into Swedish');
    check(await svTouch.locator('.character-tabs').evaluate(el => el.scrollWidth <= el.clientWidth + 1),
      'the sixth tab fits without clipping at 600 pixels');
    await svTouch.context().close();

    assert.deepEqual(errors, [], `page errors: ${errors.join('; ')}`);
    console.log(`Character pane tabs: ${checks} checks passed`);
  } finally {
    await browser?.close();
    await world.stop();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
