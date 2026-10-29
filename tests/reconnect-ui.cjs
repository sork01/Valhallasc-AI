// Real private server: an abandoned socket still holds the character during reconnect.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { requireMemoryLimit, sleep } = require('./lib/touch.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
requireMemoryLimit();
const world = new TestWorld(); world.startLevel = 17; world.godMode = true;
let browser, checks = 0;
const check = (ok, label) => { assert.ok(ok, label); checks++; };
(async () => {
  await world.start(); browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1024, height: 768 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  if (process.env.RECONNECT_CANDIDATE) for (const file of ['online.js', 'weather.js', 'field.js'])
    await page.route('**/' + file, r => r.fulfill({ path: path.join(process.env.RECONNECT_CANDIDATE, file), contentType: 'text/javascript' }));
  await page.addInitScript(() => {
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false }));
    const Native = WebSocket; window.networkSockets = []; window.holdOldSocket = true;
    window.WebSocket = new Proxy(Native, { construct(Target, args) {
      const socket = new Target(...args), close = socket.close.bind(socket), first = networkSockets.length === 0;
      socket.closeNow = close;
      socket.close = (...args) => { if (!first || !holdOldSocket) close(...args); };
      networkSockets.push(socket); return socket;
    } });
  });
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('ReconnectCheck'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0);
  const before = await page.evaluate(() => ({ id: Online.id, key: Online.currentKey }));
  await page.evaluate(() => networkSockets[0].onclose({ code: 1006 }));
  await page.waitForFunction(() => document.getElementById('connection-text').textContent.includes('previous connection'), null, { timeout: 10000 });
  check(await page.evaluate(() => networkSockets[0].readyState === WebSocket.OPEN), 'the original socket really still holds its server slot');
  check(await page.locator('#connection-retry').isVisible(), 'busy reconnect offers Retry instead of a fatal lockout');
  const health = await (await fetch(world.url + 'health')).json();
  check(health.online === 1, 'server still enforces one active copy of the character');
  await page.evaluate(() => { holdOldSocket = false; networkSockets[0].closeNow(); });
  await page.waitForFunction(() => Online.connected && document.getElementById('connection-overlay').hidden, null, { timeout: 15000 });
  check(await page.evaluate(before => Online.id === before.id && Online.currentKey === before.key, before), 'reconnect resumes the same saved character');
  check(await page.evaluate(() => networkSockets.length >= 3), 'a refused join retries after slot release');
  await page.evaluate(() => networkSockets[0].onclose({ code: 1006 })); await sleep(650);
  check(await page.evaluate(() => Online.connected && document.getElementById('connection-overlay').hidden), 'late old-socket close cannot disconnect the recovered player');
  await page.evaluate(() => {
    window.weatherCameras = []; const draw = Weather.draw;
    Weather.draw = function (...args) { weatherCameras.push(args[4]); return draw.apply(this, args); };
  });
  await page.keyboard.down('w'); await sleep(1000); await page.keyboard.up('w');
  const cameras = await page.evaluate(() => weatherCameras);
  check(cameras.length > 2 && cameras.every(c => c && Number.isFinite(c.x) && Number.isFinite(c.y)), 'the real field renderer passes its camera into weather drawing');
  check(cameras.some(c => Math.hypot(c.x - cameras[0].x, c.y - cameras[0].y) > 1), 'walking changes the weather camera');
  check(errors.length === 0, 'no browser errors: ' + errors.join('; '));
  console.log(`reconnect-ui: ${checks} checks passed; ${world.runDir}`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => { if (browser) await browser.close(); await world.stop(); });
