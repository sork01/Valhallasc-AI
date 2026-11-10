// CHEST-BIGGER: the treasure chest is drawn 1.75x larger and the whole larger box is clickable. Client-only.
// Run bounded: bash scripts/test-touch-bounded.sh tests/chest-bigger-ui.cjs  (MUTATE=1 serves the previous field.js and must fail).
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const { execFileSync } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const release = path.join(root, 'target/release/valhalla-server');
const binary = process.env.VALHALLA_BINARY || (fs.existsSync(release) ? release : undefined);
const client = new Client({ name: 'valhallasc-chest-bigger-ui', version: '1.0.0' });
let browser, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; console.log('ok -', message); };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0', ...(binary ? { VALHALLA_BINARY: binary } : {}) } }));
  const world = await call('start_world');
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  if (process.env.MUTATE === '1') {
    const old = execFileSync('git', ['show', 'HEAD:client/field.js'], { cwd: root, maxBuffer: 1 << 28 });
    await page.route('**/field.js*', route => route.fulfill({ status: 200, contentType: 'text/javascript', body: old }));
  }
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('ChestSeer'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.hero.x, null, { timeout: 60000 });
  await page.waitForFunction(() => Field._debug.chestSprites, null, { timeout: 10000 });
  const debug = command => page.evaluate(command => { Online.send({ type: 'debug', ref: Math.floor(Math.random() * 1e9), command }); }, command).then(() => page.waitForTimeout(400));
  await debug({ op: 'spawn_chest', distance: 1.2 });
  await page.waitForFunction(() => Field._debug.chests.length === 1, null, { timeout: 5000 });
  await page.waitForTimeout(300);

  // Drawn size: diff the canvas with the chest drawn against the same frame with it hidden (expiresAt in the past), so the
  // result is exactly the chest's own pixels (body, shadow and countdown), whatever the ground colour.
  const box = await page.evaluate(() => {
    const c = Field._debug.chests[0], [sx, sy] = Field._debug.w2s(c.x, c.y), cv = document.getElementById('fieldcv'), k = cv.width / 1600, g = cv.getContext('2d');
    const W = 260, H = 240, x0 = Math.round((sx - W / 2) * k), y0 = Math.round((sy - H + 50) * k), w = Math.round(W * k), h = Math.round(H * k);
    // One synchronous task, so no snapshot can replace the chest object between the two draws.
    const T = performance.now() / 1000, keep = c.expiresAt; c.expiresAt = -1; Field._debug.drawFrame(T); const without = g.getImageData(x0, y0, w, h).data;
    c.expiresAt = keep; Field._debug.drawFrame(T); const withChest = g.getImageData(x0, y0, w, h).data;
    let minX = 1e9, maxX = -1, minY = 1e9, maxY = -1;
    for (let i = 0; i < withChest.length; i += 4) {
      if (Math.abs(withChest[i] - without[i]) + Math.abs(withChest[i + 1] - without[i + 1]) + Math.abs(withChest[i + 2] - without[i + 2]) < 40) continue;
      const p = i / 4, x = p % w, y = Math.floor(p / w);
      minX = Math.min(minX, x); maxX = Math.max(maxX, x); minY = Math.min(minY, y); maxY = Math.max(maxY, y);
    }
    return { width: (maxX - minX + 1) / k, height: (maxY - minY + 1) / k, canvas: [cv.width, cv.height], sx, sy };
  });
  console.log('chest pixel bounds', box);
  // Before: the shadow was 54 px wide and the whole chest incl. its countdown about 60 px tall; at 1.75x about 95 x 105.
  check(box.width >= 85, `the drawn chest (body and shadow) is wider than the old one (${box.width.toFixed(0)} px, old about 54)`);
  check(box.height >= 85, `the drawn chest with its countdown is taller than the old one (${box.height.toFixed(0)} px, old about 60)`);

  // The click box: the old edges (27 px sideways, 37 px above, 7 below) are well inside the new one, whose edges are 1.75x.
  // A click on bare ground walks the hero, which moves the camera and so the chest on screen: stop and let it settle first.
  const settle = async () => {
    await page.evaluate(() => { Online.send({ type: 'stop' }); if (Field.hero.goal) Field.hero.goal = null; });
    let last = null;
    for (let n = 0; n < 20; n++) { const p = await page.evaluate(() => [Field.hero.x, Field.hero.y].join()); if (p === last) return; last = p; await page.waitForTimeout(250); }
  };
  const opensAfterClick = async (dx, dy) => {
    await settle();
    await page.evaluate(() => { window.__opens = 0; if (!window.__wrapped) { window.__wrapped = true; const send = Online.send; Online.send = m => { if (m.type === 'open_chest') window.__opens++; return send.call(Online, m); }; } });
    const point = await page.evaluate(({ dx, dy }) => { const c = Field._debug.chests[0], [sx, sy] = Field._debug.w2s(c.x, c.y), r = document.getElementById('fieldcv').getBoundingClientRect(); return { x: r.left + (sx + dx) / 1600 * r.width, y: r.top + (sy + dy) / 900 * r.height }; }, { dx, dy });
    await page.mouse.move(point.x, point.y); await page.mouse.click(point.x, point.y);
    await page.waitForTimeout(250);
    // The click is accepted when the hero asks to open it now or starts walking up to it (pendingChest).
    const opened = await page.evaluate(() => window.__opens > 0 || !!Field._debug.pendingChest);
    return opened;
  };
  check(!(await opensAfterClick(75, -10)), 'a click 75 px beside the chest (past the new box) does not open it');
  check(!(await opensAfterClick(0, -75)), 'a click 75 px above the chest (past the new box) does not open it');
  // Chests are opened by one request; a click in the new outer ring (beyond the old 27 px) must now ask for it.
  check(await opensAfterClick(40, -10), 'a click 40 px to the side (outside the old box, inside the new one) is accepted as a click on the chest');
  assert.deepEqual(errors, []);
  console.log(`chest-bigger-ui: ${checks} checks passed`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  try { await browser?.close(); } catch {}
  try { await call('stop_world'); } catch {}
  try { await client.close(); } catch {}
});
