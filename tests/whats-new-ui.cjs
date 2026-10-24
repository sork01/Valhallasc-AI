// UI-WHATS-NEW: real browser, private Rust world, no grinding or public guests.
// MUTATE=1 removes the saved acknowledgement: the repeat-visit assertion must fail.
process.env.TEST_WHATS_NEW = '1';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const root = path.resolve(__dirname, '..'), world = new TestWorld();
const entries = JSON.parse(fs.readFileSync(path.join(root, 'client/release-notes.txt'), 'utf8'));
const current = entries[0].version, storage = 'valhallasc.whats-new.v1';
let browser, checks = 0;
const errors = [];
const check = (ok, text) => { assert.ok(ok, text); checks++; console.log(text); };
const shown = page => page.locator('#whats-new').isVisible();
const waitOpen = page => page.locator('#whats-new').waitFor({ state: 'visible' });
async function settle(page) {
  await page.waitForLoadState('networkidle');
}
async function seed(page, lang, seen = 'Beta 1.14.33') {
  await page.addInitScript(({ lang, seen, storage }) => {
    if (sessionStorage.getItem('seeded-news')) return;
    sessionStorage.setItem('seeded-news', '1');
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang, sound: false, char: null, draft: null }));
    if (seen) localStorage.setItem(storage, seen);
  }, { lang, seen, storage });
}
async function newPage() {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce', locale: 'en-GB' });
  page.on('pageerror', error => errors.push(error.message));
  if (process.env.MUTATE === '1') await page.route('**/whatsnew.js', route => {
    const src = fs.readFileSync(path.join(root, 'client/whatsnew.js'), 'utf8');
    const body = src.replace('localStorage.setItem(STORAGE, current);', '/* acknowledgement removed */');
    assert.notEqual(body, src, 'Mutation applied');
    return route.fulfill({ body, contentType: 'text/javascript' });
  });
  return page;
}
(async () => {
  await world.start(); browser = await chromium.launch({ headless: true });
  const page = await newPage();
  await page.goto(world.url); await waitOpen(page);
  check(await page.locator('#news-title').textContent() === current, 'The dialog title is the current version');
  check(await page.locator('#news-body').textContent().then(text => /Welcome to Valhalla Rumble/.test(text) && /Greenmeadow/.test(text) && /Linden/.test(text)), 'First visit shows the welcome and where to begin');
  check(await page.locator('#news-body kbd').allTextContents().then(keys => keys.join(',') === 'W,A,S,D,Space,F,Q'), 'Welcome controls come from the current key map');
  await page.evaluate(() => { Keys.bind('moveUp', 0, 'KeyR'); Keys.bind('attack', 0, 'KeyV'); Keys.bind('talk', 0, 'KeyT'); Keys.bind('quests', 0, 'KeyU'); });
  check(await page.locator('#news-body kbd').allTextContents().then(keys => keys.join(',') === 'R,A,S,D,V,T,U'), 'Welcome controls follow changed bindings while it is open');
  check(await page.locator('#news-close').evaluate(el => el === document.activeElement), 'Close receives focus');
  await page.keyboard.press('Tab');
  check(await page.evaluate(() => !!document.activeElement.closest('#whats-new, .win-grip[data-window="whats-new"]')), 'Tab stays inside the window and its grip');
  await page.keyboard.press('Enter');
  check(!(await shown(page)) && await page.locator('#stage').getAttribute('data-scene') === 'splash', 'Enter closes without activating the title screen');
  await page.reload(); await settle(page);
  check(!(await shown(page)), 'The current version is remembered after a welcome and reload');

  await page.evaluate(storage => localStorage.setItem(storage, 'Beta 1.14.33'), storage);
  await page.reload(); await waitOpen(page);
  check(await page.locator('#news-label').textContent() === "What's new", 'A changed version shows the latest notes');
  check(await page.locator('#news-body > ul li').allTextContents().then(texts => JSON.stringify(texts) === JSON.stringify(entries[0].new)), 'The latest notes show the exact English prose from the notes file');
  await page.locator('.news-history > summary').click();
  check(await page.locator('.news-history details > summary').allTextContents().then(versions => JSON.stringify(versions) === JSON.stringify(entries.slice(1).map(entry => entry.version))), 'Older updates lists every archived version');
  await page.locator('.news-history details > summary').first().click();
  check(await page.locator('.news-history details').first().innerText().then(text => /selling window/.test(text) && /Removed/.test(text) && /so you can/.test(text)), 'An older update opens with lists and the reason for its removal');
  const text = await page.locator('#news-body').innerText();
  check(!/\b(?:const|function|undefined|localStorage|protocol|binary|Rust|MCP)\b|\w+\.(?:js|rs)\b/.test(text), 'The visible notes contain everyday language');
  await page.locator('#news-close').click();
  await page.reload(); await settle(page);
  check(!(await shown(page)), 'Close and reload do not show the same release again');
  check(await page.evaluate(storage => localStorage.getItem(storage), storage) === current, 'Seen version uses its own Valhallasc storage key');

  // Join a real private world, then use the actual Settings row.
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-mage').click(); await page.locator('#name').fill('Newsreader'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.mageSprites, null, { timeout: 60000 });
  await page.keyboard.press('Escape'); await page.locator('#p-settings').click();
  await page.locator('#set-whats-new').click(); await waitOpen(page);
  check(await page.locator('#news-label').textContent() === "What's new", 'Settings reopens the latest notes instead of the welcome');
  check(await page.evaluate(() => [...document.querySelectorAll('.panel-grip, .win-grip:not([data-window="whats-new"])')].every(el => getComputedStyle(el).visibility === 'hidden')), 'Other windows and HUD grips stay behind the notes');
  await page.keyboard.press('u');
  check(!(await page.locator('#quest-journal').isVisible()) && await shown(page), 'Gameplay shortcuts do not open windows behind the notes');
  const beforeScale = await page.locator('.news-panel').evaluate(el => el.getBoundingClientRect().width);
  await page.evaluate(() => { Prefs.set({ uiScale: 1 }); Settings.applyScale(); });
  check(await page.locator('.news-panel').evaluate(el => el.getBoundingClientRect().width) > beforeScale * 1.15, 'The window follows the global UI size');
  await page.evaluate(() => Settings.sizeWindow('whats-new', .85));
  check(await page.locator('.news-panel').evaluate(el => Math.abs(parseFloat(getComputedStyle(el).scale) - .85) < .01), 'The window has its own saved scale');
  const grip = page.locator('.win-grip[data-window="whats-new"]');
  await grip.focus(); await page.keyboard.press('ArrowLeft');
  check(await page.evaluate(() => Prefs.winScale['whats-new'] < .85), 'The corner grip can resize the window by keyboard');
  await page.keyboard.press('Escape');
  check(!(await shown(page)) && await page.locator('#settings-panel').isVisible(), 'Esc closes only the notes and returns to Settings');
  check(await page.locator('#set-whats-new').evaluate(el => el === document.activeElement), 'Closing restores focus to the Settings row');
  await page.locator('#set-whats-new').click(); await waitOpen(page);
  await page.setViewportSize({ width: 844, height: 390 });
  await page.locator('.news-history > summary').click();
  await page.locator('.news-history details > summary').last().click();
  await page.locator('.news-history details').last().locator('li').last().scrollIntoViewIfNeeded();
  const fit = await page.evaluate(() => {
    const box = document.querySelector('.news-panel').getBoundingClientRect(), stage = document.querySelector('#stage').getBoundingClientRect();
    const close = document.querySelector('#news-close').getBoundingClientRect();
    return box.top >= stage.top - 1 && box.bottom <= stage.bottom + 1 && close.bottom <= stage.bottom && box.left >= stage.left && box.right <= stage.right;
  });
  check(fit && await page.locator('#news-close').isVisible(), 'On a short phone screen the notes scroll and Close stays inside the stage');
  await page.screenshot({ path: path.join(world.runDir, 'whats-new-phone.png') });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.locator('#news-body').evaluate(el => { el.scrollTop = 0; });
  await page.screenshot({ path: path.join(world.runDir, 'whats-new-history.png') });
  await page.keyboard.press('Enter');

  const returning = await newPage(); await seed(returning, 'en', null);
  await returning.goto(world.url); await waitOpen(returning);
  check(await returning.locator('#news-label').textContent() === "What's new", 'A browser with an old game save gets release notes on first rollout');
  await returning.close();

  const sv = await newPage(); await seed(sv, 'sv');
  await sv.goto(world.url); await waitOpen(sv);
  check(await sv.locator('#news-label').textContent() === "What's new" && await sv.locator('#news-close').textContent() === 'Close', 'Swedish players see the window labels in English');
  check(await sv.locator('#news-body > h3').textContent() === 'New' && await sv.locator('#news-body > ul li').allTextContents().then(texts => JSON.stringify(texts) === JSON.stringify(entries[0].new)), 'Swedish does not translate the notes or section headings');
  await sv.locator('.news-history > summary').click(); await sv.locator('.news-history details > summary').last().click();
  check(await sv.locator('.news-history details').last().locator('h3').allTextContents().then(texts => texts.includes('Changed') && texts.includes('Removed')), 'Changed and Removed also stay English in history');
  check(await sv.locator('#set-whats-new').textContent() === "What's new", 'The Settings row stays English while the rest of Settings uses Swedish');
  await sv.keyboard.press('Escape');
  await sv.evaluate(storage => { localStorage.removeItem(storage); localStorage.removeItem('valhallasc.save.v1'); }, storage);
  // Use browser language for a genuine first visit without an existing save.
  await sv.context().setExtraHTTPHeaders({ 'Accept-Language': 'sv-SE' });
  await sv.addInitScript(() => Object.defineProperty(navigator, 'language', { value: 'sv-SE' }));
  await sv.reload(); await waitOpen(sv);
  check(await sv.locator('#news-body h3').textContent() === 'Welcome to Valhalla Rumble!' && await sv.locator('#news-close').textContent() === 'Close', 'A new Swedish player gets the English welcome too');
  await sv.close();

  const unavailable = await newPage(); await seed(unavailable, 'en');
  await unavailable.route('**/release-notes.txt', route => route.fulfill({ status: 503, body: 'Unavailable' }));
  await unavailable.goto(world.url); await settle(unavailable);
  check(!(await shown(unavailable)) && await unavailable.evaluate(storage => localStorage.getItem(storage), storage) === 'Beta 1.14.33', 'Unavailable notes leave the game usable and the release unseen');
  await unavailable.unroute('**/release-notes.txt');
  await unavailable.evaluate(() => WhatsNew.show()); await waitOpen(unavailable);
  check(await unavailable.locator('#news-title').textContent() === current, 'Opening again retries a failed notes request');
  await unavailable.close();
  check(errors.length === 0, `No browser errors: ${errors.join(' | ')}`);
  console.log(`whats-new-ui: ${checks} checks passed; screenshots: ${world.runDir}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => { await browser?.close(); await world.stop(); });
