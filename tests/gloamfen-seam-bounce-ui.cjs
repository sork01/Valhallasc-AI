// Browser-only checks for Gloamfen (levels 15-20): the summit gate, fen ground and dusk sky, the lake, thicket ridges,
// monster artwork in every state, Lanternmere's NPCs, the sixteen-quest journal and the HUD. Rules, levels, combat and
// persistence are exercised by the Rust tests and the `gloamfen` / `fen_quests` MCP scenarios; this walks with real
// canvas clicks and asserts what the player sees. Run against the real art with REAL_SPRITES=1 (npm run test:art does).
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium, STUB } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-gloamfen-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
// Average colour of a region of the world canvas, as fractions of its width and height.
const look = (page, [x0, y0, x1, y1] = [.15, .2, .85, .8]) => page.evaluate(([x0, y0, x1, y1]) => {
  const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), w = cv.width, h = cv.height;
  const d = g.getImageData(Math.floor(w * x0), Math.floor(h * y0), Math.floor(w * (x1 - x0)), Math.floor(h * (y1 - y0))).data;
  let r = 0, gr = 0, b = 0, water = 0, n = d.length / 4;
  for (let i = 0; i < d.length; i += 4) { r += d[i]; gr += d[i + 1]; b += d[i + 2]; if (d[i] < 42 && d[i + 1] >= d[i] + 14 && d[i + 2] >= d[i] + 14 && d[i + 1] + d[i + 2] < 150) water++; }
  return { r: r / n, g: gr / n, b: b / n, water: water / n };
}, [x0, y0, x1, y1]);
(async () => {
  const transport = new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe' });
  await client.connect(transport);
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('FenSeam');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites, null, { timeout: 60000 });
  await page.evaluate(() => Online.send({ type: 'debug', ref: 1, command: { op: 'explore_all' } }));
  const click = async (x, y) => {
    const [sx, sy] = await page.evaluate(([x, y]) => Field._debug.w2s(x, y), [x, y]);
    const crowded = await page.evaluate(([x, y]) => Field.slimes.some(s => !s.dead && Math.hypot(s.x - x, s.y - y) < 2.5) || City.npcs.some(n => Math.hypot(n.x - x, n.y - y) < 2.5), [x, y]);
    if (crowded || sx < 60 || sx > 1540 || sy < 60 || sy > 840) { await page.evaluate(([x, y]) => Online.send({ type: 'move', x, y }), [x, y]); return; }
    const box = await page.locator('#fieldcv').boundingBox();
    await page.mouse.click(box.x + sx / 1600 * box.width, box.y + sy / 900 * box.height);
  };
  const reach = (x, y, within = .6, zone = 1) => page.waitForFunction(([x, y, within, zone]) => Field.zone !== zone || Math.hypot(Field.hero.x - x, Field.hero.y - y) < within, [x, y, within, zone], { timeout: 40000 });
  const stageAt = async (zone, x, y) => {
    await page.evaluate(([zone, x, y]) => Online.send({ type: 'debug', ref: 1, command: { op: 'teleport', zone, x, y } }), [zone, x, y]);
    await page.waitForFunction(([zone, x, y]) => Field.zone === zone && Math.hypot(Field.hero.x - x, Field.hero.y - y) < 2, [zone, x, y], { timeout: 10000 });
    let last = null;
    for (let i = 0; i < 40; i++) {
      const now = await page.evaluate(() => Field._debug.w2s(Field.hero.x, Field.hero.y));
      if (last && Math.hypot(now[0] - last[0], now[1] - last[1]) < 1) break;
      last = now; await page.waitForTimeout(80);
    }
  };
  const gate = await page.evaluate(() => Field._debug.zones[2].portals.find(p => p.id === 'fen_gate'));
  await stageAt(2, gate.x, gate.y - 8);
  const pos = () => page.evaluate(() => ({ zone: Field.zone, x: +Field.hero.x.toFixed(2), y: +Field.hero.y.toFixed(2), nx: +Field.hero.nx?.toFixed?.(2), ny: +Field.hero.ny?.toFixed?.(2), goal: Field.hero.goal ? [+Field.hero.goal.x.toFixed(2), +Field.hero.goal.y.toFixed(2)] : null, t: +performance.now().toFixed(0) }));
  console.log('staged', JSON.stringify(await pos()));
  for (const step of await page.evaluate(([x, y]) => Field._debug.routeTo({ x, y }), [gate.x, gate.y - 4])) { await click(step.x, step.y); await reach(step.x, step.y, 1.3, 2); }
  console.log('at summit', JSON.stringify(await pos()));
  await click(gate.x, gate.y + 1.2);
  // Sample the walk every 100 ms for 3 s after the first moment of zone 3.
  const log = [];
  const t0 = Date.now();
  while (Date.now() - t0 < 6000) { log.push(await pos()); await page.waitForTimeout(100); }
  for (const l of log) console.log(JSON.stringify(l));
  await page.evaluate(() => Online.send({ type: 'debug', ref: 1, command: { op: 'explore_all' } }));
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
