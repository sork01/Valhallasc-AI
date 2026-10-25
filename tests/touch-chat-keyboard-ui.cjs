const { run, replace } = require('./lib/touch.cjs');
const suite = {
  name: 'touch-chat-keyboard',
  mutate(page) {
    if (process.env.MUTATE === 'bags') return replace(page, 'game.js', 'workspace.dataset.view = view;', "view = 'bags'; workspace.dataset.view = view;");
    return replace(page, 'touch.js', "window.visualViewport?.addEventListener('resize', queueChatFit);", '// viewport resize mutation');
  },
  async test({ player, check, out, width, height }) {
    const page = await player('KeyboardChat');
    check(await page.locator('#touch-actions [data-action="talk"]').count() === 0, 'Talk / read is removed from the row');
    const controls = await page.evaluate(() => {
      const box = selector => { const r = document.querySelector(selector).getBoundingClientRect(); return { left: r.left, right: r.right, top: r.top, bottom: r.bottom, width: r.width, height: r.height }; };
      return { food: box('#touch-quickuse'), arc: box('#touch-skills'), bags: box('#inventory-open'), social: box('#social-open') };
    });
    for (const key of ['bags', 'social']) {
      const r = controls[key];
      check(r.left >= controls.food.right && r.right <= controls.arc.left && r.bottom <= height && r.bottom >= height - 16 && r.width >= 43.9 && r.height >= 43.9, `${key} sits at bottom between food and arc: ${JSON.stringify(controls)}`);
    }
    check(controls.social.right < controls.bags.left, 'Bags and Social do not overlap');
    for (const selector of ['#inventory-open', '#touch-actions [data-action="bags"]']) {
      await page.locator(selector).tap(); await page.locator('#equipment').waitFor({ state: 'visible' });
      check(await page.locator('.character-window').isVisible() && await page.locator('.bag-window').isVisible(), `${selector} opens character and bags together`);
      await page.keyboard.press('Escape'); await page.locator('#equipment').waitFor({ state: 'hidden' });
    }
    await page.keyboard.press('KeyB');
    check(await page.locator('.character-window').isVisible() && await page.locator('.bag-window').isVisible(), 'Bags key also opens both panels');
    await page.keyboard.press('Escape');

    // Headless Chromium has no OS keyboard. Keep the real event target and emulate
    // its measured viewport, including Safari's visual-only resize and panning.
    await page.evaluate(() => {
      window.keyboardViewport = { height: innerHeight, width: innerWidth, offsetTop: 0, offsetLeft: 0 };
      for (const name of Object.keys(keyboardViewport)) Object.defineProperty(visualViewport, name, { configurable: true, get: () => keyboardViewport[name] });
    });
    await page.locator('#touch-actions [data-action="chat"]').tap();
    await page.locator('#chat-input').fill('I can see what I am typing');
    await page.waitForFunction(() => document.getElementById('stage').style.getPropertyValue('--chat-height') === `${innerHeight - 16}px`);
    async function visibleChat(label, viewport, event) {
      await page.evaluate(({ viewport, event }) => { Object.assign(keyboardViewport, viewport); visualViewport.dispatchEvent(new Event(event)); }, { viewport, event });
      await page.waitForFunction(() => {
        const r = document.querySelector('#chat').getBoundingClientRect(), v = keyboardViewport;
        return r.top >= v.offsetTop && r.bottom <= v.offsetTop + v.height && r.left >= v.offsetLeft && r.right <= v.offsetLeft + v.width;
      }, null, { timeout: 5000 });
      const field = await page.locator('#chat-input').evaluate(n => { const r = n.getBoundingClientRect(); return { top: r.top, bottom: r.bottom, size: parseFloat(getComputedStyle(n).fontSize), focused: n === document.activeElement, hit: document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2) === n }; });
      check(field.focused && field.hit && field.size >= 16 && field.top >= viewport.offsetTop && field.bottom <= viewport.offsetTop + viewport.height, `${label}: readable editor stays above keyboard: ${JSON.stringify(field)}`);
      check(await page.locator('#chat-input').inputValue() === 'I can see what I am typing', `${label}: typing is preserved`);
      for (const selector of ['#chat-form button', '.touch-chat-close']) {
        const r = await page.locator(selector).boundingBox();
        check(r && r.y >= viewport.offsetTop && r.y + r.height <= viewport.offsetTop + viewport.height && r.height >= 44, `${label}: ${selector} remains visible and tappable`);
      }
    }
    await visibleChat('keyboard open', { width, height: 180, offsetTop: 0, offsetLeft: 0 }, 'resize');
    await page.screenshot({ path: `${out}/chat-keyboard-${width}x${height}.png` });
    await visibleChat('keyboard pans viewport', { width: width - 56, height: 155, offsetTop: 45, offsetLeft: 28 }, 'scroll');
    await page.locator('.touch-chat-close').tap();
    check(await page.locator('#chat-input').isHidden(), 'in-chat Close dismisses the editor while keyboard is up');
    await page.evaluate(() => { Object.assign(keyboardViewport, { width: innerWidth, height: innerHeight, offsetTop: 0, offsetLeft: 0 }); visualViewport.dispatchEvent(new Event('resize')); });
    await page.locator('#touch-actions [data-action="chat"]').tap();
    check(await page.locator('#chat-input').inputValue() === 'I can see what I am typing', 'reopening preserves the draft after keyboard dismissal');
    await page.locator('.touch-chat-close').tap();
    await page.context().close();
  },
};
module.exports = suite;
if (require.main === module) run([suite]).catch(e => { console.error(e); process.exitCode = 1; });
