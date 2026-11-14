// Focused private browser check for the five Character pane tabs (desktop + touch + keyboard + Swedish).
const assert = require('node:assert/strict');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');

const TABS = [
  ['stats', 'Character & stats', '#character-pane-stats', 'Karaktär & attribut'],
  ['sets', 'Dungeon sets', '#character-sets', 'Dungeon-set'],
  ['achievements', 'Achievements', '#character-achievements', 'Prestationer'],
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
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: l, sound: false, char: null, draft: null }));
  }, lang);
  await page.goto(world.url);
  const dismiss = page.locator('#low-gfx-dismiss');
  if (await dismiss.isVisible().catch(() => false)) await dismiss.click();
  await page.locator('#start').click();
  await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click();
  await page.locator('#name').fill(name);
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
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
    await page.keyboard.press('e');
    await page.locator('#equipment').waitFor({ state: 'visible' });

    const tabLabels = await page.locator('#equipment .character-tab').allTextContents();
    check(JSON.stringify(tabLabels) === JSON.stringify(TABS.map(t => t[1])), `five character tabs in order: ${tabLabels.join(', ')}`);

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

    // 2. Touch Swedish (844x390): all five Swedish tab labels translate cleanly, hit >=44px touch targets, and never overflow.
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
    await svTouch.context().close();

    assert.deepEqual(errors, [], `page errors: ${errors.join('; ')}`);
    console.log(`Character pane tabs: ${checks} checks passed`);
  } finally {
    await browser?.close();
    await world.stop();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
