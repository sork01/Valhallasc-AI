// Two real browsers on a private server cover PvP consent, visible flags and arena entry/exit.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-pvp-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe' }));
  const world = await call('start_world', { levelSpread: 0 }); started = true;
  browser = await chromium.launch({ headless: true });
  const errors = [];
  async function player(name) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    page.on('pageerror', error => errors.push(`${name}: ${error.message}`));
    await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
    await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.locator('#name').fill(name); await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
    await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 0, x: 9, y: 9 } }));
    await page.waitForFunction(() => Math.hypot(Field.hero.x - 9, Field.hero.y - 9) < 2);
    return page;
  }
  const alice = await player('PvPAlice'), bob = await player('PvPBob');
  const aliceId = await alice.evaluate(() => Online.id), bobId = await bob.evaluate(() => Online.id);
  await bob.evaluate(id => Field.targetPlayer(id), aliceId);
  await bob.evaluate(id => Online.send({ type: 'pvp', command: { op: 'attack', id } }), aliceId);
  await bob.waitForFunction(() => document.querySelector('#chat-log').textContent.includes('PvP requires'));
  check(await alice.evaluate(() => Field.hero.hp === Field.hero.maxHp), 'Attacking without consent deals no damage');
  await alice.waitForFunction(() => Pvp.available);
  await alice.keyboard.press('o'); await alice.locator('#social-tab-online').click();
  await alice.waitForFunction(() => [...document.querySelectorAll('#social-body [data-player]')].some(n => n.textContent.includes('PvPBob')));
  await alice.locator('#social-body [data-player]', { hasText: 'PvPBob' }).getByRole('button', { name: 'Duel' }).click();
  await bob.waitForFunction(() => Pvp.state.requests.some(r => r.name === 'PvPAlice'));
  await bob.keyboard.press('o'); await bob.locator('#social-tab-pvp').click();
  check(await bob.locator('#social-body').getByText('PvPAlice challenged you', { exact: false }).isVisible(), 'Challenge is visible with accept and decline');
  await bob.locator('#social-body').getByRole('button', { name: 'Accept' }).click();
  await alice.waitForFunction(() => Pvp.state.duel?.name === 'PvPBob');
  await bob.waitForFunction(() => Pvp.state.duel?.name === 'PvPAlice');
  check(await bob.evaluate(() => Pvp.state.duel?.name === 'PvPAlice'), 'Both players enter the same duel');
  await bob.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 0, x: 45, y: 45 } }));
  await bob.waitForFunction(() => typeof Pvp.state.duel?.returnIn === 'number' && Pvp.state.duel.returnIn <= 10);
  check(await bob.locator('#pvp-duel-warning').isVisible(), 'Leaving the duel ring starts a visible return timer');
  await bob.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 0, x: 9, y: 9 } }));
  await bob.waitForFunction(() => Pvp.state.duel?.returnIn == null);
  check(await bob.locator('#pvp-duel-warning').isHidden(), 'Returning inside the ring clears the timer');
  await alice.locator('#social-body').getByRole('button', { name: 'End duel' }).click();
  await bob.waitForFunction(() => Pvp.state.duel === null);
  await alice.waitForFunction(() => Pvp.state.duel === null);
  check(await alice.evaluate(() => Pvp.state.duel === null), 'Ending a duel clears both states');
  await alice.locator('#social-body').getByRole('button', { name: 'Turn PvP on' }).click();
  await alice.waitForFunction(() => Pvp.state.flag && Field.hero.pvpFlag);
  await bob.waitForFunction(id => Field.remotePlayers.find(p => p.id === id)?.pvpFlag === true, aliceId);
  check(await bob.evaluate(id => Field.remotePlayers.find(p => p.id === id)?.pvpFlag, aliceId), 'PvP flag appears in authoritative player snapshots');
  await alice.locator('#social-body').getByRole('button', { name: 'Turn PvP off' }).click();
  await alice.waitForFunction(() => !Pvp.state.flag);
  await alice.locator('#social-body').getByRole('button', { name: 'Queue 1v1' }).click();
  await alice.waitForFunction(() => Pvp.state.queue === 1);
  await bob.locator('#social-body').getByRole('button', { name: 'Queue 1v1' }).click();
  await alice.waitForFunction(() => Pvp.state.arena?.size === 1 && Field.hero.zone === 40);
  await bob.waitForFunction(() => Pvp.state.arena?.size === 1 && Field.hero.zone === 40);
  check(await alice.evaluate(() => Field.hero.zone === 40 && Field.remotePlayers.some(p => p.id === Online.id) === false), 'Both teams enter the private arena zone');
  await bob.locator('#social-body').getByRole('button', { name: 'Forfeit match' }).click();
  await alice.waitForFunction(() => Pvp.state.arena === null && Field.hero.zone === 0);
  await bob.waitForFunction(() => Pvp.state.arena === null && Field.hero.zone === 0);
  check(await alice.evaluate(() => Field.hero.hp === Field.hero.maxHp), 'Match end restores health and returns players');
  assert.deepEqual(errors, [], 'No browser errors');
  console.log(`pvp-ui: ${checks} checks passed`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close().catch(() => {});
});
