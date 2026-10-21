// UI-ANNOUNCE in a real browser: the server's `announce` packet (a treasure chest appearing, through the real debug op) shows as a big line about 25% down
// the stage and is also written to the chat log and the System tab; several lines stack (three at most, newest last), fade out by themselves, never take
// clicks, do not overlap the rare-pickup banner, and the Swedish text is shown with the language set to Swedish.
// Needs a server binary that sends `announce` (bash scripts/cargo.sh build). MUTATE=1 serves an announce.js without the stack cap and must fail.
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-announce', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`); return result.structuredContent;
}
async function enter(world, name, lang) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  page.on('pageerror', e => errors.push(`${name}: ${e.message}`));
  if (process.env.MUTATE) await page.route('**/announce.js*', route => route.fulfill({ contentType: 'text/javascript', body: fs.readFileSync(path.join(root, 'client/announce.js'), 'utf8').replace('MAX = 3', 'MAX = 30') }));
  await page.addInitScript(lang => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang, sound: false })), lang);
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill(name); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.hero.x, null, { timeout: 60000 });
  return page;
}
const errors = [];
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0' } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await enter(world, 'Announcer', 'en');
  const lines = () => page.locator('#announce .announce-line').allInnerTexts();

  // --- a real server announcement: the chest spawn ---
  check((await lines()).length === 0, 'No announcement before anything happens');
  await page.evaluate(() => Online.send({ type: 'debug', ref: 1, command: { op: 'spawn_chest', distance: 1.2 } }));
  await page.waitForFunction(() => document.querySelectorAll('#announce .announce-line').length === 1, null, { timeout: 5000 });
  const first = (await lines())[0];
  check(/A treasure chest has appeared! It will vanish in 3 minutes\./.test(first), `The chest spawn is announced (${first})`);
  check(await page.locator('#announce .announce-line').getAttribute('data-kind') === 'treasure', 'It carries the treasure kind');
  const chat = await page.locator('#chat-log').innerText();
  check((chat.match(/treasure chest has appeared/g) || []).length === 1, 'The same line is in the chat log once');
  await page.locator('#tab-system').click();
  check(/treasure chest has appeared/.test(await page.locator('#system-log').innerText()), 'And on the System tab');
  await page.locator('#tab-chat').click();

  // --- where it sits and that it never takes a click ---
  const geo = await page.evaluate(() => {
    const stage = document.getElementById('stage').getBoundingClientRect(), line = document.querySelector('#announce .announce-line').getBoundingClientRect();
    const hit = document.elementFromPoint(line.left + line.width / 2, line.top + line.height / 2);
    return { top: (line.top - stage.top) / stage.height, centre: (line.left + line.width / 2 - stage.left) / stage.width, readable: line.width > 100 && line.height > 20, pe: getComputedStyle(document.getElementById('announce')).pointerEvents, hitInside: !!hit?.closest('#announce') };
  });
  check(Math.abs(geo.top - .25) < .03, `The line starts about 25% down the stage (${geo.top.toFixed(3)})`);
  check(Math.abs(geo.centre - .5) < .01, `It is centred (${geo.centre.toFixed(3)})`);
  check(geo.readable, 'It has a readable size');
  check(geo.pe === 'none' && !geo.hitInside, 'The box has pointer-events none and a click at its centre reaches what is underneath');

  // --- stacking: three at most, newest last ---
  await page.evaluate(() => { for (const n of ['one', 'two', 'three', 'four']) Announce.show(`Test ${n}`, 'info'); });
  const stacked = await lines();
  check(stacked.length === 3, `Four close together keep three on screen (${stacked.length})`);
  check(stacked[2] === 'Test four' && stacked[0] === 'Test two', `The newest is last and the oldest are dropped (${stacked.join(' | ')})`);

  // --- it does not overlap the rare-pickup banner ---
  await page.evaluate(() => Field._debug.event({ kind: 'itemPickup', actor: Online.id, x: Field.hero.x, y: Field.hero.y, item: 'warrior_weapon_royal', name: 'Golden Test Sword', quantity: 1, rarity: 'rare' }));
  await page.waitForFunction(() => !document.getElementById('rare-pickup').hidden);
  const overlap = await page.evaluate(() => {
    const a = document.getElementById('announce').getBoundingClientRect(), b = document.getElementById('rare-pickup').getBoundingClientRect();
    return Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
  });
  check(overlap <= 0, `The announcement and the rare-pickup banner do not overlap (${overlap.toFixed(1)}px; ${JSON.stringify(await page.evaluate(() => [...document.querySelectorAll("#announce,#rare-pickup,#stage")].map(n => { const r = n.getBoundingClientRect(); return [n.id, Math.round(r.top), Math.round(r.bottom)]; })))})`);

  // --- it fades by itself ---
  await page.waitForFunction(() => document.querySelectorAll('#announce .announce-line').length === 0, null, { timeout: 9000 });
  check(true, 'Every line has faded out and been removed after a few seconds');

  // --- Swedish ---
  const sv = await enter(world, 'Svensken', 'sv');
  await sv.evaluate(() => Announce.show('The treasure chest has vanished.', 'treasure'));
  check(await sv.locator('#announce .announce-line').last().innerText() === 'Skattkistan har försvunnit.', 'With Swedish selected the line is Swedish');
  check(/^En skattkista har dykt upp!/.test(await sv.locator('#announce .announce-line').first().innerText()), 'The chest still standing is announced to the late arrival, in Swedish');
  assert.deepEqual(errors, []);
  console.log(`announce-ui: ${checks} checks passed`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
});
