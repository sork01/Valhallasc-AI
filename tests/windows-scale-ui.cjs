// Browser check for WINDOWS-RESPONSIVE-SCALE: the Character pane fits its contents without scrolling, and the game windows keep their proportion to
// the screen at several viewport sizes. Run via: bash scripts/test-touch-bounded.sh tests/windows-scale-ui.cjs
// REPORT=1 only prints the measurements. MUTATE=1 puts a fixed height cap with inner scrolling back on the Character pane (38cqw: what a hero with a
// full set of gear and many sets needs more than) and must fail. On a phone (coarse pointer) touch.css keeps its own scrolling windows with 44 px targets,
// so there only 'inside the screen' is asserted.
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

const VIEWS = [
  { name: 'desktop 1440x900', viewport: { width: 1440, height: 900 } },
  { name: 'laptop 1280x720', viewport: { width: 1280, height: 720 } },
  { name: 'laptop 1366x768', viewport: { width: 1366, height: 768 } },
  { name: 'phone 844x390', viewport: { width: 844, height: 390 }, isMobile: true, hasTouch: true },
];

(async () => {
  requireMemoryLimit();
  const report = process.env.REPORT === '1';
  const world = new TestWorld(root, { env: { VALHALLA_LEVEL_SPREAD: '0' } });
  await world.start();
  const browser = await chromium.launch({ headless: true });
  const out = [];
  let checks = 0;
  const check = (cond, msg) => { if (report) { if (!cond) out.push(`NOTE ${msg}`); return; } assert.ok(cond, msg); checks++; };
  try {
    for (const [n, view] of VIEWS.entries()) {
      const ctx = await browser.newContext({ viewport: view.viewport, isMobile: view.isMobile, hasTouch: view.hasTouch, reducedMotion: 'reduce' });
      const page = await ctx.newPage();
      await page.addInitScript(() => {
        window.AudioContext = undefined; window.webkitAudioContext = undefined;
        localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {}, char: null, draft: null }));
      });
      await page.goto(world.url);
      await page.locator('#start').click();
      await page.locator('#login-guest').click();
      await page.locator('#name').fill(`Scaler${n}`);
      await page.locator('#go').click({ timeout: 60000 });
      await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
      if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
      await page.evaluate(() => { const tip = document.getElementById('tutorial-tip'); if (tip && !tip.hidden) document.getElementById('tutorial-disable')?.click(); });
      if (process.env.MUTATE === '1') await page.addStyleTag({ content: '.equipment-workspace { max-height: 38cqw !important; overflow: auto !important; } .character-window { width: 36cqw !important; }' });
      const tag = s => `${view.name}: ${s}`;

      // The Character pane, on each of its tabs: no scrollbar of its own, and everything inside the screen.
      await page.evaluate(() => CharacterPane.open('stats'));
      await page.locator('#equipment').waitFor({ state: 'visible' });
      for (const tab of ['stats', 'sets', 'achievements', 'mounts', 'rebirth']) {
        await page.evaluate(t => CharacterPane.setTab(t), tab);
        await page.waitForTimeout(120);
        const m = await page.evaluate(() => {
          const ws = document.querySelector('.equipment-workspace'), cw = document.querySelector('#equipment .character-window'), stage = document.getElementById('stage');
          const sr = stage.getBoundingClientRect(), wr = ws.getBoundingClientRect(), cr = cw.getBoundingClientRect();
          const panes = [...document.querySelectorAll('#equipment .character-tabpanel')].filter(p => !p.hidden);
          const inner = panes.map(p => ({ id: p.id, over: p.scrollHeight - p.clientHeight, ov: getComputedStyle(p).overflowY }));
          return { wsOver: ws.scrollHeight - ws.clientHeight, wsH: Math.round(wr.height), stageH: Math.round(sr.height), within: wr.top >= sr.top - 1 && wr.bottom <= sr.bottom + 1 && wr.left >= sr.left - 1 && wr.right <= sr.right + 1, cwW: Math.round(cr.width), stageW: Math.round(sr.width), inner };
        });
        out.push(`${view.name} ${tab}: ${JSON.stringify(m)}`);
        if (!view.hasTouch) check(m.wsOver <= 1, tag(`Character pane (${tab}) needs no scrolling (overflow ${m.wsOver}px)`));
        check(m.within, tag(`Character pane (${tab}) lies inside the screen`));
      }
      await page.evaluate(() => CharacterPane.close());

      // The other windows keep a sensible share of the screen and do not overflow it.
      const windows = [
        ['skills-panel', () => Skillbar.show(), '.skills-panel'],
        ['social-panel', () => Social.show(), '.social-panel'],
        ['settings-panel', () => Settings.show?.() ?? document.getElementById('p-settings')?.click(), '.settings-panel'],
      ];
      for (const [id, open, inner] of windows) {
        await page.evaluate(open).catch(() => {});
        await page.waitForTimeout(150);
        const m = await page.evaluate(([id, inner]) => {
          const root = document.getElementById(id); if (!root || root.hidden) return null;
          const el = root.querySelector(inner) || root, stage = document.getElementById('stage').getBoundingClientRect(), r = el.getBoundingClientRect();
          return { w: Math.round(r.width), h: Math.round(r.height), within: r.left >= stage.left - 1 && r.right <= stage.right + 1 && r.top >= stage.top - 1 && r.bottom <= stage.bottom + 1, share: +(r.width / stage.width).toFixed(2) };
        }, [id, inner]);
        out.push(`${view.name} ${id}: ${JSON.stringify(m)}`);
        if (m) check(m.within, tag(`${id} lies inside the screen`));
        await page.keyboard.press('Escape'); await page.keyboard.press('Escape');
      }
      await ctx.close();
    }
    if (report) { console.log(out.join('\n')); return; }
    console.log(out.join('\n'));
    console.log(`PASS windows-scale-ui (${checks} checks)`);
  } finally {
    await browser.close().catch(() => {});
    await world.stop().catch(() => {});
  }
})().catch(err => { console.error(err); process.exit(1); });
