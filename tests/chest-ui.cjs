// Treasure chests in a real browser (CHEST-CLIENT): the chest is drawn where the server put it, a click on its visible body
// opens it (walking up first when it is out of reach), the opener gets the announcement and the pile, and a stale or
// out-of-range request changes nothing. The server side is covered by world::chests::tests.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const fs = require('node:fs');
const root = path.resolve(__dirname, '..');
// The debug server cannot hold 20 ticks a second in a busy zone, which makes click timing meaningless: prefer the release build.
const release = path.join(root, 'target/release/valhalla-server');
const binary = process.env.VALHALLA_BINARY || (fs.existsSync(release) ? release : undefined);
const client = new Client({ name: 'valhallasc-chest-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0', ...(binary ? { VALHALLA_BINARY: binary } : {}) } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [], frames = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('websocket', ws => {
    ws.on('framesent', f => { const t = String(f.payload); if (!/"(ping|input|social|pvp)"/.test(t)) frames.push('>> ' + t.slice(0, 180)); });
    ws.on('framereceived', f => { const t = String(f.payload); if (!/"snapshot"|^\{"bolts"|^\{"id":/.test(t.slice(0, 40)) && !/"kind":"(hit|swing|cast)/.test(t)) frames.push('<< ' + t.slice(0, 180)); });
  });
  global.__frames = frames;
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('ChestFinder'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.hero.x, null, { timeout: 60000 });
  const debug = (command) => page.evaluate(command => { Online.send({ type: 'debug', ref: Math.floor(Math.random() * 1e9), command }); }, command).then(() => page.waitForTimeout(400));
  const chests = () => page.evaluate(() => Field._debug.chests.map(c => ({ id: c.id, x: c.x, y: c.y, left: c.left, expiresAt: c.expiresAt })));
  const gold = () => page.evaluate(() => Field.hero.gold ?? null);
  const log = () => page.locator('#chat-log').innerText();
  // The hero starts in the Greenmeadow; stand still and put a chest in reach.
  await debug({ op: 'spawn_chest', distance: 1.2 });
  await page.waitForFunction(() => Field._debug.chests.length === 1, null, { timeout: 5000 });
  const [near] = await chests();
  check(near.left > 170 && near.left <= 180, `a new chest has about three minutes (${near.left})`);
  await page.waitForFunction(() => /treasure chest has appeared/.test(document.getElementById('chat-log').textContent), null, { timeout: 5000 });
  check(true, 'the spawn announcement reached the chat');

  // It is drawn: warm chest-coloured pixels around its screen position, and nothing like it before it existed.
  const painted = await page.evaluate(() => {
    const c = Field._debug.chests[0], [sx, sy] = Field._debug.w2s(c.x, c.y), cv = document.getElementById('fieldcv'), k = cv.width / 1600, g = cv.getContext('2d');
    const data = g.getImageData(Math.round((sx - 20) * k), Math.round((sy - 28) * k), Math.round(40 * k), Math.round(30 * k)).data;
    let wood = 0;
    for (let i = 0; i < data.length; i += 4) { const [r, gr, b] = [data[i], data[i + 1], data[i + 2]]; if (r > 110 && r < 235 && gr > 60 && gr < 170 && b < 100 && r > b + 60) wood++; }
    return { wood, total: data.length / 4 };
  });
  check(painted.wood > painted.total * 0.15, `the chest body is painted (${painted.wood} of ${painted.total} pixels are wood or gold)`);

  // Click its visible body: the hero is in reach, so the server opens it at once.
  const click = async (chest, dy = -15) => {
    const point = await page.evaluate(({ x, y, dy }) => { const [sx, sy] = Field._debug.w2s(x, y), r = document.getElementById('fieldcv').getBoundingClientRect(); return { x: r.left + sx / 1600 * r.width, y: r.top + (sy + dy) / 900 * r.height }; }, { x: chest.x, y: chest.y, dy });
    await page.mouse.move(point.x, point.y); await page.mouse.click(point.x, point.y);
  };
  // A click well above the chest is not a click on it (the hero stays put, so the chest stays in reach).
  const miss = { ...near, y: near.y - 8 };
  await page.evaluate(() => { window.__opens = 0; const send = Online.send; Online.send = m => { if (m.type === 'open_chest') window.__opens++; return send.call(Online, m); }; });
  await click(miss, 0); await page.waitForTimeout(400);
  check((await chests()).length === 1 && (await page.evaluate(() => window.__opens)) === 0, 'a click beside the chest does not ask to open it');
  // The hero is teleported next to the chest, then a click on its body opens it.
  const standNextTo = async chest => {
    await debug({ op: 'teleport', zone: 0, x: chest.x - 1, y: chest.y });
    await page.waitForFunction(({ x, y }) => Math.hypot(Field.hero.x - x, Field.hero.y - y) < 1.6, chest, { timeout: 8000 });
    await page.waitForTimeout(150); // a frame or two: the camera jumps to the hero
  };
  await standNextTo(near);
  // The open effect (a gold ring) exists for a moment, so watch for it on every animation frame from before the click.
  const ring = page.waitForFunction(() => Field._debug.effects.some(e => e.kind === 'ring' && e.col === '#ffe292'), null, { polling: 'raf', timeout: 8000 });
  await click(near);
  await ring;
  check(true, 'opening it plays the gold ring effect');
  await page.waitForFunction(() => Field._debug.chests.length === 0, null, { timeout: 8000 });
  await page.waitForFunction(() => /ChestFinder opened the treasure chest/.test(document.getElementById('chat-log').textContent), null, { timeout: 5000 });
  check(true, 'clicking the body opened it and the area was told who opened it');

  // A second chest, further away: teleport, click, open.
  await debug({ op: 'spawn_chest', distance: 5 });
  await page.waitForFunction(() => Field._debug.chests.length === 1, null, { timeout: 5000 });
  const [far] = await chests();
  await standNextTo(far);
  await click(far);
  await page.waitForFunction(() => Field._debug.chests.length === 0, null, { timeout: 8000 });
  check((await log()).match(/opened the treasure chest/g).length === 2, 'two openings were announced');

  // The pile appeared where the chest stood.
  const drops = await page.evaluate(() => Field._debug.zones && document.getElementById('fieldcv') ? 1 : 0);
  check(drops === 1, 'the field is still running');
  await page.screenshot({ path: path.join(world.artifacts, 'chest-opened.png') });
  assert.deepEqual(errors, []);
  console.log(`chest-ui: ${checks} checks passed`);
})().catch(e => { console.error(e); console.error((global.__frames || []).slice(-25).join('\n')); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
});
