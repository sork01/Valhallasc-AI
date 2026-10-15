// Private-browser presentation check. The server-side pickup packet and its effective rarity
// are covered by world::tests::pickup_event_reports_the_awarded_copys_effective_rarity.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-rare-pickup-ui', version: '1.0.0' });
let browser, started = false;
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0' } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('RarePickup'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.hero.x, null, { timeout: 60000 });
  const banner = page.locator('#rare-pickup');
  const event = (actor, rarity) => page.evaluate(({ actor, rarity }) => Field._debug.event({ kind: 'itemPickup', actor: actor === 'self' ? Online.id : actor, x: Field.hero.x, y: Field.hero.y, item: 'warrior_weapon_royal', name: 'Golden Test Sword', quantity: 1, rarity }), { actor, rarity });
  await event('other-player', 'legendary');
  assert.equal(await banner.isHidden(), true, 'another player cannot trigger the banner');
  for (const [rarity, label, color] of [
    ['uncommon', 'green', 'rgb(74, 214, 109)'],
    ['rare', 'blue', 'rgb(100, 181, 255)'],
    ['epic', 'purple', 'rgb(180, 92, 255)'],
    ['legendary', 'orange', 'rgb(255, 154, 46)'],
  ]) {
    await event('self', rarity);
    assert.equal(await banner.getAttribute('data-rarity'), rarity);
    assert.match(await banner.textContent(), new RegExp(`You picked up a ${label} item!`));
    assert.match(await banner.textContent(), /Golden Test Sword/);
    assert.equal(await banner.evaluate(n => getComputedStyle(n).borderTopColor), color);
    assert.equal(await banner.isVisible(), true);
  }
  const shown = await banner.textContent();
  await event('other-player', 'uncommon');
  assert.equal(await banner.textContent(), shown, 'someone else cannot replace the recipient’s banner');
  await page.screenshot({ path: path.join(world.artifacts, 'rare-pickup-orange.png') });
  assert.deepEqual(errors, []);
  console.log('rare-pickup-ui: four rarities and recipient filtering passed');
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
});
