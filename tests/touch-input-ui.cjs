const { run, replace, safeSpot, record, touch } = require('./lib/touch.cjs');
const suite = {
  name: 'touch-input',
  mutate: page => replace(page, 'field.js', 'let [x, y] = touchDirection;', 'let [x, y] = [0, 0];'),
  async test({ player, check, width, height, sleep }) {
    const page = await player('TouchInput'); await safeSpot(page); await record(page);
    check(await page.evaluate(() => matchMedia('(pointer: coarse)').matches), 'coarse pointer is emulated');
    check(await page.locator('#touch-stick').isVisible(), 'the stick is visible on touch');
    const box = await page.locator('#touch-stick').boundingBox(), x = box.x + box.width / 2, y = box.y + box.height / 2;
    const send = await touch(page), position = () => page.evaluate(() => [Field.hero.nx, Field.hero.ny]);
    const start = await position();
    await send('touchStart', [[1, x, y]]); await send('touchMove', [[1, x + 40, y]]);
    await page.waitForFunction(start => Math.hypot(Field.hero.nx - start[0], Field.hero.ny - start[1]) > 1, start, { timeout: 4000 });
    check(await page.evaluate(() => touchSent.some(m => m.type === 'input' && m.dx > .5 && m.dy < -.5)), 'stick enters the keyboard isometric input path');
    await send('touchEnd', []); await sleep(400); const stop = await position(); await sleep(400);
    check(Math.hypot(...(await position()).map((v, i) => v - stop[i])) < .15, 'release stops server movement');
    check(await page.evaluate(() => !document.querySelector('#touch-stick').classList.contains('held')), 'release clears the stick');
    for (const end of ['cancel', 'blur', 'hidden']) {
      await send('touchStart', [[1, x, y]]); await send('touchMove', [[1, x + 38, y]]); await sleep(150);
      if (end === 'cancel') await send('touchCancel', []);
      else {
        await page.evaluate(mode => {
          if (mode === 'blur') dispatchEvent(new Event('blur'));
          else { Object.defineProperty(document, 'hidden', { configurable: true, value: true }); document.dispatchEvent(new Event('visibilitychange')); }
        }, end); await send('touchEnd', []);
      }
      await sleep(350); const endPos = await position(); await sleep(350);
      check(Math.hypot(...(await position()).map((v, i) => v - endPos[i])) < .15, `${end} stops server movement`);
      check(await page.evaluate(() => !document.querySelector('#touch-stick').classList.contains('held')), `${end} clears capture state`);
      if (end === 'hidden') await page.evaluate(() => { delete document.hidden; document.dispatchEvent(new Event('visibilitychange')); });
    }
    await page.evaluate(() => { touchSent.length = 0; });
    await page.touchscreen.tap(width * .54, height * .62);
    check(await page.evaluate(() => touchSent.some(m => m.type === 'move')), 'ordinary ground tap still routes');
    await safeSpot(page); await page.evaluate(() => { touchSent.length = 0; });
    await page.touchscreen.tap(x, y);
    check(await page.evaluate(() => touchSent.some(m => m.type === 'move')), 'tap within the movement area still routes');
    await safeSpot(page); await page.evaluate(() => { touchSent.length = 0; });
    await send('touchStart', [[1, x, y]]); await send('touchMove', [[1, x + 4, y + 2]]); await sleep(300);
    check(await page.evaluate(() => !touchSent.some(m => m.type === 'input' && (m.dx || m.dy))), 'dead zone ignores tiny movements');
    await send('touchCancel', []);
    await page.locator('#touch-actions [data-action="chat"]').click();
    check(await page.locator('#chat-input').evaluate(n => document.activeElement === n), 'touch Chat opens and focuses the composer');
    await page.keyboard.press('Escape');
    check(await page.locator('#chat-input').isHidden(), 'closing Chat restores the compact touch layout');
    await page.keyboard.press('Enter');
    check(await page.locator('#chat-input').evaluate(n => document.activeElement === n), 'the existing Chat key opens the same composer');
    await page.keyboard.press('Escape');
    await page.context().close();
    const desktop = await player('MouseInput', { isMobile: false, hasTouch: false });
    check(await desktop.locator('#touch-stick').isHidden(), 'mouse desktop shows no stick');
    await desktop.evaluate(() => Settings.startEdit());
    check(await desktop.locator('.layout-handle[data-id^="touch-"]').count() === 0, 'mouse Edit UI has no hidden touch handles');
  },
};
module.exports = suite;
if (require.main === module) run([suite]).catch(e => { console.error(e); process.exitCode = 1; });
