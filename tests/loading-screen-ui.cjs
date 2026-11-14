// Browser check for the loading screen: it says "Veyrheim awaits", covers the whole stage with one of the five loading paintings (never the game scene
// behind it) and the picture follows the random pick. Run via: bash scripts/test-touch-bounded.sh tests/loading-screen-ui.cjs
// MUTATE=1 serves the previous online.js (no random picture) and must fail.
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
        const old = execFileSync('git', ['show', 'HEAD:client/online.js'], { cwd: root, encoding: 'utf8' });
        await page.route('**/online.js*', route => route.fulfill({ contentType: 'text/javascript', body: old }));
      }
      await page.addInitScript(p => {
        window.AudioContext = undefined; window.webkitAudioContext = undefined;
        Math.random = (r => () => (window.__pickNext ? window.__pickNext() : r()))(Math.random);
        window.__pickNext = () => p;
        localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {}, char: null, draft: null }));
        // Record what the overlay looks like the moment it first opens.
        window.__shot = null;
        addEventListener('DOMContentLoaded', () => {
          const o = document.getElementById('connection-overlay');
          new MutationObserver(() => {
            if (o.hidden || window.__shot) return;
            const r = o.getBoundingClientRect(), s = document.getElementById('stage').getBoundingClientRect(), cs = getComputedStyle(o);
            window.__shot = { title: o.querySelector('h3').textContent, bg: cs.backgroundImage, art: o.dataset.art, covers: r.left <= s.left + 1 && r.top <= s.top + 1 && r.right >= s.right - 1 && r.bottom >= s.bottom - 1, size: cs.backgroundSize, text: document.getElementById('connection-text').textContent };
          }).observe(o, { attributes: true, attributeFilter: ['hidden'] });
        });
      }, pick);
      await page.goto(world.url);
      await page.locator('#start').click();
      await page.locator('#login-guest').click();
      await page.locator('#name').fill(`Loader${want}`);
      await page.locator('#go').click({ timeout: 60000 });
      await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
      const shot = await page.evaluate(() => window.__shot);
      check(shot, `[${want}] the loading screen opened while connecting`);
      check(shot.title === 'Veyrheim awaits', `[${want}] it says Veyrheim awaits (got "${shot.title}")`);
      check(shot.covers && shot.size === 'cover', `[${want}] it covers the whole stage with the picture (${shot.size})`);
      check(shot.art === String(want) && shot.bg.includes(`loading_${want}.webp`), `[${want}] random pick ${pick} shows loading_${want}.webp (${shot.bg})`);
      const status = await page.evaluate(() => document.getElementById('network-status').textContent);
      check(!/Greenmeadow awaits|Connecting to Greenmeadow/.test(status), `[${want}] status line does not name Greenmeadow while loading`);
      check(await page.evaluate(() => document.getElementById('connection-overlay').hidden), `[${want}] the loading screen closes once connected`);
      const ok = await page.evaluate(async n => (await fetch(`assets/loading_${n}.webp`)).ok, want);
      check(ok, `[${want}] the picture file is served`);
      await ctx.close();
    }
    assert.equal(errors.length, 0, `Page errors: ${errors.join('; ')}`);
    console.log(`PASS loading-screen-ui (${checks} checks)`);
  } finally {
    await browser.close().catch(() => {});
    await world.stop().catch(() => {});
  }
})().catch(err => { console.error(err); process.exit(1); });
