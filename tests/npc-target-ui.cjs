// Browser check for NPC-TARGET: clicking a townsperson shows them in the target frame (portrait, name, level).
// Run via: bash scripts/test-touch-bounded.sh tests/npc-target-ui.cjs     MUTATE=1 removes the NPC target and must fail.
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
    try { const l = fs.readFileSync(path.join(dir, 'memory.max'), 'utf8').trim(); if (/^\d+$/.test(l) && BigInt(l) <= 1536n * 1024n ** 2n) return; } catch (_) {}
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
  const errors = []; let checks = 0;
  const check = (c, m) => { assert.ok(c, m); checks++; };
  try {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    const page = await ctx.newPage();
    page.on('pageerror', e => errors.push(e.message));
    await page.addInitScript(() => {
      window.AudioContext = undefined; window.webkitAudioContext = undefined;
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {}, char: null, draft: null }));
    });
    await page.goto(world.url);
    await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.locator('#name').fill('NpcTarget'); await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
    if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
    await page.evaluate(() => { const t = document.getElementById('tutorial-tip'); if (t && !t.hidden) document.getElementById('tutorial-disable')?.click(); });
    const debug = c => page.evaluate(x => Online.send({ type: 'debug', command: x }), c);

    // A shopkeeper-style person in zone 0 who stands still and has real art.
    const npc = await page.evaluate(() => { const n = City.npcs.find(n => !n.route && !n.sign && n.art !== 'mailbox' && n.art !== 'stone' && n.art !== 'scenery' && n.offers?.length && n.x != null); return n && { id: n.id, name: n.name, role: n.role, x: n.x, y: n.y }; });
    check(npc, 'found a townsperson to click');
    await debug({ op: 'teleport', zone: 0, x: npc.x + 6, y: npc.y + 6 });
    await page.waitForFunction(p => Math.hypot(Field.hero.x - p.x - 6, Field.hero.y - p.y - 6) < 3, npc);
    check(await page.locator('#hud-target').isHidden(), 'no target frame before clicking');

    if (process.env.MUTATE !== '1') {
      const [fx, fy] = await page.evaluate(p => { const n = City.npcs.find(n => n.id === p.id); return Field.screenOf(n.x, n.y); }, npc);
      const box = await page.locator('#fieldcv').boundingBox();
      await page.mouse.click(box.x + fx * box.width, box.y + fy * box.height - 24);
    }
    await page.waitForFunction(() => !document.getElementById('hud-target').hidden, null, { timeout: 8000 });
    const t = await page.evaluate(() => ({
      name: document.getElementById('hud-target-name').textContent,
      level: document.getElementById('hud-target-level').textContent,
      role: document.getElementById('hud-target-text').textContent,
      isNpcBar: document.getElementById('hud-target-hp').classList.contains('npc'),
      painted: (() => { const c = document.getElementById('hud-target-face'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 0) n++; return n; })(),
      portraitId: document.getElementById('hud-target-face').dataset.npc,
      zoneLevels: Field.zone === 0 ? window.WORLD_MAP?.zones?.[0]?.levels : null,
    }));
    check(t.name === npc.name, `target frame names the NPC (${t.name})`);
    check(/^ Lv \d+$/.test(t.level), `target frame shows a level (${t.level})`);
    check(t.role === npc.role && t.isNpcBar, `role replaces the health numbers (${t.role})`);
    check(t.portraitId === npc.id && t.painted > 2000, `portrait is painted for the NPC (${t.painted} px)`);

    // Walking away (a held direction key) clears the NPC target again.
    await page.keyboard.down('ArrowLeft'); await page.waitForTimeout(300); await page.keyboard.up('ArrowLeft');
    await page.waitForFunction(() => document.getElementById('hud-target').hidden, null, { timeout: 5000 });
    check(true, 'moving off clears the NPC target');
    check(errors.length === 0, `no page errors: ${errors.join('; ')}`);
    console.log(`npc-target-ui: ${checks} checks passed`);
  } finally { await browser.close(); await world.stop(); }
})().catch(e => { console.error(e); process.exit(1); });
