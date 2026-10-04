// Browser checks for the progression quests (one arrives by itself every five levels and sends the player to the next area):
// how the journal shows a quest that has not arrived yet, the HUD when it arrives, the arrival in the new zone and the
// hand-in at that zone's captain. Rules (granting, reach, rewards, persistence) are in the Rust tests.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-progression-ui', version: '1.0.0' });
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
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('Progress');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites, null, { timeout: 60000 });
  const debug = command => page.evaluate(command => Online.send({ type: 'debug', ref: 1, command }), command);
  const tracker = () => page.locator('#quest-tracker').textContent();
  const journal = async () => { await page.keyboard.press('q'); await page.locator('#quest-journal').waitFor({ state: 'visible' }); };
  const card = id => page.locator(`#quest-list [data-quest="${id}"]`);
  const closeJournal = async () => { await page.keyboard.press('Escape'); await page.locator('#quest-journal').waitFor({ state: 'hidden' }); };
  const ids = ['crags_onward', 'rime_onward', 'fen_onward', 'city_onward'], levels = [5, 10, 15, 20];

  // Before any level: the journal shows none of them, and the catalogue holds each one for its level.
  await journal();
  for (const [i, id] of ids.entries()) {
    check(await card(id).count() === 0, `${id} is not in the journal before it arrives`);
    check(await page.evaluate(([id, level]) => WORLD_MAP.zones.flatMap(z => z.quests || []).find(q => q.id === id).autoLevel === level, [id, levels[i]]), `${id} finds the hero by itself at level ${levels[i]}`);
  }
  check(!(await tracker()).includes('Onward to the Crags'), 'The HUD tracker does not list a quest that has not arrived');
  await closeJournal();

  // Level 5: it arrives on its own, in progress, pointing at the new area.
  await debug({ op: 'set_level', level: 5 });
  await page.waitForFunction(() => document.getElementById('quest-tracker').textContent.includes('Onward to the Crags'), null, { timeout: 10000 });
  check((await tracker()).includes('Travel to the Emberfall Crags: 0/1'), 'The HUD shows the travel objective');
  check(await page.locator('.tracker-quest[data-quest="crags_onward"]').count() === 1 && await page.locator('.tracker-quest[data-quest="rime_onward"]').count() === 0, 'Only the quest for this level arrived');
  await journal();
  let text = await card('crags_onward').textContent();
  check(text.includes('In progress') && text.includes('Captain Sera is in Emberfall Crags'), 'The journal points the player to the new zone and its captain');
  check(await card('rime_onward').count() === 0, 'The next one still waits for level 10');
  await closeJournal();
  const row = await page.locator('#npc-quests .gossip-row[data-quest="crags_onward"]').count();
  check(row === 0, 'Nothing is listed at a giver that the player could accept');

  // Arriving in the zone completes the objective; the captain pays.
  await debug({ op: 'teleport', zone: 1, x: 46, y: 84 });
  await page.waitForFunction(() => Field.zone === 1, null, { timeout: 10000 });
  await page.waitForFunction(() => document.getElementById('quest-tracker').textContent.includes('Report to Captain Sera for your reward'), null, { timeout: 10000 });
  check(await page.locator('.tracker-quest[data-quest="crags_onward"] .tracker-objective.complete').count() === 1, 'Arriving in the Crags completes it in the HUD');
  await journal();
  check(await card('crags_onward').locator('button', { hasText: 'Report to Captain Sera' }).count() === 1, 'The journal offers to take the player to the captain');
  await card('crags_onward').locator('button', { hasText: 'Report to Captain Sera' }).click();
  await page.locator('#npc-dialogue').waitFor({ state: 'visible', timeout: 60000 });
  const done = page.locator('#npc-quests .gossip-row[data-quest="crags_onward"]');
  check(await done.getAttribute('data-status') === 'ready' && await done.locator('.gossip-icon').textContent() === '?', 'The captain lists it as ready to hand in');
  await done.click();
  await page.locator('#npc-quests [data-action="claim"]').click();
  await page.waitForFunction(() => document.getElementById('npc-notice').textContent.includes('Quest complete: Onward to the Crags'), null, { timeout: 10000 });
  await page.locator('#npc-close').click();
  await journal();
  check(await card('crags_onward').count() === 1 && await card('crags_onward').evaluate(n => n.matches('details.quest-completed *')), 'The journal moves it to the completed list');
  await closeJournal();

  // Level 10: the next one arrives, aimed at the glacier.
  await debug({ op: 'set_level', level: 10 });
  await page.waitForFunction(() => document.getElementById('quest-tracker').textContent.includes('Up the Frozen Stair'), null, { timeout: 10000 });
  check((await tracker()).includes('Travel to the Rimeveil Glacier: 0/1'), 'Level 10 sends the player on to the glacier');
  check(errors.length === 0, `No browser runtime errors: ${errors.join('; ')}`);
  console.log(`${checks} progression UI checks passed`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
