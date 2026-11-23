const assert = require('node:assert/strict');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const { playGuest } = require('./lib/guest.cjs');
const { replace, requireMemoryLimit } = require('./lib/touch.cjs');

requireMemoryLimit();
const world = new TestWorld();
world.startLevel = 1;

(async () => {
  let browser;
  try {
    await world.start();
    browser = await chromium.launch({ headless: true });
    for (const lang of ['en', 'sv']) {
      const touch = lang === 'sv';
      const context = await browser.newContext({
        viewport: touch ? { width: 844, height: 390 } : { width: 1280, height: 800 },
        isMobile: touch, hasTouch: touch, reducedMotion: 'reduce',
      });
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      if (process.env.MUTATE === 'draft') await replace(page, 'game.js',
        'const saveDraft = () => { save.draft = { ...cfg }; persist(); };',
        "const saveDraft = () => { save.draft = { ...cfg, race: 'human' }; persist(); };");
      await page.addInitScript(lang => {
        window.AudioContext = undefined;
        window.webkitAudioContext = undefined;
        if (!localStorage.getItem('valhallasc.save.v1'))
          localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang, sound: false, char: null, draft: null }));
      }, lang);
      const openGuest = async () => {
        await page.locator('#start').click();
        await playGuest(page);
      };
      await page.goto(world.url);
      await openGuest();
      const race = page.locator('#create-race');
      assert.equal(await race.inputValue(), 'human');
      assert.equal(await race.getAttribute('aria-label'), touch ? 'Folkslag' : 'Race');
      assert.deepEqual(await race.locator('option').allTextContents(),
        touch ? ['Människa', 'Nattfjärilsfolk'] : ['Human', 'Mothkin']);
      if (touch) assert.ok((await race.boundingBox()).height >= 44, 'race selector is a 44px touch target');
      const swatch = page.locator('button[data-k="skin"][data-v="0"]');
      const humanSwatch = await swatch.evaluate(button => button.style.getPropertyValue('--c'));
      await race.selectOption('mothkin');
      assert.notEqual(await swatch.evaluate(button => button.style.getPropertyValue('--c')), humanSwatch,
        'race choice replaces the appearance swatches');
      await race.selectOption('human');
      assert.equal(await swatch.evaluate(button => button.style.getPropertyValue('--c')), humanSwatch);
      await race.selectOption('mothkin');
      await page.locator('#cls-hunter').click();
      await page.locator('#gender-female').click();
      await page.locator('button[data-k="skin"][data-v="3"]').click();
      assert.equal(await race.inputValue(), 'mothkin', 'race survives class and body changes');
      await page.waitForFunction(() => window.valhalla?.sprites.hunterF?.look?.race === 'mothkin');
      await page.reload();
      await openGuest();
      assert.equal(await race.inputValue(), 'mothkin', 'race survives reloading the draft');
      assert.equal(await page.locator('button[data-k="skin"][data-v="3"]').getAttribute('aria-pressed'), 'true');
      await page.locator('#name').fill(touch ? 'NerisTouch' : 'NerisDesktop');
      await page.locator('#go').click();
      await page.waitForFunction(() => Online.connected && !!Field.hero?.look?.race);
      assert.equal(await page.evaluate(() => Field.hero.look.race), 'mothkin');
      assert.equal(await page.evaluate(() => Field.hero.look.class), 'hunter');
      assert.equal(await page.evaluate(() => Field.hero.look.skin), 3);
      await page.reload();
      await openGuest();
      await page.waitForFunction(() => Online.connected && Field.hero?.look?.race === 'mothkin');
      assert.deepEqual(errors, []);
      console.log(lang + ': race selection, draft, new guest and reconnect passed');
      await context.close();
    }
  } finally {
    if (browser) await browser.close();
    await world.stop();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
