// The signs of Elyss, Avariel, the Worldseed, the Stormgate, the Labyrinth, the Crucible, the Memory and the Solstice in a real private client, including their own telegraph diagrams.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const binary = path.join(root, 'target/debug/valhalla-server');
const signs = JSON.parse(fs.readFileSync(path.join(root, 'world/boss-signs.txt'), 'utf8'));
const zones = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8')).zones;
const kinds = ['choirmother', 'coralregent', 'seed_worldseed', 'thunder_heart', 'bloom_heart', 'solar_heart', 'amber_memory', 'solstice_heart'];
const client = new Client({ name: 'valhallasc-eight-signs-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe',
    env: { ...getDefaultEnvironment(), VALHALLA_BINARY: binary, VALHALLA_LEVEL_SPREAD: '0' } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('Signreader'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.hero.x, null, { timeout: 60000 });
  const debug = async command => {
    await page.evaluate(command => Online.send({ type: 'debug', ref: Math.floor(Math.random() * 1e9), command }), command);
    await page.waitForTimeout(350);
  };
  await debug({ op: 'set_god_mode', enabled: true });
  const diagrams = new Set();
  for (const kind of kinds) {
    // Greenmeadow is built separately and occupies server zone zero.
    const zone = zones.findIndex(z => z.final_boss === kind) + 1;
    const sign = signs[kind];
    check(zone > 0, `${kind} has a dungeon`);
    let near = false;
    let last = null;
    for (const [dx, dy] of [[0, 1.2], [1.2, 0], [-1.2, 0], [0, -1.2]]) {
      await debug({ op: 'teleport', zone, x: sign.x + dx, y: sign.y + dy });
      await page.waitForFunction(kind => Field.signs.some(s => s.id === kind), kind, { timeout: 3000 }).catch(() => {});
      last = await page.evaluate(sign => ({ signs: Field.signs.map(s => s.id), zone: Field.zone, x: Field.hero.x, y: Field.hero.y,
        distance: Math.hypot(Field.hero.x - sign.x, Field.hero.y - sign.y) }), sign);
      if (last.signs.includes(kind) && last.distance <= 2.8) { near = true; break; }
    }
    check(near, `${kind} has a readable approach (${JSON.stringify(last)})`);
    await page.keyboard.press('f');
    await page.waitForFunction(() => !document.getElementById('sign-panel').hidden, null, { timeout: 8000 });
    const panel = await page.evaluate(() => {
      const text = id => document.getElementById(id).textContent;
      const red = document.querySelector('#sign-pictures figure svg');
      const r = document.getElementById('sign-panel').getBoundingClientRect();
      return { title: text('sign-title'), what: text('sign-what'), todo: text('sign-todo'), tip: text('sign-tip'), diagram: red?.innerHTML,
        inside: r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight };
    });
    check(panel.title === sign.title && panel.what === sign.what && panel.todo === sign.todo && panel.tip === sign.tip, `${kind} reads the server's words`);
    check(panel.inside && panel.diagram?.length > 100, `${kind} has a visible diagram at desktop size`);
    diagrams.add(panel.diagram);
    await page.screenshot({ path: path.join(world.artifacts, `sign-${kind}-desktop.png`) });
    await page.setViewportSize({ width: 844, height: 390 });
    const phone = await page.evaluate(() => {
      const p = document.getElementById('sign-panel'), r = p.getBoundingClientRect();
      return { inside: r.left >= 0 && r.top >= 0 && r.right <= innerWidth + 1 && r.bottom <= innerHeight + 1,
        readable: parseFloat(getComputedStyle(document.getElementById('sign-what')).fontSize) >= 15,
        scrollable: p.scrollHeight <= p.clientHeight + 1 || getComputedStyle(p).overflowY !== 'hidden' };
    });
    check(phone.inside && phone.readable && phone.scrollable, `${kind} fits 844 x 390`);
    await page.screenshot({ path: path.join(world.artifacts, `sign-${kind}-phone.png`) });
    await page.keyboard.press('Escape');
    await page.setViewportSize({ width: 1440, height: 900 });
  }
  check(diagrams.size === kinds.length, 'every boss has its own diagram');
  const sv = await browser.newPage({ viewport: { width: 1000, height: 700 } });
  await sv.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'sv', sound: false })));
  await sv.goto(world.url);
  const translated = await sv.evaluate(signs => signs.flatMap(s => [s.what, s.todo, s.tip]).map(s => Locale.translate(s)), kinds.map(k => signs[k]));
  check(translated.every((s, i) => s !== kinds.map(k => signs[k]).flatMap(x => [x.what, x.todo, x.tip])[i]), 'all twenty-four lines have hand-written Swedish');
  assert.deepEqual(errors, []);
  console.log(`bossmech-eight-signs-ui: ${checks} checks passed; screenshots in ${world.artifacts}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
});
