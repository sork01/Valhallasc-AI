// "Visit Alderhaven" walks a route of waypoints: the hero must keep moving at full speed along it. The follower used to wait until the
// eased sprite was within .32 of each one-per-tile waypoint, but the sprite trails the server by about speed/14 tiles, so the server
// reached every waypoint, stood still, and waited for the client to catch up (a stutter at about 1.4 tiles/s instead of 5.2).
// The test reads the server's own positions and clock out of the snapshots (game time, so a slow machine does not matter).
// Needs a release server for stable timing: it defaults to target/release/valhalla-server when that exists.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const release = path.join(root, 'target/release/valhalla-server');
if (!process.env.VALHALLA_BINARY && fs.existsSync(release)) process.env.VALHALLA_BINARY = release;
const client = new Client({ name: 'valhallasc-walk-route-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
const median = a => [...a].sort((x, y) => x - y)[Math.floor(a.length / 2)];
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe' }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => {
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null }));
    // Record the hero's server position and the server clock from every snapshot.
    window.__snaps = [];
    const Native = window.WebSocket;
    window.WebSocket = function (...args) {
      const ws = new Native(...args);
      ws.addEventListener('message', e => {
        if (typeof e.data !== 'string' || !e.data.includes('"type":"snapshot"')) return;
        const p = JSON.parse(e.data), own = p.players?.find(q => q.id === window.Online?.id);
        if (own && window.__record) window.__snaps.push([p.time, own.x, own.y]);
      });
      return ws;
    };
    window.WebSocket.prototype = Native.prototype;
    Object.assign(window.WebSocket, { CONNECTING: 0, OPEN: 1, CLOSING: 2, CLOSED: 3 });
  });
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('WalkRoute');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites, null, { timeout: 60000 });
  // Far east of Alderhaven, in Greenmeadow, so the Visit button shows and the walk is long.
  await page.evaluate(() => Online.send({ type: 'debug', ref: 1, command: { op: 'teleport', zone: 0, x: 80, y: 25 } }));
  await page.waitForFunction(() => Math.hypot(Field.hero.x - 80, Field.hero.y - 25) < 3, null, { timeout: 10000 });
  await page.waitForTimeout(1500);
  check(await page.evaluate(() => !document.getElementById('city-travel').hidden), 'The Visit Alderhaven button shows away from the city');

  // The route is a few straight runs, not a waypoint on every tile.
  const route = await page.evaluate(() => Field._debug.routeTo({ x: 36, y: 79 }));
  const length = route.reduce((sum, p, i) => sum + Math.hypot(p.x - (i ? route[i - 1].x : 80), p.y - (i ? route[i - 1].y : 25)), 0);
  check(length > 40 && route.length <= length / 4, `The route of ${length.toFixed(0)} tiles has ${route.length} waypoints (at most one per 4 tiles)`);
  check(Math.hypot(route.at(-1).x - 36, route.at(-1).y - 79) < 1.5, 'The route ends at the Alderhaven goal');

  await page.evaluate(() => { window.__snaps.length = 0; window.__record = true; });
  await page.locator('#city-travel').click();
  await page.waitForFunction(() => window.__snaps.length > 0 && Math.hypot(window.__snaps.at(-1)[1] - 80, window.__snaps.at(-1)[2] - 25) > 24, null, { timeout: 30000 });
  const snaps = await page.evaluate(() => { window.__record = false; return window.__snaps; });

  // Speed between consecutive snapshots, in game time. Drop the start (the hero is still standing) and the end (arrival).
  const speeds = [];
  for (let i = 1; i < snaps.length; i++) {
    const dt = snaps[i][0] - snaps[i - 1][0];
    if (dt > 0) speeds.push({ t: snaps[i][0], v: Math.hypot(snaps[i][1] - snaps[i - 1][1], snaps[i][2] - snaps[i - 1][2]) / dt });
  }
  const moving = speeds.findIndex(s => s.v > 1);
  const mid = speeds.slice(moving + 1, speeds.length - 3);
  check(mid.length >= 30, `${mid.length} snapshots along the walk`);
  const nominal = median(mid.map(s => s.v));
  check(nominal > 4 && nominal < 9, `Walking speed is ${nominal.toFixed(2)} tiles/s`);
  const slow = mid.filter(s => s.v < nominal * .75).length;
  check(slow <= Math.ceil(mid.length * .08), `${slow} of ${mid.length} snapshots show the hero at under 75% of the walking speed (it stood still at every waypoint before)`);
  // Average over one-second windows of game time: no window may lose more than 20% of its distance.
  let worst = Infinity;
  for (let a = 0; a + 1 <= mid.at(-1).t - mid[0].t; a += .5) {
    const inside = mid.filter(s => s.t >= mid[0].t + a && s.t < mid[0].t + a + 1);
    if (inside.length >= 8) worst = Math.min(worst, inside.reduce((sum, s) => sum + s.v, 0) / inside.length / nominal);
  }
  check(worst >= .8, `The slowest one-second window of the walk is ${(worst * 100).toFixed(0)}% of the walking speed`);
  check(errors.length === 0, `No page errors: ${errors.join(' | ')}`);
  console.log(`walk-route-ui: ${checks} checks passed`);
})().then(() => cleanup(0), async e => { console.error(e); await cleanup(1); });
async function cleanup(code) {
  try { await browser?.close(); } catch {}
  try { if (started) await call('stop_world'); } catch {}
  try { await client.close(); } catch {}
  process.exit(code);
}
