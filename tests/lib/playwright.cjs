// Playwright with the client's stub sprites switched on in every page (see magesprite.js / field.js: one tiny static
// figure per class and one block per enemy kind, no atlas decoding). A page load drops from about 10 s (mage) to under 1 s.
// Set REAL_SPRITES=1 to run a suite against the real artwork. tests/sprites-real.cjs always does.
const real = require('playwright');
const STUB = process.env.REAL_SPRITES !== '1';
const init = () => { window.__valhallaTestSprites = true; };
function wrap(browser) {
  if (!STUB) return browser;
  const newContext = browser.newContext.bind(browser);
  browser.newContext = async (...args) => { const context = await newContext(...args); await context.addInitScript(init); return context; };
  browser.newPage = async (...args) => {
    const context = await browser.newContext(...args), page = await context.newPage(), close = page.close.bind(page);
    page.close = async options => { await close(options); await context.close(); };
    return page;
  };
  return browser;
}
const chromium = new Proxy(real.chromium, {
  get(target, name) {
    if (name === 'launch') return async (...args) => wrap(await target.launch(...args));
    const value = target[name]; return typeof value === 'function' ? value.bind(target) : value;
  },
});
module.exports = { ...real, chromium, STUB };
