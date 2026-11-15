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
        // Snapshots are raw-deflate binary frames when the client offers compress:true; inflate them the way online.js does.
        let text = e.data;
        if (typeof text !== 'string') { try { text = window.pako.inflateRaw(new Uint8Array(text), { to: 'string' }); } catch (_) { return; } }
        if (!text.includes('"type":"snapshot"')) return;
        const p = JSON.parse(text), own = p.players?.find(q => q.id === window.Online?.id);
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
  // Open ground in Greenmeadow straight south of Alderhaven (a start that needs no detour round scenery: a hairpin at the start made the hero pause at its first corner), outside every hub and about 49 tiles from the Visit button's goal in Alderhaven (the old (36,79) plus the zone's shape offset (207,107)): the Visit button shows and the walk is long.
  // The pier a new hero starts on is Saltby's hub, where the button is hidden.
  const [SX, SY] = (process.env.START || '250,235').split(',').map(Number);
  const START = { x: SX, y: SY }, GOAL = { x: 243, y: 186 };
  await page.evaluate(p => Online.send({ type: 'debug', ref: 1, command: { op: 'teleport', zone: 0, x: p.x, y: p.y } }), START);
  await page.waitForFunction(p => Math.hypot(Field.hero.x - p.x, Field.hero.y - p.y) < 3, START, { timeout: 10000 });
  await page.waitForTimeout(1500);
  const start = await page.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y }));
  check(await page.evaluate(() => !document.getElementById('city-travel').hidden), 'The Visit Alderhaven button shows away from the city');

  // The route is a few straight runs, not a waypoint on every tile.
  const route = await page.evaluate(g => Field._debug.routeTo(g), GOAL);
  const length = route.reduce((sum, p, i) => sum + Math.hypot(p.x - (i ? route[i - 1].x : start.x), p.y - (i ? route[i - 1].y : start.y)), 0);
  check(length > 40 && route.length <= length / 4, `The route of ${length.toFixed(0)} tiles has ${route.length} waypoints (at most one per 4 tiles)`);
  check(Math.hypot(route.at(-1).x - GOAL.x, route.at(-1).y - GOAL.y) < 1.5, 'The route ends at the Alderhaven goal');

  // Record every move goal the client sends, with the hero's server position at that moment.
  await page.evaluate(() => {
    window.__moves = []; const send = Online.send.bind(Online);
    Online.send = m => { if (m?.type === 'move' && window.__record) window.__moves.push({ goal: { x: m.x, y: m.y }, at: { x: Field.hero.nx, y: Field.hero.ny } }); return send(m); };
  });
  await page.evaluate(() => { window.__snaps.length = 0; window.__record = true; });
  await page.locator('#city-travel').click();
  await page.waitForFunction(s0 => window.__snaps.length > 0 && Math.hypot(window.__snaps.at(-1)[1] - s0.x, window.__snaps.at(-1)[2] - s0.y) > 24, start, { timeout: 30000 });
  const snaps = await page.evaluate(() => { window.__record = false; return window.__snaps; });

  // Speed between consecutive snapshots, in game time. Drop the start (the hero is still standing) and the end (arrival).
  const speeds = [];
  for (let i = 1; i < snaps.length; i++) {
    const dt = snaps[i][0] - snaps[i - 1][0];
    if (dt > 0) speeds.push({ t: snaps[i][0], v: Math.hypot(snaps[i][1] - snaps[i - 1][1], snaps[i][2] - snaps[i - 1][2]) / dt });
  }
  if (process.env.DUMP) console.log('route', JSON.stringify(route), '\nspeeds', speeds.slice(0, 60).map(s => `${s.t.toFixed(2)}:${s.v.toFixed(1)}@${snaps[speeds.indexOf(s) + 1].slice(1).map(v => v.toFixed(1))}`).join(' '));
  const moving = speeds.findIndex(s => s.v > 1);
  const mid = speeds.slice(moving + 1, speeds.length - 3);
  check(mid.length >= 30, `${mid.length} snapshots along the walk`);
  const nominal = median(mid.map(s => s.v));
  check(nominal > 4 && nominal < 9, `Walking speed is ${nominal.toFixed(2)} tiles/s`);
  const slow = mid.filter(s => s.v < nominal * .75).length;
  check(slow <= Math.ceil(mid.length * .08), `${slow} of ${mid.length} snapshots show the hero at under 75% of the walking speed (it stood still at every waypoint before)`);
  const moves = await page.evaluate(() => window.__moves);
  // Lead at each corner: how far from waypoint i the hero still was (server position) when the goal moved on to waypoint i+1.
  const leads = [];
  for (let i = 0; i + 1 < route.length; i++) {
    const m = moves.find(m => Math.hypot(m.goal.x - route[i + 1].x, m.goal.y - route[i + 1].y) < .01);
    if (m) leads.push({ corner: route[i], lead: Math.hypot(m.at.x - route[i].x, m.at.y - route[i].y) });
  }
  if (process.env.DUMP) console.log('leads', leads.map(l => `${l.corner.x},${l.corner.y}:${l.lead.toFixed(2)}`).join(' '));
  // No corner may hold the hero: at most one snapshot (0.1 s) standing still mid-walk (a waypoint held back until the hero stood on a hard corner cost two).
  let still = 0, longestStill = 0;
  for (const s of mid) { still = s.v < 1 ? still + 1 : 0; longestStill = Math.max(longestStill, still); }
  if (process.env.DUMP) console.log('longestStill', longestStill);
  check(leads.length >= (process.env.START ? 3 : 0) && leads.every(l => l.lead >= .3), `Every corner's next leg goes out at least .3 tiles before the hero reaches it (leads ${leads.map(l => l.lead.toFixed(2)).join(', ')}): a leg sent from the corner itself held the server still`);
  check(longestStill <= 1, `The hero never stands still for more than one snapshot mid-walk (longest ${longestStill})`);
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
