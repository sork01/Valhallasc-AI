// Real browser actions cover starter ownership, combat pickup, inventory controls,
// vendor sales and reload. Separate display fixtures cover rare gear and markers.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium, STUB } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-inventory-ui', version: '1.0.0' });
let browser, page, started = false, checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`); return result.structuredContent;
}
(async () => {
  // This suite checks the bag UI around one real kill, not combat difficulty: pin every enemy to its default level.
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0' } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => { if(!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })); });
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-mage').click(); await page.locator('#name').fill('InventoryUI');
  check(await page.locator('#create-mageWeapon option').count() === 1, 'Character creation offers starter gear');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.mageSprites, null, { timeout: 60000 });
  check(await page.evaluate(() => Field._debug.routeTo(WORLD_MAP.npcs.find(n => n.id === 'merchant'), true, {x:39.30887275762825,y:59.41608127806563}).length > 0), 'Town travel routes from a loot position beside a tree');
  await page.keyboard.press('e');
  check(await page.locator('#equipment').isVisible(), 'E opens character and bags');
  check(await page.locator('#inventory-list .inventory-item').count() === 3 && await page.locator('#inventory-list .bag-cell').count() === 16, 'Equipped starter gear leaves sixteen backpack cells holding only the three unworn starter pieces');
  check(await page.locator('#field-mageWeapon option').count() === 2, 'Equipment selector offers only none and owned gear');
  // Equipment icons: every piece of gear has its own pixel icon (assets/items.png), no two alike, and the bag/gear slots draw them.
  const icons = await page.evaluate(async () => {
    const at0 = ITEM_ICONS.at;
    const all = WORLD_ITEMS.filter(i => !['material', 'bag', 'food', 'potion'].includes(i.kind));
    // Original pieces have their own icon; a recolouring (art + tint) has none and shows its base piece through a colour filter.
    const gear = all.filter(i => !i.art), recoloured = all.filter(i => i.art);
    const badRecolour = recoloured.filter(i => !i.tint || !WORLD_ITEMS.some(o => o.kind === i.kind && o.class === i.class && o.variant === i.art && at0[o.id])).map(i => i.id);
    const img = new Image(); img.src = 'assets/items.png'; await img.decode();
    const c = document.createElement('canvas'); c.width = img.width; c.height = img.height; const g = c.getContext('2d', { willReadFrequently: true }); g.drawImage(img, 0, 0);
    const { size, at } = ITEM_ICONS, seen = new Map(), missing = [], blank = [];
    for (const i of gear) {
      const cell = at[i.id]; if (!cell) { missing.push(i.id); continue; }
      const px = g.getImageData(cell[0] * size, cell[1] * size, size, size).data;
      let opaque = 0; for (let k = 3; k < px.length; k += 4) opaque += px[k] > 0;
      if (opaque < 150) blank.push(i.id);
      const key = Array.from(px).join(','); seen.set(key, (seen.get(key) || []).concat(i.id));
    }
    return { gear: gear.length, recoloured: recoloured.length, badRecolour, missing, blank, twins: [...seen.values()].filter(v => v.length > 1) };
  });
  check(icons.gear >= 50 && icons.missing.length === 0, `Every original equipment item has an icon (missing: ${icons.missing})`);
  check(icons.recoloured >= 400 && icons.badRecolour.length === 0, `Every recoloured piece has a tint and a base piece with an icon (${icons.recoloured} pieces; bad: ${icons.badRecolour.slice(0, 5)})`);
  check(icons.blank.length === 0 && icons.twins.length === 0, `No icon is blank or a copy of another (blank ${icons.blank}; twins ${JSON.stringify(icons.twins)})`);
  check(await page.locator('#inventory-list [data-item="mage_headgear_apprentice"] .item-art').evaluate(n => getComputedStyle(n).backgroundImage.includes('items.png') && n.getBoundingClientRect().width > 20), 'Bag tiles draw the item\'s own pixel icon');
  check(await page.locator('[data-slot="hands"] .item-art').count() === 1 && await page.locator('[data-slot="hands"] .item-art').getAttribute('data-icon') === 'mage_weapon_ash', 'The Hands slot shows the equipped staff icon');
  await page.locator('#field-mageArmor').selectOption('none'); await page.locator('#field-mageWeapon').selectOption('none');
  await page.waitForFunction(() => Field.hero.look.mageArmor === 'none' && Field.hero.look.mageWeapon === 'none');
  check(await page.evaluate(() => Field.equipmentStats.defense === 0 && Field.equipmentStats.attack === 24), 'Rapid slot changes preserve both requests');
  await page.locator('#inventory-list [data-item="mage_weapon_ash"] button').click({ button: 'right' });
  await page.waitForFunction(() => Field.hero.look.mageWeapon === 'ash');
  check(await page.locator('#inventory-list [data-item="mage_weapon_ash"]').count() === 0 && await page.locator('[data-slot="hands"] b').textContent() === 'Ash Staff', 'Equipping moves the owned copy from bag to Hands after confirmation');
  await page.locator('#field-mageArmor').selectOption('apprentice');
  await page.waitForFunction(() => Field.hero.look.mageArmor === 'apprentice');
  await page.locator('#equipment-close').click();
  // Two green slimes are almost equally near (21.62 and 21.63 units); one stands beside an Ironhide that kills a level-1 mage.
  // Take the nearest green whose spawn has no Ironhide spawn within 9 units (home points, because the beetles wander) so the kill is the same every run.
  const enemy = await page.evaluate(() => Field.slimes.filter(s => !s.dead && s.kind === 'green' && !Field.slimes.some(o => o.kind === 'beetle' && Math.hypot(o.hx-s.hx,o.hy-s.hy) < 9)).sort((a,b) => Math.hypot(a.x-Field.hero.x,a.y-Field.hero.y)-Math.hypot(b.x-Field.hero.x,b.y-Field.hero.y))[0]);
  await page.evaluate(id => Online.send({ type: 'target', id }), enemy.id);
  await page.waitForFunction(id => Field.slimes.find(s => s.id === id).dead, enemy.id, { timeout: 30000 });
  await page.evaluate(() => Online.send({ type: 'stop' }));
  const corpse = await page.evaluate(id => { const s = Field.slimes.find(s => s.id === id); return { x:s.x, y:s.y }; }, enemy.id);
  await page.evaluate(p => Online.send({ type:'move', ...p }), corpse);
  await page.waitForFunction(() => Inventory.quantity('slime_gel') === 1, null, { timeout: 15000 });
  await page.evaluate(() => Online.send({ type: 'stop' }));
  await page.locator('#inventory-open').click();
  check(await page.locator('#inventory-list [data-item="slime_gel"]').textContent().then(t => t.includes('3 gold each')), 'Real mob material displays its sale value');
  await page.locator('#inventory-list [data-item="slime_gel"] button').click();
  check(await page.locator('#bag-details [data-action="equip"]').count() === 0, 'Materials have no equip action');
  await page.screenshot({ path: path.join(world.artifacts, 'inventory-real-loot.png') });
  await page.reload(); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.waitForFunction(() => Online.connected && Inventory.quantity('slime_gel') === 1, null, { timeout: 60000 });
  check(await page.evaluate(() => Field.hero.look.mageWeapon === 'ash'), 'Loot and gear resume after page reload');
  await page.evaluate(() => Field.visitNpc('merchant'));
  await page.locator('#npc-dialogue').waitFor({ state: 'visible', timeout: 60000 });
  check(await page.locator('#npc-offers [data-offer="satchel"]').isVisible() && await page.locator('#npc-inventory [data-item]').count() === 0, 'The merchant greets with services and keeps the sell list closed');
  await page.locator('#npc-offers [data-view="sell"]').click();
  check(await page.locator('#npc-inventory [data-item="slime_gel"] [data-sell="one"]').isVisible(), 'Merchant presents sell controls for owned loot');
  check(await page.locator('#npc-inventory [data-item="mage_weapon_ash"]').count() === 0, 'Starter gear is excluded from sales');
  await page.waitForTimeout(600);
  const before = await page.evaluate(() => Field.hero.gold);
  await page.locator('#npc-inventory [data-sell="materials"]').click();
  await page.waitForFunction(gold => Inventory.quantity('slime_gel') === 0 && Field.hero.gold === gold + 3, before);
  check(await page.locator('#npc-notice').textContent().then(t => t.includes('3 gold')), 'Sell all materials consumes loot and displays payment');
  check(await page.locator('#npc-inventory [data-item="slime_gel"]').count() === 0 && await page.locator('#npc-inventory [data-sell="materials"]').count() === 0, 'Shop removes sold materials while allowing any rare gear found in combat');
  await page.screenshot({ path: path.join(world.artifacts, 'inventory-sold.png') });
  await page.locator('#npc-close').click(); await page.locator('#inventory-open').click();
  await page.keyboard.press('Escape');
  check(await page.locator('#equipment').isHidden(), 'Escape closes inventory');
  // New tiers: use test-only grants for prerequisites, then the actual bag controls and server equip path.
  const newGear = await page.evaluate(() => [25, 30, 35, 40, 45, 50].map(level => WORLD_ITEMS.find(i => i.class === 'mage' && i.kind === 'weapon' && i.rarity === 'rare' && !i.source && i.requiredLevel === level))
    .concat(['cloister', 'reliquary', 'nave'].map(wing => WORLD_ITEMS.find(i => i.class === 'mage' && i.kind === 'armor' && i.source === 'cathedral_' + wing))));
  for (const i of newGear) {
    await page.evaluate(i => {
      Online.send({ type: 'debug', ref: 1, command: { op: 'give_item', item: i.id, quantity: 1 } });
      Online.send({ type: 'debug', ref: 2, command: { op: 'set_level', level: i.requiredLevel - 1 } });
    }, i);
    await page.waitForFunction(i => Inventory.quantity(i.id) === 1 && Field.hero.level === i.requiredLevel - 1, i);
    await page.keyboard.press('e');
    await page.locator(`#inventory-list [data-item="${i.id}"] button`).click();
    check(await page.locator('#bag-details [data-action="equip"]').isDisabled(), `${i.name}: level ${i.requiredLevel - 1} cannot equip`);
    check(await page.locator('#bag-details .item-restriction').textContent().then(t => t.includes(`Requires level ${i.requiredLevel}`)), `${i.name}: correct level requirement displayed`);
    await page.evaluate(level => Online.send({ type: 'debug', ref: 3, command: { op: 'set_level', level } }), i.requiredLevel);
    await page.waitForFunction(level => Field.hero.level === level, i.requiredLevel);
    await page.waitForFunction(() => document.querySelector('#bag-details [data-action="equip"]')?.disabled === false);
    await page.locator('#bag-details [data-action="equip"]').click();
    const slot = i.kind === 'weapon' ? 'hands' : 'chest';
    await page.waitForFunction(i => Field.hero.look[i.kind === 'weapon' ? 'mageWeapon' : 'mageArmor'] === i.variant, i);
    check(await page.locator(`[data-slot="${slot}"] b`).textContent() === i.name, `${i.name}: owned piece equips through the server`);
    check(await page.locator(`[data-slot="${slot}"] .item-art`).evaluate((n, i) => n.dataset.icon === i.id && getComputedStyle(n).backgroundImage.includes('items.png') && n.style.filter.includes(`hue-rotate(${i.tint.hue}deg)`), i), `${i.name}: worn slot uses its matching recoloured icon`);
    await page.keyboard.press('Escape');
  }
  await page.reload(); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.waitForFunction(() => Online.connected && Field.hero.look.mageWeapon === 'ash_l50_blue' && Field.hero.look.mageArmor === 'apprentice_l50_nave', null, { timeout: 60000 });
  check(await page.evaluate(() => Inventory.quantity('mage_weapon_ash_l50_blue') === 1 && Inventory.quantity('mage_armor_apprentice_l50_nave') === 1), 'Level-50 world gear and Cathedral gear persist through browser reload');
  await page.keyboard.press('e');
  await page.screenshot({ path: path.join(world.artifacts, 'inventory-gear-50-cathedral.png') });
  check(errors.length === 0, `No browser runtime errors: ${errors.join('; ')}`);

  // Display-only fixtures use the real UI modules without a game connection.
  const fixture = await browser.newPage({ viewport: { width:1440, height:900 } });
  await fixture.setContent('<div id="inventory-list"></div><div id="bag-details"></div><div id="npc-inventory"></div><button id="quest-tracker"></button><div id="quest-journal" hidden><div id="quest-list"></div><button id="quest-close"></button></div><div id="npc-dialogue" hidden><button id="npc-x"></button><button id="npc-back"></button><button id="npc-close"></button></div><canvas id="cv" width="300" height="350"></canvas>');
  await fixture.addStyleTag({ path:path.join(root, 'client/online.css') });
  await fixture.addScriptTag({ path:path.join(root, 'client/world.js') });
  await fixture.addScriptTag({ path:path.join(root, 'client/items.js') });
  await fixture.evaluate(() => {
    window.sent = []; window.Field = { hero: { level: 20 }, equip: change => sent.push(change), equipSlot: (slot, item) => { sent.push({ slot, item }); return true; }, setPaused() {} };
    window.Online = { connected:true, send: message => { sent.push(message); return true; } };
  });
  for (const script of ['inventory.js', 'quests.js', 'city.js']) await fixture.addScriptTag({ path:path.join(root, 'client', script) });
  await fixture.evaluate(() => {
    Inventory.update([{item:'mage_weapon_crystal_l10_purple',quantity:1},{item:'warrior_weapon_royal',quantity:1},{item:'mage_armor_runic',quantity:2},{item:'headgear_upgrade',quantity:1},{item:'pants_upgrade',quantity:1},{item:'mage_armor_apprentice_l5_blue',quantity:1},{item:'slime_gel',quantity:3}], { class:'mage', mageArmor:'runic', mageWeapon:'ash' });
    Inventory.render(document.getElementById('inventory-list'));
    Inventory.renderShop(WORLD_MAP.npcs.find(n => n.id === 'merchant'), document.getElementById('npc-inventory'));
  });
  const rare = fixture.locator('#inventory-list [data-item="mage_weapon_crystal_l10_purple"]');
  check(await rare.textContent().then(t => t.includes('+13.3 attack') && t.includes('Epic') && t.includes('level 10')), 'Epic equipment displays its stat bonus and rarity');
  check(await rare.locator('b').evaluate(n => getComputedStyle(n).color === 'rgb(180, 92, 255)'), 'Epic item name renders purple');
  const tierColors = await fixture.evaluate(() => {
    const out = {};
    for (const [id, tier] of [['slime_gel', 'common'], ['pants_upgrade', 'uncommon'], ['mage_armor_apprentice_l5_blue', 'rare'], ['mage_weapon_crystal_l10_purple', 'epic']]) {
      const cell = document.querySelector(`#inventory-list [data-item="${id}"]`);
      out[tier] = [cell.dataset.rarity, getComputedStyle(cell.querySelector('b')).color];
    }
    // No catalog item is legendary yet, so paint the CSS rule on a stand-in cell.
    const fake = document.createElement('div'); fake.className = 'inventory-item'; fake.dataset.rarity = 'legendary'; fake.innerHTML = '<b>x</b>';
    document.getElementById('inventory-list').append(fake); out.legendary = ['legendary', getComputedStyle(fake.querySelector('b')).color]; fake.remove();
    return out;
  });
  check(JSON.stringify(tierColors) === JSON.stringify({ common: ['common', 'rgb(196, 196, 196)'], uncommon: ['uncommon', 'rgb(74, 214, 109)'], rare: ['rare', 'rgb(100, 181, 255)'], epic: ['epic', 'rgb(180, 92, 255)'], legendary: ['legendary', 'rgb(255, 154, 46)'] }), 'Gray, green, blue, purple and orange name colours for the five tiers: ' + JSON.stringify(tierColors));
  await fixture.locator('#inventory-list [data-item="warrior_weapon_royal"] button').click();
  check(await fixture.locator('#bag-details [data-action="equip"]').count() === 0, 'Cross-class gear cannot be equipped in UI');
  check(await fixture.locator('#inventory-list [data-item="warrior_weapon_royal"]').textContent().then(t => t.includes('warrior')), 'Cross-class gear explains its class restriction');
  await rare.locator('button').click({ button: 'right' });
  check(await fixture.evaluate(() => JSON.stringify(sent[0]) === '{"slot":"hands","item":"mage_weapon_crystal_l10_purple"}'), 'Equip button requests only the selected slot');
  // Required levels: a piece above the hero's level shows a red requirement, offers no usable Equip button and sends nothing.
  await fixture.evaluate(() => { sent.length = 0; Field.hero.level = 5; Inventory.render(document.getElementById('inventory-list')); document.querySelector('#inventory-list [data-item="mage_weapon_crystal_l10_purple"] button').click(); });
  check(await fixture.locator('#bag-details [data-action="equip"]').isDisabled(), 'Equip is disabled for a level 10 piece at level 5');
  check(await fixture.locator('#bag-details .item-restriction').textContent().then(t => t.includes('Requires level 10') && t.includes('you are level 5')), 'The details panel names the missing level in the restriction colour');
  await rare.locator('button').click({ button: 'right' });
  check(await fixture.evaluate(() => sent.length === 0), 'Right-clicking a piece above your level sends no equip request');
  await rare.hover();
  check(await fixture.locator('#item-tooltip .item-restriction').textContent().then(t => t.includes('Requires level 10')), 'The tooltip shows the level requirement in red');
  await fixture.evaluate(() => { Field.hero.level = 10; Inventory.render(document.getElementById('inventory-list')); document.querySelector('#inventory-list [data-item="mage_weapon_crystal_l10_purple"] button').click(); });
  check(await fixture.locator('#bag-details [data-action="equip"]').isEnabled(), 'Equip is enabled once the hero reaches level 10');
  await fixture.evaluate(() => { Field.hero.level = 20; Inventory.render(document.getElementById('inventory-list')); sent.length = 0; });
  await rare.locator('button').click({ button: 'right' });
  check(await fixture.locator('#npc-inventory [data-item="warrior_weapon_royal"] button').count() === 1, 'Cross-class gear can be sold');
  check(await fixture.locator('#npc-inventory [data-item="mage_armor_runic"] button').count() === 1, 'Sale controls reserve one equipped copy');
  check(await fixture.locator('#npc-inventory [data-sell="materials"]').textContent().then(t => t.includes('9 gold')), 'Bulk sale displays the total material value');
  await fixture.evaluate(() => Quests.update([{id:'slime_patrol',claimed:true,completions:1,counts:[6]}]));
  check(await fixture.evaluate(() => Quests.markerInfo('merchant').symbol === '!' && Quests.markerInfo('merchant').color === '#64b5ff'), 'Repeatable availability uses a blue exclamation mark');
  await fixture.evaluate(() => Quests.update([{id:'slime_patrol',claimed:true,completions:1,counts:[6]},{id:'meadow_bounty',claimed:false,completions:0,counts:[8]}]));
  check(await fixture.evaluate(() => Quests.markerInfo('merchant').symbol === '?' && Quests.markerInfo('merchant').color === '#64b5ff'), 'Repeatable turn-in uses a blue question mark');
  check(await fixture.evaluate(() => Quests.markerInfo('guide').symbol === '!' && Quests.markerInfo('guide').color === '#ffdf88'), 'One-time quest markers retain gold');
  check(await fixture.evaluate(() => {
    const g = document.getElementById('cv').getContext('2d'), original = g.fillText, labels=[];
    g.fillText = function(text, ...args) { labels.push({text,color:this.fillStyle}); original.call(this,text,...args); };
    City.drawNpc(g,{ ...WORLD_MAP.npcs.find(n => n.id === 'merchant'), key: true },150,250,0,false);   // key: a giver with work always shows its plate (City.npcs sets it)
    return labels.some(l => l.text === '?' && l.color === '#64b5ff');
  }), 'NPC artwork draws the repeatable marker with blue paint');
  await fixture.screenshot({ path:path.join(world.artifacts,'inventory-rare-display.png') });
  console.log(`${checks} inventory UI checks passed; screenshots: ${world.artifacts}`);
})().catch(async error => { console.error(error); if(page) console.error(await page.evaluate(() => ({ connected:Online.connected, canAct:Field.canAct, equipmentOpen:!document.getElementById('equipment').hidden, skillsOpen:!document.getElementById('skills-panel').hidden, dead:Field.hero.dead, kills:Field.hero.kills, x:Field.hero.x, y:Field.hero.y, hp:Field.hero.hp, logs:document.getElementById('chat-log').textContent, errors:document.getElementById('network-status').textContent })).catch(() => null)); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if(started) await call('stop_world').catch(() => {}); await client.close();
});
