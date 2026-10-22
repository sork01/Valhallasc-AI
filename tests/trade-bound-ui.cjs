// Bound class gear (TRADE-BOUND-GEAR) in two real browsers against a private world: the trade picker greys out a class
// piece with its reason and still offers a material, a hand-built offer of the piece is refused by the server, the
// tooltip says "Bound on pickup", and a roll window (a copy whose hand-off is open for the partner) is offered with
// the time left. The server rules themselves are covered by the Rust tests (`cargo test trade`).
// MUTATE=1 serves a trade.js that ignores the bound rule: the run must fail.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-trade-bound-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (v, label) => { assert.ok(v, label); checks++; };
async function call(name, args = {}) {
  const r = await client.callTool({ name, arguments: args });
  assert.ok(!r.isError, `${name}: ${JSON.stringify(r.content)}`); return r.structuredContent;
}
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...process.env } }));
  const world = await call('start_world', { levelSpread: 0 }); started = true;
  browser = await chromium.launch({ headless: true });
  const errors = [];
  async function player(name) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    page.on('pageerror', e => errors.push(`${name}: ${e.message}`));
    await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {} })));
    if (process.env.MUTATE === '1') {
      const source = fs.readFileSync(path.join(root, 'client/trade.js'), 'utf8').replace("const bound = i =>", "const bound = i => false && ");
      await page.route('**/trade.js', route => route.fulfill({ contentType: 'text/javascript', body: source }));
    }
    await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.locator('#name').fill(name); await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
    return page;
  }
  const alice = await player('BoundAlice'), bob = await player('BoundBob');
  const debug = (page, command) => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);
  const bobId = await bob.evaluate(() => Online.id);
  const piece = 'warrior_weapon_sword_l5_gray';
  const pieceName = await alice.evaluate(id => WORLD_ITEMS.find(i => i.id === id).name, piece);
  await debug(alice, { op: 'give_item', item: piece, quantity: 2 });
  await debug(alice, { op: 'give_item', item: 'slime_gel', quantity: 3 });
  await alice.waitForFunction(id => Field.hero.inventory?.some(s => s.item === id) && Field.hero.inventory.some(s => s.item === 'slime_gel'), piece);

  // Tooltip: bound, and with a window open it names the time left.
  await alice.keyboard.press('i');
  const tip = await alice.evaluate(({ id, partner }) => {
    const button = document.querySelector(`#inventory-list [data-item="${id}"] button`);
    const read = () => { button.dispatchEvent(new Event('pointerenter')); return document.getElementById('item-tooltip').innerText; };
    const plain = read();
    const copies = Field.hero.gearInstances || [];
    Inventory.update(Field.hero.inventory, Field.hero.look, Field.hero.equipment || {}, [], copies.map(g => g.item === id ? { ...g, tradeUntil: Date.now() / 1000 + 6120, tradeWith: [partner] } : g));
    return { plain, windowed: read() };
  }, { id: piece, partner: bobId });
  check(tip.plain.includes('Bound on pickup') && tip.plain.includes('only be sold'), `Tooltip says the piece is bound: ${tip.plain}`);
  check(tip.windowed.includes('tradeable for 1 h 42 min with the party of the roll'), `An open window names the time left: ${tip.windowed}`);
  await alice.keyboard.press('i');

  await alice.keyboard.press('o'); await alice.locator('#social-tab-online').click();
  await alice.waitForFunction(() => [...document.querySelectorAll('#social-body [data-player]')].some(n => n.textContent.includes('BoundBob')));
  await alice.locator('#social-body [data-player]', { hasText: 'BoundBob' }).getByRole('button', { name: 'Trade' }).click();
  await bob.locator('#trade-request').waitFor({ state: 'visible' });
  await bob.locator('#trade-accept').click();
  await alice.waitForFunction(() => Trade.state?.state === 'open');

  const option = id => alice.evaluate(id => { const o = document.querySelector(`#trade-item option[value="${id}"]`); return o && { disabled: o.disabled, title: o.title }; }, id);
  const listed = await option(piece), material = await option('slime_gel');
  check(listed && listed.disabled, 'The picker lists the class piece greyed out');
  check(listed.title.includes('bound to its owner'), 'The greyed piece explains why');
  check(material && !material.disabled, 'A material is still offered');
  check(await alice.locator('#trade-item').inputValue() === 'slime_gel', 'The picker starts on an item that can be offered');

  // A modified client that sends the offer anyway is refused by the server.
  await alice.evaluate(id => Online.send({ type: 'trade', command: { op: 'offer', items: [{ item: id, quantity: 1 }], gold: 0 } }), piece);
  await alice.waitForTimeout(800);
  check(await alice.evaluate(() => Trade.state.mine.items.length) === 0, 'The server does not accept a bound piece in an offer');
  check(await alice.evaluate(() => document.body.innerText.includes('bound to its owner')), 'The refusal names the reason in the chat');

  // With the hand-off window open for Bob, the picker offers the piece with the time left.
  const windowed = await alice.evaluate(({ id, partner }) => {
    const hero = Field.hero, stack = hero.inventory.find(s => s.item === id);
    const copies = Array.from({ length: stack.quantity }, (_, n) => ({ id: 9000 + n, item: id, rarity: 'common', rank: 0, tradeUntil: Date.now() / 1000 + 6120, tradeWith: [partner] }));
    Trade.onSnapshot({ ...hero, gearInstances: copies });
    const o = document.querySelector(`#trade-item option[value="${id}"]`);
    return { disabled: o.disabled, title: o.title, text: o.textContent };
  }, { id: piece, partner: bobId });
  check(!windowed.disabled && windowed.title.startsWith('Tradeable for 1 h') && windowed.title.endsWith('with the party of the roll'), `A rolled copy is offered with its time left: ${JSON.stringify(windowed)}`);
  assert.deepEqual(errors, [], 'No browser errors');
  console.log(`trade-bound-ui: ${checks} checks passed`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close().catch(() => {});
});
