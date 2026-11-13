// Focused stat controls in a private world; Rust world tests cover purchases and persistence.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-stat-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, label) => { assert.ok(value, label); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe' }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => { localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })); });
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-mage').click(); await page.locator('#name').fill('StatMage'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.mageSprites, null, { timeout: 60000 });
  await page.keyboard.press('e');
  check(await page.locator('.attribute-no-points').textContent().then(t => t.includes('Level up')), 'No-points message is visible');
  check(await page.locator('.attribute-recommend').isDisabled(), 'Recommended is disabled with no points');
  await page.evaluate(() => {
    window.statSent = [];
    Online.send = action => { statSent.push(action); return true; };
    const update = Attributes.update.bind(Attributes);
    Attributes.update = () => {}; // The display fixture is isolated from the private world's snapshots.
    window.statFixture = { id: 'display-only', look: { class: 'mage' }, level: 10, attributes: {strength: 0, agility: 0, intellect: 1, stamina: 0, dexterity: 0, accuracy: 0},
      gearAttributes: {intellect: 2, stamina: 1}, passiveAttributes: {}, statPoints: 26, dead: false,
      hitChance: .9, dodgeChance: 0, critChance: .14, attackCooldown: .7 };
    window.updateStats = () => update(statFixture);
    updateStats();
  });
  check((await page.locator('.attribute-recommend').getAttribute('title')).includes('Mage:'), 'Tooltip explains the mage choice');
  const beforeRect = await page.locator('#character-attributes').boundingBox();
  await page.locator('.attribute-recommend').click();
  await page.locator('#recommended-dialog').waitFor({ state: 'visible' });
  const afterRect = await page.locator('#character-attributes').boundingBox();
  check(await page.locator('.attribute-preview').count() === 0 && Math.abs(beforeRect.height - afterRect.height) < 1 && Math.abs(beforeRect.y - afterRect.y) < 1, 'Confirmation popup does not shift or expand the attributes list');
  const centered = await page.evaluate(() => {
    const s = document.getElementById('stage').getBoundingClientRect();
    const d = document.querySelector('#recommended-dialog .recommended-dialog').getBoundingClientRect();
    return Math.abs((d.left + d.width / 2) - (s.left + s.width / 2)) < 4 && Math.abs((d.top + d.height / 2) - (s.top + s.height / 2)) < 4;
  });
  check(centered, 'Confirmation dialog is centered in the stage');
  const preview = await page.locator('#recommended-dialog .recommended-dialog').textContent();
  const sum = [...preview.matchAll(/\+(\d+)/g)].reduce((total, part) => total + Number(part[1]), 0);
  check(preview.includes('Spend 26 points?') && sum === 26, 'Preview accounts for every available point');
  check(await page.evaluate(() => !statSent.some(a => a.type === 'allocate_stat' || a.type === 'allocate_recommended')), 'Opening preview sends no allocation');
  await page.keyboard.press('Escape');
  await page.locator('#recommended-dialog').waitFor({ state: 'hidden' });
  check(await page.locator('#equipment').isVisible(), 'Escape closes the confirmation popup without closing Character');
  await page.locator('.attribute-recommend').click();
  await page.locator('#recommended-dialog').waitFor({ state: 'visible' });
  await page.locator('.attribute-recommend-cancel').click();
  check(await page.locator('#recommended-dialog').isHidden(), 'Preview can be canceled');
  await page.locator('.attribute-recommend').click();
  await page.locator('#recommended-dialog').waitFor({ state: 'visible' });
  const dlgBox = await page.locator('#recommended-dialog').boundingBox();
  await page.mouse.click(dlgBox.x + 8, dlgBox.y + 8);
  await page.locator('#recommended-dialog').waitFor({ state: 'hidden' });
  check(await page.locator('#equipment').isVisible(), 'Clicking outside the popup card closes only the confirmation popup');
  await page.locator('.attribute-recommend').click();
  await page.locator('.attribute-recommend-confirm').click();
  check(await page.locator('#recommended-dialog').isHidden(), 'Confirming closes the confirmation popup');
  check(await page.evaluate(() => statSent.filter(a => a.type === 'allocate_recommended').length === 1), 'Confirmation sends one server allocation request');
  check(await page.locator('.attribute-recommend').isDisabled(), 'Button stays disabled while pending');
  await page.evaluate(() => updateStats());
  check(await page.locator('.attribute-recommend').isDisabled(), 'An unchanged snapshot cannot clear a pending request');
  await page.evaluate(() => Attributes.error());
  check(await page.locator('.attribute-recommend').isEnabled(), 'A server error releases the pending state');
  await page.evaluate(() => { statFixture.statPoints = 0; updateStats(); });
  check(await page.locator('.attribute-no-points').count() === 1 && await page.locator('#recommended-dialog').isHidden(), 'Authoritative no-points state closes preview');
  await page.evaluate(() => { statFixture.statPoints = 1; updateStats(); });
  await page.locator('[data-stat="stamina"] .attribute-add').click();
  check(await page.evaluate(() => statSent.some(a => a.type === 'allocate_stat' && a.stat === 'stamina')), 'Manual training remains available');
  await page.evaluate(() => {
    statSent.length = 0;
    City.dialogue({npc: City.npcs.find(n => n.id === 'guide'), notice: '', gold: 200000, level: 50,
      statPoints: 135, trainedPoints: 12, statResetPrice: 130000, statResets: 0,
      attributes: {strength: 12}, inventory: [], equipment: {}, bags: [], quests: [], look: {class: 'mage', name: 'Tester'}});
    statSent.length = 0;
  });
  await page.locator('#npc-offers [data-view="stat_reset"]').click();
  check(await page.locator('#npc-offers').textContent().then(t => t.includes('130,000 gold') && t.includes('12 trained points') && t.includes('cannot be undone')), 'Reset view shows price, refund and warning');
  check(await page.evaluate(() => !statSent.some(a => a.type === 'interact' && a.offer === 'stat_reset')), 'Opening reset view sends no purchase');
  await page.locator('#npc-offers [data-offer="stat_reset"]').click();
  check(await page.evaluate(() => statSent.filter(a => a.type === 'interact' && a.offer === 'stat_reset' && a.npc === 'guide').length === 1), 'Separate confirmation sends the NPC offer');
  await page.evaluate(() => { window.statPlayersSeen = []; Attributes.update = c => { statPlayersSeen.push(c); };
    City.dialogue({npc: City.npcs.find(n => n.id === 'guide'), notice: 'Stats reset: 12 points refunded.', gold: 70000, level: 50,
      statPoints: 147, trainedPoints: 0, statResetPrice: 260000, statResets: 1,
      statPlayer: {id:'display-only', statPoints:147, attributes:{}},
      attributes: {}, inventory: [], equipment: {}, bags: [], quests: [], look: {class: 'mage', name: 'Tester'}}); });
  check(await page.locator('#npc-offers').textContent().then(t => t.includes('260,000 gold') && t.includes('147 unspent points')) && await page.locator('#npc-offers [data-offer="stat_reset"]').isDisabled(), 'Reply immediately shows rising price and refunded pool');
  // Live snapshots of the private world also reach the hook, so look for the reply's own player among every call.
  check(await page.evaluate(() => statPlayersSeen.some(c => c.id === 'display-only' && c.statPoints === 147)), 'Reset reply immediately refreshes the attribute panel');
  check(errors.length === 0, `No browser errors: ${errors.join('; ')}`);
  console.log(`${checks} stat UI checks passed`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
});
