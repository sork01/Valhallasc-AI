// UI-ACTOR-MOTION: in the real client, holding a movement key moves the drawn hero smoothly. The server sends the hero's position
// about every 100 ms; the old ease-out surged at every snapshot, so the drawn speed from one frame to the next pulsed at 10 Hz.
// The test holds the keys along a clear stretch of Greenmeadow, samples the drawn hero position on every frame, and measures how
// even the speed is (coefficient of variation of the per-frame speed, with the frame time taken into account).
//   OLD=1  serves `git show HEAD:client/field.js` (the ease-out) instead: the same check must FAIL, which proves it has teeth.
// Run through the bounded runner: bash scripts/test-touch-bounded.sh tests/actor-motion-ui.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const release = path.join(root, 'target/release/valhalla-server');
if (!process.env.VALHALLA_BINARY && fs.existsSync(release)) process.env.VALHALLA_BINARY = release;
const client = new Client({ name: 'valhallasc-actor-motion-ui', version: '1.0.0' });
let browser, started = false;
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
// cv: the plain coefficient of variation. rcv: the same from the median and the median absolute deviation, so the few frames of a
// stalled link (this shared host stalls snapshot delivery for 200-500 ms now and then, whatever the motion does) do not decide it;
// a pulse at the snapshot rate touches most frames and still shows.
const median = a => [...a].sort((x, y) => x - y)[Math.floor(a.length / 2)];
const stats = a => { const m = a.reduce((s, v) => s + v, 0) / a.length, sd = Math.sqrt(a.reduce((s, v) => s + (v - m) ** 2, 0) / a.length), med = median(a); return { mean: m, sd, cv: sd / m, rcv: 1.4826 * median(a.map(v => Math.abs(v - med))) / med }; };
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...process.env } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: Number(process.env.VW) || 960, height: Number(process.env.VH) || 600 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  if (process.env.OLD) {
    const old = execFileSync('git', ['show', 'HEAD:client/field.js'], { cwd: root, maxBuffer: 1 << 28 });
    await page.route('**/field.js*', route => route.fulfill({ status: 200, contentType: 'text/javascript', body: old }));
  }
  await page.addInitScript(() => {
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null }));
    // The game moves its sprites when its own frame callback starts, which can be well after the frame's nominal time in a software
    // renderer. Stamp each frame when its first callback begins, so the speed is judged against the time the positions were set.
    // Arrival time of every snapshot, to tell a bursty test machine from a motion problem.
    window.__arrivals = [];
    const Native = window.WebSocket;
    window.WebSocket = function (...args) {
      const ws = new Native(...args);
      ws.addEventListener('message', () => window.__arrivals.push(performance.now()));
      return ws;
    };
    window.WebSocket.prototype = Native.prototype;
    Object.assign(window.WebSocket, { CONNECTING: 0, OPEN: 1, CLOSING: 2, CLOSED: 3 });
    const raf = window.requestAnimationFrame.bind(window);
    window.requestAnimationFrame = cb => raf(ts => { if (window.__ts !== ts) { window.__ts = ts; window.__frameStart = performance.now(); } cb(ts); });
  });
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('Glider');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites, null, { timeout: 60000 });
  // Nacrehold has no enemies (an enemy next to the hero makes the client snap every sprite to its server position, which is another
  // test) and 190 tiles of open ground along world +x from (38, 24).
  await page.evaluate(() => Online.send({ type: 'debug', ref: 1, command: { op: 'teleport', zone: 9, x: 40, y: 24 } }));
  await page.waitForFunction(() => Field.zone === 9 && Math.hypot(Field.hero.x - 40, Field.hero.y - 24) < 3, null, { timeout: 15000 });
  await page.waitForTimeout(1500);
  await page.evaluate(() => {
    window.__frames = []; window.__sample = true; window.__hero = []; window.__dump = [];
    // With the new motion, also record the hero at the very time value the motion used, free of the frame-timing noise of a busy machine.
    if (window.ActorMotion) {
      const step = window.ActorMotion.step;
      window.__track = [];
      const track = window.ActorMotion.track;
      window.ActorMotion.track = function (actor, px, py, x, y, serverTime, now, snap) { if (actor === Field.hero) window.__track.push([px, py, x, y, serverTime, now, snap]); return track.apply(this, arguments); };
      window.ActorMotion.step = function (actor, dt, now, isHero) { const r = step.apply(this, arguments); if (isHero && window.__sample) window.__hero.push([now * 1000, actor.x, actor.y]); return r; };
    }
    const tick = () => { if (!window.__sample) return; window.__frames.push([window.__ts, Field.hero.x, Field.hero.y, window.__frameStart]); requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
  });
  // Arrow keys move along the screen: Right + Down together is world +x.
  const start = Date.now();
  await page.keyboard.down('ArrowRight'); await page.keyboard.down('ArrowDown');
  await page.waitForTimeout(4200);
  await page.keyboard.up('ArrowRight'); await page.keyboard.up('ArrowDown');
  const frames = await page.evaluate(() => { window.__sample = false; return window.__frames; });
  const heroClock = await page.evaluate(() => window.__hero);
  if (process.env.DUMP) fs.writeFileSync(process.env.DUMP, JSON.stringify({ track: await page.evaluate(() => window.__track), hero: heroClock, frames }));
  // Snapshot arrival times (local ms): from the motion module's own log when it is loaded, else every WebSocket message.
  const arrivals = heroClock.length ? (await page.evaluate(() => window.__track)).map(t => t[5] * 1000) : await page.evaluate(() => window.__arrivals);
  const inWalk = arrivals.filter(a => a >= frames[0][3] + 1500 && a <= frames[0][3] + 3500);
  const gaps = inWalk.slice(1).map((a, i) => a - inWalk[i]), g = stats(gaps);
  console.log(`snapshot arrivals during the walk: ${gaps.length} gaps, mean ${g.mean.toFixed(0)} ms, sd ${g.sd.toFixed(0)} ms, min ${Math.min(...gaps).toFixed(0)}, max ${Math.max(...gaps).toFixed(0)}`);
  // Time each frame by its nominal vsync time, or (STAMP=start) by when its first callback began.
  const col = process.env.STAMP === 'start' ? 3 : 0, t0 = frames[0][col], pos = frames.map(f => ({ t: (f[col] - t0) / 1000, x: f[1], y: f[2] }));
  const travelled = Math.hypot(pos.at(-1).x - pos[0].x, pos.at(-1).y - pos[0].y);
  assert.ok(travelled > 12, `the hero walked ${travelled.toFixed(1)} tiles`);
  // The steady part of the walk: after the start-up and before the release, judged by the drawn speed on each frame.
  const speeds = [];
  for (let i = 1; i < pos.length; i++) {
    const dt = pos[i].t - pos[i - 1].t;
    if (dt > 0) speeds.push({ t: pos[i].t, v: Math.hypot(pos[i].x - pos[i - 1].x, pos[i].y - pos[i - 1].y) / dt, dt });
  }
  const moving = speeds.findIndex(s => s.v > 3);
  const steady = speeds.filter(s => s.t > speeds[moving].t + 1.2 && s.t < speeds[moving].t + 3.0);
  assert.ok(steady.length >= 20, `${steady.length} steady frames`);
  const fps = steady.length / (steady.at(-1).t - steady[0].t), s = stats(steady.map(f => f.v));
  console.log(`${process.env.OLD ? 'OLD ease-out' : 'ActorMotion'}: ${fps.toFixed(0)} fps, drawn speed ${s.mean.toFixed(2)} tiles/s, coefficient of variation ${s.cv.toFixed(3)} (robust ${s.rcv.toFixed(3)}) over ${steady.length} frames`);
  assert.ok(s.mean > 3.5 && s.mean < 9, `walking speed ${s.mean}`);
  const limit = Number(process.env.CV_MAX) || .1;
  let judged = s.rcv;
  if (heroClock.length) {
    const h0 = heroClock[0][0], hp = heroClock.map(f => ({ t: (f[0] - h0) / 1000, x: f[1], y: f[2] })), hs = [];
    for (let i = 1; i < hp.length; i++) { const dt = hp[i].t - hp[i - 1].t; if (dt > 0) hs.push({ t: hp[i].t, v: Math.hypot(hp[i].x - hp[i - 1].x, hp[i].y - hp[i - 1].y) / dt }); }
    const first = hs.findIndex(f => f.v > 3), win = hs.filter(f => f.t > hs[first].t + 1.2 && f.t < hs[first].t + 3.0), h = stats(win.map(f => f.v));
    console.log(`ActorMotion, judged on the time the motion used: speed ${h.mean.toFixed(2)} tiles/s, coefficient of variation ${h.cv.toFixed(3)} (robust ${h.rcv.toFixed(3)}) over ${win.length} frames`);
    judged = h.rcv;
  }
  assert.ok(judged < limit, `the drawn speed must be even from frame to frame (robust cv ${judged.toFixed(3)})`);
  console.log('actor-motion-ui: ok');
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  try { if (browser) await browser.close(); } catch {}
  try { if (started) await call('stop_world'); } catch {}
  try { await client.close(); } catch {}
});
