const { frameJson } = require('./lib/frames.cjs');
// Opening or closing a window, or focusing the chat, must not interrupt a basic attack on the selected monster, while it still
// halts walking. MUTATE=1 serves a field.js that forgets the selection (the old `stop`), which must fail.
// Run: bash scripts/test-touch-bounded.sh tests/autoattack-window-ui.cjs   (needs a `--profile test` or release binary)
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-autoattack-window', version: '1.0.0' });
let browser, started = false;
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath,
    args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe',
    env: { ...process.env, VALHALLA_BINARY: process.env.VALHALLA_BINARY || path.join(root, 'target/release/valhalla-server') } }));
  const world = await call('start_world', { startLevel: 99, godMode: true, levelSpread: 0 }); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const snapshots = [], events = [], errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('websocket', socket => socket.on('framereceived', ({ payload }) => {
    const packet = frameJson(payload);
    if (packet.type === 'snapshot') snapshots.push(packet);
    if (packet.type === 'event') events.push({ ...packet, time: snapshots.at(-1)?.time || 0 });
  }));
  if (process.env.MUTATE === '1') {
    await page.route('**/field.js*', async route => {
      const response = await route.fetch(); let text = await response.text();
      assert.ok(text.includes('keepAttack = id !== null'), 'the fix is in field.js');
      await route.fulfill({ response, body: text.replace('keepAttack = id !== null', 'keepAttack = false && id !== null') });
    });
  }
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('Autowin');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero.level === 99, null, { timeout: 60000 });
  const actor = await page.evaluate(() => Online.id);
  const debug = command => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);
  await debug({ op: 'teleport', zone: 0, x: 250, y: 235 });
  await page.waitForFunction(() => Field.zone === 0 && Math.hypot(Field.hero.x - 250, Field.hero.y - 235) < 8, null, { timeout: 30000 });
  await page.waitForTimeout(500);
  const home = await page.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y }));
  for (const id of await page.evaluate(h => Field.slimes.filter(s => !s.dead && Math.hypot(s.x - h.x, s.y - h.y) < 15).map(s => s.id), home)) await debug({ op: 'kill_enemy', id });
  await debug({ op: 'spawn_enemy', kind: 'cf_brute', level: 99, x: home.x + 3, y: home.y + 3 });
  await page.waitForFunction(() => Field.slimes.some(s => s.kind === 'cf_brute' && !s.dead), null, { timeout: 15000 });
  const brute = await page.evaluate(() => Field.slimes.find(s => s.kind === 'cf_brute' && !s.dead).id);
  assert.equal(await page.evaluate(id => Field.targetEnemy(id), brute), true, 'the real selection path accepted the monster');
  const swings = since => events.filter(e => e.time >= since && e.actor === actor && ['cast', 'swing'].includes(e.kind)).length;
  const serverTime = () => snapshots.at(-1).time;
  async function window2(seconds) {            // let `seconds` of server time pass
    const until = serverTime() + seconds, deadline = Date.now() + 30000;
    while (serverTime() < until && Date.now() < deadline) await page.waitForTimeout(100);
    assert.ok(serverTime() >= until, 'the private server advanced');
  }
  await window2(2.5);
  assert.ok(swings(0) >= 2, `the fixture attacks by itself first (${swings(0)})`);
  let checks = 0;
  const steps = [
    ['open a window (setPaused true)', () => page.evaluate(() => Field.setPaused(true))],
    ['close it again (setPaused false)', () => page.evaluate(() => Field.setPaused(false))],
    ['focus the chat box', () => page.evaluate(() => document.querySelector('#chat-input').focus())],
  ];
  for (const [label, act] of steps) {
    const from = serverTime(); await act(); await window2(3);
    const n = swings(from + .2);
    assert.ok(n >= 2, `${label}: the basic attack went on (${n} swings in 3 s)`);
    assert.equal(await page.evaluate(() => Field.hero.target?.id), brute, `${label}: the monster is still selected`);
    console.log(`${label}: ${n} swings in 3 s, target kept`); checks++;
  }
  // Walking is still halted by a window: no selection, a click-to-move walk, then a window.
  await page.evaluate(() => { Field.hero.target = null; Online.send({ type: 'stop' }); });
  await debug({ op: 'kill_enemy', id: brute });
  await page.waitForFunction(id => Field.slimes.find(s => s.id === id)?.dead, brute);
  await page.evaluate(h => Online.send({ type: 'move', x: h.x - 12, y: h.y - 12 }), home);
  const start = await page.evaluate(() => ({ x: Field.hero.nx, y: Field.hero.ny }));
  await page.waitForFunction(s => Math.hypot(Field.hero.nx - s.x, Field.hero.ny - s.y) > .5, start, { timeout: 8000 });
  await page.evaluate(() => Field.setPaused(true));
  const track = [];
  for (let i = 0; i < 8; i++) { await page.waitForTimeout(250); track.push(await page.evaluate(() => [Field.hero.nx, Field.hero.ny].map(v => +v.toFixed(2)))); }
  console.log('after the window opened:', JSON.stringify(track));
  const rest = { x: track[3][0], y: track[3][1] }, later = { x: track[7][0], y: track[7][1] };
  assert.ok(Math.hypot(later.x - rest.x, later.y - rest.y) < .05, `a window still halts a walk (${JSON.stringify(rest)} -> ${JSON.stringify(later)})`); checks++;
  assert.deepEqual(errors, []);
  console.log(`autoattack-window-ui: ${checks} checks passed`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
