const assert = require('node:assert/strict');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const { playGuest } = require('./lib/guest.cjs');
const { requireMemoryLimit, sleep, touch } = require('./lib/touch.cjs');

requireMemoryLimit();

async function visibleTarget(control) {
  return control.evaluate(button => {
    const rect = button.getBoundingClientRect();
    const stage = document.querySelector('#stage').getBoundingClientRect();
    const x = rect.left + rect.width / 2, y = rect.top + rect.height / 2;
    const visible = rect.left >= stage.left && rect.right <= stage.right &&
      rect.top >= stage.top && rect.bottom <= stage.bottom && button.contains(document.elementFromPoint(x, y));
    return { x, y, visible, width: rect.width, height: rect.height };
  });
}

async function swipeUp(send, height) {
  const x = 20;
  await send('touchStart', [[1, x, Math.round(height * .85)]]);
  for (let step = 1; step <= 10; step++) {
    await send('touchMove', [[1, x, Math.round(height * (.85 - .07 * step))]]);
    await sleep(20);
  }
  await send('touchEnd', []);
}

(async () => {
  const world = new TestWorld();
  let browser;
  try {
    await world.start();
    for (const [width, height, mobile, lang] of [[740, 280, true, 'en'], [844, 390, true, 'sv'], [1280, 800, false, 'en']]) {
      browser = await chromium.launch({ headless: true });
      const page = await browser.newPage({ viewport: { width, height }, isMobile: mobile, hasTouch: mobile, reducedMotion: 'reduce' });
      await page.addInitScript(lang => {
        window.AudioContext = undefined;
        window.webkitAudioContext = undefined;
        if (!localStorage.getItem('valhallasc.save.v1'))
          localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang, sound: false, char: null, draft: null }));
      }, lang);
      const scene = page.locator('#scene-create');
      const enter = async () => {
        await page.locator('#start').click();
        await playGuest(page);
        await scene.waitFor();
      };
      await page.goto(world.url);
      await enter();
      const classes = ['warrior', 'mage', 'assassin', 'priest', 'hunter'];
      const targets = await Promise.all(classes.map(cls => visibleTarget(page.locator('#cls-' + cls))));
      assert.deepEqual(classes.filter((_, index) => !targets[index].visible), [], `${width}x${height}: all playable classes are visible before scrolling`);
      if (mobile) {
        for (const [index, target] of targets.entries()) {
          assert.ok(target.width >= 44 && target.height >= 44, `${classes[index]} has a full touch target`);
          await page.touchscreen.tap(target.x, target.y);
          assert.equal(await page.locator('#cls-' + classes[index]).getAttribute('aria-pressed'), 'true');
        }
        assert.ok(await scene.evaluate(node => node.scrollWidth === node.clientWidth), 'creator fits without horizontal scrolling');
        await page.locator('#create-turn-left').tap();
        assert.ok(await page.locator('.cc-turn').evaluate(node => node.scrollWidth === node.clientWidth), 'preview rotation and its facing label fit together');

        await page.locator('#name').fill('MobileHunter' + width);
        await page.locator('#create-race').selectOption('gnome');
        await page.locator('#gender-female').tap();
        await scene.evaluate(node => { node.scrollTop = 0; });
        const send = await touch(page);
        await swipeUp(send, height);
        await page.waitForFunction(() => document.querySelector('#scene-create').scrollTop > 100);
        const go = page.locator('#go');
        for (let i = 0; i < 4 && !(await visibleTarget(go)).visible; i++) await swipeUp(send, height);
        assert.ok((await visibleTarget(page.locator('#back'))).visible, 'a swipe reaches Back');
        const confirm = await visibleTarget(go);
        assert.ok(confirm.visible && confirm.height >= 44, 'a swipe reaches the full create button');
        await page.locator('#back').tap();
        await enter();
        assert.equal(await scene.evaluate(node => node.scrollTop), 0, 'the creator reopens at the class choices');
        assert.equal(await page.locator('#cls-hunter').getAttribute('aria-pressed'), 'true');
        assert.equal(await page.locator('#create-race').inputValue(), 'gnome');
        assert.equal(await page.locator('#gender-female').getAttribute('aria-pressed'), 'true');
        await go.tap();
        await page.waitForFunction(() => Online.connected && Field.hero?.look?.class === 'hunter' && Field.hero.look.race === 'gnome');
      } else {
        await page.locator('#cls-hunter').click();
        assert.ok((await visibleTarget(page.locator('#go'))).visible, 'desktop confirmation fits the stage');
      }
      console.log(`${width}x${height}: character creation layout passed`);
      await browser.close();
      browser = null;
    }
  } finally {
    await browser?.close();
    await world.stop();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
