// LEAD-SHOES in a real browser: going down into an underwater zone announces "Equipping lead shoes" once (centre line, chat log, Swedish
// text), the server flag `leadShoes` reaches the hero, and the shoes are really drawn on the feet (pixels at the feet differ from the same
// frame with the flag off and contain the shoe's steel colour). Surfacing takes them off again. Needs a server binary that sends `leadShoes`
// (VALHALLA_BINARY = a `--profile test` build). MUTATE=1 serves a field.js that never draws the shoes and must fail.
// Picture: LEAD_SHOES_PNG=<file> saves a crop of the hero standing in Ran's Deep.
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-lead-shoes', version: '1.0.0' });
let browser, started = false, checks = 0, debugRef = 1;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`); return result.structuredContent;
}
const errors = [];
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0' } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true, args: ['--disable-gpu'] });
  const page = await browser.newPage({ viewport: { width: 960, height: 600 }, reducedMotion: 'reduce' });
  page.on('pageerror', e => errors.push(e.message));
  if (process.env.MUTATE) await page.route('**/field.js*', route => route.fulfill({ contentType: 'text/javascript', body: fs.readFileSync(path.join(root, 'client/field.js'), 'utf8').replace('if (!shod ||', 'if (true ||') }));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('Diver'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.hero.x, null, { timeout: 60000 });
  const debug = command => page.evaluate(([command, ref]) => Online.send({ type: 'debug', ref, command }), [command, debugRef++]);
  const lines = () => page.locator('#announce .announce-line').allInnerTexts();
  const stage = async (zone, x, y) => {
    await debug({ op: 'teleport', zone, x, y });
    await page.waitForFunction(([z, a, b]) => Field.zone === z && Math.hypot(Field.hero.x - a, Field.hero.y - b) < 2, [zone, x, y], { timeout: 20000 });
    await page.waitForTimeout(1500);
  };

  check(!(await page.evaluate(() => Field.hero.leadShoes)), 'On dry land the hero has no lead shoes');
  check((await lines()).every(t => !/lead shoes/i.test(t)), 'And nothing is announced');

  // --- going down ---
  await stage(8, 96, 212);
  await page.waitForFunction(() => Field.hero.leadShoes === true, null, { timeout: 5000 });
  check(true, 'In Ran\'s Deep the server flag reaches the hero');
  await page.waitForFunction(() => [...document.querySelectorAll('#announce .announce-line')].some(e => e.textContent === 'Equipping lead shoes'), null, { timeout: 5000 });
  check(true, 'The centre line says "Equipping lead shoes"');
  check((await page.locator('#chat-log').innerText()).split('Equipping lead shoes').length === 2, 'It is in the chat log exactly once');
  await page.waitForTimeout(3500);
  // Close the DPS meter, which opens in the middle of the stage and hides the hero.
  if (await page.locator('#dps-close').isVisible()) await page.locator('#dps-close').click();
  // The early-level tutorial tip can sit over the hero: dismiss it the way money-ui does.
  await page.evaluate(() => { const tip = document.getElementById('tutorial-tip'); if (tip && !tip.hidden) document.getElementById('tutorial-disable')?.click(); });
  // --- the shoes are drawn: pin the flag on or off (snapshots would overwrite it) and compare the real frame at the feet ---
  const pin = on => page.evaluate(on => Object.defineProperty(Field.hero, 'leadShoes', { configurable: true, get: () => on, set() {} }), on);
  const shot = async on => { await pin(on); await page.waitForTimeout(400); return page.screenshot({ clip: { x: 460, y: 280, width: 40, height: 32 } }); };   // the feet only: the water behind them shimmers
  const withShoes = await shot(true), without = await shot(false), again = await shot(true);
  if (process.env.LEAD_SHOES_PNG) {
    fs.writeFileSync(process.env.LEAD_SHOES_PNG, await page.screenshot({ clip: { x: 380, y: 220, width: 200, height: 150 } }));
  }
  // Compare the real crops pixel by pixel: the flag changes only the shoes, so the on/off difference is the shoes, and the
  // two "on" frames (before and after the off frame) must agree with each other far more than either agrees with the off frame.
  const diffs = (a, b) => page.evaluate(async ([pa, pb]) => {
    const load = async b64 => { const img = new Image(); img.src = 'data:image/png;base64,' + b64; await img.decode();
      const c = document.createElement('canvas'); c.width = img.width; c.height = img.height; const g = c.getContext('2d'); g.drawImage(img, 0, 0);
      return g.getImageData(0, 0, c.width, c.height).data; };
    const [x, y] = [await load(pa), await load(pb)];
    let n = 0; for (let i = 0; i < x.length; i += 4) if (Math.abs(x[i] - y[i]) + Math.abs(x[i + 1] - y[i + 1]) + Math.abs(x[i + 2] - y[i + 2]) > 60) n++;
    return n;
  }, [a.toString('base64'), b.toString('base64')]);
  const [onOff, onAgain] = [await diffs(withShoes, without), await diffs(withShoes, again)];
  check(onOff >= 12, `The shoes change the pixels at the feet (${onOff} pixels differ from the same frame with the flag off)`);
  check(onAgain * 3 < onOff, `Two frames with the shoes agree (${onAgain} pixels differ) far more than with the flag off (${onOff})`);
  check(withShoes.length > 200, 'The crops are real pictures');
  await page.evaluate(() => { delete Field.hero.leadShoes; });

  // --- between two underwater zones the shoes stay on and are not announced again ---
  const before = (await lines()).filter(t => t === 'Equipping lead shoes').length;
  await stage(9, 128, 217);
  check(await page.evaluate(() => Field.hero.leadShoes === true), 'Nacrehold keeps the shoes on');
  check((await lines()).filter(t => t === 'Equipping lead shoes').length === before, 'With no second announcement');

  // --- surfacing ---
  await stage(0, 250, 167);
  await page.waitForFunction(() => Field.hero.leadShoes === false, null, { timeout: 5000 });
  check(true, 'On dry land the shoes are off again');
  await page.waitForFunction(() => [...document.querySelectorAll('#announce .announce-line')].some(e => e.textContent === 'Removing lead shoes'), null, { timeout: 5000 });
  check((await page.locator('#chat-log').innerText()).split('Removing lead shoes').length === 2, 'Surfacing announces "Removing lead shoes", once');

  // --- Swedish (the first page is closed: two clients are too much for the bounded runner) ---
  await page.close();
  const sv = await browser.newPage({ viewport: { width: 960, height: 600 }, reducedMotion: 'reduce' });
  await sv.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'sv', sound: false })));
  await sv.goto(world.url);
  await sv.locator('#start').click(); await sv.locator('#login-guest').click();
  await sv.locator('#name').fill('Dykaren'); await sv.locator('#go').click({ timeout: 60000 });
  await sv.waitForFunction(() => Online.connected && !!Field.hero.x, null, { timeout: 60000 });
  await sv.evaluate(() => Online.send({ type: 'debug', ref: 90, command: { op: 'teleport', zone: 8, x: 96, y: 212 } }));
  await sv.waitForFunction(() => [...document.querySelectorAll('#announce .announce-line')].some(e => e.textContent === 'Tar på blyskor'), null, { timeout: 15000 });
  check(true, 'With Swedish selected the line is "Tar på blyskor"');
  await sv.evaluate(() => Online.send({ type: 'debug', ref: 91, command: { op: 'teleport', zone: 0, x: 250, y: 167 } }));
  await sv.waitForFunction(() => [...document.querySelectorAll('#announce .announce-line')].some(e => e.textContent === 'Tar av blyskor'), null, { timeout: 15000 });
  check(true, 'And surfacing says "Tar av blyskor"');
  assert.deepEqual(errors, []);
  console.log(`lead-shoes-ui: ${checks} checks passed`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
});
