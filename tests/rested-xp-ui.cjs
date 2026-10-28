const { run, debug, safeSpot } = require('./lib/touch.cjs');

run([{
  name: 'rested-xp',
  async test({ player, check, width, height, out }) {
    const lang = width > 900 ? 'sv' : 'en';
    const page = await player('RestedXpHero', { lang });
    await safeSpot(page);
    await debug(page, { op: 'quest', id: 'crags_onward', action: 'finish' });
    await page.waitForFunction(() => Field.hero.xp > 0 && document.querySelector('#xp-meter').getAttribute('aria-valuenow') === String(Field.hero.xp));
    const live = await page.evaluate(() => {
      const hero = Field.hero, meter = document.querySelector('#xp-meter');
      return {
        xp: hero.xp, need: hero.xpNeed,
        width: parseFloat(document.querySelector('#xp-fill').style.width),
        text: document.querySelector('#xp-tooltip').textContent,
        reserve: parseFloat(document.querySelector('#xp-rested').style.width),
        pointer: getComputedStyle(meter).pointerEvents,
      };
    });
    check(Math.abs(live.width - live.xp / live.need * 100) < .051, 'earned XP remains the blue fill from real HUD updates');
    check(live.text === `${live.xp}/${live.need} (0% ${lang === 'sv' ? 'utvilad' : 'rested'} 0xp)`, 'hover details use the actual XP and level requirement');
    check(live.reserve === 0, 'empty Rested reserve paints no green');
    check(live.pointer === 'auto', 'XP bar accepts hover through the HUD');

    // Exercise display snapshots directly; these never change authoritative player state.
    await page.evaluate(() => {
      const update = Rested.update;
      let display;
      for (const key of ['xp', 'xpNeed', 'rested']) {
        Object.defineProperty(Field.hero, key, { get: () => display?.[key], set() {}, configurable: true });
      }
      window.xpDisplay = state => { display = state; update(state); };
      xpDisplay({ xp: 9354, xpNeed: 238299, rested: { percent: 5.5 } });
    });
    await page.waitForFunction(() => document.querySelector('#xp-fill').style.width === '3.9%');
    const meter = page.locator('#xp-meter'), tooltip = page.locator('#xp-tooltip');
    await page.mouse.move(width - 2, height - 2);
    check(await tooltip.isHidden(), 'details stay hidden before hover or focus');
    await meter.hover();
    check(await tooltip.isVisible(), 'hover displays the XP details');
    check(await tooltip.textContent() === `9354/238299 (5.5% ${lang === 'sv' ? 'utvilad' : 'rested'} 13106xp)`, 'fractional reserve and whole bonus XP are localized');
    const segment = await page.locator('#xp-rested').evaluate(el => ({ left: parseFloat(el.style.left), width: parseFloat(el.style.width), color: getComputedStyle(el).backgroundImage }));
    check(Math.abs(segment.left - 9354 / 238299 * 100) < .001 && segment.width === 5.5, 'green reserve starts after earned XP and spans its level percentage');
    check(segment.color.includes('211, 255, 207') && segment.color.includes('136, 219, 162'), 'reserve uses the light green gradient');
    check(await page.evaluate(() => {
      const blue = document.querySelector('#xp-fill').getBoundingClientRect();
      const green = document.querySelector('#xp-rested').getBoundingClientRect();
      return Math.abs(blue.right - green.left) < 1;
    }), 'earned XP and reserve meet without overlapping');
    const box = await tooltip.boundingBox();
    check(box.x >= 0 && box.x + box.width <= width && box.y + box.height <= height, 'hover details fit the viewport');
    check(await meter.getAttribute('aria-valuetext') === await tooltip.textContent(), 'assistive technology receives the same XP details');
    await page.screenshot({ path: `${out}/rested-xp-${width}x${height}.png` });
    await page.mouse.move(width - 2, height - 2);
    check(await tooltip.isHidden(), 'leaving the bar hides the details');
    await meter.focus();
    await page.keyboard.press('Tab');
    await page.keyboard.press('Shift+Tab');
    check(await tooltip.isVisible(), 'keyboard focus displays the XP details');

    await page.evaluate(() => xpDisplay({ xp: 90, xpNeed: 100, rested: { percent: 200 } }));
    check(await page.locator('#xp-rested').evaluate(el => parseFloat(el.style.left) === 90 && parseFloat(el.style.width) === 10), 'full reserve clips at the level boundary');
    check((await tooltip.textContent()).includes('200%') && (await tooltip.textContent()).includes('200xp'), 'clipping preserves the full reserve in the details');
    await page.evaluate(() => xpDisplay({ xp: 3, xpNeed: 200, rested: { percent: 25 } }));
    check((await tooltip.textContent()).includes('3/200') && (await tooltip.textContent()).includes('50xp'), 'level changes recalculate stored bonus XP');
    await page.evaluate(() => xpDisplay({ xp: 3, xpNeed: 200, rested: { percent: 0 } }));
    check(await page.locator('#xp-rested').evaluate(el => parseFloat(el.style.width) === 0), 'exhausting reserve clears the green segment');
    await page.evaluate(() => xpDisplay({ xp: 3, xpNeed: 200 }));
    check(await tooltip.textContent() === '3/200' && await page.locator('#rested').isHidden(), 'older servers retain the plain XP readout');
  },
}]).catch(e => { console.error(e); process.exitCode = 1; });
