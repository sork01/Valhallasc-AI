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
  // MUTATE=giver serves the journal without its giver line: the run must fail.
  if (process.env.MUTATE === 'giver') await page.route('**/quests.js', async r => { const res = await r.fetch(); await r.fulfill({ response: res, body: (await res.text()).replace('`Quest giver: ${', '`Giver: ${') }); });
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('Progress');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites, null, { timeout: 60000 });
  const debug = command => page.evaluate(command => Online.send({ type: 'debug', ref: 1, command }), command);
  // A new hero starts on the Saltby landing dock, and progression quests only arrive once the hero has stepped ashore.
  await debug({ op: 'teleport', zone: 0, x: 250, y: 235 });
  await page.waitForFunction(() => Math.hypot(Field.hero.nx - 250, Field.hero.ny - 235) < 2, null, { timeout: 20000 });
  await page.evaluate(() => { Field.clearInput(); Online.send({ type: 'stop' }); });
  const tracker = () => page.locator('#quest-tracker').textContent();
  const journal = async () => { await page.keyboard.press('q'); await page.locator('#quest-journal').waitFor({ state: 'visible' }); for (const row of await page.locator('#quest-list > .quest-entry').all()) { await row.locator(':scope > summary').click(); await row.locator('.quest-state').waitFor({state:'visible'}); } };
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
  check(await card('rime_onward').count() === 0, 'The next one still waits for level 10');
  await card('crags_onward').click();
  const text = await page.locator('#quest-page article.journal-detail[data-quest="crags_onward"]').textContent();
  check(text.includes('In progress') && text.includes('Quest giver: Captain Sera · Emberfall Crags'), `The journal points the player to the new zone and its captain: ${JSON.stringify(text)}`);
  await closeJournal();
  const row = await page.locator('#npc-quest-list .journal-quest[data-quest="crags_onward"]').count();
  check(row === 0, 'Nothing is listed at a giver that the player could accept');

  // Arriving in the zone completes the objective; the captain pays.
  await debug({ op: 'teleport', zone: 1, x: 46, y: 84 });
  await page.waitForFunction(() => Field.zone === 1, null, { timeout: 10000 });
  await page.waitForFunction(() => document.querySelector('.tracker-quest[data-quest="crags_onward"] .tracker-destination')?.textContent.includes('Hand in: Captain Sera · Emberfall Crags'), null, { timeout: 10000 });
  check(await page.locator('.tracker-quest[data-quest="crags_onward"] .tracker-objective.complete').count() === 1, 'Arriving in the Crags completes it in the HUD');
  await journal();
  await card('crags_onward').click();
  const ready = await page.locator('#quest-page article.journal-detail[data-quest="crags_onward"]').textContent();
  check(ready.includes('Ready to turn in') && ready.includes('Hand in: Captain Sera · Emberfall Crags'), `The journal names the captain to hand it in to: ${JSON.stringify(ready)}`);
  await closeJournal();
  // The captain stands far off in the Crags and a long walk to him did not reach the dialogue in time; stand beside him first.
  const captain = await page.evaluate(() => { const c = City.npcs.find(n => n.id === 'crags_captain'); return { x: c.x, y: c.y }; });
  await debug({ op: 'teleport', zone: 1, x: captain.x, y: captain.y });
  await page.waitForFunction(c => Math.hypot(Field.hero.nx - c.x, Field.hero.ny - c.y) < 6, captain, { timeout: 15000 });
  await page.locator('.tracker-quest[data-quest="crags_onward"] .tracker-destination').click();
  await page.locator('#npc-dialogue').waitFor({ state: 'visible', timeout: 60000 });
  const done = page.locator('#npc-quest-list .journal-quest[data-quest="crags_onward"]');
  check(await done.getAttribute('data-status') === 'ready' && await done.locator('.journal-quest-mark').textContent() === '?', 'The captain lists it as ready to hand in');
  await done.click();
  await page.locator('#npc-dialogue [data-action="claim"]').click();
  await page.waitForFunction(() => document.getElementById('npc-notice').textContent.includes('Quest complete: Onward to the Crags'), null, { timeout: 10000 });
  await page.locator('#npc-x').click();
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
