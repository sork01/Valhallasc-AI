// Two real browsers and a private server exercise trade requests, offer review, confirmation and cancellation.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-trade-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (v, label) => { assert.ok(v, label); checks++; };
async function call(name, args = {}) {
  const r = await client.callTool({ name, arguments: args });
  assert.ok(!r.isError, `${name}: ${JSON.stringify(r.content)}`); return r.structuredContent;
}
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe' }));
  const world = await call('start_world', { levelSpread: 0 }); started = true;
  browser = await chromium.launch({ headless: true });
  const errors = [];
  async function player(name) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    page.on('pageerror', e => errors.push(`${name}: ${e.message}`));
    await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
    await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.locator('#name').fill(name); await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
    return page;
  }
  const alice = await player('TradeAlice'), bob = await player('TradeBob');
  const debug = (page, command) => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);
  const count = (page, item) => page.evaluate(id => Field.hero.inventory?.find(s => s.item === id)?.quantity || 0, item);
  await debug(alice, { op: 'give_item', item: 'slime_gel', quantity: 3 });
  await debug(alice, { op: 'set_gold', gold: 50 });
  await debug(bob, { op: 'give_item', item: 'blue_gel', quantity: 2 });
  await debug(bob, { op: 'set_gold', gold: 20 });
  await alice.waitForFunction(() => Field.hero.gold === 50 && Field.hero.inventory.some(s => s.item === 'slime_gel'));
  await bob.waitForFunction(() => Field.hero.gold === 20 && Field.hero.inventory.some(s => s.item === 'blue_gel'));
  await alice.keyboard.press('o'); await alice.locator('#social-tab-online').click();
  await alice.waitForFunction(() => [...document.querySelectorAll('#social-body [data-player]')].some(n => n.textContent.includes('TradeBob')));
  await alice.locator('#social-body [data-player]', { hasText: 'TradeBob' }).getByRole('button', { name: 'Trade' }).click();
  await bob.locator('#trade-request').waitFor({ state: 'visible' });
  check(await bob.locator('#trade-request-text').textContent().then(t => t.includes('TradeAlice')), 'The nearby player receives a named trade request');
  await bob.locator('#trade-accept').click();
  await alice.locator('#trade-panel').waitFor({ state: 'visible' });
  await bob.locator('#trade-panel').waitFor({ state: 'visible' });
  await alice.waitForFunction(() => Trade.state?.state === 'open');
  await bob.waitForFunction(() => Trade.state?.state === 'open');
  check(await alice.locator('#trade-offers').isVisible() && await bob.locator('#trade-offers').isVisible(), 'Both players see the trade review');
  check(await alice.locator('#trade-item option[value="warrior_weapon_sword"]').count() === 0, 'Worn starter gear is unavailable to offer');
  await alice.locator('#trade-item').selectOption('slime_gel'); await alice.locator('#trade-quantity').fill('2'); await alice.locator('#trade-set-item').click();
  await alice.locator('#trade-gold').fill('10'); await alice.locator('#trade-set-gold').click();
  await bob.locator('#trade-item').selectOption('blue_gel'); await bob.locator('#trade-quantity').fill('1'); await bob.locator('#trade-set-item').click();
  await bob.locator('#trade-gold').fill('5'); await bob.locator('#trade-set-gold').click();
  try { await alice.waitForFunction(() => Trade.state?.theirs.gold === 5 && Trade.state?.mine.gold === 10, null, { timeout: 10000 }); }
  catch (e) { throw new Error(`Offer did not settle: ${JSON.stringify(await alice.evaluate(() => ({ trade: Trade.state, notice: document.querySelector('#social-notice').textContent, log: document.querySelector('#chat-log').textContent.slice(-300) })))}; ${e.message}`); }
  check(await alice.locator('#trade-theirs').textContent().then(t => t.includes('Blue Slime Gel ×1') && t.includes('5 gold')), 'The other offer shows item and gold before confirmation');
  await alice.locator('#trade-confirm').click();
  await alice.waitForFunction(() => Trade.state?.mine.ready === true);
  check(await count(alice, 'slime_gel') === 3 && await alice.evaluate(() => Field.hero.gold) === 50, 'One confirmation transfers nothing');
  await bob.locator('#trade-gold').fill('6'); await bob.locator('#trade-set-gold').click();
  await alice.waitForFunction(() => Trade.state?.mine.ready === false && Trade.state?.theirs.gold === 6);
  check(await alice.locator('#trade-confirm').isEnabled(), 'Changing an offer clears the earlier confirmation');
  await alice.locator('#trade-confirm').click(); await bob.locator('#trade-confirm').click();
  await alice.waitForFunction(() => Trade.state === null && Field.hero.gold === 46 && Field.hero.inventory.some(s => s.item === 'blue_gel'));
  await bob.waitForFunction(() => Trade.state === null && Field.hero.gold === 24 && Field.hero.inventory.some(s => s.item === 'slime_gel'));
  check(await count(alice, 'slime_gel') === 1 && await count(alice, 'blue_gel') === 1 && await count(bob, 'slime_gel') === 2 && await count(bob, 'blue_gel') === 1, 'Both inventories exchange the exact offered quantities');
  check(await alice.locator('#trade-panel').isHidden() && await bob.locator('#trade-panel').isHidden(), 'Both trade panels close after completion');
  await alice.keyboard.press('o'); await alice.locator('#social-tab-online').click();
  await alice.locator('#social-body [data-player]', { hasText: 'TradeBob' }).getByRole('button', { name: 'Trade' }).click();
  await bob.locator('#trade-request').waitFor({ state: 'visible' }); await bob.locator('#trade-decline').click();
  await alice.waitForFunction(() => Trade.state === null);
  await bob.locator('#trade-request').waitFor({ state: 'hidden' });
  check(await bob.locator('#trade-request').isHidden() && await alice.locator('#trade-panel').isHidden(), 'Declining a new request closes it for both players');
  assert.deepEqual(errors, [], 'No browser errors');
  console.log(`trade-ui: ${checks} checks passed`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close().catch(() => {});
});
