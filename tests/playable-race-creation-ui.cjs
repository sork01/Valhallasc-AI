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
      if (process.env.MUTATE === 'shadow') await replace(page, 'field.js',
        'g.scale(...mageSpr.bodyScale);', 'g.scale(1, 1);');
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
        touch ? ['Människa', 'Nattfjärilsfolk', 'Tidvattenfolk', 'Gnom'] : ['Human', 'Mothkin', 'Tidekin', 'Gnome']);
      if (touch) assert.ok((await race.boundingBox()).height >= 44, 'race selector is a 44px touch target');
      const swatch = page.locator('button[data-k="skin"][data-v="0"]');
      const humanSwatch = await swatch.evaluate(button => button.style.getPropertyValue('--c'));
      await race.selectOption('mothkin');
      const mothkinSwatch = await swatch.evaluate(button => button.style.getPropertyValue('--c'));
      assert.notEqual(mothkinSwatch, humanSwatch, 'Mothkin have their own skin palette');
      await race.selectOption('human');
      assert.equal(await swatch.evaluate(button => button.style.getPropertyValue('--c')), humanSwatch);
      await race.selectOption('tidekin');
      const tidekinSwatch = await swatch.evaluate(button => button.style.getPropertyValue('--c'));
      assert.notEqual(tidekinSwatch, humanSwatch, 'Tidekin have their own skin palette');
      assert.notEqual(tidekinSwatch, mothkinSwatch, 'Tidekin and Mothkin use different skin palettes');
      await race.selectOption('gnome');
      assert.equal(await swatch.evaluate(button => button.style.getPropertyValue('--c')), humanSwatch,
        'Gnomes can use the usual skin palette');
      await page.locator('#cls-assassin').click();
      await page.locator('#gender-female').click();
      await page.locator('button[data-k="skin"][data-v="3"]').click();
      assert.equal(await race.inputValue(), 'gnome', 'race survives class and body changes');
      await page.waitForFunction(() => window.valhalla?.sprites.assassinF?.look?.race === 'gnome');
      assert.deepEqual(await page.evaluate(() => valhalla.sprites.assassinF.bodyScale), [.76, .67]);
      await page.reload();
      await openGuest();
      assert.equal(await race.inputValue(), 'gnome', 'race survives reloading the draft');
      assert.equal(await page.locator('button[data-k="skin"][data-v="3"]').getAttribute('aria-pressed'), 'true');
      await page.locator('#name').fill(touch ? 'GnomeTouch' : 'GnomeDesktop');
      await page.locator('#go').click();
      await page.waitForFunction(() => Online.connected && !!Field.hero?.look?.race);
      assert.equal(await page.evaluate(() => Field.hero.look.race), 'gnome');
      assert.equal(await page.evaluate(() => Field.hero.look.class), 'assassin');
      assert.equal(await page.evaluate(() => Field.hero.look.skin), 3);
      if (!touch) {
        await page.waitForFunction(() => !!Field.assassinSprites);
        const shadow = await page.evaluate(() => {
          const sprite = Field.assassinSprites, shadow = sprite.frame('walk', 0, 0);
          const prototype = CanvasRenderingContext2D.prototype, drawImage = prototype.drawImage;
          const effect = { kind: 'shadow', x: Field.hero.x, y: Field.hero.y, dir: 0, frame: 0, t: 0 };
          let result = null;
          prototype.drawImage = function(image, x, y, ...rest) {
            if (image === shadow && Math.abs(this.globalAlpha - .35) < .001) {
              const { a, d } = this.getTransform();
              result = { ratio: a / d, x, y, anchor: sprite.meta.anchor };
            }
            return drawImage.call(this, image, x, y, ...rest);
          };
          Field._debug.effects.push(effect);
          try { Field._debug.drawFrame(performance.now() / 1000); }
          finally {
            Field._debug.effects.splice(Field._debug.effects.indexOf(effect), 1);
            prototype.drawImage = drawImage;
          }
          return result;
        });
        assert.ok(shadow && Math.abs(shadow.ratio - .76 / .67) < 1e-6, 'Shadowstep afterimage uses the Gnome body scale');
        assert.deepEqual([shadow.x, shadow.y], shadow.anchor.map(value => -value), 'Shadowstep keeps the foot anchor');
      }
      await page.reload();
      await openGuest();
      await page.waitForFunction(() => Online.connected && Field.hero?.look?.race === 'gnome');
      assert.deepEqual(errors, []);
      console.log(lang + ': race selection, draft, new guest and reconnect passed');
      await context.close();
    }
  } finally {
    if (browser) await browser.close();
    await world.stop();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
