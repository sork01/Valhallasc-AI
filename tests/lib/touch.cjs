const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./playwright.cjs');
const { TestWorld } = require('../../scripts/testing/driver.cjs');
const root = path.resolve(__dirname, '../..');
const out = path.join(root, 'test-results/touch');
const sizes = process.env.TOUCH_SIZE ? [process.env.TOUCH_SIZE.split('x').map(Number)] : [[844, 390], [1024, 768]];
const sleep = ms => new Promise(r => setTimeout(r, ms));
// This is a shared production host. Refuse to start a private server or browser
// unless the whole process tree is contained by a hard cgroup memory limit.
// Run via scripts/test-touch-bounded.sh; an environment flag is not sufficient.
function requireMemoryLimit() {
  const entry = fs.readFileSync('/proc/self/cgroup', 'utf8').split('\n').find(s => s.startsWith('0::'));
  if (!entry) throw Error('Touch tests require a cgroup v2 memory limit. Use scripts/test-touch-bounded.sh.');
  let dir = path.join('/sys/fs/cgroup', entry.slice(3));
  let bounded = false;
  while (dir.startsWith('/sys/fs/cgroup')) {
    try {
      const limit = fs.readFileSync(path.join(dir, 'memory.max'), 'utf8').trim();
      if (/^\d+$/.test(limit) && BigInt(limit) <= 1536n * 1024n ** 2n) bounded = true;
    } catch (_) {}
    if (dir === '/sys/fs/cgroup') break;
    dir = path.dirname(dir);
  }
  if (!bounded) throw Error('Refusing uncapped touch tests on the production host. Use scripts/test-touch-bounded.sh (maximum 1.5 GiB for the whole process tree).');
}
async function run(suites) {
  requireMemoryLimit();
  const world = new TestWorld(); world.startLevel = 40;
  let browser, checks = 0;
  fs.mkdirSync(out, { recursive: true });
  const check = (value, label) => { assert.ok(value, label); checks++; };
  try {
    await world.start();
    for (const suite of suites) for (const [width, height] of sizes) {
      console.log(`${suite.name}: ${width}x${height}`);
      browser = await chromium.launch({ headless: true, ignoreDefaultArgs: ['--hide-scrollbars'] });
      const errors = [];
      async function player(name, opts = {}) {
        const { keepSuggestion = false, lang = 'en', characterClass = 'mage', ...contextOptions } = opts;
        const context = await browser.newContext({ viewport: { width, height }, isMobile: true, hasTouch: true, deviceScaleFactor: 1, reducedMotion: 'reduce', ...contextOptions });
        const page = await context.newPage(); page.on('pageerror', e => { errors.push(e.message); console.error('Browser:', e.message); });
        await page.addInitScript(lang => {
          // These checks exercise controls and layout. Skip audio decoding in each browser.
          window.AudioContext = undefined; window.webkitAudioContext = undefined;
          if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang, sound: false, uiSet: true, ui: { obsolete: { x: 9, y: 9 } }, panelSizeSet: true, panelSize: {}, char: null, draft: null }));
        }, lang);
        if (process.env.MUTATE) await suite.mutate?.(page);
        await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
        await page.locator('#cls-' + characterClass).click(); await page.locator('#name').fill(name); await page.locator('#go').click({ timeout: 60000 });
        await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
        await page.waitForFunction(() => window.TouchControls && (!matchMedia('(pointer: coarse)').matches || document.querySelector('#touch-skills [data-skill]')));
        if (!keepSuggestion && await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
        return page;
      }
      await suite.test({ player, check, world, browser, width, height, out, sleep });
      check(errors.length === 0, `${suite.name} page errors: ${errors.join('; ')}`);
      await browser.close(); browser = null;
    }
    console.log(`touch: ${checks} checks passed`);
  } finally {
    const entry = fs.readFileSync('/proc/self/cgroup', 'utf8').trim().split('::')[1];
    try { console.log('Test memory peak: ' + Math.round(+fs.readFileSync('/sys/fs/cgroup' + entry + '/memory.peak', 'utf8') / 1048576) + ' MiB'); } catch (_) {}
    if (browser) await browser.close(); await world.stop();
  }
}
const source = name => fs.readFileSync(path.join(root, 'client', name), 'utf8');
const replace = async (page, file, before, after) => {
  const original = source(file); assert.ok(original.includes(before), `mutation target exists in ${file}`);
  await page.route(`**/${file}`, r => r.fulfill({ contentType: file.endsWith('.css') ? 'text/css' : 'text/javascript', body: original.replace(before, after) }));
};
const debug = (page, command) => page.evaluate(command => Online.send({ type: 'debug', command }), command);
async function safeSpot(page) {
  await debug(page, { op: 'teleport', zone: 0, x: 80, y: 80 });
  await page.waitForFunction(() => Math.hypot(Field.hero.nx - 80, Field.hero.ny - 80) < 2);
  await page.evaluate(() => { Field.clearInput(); Online.send({ type: 'stop' }); }); await sleep(250);
}
async function record(page) {
  await page.evaluate(() => {
    window.touchSent = []; window.touchEvents = [];
    for (const name of ['pointerdown', 'pointerup', 'pointercancel', 'lostpointercapture']) document.addEventListener(name, e => touchEvents.push({ type: e.type, id: e.pointerId, target: e.target.id || e.target.className }), true);
    const send = Online.send;
    Online.send = function(m) { touchSent.push({ ...m, at: performance.now() }); return send.call(this, m); };
  });
}
async function touch(page) {
  const cdp = await page.context().newCDPSession(page);
  return async (type, points) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: points.map(([id, x, y]) => ({ id, x, y, radiusX: 3, radiusY: 3, force: 1 })) });
}
module.exports = { requireMemoryLimit, run, replace, debug, safeSpot, record, touch, sleep };
