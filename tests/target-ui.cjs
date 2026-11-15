// Real browser input against a private world: upper sprite clicks select enemies and the adjacent badge follows them.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium, STUB } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-target-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
// The upper-sprite geometry needs the real monster art: the 12-pixel stub is too short to clear the ground radius.
if (STUB) throw new Error('target-ui needs real artwork: run with REAL_SPRITES=1');
const check = (value, label) => { assert.ok(value, label); checks++; };
async function call(name, args = {}) {
  const r = await client.callTool({ name, arguments: args });
  assert.ok(!r.isError, `${name}: ${JSON.stringify(r.content)}`);
  return r.structuredContent;
}
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0' } }));
  const world = await call('start_world', { levelSpread: 0 }); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('TargetUI'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites && !!Field.hero, null, { timeout: 60000 });
  // A new hero stands on the Saltby pier, beside a wall: move to open ground first (the spawns sit four tiles either side).
  await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 0, x: 250, y: 235 } }));
  await page.waitForFunction(() => Field.zone === 0 && Math.hypot(Field.hero.nx - 250, Field.hero.ny - 235) < 8, null, { timeout: 30000 });
  // The hero's drawn position eases to the server's (a teleport can land on the nearest free ground): wait until they agree.
  await page.waitForFunction(() => Math.hypot(Field.hero.x - Field.hero.nx, Field.hero.y - Field.hero.ny) < 0.05, null, { timeout: 15000 });
  await page.waitForTimeout(500);
  const debug = command => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);
  const badge = page.locator('#hud-target');
  check(await badge.isHidden(), 'No target badge before selecting an enemy');
  const stage = async (kind, dx, dy) => {
    const at = await page.evaluate(([dx, dy]) => ({ x: Field.hero.x + dx, y: Field.hero.y + dy }), [dx, dy]);
    await debug({ op: 'spawn_enemy', kind, x: at.x, y: at.y, level: 1 });
    await page.waitForFunction(([kind, at]) => Field.slimes.some(s => s.kind === kind && !s.dead && Math.hypot(s.x - at.x, s.y - at.y) < 4), [kind, at], { timeout: 10000 });
    return at;
  };
  const clickUpperBody = async (kind, at) => {
    // The hero can take a late server correction after a teleport, so each attempt re-reads the sprite and its screen point.
    let last;
    for (let attempt = 0; attempt < 3; attempt++) {
      const p = await page.evaluate(([kind, at]) => {
        const s = Field.slimes.filter(s => s.kind === kind && !s.dead).sort((a, b) => Math.hypot(a.x - at.x, a.y - at.y) - Math.hypot(b.x - at.x, b.y - at.y))[0];
        const [sx, sy] = Field._debug.w2s(s.x, s.y), b = Field._debug.enemyHitbox(s), y = sy + (b.y0 * .7 + b.y1 * .3) * 2.1 * s.d.scale;
        const cv = document.querySelector('#fieldcv');
        return { id: s.id, x: sx, y, cw: cv.width, ch: cv.height, groundDistance: Math.hypot(s.x - Field._debug.s2w(sx, y)[0], s.y - Field._debug.s2w(sx, y)[1]) };
      }, [kind, at]);
      const box = await page.locator('#fieldcv').boundingBox();
      // Screen points are in the canvas's own pixels, so scale by its intrinsic size (the viewport is not 1600x900).
      // w2s is in logical units (1600 x VH, client `VW`), the same space the pointer handler maps clicks into.
      const logicalH = p.ch * 1600 / p.cw;
      await page.mouse.click(box.x + p.x / 1600 * box.width, box.y + p.y / logicalH * box.height);
      const selected = await page.waitForFunction(id => Field.hero.target?.id === id && !document.querySelector('#hud-target').hidden, p.id, { timeout: 4000 }).then(() => true, () => false);
      if (selected) return p;
      last = p;
      await page.waitForTimeout(400);
    }
    const probe = await page.evaluate(id => { const s = Field.slimes.find(z => z.id === id); return { target: Field.hero.target ? { id: Field.hero.target.id, kind: Field.hero.target.kind } : null, hero: { x: Field.hero.x, y: Field.hero.y, nx: Field.hero.nx, ny: Field.hero.ny }, slime: s ? { x: s.x, y: s.y, dead: s.dead, dir: s.dir, box: Field._debug.enemyHitbox(s), scale: s.d.scale } : null }; }, last.id);
    const cbox = await page.locator('#fieldcv').boundingBox();
    const under = await page.evaluate(([x, y]) => { const e = document.elementFromPoint(x, y); return e ? `${e.tagName}#${e.id}.${e.className}` : null; }, [cbox.x + last.x / 1600 * cbox.width, cbox.y + last.y / (last.ch * 1600 / last.cw) * cbox.height]);
    throw new Error(`click on ${kind} ${last.id} did not select it after 3 attempts (topmost element at the click: ${under}): ${JSON.stringify({ point: [last.x, last.y], canvas: [last.cw, last.ch], probe })}`);
  };
  // Eight tiles out: a level-1 slime four tiles away walks onto the hero within seconds and its upper body then sits under the hero's own sprite.
  const greenAt = await stage('green', 8, 0);
  const green = await clickUpperBody('green', greenAt);
  check(green.groundDistance > 1.1, `Upper sprite click is outside the old ground target radius (${green.groundDistance.toFixed(2)})`);
  check((await page.locator('#hud-target-name').textContent()).includes('Green Slime'), 'Badge shows the selected monster name');
  check(await page.evaluate(() => { const c = document.querySelector('#hud-target-face'); return [...c.getContext('2d').getImageData(0, 0, c.width, c.height).data].some((v, i) => i % 4 === 3 && v > 0); }), 'Badge paints the monster portrait');
  check(await page.evaluate(() => document.querySelector('#hud-target-text').textContent === `${Math.min(Math.ceil(Field.hero.target.hp), Math.round(Field.hero.target.maxHp))} / ${Math.round(Field.hero.target.maxHp)}`), 'Badge shows authoritative monster HP');
  const blueAt = await stage('blue', -8, 0);
  const blue = await clickUpperBody('blue', blueAt);
  check(blue.id !== green.id && (await page.locator('#hud-target-name').textContent()).includes('Blue Slime'), 'Selecting another monster updates the badge');
  await page.keyboard.press('w');
  await page.waitForFunction(() => Field.hero.target === null && document.querySelector('#hud-target').hidden);
  check(await badge.isHidden(), 'Movement clears the target badge');
  assert.deepEqual(errors, [], 'No browser errors');
  console.log(`target-ui: ${checks} checks passed`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close().catch(() => {});
});
