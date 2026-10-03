// Browser checks for the party loot-roll cards: what a start packet shows, which buttons work, what a click sends,
// and how a confirmation, a refusal and a disconnect clean up. The rules (who may roll, who wins, gold and
// round-robin sharing) live in server/src/world/rolls.rs and its Rust tests.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-rolls-ui', version: '1.0.0' });
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
  const world = await call('start_world', { levelSpread: 0 }); started = true;
  browser = await chromium.launch({ headless: true });
  const errors = [];
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('Roller');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero && Field.hero.hp > 0, null, { timeout: 60000 });

  // Capture what the client sends, without touching the socket.
  await page.evaluate(() => { window.sent = []; const real = Online.send.bind(Online); Online.send = m => { if (m.type === 'roll') window.sent.push(m); else real(m); }; });
  const green = await page.evaluate(() => WORLD_ITEMS.find(i => i.rarity === 'uncommon' && i.class === 'mage' && i.kind !== 'material')?.id);
  check(!!green, 'The catalog has a green mage piece');
  check(await page.locator('#loot-rolls').count() === 1 && await page.locator('.roll-card').count() === 0, 'No card shows before a roll');

  await page.evaluate(id => { Rolls.onPacket({ type: 'roll', op: 'start', id: 11, item: id, seconds: 30, need: false }); Rolls.onPacket({ type: 'roll', op: 'start', id: 12, item: id, seconds: 30, need: true }); }, green);
  check(await page.locator('.roll-card').count() === 2, 'Each start packet adds one card');
  const first = page.locator('.roll-card[data-roll="11"]'), second = page.locator('.roll-card[data-roll="12"]');
  check(await first.isVisible() && await first.locator('.roll-name').innerText() === (await page.evaluate(id => WORLD_ITEMS.find(i => i.id === id).name, green)), 'The card names the item');
  check((await first.locator('.roll-name').evaluate(n => getComputedStyle(n).color)) === 'rgb(74, 214, 109)', 'A green piece is named in green');
  check(await first.locator('.roll-need').isDisabled() && await second.locator('.roll-need').isEnabled(), 'Need is only enabled for someone who can use the piece');
  check(/^\d+s$/.test(await first.locator('.roll-time').innerText()), 'The card counts down in seconds');
  check((await first.boundingBox()).width > 150 && (await page.locator('#loot-rolls').boundingBox()).x >= 0, 'The cards sit on screen');

  await second.locator('.roll-greed').click();
  const sent = await page.evaluate(() => window.sent);
  check(sent.length === 1 && sent[0].id === 12 && sent[0].choice === 'greed', 'Greed sends the roll id and choice');
  check(await second.locator('button').evaluateAll(bs => bs.every(b => b.disabled)), 'A vote disables the card until the server answers');
  await page.evaluate(() => Rolls.onPacket({ type: 'roll', op: 'voted', id: 12, choice: 'greed' }));
  check(await page.locator('.roll-card[data-roll="12"]').count() === 0, 'The server confirmation closes the card');

  // A refusal reopens the buttons (Need stays off where it never applied).
  await first.locator('.roll-pass').click();
  await page.evaluate(() => Rolls.reopen());
  check(await first.locator('.roll-greed').isEnabled() && await first.locator('.roll-need').isDisabled(), 'A refused vote leaves the card usable');
  await page.evaluate(() => Rolls.onPacket({ type: 'roll', op: 'end', id: 11 }));
  check(await page.locator('.roll-card').count() === 0, 'The end packet removes the card');

  // Hostile text never becomes markup.
  await page.evaluate(() => Rolls.onPacket({ type: 'roll', op: 'start', id: 13, item: '<img src=x onerror=window.pwned=1>', seconds: 5, need: false }));
  check(await page.locator('.roll-card img').count() === 0 && await page.evaluate(() => !window.pwned), 'An unknown item id is shown as text');
  await page.evaluate(() => Rolls.reset());
  check(await page.locator('.roll-card').count() === 0, 'reset() clears every card');
  assert.deepEqual(errors, [], 'no page errors');
  console.log(`rolls-ui: ${checks} checks passed`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close().catch(() => {});
});
