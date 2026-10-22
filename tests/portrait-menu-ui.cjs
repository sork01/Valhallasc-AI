// Portrait menu on the target badge (client/portrait-menu.js) and the inspect window (client/inspect.js), in real
// Chromium pages against a private world with adventurers: right-click, keyboard and long-press opening, disabled
// entries that say why, Trade and Duel declined by an adventurer, Inspect showing another player's gear and stats.
// MUTATE=1 serves a portrait-menu.js with the trade-range rule removed: the run must fail.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-portrait-menu-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, label) => { assert.ok(value, label); checks++; };
async function call(name, args = {}) {
  const r = await client.callTool({ name, arguments: args });
  assert.ok(!r.isError, `${name}: ${JSON.stringify(r.content)}`);
  return r.structuredContent;
}
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...process.env, VALHALLA_LEVEL_SPREAD: '0' } }));
  const world = await call('start_world', { levelSpread: 0, ambientPlayers: true }); started = true;
  browser = await chromium.launch({ headless: true });
  const errors = [];
  async function player(name, options = {}) {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce', ...options });
    const page = await context.newPage();
    page.on('pageerror', e => errors.push(`${name}: ${e.message}`));
    await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {} })));
    if (process.env.MUTATE === '1') {
      const source = fs.readFileSync(path.join(root, 'client/portrait-menu.js'), 'utf8').replace('distance(hero, r) > TRADE_RANGE', 'false');
      await page.route('**/portrait-menu.js', route => route.fulfill({ contentType: 'text/javascript', body: source }));
    }
    await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.locator('#name').fill(name); await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
    return page;
  }
  const alice = await player('MenuAlice'), bob = await player('MenuBob');
  const debug = (page, command) => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);
  const bobId = await bob.evaluate(() => Online.id);
  const badge = alice.locator('#hud-target'), menu = alice.locator('#portrait-menu');
  const entry = act => alice.locator(`#portrait-menu [data-act="${act}"]`);
  const target = id => alice.evaluate(id => Field.targetPlayer(id), id);

  // Bob wears a catalogue necklace so Inspect has gear to show.
  const necklace = await bob.evaluate(() => WORLD_ITEMS.filter(i => i.kind === 'necklace' && i.rarity === 'rare' && !i.class).sort((a, b) => a.requiredLevel - b.requiredLevel)[0]);
  assert.ok(necklace, 'a rare necklace exists');
  await debug(bob, { op: 'set_level', level: Math.max(1, necklace.requiredLevel) });
  await debug(bob, { op: 'give_item', item: necklace.id, quantity: 1 });
  await bob.waitForFunction(id => Field.hero.inventory?.some(s => s.item === id), necklace.id);
  await bob.evaluate(id => Online.send({ type: 'equip', slots: { necklace: id } }), necklace.id);
  await bob.waitForFunction(id => Field.hero.equipment?.necklace === id, necklace.id);

  check(await badge.isHidden(), 'No target badge before targeting a player');
  await alice.waitForFunction(id => Field.remotePlayers.some(p => p.id === id), bobId);
  await target(bobId);
  await alice.waitForFunction(() => !document.getElementById('hud-target').hidden);
  check(await badge.getAttribute('tabindex') === '0' && await badge.getAttribute('aria-haspopup') === 'menu', 'A player target makes the badge focusable and marks it as a menu button');
  check(await menu.isHidden(), 'The menu stays closed until asked for');

  // Right-click opens it with the three entries; Escape closes it without opening the world menu.
  await badge.click({ button: 'right' });
  await menu.waitFor({ state: 'visible' });
  check((await menu.locator('[role=menuitem]').allTextContents()).map(t => t.trim().split('\n')[0]).join('|').startsWith('Trade'), 'The menu lists Trade first');
  check(await menu.locator('[role=menuitem]:visible').count() === 3, 'Trade, Duel and Inspect are all there');
  check(await alice.evaluate(() => document.activeElement?.dataset.act) === 'trade', 'Focus lands on the first entry');
  await alice.keyboard.press('ArrowDown');
  check(await alice.evaluate(() => document.activeElement?.dataset.act) === 'duel', 'Arrow keys move through the entries');
  await alice.keyboard.press('Tab'); await alice.keyboard.press('Tab');
  check(await alice.evaluate(() => document.activeElement?.dataset.act) === 'trade', 'Tab wraps inside the menu (focus trap)');
  await alice.keyboard.press('Escape');
  check(await menu.isHidden() && await alice.locator('#pause').isHidden(), 'Escape closes the menu and does not open the world menu');
  check(await alice.evaluate(() => document.activeElement?.id) === 'hud-target', 'Focus returns to the badge');
  // Keyboard: the Menu key and Shift+F10 open it, a click elsewhere closes it.
  await alice.keyboard.press('ContextMenu');
  check(await menu.isVisible(), 'The Menu key opens the menu from the focused badge');
  await alice.keyboard.press('Escape');
  await alice.keyboard.press('Shift+F10');
  check(await menu.isVisible(), 'Shift+F10 opens it too');
  await alice.mouse.click(700, 500);
  check(await menu.isHidden(), 'A click outside closes the menu');
  // Clicking the world also drops the target (the ordinary game rule), so aim at Bob again.
  await alice.waitForFunction(() => document.getElementById('hud-target').hidden);
  await target(bobId);
  await alice.waitForFunction(() => !document.getElementById('hud-target').hidden);

  // Disabled entries say why. Both start at the same spot, so Trade is possible and the reason for Duel depends on the place.
  await badge.click({ button: 'right' });
  const tradeOff = async () => await entry('trade').getAttribute('aria-disabled') === 'true';
  check(!await tradeOff(), 'Trade is enabled next to the other player');
  const duelOff = await entry('duel').getAttribute('aria-disabled') === 'true';
  const duelWhy = (await entry('duel').locator('.pm-reason').textContent()).trim();
  const inCity = await alice.evaluate(() => City.inside(Field.hero.x, Field.hero.y));
  check(duelOff === !!duelWhy && (!inCity || duelWhy.includes('sanctuary')), `Duel is disabled exactly when it states a reason (${duelWhy || 'none'})`);
  check(duelOff ? await entry('duel').getAttribute('title') === duelWhy : true, 'The reason is also the tooltip');
  await alice.keyboard.press('Escape');
  // Move Bob out of trade range (still in the same zone): Trade turns off with its reason, Inspect stays on.
  await debug(bob, { op: 'teleport', zone: 0, x: await alice.evaluate(() => Field.hero.x) + 12, y: await alice.evaluate(() => Field.hero.y) });
  await alice.waitForFunction(id => { const p = Field.remotePlayers.find(p => p.id === id); return p && Math.hypot(p.nx - Field.hero.nx, p.ny - Field.hero.ny) > 6; }, bobId);
  const retargeted = await target(bobId);
  if (!retargeted || await badge.isHidden()) throw new Error('retarget failed: ' + JSON.stringify(await alice.evaluate(id => ({ ok: Field.targetPlayer(id), pvp: Field.hero.pvpTargetId, hidden: document.getElementById('hud-target').hidden, remotes: Field.remotePlayers.map(p => [p.id.slice(0, 6), p.dead, p.nx, p.ny, p.sparkTravel]), hero: [Field.hero.nx, Field.hero.ny] }), bobId)));
  await badge.click({ button: 'right' });
  check(await tradeOff(), 'Trade is disabled out of range');
  check((await entry('trade').locator('.pm-reason').textContent()).includes('four steps'), 'Its reason names the range');
  await entry('trade').click({ force: true });
  check(await alice.locator('#trade-panel').isHidden() && await alice.evaluate(() => Trade.state === null), 'A disabled Trade entry does nothing');
  check(await menu.isVisible(), 'A disabled entry leaves the menu open');

  // Inspect: Bob's gear and stats.
  await entry('inspect').click();
  await alice.locator('#inspect-panel').waitFor({ state: 'visible' });
  check(await menu.isHidden(), 'Choosing Inspect closes the menu');
  await alice.waitForFunction(() => !document.getElementById('inspect-body').hidden, null, { timeout: 10000 });
  check((await alice.locator('#inspect-title').textContent()).includes('MenuBob'), 'The window is titled with the character');
  check((await alice.locator('#inspect-subtitle').textContent()).includes('Level'), 'The subtitle shows level and class');
  const necklaceCard = alice.locator('#inspect-slots [data-slot="necklace"]');
  check((await necklaceCard.textContent()).includes(necklace.name), 'The necklace slot shows the worn piece');
  check(await necklaceCard.getAttribute('data-rarity') === 'rare', 'The slot is coloured by the piece rarity');
  check(await alice.locator('#inspect-slots .equipped-slot').count() === 9, 'All nine slots are listed');
  check(await alice.locator('#inspect-slots [data-slot="headgear"]').getAttribute('data-empty') === 'true', 'An empty slot reads empty');
  await necklaceCard.locator('button').hover();
  check((await alice.locator('#inspect-tip').textContent()).includes(necklace.name), 'Hovering a slot shows its tooltip');
  const bobAttack = await bob.evaluate(() => Number(Field.hero.attack.toFixed(1)));
  const statsText = await alice.locator('#inspect-stats').textContent();
  check(statsText.includes(String(bobAttack)), `The stat sheet carries Bob's attack (${bobAttack})`);
  check(await alice.locator('#inspect-panel').evaluate(n => getComputedStyle(n).zIndex) === '50', 'The window sits above the other modals');
  await alice.screenshot({ path: '/media/raid/valhallasc-data/portrait-inspect.png' });
  const iconBox = await alice.evaluate(() => { const b = document.querySelector('#inspect-slots [data-slot="necklace"] button'); const r = b.getBoundingClientRect(), c = getComputedStyle(b); return { w: r.width, h: r.height, display: c.display, width: c.width, art: b.innerHTML.length > 0 }; });
  check(iconBox.w > 20 && iconBox.h > 20 && iconBox.art, `The slot icons have real size and art ${JSON.stringify(iconBox)}`);
  if (process.env.REAL_SPRITES === '1') {
    await alice.waitForFunction(() => { const c = document.getElementById('inspect-cv'); return [...c.getContext('2d').getImageData(0, 0, c.width, c.height).data].some((v, i) => i % 4 === 3 && v > 0); }, null, { timeout: 20000 });
    checks++;
  }
  // Live refresh: when the character leaves, the window says so.
  await debug(bob, { op: 'teleport', zone: 0, x: 8, y: 8 });
  await debug(alice, { op: 'teleport', zone: 0, x: 180, y: 180 });
  await alice.waitForFunction(() => document.getElementById('inspect-note').textContent.includes('No longer nearby'), null, { timeout: 15000 });
  check(true, 'The window says "No longer nearby" when the target is out of reach');
  await alice.keyboard.press('Escape');
  check(await alice.locator('#inspect-panel').isHidden() && await alice.locator('#pause').isHidden(), 'Escape closes the inspect window only');

  // An adventurer: Trade and Duel go out and come back declined; nothing opens.
  const near = await alice.evaluate(async () => {
    for (let n = 0; n < 200; n++) {
      const bot = Field.remotePlayers.find(p => p.id !== Online.id && !p.dead && !City.inside(p.nx, p.ny));
      if (bot) return { id: bot.id, x: bot.nx, y: bot.ny, name: bot.look.name };
      await new Promise(r => setTimeout(r, 250));
    }
    return null;
  });
  assert.ok(near, 'an adventurer shows up outside the city');
  const stand = async () => {
    const at = await alice.evaluate(id => { const p = Field.remotePlayers.find(p => p.id === id); return p && { x: p.nx, y: p.ny }; }, near.id);
    assert.ok(at, 'the adventurer is still in view');
    await debug(alice, { op: 'teleport', zone: 0, x: at.x + 1, y: at.y });
    await alice.waitForFunction(id => { const p = Field.remotePlayers.find(p => p.id === id); return p && Math.hypot(p.nx - Field.hero.nx, p.ny - Field.hero.ny) < 3; }, near.id, { timeout: 10000 });
    await target(near.id);
  };
  await stand();
  await badge.click({ button: 'right' });
  check(!await tradeOff(), 'Trade is enabled for an adventurer like for a person');
  await entry('trade').click();
  await alice.waitForFunction(() => document.getElementById('chat-log').textContent.includes('declined your trade request'), null, { timeout: 10000 });
  check(await alice.locator('#trade-panel').isHidden() && await alice.evaluate(() => Trade.state === null), 'The adventurer declines the trade and no window opens');
  await stand();
  await badge.click({ button: 'right' });
  if (await entry('duel').getAttribute('aria-disabled') === 'false') {
    await entry('duel').click();
    await alice.waitForFunction(() => document.getElementById('chat-log').textContent.includes('declined your duel'), null, { timeout: 10000 });
    check(await alice.evaluate(() => !Pvp.state.duel && Pvp.state.requests.length === 0), 'The adventurer declines the duel and nothing is queued');
  } else await alice.keyboard.press('Escape');

  // Touch: a long press opens it and the entries reach 44 px.
  const carol = await player('MenuCarol', { viewport: { width: 844, height: 390 }, hasTouch: true, isMobile: true });
  await carol.evaluate(id => Field.remotePlayers.some(p => p.id === id), bobId).catch(() => {});
  const carolSees = await carol.evaluate(() => new Promise(r => { const t = setInterval(() => { const p = Field.remotePlayers.find(p => p.look && p.look.name !== 'MenuCarol'); if (p) { clearInterval(t); r(p.id); } }, 200); }));
  await carol.evaluate(id => Field.targetPlayer(id), carolSees);
  await carol.waitForFunction(() => !document.getElementById('hud-target').hidden);
  await carol.evaluate(() => {
    const b = document.getElementById('hud-target'), r = b.getBoundingClientRect();
    b.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, pointerType: 'touch', clientX: r.x + 5, clientY: r.y + 5 }));
  });
  await carol.waitForTimeout(250);
  check(await carol.locator('#portrait-menu').isHidden(), 'A short touch does not open the menu');
  await carol.waitForTimeout(500);
  check(await carol.locator('#portrait-menu').isVisible(), 'A long press opens the menu');
  const heights = await carol.locator('#portrait-menu [role=menuitem]:visible').evaluateAll(n => n.map(b => b.getBoundingClientRect().height));
  const scale = await carol.evaluate(() => document.querySelector('.hud-tl').getBoundingClientRect().width / document.querySelector('.hud-tl').offsetWidth);
  check(heights.length === 3 && heights.every(h => h >= 44 * scale - 0.5), `Touch entries are at least 44 px tall (${heights.map(h => h.toFixed(1))}, scale ${scale.toFixed(2)})`);
  const box = await carol.locator('#portrait-menu').boundingBox();
  check(box.x >= 0 && box.x + box.width <= 844 && box.y + box.height <= 390, 'The menu fits the 844x390 phone stage');

  assert.deepEqual(errors, [], 'No browser errors');
  console.log(`portrait-menu-ui: ${checks} checks passed`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  try { if (started) await call('stop_world'); } catch (_) {}
  await browser?.close(); await client.close();
});
