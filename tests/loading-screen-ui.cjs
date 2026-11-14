// Browser check for the loading screen: only "Veyrheim awaits" at the top, one of the five paintings behind it (already loaded before the screen
// first appears), a random tip at the bottom and no connection panel; and it stays up until every image the world asked for has arrived.
// Run via: bash scripts/test-touch-bounded.sh tests/loading-screen-ui.cjs
// MUTATE=1 serves the previous online.js (panel, no tips, closes at once) and must fail.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');

const root = path.resolve(__dirname, '..');

function requireMemoryLimit() {
  const entry = fs.readFileSync('/proc/self/cgroup', 'utf8').split('\n').find(s => s.startsWith('0::'));
  if (!entry) throw Error('Use scripts/test-touch-bounded.sh (1536M cap).');
  let dir = path.join('/sys/fs/cgroup', entry.slice(3));
  while (dir.startsWith('/sys/fs/cgroup')) {
    try {
      const limit = fs.readFileSync(path.join(dir, 'memory.max'), 'utf8').trim();
      if (/^\d+$/.test(limit) && BigInt(limit) <= 1536n * 1024n ** 2n) return;
    } catch (_) {}
    if (dir === '/sys/fs/cgroup') break;
    dir = path.dirname(dir);
  }
  throw Error('Refusing uncapped browser run; use scripts/test-touch-bounded.sh.');
}

(async () => {
  requireMemoryLimit();
  const world = new TestWorld(root, { env: { VALHALLA_LEVEL_SPREAD: '0' } });
  await world.start();
  const browser = await chromium.launch({ headless: true });
  const errors = [];
  let checks = 0;
  const check = (cond, msg) => { assert.ok(cond, msg); checks++; };
  try {
    for (const pick of [0, 0.99]) {
      const want = pick === 0 ? 1 : 5;
      const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
      const page = await ctx.newPage();
      page.on('pageerror', e => errors.push(e.message));
      if (process.env.MUTATE === '1') {
        const { execFileSync } = require('node:child_process');
        const old = execFileSync('git', ['show', '53a4a132:client/online.js'], { cwd: root, encoding: 'utf8' });
        await page.route('**/online.js*', route => route.fulfill({ contentType: 'text/javascript', body: old }));
      }
      // Every game image (not the loading paintings) takes a second and a half, so the screen must wait for them.
      const delayed = { count: 0, last: 0 };
      await page.route(/\/assets\/(?!loading_)[^/]*\.png(\?.*)?$/, async route => {
        await new Promise(r => setTimeout(r, 1500));
        const response = await route.fetch(); await route.fulfill({ response });
        delayed.count++; delayed.last = Date.now();
      });
      await page.addInitScript(p => {
        window.AudioContext = undefined; window.webkitAudioContext = undefined;
        const real = Math.random; Math.random = () => (window.__pick === undefined ? real() : window.__pick); window.__pick = p;
        localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {}, char: null, draft: null }));
        window.__shot = null; window.__hiddenAt = 0;
        addEventListener('DOMContentLoaded', () => {
          const o = document.getElementById('connection-overlay');
          new MutationObserver(() => {
            if (o.hidden) { if (window.__shot && !window.__hiddenAt) window.__hiddenAt = performance.timeOrigin + performance.now(); return; }
            if (window.__shot) return;
            const r = o.getBoundingClientRect(), s = document.getElementById('stage').getBoundingClientRect(), cs = getComputedStyle(o);
            const t = document.getElementById('loading-title').getBoundingClientRect(), tip = document.getElementById('loading-tip').getBoundingClientRect();
            window.__shot = { title: document.getElementById('loading-title').textContent, titleTop: t.top < s.top + s.height * 0.2 && t.width > 0, tip: document.getElementById('loading-tip').textContent, tipBottom: tip.top > s.top + s.height * 0.7 && tip.width > 0,
              panel: getComputedStyle(document.querySelector('#connection-overlay .connection-panel')).display, bg: cs.backgroundImage, art: o.dataset.art, size: cs.backgroundSize,
              covers: r.left <= s.left + 1 && r.top <= s.top + 1 && r.right >= s.right - 1 && r.bottom >= s.bottom - 1, tips: window.LoadingTips.list };
          }).observe(o, { attributes: true, attributeFilter: ['hidden'] });
        });
      }, pick);
      await page.goto(world.url);
      // The paintings are decoded while the player is still on the title screen.
      await page.waitForFunction(() => window.LoadGate?.art.ready.length === 5, null, { timeout: 15000 });
      check(true, `[${want}] all five loading paintings are decoded before the screen first appears`);
      await page.locator('#start').click();
      await page.locator('#login-guest').click();
      await page.locator('#name').fill(`Loader${want}`);
      await page.locator('#go').click({ timeout: 60000 });
      if (process.env.SHOT_DIR) { await page.waitForFunction(() => !document.getElementById('connection-overlay').hidden && document.getElementById('loading-tip').textContent, null, { timeout: 30000 }); await page.waitForTimeout(400); await page.screenshot({ path: path.join(process.env.SHOT_DIR, `loading-${want}.png`) }); }
      await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0 && document.getElementById('connection-overlay').hidden, null, { timeout: 90000 });
      const shot = await page.evaluate(() => window.__shot), hiddenAt = await page.evaluate(() => window.__hiddenAt);
      check(shot, `[${want}] the loading screen opened while connecting`);
      check(shot.title === 'Veyrheim awaits' && shot.titleTop, `[${want}] "Veyrheim awaits" is written at the top (got "${shot.title}")`);
      check(shot.tipBottom && shot.tips.includes(shot.tip), `[${want}] a game tip sits at the bottom ("${shot.tip}")`);
      check(shot.panel === 'none', `[${want}] the connection panel is not shown (${shot.panel})`);
      check(shot.covers && shot.size === 'cover', `[${want}] the picture covers the whole stage (${shot.size})`);
      check(shot.art === String(want) && shot.bg.includes(`loading_${want}.webp`), `[${want}] random pick ${pick} shows loading_${want}.webp (${shot.bg})`);
      check(delayed.count > 0, `[${want}] the test held back ${delayed.count} game images`);
      check(hiddenAt >= delayed.last, `[${want}] the screen stayed up until the last image arrived (${Math.round(hiddenAt - delayed.last)} ms later)`);
      check(await page.evaluate(() => LoadGate.pending === 0), `[${want}] nothing is still loading when the screen goes`);
      await ctx.close();
    }
    assert.equal(errors.length, 0, `Page errors: ${errors.join('; ')}`);
    console.log(`PASS loading-screen-ui (${checks} checks)`);
  } finally {
    await browser.close().catch(() => {});
    await world.stop().catch(() => {});
  }
})().catch(err => { console.error(err); process.exit(1); });
