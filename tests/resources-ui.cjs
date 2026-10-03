// Real server snapshots and browser controls; debug commands only stage resource/item prerequisites.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-resources-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (ok, message) => { assert.ok(ok, message); checks++; };
async function call(name, args = {}) {
  const r = await client.callTool({ name, arguments: args });
  assert.ok(!r.isError, `${name}: ${JSON.stringify(r.content)}`); return r.structuredContent;
}
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment() } }));
  const world = await call('start_world', { startLevel: 20, levelSpread: 0 }); started = true;
  browser = await chromium.launch({ headless: true });
  const errors = [];
  const pages = {};
  for (const cls of ['warrior', 'assassin', 'hunter', 'mage', 'priest']) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' }); pages[cls] = page;
    page.on('pageerror', e => errors.push(e.message));
    await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
    await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.locator(`#cls-${cls}`).click(); await page.locator('#name').fill(`Resource ${cls}`); await page.locator('#go').click();
    await page.waitForFunction(() => Online.connected && Field.hero.level === 20 && document.querySelector('#resource-text').textContent.includes('/'), null, { timeout: 60000 });
    const kind = cls === 'warrior' ? 'rage' : ['assassin', 'hunter'].includes(cls) ? 'energy' : 'mana';
    check(await page.locator('#resource-bar').getAttribute('data-type') === kind, `${cls} HUD uses ${kind}`);
    const state = await page.evaluate(() => ({ resource: Field.hero.resource, max: Field.hero.maxResource, text: document.querySelector('#resource-text').textContent, label: document.querySelector('#resource-bar').getAttribute('aria-label') }));
    check(state.resource === (cls === 'warrior' ? 0 : state.max) && state.text.includes(`${Math.floor(state.resource)} / ${state.max}`), `${cls} HUD displays the server's amount and capacity`);
    check(state.label.toLowerCase() === kind, `${cls} resource has an accessible name`);
    check(await page.locator('#quickuse [data-kind="mana"]').isVisible() === (kind === 'mana'), `${cls} shows the mana shortcut only when applicable`);
    const colors = await page.locator('#resource-fill').evaluate(n => getComputedStyle(n).backgroundImage);
    check(colors.includes('linear-gradient'), `${cls} resource is visibly coloured`);
    await page.keyboard.press('k');
    const skill = await page.locator('#skill-library .skill-card').nth(cls === 'assassin' ? 2 : 1).textContent();
    check(skill.toLowerCase().includes(kind), `${cls} skill library displays resource cost`);
    await page.keyboard.press('k');
  }
  const mage = pages.mage;
  const debug = (page, command) => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);
  await mage.keyboard.press('2');
  await mage.waitForFunction(() => Field.hero.skillCd?.twinbolt > 0);
  check(await mage.evaluate(() => Math.abs(Field.hero.resource - (Field.hero.maxResource - WORLD_SKILLS.find(s => s.id === "twinbolt").cost)) < 15), 'Keyboard skill spends mana and the HUD follows its snapshot');
  await debug(mage, { op: 'set_resource', amount: 0 });
  await mage.waitForFunction(() => Field.hero.resource < 15 && document.querySelector('#skillbar-slots [data-skill="starfall"]').disabled);
  check(await mage.locator('#skillbar-slots [data-skill="starfall"]').getAttribute('class').then(c => c.includes('resource-empty')), 'Insufficient mana visibly disables a ready skill');
  await mage.waitForFunction(() => !document.querySelector('#skillbar-slots [data-skill="attack"]').disabled, null, { timeout: 5000 });   // its own short cooldown may still be running
  check(await mage.locator('#skillbar-slots [data-skill="attack"]').isEnabled(), 'Basic attack remains usable at zero mana');
  await mage.keyboard.press('-');
  check(await mage.evaluate(() => !Field.hero.skillCd?.starfall), 'Exhausted skill key does not start a cooldown');
  await debug(mage, { op: 'give_item', item: 'mana_potion', quantity: 2 });
  await debug(mage, { op: 'give_item', item: 'health_potion', quantity: 1 });
  await mage.waitForFunction(() => Inventory.quantity('mana_potion') === 2);
  const manaSlot = mage.locator('#quickuse [data-kind="mana"]');
  check(await manaSlot.getAttribute('title').then(t => t.includes('100 mana') && t.includes('C')), 'Mana slot explains its recovery and key');
  await mage.keyboard.press('c');
  await mage.waitForFunction(() => Field.hero.potionCd > 0);
  check(await mage.evaluate(() => Math.abs(Field.hero.resource - 100) < 15 && Inventory.quantity('mana_potion') === 1 && Field.hero.hp === Field.hero.maxHp), 'C drinks a mana potion at full health');
  check(await manaSlot.isDisabled() && await mage.locator('#quickuse [data-kind="potion"]').isDisabled(), 'Health and mana quick slots show the same potion cooldown');
  await debug(mage, { op: 'give_item', item: 'traveler_stew', quantity: 1 });
  await mage.waitForFunction(() => Inventory.quantity('traveler_stew') === 1);
  await mage.keyboard.press('z');
  await mage.waitForFunction(() => Field.hero.buffs.some(b => b.kind === 'regen'));
  check(await mage.evaluate(() => Field.hero.hp === Field.hero.maxHp && Inventory.quantity('traveler_stew') === 0), 'Food is usable to restore mana at full health');
  await mage.keyboard.press('i');
  // Tooltips are also accessible through the quick slot; check the bag's catalog description directly.
  check(await mage.evaluate(() => Inventory.effect(WORLD_ITEMS.find(i => i.id === 'mana_potion')).includes('100 mana')), 'Bag description names mana recovery');
  await mage.keyboard.press('i');
  await mage.screenshot({ path: path.join(world.artifacts, 'resources-mana.png') });
  await pages.warrior.screenshot({ path: path.join(world.artifacts, 'resources-rage.png') });
  await pages.assassin.screenshot({ path: path.join(world.artifacts, 'resources-energy.png') });
  await mage.setViewportSize({ width: 800, height: 450 });
  const boxes = await mage.locator('#resource-bar, #quickuse').evaluateAll(nodes => nodes.map(n => { const r = n.getBoundingClientRect(); return { x: r.x, y: r.y, right: r.right, bottom: r.bottom }; }));
  check(boxes.every(r => r.x >= 0 && r.y >= 0 && r.right <= 800 && r.bottom <= 450), 'Resource HUD and three quick slots fit a phone landscape viewport');
  check(errors.length === 0, 'No browser JavaScript errors');
  console.log(JSON.stringify({ passed: true, checks, artifacts: world.artifacts }, null, 2));
})().catch(e => { console.error(e.stack || e); process.exitCode = 1; }).finally(async () => { await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close().catch(() => {}); });
