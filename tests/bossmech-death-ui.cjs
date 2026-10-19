// BOSSMECH-DEATH on the screen, in a real browser against a real private server: a hero who falls while a boss fight runs lies
// where they fell, the defeat screen says to wait for the fight (not "you wake up back at the start"), the body does not fade
// away, and once the boss is dead the usual three seconds start and the hero wakes at the start with the normal line again.
// The fight is a fixture: a table of its own (VALHALLA_BOSSMECH_FILE) gives the green slime a mechanic that never fires, and a
// second hero (a bot in god mode would be global, so it is simply out of reach) keeps the boss fighting.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const release = path.join(root, 'target/release/valhalla-server');
const debugBin = path.join(root, 'target/debug/valhalla-server');
const newest = [release, debugBin].filter(f => fs.existsSync(f)).sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs)[0];
const binary = process.env.VALHALLA_BINARY || newest;
const dir = fs.mkdtempSync(path.join(root, 'test-results', 'bossmech-death-'));
const table = path.join(dir, 'boss-mechanics.txt');
fs.writeFileSync(table, JSON.stringify({
  green: { mechanics: [{ name: 'Test Toll', block: 'zone', shape: { kind: 'circle', r: 6 }, effect: 'kill', cast: 5, every: 3000, first: 3000 }] },
}));
const client = new Client({ name: 'valhallasc-bossmech-death-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe',
    env: { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0', VALHALLA_BOSSMECH_FILE: table, ...(binary ? { VALHALLA_BINARY: binary } : {}) } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('Watcher'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.hero.x, null, { timeout: 60000 });
  const debug = command => page.evaluate(command => { Online.send({ type: 'debug', ref: Math.floor(Math.random() * 1e9), command }); }, command).then(() => page.waitForTimeout(300));
  const hero = () => page.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y }));
  const text = id => page.evaluate(id => { const el = document.getElementById(id); return { hidden: el.hidden, shown: getComputedStyle(el).display !== 'none', text: el.textContent }; }, id);

  // a second hero who stays alive: a bot beside the first, strong enough to outlast the boss for the length of the test
  await call('connect_bot', { bot: 'Anchor', class: 'warrior' });
  await call('set_level', { bot: 'Anchor', level: 99 });
  const h = await hero();
  await call('teleport', { bot: 'Anchor', to: { x: h.x + 1, y: h.y + 1 } });
  await debug({ op: 'set_god_mode', enabled: true });

  // ---- 1. a boss fight starts, then the hero falls: the line says to wait ------------------------------------------------------
  await debug({ op: 'spawn_enemy', kind: 'green', x: h.x + 3, y: h.y, level: 1 });
  await page.waitForFunction(() => BossMech.active, null, { timeout: 15000 });
  const boss = await page.evaluate(() => BossMech.fights[0].boss);
  await debug({ op: 'die' });
  await page.waitForFunction(() => Field.hero.dead, null, { timeout: 5000 });
  await page.waitForFunction(() => Field.hero.fallen === true, null, { timeout: 5000 });
  const wait = await text('dead-wait'), sub = await text('dead-sub');
  check(wait.shown && wait.text === 'You have fallen. Wait for the fight to end.', `the defeat screen says to wait for the fight (${wait.text})`);
  check(!sub.shown, 'the line promising to wake at the start is hidden while the fight runs');
  await page.screenshot({ path: path.join(world.artifacts, 'bossmech-death-fallen.png') });

  // ---- 2. five seconds on, still down, and the body has not faded away ------------------------------------------------------
  await page.waitForTimeout(5000);
  check(await page.evaluate(() => Field.hero.dead && Field.hero.fallen && Field.hero.deadT > 4), 'five seconds later the hero is still down');
  check(await page.evaluate(() => BossMech.active), 'the fight is still running');
  const where = await hero();
  check(Math.hypot(where.x - h.x, where.y - h.y) < 6, 'the hero lies where they fell, not at the start');
  // the body is drawn at full strength, not faded out as an ordinary body is after three seconds
  check(await page.evaluate(() => { const c = document.getElementById('fieldcv'), g = c.getContext('2d'), [sx, sy] = Field._debug.w2s(Field.hero.x, Field.hero.y), k = c.width / 1600; const d = g.getImageData(Math.round((sx - 12) * k), Math.round((sy - 18) * k), Math.round(24 * k), Math.round(18 * k)).data; let sum = 0; for (let i = 0; i < d.length; i += 4) sum += d[i] + d[i + 1] + d[i + 2]; return sum > 0; }), 'something is drawn where the hero lies');
  await page.screenshot({ path: path.join(world.artifacts, 'bossmech-death-lying.png') });

  // ---- 3. the boss dies: three seconds later the hero wakes and the normal line is back ---------------------------------------------
  await call('kill_enemies', { bot: 'Anchor', ids: [boss] });
  await page.waitForFunction(() => !BossMech.active, null, { timeout: 8000 });
  const still = await page.evaluate(() => Field.hero.dead);
  check(still, 'the kill does not wake the hero at once: the usual three seconds start now');
  const normal = await text('dead-sub'), waiting = await text('dead-wait');
  check(normal.shown && !waiting.shown, 'the defeat screen goes back to its normal line once the fight is over');
  await page.waitForFunction(() => !Field.hero.dead, null, { timeout: 8000 });
  check(await page.evaluate(() => document.getElementById('dead-msg').hidden), 'the defeat screen closes when the hero wakes');

  // ---- 4. a death with no fight is as before ------------------------------------------------------------------------------------
  await debug({ op: 'die' });
  await page.waitForFunction(() => Field.hero.dead, null, { timeout: 5000 });
  check(!(await text('dead-sub')).hidden && (await text('dead-wait')).hidden, 'no fight: the normal line');
  check(await page.evaluate(() => !Field.hero.fallen), 'no fight: not held');
  await page.waitForFunction(() => !Field.hero.dead, null, { timeout: 8000 });

  // ---- 5. the new text exists in Swedish, written by hand ----------------------------------------------------------------------------
  const sv = await browser.newPage({ viewport: { width: 1000, height: 700 } });
  await sv.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'sv', sound: false })));
  await sv.goto(world.url);
  check(await sv.evaluate(() => Locale.translate('You have fallen. Wait for the fight to end.')) === 'Du har fallit. Vänta tills striden är över.', 'Swedish exists');

  assert.deepEqual(errors, []);
  console.log(`bossmech-death-ui: ${checks} checks passed`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
});
