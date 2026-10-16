// TIME-CHECK in a private world: the clock keeps 24 game hours to 20 real minutes, two clients show the same hour, every
// outdoor zone stays readable at midnight while every enclosed one ignores the cycle, and the night tint stays inside
// the render budget. The server-side halves (the stored epoch surviving a restart, the frozen test clock) are the Rust
// tests in world/daynight.rs. Screenshots of the darkest hour go to the world's artifacts folder.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-daynight-check', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, label) => { assert.ok(value, label); checks++; };
async function call(name, args = {}) {
  const reply = await client.callTool({ name, arguments: args });
  assert.ok(!reply.isError, `${name}: ${JSON.stringify(reply.content)}`);
  return reply.structuredContent;
}
const wrap = (a, b) => { const d = Math.abs(a - b) % 24; return Math.min(d, 24 - d); };
async function join(world, name) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
  page.errors = []; page.on('pageerror', e => page.errors.push(e.message));
  await page.addInitScript(() => { localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })); });
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill(name); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!window.DayNight && DayNight.hour >= 0 && Field.hero?.hp > 0, null, { timeout: 60000 });
  return page;
}
const debug = (page, command) => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);
// Mean brightness (0-255) of the middle of the world canvas.
const brightness = page => page.evaluate(() => {
  const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), w = cv.width, h = cv.height;
  const d = g.getImageData(Math.floor(w * .2), Math.floor(h * .2), Math.floor(w * .6), Math.floor(h * .6)).data;
  let sum = 0; for (let i = 0; i < d.length; i += 4) sum += .2126 * d[i] + .7152 * d[i + 1] + .0722 * d[i + 2];
  return sum / (d.length / 4);
});
const taskSeconds = async cdp => (await cdp.send('Performance.getMetrics')).metrics.find(m => m.name === 'TaskDuration').value;

(async () => {
  const env = { ...getDefaultEnvironment(), ...(process.env.VALHALLA_BINARY ? { VALHALLA_BINARY: process.env.VALHALLA_BINARY } : {}) };
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const a = await join(world, 'ClockA'), b = await join(world, 'ClockB');

  // --- the clock: 24 game hours in 1,200 real seconds, the same for every client ---
  await debug(a, { op: 'set_time', hour: 6, freeze: false });
  await a.waitForTimeout(1500);
  const read = page => page.evaluate(() => ({ hour: DayNight.hour, at: performance.now() }));
  const [a0, b0] = await Promise.all([read(a), read(b)]);
  check(wrap(a0.hour, b0.hour) < .1, `two clients show the same hour (${a0.hour.toFixed(2)} and ${b0.hour.toFixed(2)})`);
  await a.waitForTimeout(8000);
  const [a1, b1] = await Promise.all([read(a), read(b)]);
  const rate = (wrap(a1.hour, a0.hour)) / ((a1.at - a0.at) / 1000);
  check(Math.abs(rate - .02) < .001, `the clock runs at 0.02 game hours per real second (${rate.toFixed(4)})`);
  check(Math.abs(24 / rate - 1200) < 60, `24 game hours take ${(24 / rate).toFixed(0)} real seconds`);
  check(wrap(a1.hour, b1.hour) < .1, `the clients still agree after eight seconds (${a1.hour.toFixed(2)} and ${b1.hour.toFixed(2)})`);

  // --- every zone at midnight against noon ---
  await debug(a, { op: 'set_god_mode', enabled: true });
  const zones = await a.evaluate(() => WORLD_MAP.zones.map((z, i) => ({ n: i + 1, name: z.name, spawn: z.spawn, outdoor: DayNight.isOutdoor(z) })));
  const reached = [], skipped = [], rows = [];
  for (const z of zones) {
    await debug(a, { op: 'set_time', hour: 12, freeze: true });
    await debug(a, { op: 'teleport', zone: z.n, x: z.spawn.x, y: z.spawn.y });
    try { await a.waitForFunction(n => Field.zone === n, z.n, { timeout: 5000 }); } catch { skipped.push(`${z.n} ${z.name}`); continue; }
    await a.waitForFunction(outdoor => outdoor ? DayNight.outdoorBlend > .9 : DayNight.outdoorBlend < .1, z.outdoor, { timeout: 6000 });
    await a.waitForFunction(() => Math.abs(DayNight.hour - 12) < .01, null, { timeout: 5000 });
    await a.waitForTimeout(700);
    const noon = await brightness(a);
    await debug(a, { op: 'set_time', hour: 0, freeze: true });
    await a.waitForFunction(() => Math.abs(DayNight.hour) < .01 || Math.abs(DayNight.hour - 24) < .01, null, { timeout: 5000 });
    await a.waitForTimeout(1500);
    const night = await brightness(a);
    if (z.n % 6 === 1) await a.screenshot({ path: path.join(world.artifacts, `midnight-zone-${z.n}.png`) });
    reached.push(z.n); rows.push({ ...z, noon, night });
  }
  check(reached.length >= 25, `most zones can be visited (${reached.length} of ${zones.length}; unreachable: ${skipped.join(', ') || 'none'})`);
  for (const r of rows.filter(r => r.outdoor && r.noon > 20)) {
    check(r.night >= 10, `zone ${r.n} ${r.name} stays readable at midnight (brightness ${r.night.toFixed(0)})`);
    check(r.night >= r.noon * .2, `zone ${r.n} ${r.name} keeps a gentle floor (${r.night.toFixed(0)} of ${r.noon.toFixed(0)} at noon)`);
  }
  const indoor = rows.filter(r => !r.outdoor);
  for (const r of indoor) check(Math.abs(r.night - r.noon) <= Math.max(3, r.noon * .06), `enclosed zone ${r.n} ${r.name} ignores the cycle (${r.noon.toFixed(0)} at noon, ${r.night.toFixed(0)} at midnight)`);
  check(indoor.length >= 5, `enclosed zones were checked (${indoor.length})`);

  // --- render budget: main-thread time at midnight with the tint on, off and at noon ---
  await debug(a, { op: 'teleport', zone: 0, x: 36, y: 60 });
  await a.waitForFunction(() => Field.zone === 0 && DayNight.outdoorBlend > .9, null, { timeout: 8000 });
  const cdp = await a.context().newCDPSession(a); await cdp.send('Performance.enable');
  const cost = async (hour, night) => {
    await a.evaluate(n => Prefs.set({ night: n }), night);
    await debug(a, { op: 'set_time', hour, freeze: true });
    await a.waitForTimeout(1500);
    const start = await taskSeconds(cdp); await a.waitForTimeout(6000);
    return (await taskSeconds(cdp)) - start;
  };
  const costs = { tintOn: [], tintOff: [] };
  for (let round = 0; round < 2; round++) { costs.tintOn.push(await cost(0, 1)); costs.tintOff.push(await cost(0, 0)); }
  const on = Math.min(...costs.tintOn), off = Math.min(...costs.tintOff);
  check(on <= off * 1.35 + .1, `the night tint stays inside the render budget (${on.toFixed(2)} s with it, ${off.toFixed(2)} s without, per six seconds)`);
  check(a.errors.length + b.errors.length === 0, `no browser errors: ${[...a.errors, ...b.errors].join('; ')}`);
  console.log(`${checks} day/night verification checks passed; screenshots: ${world.artifacts}`);
  console.log('zone brightness (noon -> midnight):', rows.map(r => `${r.n}${r.outdoor ? '' : '*'}:${r.noon.toFixed(0)}->${r.night.toFixed(0)}`).join(' '));
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  if (browser) await browser.close();
  if (started) { try { await call('stop_world'); } catch (_) {} }
  await client.close();
});
