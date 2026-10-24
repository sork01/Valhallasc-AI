// Playwright with the client's stub sprites switched on in every page (see magesprite.js / field.js: one tiny static
// figure per class and one block per enemy kind, no atlas decoding). A page load drops from about 10 s (mage) to under 1 s.
// Set REAL_SPRITES=1 to run a suite against the real artwork. tests/sprites-real.cjs always does.
const real = require('playwright');
const STUB = process.env.REAL_SPRITES !== '1';
// Most tests exercise a different window. Acknowledge the release before loading it so the new-player dialog does not
// cover their controls. The dedicated release-notes test opts in to the real first-visit behavior.
const newsVersion = process.env.TEST_WHATS_NEW === '1' ? null : require('node:fs').readFileSync(require('node:path').join(__dirname, '../../client/index.html'), 'utf8').match(/class="version">([^<]+)</)[1];
const init = ({ stub, version }) => {
  if (stub) window.__valhallaTestSprites = true;
  if (version) { try { localStorage.setItem('valhallasc.whats-new.v1', version); } catch (_) {} }
};
function wrap(browser) {
  if (!STUB && !newsVersion) return browser;
  const newContext = browser.newContext.bind(browser);
  browser.newContext = async (...args) => { const context = await newContext(...args); await context.addInitScript(init, { stub: STUB, version: newsVersion }); return context; };
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
