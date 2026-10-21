// A real client takes an arena trial: the giver's offer, the banner and its countdown, the opponent appearing and being
// targeted, forfeiting, and handing the won quest in. Needs VALHALLA_BINARY (a build with the gauntlet) and
// PLAYWRIGHT_BROWSERS_PATH with chromium-headless-shell.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-gauntlet-ui', version: '1.0.0' });
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
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('Gauntlet'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'set_level', level: 20 } }));
  await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 4, x: 80, y: 25 } }));
  await page.waitForFunction(() => Field.hero.zone === 4 && Math.hypot(Field.hero.x - 80, Field.hero.y - 25) < 3);
  await page.evaluate(() => Field.visitNpc('city_steward'));
  const dialogue = page.locator('#npc-dialogue');
  await dialogue.waitFor({ state: 'visible' });
  // Asking before the quest is taken is refused and the button comes back.
  await dialogue.locator('[data-offer="gauntlet"]').click();
  await page.waitForFunction(() => document.querySelector('#npc-dialogue').textContent.includes('Take one of my arena quests first'));
  check(await dialogue.locator('[data-offer="gauntlet"]').isEnabled(), 'A refusal leaves the Enter the Arena button usable');
  const accept = dialogue.locator('.gossip-row[data-quest="arena_skald_20"]');
  check(await accept.count() === 1, 'The steward lists the level 20 arena trial');
  await accept.click();
  await dialogue.locator('[data-action=accept]').click();
  await page.waitForFunction(() => document.querySelector('#npc-dialogue').textContent.includes('Quest accepted: Arena Trial: Initiate'));
  await page.evaluate(() => Field.visitNpc('city_steward'));
  await dialogue.waitFor({ state: 'visible' });
  await dialogue.locator('[data-offer="gauntlet"]').click();
  await page.waitForFunction(() => Field.hero.zone === 40 && Pvp.state.gauntlet?.fight === 1, null, { timeout: 30000 });
  check(await page.locator('#gauntlet-banner').isVisible(), 'The banner shows while the run lasts');
  check(await dialogue.isHidden(), 'The giver\'s dialogue closes when the run starts');
  const title = await page.locator('#gauntlet-title').textContent();
  check(title.includes('Fight 1 of 5'), 'The banner names the fight');
  const first = await page.evaluate(() => Pvp.state.gauntlet.countdown);
  check(first > 0 && first <= 10, 'A countdown runs before the first fight');
  await page.waitForFunction(() => Pvp.state.gauntlet?.opponent, null, { timeout: 30000 });
  const opponent = await page.evaluate(() => Pvp.state.gauntlet.opponent);
  check(opponent.name.startsWith('Arena '), 'The opponent is named after its class');
  await page.waitForFunction(id => Field.remotePlayers.some(p => p.id === id), opponent.id, { timeout: 15000 });
  check(await page.evaluate(id => Pvp.canAttack(id, false), opponent.id), 'The hero may attack the opponent');
  check((await page.locator('#gauntlet-line').textContent()).includes(opponent.name), 'The banner names the opponent');
  // Forfeit: back at the giver, the progress reset, the banner gone.
  await page.locator('#gauntlet-leave').click();
  await page.waitForFunction(() => Field.hero.zone === 4 && !Pvp.state.gauntlet, null, { timeout: 15000 });
  check(await page.locator('#gauntlet-banner').isHidden(), 'The banner goes away when the run ends');
  assert.deepEqual(errors, [], 'No browser errors');
  console.log(`gauntlet-ui: ${checks} checks passed`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close().catch(() => {});
});
