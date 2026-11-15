// Real canvas click on a WALKING townsperson (Skaldholm's courier, 2.6 tiles a second) from six tiles away: the hero must
// walk to her and her conversation must open. Reproduces the lookinto.md (slot E round 13) defect: talkTo routes to where
// she stood and pendingNpc only opens the dialogue within 2.5 tiles of her live position.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-walker-talk-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
(async () => {
  const transport = new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe' });
  await client.connect(transport);
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
  if (process.env.MUTATE) { // drop the give-up notice from the served field.js: the notice check must fail
    const fs = require('node:fs'); const src = fs.readFileSync(path.join(root, 'client/field.js'), 'utf8');
    const changed = src.replace("window.Announce?.show('That person is out of reach.','error')", '0');
    assert.notEqual(changed, src, 'mutation target exists');
    await page.route('**/field.js*', r => r.fulfill({ contentType: 'text/javascript', body: changed }));
  }
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('WalkerTalk');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites, null, { timeout: 60000 });
  const debug = command => page.evaluate(command => Online.send({ type: 'debug', ref: 1, command }), command);
  await debug({ op: 'set_time', hour: 12, freeze: true });
  // Skaldholm (zone 4): the hero starts on open city ground and the courier walks wherever she walks.
  // The courier's own spot (the server lands the hero on the nearest free ground there), then wait for her to walk 4-8 tiles off.
  const spot = { x: 71.9, y: 65.0 }; // her spawn in world/map.txt
  await debug({ op: 'teleport', zone: 4, x: spot.x, y: spot.y });
  await page.waitForFunction(() => Field.zone === 4 && City.npcs.some(n => n.id === 'city_courier'), null, { timeout: 30000 });
  await page.waitForFunction(() => { const n = City.npcs.find(n => n.id === 'city_courier'); return Math.hypot(Field.hero.nx - n.x, Field.hero.ny - n.y) < 3; }, null, { timeout: 20000 }).catch(() => {});
  await page.waitForFunction(() => { const n = City.npcs.find(n => n.id === 'city_courier'); const d = Math.hypot(Field.hero.nx - n.x, Field.hero.ny - n.y); return d >= 4 && d <= 8; }, null, { timeout: 20000, polling: 100 }).catch(() => {});
  const courier = () => page.evaluate(() => { const n = City.npcs.find(n => n.id === 'city_courier'); return { x: n.x, y: n.y }; });
  const hero = () => page.evaluate(() => ({ x: Field.hero.nx, y: Field.hero.ny }));
  const c0 = await courier(), h0 = await hero();
  console.log('start courier', c0, 'hero', h0);
  // Click her drawn body, the middle of the band onPointerDown treats as her (between her nameplate top and her feet).
  // Dispatch the press inside the page, in the same tick that reads her position: she walks about 100 px a second, so a
  // Playwright mouse click read a few hundred ms earlier misses her hit band by a few pixels.
  const clicked = await page.evaluate(() => {
    const n = City.npcs.find(n => n.id === 'city_courier');
    const [x, y] = Field._debug.w2s(n.x, n.y), cv = document.getElementById('fieldcv'), r = cv.getBoundingClientRect();
    const clientX = r.left + x / 1600 * r.width, clientY = r.top + (y - City.nameplateTop(n) / 2) / (cv.height * 1600 / cv.width) * r.height;
    cv.dispatchEvent(new PointerEvent('pointerdown', { clientX, clientY, bubbles: true }));
    window.dispatchEvent(new PointerEvent('pointerup', { clientX, clientY, bubbles: true }));
    return { courier: [n.x, n.y], hero: [Field.hero.nx, Field.hero.ny], goal: Field.hero.goal ? [Field.hero.goal.x, Field.hero.goal.y] : null, route: Field._debug.cityRoute.length };
  });
  console.log('clicked', JSON.stringify(clicked));
  // Sample the talk walk every 100 ms until the dialogue opens. An idle hero is one that does not move while the talk is
  // pending (no route left) and she is still more than 2.5 tiles away: the client must then re-route at once.
  const sample = () => page.evaluate(() => { const n = City.npcs.find(n => n.id === 'city_courier'); return { hero: [Field.hero.nx, Field.hero.ny], route: Field._debug.cityRoute.length, npc: [n.x, n.y] }; });
  const trace = [];
  let idle = 0, longestIdle = 0, prev = null;
  for (let t = 0; t < 80; t++) {
    const s0 = await sample();
    const opened = await page.evaluate(() => { const d = document.getElementById('npc-dialogue'); return !!d && !d.hidden && getComputedStyle(d).display !== 'none'; });
    const far = Math.hypot(s0.hero[0] - s0.npc[0], s0.hero[1] - s0.npc[1]) > 2.5;
    const still = prev && Math.hypot(s0.hero[0] - prev.hero[0], s0.hero[1] - prev.hero[1]) < 0.02;
    idle = opened || !far || !still || s0.route > 0 ? 0 : idle + 0.1;
    longestIdle = Math.max(longestIdle, idle);
    if (t % 5 === 0) trace.push({ t: t / 10, hero: s0.hero.map(v => +v.toFixed(1)), route: s0.route, npc: s0.npc.map(v => +v.toFixed(1)) });
    if (opened) break;
    prev = s0;
    await page.waitForTimeout(100);
  }
  const opened = await page.evaluate(() => { const d = document.getElementById('npc-dialogue'); return !!d && !d.hidden && getComputedStyle(d).display !== 'none'; });
  const h1 = await hero(), c1 = await courier();
  console.log('trace', JSON.stringify(trace));
  console.log('after click', JSON.stringify({ opened, longestIdle: +longestIdle.toFixed(1), hero: h1, courier: c1, dist: +Math.hypot(h1.x - c1.x, h1.y - c1.y).toFixed(2) }));
  check(longestIdle < 0.5, `the hero keeps walking to her while the talk is pending (idle ${longestIdle.toFixed(1)} s with no route and her more than 2.5 tiles away)`);
  check(opened, `The conversation with the walking courier opens after a click on her (hero ${h1.x.toFixed(1)},${h1.y.toFixed(1)}; courier ${c1.x.toFixed(1)},${c1.y.toFixed(1)}; ${Math.hypot(h1.x - c1.x, h1.y - c1.y).toFixed(1)} tiles apart)`);
  if (opened) check((await page.locator('#npc-name').textContent()).includes('Courier Fia'), 'the dialogue is the courier\'s');
  // The 20 s give-up: expire a second pending talk at once (debug hook) and read the notice the player sees.
  if (opened) { await page.locator('#npc-dialogue .gossip-row, #npc-quest-close').first().waitFor({ state: 'attached', timeout: 5000 }).catch(() => {}); await page.keyboard.press('Escape').catch(() => {}); }
  await page.waitForTimeout(300);
  await debug({ op: 'teleport', zone: 4, x: spot.x, y: spot.y });
  await page.waitForTimeout(800);
  const far = await page.evaluate(() => { const n = City.npcs.find(n => n.id === 'city_courier'); const [x, y] = Field._debug.w2s(n.x, n.y), cv = document.getElementById('fieldcv'), r = cv.getBoundingClientRect(); return Math.hypot(Field.hero.nx - n.x, Field.hero.ny - n.y) > 2.5; });
  let pending = false;
  if (far) pending = await page.evaluate(() => {
    const n = City.npcs.find(n => n.id === 'city_courier');
    const [x, y] = Field._debug.w2s(n.x, n.y), cv = document.getElementById('fieldcv'), r = cv.getBoundingClientRect();
    const clientX = r.left + x / 1600 * r.width, clientY = r.top + (y - City.nameplateTop(n) / 2) / (cv.height * 1600 / cv.width) * r.height;
    cv.dispatchEvent(new PointerEvent('pointerdown', { clientX, clientY, bubbles: true }));
    window.dispatchEvent(new PointerEvent('pointerup', { clientX, clientY, bubbles: true }));
    return Field._debug.expirePendingNpc();
  });
  check(far && pending, 'a second click on the walking courier leaves a pending talk to expire');
  await page.waitForFunction(() => /out of reach/i.test(document.getElementById('error-messages')?.textContent || ''), null, { timeout: 5000 }).catch(() => {});
  const notice = await page.evaluate(() => document.getElementById('error-messages')?.textContent || '');
  check(/That person is out of reach/.test(notice), 'giving up on a pending talk says so: ' + JSON.stringify(notice));
  check(errors.length === 0, 'no page errors: ' + errors.join(' | '));
  console.log(`walker-talk-ui: ${checks} checks passed`);
})().catch(err => { console.error(err.message); process.exitCode = 1; }).finally(async () => {
  if (browser) await browser.close();
  if (started) await client.close();
});
